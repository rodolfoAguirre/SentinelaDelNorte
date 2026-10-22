# Descripcion: explora la red sobre el mapa con capas de algoritmos
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import streamlit as st

from .. import charts
from ..scenarios import flowRequest, haversineKm, mstRequest, polygonArea, tspRequest, voronoiRequest
from ..state import activeScenario, edgeLabel, nodeLabel, resultOf, runEngine, sectionHeader


# Dibuja el explorador con capas, inspector de nodos y consultas de cercania
# Parametros: ninguno
# Retorno: sin valor; dibuja la pagina
def render() -> None:
	scenario = activeScenario()
	nodeCount = len(scenario["nodes"])
	sectionHeader("MÓDULO 01 · NETWORK EXPLORER", "La red, sobre el mapa.",
	              "Activa capas calculadas por el motor C++ y pasa el cursor sobre centrales y enlaces para ver sus datos.")

	mapColumn, controlColumn = st.columns([3.3, 1.2], gap="medium")
	with controlColumn:
		st.markdown("**Capas**")
		showMst = st.toggle("Árbol de expansión mínima", value=True)
		showTour = st.toggle("Ruta de mantenimiento (TSP)")
		showFlow = st.toggle("Flujo máximo y corte mínimo")
		showRegions = st.toggle("Regiones de Voronoi")
		source = sink = None
		if showFlow:
			source = st.selectbox("Origen", range(nodeCount), index=min(scenario["source"], nodeCount - 1),
			                      format_func=lambda index: nodeLabel(scenario, index))
			sink = st.selectbox("Destino", range(nodeCount), index=min(scenario["sink"], nodeCount - 1),
			                    format_func=lambda index: nodeLabel(scenario, index))
		st.divider()
		with st.expander("Consultar una ubicación", expanded=False):
			st.caption("Asigna un punto a la central más cercana (Voronoi)")
			longitude = st.number_input("Longitud", -180.0, 180.0, 11.58, step=0.5)
			latitude = st.number_input("Latitud", -90.0, 90.0, 48.14, step=0.5)
			if st.button("Asignar a central", width="stretch"):
				st.session_state.explorerQueries = st.session_state.get("explorerQueries", []) + [(longitude, latitude)]
			if st.session_state.get("explorerQueries") and st.button("Limpiar consultas", width="stretch"):
				st.session_state.explorerQueries = []

	layers = {}
	problems = []
	if showMst:
		layers["mst"] = resultOf(mstRequest(scenario))
	if showTour:
		selected = [index for index in scenario["tspSelected"] if index < nodeCount] or [0]
		outcome = runEngine(*tspRequest(scenario, selected))
		if outcome["ok"]:
			layers["tsp"] = outcome["response"]["result"]
		else:
			problems.append(f"TSP: {outcome['error']}")
	if showFlow and source == sink:
		problems.append("Flujo máximo: el origen y el destino deben ser distintos")
	elif showFlow:
		outcome = runEngine(*flowRequest(scenario, source, sink))
		if outcome["ok"]:
			layers["flow"] = {"result": outcome["response"]["result"], "source": source, "sink": sink}
		else:
			problems.append(f"Flujo máximo: {outcome['error']}")
	queries = st.session_state.get("explorerQueries", [])
	voronoi = None
	if showRegions or queries:
		voronoi = resultOf(voronoiRequest(scenario, queries))
		if voronoi and showRegions:
			layers["voronoi"] = voronoi
	if voronoi and queries:
		layers["queries"] = queries
		layers["queryLabels"] = [f"Consulta {index + 1} → {scenario['nodes'][nearest]['label']}"
		                         for index, nearest in enumerate(voronoi["nearest"])]
	layers = {key: value for key, value in layers.items() if value is not None}

	with mapColumn:
		for problem in problems:
			st.warning(problem)
		st.plotly_chart(charts.networkMap(scenario, layers), width="stretch",
		                config={"displaylogo": False, "scrollZoom": True})
		st.caption("Arrastra para desplazar y usa la rueda para acercar. Las centrales alejadas del núcleo, como "
		           "Nueva York en GÉANT, quedan fuera del encuadre inicial pero sus enlaces se dibujan.")

	columns = st.columns(4)
	if "mst" in layers:
		columns[0].metric("Costo del MST", f"{layers['mst']['total_cost']:,.0f}",
		                  help=f"{len(layers['mst']['edge_indices'])} enlaces · {layers['mst']['components']} componente(s)")
	if "tsp" in layers:
		columns[1].metric("Distancia TSP", f"{layers['tsp']['total_distance']:,.0f} km",
		                  help="Exacto (Held–Karp)" if layers["tsp"]["exact"] else "Heurístico (vecino más cercano + 2-opt)")
	if "flow" in layers:
		columns[2].metric("Flujo máximo", f"{layers['flow']['result']['value']:,.0f} Mbit/s")
	if voronoi:
		columns[3].metric("Regiones de servicio", sum(1 for cell in voronoi["cells"] if cell))

	if voronoi and queries:
		st.dataframe([{"consulta": index + 1, "longitud": query[0], "latitud": query[1],
		               "central asignada": nodeLabel(scenario, nearest),
		               "distancia (km)": round(haversineKm({"lon": query[0], "lat": query[1]}, scenario["nodes"][nearest]), 1)}
		              for index, (query, nearest) in enumerate(zip(queries, voronoi["nearest"]))],
		             hide_index=True, width="stretch")

	st.markdown("**Inspector de centrales**")
	inspected = st.selectbox("Central", range(nodeCount), format_func=lambda index: nodeLabel(scenario, index),
	                         label_visibility="collapsed")
	node = scenario["nodes"][inspected]
	incident = [index for index, edge in enumerate(scenario["edges"]) if inspected in (edge["u"], edge["v"])]
	columns = st.columns(4)
	columns[0].metric("Grado", len(incident))
	columns[1].metric("Coordenadas", f"{node['lat']:.2f}°, {node['lon']:.2f}°")
	columns[2].metric("Capacidad conectada", f"{sum(scenario['edges'][index]['capacity'] for index in incident):,.0f} Mbit/s")
	if voronoi:
		columns[3].metric("Área de su región", f"{polygonArea(voronoi['cells'][inspected]):,.0f} km²",
		                  help="Área en el plano equirectangular del escenario")
	mstEdges = set(layers["mst"]["edge_indices"]) if "mst" in layers else set()
	st.dataframe([{
		"enlace": edgeLabel(scenario, index), "id": scenario["edges"][index]["id"],
		"costo": scenario["edges"][index]["cost"], "distancia (km)": round(scenario["edges"][index]["distance"], 1),
		"capacidad (Mbit/s)": scenario["edges"][index]["capacity"],
		"en MST": "sí" if index in mstEdges else "no" if mstEdges else "—",
	} for index in incident], hide_index=True, width="stretch")
	if not incident:
		st.info("Esta central no tiene enlaces en el escenario activo")
