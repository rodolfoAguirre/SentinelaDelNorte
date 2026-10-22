# Descripcion: reproduce los casos funcionales y de estres del autograder web 1.1.0
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = ROOT / ("build/sentinela.exe" if sys.platform == "win32" else "build/sentinela")
MODES = ["mst", "tsp", "flow", "voronoi", "matching", "palindrome", "common"]
HEX = "0123456789ABCDEF"
MASK = 0xFFFFFFFF
PROFILES = {
	"lite": {"mst_n": 400, "mst_extra": 2000, "tsp_n": 60, "flow_n": 80, "flow_extra": 600,
	         "voronoi_n": 80, "matching_len": 50000, "pal_len": 50000, "common_len": 12000, "timeout": 6},
	"normal": {"mst_n": 1200, "mst_extra": 7000, "tsp_n": 120, "flow_n": 180, "flow_extra": 1800,
	           "voronoi_n": 180, "matching_len": 220000, "pal_len": 220000, "common_len": 55000, "timeout": 8},
	"huge": {"mst_n": 5000, "mst_extra": 30000, "tsp_n": 450, "flow_n": 450, "flow_extra": 9000,
	         "voronoi_n": 500, "matching_len": 1000000, "pal_len": 1000000, "common_len": 180000, "timeout": 18},
}


class SiteRandom:
	# Inicializa el generador con la misma semilla de 32 bits del sitio
	# Parametro seed: semilla del reporte
	# Retorno: instancia lista para generar valores
	def __init__(self, seed):
		self.state = seed & MASK

	# Replica el generador mulberry32 de la pagina
	# Parametros: ninguno
	# Retorno: flotante en [0, 1)
	def random(self):
		self.state = (self.state + 1831565813) & MASK
		value = self.state
		value = ((value ^ (value >> 15)) * (value | 1)) & MASK
		value ^= (value + (((value ^ (value >> 7)) * (value | 61)) & MASK)) & MASK
		return ((value ^ (value >> 14)) & MASK) / 4294967296

	# Genera un entero inclusivo
	# Parametros low y high: limites del intervalo
	# Retorno: entero entre low y high
	def randint(self, low, high):
		return low + math.floor(self.random() * (high - low + 1))

	# Genera un indice menor al limite
	# Parametro limit: cantidad de opciones
	# Retorno: entero entre 0 y limit - 1
	def randrange(self, limit):
		return math.floor(self.random() * limit)

	# Construye un texto con simbolos aleatorios
	# Parametros alphabet y count: simbolos y longitud
	# Retorno: cadena generada
	def choices(self, alphabet, count):
		return "".join(alphabet[self.randrange(len(alphabet))] for _ in range(count))

	# Toma una muestra sin reemplazo con Fisher-Yates parcial
	# Parametros values y count: poblacion y cantidad
	# Retorno: lista con la muestra
	def sample(self, values, count):
		pool = list(values)
		for index in range(count):
			other = index + self.randrange(len(pool) - index)
			pool[index], pool[other] = pool[other], pool[index]
		return pool[:count]


# Redondea como Math.round de JavaScript
# Parametro value: numero a redondear
# Retorno: entero mas cercano con mitades hacia arriba
def jsRound(value):
	return math.floor(value + 0.5)


# Compara con la tolerancia relativa del sitio
# Parametros actual, expected y tolerance: valores y tolerancia
# Retorno: true si son equivalentes
def isClose(actual, expected, tolerance=1e-5):
	return (isinstance(actual, (int, float)) and math.isfinite(actual) and
	        abs(actual - expected) <= tolerance * max(1, abs(expected)))


# Genera una matriz simetrica de distancias enteras
# Parametros generator, size, low y high: generador, nodos y rango
# Retorno: matriz cuadrada
def randomMatrix(generator, size, low=1, high=60):
	matrix = [[0] * size for _ in range(size)]
	for row in range(size):
		for column in range(row + 1, size):
			matrix[row][column] = matrix[column][row] = generator.randint(low, high)
	return matrix


# Genera los casos funcionales de un modo
# Parametros mode y generator: algoritmo y generador compartido
# Retorno: lista de entradas
def functionalCases(mode, generator):
	cases = []
	if mode == "mst":
		for size in (4, 7, 11):
			edges = [{"u": node, "v": node + 1, "weight": generator.randint(1, 25)} for node in range(size - 1)]
			for source in range(size):
				for target in range(source + 2, size):
					if generator.random() < 0.4:
						edges.append({"u": source, "v": target, "weight": generator.randint(1, 25)})
			cases.append({"nodes": list(range(size)), "edges": edges})
	if mode == "tsp":
		for size in (4, 6, 9):
			cases.append({"distances": randomMatrix(generator, size)})
	if mode == "flow":
		for size in (4, 7, 10):
			edges = [{"u": node, "v": node + 1, "capacity": generator.randint(5, 30)} for node in range(size - 1)]
			for source in range(size):
				for target in range(size):
					if source != target and generator.random() < 0.18:
						edges.append({"u": source, "v": target, "capacity": generator.randint(1, 35)})
			cases.append({"n": size, "edges": edges, "source": 0, "sink": size - 1})
	if mode == "voronoi":
		grid = [[x, y] for x in range(5, 96, 10) for y in range(5, 96, 10)]
		for count in (2, 4, 7):
			cases.append({"sites": generator.sample(grid, count), "bounds": [0, 0, 100, 100]})
	if mode == "matching":
		cases.append({"transmissions": ["AAABCDFFF", "001234ABCDEF"], "patterns": ["ABCD", "1234", "FFFF"]})
		first = generator.choices(HEX, 2500)
		second = generator.choices(HEX, 2600)
		signature = "FEDCBA9876543210"
		first = first[:1300] + signature + first[1300:]
		cases.append({"transmissions": [first, second], "patterns": [signature, "ABC", "0000000"]})
	if mode == "palindrome":
		cases.append({"transmissions": ["AABCDCBAE", "ABCBA123321"]})
		cases.append({"transmissions": ["ABCDEF", "AAAABAAAA"]})
	if mode == "common":
		cases.append({"transmissions": ["AA1234BBB", "DD1234EE"]})
		cases.append({"transmissions": ["ABCXXCBA", "ZZABCYYCBA"]})
	return cases


# Genera el caso grande de un modo segun el perfil
# Parametros mode, generator y profile: algoritmo, generador y tamanos
# Retorno: entrada del caso de estres
def stressCase(mode, generator, profile):
	if mode == "mst":
		size = profile["mst_n"]
		edges = [{"u": node, "v": node + 1, "weight": generator.randint(1, 1000)} for node in range(size - 1)]
		seen = {edge["u"] * size + edge["v"] for edge in edges}
		while len(edges) < size - 1 + profile["mst_extra"]:
			source, target = generator.randrange(size), generator.randrange(size)
			if source != target:
				source, target = min(source, target), max(source, target)
				if source * size + target not in seen:
					seen.add(source * size + target)
					edges.append({"u": source, "v": target, "weight": generator.randint(1, 1000)})
		return {"nodes": list(range(size)), "edges": edges}
	if mode == "tsp":
		size = profile["tsp_n"]
		points = []
		for index in range(size):
			angle = 2 * math.pi * index / size
			radius = 100000 + generator.randint(-100, 100)
			points.append((radius * math.cos(angle), radius * math.sin(angle)))
		matrix = [[0] * size for _ in range(size)]
		for row in range(size):
			for column in range(row + 1, size):
				matrix[row][column] = matrix[column][row] = jsRound(math.hypot(
					points[row][0] - points[column][0], points[row][1] - points[column][1]))
		return {"distances": matrix}
	if mode == "flow":
		size = profile["flow_n"]
		edges = [{"u": node, "v": node + 1, "capacity": generator.randint(100, 10000)} for node in range(size - 1)]
		seen = {edge["u"] * size + edge["v"] for edge in edges}
		while len(edges) < size - 1 + profile["flow_extra"]:
			source, target = generator.randrange(size), generator.randrange(size)
			if source != target and source * size + target not in seen:
				seen.add(source * size + target)
				edges.append({"u": source, "v": target, "capacity": generator.randint(1, 10000)})
		return {"n": size, "edges": edges, "source": 0, "sink": size - 1}
	if mode == "voronoi":
		sites = []
		seen = set()
		while len(sites) < profile["voronoi_n"]:
			site = (generator.randint(1, 99999), generator.randint(1, 99999))
			if site not in seen:
				seen.add(site)
				sites.append(list(site))
		return {"sites": sites, "bounds": [0, 0, 100000, 100000]}
	if mode == "matching":
		length = profile["matching_len"]
		first = generator.choices(HEX, length)
		second = generator.choices(HEX, length)
		patterns = ["DEADBEEFCAFEBABE", "0123456789ABCDEF0123456789ABCDEF",
		            "FACEFACEFACEFACEFACE", "FFFFEEEEDDDDCCCCBBBB"]
		third, twoThirds = length // 3, (2 * length) // 3
		first = first[:third] + patterns[0] + first[third:]
		second = second[:twoThirds] + patterns[1] + second[twoThirds:]
		return {"transmissions": [first, second], "patterns": patterns}
	if mode == "palindrome":
		length = profile["pal_len"]
		half = generator.choices(HEX, length // 4)
		mirrored = half + "A" + half[::-1]
		prefix = generator.choices(HEX, max(1, length // 4))
		suffix = generator.choices(HEX, max(1, length // 4))
		return {"transmissions": [prefix + mirrored + suffix, generator.choices(HEX, length)]}
	length = profile["common_len"]
	shared = generator.choices(HEX, max(500, length // 8))
	half = length // 2
	first = generator.choices(HEX, half) + shared + generator.choices(HEX, half)
	second = generator.choices(HEX, half) + shared + generator.choices(HEX, half)
	return {"transmissions": [first, second]}


# Calcula el costo del MST de referencia con Kruskal
# Parametro case: entrada del caso
# Retorno: costo minimo
def referenceMst(case):
	parents = list(range(len(case["nodes"])))

	# Busca el representante con compresion de camino
	# Parametro node: nodo consultado
	# Retorno: representante del conjunto
	def findRoot(node):
		while parents[node] != node:
			parents[node] = parents[parents[node]]
			node = parents[node]
		return node

	cost = 0
	for edge in sorted(case["edges"], key=lambda item: (item["weight"], item["u"], item["v"])):
		first, second = findRoot(edge["u"]), findRoot(edge["v"])
		if first != second:
			parents[first] = second
			cost += edge["weight"]
	return cost


# Calcula el tour optimo de referencia con Held-Karp
# Parametro case: matriz de distancias pequena
# Retorno: costo optimo
def referenceTsp(case):
	matrix = case["distances"]
	size = len(matrix)
	if size <= 1:
		return 0
	costs = {(1, 0): 0}
	for mask in range(1, 1 << size, 2):
		for last in range(size):
			current = costs.get((mask, last))
			if current is not None:
				for nextNode in range(1, size):
					if not mask & (1 << nextNode):
						key = (mask | (1 << nextNode), nextNode)
						candidate = current + matrix[last][nextNode]
						if candidate < costs.get(key, math.inf):
							costs[key] = candidate
	full = (1 << size) - 1
	return min(costs[(full, last)] + matrix[last][0] for last in range(1, size))


# Calcula el flujo maximo de referencia con Edmonds-Karp
# Parametro case: red dirigida con capacidades
# Retorno: valor del flujo maximo
def referenceFlow(case):
	size = case["n"]
	adjacency = [[] for _ in range(size)]
	targets, residuals = [], []
	for edge in case["edges"]:
		adjacency[edge["u"]].append(len(targets))
		targets.append(edge["v"])
		residuals.append(edge["capacity"])
		adjacency[edge["v"]].append(len(targets))
		targets.append(edge["u"])
		residuals.append(0)
	source, sink, total = case["source"], case["sink"], 0
	augmenting = True
	while augmenting:
		parentArc = [-1] * size
		parentArc[source] = -2
		queue = [source]
		head = 0
		while head < len(queue) and parentArc[sink] == -1:
			node = queue[head]
			head += 1
			for arc in adjacency[node]:
				if residuals[arc] > 0 and parentArc[targets[arc]] == -1:
					parentArc[targets[arc]] = arc
					queue.append(targets[arc])
		augmenting = parentArc[sink] != -1
		if augmenting:
			bottleneck, node = math.inf, sink
			while node != source:
				arc = parentArc[node]
				bottleneck = min(bottleneck, residuals[arc])
				node = targets[arc ^ 1]
			node = sink
			while node != source:
				arc = parentArc[node]
				residuals[arc] -= bottleneck
				residuals[arc ^ 1] += bottleneck
				node = targets[arc ^ 1]
			total += bottleneck
	return total


# Calcula las areas de referencia recortando semiplanos
# Parametro case: sitios y limites
# Retorno: lista de areas por sitio
def referenceVoronoiAreas(case):
	sites = case["sites"]
	xMin, yMin, xMax, yMax = case["bounds"]
	areas = []
	for siteIndex, (siteX, siteY) in enumerate(sites):
		polygon = [(xMin, yMin), (xMax, yMin), (xMax, yMax), (xMin, yMax)]
		for otherIndex, (otherX, otherY) in enumerate(sites):
			if otherIndex != siteIndex and polygon:
				normalX, normalY = 2 * (otherX - siteX), 2 * (otherY - siteY)
				offset = otherX * otherX + otherY * otherY - siteX * siteX - siteY * siteY
				clipped = []
				for vertexIndex, point in enumerate(polygon):
					nextPoint = polygon[(vertexIndex + 1) % len(polygon)]
					first = normalX * point[0] + normalY * point[1] - offset
					second = normalX * nextPoint[0] + normalY * nextPoint[1] - offset
					if first <= 1e-9:
						clipped.append(point)
					if (first < -1e-9 and second > 1e-9) or (first > 1e-9 and second < -1e-9):
						fraction = first / (first - second)
						clipped.append((point[0] + fraction * (nextPoint[0] - point[0]),
						                point[1] + fraction * (nextPoint[1] - point[1])))
				polygon = clipped
		areas.append(polygonArea(polygon))
	return areas


# Calcula el area de un poligono con la formula del zapato
# Parametro polygon: vertices en orden
# Retorno: area absoluta
def polygonArea(polygon):
	if len(polygon) < 3:
		return 0
	return abs(sum(polygon[index][0] * polygon[(index + 1) % len(polygon)][1] -
	               polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
	               for index in range(len(polygon)))) / 2


# Calcula el palindromo de referencia con Manacher sobre texto intercalado
# Parametro text: transmision
# Retorno: intervalo inclusivo base uno
def referencePalindrome(text):
	if not text:
		return [0, 0]
	expanded = "^#" + "#".join(text) + "#$"
	radii = [0] * len(expanded)
	center = right = 0
	bestLength, bestStart = 1, 0
	for index in range(1, len(expanded) - 1):
		if index < right:
			radii[index] = min(right - index, radii[2 * center - index])
		while expanded[index + 1 + radii[index]] == expanded[index - 1 - radii[index]]:
			radii[index] += 1
		if index + radii[index] > right:
			center, right = index, index + radii[index]
		length, start = radii[index], (index - radii[index]) >> 1
		if length > bestLength or (length == bestLength and start < bestStart):
			bestLength, bestStart = length, start
	return [bestStart + 1, bestStart + bestLength]


# Calcula la subcadena comun de referencia con programacion dinamica
# Parametro case: dos transmisiones pequenas
# Retorno: intervalo inclusivo en la primera transmision
def referenceCommon(case):
	first, second = case["transmissions"]
	previous = [0] * (len(second) + 1)
	bestLength = bestStart = bestSecond = 0
	for firstIndex in range(len(first)):
		current = [0] * (len(second) + 1)
		for secondIndex in range(len(second)):
			if first[firstIndex] == second[secondIndex]:
				length = current[secondIndex + 1] = previous[secondIndex] + 1
				start, secondStart = firstIndex - length + 1, secondIndex - length + 1
				if length > bestLength or (length == bestLength and (start, secondStart) < (bestStart, bestSecond)):
					bestLength, bestStart, bestSecond = length, start, secondStart
		previous = current
	return [0, 0] if bestLength == 0 else [bestStart + 1, bestStart + bestLength]


# Valida una respuesta con las reglas del sitio
# Parametros mode, case, answer y stress: modo, entrada, salida y tipo de caso
# Retorno: tupla con aprobado y motivo
def validate(mode, case, answer, stress):
	if not isinstance(answer, dict):
		return False, "response is not a JSON object"
	if mode == "mst":
		size = len(case["nodes"])
		edges = answer.get("edges")
		if not isinstance(edges, list) or len(edges) != size - 1:
			return False, "MST must return exactly n-1 edges"
		weights = {}
		for edge in case["edges"]:
			key = (min(edge["u"], edge["v"]), max(edge["u"], edge["v"]))
			weights[key] = min(weights.get(key, math.inf), edge["weight"])
		parents = list(range(size))

		# Busca el representante para detectar ciclos
		# Parametro node: nodo consultado
		# Retorno: representante del conjunto
		def findRoot(node):
			while parents[node] != node:
				parents[node] = parents[parents[node]]
				node = parents[node]
			return node

		total = 0
		for edge in edges:
			key = (min(edge[0], edge[1]), max(edge[0], edge[1]))
			if key not in weights:
				return False, "MST uses a non-existing edge"
			first, second = findRoot(edge[0]), findRoot(edge[1])
			if first == second:
				return False, "MST contains cycle"
			parents[first] = second
			total += weights[key]
		if len({findRoot(node) for node in range(size)}) != 1:
			return False, "MST not connected"
		if not isClose(answer.get("cost"), total):
			return False, "reported MST cost does not match selected edges"
		return (True, "ok") if isClose(total, referenceMst(case)) else (False, "MST is not minimum")
	if mode == "tsp":
		route, matrix = answer.get("route"), case["distances"]
		size = len(matrix)
		if not isinstance(route, list) or len(route) != size + 1:
			return False, "TSP route must have n+1 nodes"
		if route[0] != 0 or route[-1] != 0 or sorted(route[:-1]) != list(range(size)):
			return False, "TSP route is not a Hamiltonian cycle from node 0"
		total = sum(matrix[route[index]][route[index + 1]] for index in range(size))
		if not isClose(answer.get("cost"), total):
			return False, "reported TSP cost does not match route"
		if not stress and not isClose(total, referenceTsp(case)):
			return False, "TSP is not optimal on exact test"
		return True, "ok"
	if mode == "flow":
		return (True, "ok") if isClose(answer.get("flow"), referenceFlow(case)) else (False, "wrong maximum flow")
	if mode == "voronoi":
		cells = answer.get("cells")
		if not isinstance(cells, list) or len(cells) != len(case["sites"]):
			return False, "wrong number of Voronoi cells"
		expected = referenceVoronoiAreas(case)
		for index, cell in enumerate(cells):
			if not isinstance(cell, list) or len(cell) < 3:
				return False, f"invalid Voronoi cell {index}"
			if not isClose(polygonArea(cell), expected[index], 0.003):
				return False, f"wrong Voronoi area for cell {index}"
		return True, "ok"
	if mode == "matching":
		expected = [[text.find(pattern) + 1 if pattern in text else -1 for pattern in case["patterns"]]
		            for text in case["transmissions"]]
		return (True, "ok") if answer.get("matches") == expected else (False, "wrong string-match positions")
	if mode == "palindrome":
		expected = [referencePalindrome(text) for text in case["transmissions"]]
		return (True, "ok") if answer.get("ranges") == expected else (False, "wrong longest-palindrome ranges")
	if not stress:
		return (True, "ok") if answer.get("range") == referenceCommon(case) else (
			False, "wrong longest-common-substring range")
	return validateLargeCommon(case, answer)


# Valida la subcadena comun grande como lo hace el sitio
# Parametros case y answer: entrada y salida del motor
# Retorno: tupla con aprobado y motivo
def validateLargeCommon(case, answer):
	interval = answer.get("range")
	if not isinstance(interval, list) or len(interval) != 2 or not all(isinstance(value, int) for value in interval):
		return False, "invalid common-substring response"
	start, end = interval
	first, second = case["transmissions"]
	if start == 0 and end == 0:
		return False, "empty range on large common-substring test"
	if not 1 <= start <= end <= len(first):
		return False, "invalid common-substring range"
	fragment = first[start - 1:end]
	minimum = max(500, case["sharedLength"])
	if len(fragment) >= minimum and fragment in second:
		return True, "ok"
	return False, "returned common substring is too short or absent in second transmission"


# Ejecuta el motor con el contrato web
# Parametros executable, mode, case y timeout: binario, modo, entrada y limite
# Retorno: respuesta, segundos y error
def runEngine(executable, mode, case, timeout):
	payload = json.dumps({"mode": mode, "input": {key: value for key, value in case.items() if key != "sharedLength"}})
	started = time.perf_counter()
	try:
		process = subprocess.run([str(executable), "--autograder"], input=payload, text=True,
		                         capture_output=True, timeout=timeout)
	except subprocess.TimeoutExpired:
		return None, time.perf_counter() - started, "timeout"
	seconds = time.perf_counter() - started
	if process.returncode != 0:
		return None, seconds, f"exit {process.returncode}: {process.stderr.strip()[:200]}"
	try:
		return json.loads(process.stdout), seconds, ""
	except json.JSONDecodeError:
		return None, seconds, "invalid JSON on stdout"


# Corre una semilla completa con el mismo orden de generacion del sitio
# Parametros executable, seed y profileName: binario, semilla y perfil
# Retorno: lista de registros
def runSeed(executable, seed, profileName):
	profile = PROFILES[profileName]
	generator = SiteRandom(seed)
	records = []
	for mode in MODES:
		for caseIndex, case in enumerate(functionalCases(mode, generator)):
			answer, seconds, error = runEngine(executable, mode, case, profile["timeout"])
			passed, reason = validate(mode, case, answer, False) if not error else (False, error)
			records.append({"seed": seed, "profile": profileName, "mode": mode, "stress": False,
			                "case": caseIndex, "pass": passed, "reason": reason, "seconds": round(seconds, 4)})
	for mode in MODES:
		case = stressCase(mode, generator, profile)
		if mode == "common":
			case["sharedLength"] = profile["common_len"] // 8
		answer, seconds, error = runEngine(executable, mode, case, profile["timeout"])
		passed, reason = validate(mode, case, answer, True) if not error else (False, error)
		records.append({"seed": seed, "profile": profileName, "mode": mode, "stress": True,
		                "pass": passed, "reason": reason, "seconds": round(seconds, 4),
		                "timeoutSeconds": profile["timeout"]})
		print(f"[{'OK' if passed else 'FALLA'}] {profileName:6} semilla={seed} {mode:10} "
		      f"{seconds:7.3f}s / {profile['timeout']}s  {reason}", flush=True)
	return records


# Ejecuta perfiles y semillas, y guarda el reporte
# Parametros: ninguno; lee argumentos de terminal
# Retorno: cero si todos los casos aprueban
def main():
	parser = argparse.ArgumentParser(description="Replica local del autograder web de Sentinela")
	parser.add_argument("executable", nargs="?", default=str(DEFAULT_EXE))
	parser.add_argument("--profiles", nargs="+", default=["lite", "normal", "huge"], choices=list(PROFILES))
	parser.add_argument("--seeds", nargs="+", type=int, default=[1114129554, 2038, 42])
	parser.add_argument("--output", default=str(ROOT / "results/stress_autograder.json"))
	arguments = parser.parse_args()
	executable = Path(arguments.executable).resolve()

	records = []
	for profileName in arguments.profiles:
		for seed in arguments.seeds:
			records.extend(runSeed(executable, seed, profileName))
	failures = [record for record in records if not record["pass"]]
	report = {"graderVersion": "1.1.0-web", "target": "native replay of site generators and validators",
	          "executable": executable.name, "profiles": arguments.profiles, "seeds": arguments.seeds,
	          "cases": len(records), "failures": len(failures), "success": not failures, "records": records}
	Path(arguments.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
	print(f"{len(records) - len(failures)}/{len(records)} casos aprobados; reporte en {arguments.output}")
	return 0 if not failures else 1


if __name__ == "__main__":
	sys.exit(main())
