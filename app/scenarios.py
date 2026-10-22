# Descripcion: construye, modifica y serializa los escenarios de red de la app
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path
import random
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EARTH_RADIUS_KM = 6371.0088
DOMAIN_MARGIN_KM = 100.0
MAX_SCENARIO_NODES = 2000
COUNTRY_NAMES = {
	"at": "Austria", "be": "Bélgica", "ch": "Suiza", "cz": "Chequia", "de": "Alemania",
	"es": "España", "fr": "Francia", "gr": "Grecia", "hr": "Croacia", "hu": "Hungría",
	"ie": "Irlanda", "il": "Israel", "it": "Italia", "lu": "Luxemburgo", "nl": "Países Bajos",
	"ny": "Nueva York", "pl": "Polonia", "pt": "Portugal", "se": "Suecia", "si": "Eslovenia",
	"sk": "Eslovaquia", "uk": "Reino Unido",
}


# Lee una tabla CSV de los datos derivados
# Parametro name: nombre del archivo en data/derived
# Retorno: lista de filas como diccionarios
def readTable(name: str) -> list[dict[str, str]]:
	with (ROOT / "data/derived" / name).open(encoding="utf-8", newline="") as source:
		return list(csv.DictReader(source))


# Proyecta longitud y latitud al plano equirectangular del escenario
# Parametros longitude, latitude y projection: coordenadas y parametros
# Retorno: par x, y en km
def projectPoint(longitude: float, latitude: float, projection: dict[str, float]) -> tuple[float, float]:
	scale = projection["radius_km"]
	x = scale * math.radians(longitude - projection["lon0"]) * math.cos(math.radians(projection["lat0"]))
	y = scale * math.radians(latitude - projection["lat0"])
	return x, y


# Recupera longitud y latitud desde el plano del escenario
# Parametros x, y y projection: coordenadas planas y parametros
# Retorno: par longitud, latitud en grados
def unprojectPoint(x: float, y: float, projection: dict[str, float]) -> tuple[float, float]:
	scale = projection["radius_km"]
	longitude = projection["lon0"] + math.degrees(x / (scale * math.cos(math.radians(projection["lat0"]))))
	latitude = projection["lat0"] + math.degrees(y / scale)
	return longitude, latitude


# Calcula la distancia haversine entre dos coordenadas
# Parametros first y second: nodos con lon y lat
# Retorno: distancia en km
def haversineKm(first: dict[str, Any], second: dict[str, Any]) -> float:
	firstLatitude, secondLatitude = math.radians(first["lat"]), math.radians(second["lat"])
	deltaLatitude = secondLatitude - firstLatitude
	deltaLongitude = math.radians(second["lon"] - first["lon"])
	value = (math.sin(deltaLatitude / 2) ** 2 +
	         math.cos(firstLatitude) * math.cos(secondLatitude) * math.sin(deltaLongitude / 2) ** 2)
	return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))


# Calcula el rectangulo planar que envuelve los nodos con margen
# Parametro nodes: nodos con x e y
# Retorno: dominio [xmin, ymin, xmax, ymax]
def planarDomain(nodes: list[dict[str, Any]]) -> list[float]:
	xs = [node["x"] for node in nodes]
	ys = [node["y"] for node in nodes]
	return [min(xs) - DOMAIN_MARGIN_KM, min(ys) - DOMAIN_MARGIN_KM,
	        max(xs) + DOMAIN_MARGIN_KM, max(ys) + DOMAIN_MARGIN_KM]


# Construye el escenario base GEANT a partir de los archivos derivados
# Parametros: ninguno
# Retorno: escenario con nodos, enlaces y parametros de prueba
def geantScenario() -> dict[str, Any]:
	settings = json.loads((ROOT / "data/derived/scenarios.json").read_text(encoding="utf-8"))
	capacities = {int(row["edge_index"]): float(row["scenario_capacity_mbps"]) for row in readTable("capacities.csv")}
	nodes = []
	for row in readTable("nodes.csv"):
		code = row["id"].split(".")[-1]
		nodes.append({
			"id": row["id"], "label": COUNTRY_NAMES.get(code, row["id"]), "short": code.upper(),
			"lon": float(row["longitude_deg"]), "lat": float(row["latitude_deg"]),
			"x": float(row["x_km"]), "y": float(row["y_km"]),
		})
	edges = []
	for row in readTable("edges.csv"):
		index = int(row["index"])
		edges.append({
			"id": row["id"], "u": int(row["u"]), "v": int(row["v"]),
			"cost": float(row["working_cost"]), "distance": float(row["distance_km"]),
			"capacity": capacities[index],
		})
	return {
		"name": "GÉANT base", "kind": "geant",
		"description": "Topología SNDlib GÉANT (22 nodos, 36 enlaces). Capacidades con un módulo supuesto de "
		               "40 000 Mbit/s por enlace; distancias haversine; costos en unidades del XML.",
		"nodes": nodes, "edges": edges, "projection": settings["projection"],
		"domain": settings["domain"], "source": settings["source"], "sink": settings["sink"],
		"tspSelected": settings["tsp_selected"],
	}


# Genera una red sintetica conectada sobre Europa con semilla reproducible
# Parametros nodeCount, extraRatio y seed: tamano, densidad y semilla
# Retorno: escenario sintetico
def syntheticScenario(nodeCount: int, extraRatio: float, seed: int) -> dict[str, Any]:
	if not 3 <= nodeCount <= 300:
		raise ValueError("La red sintética admite entre 3 y 300 nodos")
	generator = random.Random(seed)
	projection = {"type": "equirectangular", "lat0": 50.0, "lon0": 10.0, "radius_km": EARTH_RADIUS_KM}
	nodes = []
	for index in range(nodeCount):
		longitude, latitude = generator.uniform(-9.0, 28.0), generator.uniform(37.0, 60.0)
		x, y = projectPoint(longitude, latitude, projection)
		nodes.append({"id": f"s{index:03d}", "label": f"Central {index + 1}", "short": str(index + 1), "lon": longitude,
		              "lat": latitude, "x": x, "y": y})

	pairs = set()
	connected = [False] * nodeCount
	bestDistance = [math.inf] * nodeCount
	bestParent = [-1] * nodeCount
	bestDistance[0] = 0.0
	for _ in range(nodeCount):
		current = min((index for index in range(nodeCount) if not connected[index]), key=lambda index: bestDistance[index])
		connected[current] = True
		if bestParent[current] >= 0:
			pairs.add((min(current, bestParent[current]), max(current, bestParent[current])))
		for other in range(nodeCount):
			distance = haversineKm(nodes[current], nodes[other])
			if not connected[other] and distance < bestDistance[other]:
				bestDistance[other], bestParent[other] = distance, current
	candidates = sorted(((haversineKm(nodes[first], nodes[second]), first, second)
	                     for first in range(nodeCount) for second in range(first + 1, nodeCount)
	                     if (first, second) not in pairs))
	extraCount = min(len(candidates), round(extraRatio * nodeCount))
	shortlist = candidates[:max(extraCount * 3, extraCount)]
	for _, first, second in generator.sample(shortlist, extraCount):
		pairs.add((first, second))

	edges = []
	for first, second in sorted(pairs):
		distance = haversineKm(nodes[first], nodes[second])
		edges.append({
			"id": f"{nodes[first]['id']}_{nodes[second]['id']}", "u": first, "v": second,
			"cost": round(distance * generator.uniform(0.8, 1.6), 1), "distance": round(distance, 3),
			"capacity": float(generator.choice([10000, 40000, 40000, 100000])),
		})
	return {
		"name": f"Sintética {nodeCount} nodos · semilla {seed}", "kind": "synthetic",
		"description": f"Red aleatoria reproducible: árbol euclidiano mínimo (Prim) y {extraCount} enlaces "
		               f"adicionales entre centrales próximas. Costos proporcionales a la distancia.",
		"nodes": nodes, "edges": edges, "projection": projection, "domain": planarDomain(nodes),
		"source": 0, "sink": nodeCount - 1, "tspSelected": list(range(min(nodeCount, 40))),
	}


# Deriva un escenario con enlaces caidos y capacidades escaladas
# Parametros base, failedEdgeIds, capacityFactor y name: escenario y cambios
# Retorno: escenario nuevo, sin modificar el original
def derivedScenario(base: dict[str, Any], failedEdgeIds: list[str], capacityFactor: float, name: str) -> dict[str, Any]:
	if capacityFactor <= 0:
		raise ValueError("El factor de capacidad debe ser positivo")
	scenario = copy.deepcopy(base)
	failed = set(failedEdgeIds)
	scenario["edges"] = [edge for edge in scenario["edges"] if edge["id"] not in failed]
	for edge in scenario["edges"]:
		edge["capacity"] = edge["capacity"] * capacityFactor
	changes = []
	if failed:
		changes.append(f"{len(failed)} enlace(s) fuera de servicio: {', '.join(sorted(failed))}")
	if capacityFactor != 1:
		changes.append(f"capacidades × {capacityFactor:g}")
	scenario["name"] = name
	scenario["kind"] = "derived"
	scenario["description"] = f"Derivado de «{base['name']}»" + (": " + "; ".join(changes) if changes else "")
	return scenario


# Valida la estructura de un escenario importado
# Parametro scenario: objeto leido desde JSON
# Retorno: escenario normalizado; lanza ValueError si es invalido
def validateScenario(scenario: Any) -> dict[str, Any]:
	if not isinstance(scenario, dict):
		raise ValueError("El escenario debe ser un objeto JSON")
	for key in ("name", "nodes", "edges"):
		if key not in scenario:
			raise ValueError(f"Falta el campo {key}")
	nodes, edges = scenario["nodes"], scenario["edges"]
	if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_SCENARIO_NODES:
		raise ValueError(f"nodes debe tener entre 1 y {MAX_SCENARIO_NODES} elementos")
	projection = scenario.get("projection") or {"type": "equirectangular", "lat0": 50.0, "lon0": 10.0,
	                                            "radius_km": EARTH_RADIUS_KM}
	valid = (isinstance(projection, dict) and
	         all(isinstance(projection.get(key), (int, float)) for key in ("lat0", "lon0", "radius_km")) and
	         abs(projection["lat0"]) < 85 and projection["radius_km"] > 0)
	if not valid:
		raise ValueError("projection necesita lat0 entre -85 y 85, lon0 y radius_km positivo")
	normalizedNodes = []
	for index, node in enumerate(nodes):
		if not isinstance(node, dict) or not all(isinstance(node.get(key), (int, float)) for key in ("lon", "lat")):
			raise ValueError(f"El nodo {index} necesita lon y lat numéricos")
		if not (-180 <= node["lon"] <= 180 and -90 <= node["lat"] <= 90):
			raise ValueError(f"El nodo {index} tiene coordenadas fuera de rango")
		x, y = projectPoint(node["lon"], node["lat"], projection)
		identifier = str(node.get("id", f"n{index}"))
		normalizedNodes.append({"id": identifier, "label": str(node.get("label", identifier)),
		                        "short": str(node.get("short", identifier))[:6],
		                        "lon": float(node["lon"]), "lat": float(node["lat"]), "x": x, "y": y})
	normalizedEdges = []
	for index, edge in enumerate(edges if isinstance(edges, list) else []):
		valid = (isinstance(edge, dict) and type(edge.get("u")) is int and type(edge.get("v")) is int
		         and 0 <= edge["u"] < len(nodes) and 0 <= edge["v"] < len(nodes) and edge["u"] != edge["v"])
		if not valid:
			raise ValueError(f"El enlace {index} necesita u y v enteros distintos dentro de rango")
		distance = edge.get("distance", haversineKm(normalizedNodes[edge["u"]], normalizedNodes[edge["v"]]))
		normalizedEdges.append({
			"id": str(edge.get("id", f"{normalizedNodes[edge['u']]['id']}_{normalizedNodes[edge['v']]['id']}")),
			"u": edge["u"], "v": edge["v"], "cost": float(edge.get("cost", distance)),
			"distance": float(distance), "capacity": float(edge.get("capacity", 40000)),
		})
	values = [value for edge in normalizedEdges for value in (edge["cost"], edge["distance"], edge["capacity"])]
	if not all(math.isfinite(value) for value in values):
		raise ValueError("Costos, distancias y capacidades deben ser números finitos")
	if any(edge["distance"] < 0 or edge["capacity"] < 0 for edge in normalizedEdges):
		raise ValueError("Distancias y capacidades deben ser no negativas")

	# Comprueba que un campo opcional sea un indice de nodo valido
	# Parametros key y default: campo y valor por omision
	# Retorno: indice validado
	def nodeIndex(key: str, default: int) -> int:
		value = scenario.get(key, default)
		if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < len(nodes):
			raise ValueError(f"{key} debe ser un índice de nodo entre 0 y {len(nodes) - 1}")
		return value

	selected = scenario.get("tspSelected", list(range(min(len(nodes), 40))))
	if (not isinstance(selected, list) or not selected or len(set(map(str, selected))) != len(selected) or
	    not all(isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(nodes) for value in selected)):
		raise ValueError("tspSelected debe ser una lista no vacía de índices de nodo distintos")
	domain = scenario.get("domain") or planarDomain(normalizedNodes)
	if (not isinstance(domain, list) or len(domain) != 4 or
	    not all(isinstance(value, (int, float)) and math.isfinite(value) for value in domain) or
	    domain[0] >= domain[2] or domain[1] >= domain[3]):
		raise ValueError("domain debe ser [xmin, ymin, xmax, ymax] con área positiva")
	return {
		"name": str(scenario["name"]), "kind": "uploaded",
		"description": str(scenario.get("description", "Escenario importado desde JSON")),
		"nodes": normalizedNodes, "edges": normalizedEdges, "projection": projection,
		"domain": [float(value) for value in domain],
		"source": nodeIndex("source", 0), "sink": nodeIndex("sink", len(nodes) - 1), "tspSelected": selected,
	}


# Serializa un escenario para descargarlo y volver a cargarlo
# Parametro scenario: escenario de la app
# Retorno: texto JSON con indentacion
def scenarioToJson(scenario: dict[str, Any]) -> str:
	exported = {key: scenario[key] for key in ("name", "description", "projection", "domain", "source",
	                                           "sink", "tspSelected")}
	exported["nodes"] = [{key: node[key] for key in ("id", "label", "short", "lon", "lat") if key in node}
	                     for node in scenario["nodes"]]
	exported["edges"] = scenario["edges"]
	return json.dumps(exported, indent=2, ensure_ascii=False)


# Arma la solicitud del arbol de expansion minima
# Parametro scenario: escenario activo
# Retorno: modo y entrada del motor
def mstRequest(scenario: dict[str, Any]) -> tuple[str, dict[str, Any]]:
	return "mst", {"n": len(scenario["nodes"]),
	               "edges": [{"u": edge["u"], "v": edge["v"], "cost": edge["cost"]} for edge in scenario["edges"]]}


# Arma la solicitud del recorrido de mantenimiento
# Parametros scenario, selected, exactLimit y maxPasses: escenario y opciones
# Retorno: modo y entrada del motor
def tspRequest(scenario: dict[str, Any], selected: list[int], exactLimit: int = 16,
               maxPasses: int = 100) -> tuple[str, dict[str, Any]]:
	return "tsp", {"n": len(scenario["nodes"]), "selected": list(selected), "exact_limit": exactLimit,
	               "max_passes": maxPasses,
	               "edges": [{"u": edge["u"], "v": edge["v"], "distance": edge["distance"]} for edge in scenario["edges"]]}


# Arma la solicitud del flujo maximo
# Parametros scenario, source, sink y directed: escenario y extremos
# Retorno: modo y entrada del motor
def flowRequest(scenario: dict[str, Any], source: int, sink: int, directed: bool = False) -> tuple[str, dict[str, Any]]:
	return "max_flow", {"n": len(scenario["nodes"]), "source": source, "sink": sink, "directed": directed,
	                    "edges": [{"u": edge["u"], "v": edge["v"], "capacity": edge["capacity"]}
	                              for edge in scenario["edges"]]}


# Arma la solicitud de regiones de Voronoi con consultas opcionales
# Parametros scenario y queries: escenario y puntos lon/lat a consultar
# Retorno: modo y entrada del motor
def voronoiRequest(scenario: dict[str, Any], queries: list[tuple[float, float]] | None = None) -> tuple[str, dict[str, Any]]:
	projected = [list(projectPoint(longitude, latitude, scenario["projection"])) for longitude, latitude in queries or []]
	return "voronoi", {"sites": [[node["x"], node["y"]] for node in scenario["nodes"]],
	                   "domain": scenario["domain"], "queries": projected}


# Calcula el area planar de un poligono
# Parametro polygon: vertices [x, y]
# Retorno: area en unidades al cuadrado
def polygonArea(polygon: list[list[float]]) -> float:
	if len(polygon) < 3:
		return 0.0
	return abs(sum(polygon[index][0] * polygon[(index + 1) % len(polygon)][1] -
	               polygon[(index + 1) % len(polygon)][0] * polygon[index][1]
	               for index in range(len(polygon)))) / 2


# Lee las transmisiones y firmas de ejemplo con su asociacion simulada
# Parametros: ninguno
# Retorno: textos, firmas y filas de mapping.csv
def sampleTransmissions() -> tuple[list[str], list[str], list[dict[str, str]]]:
	folder = ROOT / "data/synthetic"
	texts = [(folder / f"transmission{index}.txt").read_text(encoding="ascii").replace("\r", "").replace("\n", "")
	         for index in (1, 2)]
	patterns = [(folder / f"mcode{index}.txt").read_text(encoding="ascii").strip() for index in (1, 2, 3)]
	with (ROOT / "data/original/mapping.csv").open(encoding="utf-8", newline="") as source:
		mapping = list(csv.DictReader(source))
	return texts, patterns, mapping
