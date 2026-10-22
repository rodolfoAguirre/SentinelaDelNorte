# Descripcion: comparte el motor, la cache de resultados y los escenarios de la sesion
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

from __future__ import annotations

import json
import time
from typing import Any

import streamlit as st

from .adapter import EngineAdapter, EngineError
from .scenarios import geantScenario


# Crea un adaptador unico para toda la app
# Parametros: ninguno
# Retorno: adaptador con el ejecutable localizado
@st.cache_resource(show_spinner=False)
def getAdapter() -> EngineAdapter:
	return EngineAdapter(timeoutSeconds=60)


# Ejecuta el motor C++ y guarda la respuesta por solicitud y binario
# Parametros executableKey y requestText: identidad del binario y solicitud serializada
# Retorno: respuesta completa o descripcion del error
@st.cache_data(show_spinner=False, max_entries=512)
def runCached(executableKey: str, requestText: str) -> dict[str, Any]:
	request = json.loads(requestText)
	started = time.perf_counter()
	try:
		response = getAdapter().run(request["mode"], request["input"], metrics=True)
	except EngineError as error:
		return {"ok": False, "error": str(error), "kind": error.kind}
	return {"ok": True, "response": response, "wallSeconds": time.perf_counter() - started}


# Ejecuta un modo del motor usando la cache de la sesion
# Parametros mode e inputData: algoritmo y entrada del contrato
# Retorno: diccionario con ok, respuesta y tiempos o error
def runEngine(mode: str, inputData: dict[str, Any]) -> dict[str, Any]:
	adapter = getAdapter()
	stat = adapter.executablePath.stat()
	executableKey = f"{adapter.executablePath}:{stat.st_mtime_ns}:{stat.st_size}"
	return runCached(executableKey, json.dumps({"mode": mode, "input": inputData}, sort_keys=True))


# Ejecuta una solicitud ya armada por los constructores de escenarios
# Parametro request: tupla modo y entrada
# Retorno: resultado del algoritmo o None si hubo error
def resultOf(request: tuple[str, dict[str, Any]]) -> dict[str, Any] | None:
	outcome = runEngine(*request)
	return outcome["response"]["result"] if outcome["ok"] else None


# Prepara los escenarios de la sesion la primera vez
# Parametros: ninguno
# Retorno: sin valor; inicializa session_state
def initState() -> None:
	if "scenarios" not in st.session_state:
		base = geantScenario()
		st.session_state.scenarios = {base["name"]: base}
		st.session_state.activeScenario = base["name"]
	if "activeSelector" not in st.session_state:
		st.session_state.activeSelector = st.session_state.activeScenario
	if st.session_state.get("pendingActive"):
		st.session_state.activeScenario = st.session_state.pendingActive
		st.session_state.activeSelector = st.session_state.pendingActive
		st.session_state.pendingActive = None


# Devuelve el escenario activo
# Parametros: ninguno
# Retorno: escenario seleccionado en la barra lateral
def activeScenario() -> dict[str, Any]:
	return st.session_state.scenarios[st.session_state.activeScenario]


# Registra un escenario nuevo y lo activa en la siguiente ejecucion
# Parametro scenario: escenario a agregar
# Retorno: nombre definitivo, sin colisiones
def addScenario(scenario: dict[str, Any]) -> str:
	name, suffix = scenario["name"], 2
	while name in st.session_state.scenarios:
		name = f"{scenario['name']} ({suffix})"
		suffix += 1
	scenario["name"] = name
	st.session_state.scenarios[name] = scenario
	st.session_state.pendingActive = name
	return name


# Etiqueta un nodo para mostrarlo en selectores
# Parametros scenario e index: escenario y nodo
# Retorno: texto legible
def nodeLabel(scenario: dict[str, Any], index: int) -> str:
	node = scenario["nodes"][index]
	return f"{node['label']} ({node['id']})"


# Etiqueta un enlace con los nombres de sus extremos
# Parametros scenario e index: escenario y enlace
# Retorno: texto legible
def edgeLabel(scenario: dict[str, Any], index: int) -> str:
	edge = scenario["edges"][index]
	return f"{scenario['nodes'][edge['u']]['label']} – {scenario['nodes'][edge['v']]['label']}"


# Muestra las metricas de ejecucion del motor en una fila
# Parametros outcome y columns: respuesta del motor y columnas destino
# Retorno: sin valor; dibuja metricas
def showEngineMetrics(outcome: dict[str, Any], columns: list) -> None:
	metrics = outcome["response"]["metrics"]
	memory = metrics.get("peak_process_bytes")
	columns[0].metric("Tiempo del algoritmo C++", f"{metrics['algorithm_us'] / 1000:.3f} ms")
	columns[1].metric("Llamada completa", f"{outcome['wallSeconds'] * 1000:.1f} ms",
	                  help="Incluye iniciar el proceso, enviar el JSON y leer la respuesta")
	columns[2].metric("Pico de memoria del proceso", f"{memory / 1048576:.1f} MiB" if memory else "—")


# Muestra un encabezado de seccion con antetitulo
# Parametros kicker, title y subtitle: textos del encabezado
# Retorno: sin valor; dibuja el encabezado
def sectionHeader(kicker: str, title: str, subtitle: str = "") -> None:
	st.markdown(f'<div class="kicker">{kicker}</div><h1 class="section-title">{title}</h1>', unsafe_allow_html=True)
	if subtitle:
		st.markdown(f'<p class="section-subtitle">{subtitle}</p>', unsafe_allow_html=True)
