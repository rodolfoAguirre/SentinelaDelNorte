# Descripcion: construye mapas y graficas interactivas con Plotly
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

from __future__ import annotations

import math
from typing import Any

import plotly.graph_objects as go

from .scenarios import unprojectPoint


INK = "#E6EDF7"
MUTED = "#7F8DA6"
GRID = "#24324A"
LINK = "#3A4A66"
ACCENT = "#4C7BF4"
MST_COLOR = "#36E2AC"
TOUR_COLOR = "#FFB547"
FLOW_COLOR = "#4C9BFF"
CUT_COLOR = "#FF5C7A"
REGION_COLORS = ["#4C7BF4", "#36E2AC", "#FFB547", "#FF5C7A", "#B07CFF", "#3CC8E0", "#F27F3D", "#9BD55A"]
DENSIFY_STEP_KM = 40.0
FRAME_LON_DEG = 40.0
FRAME_LAT_DEG = 28.0
ROLE_LABELS = {"source": "Origen del flujo", "sink": "Destino del flujo", "selected": "Central del recorrido"}


# Convierte un color hexadecimal en rgba con transparencia
# Parametros color y alpha: color #RRGGBB y opacidad
# Retorno: texto rgba aceptado por Plotly
def withAlpha(color: str, alpha: float) -> str:
	red, green, blue = (int(color[index:index + 2], 16) for index in (1, 3, 5))
	return f"rgba({red},{green},{blue},{alpha})"


# Elige las coordenadas que definen el encuadre inicial sin centrales aisladas
# Parametro scenario: escenario a mostrar
# Retorno: longitudes y latitudes del nucleo de la red
def framedCoordinates(scenario: dict[str, Any]) -> tuple[list[float], list[float]]:
	longitudes = sorted(node["lon"] for node in scenario["nodes"])
	latitudes = sorted(node["lat"] for node in scenario["nodes"])
	middleLon, middleLat = longitudes[len(longitudes) // 2], latitudes[len(latitudes) // 2]
	core = [node for node in scenario["nodes"]
	        if abs(node["lon"] - middleLon) <= FRAME_LON_DEG and abs(node["lat"] - middleLat) <= FRAME_LAT_DEG]
	if len(core) < 0.8 * len(scenario["nodes"]):
		core = scenario["nodes"]
	return [node["lon"] for node in core], [node["lat"] for node in core]


# Aplica el estilo oscuro comun a una figura geografica
# Parametros figure, scenario y height: figura, escenario y alto en pixeles
# Retorno: la misma figura con layout configurado
def styleGeo(figure: go.Figure, scenario: dict[str, Any], height: int = 560) -> go.Figure:
	longitudes, latitudes = framedCoordinates(scenario)
	marginLon = max(2.0, 0.08 * (max(longitudes) - min(longitudes)))
	marginLat = max(2.0, 0.08 * (max(latitudes) - min(latitudes)))
	figure.update_geos(
		projection_type="equirectangular", showland=True, landcolor="#161F31", showocean=True,
		oceancolor="#0B1220", showcountries=True, countrycolor="#2B3852", showcoastlines=True,
		coastlinecolor="#33415C", showlakes=False, showframe=False, bgcolor="#0B1220",
		lonaxis_range=[min(longitudes) - marginLon, max(longitudes) + marginLon],
		lataxis_range=[min(latitudes) - marginLat, max(latitudes) + marginLat],
	)
	figure.update_layout(
		height=height, margin={"l": 0, "r": 0, "t": 34, "b": 0}, paper_bgcolor="#0B1220",
		font={"color": INK}, showlegend=True, hoverlabel={"bgcolor": "#121C2E", "font_color": INK},
		legend={"orientation": "h", "bgcolor": "rgba(0,0,0,0)", "x": 0, "y": 1.0, "xanchor": "left",
		        "yanchor": "bottom", "font": {"size": 12}},
	)
	return figure


# Agrupa segmentos en una sola traza separada por valores nulos
# Parametros scenario, edgeIndices: escenario y enlaces a dibujar
# Retorno: listas de longitudes y latitudes
def segmentCoordinates(scenario: dict[str, Any], edgeIndices: list[int]) -> tuple[list, list]:
	longitudes, latitudes = [], []
	for index in edgeIndices:
		edge = scenario["edges"][index]
		first, second = scenario["nodes"][edge["u"]], scenario["nodes"][edge["v"]]
		longitudes.extend([first["lon"], second["lon"], None])
		latitudes.extend([first["lat"], second["lat"], None])
	return longitudes, latitudes


# Agrega una capa de enlaces con un mismo estilo
# Parametros figure, scenario, edgeIndices, color, width y name: datos y estilo
# Retorno: sin valor; modifica la figura
def addEdgeLayer(figure: go.Figure, scenario: dict[str, Any], edgeIndices: list[int], color: str,
                 width: float, name: str, dash: str = "solid") -> None:
	if edgeIndices:
		longitudes, latitudes = segmentCoordinates(scenario, edgeIndices)
		figure.add_trace(go.Scattergeo(lon=longitudes, lat=latitudes, mode="lines", name=name,
		                               line={"color": color, "width": width, "dash": dash}, hoverinfo="skip"))


# Agrega marcadores invisibles en el punto medio de cada enlace para mostrar datos
# Parametros figure, scenario y extra: escenario y texto adicional por enlace
# Retorno: sin valor; modifica la figura
def addEdgeHover(figure: go.Figure, scenario: dict[str, Any], extra: dict[int, str] | None = None) -> None:
	longitudes, latitudes, texts = [], [], []
	for index, edge in enumerate(scenario["edges"]):
		first, second = scenario["nodes"][edge["u"]], scenario["nodes"][edge["v"]]
		longitudes.append((first["lon"] + second["lon"]) / 2)
		latitudes.append((first["lat"] + second["lat"]) / 2)
		text = (f"<b>{first['label']} – {second['label']}</b><br>Costo: {edge['cost']:,.1f}"
		        f"<br>Distancia: {edge['distance']:,.0f} km<br>Capacidad: {edge['capacity']:,.0f} Mbit/s")
		texts.append(text + (extra or {}).get(index, ""))
	figure.add_trace(go.Scattergeo(lon=longitudes, lat=latitudes, mode="markers", text=texts,
	                               hovertemplate="%{text}<extra></extra>", showlegend=False,
	                               marker={"size": 9, "color": "rgba(0,0,0,0)"}))


# Agrega los nodos con etiqueta y resaltados opcionales
# Parametros figure, scenario y highlights: escenario y nodos destacados con su rol
# Retorno: sin valor; modifica la figura
def addNodes(figure: go.Figure, scenario: dict[str, Any], highlights: dict[int, str] | None = None) -> None:
	highlights = highlights or {}
	nodes = scenario["nodes"]
	showLabels = len(nodes) <= 60
	colors = [CUT_COLOR if highlights.get(index) == "sink" else MST_COLOR if highlights.get(index) == "source"
	          else TOUR_COLOR if highlights.get(index) == "selected" else INK for index in range(len(nodes))]
	sizes = [13 if index in highlights else 8 for index in range(len(nodes))]
	texts = [f"<b>{node['label']}</b><br>{node['id']}<br>{node['lat']:.2f}°, {node['lon']:.2f}°"
	         + (f"<br><i>{ROLE_LABELS[highlights[index]]}</i>" if index in highlights else "") for index, node in enumerate(nodes)]
	figure.add_trace(go.Scattergeo(
		lon=[node["lon"] for node in nodes], lat=[node["lat"] for node in nodes],
		mode="markers+text" if showLabels else "markers", name="Centrales",
		text=[node.get("short", node["label"]) for node in nodes] if showLabels else None, textposition="top center",
		textfont={"color": INK, "size": 10}, customdata=texts, hovertemplate="%{customdata}<extra></extra>",
		marker={"size": sizes, "color": colors, "line": {"color": "#0B1220", "width": 1.5}},
	))


# Interpola un poligono planar para que sus lados se vean rectos en el mapa
# El motor entrega celdas antihorarias; d3-geo rellena el complemento de esos anillos, por eso se invierten
# Parametros polygon y projection: vertices planares y proyeccion
# Retorno: listas de longitudes y latitudes cerradas
def densifyPolygon(polygon: list[list[float]], projection: dict[str, float]) -> tuple[list[float], list[float]]:
	longitudes, latitudes = [], []
	clockwise = polygon[::-1]
	for index, start in enumerate(clockwise):
		end = clockwise[(index + 1) % len(clockwise)]
		steps = max(1, math.ceil(math.dist(start, end) / DENSIFY_STEP_KM))
		for step in range(steps):
			fraction = step / steps
			longitude, latitude = unprojectPoint(start[0] + fraction * (end[0] - start[0]),
			                                     start[1] + fraction * (end[1] - start[1]), projection)
			longitudes.append(longitude)
			latitudes.append(latitude)
	longitudes.append(longitudes[0])
	latitudes.append(latitudes[0])
	return longitudes, latitudes


# Dibuja las regiones de Voronoi como poligonos rellenos
# Parametros figure, scenario y cells: escenario y celdas del motor
# Retorno: sin valor; modifica la figura
def addRegions(figure: go.Figure, scenario: dict[str, Any], cells: list[list[list[float]]]) -> None:
	for index, cell in enumerate(cells):
		if len(cell) >= 3:
			longitudes, latitudes = densifyPolygon(cell, scenario["projection"])
			color = REGION_COLORS[index % len(REGION_COLORS)]
			figure.add_trace(go.Scattergeo(
				lon=longitudes, lat=latitudes, mode="lines", fill="toself", fillcolor=withAlpha(color, 0.18),
				line={"color": color, "width": 1}, name="Regiones Voronoi", legendgroup="voronoi",
				showlegend=index == 0, hoverinfo="text", text=f"Región de {scenario['nodes'][index]['label']}",
			))


# Construye el mapa de la red con las capas solicitadas
# Parametros scenario y layers: escenario y resultados por capa
# Retorno: figura de Plotly lista para mostrar
def networkMap(scenario: dict[str, Any], layers: dict[str, Any], height: int = 560) -> go.Figure:
	figure = go.Figure()
	highlights: dict[int, str] = {}
	hoverExtra: dict[int, str] = {}
	if "voronoi" in layers:
		addRegions(figure, scenario, layers["voronoi"]["cells"])
	addEdgeLayer(figure, scenario, list(range(len(scenario["edges"]))), LINK, 1.2, "Enlaces")
	if "mst" in layers:
		addEdgeLayer(figure, scenario, layers["mst"]["edge_indices"], MST_COLOR, 3.2,
		             f"MST · costo {layers['mst']['total_cost']:,.0f}")
	if "flow" in layers:
		flow = layers["flow"]
		capacities = [edge["capacity"] for edge in scenario["edges"]]
		buckets: dict[int, list[int]] = {}
		for entry in flow["result"]["flows"]:
			index, amount = entry["edge_index"], abs(entry["flow"])
			if amount > 1e-9:
				usage = amount / capacities[index] if capacities[index] else 1
				buckets.setdefault(min(4, int(usage * 5)), []).append(index)
				hoverExtra[index] = f"<br>Flujo: {entry['flow']:,.0f} Mbit/s ({usage:.0%} de capacidad)"
		for bucket, indices in sorted(buckets.items()):
			addEdgeLayer(figure, scenario, indices, FLOW_COLOR, 1.5 + 1.6 * bucket,
			             f"Flujo {bucket * 20}–{bucket * 20 + 20}% de capacidad")
		sourceSide = set(flow["result"]["source_side"])
		cut = [index for index, edge in enumerate(scenario["edges"]) if (edge["u"] in sourceSide) != (edge["v"] in sourceSide)]
		addEdgeLayer(figure, scenario, cut, CUT_COLOR, 2, "Corte mínimo", dash="dot")
		highlights[flow["source"]] = "source"
		highlights[flow["sink"]] = "sink"
	if "tsp" in layers:
		tour = layers["tsp"]
		addEdgeLayer(figure, scenario, tour["physical_edge_indices"], TOUR_COLOR, 2.4,
		             f"Ruta TSP · {tour['total_distance']:,.0f} km")
		for node in tour["tour"][:-1]:
			highlights.setdefault(node, "selected")
	if "highlight" in layers:
		indices, name = layers["highlight"]
		addEdgeLayer(figure, scenario, indices, CUT_COLOR, 4, name)
	addEdgeHover(figure, scenario, hoverExtra)
	addNodes(figure, scenario, highlights)
	if layers.get("queries"):
		figure.add_trace(go.Scattergeo(
			lon=[query[0] for query in layers["queries"]], lat=[query[1] for query in layers["queries"]],
			mode="markers", name="Consultas", marker={"symbol": "x", "size": 11, "color": TOUR_COLOR},
			text=layers.get("queryLabels"), hovertemplate="%{text}<extra></extra>",
		))
	return styleGeo(figure, scenario, height)


# Aplica el estilo oscuro a graficas cartesianas
# Parametros figure y height: figura y alto
# Retorno: la misma figura con estilo
def styleChart(figure: go.Figure, height: int = 360) -> go.Figure:
	figure.update_layout(
		height=height, margin={"l": 10, "r": 10, "t": 30, "b": 10}, paper_bgcolor="rgba(0,0,0,0)",
		plot_bgcolor="#0F1828", font={"color": INK}, legend={"bgcolor": "rgba(0,0,0,0)"},
	)
	figure.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
	figure.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
	return figure


# Grafica las curvas de escalabilidad en escala log-log
# Parametro fits: ajustes guardados por las pruebas de estres
# Retorno: figura con una curva por algoritmo
def scalingChart(fits: list[dict[str, Any]]) -> go.Figure:
	figure = go.Figure()
	for index, fit in enumerate(fits):
		figure.add_trace(go.Scatter(
			x=fit["sizes"], y=[value * 1000 for value in fit["medianAlgorithmSeconds"]], mode="lines+markers",
			name=f"{fit['algorithm']} · pendiente {fit['logLogSlope']:.2f}",
			line={"color": REGION_COLORS[index % len(REGION_COLORS)]},
			hovertemplate="tamaño %{x:,}<br>%{y:.2f} ms<extra>" + fit["theory"] + "</extra>",
		))
	figure.update_xaxes(type="log", title="Tamaño de entrada (aristas, centrales, sitios o caracteres)")
	figure.update_yaxes(type="log", title="Tiempo del algoritmo C++ (ms)")
	return styleChart(figure, 440)


# Grafica una comparacion de barras entre escenarios
# Parametros names, values, title y color: categorias, valores y estilo
# Retorno: figura de barras
def comparisonChart(names: list[str], values: list[float], title: str, color: str = ACCENT) -> go.Figure:
	figure = go.Figure(go.Bar(x=names, y=values, marker_color=color, text=[f"{value:,.1f}" if abs(value) >= 10 else f"{value:.3g}" for value in values],
	                          textposition="outside", cliponaxis=False))
	figure.update_layout(title={"text": title, "font": {"size": 14}})
	return styleChart(figure, 320)
