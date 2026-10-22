# Descripcion: crea, importa, exporta y activa escenarios de prueba
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import json

import streamlit as st

from ..scenarios import derivedScenario, mstRequest, scenarioToJson, syntheticScenario, validateScenario
from ..state import activeScenario, addScenario, edgeLabel, resultOf, sectionHeader


BASE_NAME = "GÉANT base"


# Resume un escenario en una fila de tabla
# Parametros name y scenario: identificador y datos
# Retorno: fila con tamano, capacidad y conectividad
def summaryRow(name: str, scenario: dict) -> dict:
	mst = resultOf(mstRequest(scenario))
	nodeCount = len(scenario["nodes"])
	return {
		"activo": "●" if name == st.session_state.activeScenario else "", "escenario": name,
		"tipo": {"geant": "Base", "synthetic": "Sintético", "derived": "Derivado", "uploaded": "Importado"}[scenario["kind"]],
		"centrales": nodeCount, "enlaces": len(scenario["edges"]),
		"grado medio": round(2 * len(scenario["edges"]) / nodeCount, 2),
		"capacidad total (Gbit/s)": round(sum(edge["capacity"] for edge in scenario["edges"]) / 1000, 1),
		"conectada": ("sí" if mst["connected"] else f"no · {mst['components']} componentes") if mst else "—",
	}


# Registra un escenario, avisa si queda desconectado y recarga la app
# Parametro scenario: escenario nuevo
# Retorno: sin valor; reinicia la ejecucion
def registerAndReload(scenario: dict) -> None:
	name = addScenario(scenario)
	mst = resultOf(mstRequest(scenario))
	message = f"Escenario «{name}» creado y activado"
	if mst and not mst["connected"]:
		message += f". Atención: quedó dividido en {mst['components']} componentes"
	st.session_state.managerMessage = message
	st.rerun()


# Formulario para simular fallas de enlaces y cambios de capacidad
# Parametros: ninguno
# Retorno: sin valor; dibuja la pestana
def failureTab() -> None:
	scenarios = st.session_state.scenarios
	baseName = st.selectbox("Escenario base", list(scenarios), index=list(scenarios).index(st.session_state.activeScenario))
	base = scenarios[baseName]
	failed = st.multiselect("Enlaces fuera de servicio", range(len(base["edges"])),
	                        format_func=lambda index: f"{edgeLabel(base, index)} · {base['edges'][index]['id']}")
	factor = st.slider("Factor de capacidad para los enlaces restantes", 0.25, 4.0, 1.0, step=0.25)
	defaultName = f"{baseName} · {len(failed)} falla(s)" + (f" · capacidad ×{factor:g}" if factor != 1 else "")
	name = st.text_input("Nombre del escenario", defaultName)
	if st.button("Crear escenario derivado", type="primary"):
		registerAndReload(derivedScenario(base, [base["edges"][index]["id"] for index in failed], factor, name.strip() or defaultName))


# Formulario para generar una red sintetica reproducible
# Parametros: ninguno
# Retorno: sin valor; dibuja la pestana
def syntheticTab() -> None:
	st.caption("Genera centrales aleatorias sobre Europa, las conecta con un árbol euclidiano mínimo (Prim) y agrega "
	           "enlaces entre centrales próximas. La misma semilla produce la misma red.")
	columns = st.columns(3)
	nodeCount = columns[0].slider("Centrales", 5, 300, 40)
	extraRatio = columns[1].slider("Enlaces extra por central", 0.0, 3.0, 0.8, step=0.1)
	seed = columns[2].number_input("Semilla", 0, 2 ** 31 - 1, 2038)
	if st.button("Generar red sintética", type="primary"):
		registerAndReload(syntheticScenario(nodeCount, extraRatio, int(seed)))


# Importa y exporta escenarios en JSON
# Parametros: ninguno
# Retorno: sin valor; dibuja la pestana
def transferTab() -> None:
	scenario = activeScenario()
	st.download_button("Descargar escenario activo (JSON)", scenarioToJson(scenario),
	                   file_name=f"{scenario['name']}.json".replace(" ", "_"), mime="application/json")
	st.caption("Formato: name, nodes [{id, label, lon, lat}], edges [{u, v, cost, distance, capacity}], y opcionales "
	           "source, sink, tspSelected, domain y projection. Los índices de nodos empiezan en 0.")
	upload = st.file_uploader("Importar escenario JSON", type=["json"])
	if upload is not None and st.button("Importar", type="primary"):
		try:
			registerAndReload(validateScenario(json.loads(upload.getvalue().decode("utf-8"))))
		except (ValueError, TypeError, UnicodeDecodeError) as error:
			st.error(f"No se pudo importar: {error}")


# Dibuja el administrador de escenarios
# Parametros: ninguno
# Retorno: sin valor; dibuja la pagina
def render() -> None:
	sectionHeader("MÓDULO 04 · SCENARIO MANAGER", "Carga, modifica y compara escenarios.",
	              "El escenario activo alimenta el explorador, el laboratorio y la consola. Al cambiarlo, todos los "
	              "resultados se recalculan con el motor C++.")
	if st.session_state.get("managerMessage"):
		st.success(st.session_state.managerMessage)
		st.session_state.managerMessage = None

	scenarios = st.session_state.scenarios
	st.dataframe([summaryRow(name, scenario) for name, scenario in scenarios.items()], hide_index=True, width="stretch")
	columns = st.columns([3, 1, 1])
	chosen = columns[0].selectbox("Escenario", list(scenarios), index=list(scenarios).index(st.session_state.activeScenario),
	                              label_visibility="collapsed")
	if columns[1].button("Activar", width="stretch", disabled=chosen == st.session_state.activeScenario):
		st.session_state.pendingActive = chosen
		st.rerun()
	if columns[2].button("Eliminar", width="stretch", disabled=chosen == BASE_NAME):
		del scenarios[chosen]
		if chosen == st.session_state.activeScenario:
			st.session_state.pendingActive = BASE_NAME
		st.rerun()
	st.caption(activeScenario()["description"])

	tabs = st.tabs(["Fallas y capacidades", "Red sintética", "Importar / exportar"])
	with tabs[0]:
		failureTab()
	with tabs[1]:
		syntheticTab()
	with tabs[2]:
		transferTab()
