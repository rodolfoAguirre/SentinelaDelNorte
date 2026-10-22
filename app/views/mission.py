# Descripcion: presenta la mision, la arquitectura y el escenario activo
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import streamlit as st

from .. import charts
from ..scenarios import mstRequest
from ..state import activeScenario, getAdapter, resultOf


LAYERS = [
	("L0", "Infraestructura y tráfico", "SNDlib GÉANT, transmisiones hexadecimales y mapping.csv como construcción de simulación"),
	("L1", "Network Intelligence", "MST con Kruskal, TSP con Held–Karp o 2-opt, flujo máximo con Dinic y Voronoi por semiplanos"),
	("L2", "Cybersecurity Intelligence", "Firmas con KMP, palíndromos con Manacher y subcadena común con autómata de sufijos"),
	("L3", "SENTINEL Digital Twin", "Esta aplicación: cada resultado se calcula en vivo con el motor C++17"),
]
MODULES = [
	("01", "Network Explorer", "Nodos, enlaces, rutas, capacidades y regiones sobre el mapa, con capas interactivas"),
	("02", "Algorithm Laboratory", "Ejecuta cada algoritmo con sus parámetros y compara resultados entre escenarios"),
	("03", "Cybersecurity Console", "Analiza dos transmisiones contra tres firmas con salida en formato oficial"),
	("04", "Scenario Manager", "Crea fallas de enlaces, redes sintéticas o importa escenarios y actualiza todo"),
]


# Dibuja la portada con metricas del escenario activo
# Parametros: ninguno
# Retorno: sin valor; dibuja la pagina
def render() -> None:
	scenario = activeScenario()
	st.markdown(
		'<div class="kicker">HACKATHON INTEGRADOR · TC2038</div>'
		'<div class="hero"><span class="hero-muted">Sentinela</span><br><span class="hero-accent">del Norte</span></div>'
		'<p class="hero-tagline">Smart Networks Under Attack <span class="mono">DESIGN. CONNECT. OPTIMIZE. DEFEND.</span></p>',
		unsafe_allow_html=True,
	)
	st.markdown(
		'<p class="section-subtitle">Una infraestructura por optimizar y transmisiones por analizar. '
		'Siete desafíos algorítmicos integrados en un único gemelo digital.</p>', unsafe_allow_html=True,
	)

	columns = st.columns(4)
	columns[0].metric("Centrales", len(scenario["nodes"]))
	columns[1].metric("Enlaces", len(scenario["edges"]))
	columns[2].metric("Capacidad total", f"{sum(edge['capacity'] for edge in scenario['edges']) / 1e6:,.2f} Tbit/s")
	columns[3].metric("Algoritmos en C++", 7)

	layers = {}
	mst = resultOf(mstRequest(scenario))
	if mst:
		layers["mst"] = mst
	st.plotly_chart(charts.networkMap(scenario, layers, height=460), width="stretch",
	                config={"displaylogo": False, "scrollZoom": True})
	st.caption(f"Escenario activo: **{scenario['name']}** · {scenario['description']}")

	st.markdown('<div class="kicker">ARQUITECTURA GENERAL</div>', unsafe_allow_html=True)
	columns = st.columns(4)
	for column, (code, title, detail) in zip(columns, LAYERS):
		column.markdown(f'<div class="card"><div class="mono muted">{code}</div><h4>{title}</h4><p>{detail}</p></div>',
		                unsafe_allow_html=True)

	st.markdown('<div class="kicker">MÓDULOS DEL GEMELO DIGITAL</div>', unsafe_allow_html=True)
	columns = st.columns(4)
	for column, (code, title, detail) in zip(columns, MODULES):
		column.markdown(f'<div class="card"><div class="mono accent">{code}</div><h4>{title}</h4><p>{detail}</p></div>',
		                unsafe_allow_html=True)

	with st.expander("Cómo se calcula cada resultado"):
		st.markdown(
			"Streamlit arma una solicitud JSON → `app/adapter.py` inicia el ejecutable C++ → el motor valida, "
			"ejecuta el algoritmo y responde JSON con tiempo y memoria → la interfaz dibuja tablas y capas. "
			"No hay resultados precalculados: cambiar un parámetro o escenario vuelve a invocar el motor.")
		st.code(str(getAdapter().executablePath), language=None)
		st.caption("GÉANT y CIC-IDS2017 provienen de entornos independientes. mapping.csv es una construcción de "
		           "simulación: detectar una cadena no confirma una infección ni un ataque real en GÉANT.")
