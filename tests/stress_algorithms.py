# Descripcion: pruebas de estres de los siete algoritmos hasta los limites del contrato
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import argparse
import csv
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = ROOT / ("build/sentinela.exe" if os.name == "nt" else "build/sentinela")
SEED = 20261022
HEX = "0123456789ABCDEF"
TIME_BUDGET_SECONDS = 10.0
MEMORY_BUDGET_BYTES = 1024 * 1024 * 1024
HASH_MODULUS = (1 << 61) - 1
HASH_BASE = 1_000_003
SCALES = {
	"pequena": {"nodes": 12, "edges": 30, "tspSelected": 8, "exactLimit": 8, "sites": 12,
	            "queries": 200, "textLength": 80},
	"mediana": {"nodes": 200, "edges": 2000, "tspSelected": 60, "exactLimit": 12, "sites": 150,
	            "queries": 5000, "textLength": 20000},
	"grande": {"nodes": 1000, "edges": 50000, "tspSelected": 250, "exactLimit": 16, "sites": 500,
	           "queries": 50000, "textLength": 250000},
	"limite": {"nodes": 2000, "edges": 200000, "tspSelected": 500, "exactLimit": 18, "sites": 1000,
	           "queries": 100000, "textLength": 2000000},
}


class Engine:
	# Guarda la ruta del motor y las mediciones acumuladas
	# Parametro executable: ruta del ejecutable
	# Retorno: instancia lista para ejecutar casos
	def __init__(self, executable):
		self.executable = executable
		self.records = []

	# Ejecuta una solicitud con metricas y valida presupuestos
	# Parametros group, label, mode e inputData: identificacion y datos del caso
	# Parametro expectError: true si el caso debe rechazarse
	# Retorno: resultado del algoritmo o mensaje de error esperado
	def run(self, group, label, mode, inputData, expectError=False, size=None):
		payload = json.dumps({"mode": mode, "input": inputData, "metrics": True})
		started = time.perf_counter()
		process = subprocess.run([str(self.executable)], input=payload, text=True,
		                         capture_output=True, cwd=ROOT, timeout=120)
		wallSeconds = time.perf_counter() - started
		response = json.loads(process.stdout)
		metrics = response.get("metrics", {})
		record = {
			"group": group, "case": label, "mode": mode, "size": size,
			"payloadBytes": len(payload), "wallSeconds": round(wallSeconds, 4),
			"algorithmSeconds": round(metrics.get("algorithm_us", 0) / 1e6, 6),
			"peakProcessBytes": metrics.get("peak_process_bytes"),
		}
		self.records.append(record)
		if expectError:
			assert not response["ok"] and process.returncode == 1, f"{label}: se esperaba rechazo"
			assert wallSeconds < TIME_BUDGET_SECONDS, f"{label}: el rechazo tardo {wallSeconds:.2f}s"
			record["error"] = response["error"]
			return response["error"]

		assert response["ok"] and process.returncode == 0, f"{label}: {response.get('error')}"
		assert wallSeconds < TIME_BUDGET_SECONDS, f"{label}: {wallSeconds:.2f}s excede {TIME_BUDGET_SECONDS}s"
		peak = record["peakProcessBytes"]
		assert peak is None or peak < MEMORY_BUDGET_BYTES, f"{label}: {peak} bytes excede el presupuesto"
		return response["result"]


# Genera una red conectada con costo, distancia y capacidad por enlace
# Parametros nodeCount, edgeCount y generator: tamano y generador
# Retorno: lista de enlaces con los tres pesos
def randomGraph(nodeCount, edgeCount, generator):
	edges = []
	for node in range(1, nodeCount):
		edges.append({"u": generator.randrange(node), "v": node})
	while len(edges) < edgeCount:
		source, target = generator.randrange(nodeCount), generator.randrange(nodeCount)
		if source != target:
			edges.append({"u": source, "v": target})
	for edge in edges:
		edge["cost"] = generator.randint(-50, 1000)
		edge["distance"] = generator.randint(1, 1000)
		edge["capacity"] = generator.randint(1, 1000)
	return edges


# Conserva solo los campos necesarios de cada enlace
# Parametros edges y field: enlaces y peso requerido
# Retorno: enlaces con u, v y el peso indicado
def project(edges, field):
	return [{"u": edge["u"], "v": edge["v"], field: edge[field]} for edge in edges]


class DisjointSet:
	# Inicializa un componente por nodo
	# Parametro size: cantidad de nodos
	# Retorno: estructura lista
	def __init__(self, size):
		self.parents = list(range(size))

	# Busca el representante con compresion de camino
	# Parametro node: nodo consultado
	# Retorno: representante
	def find(self, node):
		while self.parents[node] != node:
			self.parents[node] = self.parents[self.parents[node]]
			node = self.parents[node]
		return node

	# Une dos componentes
	# Parametros first y second: nodos a unir
	# Retorno: true si estaban separados
	def join(self, first, second):
		first, second = self.find(first), self.find(second)
		self.parents[first] = second
		return first != second


# Verifica bosque, costo y minimalidad contra Kruskal independiente
# Parametros result, nodeCount y edges: respuesta y entrada
# Retorno: sin valor; falla si el bosque no es minimo
def checkMst(result, nodeCount, edges):
	forest = DisjointSet(nodeCount)
	for index in result["edge_indices"]:
		assert forest.join(edges[index]["u"], edges[index]["v"]), "el MST contiene un ciclo"
	assert result["total_cost"] == sum(edges[index]["cost"] for index in result["edge_indices"])

	reference = DisjointSet(nodeCount)
	referenceCost, components = 0, nodeCount
	for edge in sorted(edges, key=lambda item: item["cost"]):
		if reference.join(edge["u"], edge["v"]):
			referenceCost += edge["cost"]
			components -= 1
	assert result["total_cost"] == referenceCost, "el costo no es minimo"
	assert result["components"] == components
	assert result["connected"] == (components == 1)
	assert len(result["edge_indices"]) == nodeCount - components


# Verifica tour, recorrido fisico y distancia reportada
# Parametros result, edges y selected: respuesta y entrada
# Retorno: sin valor; falla ante un recorrido inconsistente
def checkTour(result, edges, selected):
	tour, nodes, edgeIndices = result["tour"], result["physical_nodes"], result["physical_edge_indices"]
	assert tour[0] == tour[-1] == selected[0]
	assert sorted(tour[:-1]) == sorted(selected), "el tour no visita cada central una vez"
	assert nodes[0] == nodes[-1] == selected[0]
	assert len(edgeIndices) == len(nodes) - 1
	for position, index in enumerate(edgeIndices):
		assert {edges[index]["u"], edges[index]["v"]} == {nodes[position], nodes[position + 1]}
	assert math.isclose(sum(edges[index]["distance"] for index in edgeIndices), result["total_distance"])
	cursor = 0
	for node in nodes:
		if cursor < len(tour) and node == tour[cursor]:
			cursor += 1
	assert cursor == len(tour), "el recorrido fisico no sigue el orden del tour"


# Calcula el optimo por permutaciones sobre distancias minimas
# Parametros nodeCount, edges y selected: entrada pequena
# Retorno: distancia optima
def bruteForceTour(nodeCount, edges, selected):
	distances = [[math.inf] * nodeCount for _ in range(nodeCount)]
	for node in range(nodeCount):
		distances[node][node] = 0
	for edge in edges:
		weight = min(distances[edge["u"]][edge["v"]], edge["distance"])
		distances[edge["u"]][edge["v"]] = distances[edge["v"]][edge["u"]] = weight
	for middle, source, target in itertools.product(range(nodeCount), repeat=3):
		distances[source][target] = min(distances[source][target], distances[source][middle] + distances[middle][target])
	start = selected[0]
	return min(sum(distances[route[index]][route[index + 1]] for index in range(len(route) - 1))
	           for order in itertools.permutations(selected[1:])
	           for route in [(start,) + order + (start,)])


# Verifica capacidades, conservacion y el certificado de corte minimo
# Parametros result, inputData: respuesta y entrada
# Retorno: sin valor; falla si el flujo no es maximo
def checkFlow(result, inputData):
	edges, directed = inputData["edges"], inputData["directed"]
	source, sink = inputData["source"], inputData["sink"]
	balance = [0.0] * inputData["n"]
	for item in result["flows"]:
		edge, flow = edges[item["edge_index"]], item["flow"]
		lower = 0 if directed else -edge["capacity"]
		assert lower - 1e-9 <= flow <= edge["capacity"] + 1e-9, "flujo fuera de capacidad"
		balance[edge["u"]] -= flow
		balance[edge["v"]] += flow
	tolerance = 1e-7 * max(1.0, result["value"])
	for node, amount in enumerate(balance):
		assert node in (source, sink) or abs(amount) <= tolerance, f"no se conserva el flujo en {node}"
	assert math.isclose(balance[sink], result["value"], rel_tol=1e-9, abs_tol=1e-7)

	sourceSide = set(result["source_side"])
	assert source in sourceSide and sink not in sourceSide
	cut = sum(edge["capacity"] for edge in edges if
	          (edge["u"] in sourceSide and edge["v"] not in sourceSide) or
	          (not directed and edge["v"] in sourceSide and edge["u"] not in sourceSide))
	assert math.isclose(cut, result["value"], rel_tol=1e-9, abs_tol=1e-7), "el flujo no iguala el corte"


# Calcula el area con signo de un poligono
# Parametro polygon: vertices en orden
# Retorno: area positiva si es antihorario
def signedArea(polygon):
	return sum(polygon[index][0] * polygon[(index + 1) % len(polygon)][1] -
	           polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
	           for index in range(len(polygon))) / 2


# Verifica particion del dominio, equidistancia de vertices y consultas
# Parametros result, inputData y generator: respuesta, entrada y muestreo
# Retorno: sin valor; falla si alguna region es incorrecta
def checkVoronoi(result, inputData, generator):
	sites, queries = inputData["sites"], inputData.get("queries", [])
	xMin, yMin, xMax, yMax = inputData["domain"]
	domainArea = (xMax - xMin) * (yMax - yMin)
	assert len(result["cells"]) == len(sites)
	assert all(signedArea(cell) >= -1e-9 * domainArea for cell in result["cells"] if cell), "celda no antihoraria"
	totalArea = sum(signedArea(cell) for cell in result["cells"] if cell)
	assert math.isclose(totalArea, domainArea, rel_tol=1e-7), "las celdas no cubren el dominio"

	sampled = generator.sample(range(len(sites)), min(len(sites), 60))
	scale = max(xMax - xMin, yMax - yMin)
	for siteIndex in sampled:
		for vertex in result["cells"][siteIndex]:
			own = math.dist(vertex, sites[siteIndex])
			assert all(own <= math.dist(vertex, other) + 1e-7 * scale for other in sites), "vertice fuera de su region"

	for queryIndex in generator.sample(range(len(queries)), min(len(queries), 2000)):
		query = queries[queryIndex]
		expected = min(range(len(sites)), key=lambda index: ((query[0] - sites[index][0]) ** 2 +
		                                                     (query[1] - sites[index][1]) ** 2, index))
		assert result["nearest"][queryIndex] == expected, "consulta asignada al sitio equivocado"


# Calcula el palindromo mas largo con Manacher sobre texto intercalado
# Parametro text: transmision
# Retorno: inicio base cero y longitud
def referencePalindrome(text):
	if not text:
		return 0, 0
	expanded = "^#" + "#".join(text) + "#$"
	radii = [0] * len(expanded)
	center = right = 0
	bestLength, bestStart = 1, 0
	for index in range(1, len(expanded) - 1):
		radius = min(right - index, radii[2 * center - index]) if index < right else 0
		while expanded[index + 1 + radius] == expanded[index - 1 - radius]:
			radius += 1
		radii[index] = radius
		if index + radius > right:
			center, right = index, index + radius
		start = (index - radius) >> 1
		if radius > bestLength or (radius == bestLength and start < bestStart):
			bestLength, bestStart = radius, start
	return bestStart, bestLength


# Calcula los hashes rodantes de todas las ventanas de una longitud
# Parametros text y length: secuencia y tamano de ventana
# Retorno: lista de hashes por posicion inicial
def windowHashes(text, length):
	if length == 0 or length > len(text):
		return []
	power = pow(HASH_BASE, length, HASH_MODULUS)
	current, hashes = 0, []
	for position, character in enumerate(text):
		current = (current * HASH_BASE + ord(character)) % HASH_MODULUS
		if position >= length:
			current = (current - ord(text[position - length]) * power) % HASH_MODULUS
		if position >= length - 1:
			hashes.append(current)
	return hashes


# Busca la primera ventana de la primera secuencia presente en la segunda
# Parametros firstText, secondText y length: secuencias y longitud
# Retorno: inicio base cero o -1 si no existe
def firstSharedWindow(firstText, secondText, length):
	secondHashes = set(windowHashes(secondText, length))
	found = -1
	for start, value in enumerate(windowHashes(firstText, length)):
		if found < 0 and value in secondHashes and firstText[start:start + length] in secondText:
			found = start
	return found


# Verifica firmas, palindromos y subcadena comun con referencias independientes
# Parametros result, texts y patterns: respuesta y entradas
# Retorno: sin valor; falla ante cualquier diferencia
def checkStrings(result, texts, patterns):
	for match in result["matches"]:
		position = texts[match["transmission"] - 1].find(patterns[match["pattern"] - 1])
		assert match["found"] == (position >= 0)
		assert match["position"] == (position + 1 if position >= 0 else 0)

	for text, palindrome in zip(texts, result["palindromes"]):
		start, length = referencePalindrome(text)
		assert palindrome["length"] == length, "palindromo no maximo"
		assert palindrome["start"] == (start + 1 if length else 0), "desempate de palindromo incorrecto"

	common = result["common"]
	length = common["length"]
	if length:
		fragment = texts[0][common["start"] - 1:common["end"]]
		assert len(fragment) == length and texts[1][common["start2"] - 1:common["end2"]] == fragment
		assert firstSharedWindow(texts[0], texts[1], length) == common["start"] - 1, "desempate en T1"
		assert texts[1].find(fragment) == common["start2"] - 1, "desempate en T2"
	assert firstSharedWindow(texts[0], texts[1], length + 1) < 0, "existe una subcadena comun mas larga"


# Ejecuta los siete algoritmos en una escala con certificados de correctitud
# Parametros engine, label, settings y generator: motor, escala y generador
# Retorno: sin valor; falla si una propiedad se rompe
def stressScale(engine, label, settings, generator):
	nodeCount, edgeCount = settings["nodes"], settings["edges"]
	edges = randomGraph(nodeCount, edgeCount, generator)
	group = f"escala:{label}"

	result = engine.run(group, f"{label}-mst", "mst", {"n": nodeCount, "edges": project(edges, "cost")}, size=edgeCount)
	checkMst(result, nodeCount, edges)

	selected = generator.sample(range(nodeCount), settings["tspSelected"])
	tspInput = {"n": nodeCount, "edges": project(edges, "distance"), "selected": selected}
	result = engine.run(group, f"{label}-tsp-heuristico", "tsp", dict(tspInput, exact_limit=1, max_passes=1000),
	                    size=len(selected))
	checkTour(result, edges, selected)
	assert not result["exact"] and result["improvements"] < 1000, "2-opt agoto el presupuesto de pases"
	heuristicDistance = result["total_distance"]

	exactSelected = selected[:settings["exactLimit"]]
	result = engine.run(group, f"{label}-tsp-exacto", "tsp", dict(tspInput, selected=exactSelected, exact_limit=18),
	                    size=len(exactSelected))
	checkTour(result, edges, exactSelected)
	assert result["exact"]
	if len(exactSelected) <= 8:
		assert math.isclose(result["total_distance"], bruteForceTour(nodeCount, project(edges, "distance"), exactSelected))
	if len(exactSelected) == len(selected):
		assert result["total_distance"] <= heuristicDistance + 1e-9

	for directed in (True, False):
		flowInput = {"n": nodeCount, "edges": project(edges, "capacity"), "source": 0,
		             "sink": nodeCount - 1, "directed": directed}
		result = engine.run(group, f"{label}-flujo-{'dirigido' if directed else 'no-dirigido'}", "max_flow",
		                    flowInput, size=edgeCount)
		checkFlow(result, flowInput)

	span = 1000.0 * settings["sites"]
	voronoiInput = {
		"sites": [[generator.uniform(0, span), generator.uniform(0, span)] for _ in range(settings["sites"])],
		"domain": [0, 0, span, span],
		"queries": [[generator.uniform(-0.1 * span, 1.1 * span), generator.uniform(-0.1 * span, 1.1 * span)]
		            for _ in range(settings["queries"])],
	}
	result = engine.run(group, f"{label}-voronoi", "voronoi", voronoiInput, size=settings["sites"])
	checkVoronoi(result, voronoiInput, generator)

	textLength = settings["textLength"]
	texts = [generator.choices(HEX, k=textLength) for _ in range(2)]
	texts = ["".join(texts[0]), "".join(texts[1])]
	planted = "".join(generator.choices(HEX, k=min(64, textLength // 4)))
	position = generator.randrange(textLength - len(planted))
	texts[1] = texts[1][:position] + planted + texts[1][position + len(planted):]
	patterns = [texts[0][textLength // 2:textLength // 2 + 32], planted, "0123456789ABCDEF"]
	result = engine.run(group, f"{label}-cadenas", "strings", {"transmissions": texts, "patterns": patterns},
	                    size=textLength)
	checkStrings(result, texts, patterns)


# Ejecuta entradas degeneradas y peores casos de cada algoritmo
# Parametros engine y generator: motor y generador
# Retorno: sin valor; falla si un caso extremo se resuelve mal
def stressAdversarial(engine, generator):
	group = "adversarial"
	disconnected = [{"u": index, "v": index + 1, "cost": 5} for index in range(0, 1999, 2)]
	result = engine.run(group, "mst-desconectado-1000-componentes", "mst", {"n": 2000, "edges": disconnected}, size=2000)
	checkMst(result, 2000, disconnected)
	assert not result["connected"] and result["components"] == 1000

	ties = [{"u": source, "v": target, "cost": 7} for source in range(300) for target in range(source + 1, 300)]
	result = engine.run(group, "mst-empates-grafo-completo", "mst", {"n": 300, "edges": ties}, size=len(ties))
	checkMst(result, 300, ties)
	assert result["edge_indices"] == sorted(result["edge_indices"]), "el desempate por indice no es estable"

	parallel = [{"u": 0, "v": 1, "cost": cost} for cost in range(1000, -1000, -1)]
	result = engine.run(group, "mst-enlaces-paralelos-negativos", "mst", {"n": 2, "edges": parallel}, size=2000)
	assert result["total_cost"] == -999 and result["edge_indices"] == [1999]

	line = [{"u": index, "v": index + 1, "distance": 1} for index in range(1999)]
	ends = list(range(0, 2000, 4))
	result = engine.run(group, "tsp-linea-500-centrales", "tsp", {"n": 2000, "edges": line, "selected": ends},
	                    size=len(ends))
	checkTour(result, line, ends)
	assert result["total_distance"] == 2 * (ends[-1] - ends[0]), "la ruta optima en linea es ir y volver"

	star = [{"u": 0, "v": leaf, "distance": leaf} for leaf in range(1, 18)]
	result = engine.run(group, "tsp-estrella-exacto-18", "tsp",
	                    {"n": 18, "edges": star, "selected": list(range(18)), "exact_limit": 18}, size=18)
	checkTour(result, star, list(range(18)))
	assert result["total_distance"] == 2 * sum(range(1, 18))

	result = engine.run(group, "tsp-una-central", "tsp", {"n": 1, "edges": [], "selected": [0]}, size=1)
	assert result["tour"] == [0, 0] and result["total_distance"] == 0

	chain = [{"u": index, "v": index + 1, "capacity": 1000 - index % 997} for index in range(1999)]
	flowInput = {"n": 2000, "edges": chain, "source": 0, "sink": 1999, "directed": True}
	result = engine.run(group, "flujo-cadena-2000-profundidad", "max_flow", flowInput, size=2000)
	checkFlow(result, flowInput)
	assert result["value"] == min(edge["capacity"] for edge in chain)

	layers, width = 39, 50
	layered = [{"u": 0, "v": 1 + column, "capacity": 1} for column in range(width)]
	for layer in range(layers - 1):
		for column in range(width):
			for other in range(width):
				layered.append({"u": 1 + layer * width + column, "v": 1 + (layer + 1) * width + other, "capacity": 1})
	sink = 1 + layers * width
	layered.extend({"u": 1 + (layers - 1) * width + column, "v": sink, "capacity": 1} for column in range(width))
	flowInput = {"n": sink + 1, "edges": layered, "source": 0, "sink": sink, "directed": True}
	result = engine.run(group, "flujo-capas-unitarias-95k", "max_flow", flowInput, size=len(layered))
	checkFlow(result, flowInput)
	assert result["value"] == width

	flowInput = {"n": 2000, "edges": [{"u": 1, "v": 2, "capacity": 9}], "source": 0, "sink": 1999, "directed": False}
	result = engine.run(group, "flujo-sin-camino", "max_flow", flowInput, size=1)
	assert result["value"] == 0

	collinear = {"sites": [[float(index), 0.0] for index in range(1000)], "domain": [-1, -500, 1000, 500],
	             "queries": [[index + 0.5, 3.0] for index in range(999)]}
	result = engine.run(group, "voronoi-1000-colineales", "voronoi", collinear, size=1000)
	checkVoronoi(result, collinear, generator)
	assert result["nearest"] == list(range(999)), "empates deben ir al menor indice"

	grid = {"sites": [[float(x), float(y)] for x in range(32) for y in range(31)], "domain": [-1, -1, 32, 31],
	        "queries": [[x + 0.5, y + 0.5] for x in range(31) for y in range(30)]}
	result = engine.run(group, "voronoi-rejilla-992-equidistantes", "voronoi", grid, size=992)
	checkVoronoi(result, grid, generator)

	duplicates = {"sites": [[5.0, 5.0]] * 500 + [[1.0, 1.0]] * 500, "domain": [0, 0, 10, 10]}
	result = engine.run(group, "voronoi-500-duplicados", "voronoi", duplicates, size=1000)
	assert result["cells"][0] and result["cells"][500] and all(not cell for index, cell in
	                                                           enumerate(result["cells"]) if index not in (0, 500))

	single = {"sites": [[1e7, 1e7]], "domain": [-1e7, -1e7, 1e7, 1e7], "queries": [[0, 0]]}
	result = engine.run(group, "voronoi-un-sitio-fuera-de-escala", "voronoi", single, size=1)
	assert math.isclose(signedArea(result["cells"][0]), 4e14)

	length = 2_000_000
	cases = [
		("cadenas-todo-A-2M", ["A" * length, "A" * length], ["A" * (length // 2) + "B", "A" * 1000, ""]),
		("cadenas-vacias", ["", ""], ["", "A", "F"]),
		("cadenas-patron-mayor-que-texto", ["ABC", "DEF"], ["ABCD", "DEFF", "A" * 5000]),
		("cadenas-periodicas-250k", ["ABC" * 83333, "BCA" * 83333], ["ABC" * 1000, "CAB", "AA"]),
	]
	for label, texts, patterns in cases:
		result = engine.run(group, label, "strings", {"transmissions": texts, "patterns": patterns}, size=len(texts[0]))
		checkStrings(result, texts, patterns)

	alternating = ["AB" * (length // 2), "BA" * (length // 2)]
	result = engine.run(group, "cadenas-alternadas-2M", "strings",
	                    {"transmissions": alternating, "patterns": ["AB" * 500 + "A", "BB", "ABA"]}, size=length)
	assert result["palindromes"][0] == {"start": 1, "end": length - 1, "length": length - 1}
	assert result["common"] == {"start": 1, "end": length - 1, "start2": 2, "end2": length, "length": length - 1}
	assert [match["found"] for match in result["matches"]] == [True, False, True, True, False, True]


# Comprueba que cada limite del contrato se rechaza sin colapsar
# Parametro engine: motor
# Retorno: sin valor; falla si un exceso se acepta o rompe el proceso
def stressRejections(engine):
	group = "rechazo"
	oversized = [
		("mst-2001-nodos", "mst", {"n": 2001, "edges": []}),
		("mst-200001-enlaces", "mst", {"n": 2, "edges": [{"u": 0, "v": 1, "cost": 1}] * 200001}),
		("mst-peso-1e13", "mst", {"n": 2, "edges": [{"u": 0, "v": 1, "cost": 1e13}]}),
		("tsp-501-centrales", "tsp", {"n": 600, "edges": [], "selected": list(range(501))}),
		("tsp-exact-limit-19", "tsp", {"n": 2, "edges": [], "selected": [0, 1], "exact_limit": 19}),
		("tsp-desconectado", "tsp", {"n": 3, "edges": [{"u": 0, "v": 1, "distance": 1}], "selected": [0, 2]}),
		("flujo-capacidad-negativa", "max_flow", {"n": 2, "edges": [{"u": 0, "v": 1, "capacity": -1}],
		                                          "source": 0, "sink": 1, "directed": True}),
		("voronoi-1001-sitios", "voronoi", {"sites": [[index, 0] for index in range(1001)], "domain": [0, 0, 1, 1]}),
		("voronoi-100001-consultas", "voronoi", {"sites": [[0, 0]], "domain": [0, 0, 1, 1],
		                                         "queries": [[0, 0]] * 100001}),
		("voronoi-coordenada-1e8", "voronoi", {"sites": [[1e8, 0]], "domain": [0, 0, 1, 1]}),
		("cadena-2000001", "palindrome", {"transmissions": ["A" * 2000001, "A"]}),
		("cadena-minusculas", "palindrome", {"transmissions": ["abc", "A"]}),
		("cadena-espacios", "palindrome", {"transmissions": ["AB C", "A"]}),
	]
	for label, mode, inputData in oversized:
		engine.run(group, label, mode, inputData, expectError=True)


# Mide la pendiente log-log del tiempo frente al tamano
# Parametros sizes y seconds: tamanos y tiempos medianos
# Retorno: pendiente de minimos cuadrados
def logSlope(sizes, seconds):
	points = [(math.log(size), math.log(max(value, 1e-6))) for size, value in zip(sizes, seconds)]
	meanX = statistics.fmean(point[0] for point in points)
	meanY = statistics.fmean(point[1] for point in points)
	return (sum((x - meanX) * (y - meanY) for x, y in points) /
	        sum((x - meanX) ** 2 for x, _ in points))


# Duplica el tamano de entrada y compara el crecimiento con la teoria
# Parametros engine y generator: motor y generador
# Retorno: lista de ajustes por algoritmo
def stressScaling(engine, generator):
	families = []
	baseEdges = randomGraph(2000, 200000, generator)
	edgeSizes = [25000, 50000, 100000, 200000]
	families.append(("mst", "O(E log E)", 1.0, edgeSizes,
	                 lambda size: ("mst", {"n": 2000, "edges": project(baseEdges[:size], "cost")})))
	families.append(("max_flow", "O(V^2 E) peor caso", None, edgeSizes,
	                 lambda size: ("max_flow", {"n": 2000, "edges": project(baseEdges[:size], "capacity"),
	                                            "source": 0, "sink": 1999, "directed": True})))
	families.append(("tsp_heuristico", "O(k (V+E) log V + P k^2)", 1.0, [62, 125, 250, 500],
	                 lambda size: ("tsp", {"n": 2000, "edges": project(baseEdges[:20000], "distance"),
	                                       "selected": list(range(size)), "exact_limit": 1})))
	families.append(("tsp_held_karp", "O(2^k k^2)", None, [12, 14, 16, 18],
	                 lambda size: ("tsp", {"n": 2000, "edges": project(baseEdges[:20000], "distance"),
	                                       "selected": list(range(size)), "exact_limit": 18})))
	families.append(("voronoi", "O(n^2 m)", 2.0, [125, 250, 500, 1000],
	                 lambda size: ("voronoi", {"sites": [[generator.uniform(0, 1e6), generator.uniform(0, 1e6)]
	                                                     for _ in range(size)], "domain": [0, 0, 1e6, 1e6]})))
	text = "".join(generator.choices(HEX, k=2_000_000))
	other = "".join(generator.choices(HEX, k=2_000_000))
	textSizes = [250000, 500000, 1000000, 2000000]
	for mode in ("matching", "palindrome", "common_substring"):
		families.append((mode, "O(n + m)" if mode == "matching" else "O(n)", 1.0, textSizes,
		                 lambda size, mode=mode: (mode, {"transmissions": [text[:size], other[:size]],
		                                                 "patterns": ["F" * 32, text[size // 2:size // 2 + 64], "A" * 64]})))

	fits = []
	for name, complexity, expected, sizes, build in families:
		medians = []
		for size in sizes:
			mode, inputData = build(size)
			samples = []
			for repetition in range(3):
				engine.run("escalabilidad", f"{name}-{size}-r{repetition}", mode, inputData, size=size)
				samples.append(engine.records[-1]["algorithmSeconds"])
			medians.append(statistics.median(samples))
		slope = logSlope(sizes, medians)
		fits.append({"algorithm": name, "theory": complexity, "sizes": sizes,
		             "medianAlgorithmSeconds": medians, "logLogSlope": round(slope, 3),
		             "expectedSlope": expected,
		             "withinExpectation": None if expected is None else slope <= expected + 0.35})
		print(f"  {name:18} pendiente={slope:5.2f} esperada={expected if expected is not None else '-':>4}  {complexity}")
	return fits


# Ejecuta las escalas, los casos extremos, los rechazos y la escalabilidad
# Parametros: ninguno; lee argumentos de terminal
# Retorno: cero si todas las propiedades se cumplen
def main():
	parser = argparse.ArgumentParser(description="Pruebas de estres del motor Sentinela")
	parser.add_argument("executable", nargs="?", default=str(DEFAULT_EXE))
	parser.add_argument("--quick", action="store_true", help="omite la escala limite y la escalabilidad")
	arguments = parser.parse_args()
	engine = Engine(Path(arguments.executable).resolve())
	generator = random.Random(SEED)
	started = time.perf_counter()

	for label, settings in SCALES.items():
		if not (arguments.quick and label == "limite"):
			stressScale(engine, label, settings, generator)
			print(f"[OK] escala {label}: {settings['nodes']} nodos, {settings['edges']} enlaces, "
			      f"{settings['textLength']} caracteres", flush=True)
	stressAdversarial(engine, generator)
	print("[OK] casos adversariales", flush=True)
	stressRejections(engine)
	print("[OK] rechazos de entradas fuera de contrato", flush=True)
	fits = []
	if not arguments.quick:
		print("Escalabilidad (tiempo interno del algoritmo, mediana de 3):")
		fits = stressScaling(engine, generator)

	slowest = max(engine.records, key=lambda record: record["wallSeconds"])
	heaviest = max(engine.records, key=lambda record: record["peakProcessBytes"] or 0)
	report = {
		"seed": SEED, "executable": engine.executable.name, "success": True,
		"platform": platform.platform(), "processor": platform.processor() or platform.machine(),
		"python": platform.python_version(), "quick": arguments.quick,
		"timeBudgetSeconds": TIME_BUDGET_SECONDS, "memoryBudgetBytes": MEMORY_BUDGET_BYTES,
		"totalSeconds": round(time.perf_counter() - started, 2), "cases": len(engine.records),
		"slowestCase": slowest, "heaviestCase": heaviest, "scaling": fits, "records": engine.records,
	}
	if arguments.quick:
		print(f"{len(engine.records)} ejecuciones aprobadas en {report['totalSeconds']}s (modo rapido, sin reporte)")
		return 0

	output = ROOT / "results/stress_tests.json"
	output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
	with (ROOT / "results/stress_tests.csv").open("w", newline="", encoding="utf-8") as table:
		writer = csv.DictWriter(table, fieldnames=["group", "case", "mode", "size", "payloadBytes",
		                                           "wallSeconds", "algorithmSeconds", "peakProcessBytes", "error"])
		writer.writeheader()
		writer.writerows(engine.records)
	print(f"{len(engine.records)} ejecuciones aprobadas en {report['totalSeconds']}s; "
	      f"mas lenta: {slowest['case']} {slowest['wallSeconds']}s; "
	      f"mayor memoria: {heaviest['case']} {(heaviest['peakProcessBytes'] or 0) / 2 ** 20:.0f} MB")
	return 0


if __name__ == "__main__":
	sys.exit(main())
