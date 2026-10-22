# Prepara datos de trabajo reproducibles
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-21

"""Prepara datos de trabajo reproducibles"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://sndlib.zib.de/network'}

# Guarda datos con formato JSON
# Parametro path: ruta del archivo
# Parametro data: datos que se guardan
# Retorno: sin valor; escribe el archivo
def writeJson(path, data):
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Guarda filas con encabezado CSV
# Parametro path: ruta del archivo
# Parametro rows: filas que se guardan
# Retorno: sin valor; escribe el archivo
def writeCsv(path, rows):
	with path.open('w', newline='', encoding='utf-8') as fileHandle:
		writer = csv.DictWriter(fileHandle, fieldnames=list(rows[0]))
		writer.writeheader()
		writer.writerows(rows)

# Coordina la ejecucion del programa
# Parametros: ninguno
# Retorno: sin valor; guarda resultados o informa errores
def main():
	argumentParser = argparse.ArgumentParser(description=__doc__)
	argumentParser.add_argument('--xml', type=Path, default=ROOT / 'geant.xml')
	argumentParser.add_argument('--mapping', type=Path, default=ROOT / 'mapping.csv')
	argumentParser.add_argument('--modules', type=int, default=1)
	argumentParser.add_argument('--lat0', type=float, default=50)
	argumentParser.add_argument('--lon0', type=float, default=10)
	argumentParser.add_argument('--margin-km', type=float, default=100)
	arguments = argumentParser.parse_args()
	if arguments.modules < 0 or arguments.modules > 1000000 or (not -89 <= arguments.lat0 <= 89) or (not -180 <= arguments.lon0 <= 180) or (not math.isfinite(arguments.margin_km)) or (arguments.margin_km <= 0):
		argumentParser.error('Invalid modules, projection origin, or margin')
	original, derived, synthetic = [ROOT / 'data' / d for d in ('original', 'derived', 'synthetic')]

	for p in (original, derived, synthetic):
		p.mkdir(parents=True, exist_ok=True)

	for sourcePath, name in ((arguments.xml, 'geant.xml'), (arguments.mapping, 'mapping.csv')):
		if sourcePath.resolve() != (original / name).resolve():
			shutil.copyfile(sourcePath, original / name)
	document = ET.parse(arguments.xml).getroot()

	# Consulta un campo XML obligatorio
	# Parametro element: elemento XML
	# Parametro path: ruta del campo XML
	# Retorno: texto del campo solicitado
	def text(element, path):
		value = element.findtext(path, namespaces=NS)
		if value is None:
			raise ValueError('Missing XML field: ' + path)
		return value

	# Valida un campo XML numerico
	# Parametro element: elemento XML
	# Parametro path: ruta del campo XML
	# Retorno: numero finito del campo
	def num(element, path):
		numericValue = float(text(element, path))
		if not math.isfinite(numericValue):
			raise ValueError('Nonfinite XML value')
		return numericValue
	nodes = []

	for i, n in enumerate(document.findall('s:networkStructure/s:nodes/s:node', NS)):
		longitude, latitude = (num(n, 's:coordinates/s:x'), num(n, 's:coordinates/s:y'))
		nodes.append(dict(index=i, id=n.attrib['id'], longitude_deg=longitude,
			latitude_deg=latitude, x_km=6371.0088 * math.radians(longitude - arguments.lon0) * math.cos(math.radians(arguments.lat0)),
			y_km=6371.0088 * math.radians(latitude - arguments.lat0)))
	ids = {n['id']: n['index'] for n in nodes}
	if len(ids) != len(nodes):
		raise ValueError('Duplicate node ID')
	edges, capacities = ([], [])

	for i, element in enumerate(document.findall('s:networkStructure/s:links/s:link', NS)):
		u, numericValue = (ids[text(element, 's:source')], ids[text(element, 's:target')])
		modules = element.findall('s:additionalModules/s:addModule', NS)
		if len(modules) != 1 or element.find('s:preInstalledModule', NS) is not None:
			raise ValueError('Converter expects this instance: one additional module, no installed capacity')
		moduleCapacity, cost = (num(modules[0], 's:capacity'), num(modules[0], 's:cost'))
		a, b = (nodes[u], nodes[numericValue])
		la, lb = (math.radians(a['latitude_deg']), math.radians(b['latitude_deg']))
		h = math.sin((lb - la) / 2) ** 2 + math.cos(la) * math.cos(lb) * math.sin(math.radians(b['longitude_deg'] - a['longitude_deg']) / 2) ** 2
		distance = 2 * 6371.0088 * math.asin(math.sqrt(min(1, max(0, h))))
		edges.append(dict(index=i, id=element.attrib['id'], u=u, v=numericValue,
			module_cost=cost, working_cost=cost * arguments.modules, distance_km=distance,
			directed=False))
		capacities.append(dict(edge_index=i, module_capacity_mbps=moduleCapacity,
			assumed_modules=arguments.modules, scenario_capacity_mbps=moduleCapacity * arguments.modules,
			installed_capacity='unknown', provenance='synthetic_module_count'))
	demands = [dict(id=d.attrib['id'], u=ids[text(d, 's:source')], v=ids[text(d,
		's:target')], demand_mbps=num(d, 's:demandValue'), directed=True) for d in document.findall('s:demands/s:demand',
		NS)]

	for name, rows in [('nodes', nodes), ('edges', edges), ('capacities', capacities), ('demands', demands)]:
		writeCsv(derived / (name + '.csv'), rows)
	aliases = {'Austria': 'at1.at', 'Suiza': 'ch1.ch', 'Alemania': 'de1.de'}
	checks = []

	with arguments.mapping.open(encoding='utf-8-sig', newline='') as fileHandle:
		for row in csv.DictReader(fileHandle):
			countries = [x.strip() for x in row['link'].replace('–', '-').split('-')]
			pair = [ids[aliases[x]] for x in countries]
			matches = [element['id'] for element in edges if {element['u'], element['v']} == set(pair)]
			checks.append(dict(**row, node_indices=pair, matching_links=matches,
				topology_match=bool(matches), transmission_available=(original / row['transmission']).exists()))
	domain = [min((n['x_km'] for n in nodes)) - arguments.margin_km, min((n['y_km'] for n in nodes)) - arguments.margin_km,
		max((n['x_km'] for n in nodes)) + arguments.margin_km, max((n['y_km'] for n in nodes)) + arguments.margin_km]
	config = dict(status='WORKING SYNTHETIC SCENARIO - NOT OFFICIAL', modules_per_link=arguments.modules,
		source=ids['at1.at'], sink=ids['de1.de'], tsp_selected=list(range(len(nodes))),
		domain=domain, projection=dict(type='equirectangular', lat0=arguments.lat0,
		lon0=arguments.lon0, radius_km=6371.0088), links='undirected; signed net flow with shared capacity',
		capacities='assumed installation of additional modules', costs='module_cost * assumed_modules; XML cost units unspecified',
		distances='haversine endpoint distance, km, only existing links',
		demands='original directed demand matrix, never capacities')
	writeJson(derived / 'scenarios.json', config)
	report = dict(counts=dict(nodes=len(nodes), edges=len(edges), demands=len(demands)),
		xml_meta={c.tag.split('}')[-1]: c.text for c in document.find('s:meta',
		NS)}, original_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in original.iterdir() if p.is_file()},
		mapping=checks, installed_capacity_present=False, note='No discrepancies in supplied mappings' if all((c['topology_match'] for c in checks)) else 'Mapping discrepancy detected')
	writeJson(derived / 'inspection.json', report)

	for mode, key, source in [('mst', 'cost', 'working_cost'), ('tsp',
		'distance', 'distance_km'), ('max_flow', 'capacity', None)]:
		inputData = dict(n=len(nodes), edges=[dict(u=element['u'], v=element['v'],
			**{key: element[source] if source else capacities[i]['scenario_capacity_mbps']}) for i,
			element in enumerate(edges)])
		if mode == 'tsp':
			inputData['selected'] = config['tsp_selected']
		if mode == 'max_flow':
			inputData.update(source=config['source'], sink=config['sink'], directed=False)
		writeJson(derived / (mode + '.input.json'), dict(mode=mode, input=inputData))
	writeJson(derived / 'voronoi.input.json', dict(mode='voronoi', input=dict(sites=[[n['x_km'],
		n['y_km']] for n in nodes], domain=domain, queries=[[0, 0]])))

	for name, content in [('transmission1', 'AABCDCBA12FFABBA'), ('transmission2',
		'00BCDCBAFFABBA77'), ('mcode1', 'ABBA'), ('mcode2', 'FF'), ('mcode3',
		'DEAD')]:
		(synthetic / (name + '.txt')).write_text(content + '\n', encoding='ascii')
	writeJson(synthetic / 'strings.input.json', dict(mode='strings', input=dict(transmissions=[{'file': f'data/synthetic/transmission{i}.txt'} for i in (1,
		2)], patterns=[{'file': f'data/synthetic/mcode{i}.txt'} for i in (1,
		2, 3)])))
	(synthetic / 'README.md').write_text('Casos sintéticos ilustrativos del PDF, página 11. No son transmisiones ni firmas oficiales.\nLas etiquetas benigno/DDoS de mapping.csv no se transfieren a estos textos.\n',
		encoding='utf-8')
	print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
	main()
