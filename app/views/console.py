# Descripcion: analiza transmisiones hexadecimales contra firmas de referencia
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import html

import streamlit as st

from .. import charts
from ..adapter import EngineError, hexFromBytes
from ..scenarios import sampleTransmissions
from ..state import activeScenario, runEngine, sectionHeader, showEngineMetrics


SIGNATURE_CLASSES = ["sig0", "sig1", "sig2"]
FULL_VIEW_LIMIT = 2400
CONTEXT = 48
LINK_ALIASES = {"Austria – Suiza": "at1.at_ch1.ch", "Austria – Alemania": "at1.at_de1.de"}


# Marca cada caracter con los hallazgos que lo cubren
# Parametros text, intervals: transmision y lista de intervalos con clase
# Retorno: lista de conjuntos de clases por caracter
def characterClasses(text: str, intervals: list[tuple[int, int, str]]) -> list[set[str]]:
	classes = [set() for _ in text]
	for start, end, name in intervals:
		for position in range(max(0, start), min(len(text), end)):
			classes[position].add(name)
	return classes


# Convierte un tramo marcado en HTML agrupando clases iguales
# Parametros text, classes, first y last: texto, marcas y limites del tramo
# Retorno: fragmento HTML
def renderSpan(text: str, classes: list[set[str]], first: int, last: int) -> str:
	parts = []
	position = first
	while position < last:
		current = classes[position]
		end = position
		while end < last and classes[end] == current:
			end += 1
		fragment = html.escape(text[position:end])
		parts.append(f'<span class="{" ".join(sorted(current))}">{fragment}</span>' if current else fragment)
		position = end
	return "".join(parts)


# Construye la vista resaltada completa o por ventanas alrededor de cada hallazgo
# Parametros text e intervals: transmision y hallazgos
# Retorno: HTML listo para mostrar
def highlightedTransmission(text: str, intervals: list[tuple[int, int, str]]) -> str:
	if not text:
		return '<div class="hexview muted">(transmisión vacía)</div>'
	if len(text) <= FULL_VIEW_LIMIT:
		classes = characterClasses(text, intervals)
		return f'<div class="hexview">{renderSpan(text, classes, 0, len(text))}</div>'
	windows = sorted((max(0, start - CONTEXT), min(len(text), min(end, start + 400) + CONTEXT))
	                 for start, end, _ in intervals if end > start)
	merged = []
	for start, end in windows:
		if merged and start <= merged[-1][1]:
			merged[-1] = (merged[-1][0], max(merged[-1][1], end))
		else:
			merged.append((start, end))
	if not merged:
		merged.append((0, min(len(text), 400)))
	pieces = []
	for start, end in merged:
		window = text[start:end]
		shifted = [(first - start, last - start, name) for first, last, name in intervals]
		classes = characterClasses(window, shifted)
		pieces.append(f'<span class="muted">[{start + 1}]</span> {renderSpan(window, classes, 0, len(window))}')
	return '<div class="hexview">' + ' <span class="muted">…</span><br>'.join(pieces) + "</div>"


# Arma las nueve lineas del formato oficial de salida
# Parametro result: resultado del modo strings
# Retorno: texto con seis lineas de firmas, dos de palindromos y una comun
def officialOutput(result: dict) -> str:
	lines = [f"true {match['position']}" if match["found"] else "false" for match in result["matches"]]
	lines += [f"{palindrome['start']} {palindrome['end']}" for palindrome in result["palindromes"]]
	lines.append(f"{result['common']['start']} {result['common']['end']}")
	return "\n".join(lines) + "\n"


# Lee las entradas del usuario y las normaliza como hexadecimal
# Parametros: ninguno
# Retorno: transmisiones y firmas, o None si son invalidas
def readInputs() -> tuple[list[str], list[str]] | None:
	sampleTexts, samplePatterns, _ = sampleTransmissions()
	columns = st.columns(2)
	texts = []
	for index, column in enumerate(columns):
		with column:
			text = st.text_area(f"Transmisión {index + 1}", sampleTexts[index], height=110, key=f"transmission{index}")
			upload = st.file_uploader(f"Cargar transmission{index + 1}.txt", type=["txt"], key=f"upload{index}")
			texts.append(upload.getvalue() if upload else text.strip().encode("utf-8"))
	signatureText = st.text_input("Tres firmas (separadas por comas)", ", ".join(samplePatterns))
	patterns = [value.strip() for value in signatureText.split(",")]
	if len(patterns) != 3:
		st.error(f"Se requieren exactamente tres firmas; se recibieron {len(patterns)}")
		return None
	try:
		return [hexFromBytes(content) for content in texts], [hexFromBytes(value.encode("utf-8")) for value in patterns]
	except EngineError as error:
		st.error(f"{error}. Solo se permiten 0-9 y A-F en mayúsculas; se ignoran saltos de línea")
		return None


# Dibuja la consola de ciberseguridad
# Parametros: ninguno
# Retorno: sin valor; dibuja la pagina
def render() -> None:
	sectionHeader("MÓDULO 03 · CYBERSECURITY CONSOLE", "Analiza las transmisiones.",
	              "Localiza firmas con KMP, secuencias simétricas con Manacher y fragmentos compartidos con un "
	              "autómata de sufijos. Posiciones base 1 sobre la secuencia normalizada.")
	_, _, mapping = sampleTransmissions()
	scenario = activeScenario()
	with st.expander("Asociación simulada de transmisiones con enlaces (mapping.csv)", expanded=False):
		st.dataframe([{"transmisión": row["transmission"], "conexión asignada": row["link"], "escenario": row["scenario"],
		               "estado": row["status"]} for row in mapping], hide_index=True, width="stretch")
		identifiers = {edge["id"]: index for index, edge in enumerate(scenario["edges"])}
		linked = [identifiers[LINK_ALIASES[row["link"]]] for row in mapping
		          if LINK_ALIASES.get(row["link"]) in identifiers]
		if linked:
			st.plotly_chart(charts.networkMap(scenario, {"highlight": (linked, "Enlaces con transmisión asignada")}, height=340),
			                width="stretch", config={"displaylogo": False})
		st.caption("GÉANT y CIC-IDS2017 son entornos independientes. La asociación es una construcción de simulación; "
		           "las etiquetas de tráfico dan contexto y no sustituyen los resultados. Encontrar una firma no confirma un ataque.")

	inputs = readInputs()
	if inputs is None:
		return
	texts, patterns = inputs
	outcome = runEngine("strings", {"transmissions": texts, "patterns": patterns})
	if not outcome["ok"]:
		st.error(f"El motor rechazó la solicitud: {outcome['error']}")
		return
	result = outcome["response"]["result"]
	found = sum(1 for match in result["matches"] if match["found"])
	columns = st.columns(4)
	columns[0].metric("Firmas detectadas", f"{found} de 6")
	columns[1].metric("Palíndromo más largo", f"{max(item['length'] for item in result['palindromes'])} caracteres")
	columns[2].metric("Subcadena común", f"{result['common']['length']} caracteres")
	columns[3].metric("Longitudes", f"{len(texts[0]):,} / {len(texts[1]):,}")
	showEngineMetrics(outcome, st.columns(3))

	st.markdown("**KMP · primera aparición de cada firma**")
	rows = []
	for patternIndex, pattern in enumerate(patterns):
		row = {"firma": pattern or "(vacía)"}
		for match in result["matches"]:
			if match["pattern"] == patternIndex + 1:
				row[f"T{match['transmission']}"] = f"true {match['position']}" if match["found"] else "false"
		rows.append(row)
	st.dataframe(rows, hide_index=True, width="stretch")

	st.markdown("**Transmisiones con hallazgos resaltados**")
	st.markdown('<span class="sig0">firma 1</span> <span class="sig1">firma 2</span> <span class="sig2">firma 3</span> '
	            '<span class="pal">palíndromo</span> <span class="common">subcadena común</span>', unsafe_allow_html=True)
	common = result["common"]
	for index, text in enumerate(texts):
		intervals = []
		for match in result["matches"]:
			if match["transmission"] == index + 1 and match["found"]:
				length = len(patterns[match["pattern"] - 1])
				intervals.append((match["position"] - 1, match["position"] - 1 + length, SIGNATURE_CLASSES[match["pattern"] - 1]))
		palindrome = result["palindromes"][index]
		if palindrome["length"]:
			intervals.append((palindrome["start"] - 1, palindrome["end"], "pal"))
		if common["length"]:
			start = common["start"] if index == 0 else common["start2"]
			intervals.append((start - 1, start - 1 + common["length"], "common"))
		st.markdown(f"T{index + 1}")
		st.markdown(highlightedTransmission(text, intervals), unsafe_allow_html=True)

	columns = st.columns(2)
	with columns[0]:
		st.markdown("**Palíndromo más largo**")
		for index, palindrome in enumerate(result["palindromes"]):
			fragment = texts[index][palindrome["start"] - 1:palindrome["end"]] if palindrome["length"] else ""
			st.markdown(f"T{index + 1}: `{fragment[:60] + ('…' if len(fragment) > 60 else '') or '—'}` · "
			            f"{palindrome['start']}–{palindrome['end']}")
		st.markdown("**Subcadena común más larga**")
		fragment = texts[0][common["start"] - 1:common["end"]] if common["length"] else ""
		st.markdown(f"`{fragment[:60] + ('…' if len(fragment) > 60 else '') or '—'}` · T1 {common['start']}–{common['end']} · "
		            f"T2 {common['start2']}–{common['end2']}")
	with columns[1]:
		st.markdown("**Salida en formato oficial**")
		output = officialOutput(result)
		st.code(output, language=None)
		st.download_button("Descargar salida", output, file_name="sentinela_output.txt", mime="text/plain")
