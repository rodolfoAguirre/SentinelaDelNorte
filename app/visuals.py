# Descripcion: construye el mapa geografico y la identidad visual
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import colorsys
import math
import time

import pydeck as pdk
import streamlit as st
from app.presentation import centralName


ACCENT = [54, 226, 172, 235]
MUTED = [113, 139, 170, 130]


# Aplica estilos comunes a formularios, metricas y resultados
# Parametros: ninguno
# Retorno: sin valor; inserta estilos en la pagina
def applyTheme():
	st.markdown("""<style>
	.stApp {background: #0b1220; color: #e7edf7}
	[data-testid="stSidebar"] {background: #101c2e; border-right: 1px solid #24334b}
	.block-container {padding-top: 4.3rem; max-width: 1500px}
	h1 {letter-spacing: -.05em; font-weight: 750 !important}
	[data-testid="stMetric"] {background: #132237; padding: 18px 20px;
	 border: 1px solid #2a3a52; border-radius: 14px; min-height: 112px}
	[data-testid="stMetricValue"] {color: #5be5bd; font-variant-numeric: tabular-nums}
	[data-testid="stForm"] {border: 1px solid #283952; background: #101c2e; border-radius: 16px}
	.eyebrow {color: #59dfb7; font-size: .74rem; letter-spacing: .18em; font-weight: 700}
	.hex-preview {background: #132237; padding: 18px; border-radius: 12px;
	 font-family: monospace; line-height: 2; overflow-wrap: anywhere; color: #c1cfe3}
	.hex-preview mark {background: #165f51; color: #b1ffe4; padding: 3px 0}
	</style>""", unsafe_allow_html=True)


# Convierte coordenadas del escenario al mapa geografico
# Parametros point y projection: coordenadas planas y proyeccion original
# Retorno: longitud y latitud en grados
def geographicPoint(point, projection):
	radius = projection["radius_km"]
	return [projection["lon0"] + math.degrees(point[0] / (radius * math.cos(math.radians(projection["lat0"])))),
	        projection["lat0"] + math.degrees(point[1] / radius)]


# Construye capas con nodos, enlaces, rutas o regiones del resultado
# Parametros nodes, request, result, projection y options: datos y controles del mapa
# Retorno: mapa Pydeck con informacion al pasar el cursor
def buildMap(nodes, request, result, projection, options):
	mode, inputData = request["mode"], request["input"]
	positions = [[float(node["longitude_deg"]), float(node["latitude_deg"])] for node in nodes]
	layers = []
	chosen = set(result.get("edge_indices", result.get("physical_edge_indices", [])))
	flowValues = {entry["edge_index"]: entry["flow"] for entry in result.get("flows", [])}
	step = options.get("step")
	if result and step is not None:
		if mode == "tsp":
			chosen = set(result["physical_edge_indices"][:step])
		elif mode == "mst":
			chosen = set(result["edge_indices"][:step])
		elif mode == "max_flow":
			flowValues = dict(list((index, value) for index, value in flowValues.items() if abs(value) > 1e-9)[:step])
	if mode == "voronoi" and result:
		polygons = []
		for index, polygon in enumerate(result["cells"]):
			if polygon and (step is None or index < step):
				vertices = []
				for first, second in zip(polygon, polygon[1:] + polygon[:1]):
					for fraction in (0, .25, .5, .75):
						point = [first[axis] + fraction * (second[axis] - first[axis]) for axis in (0, 1)]
						vertices.append(geographicPoint(point, projection))
				color = [int(channel * 255) for channel in colorsys.hsv_to_rgb((index * .618) % 1, .6, .85)] + [95]
				polygons.append({"polygon": vertices, "color": color, "title": centralName(nodes[index]), "detail": "Región de proximidad del escenario proyectado"})
		layers.append(pdk.Layer("PolygonLayer", polygons, id="regions", get_polygon="polygon", get_fill_color="color", get_line_color=[177, 196, 218], line_width_min_pixels=1, pickable=True))
	edges = []
	for index, edge in enumerate(inputData.get("edges", [])):
		active = index in chosen or abs(flowValues.get(index, 0)) > 1e-9
		if active or options["base"] or not result:
			firstNode, secondNode = edge["u"], edge["v"]
			if mode == "max_flow":
				flow = flowValues.get(index, 0)
				if flow < 0:
					firstNode, secondNode = secondNode, firstNode
				detail = f"Transporta {abs(flow):,.0f} Mbit/s · capacidad {edge['capacity']:,.0f} Mbit/s"
				width = 2 + 6 * abs(flow) / max(edge["capacity"], 1) if active else 1
			else:
				detail = f"Distancia: {edge['distance']:,.2f} km" if mode == "tsp" else f"Costo: {edge['cost']:,.2f}"
				width = 4 if active else 1
			edges.append({"source": positions[firstNode], "target": positions[secondNode], "color": ACCENT if active else MUTED, "width": width,
			              "title": f"{centralName(nodes[firstNode])} → {centralName(nodes[secondNode])}", "detail": detail})
	if edges:
		layers.append(pdk.Layer("LineLayer", edges, id="links", get_source_position="source", get_target_position="target", get_color="color", get_width="width", width_min_pixels=1, pickable=True, auto_highlight=True))
	points = []
	for index, node in enumerate(nodes):
		role = "Central de la red"
		color = ACCENT
		if mode == "max_flow":
			if index == inputData["source"]:
				role, color = "Origen del flujo", [255, 197, 89]
			elif index == inputData["sink"]:
				role, color = "Destino del flujo", [249, 111, 139]
		if mode == "tsp" and index in inputData["selected"]:
			role = "Central seleccionada para mantenimiento"
		if mode == "tsp" and result and step is not None and result["physical_nodes"][step] == index:
			role, color = "Posición actual del recorrido", [255, 197, 89]
		points.append({"position": positions[index], "color": color, "title": centralName(node), "detail": role, "node_index": index, "label": node["id"],
		               "latitude": float(node["latitude_deg"]), "longitude": float(node["longitude_deg"])})
	layers.append(pdk.Layer("ScatterplotLayer", points, id="nodes", get_position="position", get_fill_color="color", get_radius=6000, radius_min_pixels=5, radius_max_pixels=10, pickable=True, auto_highlight=True))
	if options["labels"]:
		layers.append(pdk.Layer("TextLayer", points, id="labels", get_position="position", get_text="label", get_color=[235, 244, 255], get_size=12, get_pixel_offset=[0, -15]))
	view = pdk.ViewState(longitude=12, latitude=51, zoom=3.2)
	if options["region"] == "Toda la red":
		view = pdk.ViewState(longitude=-24, latitude=45, zoom=2)
	elif options["region"] == "Norteamérica":
		view = pdk.ViewState(longitude=-74, latitude=41, zoom=4)
	return pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto", map_style=pdk.map_styles.DARK,
	                tooltip={"text": "{title}\n{detail}"})


# Presenta controles de exploracion y detalle de la central elegida
# Parametros nodes, request, result y projection: escenario y respuesta calculada
# Retorno: sin valor; dibuja un mapa interactivo
def showMap(nodes, request, result, projection):
	mode = request["mode"]
	controls = st.columns([2, 1, 1])
	region = controls[0].selectbox("Encuadre", ["Europa", "Toda la red", "Norteamérica"], key=f"region_{mode}")
	base = controls[1].checkbox("Red completa", value=True, key=f"base_{mode}")
	labels = controls[2].checkbox("Etiquetas", value=True, key=f"labels_{mode}")
	sequence = animationSequence(request, result, nodes)
	state = st.session_state.setdefault(f"animation_{mode}", {"position": len(sequence), "playing": False, "next_tick": 0})
	if result:
		st.caption("La animación presenta el resultado ya calculado; su duración no forma parte del tiempo del algoritmo")
		if mode == "max_flow":
			st.caption("Los enlaces con flujo se revelan en el orden de la tabla; no representa los aumentos internos de Dinic")
		elif mode == "voronoi":
			st.caption("Las regiones se presentan en el orden de las centrales")
	# Actualiza solo el mapa y sus controles durante la reproduccion
	# Parametros: ninguno; usa el resultado capturado
	# Retorno: sin valor; renderiza un fotograma
	@st.fragment(run_every=.7 if state["playing"] and sequence else None)
	def renderFrame():
		if state["playing"] and time.monotonic() >= state["next_tick"]:
			state["position"] = min(state["position"] + 1, len(sequence))
			state["next_tick"] = time.monotonic() + .7
			if state["position"] == len(sequence):
				state["playing"] = False
				st.rerun()
		if sequence:
			buttons = st.columns(5)
			if buttons[0].button("Pausar" if state["playing"] else "Reproducir", key=f"play_{mode}"):
				state["playing"] = not state["playing"]
				if state["position"] == len(sequence):
					state["position"] = 0
				state["next_tick"] = time.monotonic() + .7
				st.rerun()
			if buttons[1].button("Reiniciar", key=f"restart_{mode}"):
				state.update(position=0, playing=True, next_tick=time.monotonic() + .7)
				st.rerun()
			for column, title, position in ((2, "Anterior", max(0, state["position"] - 1)), (3, "Siguiente", min(len(sequence), state["position"] + 1)), (4, "Ver todo", len(sequence))):
				if buttons[column].button(title, key=f"{column}_{mode}"):
					state.update(position=position, playing=False)
					st.rerun()
			st.progress(state["position"] / len(sequence), text=f"Paso {state['position']} de {len(sequence)}")
			st.write(sequence[state["position"] - 1] if state["position"] else "Listo para mostrar la primera conexión o región")
		deck = buildMap(nodes, request, result, projection, {"region": region, "base": base, "labels": labels, "step": state["position"] if result else None})
		event = st.pydeck_chart(deck, height=530, key=f"map_{mode}_{region}", on_select="rerun", selection_mode="single-object")
		selected = event.selection.get("objects", {}).get("nodes", [])
		if selected:
			point = selected[0]
			st.info(f"{point['title']} · {point['latitude']:.4f}° latitud · {point['longitude']:.4f}° longitud · {point['detail']}")
	renderFrame()
	st.caption("Arrastra para desplazarte, usa la rueda para acercarte y selecciona una central para consultar sus coordenadas. Verde: enlaces del resultado. El fondo cartográfico requiere internet")
	if mode == "voronoi":
		st.caption("Las celdas se calcularon en el plano del escenario y se transformaron a coordenadas geográficas para mostrarlas; conservan la aproximación de esa proyección")


# Describe el orden de presentacion de cada resultado de red
# Parametros request, result y nodes: entrada, respuesta y centrales
# Retorno: descripciones de los pasos en orden
def animationSequence(request, result, nodes):
	mode, data = request["mode"], request["input"]
	if mode == "mst":
		return [f"Conexión {step}: {centralName(nodes[data['edges'][index]['u']])} ↔ {centralName(nodes[data['edges'][index]['v']])} · costo {data['edges'][index]['cost']:,.2f}" for step, index in enumerate(result.get("edge_indices", []), 1)]
	if mode == "tsp":
		return [f"Tramo {step}: {centralName(nodes[result['physical_nodes'][step - 1]])} → {centralName(nodes[result['physical_nodes'][step]])} · {data['edges'][index]['distance']:,.2f} km" for step, index in enumerate(result.get("physical_edge_indices", []), 1)]
	if mode == "max_flow":
		steps = []
		for entry in result.get("flows", []):
			if abs(entry["flow"]) > 1e-9:
				edge = data["edges"][entry["edge_index"]]
				first, second = (edge["u"], edge["v"]) if entry["flow"] > 0 else (edge["v"], edge["u"])
				steps.append(f"{centralName(nodes[first])} → {centralName(nodes[second])} · transporta {abs(entry['flow']):,.2f} Mbit/s")
		return steps
	return [f"Región {index + 1}: puntos más cercanos a {centralName(nodes[index])} en el plano del escenario" for index in range(len(result.get("cells", [])))]
