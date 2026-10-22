# Descripcion: presenta escenarios, resultados y metricas del motor
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import copy
import csv
import html
import json
from pathlib import Path
import sys
import time

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from app import EngineAdapter, EngineError, hexFromBytes


MODES = {
	"Conexiones de menor costo · MST": "mst",
	"Ruta de mantenimiento · TSP": "tsp",
	"Capacidad de transporte · Flujo máximo": "max_flow",
	"Regiones de proximidad · Voronoi": "voronoi",
	"Firmas y transmisiones": "strings",
	"Búsqueda de firmas · KMP": "matching",
	"Palíndromos · Manacher": "palindrome",
	"Subcadena común": "common_substring",
}

STRING_MODES = {"strings", "matching", "palindrome", "common_substring"}


# Lee tablas con rutas relativas al proyecto
# Parametro name: nombre del archivo derivado
# Retorno: filas de la tabla
def readTable(name):
	with (ROOT / "data/derived" / name).open(encoding="utf-8", newline="") as source:
		return list(csv.DictReader(source))


# Dibuja el escenario y los enlaces seleccionados
# Parametros nodes, request y result: nodos, entrada y resultado
# Retorno: imagen SVG del resultado
def networkImage(nodes, request, result):
	mode = request["mode"]
	inputData = request["input"]
	points = [(float(node["x_km"]), float(node["y_km"])) for node in nodes]
	xmin, ymin = min(p[0] for p in points), min(p[1] for p in points)
	xmax, ymax = max(p[0] for p in points), max(p[1] for p in points)
	if mode == "voronoi":
		xmin, ymin, xmax, ymax = inputData["domain"]

	# Proyecta coordenadas al lienzo
	# Parametro point: par de coordenadas planas
	# Retorno: posicion en la imagen
	def screen(point):
		return (35 + 830 * (point[0] - xmin) / max(1, xmax - xmin),
		        465 - 420 * (point[1] - ymin) / max(1, ymax - ymin))

	parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 510">',
	         '<rect width="900" height="510" rx="16" fill="#101b30"/>']
	if mode == "voronoi":
		for index, polygon in enumerate(result["cells"]):
			vertices = " ".join(f"{screen(p)[0]:.2f},{screen(p)[1]:.2f}" for p in polygon)
			parts.append(f'<polygon points="{vertices}" fill="hsl({index * 137 % 360},55%,45%)" fill-opacity=".35" stroke="#90a4bc" stroke-width="1"/>')
	else:
		chosen = set(result.get("edge_indices", result.get("physical_edge_indices", [])))
		flows = {entry["edge_index"]: entry["flow"] for entry in result.get("flows", [])}
		for index, edge in enumerate(inputData["edges"]):
			first, second = screen(points[edge["u"]]), screen(points[edge["v"]])
			active = index in chosen or abs(flows.get(index, 0)) > 1e-9
			color, width = ("#36e2ac", 3) if active else ("#455773", 1)
			parts.append(f'<line x1="{first[0]}" y1="{first[1]}" x2="{second[0]}" y2="{second[1]}" stroke="{color}" stroke-width="{width}"/>')
	for index, point in enumerate(points):
		x, y = screen(point)
		label = html.escape(nodes[index]["id"])
		parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#e8f3ff"/><text x="{x + 6}" y="{y - 6}" fill="#e8f3ff" font-size="11">{label}</text>')
	parts.append('</svg>')
	return "".join(parts)


# Presenta resultados interpretables y tablas de detalle
# Parametros request, result y nodes: entrada, resultado y etiquetas
# Retorno: sin valor; dibuja componentes
def showResults(request, result, nodes):
	mode, inputData = request["mode"], request["input"]
	if mode == "mst":
		st.metric("Costo total del escenario", f'{result["total_cost"]:,.2f}')
		st.write(f'{len(result["edge_indices"])} enlaces · {result["components"]} componente(s)')
		if not result["connected"]:
			st.warning("La red está desconectada: el resultado es un bosque mínimo")
	elif mode == "tsp":
		st.metric("Distancia del recorrido", f'{result["total_distance"]:,.2f} km')
		st.write("Solución exacta" if result["exact"] else "Solución heurística · no garantiza el óptimo")
		st.write(" → ".join(nodes[index]["id"] for index in result["tour"]))
	elif mode == "max_flow":
		st.metric("Flujo máximo del escenario", f'{result["value"]:,.2f} Mbit/s')
		st.caption("Enlaces resaltados: flujo neto distinto de cero. El signo en la tabla indica dirección respecto a u → v")
	elif mode == "voronoi":
		st.metric("Regiones calculadas", len(result["cells"]))
		st.caption("Proximidad euclidiana en el plano proyectado del escenario")
	if mode not in STRING_MODES:
		st.image(networkImage(nodes, request, result), use_container_width=True)
		if mode == "mst":
			st.dataframe([dict(index=index, **inputData["edges"][index]) for index in result["edge_indices"]], use_container_width=True)
		elif mode == "tsp":
			st.dataframe([{"paso": step, "central": nodes[index]["id"]} for step, index in enumerate(result["physical_nodes"])], use_container_width=True)
		elif mode == "max_flow":
			st.dataframe([dict(**entry, **inputData["edges"][entry["edge_index"]]) for entry in result["flows"]], use_container_width=True)
		elif mode == "voronoi":
			st.dataframe([{"central": nodes[index]["id"], "vertices": len(cell)} for index, cell in enumerate(result["cells"])], use_container_width=True)
	else:
		if "matches" in result:
			st.write("Primera aparición de cada firma · posiciones desde 1")
			st.dataframe(result["matches"], use_container_width=True)
		if "palindromes" in result:
			st.write("Palíndromo más largo por transmisión")
			st.dataframe(result["palindromes"], use_container_width=True)
		if "common" in result:
			st.metric("Longitud de la subcadena común", result["common"]["length"])
			st.json(result["common"])
			common = result["common"]
			fragment = inputData["transmissions"][0][common["start"] - 1:common["end"]] if common["length"] else ""
			st.code(fragment[:200] or "Sin coincidencia")
		for index, palindrome in enumerate(result.get("palindromes", [])):
			fragment = inputData["transmissions"][index][palindrome["start"] - 1:palindrome["end"]] if palindrome["length"] else ""
			st.caption(f"Palíndromo T{index + 1} · primeros 200 caracteres")
			st.code(fragment[:200] or "Sin intervalo")


# Construye formularios y conserva resultados con su entrada
# Parametros: ninguno
# Retorno: sin valor; ejecuta la interfaz
def main():
	st.set_page_config(page_title="Sentinela del Norte", page_icon="🛡️", layout="wide")
	st.title("Sentinela del Norte")
	st.caption("Análisis de redes y transmisiones · motor C++17")
	mode = MODES[st.sidebar.selectbox("Análisis", list(MODES))]
	st.sidebar.info("Resultados y métricas se calculan al pulsar Ejecutar")
	try:
		adapter = EngineAdapter()
		nodes = readTable("nodes.csv")
		request = adapter.loadRequest("data/synthetic/strings.input.json" if mode in STRING_MODES else f"data/derived/{mode}.input.json")
	except (EngineError, OSError) as error:
		st.error(str(error))
		st.stop()
	inputData = request["input"]
	labels = [node["id"] for node in nodes]
	if mode in STRING_MODES:
		st.info("Los valores iniciales son ejemplos ilustrativos. Puedes cargar tus propias transmisiones y firmas hexadecimales")
	else:
		st.info("Escenario GÉANT histórico · 22 nodos y 36 enlaces. Capacidades suponen un módulo de 40000 Mbit/s por enlace; distancias aproximadas y dominio proyectado")
	with st.form(f"form_{mode}"):
		if mode == "tsp":
			selected = st.multiselect("Centrales que visitará la ruta", list(range(len(nodes))), default=inputData["selected"], format_func=lambda index: labels[index])
			inputData["selected"] = selected
		elif mode == "max_flow":
			inputData["source"] = st.selectbox("Origen", list(range(len(nodes))), index=inputData["source"], format_func=lambda index: labels[index])
			inputData["sink"] = st.selectbox("Destino", list(range(len(nodes))), index=inputData["sink"], format_func=lambda index: labels[index])
		elif mode in STRING_MODES:
			texts = []
			for index in range(2):
				value = inputData["transmissions"][index]
				default = (ROOT / value["file"]).read_text(encoding="ascii") if isinstance(value, dict) else value
				text = st.text_area(f"Transmisión {index + 1}", default, height=110)
				upload = st.file_uploader(f"O cargar transmisión {index + 1}", type=["txt"], key=f"upload_{index}")
				texts.append((text, upload))
			patterns = []
			for index, value in enumerate(inputData["patterns"]):
				default = (ROOT / value["file"]).read_text(encoding="ascii") if isinstance(value, dict) else value
				patterns.append(st.text_input(f"Firma {index + 1}", default.strip()))
		else:
			st.write("Se utilizará la topología y el escenario preparados en el proyecto")
		submitted = st.form_submit_button("Ejecutar análisis", type="primary")
	if submitted:
		try:
			if mode in STRING_MODES:
				inputData["transmissions"] = [hexFromBytes(upload.getvalue() if upload else text.encode("utf-8")) for text, upload in texts]
				inputData["patterns"] = [hexFromBytes(pattern.encode("utf-8")) for pattern in patterns]
			with st.spinner("Ejecutando el motor C++..."):
				started = time.perf_counter()
				response = adapter.run(mode, inputData, metrics=True)
				elapsed = time.perf_counter() - started
			st.session_state[f"result_{mode}"] = {"request": copy.deepcopy({"mode": mode, "input": inputData}), "response": response, "total_seconds": elapsed}
		except EngineError as error:
			st.session_state.pop(f"result_{mode}", None)
			st.error(f"{error.kind}: {error}")
			if error.diagnostics:
				st.code(error.diagnostics)
	stored = st.session_state.get(f"result_{mode}")
	if stored:
		st.subheader("Resultado de la última ejecución")
		response = stored["response"]
		metrics = response["metrics"]
		columns = st.columns(3)
		columns[0].metric("Tiempo del algoritmo C++", f'{metrics["algorithm_us"] / 1000:.3f} ms')
		columns[1].metric("Tiempo total de la llamada", f'{stored["total_seconds"] * 1000:.3f} ms')
		memory = metrics.get("peak_process_bytes")
		columns[2].metric("Pico de memoria del proceso", f'{memory / 1048576:.2f} MiB' if memory is not None else "No disponible")
		st.caption("Tiempo C++: cálculo y preparación interna. Tiempo total: incluye proceso y JSON. Memoria: pico del proceso completo, no memoria exclusiva del algoritmo")
		if mode == "strings":
			st.caption("En este modo conjunto, el tiempo C++ suma KMP, Manacher y subcadena común. Usa sus vistas individuales para medirlos por separado")
		showResults(stored["request"], response["result"], nodes)
		with st.expander("Entrada utilizada y respuesta completa"):
			st.json(stored["request"])
			st.json(response)
		st.download_button("Descargar resultado y métricas", json.dumps(stored, indent=2, ensure_ascii=False), file_name=f"sentinela_{mode}.json", mime="application/json")
	else:
		st.write("Configura el escenario y pulsa Ejecutar análisis para obtener resultados y métricas")


if __name__ == "__main__":
	main()
