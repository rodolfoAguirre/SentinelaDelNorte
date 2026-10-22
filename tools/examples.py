# Descripcion: genera ejemplos con resultados reales
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-21

"""Genera ejemplos con resultados reales"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv[1]).resolve()
OUT = ROOT / 'examples'
OUT.mkdir(exist_ok=True)
links = [(0, 1, 2), (1, 2, 3), (0, 2, 9)]
cases = {'mst': dict(n=3, edges=[dict(u=u, v=v, cost=w) for u, v, w in links]),
	'tsp': dict(n=3, edges=[dict(u=u, v=v, distance=w) for u, v, w in links],
	selected=[0, 1, 2]), 'max_flow': dict(n=3, edges=[dict(u=u, v=v, capacity=w) for u,
	v, w in links], source=0, sink=2, directed=True), 'voronoi': dict(sites=[[0,
	0], [2, 0]], domain=[-1, -1, 3, 1], queries=[[1, 0], [3, 1]])}

for mode in ('matching', 'palindrome', 'common_substring', 'strings'):
	cases[mode] = dict(transmissions=['AABCDCBA12FFABBA', '00BCDCBAFFABBA77'])
	if mode in ('matching', 'strings'):
		cases[mode]['patterns'] = ['ABBA', 'FF', 'DEAD']

for mode, inputData in cases.items():
	request = json.dumps(dict(mode=mode, input=inputData), indent=2) + '\n'
	(OUT / (mode + '.input.json')).write_text(request, encoding='utf-8')
	process = subprocess.run([str(EXE)], input=request, text=True, capture_output=True, check=True)
	(OUT / (mode + '.output.json')).write_text(json.dumps(json.loads(process.stdout),
		indent=2) + '\n', encoding='utf-8')
	if mode == 'strings':
		process = subprocess.run([str(EXE), '--text'], input=request, text=True,
			capture_output=True, check=True)
		(OUT / 'strings.output.txt').write_text(process.stdout, encoding='utf-8')

for path in (ROOT / 'data/derived').glob('*.input.json'):
	process = subprocess.run([str(EXE)], input=path.read_text(), text=True, capture_output=True, check=True)
	(ROOT / 'results' / path.name.replace('.input.', '.geant.output.')).write_text(json.dumps(json.loads(process.stdout),
		indent=2) + '\n', encoding='utf-8')
print('Saved 8 example request/response pairs, text output and 4 working GEANT results.')
