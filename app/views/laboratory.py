# Descripcion: ejecuta los algoritmos de red con parametros y compara escenarios
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import json
from pathlib import Path
import random

import streamlit as st

from .. import charts
from ..scenarios import (ROOT, flowRequest, haversineKm, mstRequest, polygonArea, readTable, tspRequest,
                         voronoiRequest)
from ..state import (activeScenario, edgeLabel, nodeLabel, runEngine, sectionHeader, showEngineMetrics)


DEFAULT_QUERIES = [
	{"lugar": "Múnich", "longitud": 11.58, "latitud": 48.14},
	{"lugar": "Barcelona", "longitud": 2.17, "latitud": 41.39},
	{"lugar": "Varsovia", "longitud": 21.01, "latitud": 52.23},
	{"lugar": "Copenhague", "longitud": 12.57, "latitud": 55.68},
	{"lugar": "Atenas", "longitud": 23.73, "latitud": 37.98},
]
COMPARISONS = {
	"Costo del MST": "mst",
	"Distancia del recorrido TSP": "tsp",
	"Flujo máximo origen → destino": "max_flow",
	"Área máxima de una región Voronoi": "voronoi",
}


# Muestra el error del motor o devuelve el resultado
# Parametro outcome: respuesta de runEngine
# Retorno: resultado del algoritmo o None
def resultOrError(outcome: dict) -> dict | None:
	if not outcome["ok"]:
		st.error(f"El motor rechazó la solicitud ({outcome['kind']}): {outcome['error']}")
		return None
	return outcome["response"]["result"]


# Pestaña del arbol de expansion minima
# Parametro scenario: escenario activo
# Retorno: sin valor; dibuja la pestana
def mstTab(scenario: dict) -> None:
	st.markdown("Conecta todas las centrales con el menor costo total de instalación, sin ciclos. **Kruskal** "
	            "ordena los enlaces por costo y usa conjuntos disjuntos con compresión de caminos: O(E log E).")
	outcome = runEngine(*mstRequest(scenario))
	result = resultOrError(outcome)
	if result:
		totalCost = sum(edge["cost"] for edge in scenario["edges"])
		columns = st.columns(3)
		columns[0].metric("Costo total del árbol", f"{result['total_cost']:,.0f}")
		columns[1].metric("Enlaces seleccionados", f"{len(result['edge_indices'])} de {len(scenario['edges'])}")
		columns[2].metric("Ahorro frente a instalar todo", f"{1 - result['total_cost'] / totalCost:.1%}" if totalCost else "—")
		showEngineMetrics(outcome, st.columns(3))
		if not result["connected"]:
			st.warning(f"La red está desconectada: se obtuvo un bosque mínimo con {result['components']} componentes")
		st.plotly_chart(charts.networkMap(scenario, {"mst": result}, height=430), width="stretch",
		                config={"displaylogo": False})
		st.dataframe([{"orden": order + 1, "enlace": edgeLabel(scenario, index), "costo": scenario["edges"][index]["cost"],
		               "distancia (km)": round(scenario["edges"][index]["distance"], 1)}
		              for order, index in enumerate(result["edge_indices"])], hide_index=True, width="stretch")


# Pestana del recorrido de mantenimiento con comparacion exacto contra heuristico
# Parametro scenario: escenario activo
# Retorno: sin valor; dibuja la pestana
def tspTab(scenario: dict) -> None:
	st.markdown("Un equipo visita cada central seleccionada una vez y regresa al origen. Con pocas centrales se usa "
	            "**Held–Karp** (exacto, O(2ᵏk²)); con más, **vecino más cercano + 2-opt** (heurístico). El tránsito "
	            "físico sigue caminos mínimos por enlaces existentes y puede repetir nodos intermedios.")
	nodeCount = len(scenario["nodes"])
	defaults = [index for index in scenario["tspSelected"] if index < nodeCount][:12] or [0]
	selected = st.multiselect("Centrales a visitar (la primera es el origen)", range(nodeCount), default=defaults,
	                          format_func=lambda index: nodeLabel(scenario, index), key=f"tsp_{scenario['name']}_{nodeCount}_{len(scenario['edges'])}")
	columns = st.columns(2)
	exactLimit = columns[0].slider("Máximo de centrales para solución exacta", 1, 18, 16)
	maxPasses = columns[1].slider("Máximo de pasadas 2-opt", 0, 1000, 100, step=10)
	if not selected:
		st.info("Selecciona al menos una central")
		return
	outcome = runEngine(*tspRequest(scenario, selected, exactLimit, maxPasses))
	result = resultOrError(outcome)
	if result:
		columns = st.columns(3)
		columns[0].metric("Distancia total", f"{result['total_distance']:,.1f} km")
		columns[1].metric("Método", "Exacto · Held–Karp" if result["exact"] else "Heurístico · 2-opt")
		columns[2].metric("Mejoras 2-opt aplicadas", result["improvements"])
		showEngineMetrics(outcome, st.columns(3))
		st.markdown("**Orden de visita:** " + " → ".join(scenario["nodes"][index]["label"] for index in result["tour"]))
		st.plotly_chart(charts.networkMap(scenario, {"tsp": result}, height=430), width="stretch",
		                config={"displaylogo": False})

	if len(selected) <= 18:
		st.markdown("**Exacto contra heurístico** sobre las mismas centrales")
		rows = []
		for label, limit, passes in (("Held–Karp (exacto)", 18, 0), ("Vecino más cercano", 1, 0),
		                             ("Vecino más cercano + 2-opt", 1, 1000)):
			comparison = runEngine(*tspRequest(scenario, selected, limit, passes))
			if comparison["ok"]:
				answer = comparison["response"]["result"]
				rows.append({"método": label, "distancia (km)": round(answer["total_distance"], 1),
				             "tiempo C++ (ms)": round(comparison["response"]["metrics"]["algorithm_us"] / 1000, 3)})
		if len(rows) == 3:
			optimum = rows[0]["distancia (km)"]
			for row in rows:
				row["brecha vs óptimo"] = f"{row['distancia (km)'] / optimum - 1:.2%}" if optimum else "0.00%"
			st.dataframe(rows, hide_index=True, width="stretch")
	else:
		st.caption("Con más de 18 centrales solo se ejecuta la heurística: Held–Karp crece como 2ᵏ")


# Busca la demanda registrada entre dos centrales cuando existe en los datos GEANT
# Parametros scenario, source y sink: escenario y extremos
# Retorno: demanda en Mbit/s o None
def recordedDemand(scenario: dict, source: int, sink: int) -> float | None:
	identifiers = {node["id"]: index for index, node in enumerate(scenario["nodes"])}
	if "at1.at" not in identifiers:
		return None
	sourceId, sinkId = scenario["nodes"][source]["id"], scenario["nodes"][sink]["id"]
	return sum(float(row["demand_mbps"]) for row in readTable("demands.csv")
	           if row["id"] == f"{sourceId}_{sinkId}") or None


# Pestana de flujo maximo con corte minimo y utilizacion
# Parametro scenario: escenario activo
# Retorno: sin valor; dibuja la pestana
def flowTab(scenario: dict) -> None:
	st.markdown("Máxima información transportable entre dos centrales respetando capacidades y conservación. "
	            "**Dinic** construye niveles con BFS y envía flujo bloqueante por DFS: O(V²E). El corte mínimo "
	            "certifica el resultado: su capacidad es igual al flujo.")
	nodeCount = len(scenario["nodes"])
	columns = st.columns([2, 2, 1])
	source = columns[0].selectbox("Origen", range(nodeCount), index=min(scenario["source"], nodeCount - 1),
	                              format_func=lambda index: nodeLabel(scenario, index), key="labSource")
	sink = columns[1].selectbox("Destino", range(nodeCount), index=min(scenario["sink"], nodeCount - 1),
	                            format_func=lambda index: nodeLabel(scenario, index), key="labSink")
	directed = columns[2].toggle("Dirigido", help="En no dirigido, cada enlace comparte su capacidad en ambos sentidos")
	if source == sink:
		st.error("El origen y el destino deben ser distintos")
		return
	outcome = runEngine(*flowRequest(scenario, source, sink, directed))
	result = resultOrError(outcome)
	if not result:
		return
	sourceSide = set(result["source_side"])
	cut = [index for index, edge in enumerate(scenario["edges"])
	       if (edge["u"] in sourceSide and edge["v"] not in sourceSide) or
	       (not directed and edge["v"] in sourceSide and edge["u"] not in sourceSide)]
	columns = st.columns(3)
	columns[0].metric("Flujo máximo", f"{result['value']:,.0f} Mbit/s")
	columns[1].metric("Enlaces del corte mínimo", len(cut))
	demand = recordedDemand(scenario, source, sink)
	columns[2].metric("Demanda registrada (contexto)", f"{demand:,.0f} Mbit/s" if demand else "—",
	                  help="Demanda pico del XML entre este par. Es contexto: no es una entrada del flujo máximo")
	showEngineMetrics(outcome, st.columns(3))
	st.plotly_chart(charts.networkMap(scenario, {"flow": {"result": result, "source": source, "sink": sink}}, height=430),
	                width="stretch", config={"displaylogo": False})
	rows = []
	for entry in result["flows"]:
		edge = scenario["edges"][entry["edge_index"]]
		if abs(entry["flow"]) > 1e-9:
			rows.append({"enlace": edgeLabel(scenario, entry["edge_index"]), "flujo (Mbit/s)": round(entry["flow"], 1),
			             "capacidad (Mbit/s)": edge["capacity"],
			             "uso": round(abs(entry["flow"]) / edge["capacity"], 4) if edge["capacity"] else 1.0,
			             "en corte mínimo": "sí" if entry["edge_index"] in cut else ""})
	st.dataframe(rows, hide_index=True, width="stretch",
	             column_config={"uso": st.column_config.ProgressColumn("uso", min_value=0, max_value=1, format="percent")})
	st.caption("Flujo con signo: positivo en el sentido u → v del enlace y negativo en sentido contrario")


# Pestana de regiones de proximidad con consultas editables
# Parametro scenario: escenario activo
# Retorno: sin valor; dibuja la pestana
def voronoiTab(scenario: dict) -> None:
	st.markdown("Cada nueva contratación se asigna a su central más cercana. Las regiones se obtienen recortando el "
	            "dominio con las mediatrices de cada par de centrales: O(n²·m). Se calculan en el plano "
	            "equirectangular del escenario, por lo que hay distorsión lejos de la latitud de referencia.")
	queries = st.data_editor(DEFAULT_QUERIES, num_rows="dynamic", width="stretch", key="voronoiQueries",
	                         column_config={"longitud": st.column_config.NumberColumn(min_value=-180, max_value=180),
	                                        "latitud": st.column_config.NumberColumn(min_value=-90, max_value=90)})
	points = [(float(row["longitud"]), float(row["latitud"])) for row in queries
	          if row.get("longitud") is not None and row.get("latitud") is not None]
	outcome = runEngine(*voronoiRequest(scenario, points))
	result = resultOrError(outcome)
	if not result:
		return
	showEngineMetrics(outcome, st.columns(3))
	labels = [row.get("lugar") or f"Consulta {index + 1}" for index, row in enumerate(queries)
	          if row.get("longitud") is not None and row.get("latitud") is not None]
	layers = {"voronoi": result, "queries": points,
	          "queryLabels": [f"{label} → {scenario['nodes'][nearest]['label']}" for label, nearest in zip(labels, result["nearest"])]}
	st.plotly_chart(charts.networkMap(scenario, layers, height=470), width="stretch", config={"displaylogo": False})
	columns = st.columns(2)
	columns[0].markdown("**Asignación de consultas**")
	columns[0].dataframe([{"lugar": label, "central": scenario["nodes"][nearest]["label"],
	                       "distancia (km)": round(haversineKm({"lon": point[0], "lat": point[1]}, scenario["nodes"][nearest]), 1)}
	                      for label, point, nearest in zip(labels, points, result["nearest"])], hide_index=True, width="stretch")
	columns[1].markdown("**Área por región**")
	areas = sorted(((polygonArea(cell), index) for index, cell in enumerate(result["cells"])), reverse=True)
	columns[1].dataframe([{"central": scenario["nodes"][index]["label"], "área (km²)": round(area)} for area, index in areas],
	                     hide_index=True, width="stretch")


# Calcula el indicador principal de un algoritmo para un escenario
# Parametros scenario y mode: escenario y algoritmo a comparar
# Retorno: fila con valor, tiempos y estado
def comparisonRow(scenario: dict, mode: str) -> dict:
	nodeCount = len(scenario["nodes"])
	if mode == "mst":
		request = mstRequest(scenario)
	elif mode == "tsp":
		request = tspRequest(scenario, [index for index in scenario["tspSelected"] if index < nodeCount] or [0])
	elif mode == "max_flow":
		request = flowRequest(scenario, min(scenario["source"], nodeCount - 1), min(scenario["sink"], nodeCount - 1))
	else:
		request = voronoiRequest(scenario)
	outcome = runEngine(*request)
	row = {"escenario": scenario["name"], "centrales": nodeCount, "enlaces": len(scenario["edges"])}
	if not outcome["ok"]:
		row.update({"valor": None, "estado": outcome["error"]})
		return row
	result = outcome["response"]["result"]
	value = (result["total_cost"] if mode == "mst" else result["total_distance"] if mode == "tsp"
	         else result["value"] if mode == "max_flow" else max(polygonArea(cell) for cell in result["cells"]))
	status = "ok"
	if mode == "mst" and not result["connected"]:
		status = f"bosque de {result['components']} componentes"
	elif mode == "tsp":
		status = "exacto" if result["exact"] else "heurístico"
	row.update({"valor": round(value, 2), "estado": status,
	            "tiempo C++ (ms)": round(outcome["response"]["metrics"]["algorithm_us"] / 1000, 3),
	            "memoria (MiB)": round((outcome["response"]["metrics"].get("peak_process_bytes") or 0) / 1048576, 1)})
	return row


# Pestana que ejecuta un mismo algoritmo sobre varios escenarios
# Parametros: ninguno
# Retorno: sin valor; dibuja la pestana
def compareTab() -> None:
	scenarios = st.session_state.scenarios
	st.markdown("Ejecuta un mismo algoritmo sobre varios escenarios del **Scenario Manager** para medir el efecto "
	            "de fallas, cambios de capacidad o topologías distintas.")
	columns = st.columns([1, 2])
	metric = columns[0].selectbox("Indicador", list(COMPARISONS))
	chosen = columns[1].multiselect("Escenarios", list(scenarios), default=list(scenarios))
	if not chosen:
		return
	rows = [comparisonRow(scenarios[name], COMPARISONS[metric]) for name in chosen]
	st.dataframe(rows, hide_index=True, width="stretch")
	valid = [row for row in rows if row["valor"] is not None]
	if valid:
		columns = st.columns(2)
		columns[0].plotly_chart(charts.comparisonChart([row["escenario"] for row in valid], [row["valor"] for row in valid],
		                                               metric), width="stretch", config={"displaylogo": False})
		columns[1].plotly_chart(charts.comparisonChart([row["escenario"] for row in valid],
		                                               [row["tiempo C++ (ms)"] for row in valid],
		                                               "Tiempo del algoritmo C++ (ms)", charts.TOUR_COLOR),
		                        width="stretch", config={"displaylogo": False})
	if len(scenarios) == 1:
		st.info("Solo hay un escenario. Crea fallas de enlaces o redes sintéticas en el Scenario Manager para compararlas")


# Ejecuta una serie corta de tamanos crecientes en vivo
# Parametros mode y generator: algoritmo y generador
# Retorno: filas con tamano y tiempo del algoritmo
def liveBenchmark(mode: str, generator: random.Random) -> list[dict]:
	rows = []
	for size in (25000, 50000, 100000, 200000) if mode in ("mst", "max_flow") else (125000, 250000, 500000, 1000000):
		if mode in ("mst", "max_flow"):
			edges = [{"u": node - 1, "v": node} for node in range(1, 2000)]
			edges += [{"u": generator.randrange(2000), "v": generator.randrange(2000)} for _ in range(size - len(edges))]
			edges = [edge for edge in edges if edge["u"] != edge["v"]]
			field = "cost" if mode == "mst" else "capacity"
			inputData = {"n": 2000, "edges": [dict(edge, **{field: generator.randint(1, 1000)}) for edge in edges]}
			if mode == "max_flow":
				inputData.update({"source": 0, "sink": 1999, "directed": True})
		else:
			texts = ["".join(generator.choices("0123456789ABCDEF", k=size)) for _ in range(2)]
			inputData = {"transmissions": texts, "patterns": ["DEADBEEF", texts[0][size // 2:size // 2 + 40], "F" * 32]}
		outcome = runEngine(mode, inputData)
		if outcome["ok"]:
			rows.append({"tamaño": size, "tiempo C++ (ms)": round(outcome["response"]["metrics"]["algorithm_us"] / 1000, 3),
			             "llamada completa (ms)": round(outcome["wallSeconds"] * 1000, 1)})
	return rows


# Pestana con la evidencia de escalabilidad y una medicion en vivo
# Parametros: ninguno
# Retorno: sin valor; dibuja la pestana
def scalingTab() -> None:
	reportPath = Path(ROOT) / "results/stress_tests.json"
	if reportPath.is_file():
		report = json.loads(reportPath.read_text(encoding="utf-8"))
		if report.get("scaling"):
			st.markdown(f"Resultados de `tests/stress_algorithms.py`: {report['cases']} ejecuciones aprobadas hasta "
			            "los límites del contrato. Cada punto es la mediana de 3 repeticiones del tiempo interno del algoritmo; "
			            "la pendiente log-log se compara con la complejidad teórica.")
			st.plotly_chart(charts.scalingChart(report["scaling"]), width="stretch", config={"displaylogo": False})
			st.dataframe([{"algoritmo": fit["algorithm"], "complejidad teórica": fit["theory"], "pendiente medida": fit["logLogSlope"],
			               "pendiente esperada": f"{fit['expectedSlope']:g}" if fit["expectedSlope"] is not None else "—"} for fit in report["scaling"]], hide_index=True, width="stretch")
			limit = [record for record in report["records"] if record["group"] == "escala:limite"]
			if limit:
				st.markdown("**Escala límite del contrato**")
				st.dataframe([{"caso": record["case"], "reloj (s)": record["wallSeconds"], "algoritmo (s)": record["algorithmSeconds"],
				               "pico (MiB)": round((record["peakProcessBytes"] or 0) / 1048576, 1),
				               "JSON (MiB)": round(record["payloadBytes"] / 1048576, 2)} for record in limit],
				             hide_index=True, width="stretch")
	st.markdown("**Medición en vivo**")
	columns = st.columns([2, 1])
	mode = columns[0].selectbox("Algoritmo", ["mst", "max_flow", "matching", "palindrome", "common_substring"],
	                            format_func=lambda value: {"mst": "MST · Kruskal", "max_flow": "Flujo · Dinic",
	                                                       "matching": "Firmas · KMP", "palindrome": "Palíndromo · Manacher",
	                                                       "common_substring": "Subcadena común · autómata"}[value])
	if columns[1].button("Medir 4 tamaños", type="primary", width="stretch"):
		with st.spinner("Generando entradas y ejecutando el motor C++"):
			st.session_state.liveBenchmark = (mode, liveBenchmark(mode, random.Random(2038)))
	if st.session_state.get("liveBenchmark"):
		measuredMode, rows = st.session_state.liveBenchmark
		st.caption(f"Última medición: {measuredMode}")
		st.dataframe(rows, hide_index=True, width="stretch")


# Dibuja el laboratorio con una pestana por algoritmo
# Parametros: ninguno
# Retorno: sin valor; dibuja la pagina
def render() -> None:
	scenario = activeScenario()
	sectionHeader("MÓDULO 02 · ALGORITHM LABORATORY", "Siete algoritmos. Un único caso.",
	              f"Escenario activo: {scenario['name']}. Todos los resultados se calculan en C++ al cambiar un parámetro.")
	tabs = st.tabs(["MST", "TSP", "Flujo máximo", "Voronoi", "Comparar escenarios", "Escalabilidad"])
	with tabs[0]:
		mstTab(scenario)
	with tabs[1]:
		tspTab(scenario)
	with tabs[2]:
		flowTab(scenario)
	with tabs[3]:
		voronoiTab(scenario)
	with tabs[4]:
		compareTab()
	with tabs[5]:
		scalingTab()
