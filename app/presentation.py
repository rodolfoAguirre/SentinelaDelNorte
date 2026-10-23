# Descripcion: traduce resultados a tablas comprensibles
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22


LOCATIONS = {
	"at": "Austria", "be": "Bélgica", "ch": "Suiza", "cz": "Chequia", "de": "Alemania",
	"es": "España", "fr": "Francia", "gr": "Grecia", "hr": "Croacia", "hu": "Hungría",
	"ie": "Irlanda", "il": "Israel", "it": "Italia", "lu": "Luxemburgo", "nl": "Países Bajos",
	"ny": "Nueva York", "pl": "Polonia", "pt": "Portugal", "se": "Suecia", "si": "Eslovenia",
	"sk": "Eslovaquia", "uk": "Reino Unido",
}


# Agrega una ubicacion legible al identificador de la central
# Parametro node: fila de nodos del escenario
# Retorno: etiqueta comprensible
def centralName(node):
	identifier = node["id"]
	return f"{LOCATIONS.get(identifier.split('.')[-1], identifier)} · {identifier}"


# Construye tablas con unidades y etiquetas de negocio
# Parametros request, result y nodes: solicitud, respuesta y centrales
# Retorno: filas de la tabla principal
def resultRows(request, result, nodes):
	mode, data = request["mode"], request["input"]
	rows = []
	if mode == "mst":
		accumulated = 0
		for step, index in enumerate(result["edge_indices"], 1):
			edge = data["edges"][index]
			accumulated += edge["cost"]
			rows.append({"Orden de selección": step, "Central A": centralName(nodes[edge["u"]]),
			             "Central B": centralName(nodes[edge["v"]]), "Costo del enlace": edge["cost"], "Costo acumulado": accumulated})
	elif mode == "tsp":
		for step, index in enumerate(result["physical_edge_indices"], 1):
			edge = data["edges"][index]
			rows.append({"Tramo": step, "Desde": centralName(nodes[result["physical_nodes"][step - 1]]),
			             "Hasta": centralName(nodes[result["physical_nodes"][step]]), "Distancia (km)": edge["distance"]})
	elif mode == "max_flow":
		for entry in result["flows"]:
			edge = data["edges"][entry["edge_index"]]
			first, second = (edge["u"], edge["v"]) if entry["flow"] >= 0 else (edge["v"], edge["u"])
			flow = abs(entry["flow"])
			rows.append({"Desde": centralName(nodes[first]), "Hasta": centralName(nodes[second]),
			             "Flujo enviado (Mbit/s)": flow, "Capacidad (Mbit/s)": edge["capacity"],
			             "Uso de capacidad (%)": flow / edge["capacity"] * 100 if edge["capacity"] else 0,
			             "Estado": "Transporta flujo" if flow > 1e-9 else "Sin flujo"})
	elif mode == "voronoi":
		for index, polygon in enumerate(result["cells"]):
			area = abs(sum(first[0] * second[1] - second[0] * first[1] for first, second in zip(polygon, polygon[1:] + polygon[:1]))) / 2
			rows.append({"Central responsable": centralName(nodes[index]), "Área en el plano (km²)": area,
			             "Estado": "Región asignada" if polygon else "Sin región propia"})
	return rows
