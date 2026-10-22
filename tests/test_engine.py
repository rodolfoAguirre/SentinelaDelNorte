# Valida el motor con referencias independientes
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-21

"""Valida el motor con referencias independientes"""
import itertools
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else ROOT / 'build/sentinela.exe'

engineCalls = 0

# Ejecuta el motor y valida su respuesta
# Parametro mode: modo de analisis solicitado
# Parametro inputData: parametros del motor
# Parametro ok: estado esperado de la respuesta
# Parametro text: activa la salida de texto
# Retorno: resultado JSON o salida de texto
def run(mode, inputData, ok=True, text=False):
	global engineCalls
	engineCalls += 1
	p = subprocess.run([str(EXE)] + (['--text'] if text else []), input=json.dumps(dict(mode=mode,
		input=inputData)), text=True, capture_output=True, cwd=ROOT, timeout=30)
	if text:
		assert p.returncode == 0, p.stderr
		return p.stdout
	result = json.loads(p.stdout)
	assert result['ok'] == ok and (p.returncode == 0) == ok, (result, p.stderr)
	if ok:
		assert not p.stderr, p.stderr
		return result['result']
	assert p.stderr
	return result

# Enumera palindromos como referencia
# Parametro s: secuencia o conjunto de referencia
# Retorno: intervalo mas largo con menor inicio
def palindrome(s):
	candidates = [(j - i, -i) for i in range(len(s)) for j in range(i + 1,
		len(s) + 1) if s[i:j] == s[i:j][::-1]]
	length, negativeFirstStart = max(candidates, default=(0, 0))
	return dict(start=1 - negativeFirstStart if length else 0, end=length - negativeFirstStart if length else 0,
		length=length)

# Enumera fragmentos compartidos
# Parametro a: primera secuencia
# Parametro b: segunda secuencia
# Retorno: intervalos con los desempates requeridos
def common(a, b):
	best = (0, 0, 0)

	for i in range(len(a)):
		for j in range(len(b)):
			length = 0
			while i + length < len(a) and j + length < len(b) and (a[i + length] == b[j + length]):
				length += 1
			best = max(best, (length, -i, -j))
	length, negativeFirstStart, negativeSecondStart = best
	return dict(start=1 - negativeFirstStart if length else 0, end=length - negativeFirstStart if length else 0,
		start2=1 - negativeSecondStart if length else 0, end2=length - negativeSecondStart if length else 0,
		length=length)

# Calcula un costo minimo de referencia
# Parametro n: cantidad de nodos
# Parametro edges: enlaces del grafo
# Retorno: costo del arbol o None si esta desconectado
def prim(n, edges):
	visited = {0}
	cost = 0
	while len(visited) < n:
		crossing = [e for e in edges if (e['u'] in visited) != (e['v'] in visited)]
		if not crossing:
			return None
		e = min(crossing, key=lambda e: e['cost'])
		visited.update((e['u'], e['v']))
		cost += e['cost']
	return cost

# Calcula distancias de referencia
# Parametro n: cantidad de nodos
# Parametro edges: enlaces del grafo
# Retorno: matriz de caminos minimos
def floyd(n, edges):
	d = [[math.inf] * n for _ in range(n)]

	for i in range(n):
		d[i][i] = 0

	for e in edges:
		u, v = (e['u'], e['v'])
		d[u][v] = d[v][u] = min(d[u][v], e['distance'])

	for k in range(n):
		for i in range(n):
			for j in range(n):
				d[i][j] = min(d[i][j], d[i][k] + d[k][j])
	return d

# Calcula el area de un poligono
# Parametro poly: vertices del poligono
# Retorno: area sin signo
def area(poly):
	return abs(sum((a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1])))) / 2

class EngineTest(unittest.TestCase):

	# Contrasta cadenas con referencias simples
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testStringsReferences(self):
		randomGenerator = random.Random(2038)
		pairs = [('', ''), ('A', ''), ('ABBA', '00'), ('AAAA', 'AA'), ('ABAB',
			'BABA'), ('AABCDCBA12FFABBA', '00BCDCBAFFABBA77'), ('ABCABC', 'ABC'),
			('0123', 'FFFF')]
		pairs += [(''.join(randomGenerator.choices('012ABC', k=randomGenerator.randrange(35))),
			''.join(randomGenerator.choices('012ABC', k=randomGenerator.randrange(35)))) for _ in range(150)]
		words = [''.join(x) for n in range(4) for x in itertools.product('AB', repeat=n)]
		pairs += list(itertools.product(words, repeat=2))

		for a, b in pairs:
			patterns = ['', a[:3], 'FFF']
			result = run('strings', dict(transmissions=[a[:2] + '\r\n' + a[2:], b], patterns=patterns))
			self.assertEqual(result['palindromes'], [palindrome(a), palindrome(b)])
			self.assertEqual(result['common'], common(a, b))

			for t, s in enumerate((a, b)):
				for p, pattern in enumerate(patterns):
					expected = s.find(pattern)
					m = result['matches'][3 * t + p]
					self.assertEqual((m['found'], m['position']), (expected >= 0, expected + 1))

	# Verifica costo y conectividad del bosque
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testMst(self):
		randomGenerator = random.Random(2039)

		for _ in range(70):
			n = randomGenerator.randrange(1, 10)
			edges = [dict(u=u, v=v, cost=randomGenerator.randrange(-4, 20)) for u in range(n) for v in range(u + 1,
				n) if randomGenerator.random() < 0.45]
			r = run('mst', dict(n=n, edges=edges))
			reference = prim(n, edges)
			self.assertEqual(r['connected'], reference is not None)
			parent = list(range(n))

			# Busca una componente en la referencia
			# Parametro a: primera secuencia
			# Retorno: representante del nodo
			def root(a):
				while parent[a] != a:
					a = parent[a]
				return a
			total = 0

			for i in r['edge_indices']:
				e = edges[i]
				a, b = (root(e['u']), root(e['v']))
				self.assertNotEqual(a, b)
				parent[a] = b
				total += e['cost']
			self.assertEqual(total, r['total_cost'])
			self.assertEqual(len(r['edge_indices']), n - r['components'])
			if reference is not None:
				self.assertEqual(total, reference)

			for e in edges:
				self.assertEqual(root(e['u']), root(e['v']))
		r = run('mst', dict(n=2, edges=[dict(u=0, v=1, cost=5), dict(u=0, v=1, cost=1)]))
		self.assertEqual(r['edge_indices'], [1])

	# Verifica tours exactos y heuristicos
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testTsp(self):
		randomGenerator = random.Random(2040)

		for _ in range(45):
			n = randomGenerator.randrange(2, 8)
			edges = [dict(u=i - 1, v=i, distance=randomGenerator.randrange(0, 10)) for i in range(1, n)]
			edges += [dict(u=u, v=v, distance=randomGenerator.randrange(0, 20)) for u in range(n) for v in range(u + 1,
				n) if randomGenerator.random() < 0.4]
			selected = randomGenerator.sample(range(n), randomGenerator.randrange(1, n + 1))
			d = floyd(n, edges)
			optimal = min((sum((d[a][b] for a, b in zip([selected[0]] + list(p),
				list(p) + [selected[0]]))) for p in itertools.permutations(selected[1:])))

			for limit in (1, 16):
				r = run('tsp', dict(n=n, edges=edges, selected=selected, exact_limit=limit))
				self.assertEqual(r['tour'][0], selected[0])
				self.assertEqual(r['tour'][-1], selected[0])
				self.assertEqual(sorted(r['tour'][:-1]), sorted(selected))
				self.assertEqual(r['exact'], len(selected) <= limit)
				if r['exact']:
					self.assertAlmostEqual(r['total_distance'], optimal)
				self.assertGreaterEqual(r['total_distance'] + 1e-08, optimal)
				route = r['physical_nodes']
				indices = r['physical_edge_indices']
				self.assertEqual(len(route), len(indices) + 1)
				self.assertEqual(route[0], selected[0])
				self.assertEqual(route[-1], selected[0])

				for a, b, i in zip(route, route[1:], indices):
					self.assertEqual({a, b}, {edges[i]['u'], edges[i]['v']})
				self.assertAlmostEqual(sum((edges[i]['distance'] for i in indices)), r['total_distance'])
			base = run('tsp', dict(n=n, edges=edges, selected=selected, exact_limit=1, max_passes=0))
			improved = run('tsp', dict(n=n, edges=edges, selected=selected, exact_limit=1))
			self.assertLessEqual(improved['total_distance'], base['total_distance'] + 1e-08)

	# Verifica cortes minimos y conservacion del flujo
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testFlowMinCutsAndConservation(self):
		randomGenerator = random.Random(2041)

		for directed in (False, True):
			for _ in range(70):
				n = randomGenerator.randrange(2, 8)
				edges = [dict(u=u, v=v, capacity=randomGenerator.randrange(0, 30) / 2) for u in range(n) for v in range(n) if u != v and randomGenerator.random() < 0.3]
				if edges:
					edges.append(dict(edges[0]))
				r = run('max_flow', dict(n=n, edges=edges, source=0, sink=n - 1, directed=directed))

				# Suma capacidades que cruzan un corte
				# Parametro s: secuencia o conjunto de referencia
				# Retorno: capacidad del corte seleccionado
				def cut(s):
					return sum((e['capacity'] for e in edges if e['u'] in s and e['v'] not in s or (not directed and e['v'] in s and (e['u'] not in s))))
				cuts = [{0} | {i + 1 for i in range(n - 2) if mask & 1 << i} for mask in range(1 << n - 2)]
				self.assertAlmostEqual(r['value'], min(map(cut, cuts)))
				self.assertAlmostEqual(r['value'], cut(set(r['source_side'])))
				balance = [0] * n

				for e, f in zip(edges, r['flows']):
					flow = f['flow']
					self.assertLessEqual(flow, e['capacity'] + 1e-08)
					self.assertGreaterEqual(flow, -1e-08 if directed else -e['capacity'] - 1e-08)
					balance[e['u']] += flow
					balance[e['v']] -= flow
				self.assertAlmostEqual(balance[0], r['value'])
				self.assertAlmostEqual(balance[-1], -r['value'])

				for b in balance[1:-1]:
					self.assertAlmostEqual(b, 0)

	# Verifica regiones y consultas de cercania
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testVoronoi(self):
		randomGenerator = random.Random(2042)
		cases = [[[0, 0]], [[-1, 0], [1, 0]], [[0, 0], [0, 0], [1, 0]], [[-1,
			0], [0, 0], [1, 0]], [[100, 0], [200, 0]]]
		cases += [[[randomGenerator.uniform(-4, 4), randomGenerator.uniform(-4,
			4)] for _ in range(randomGenerator.randrange(1, 15))] for _ in range(45)]

		for sites in cases:
			queries = [[0, 0], [10, 10]] + [[randomGenerator.uniform(-2, 2), randomGenerator.uniform(-2,
				2)] for _ in range(15)]
			r = run('voronoi', dict(sites=sites, queries=queries, domain=[-2, -2, 2, 2]))
			self.assertAlmostEqual(sum(map(area, r['cells'])), 16, places=6)

			for i, cell in enumerate(r['cells']):
				if sites[i] in sites[:i]:
					self.assertEqual(cell, [])

				for p in cell:
					self.assertTrue(-2 - 1e-08 <= p[0] <= 2 + 1e-08 and -2 - 1e-08 <= p[1] <= 2 + 1e-08)
					own = math.dist(p, sites[i]) ** 2

					for s in sites:
						self.assertLessEqual(own, math.dist(p, s) ** 2 + 1e-07)

			for q, actual in zip(queries, r['nearest']):
				self.assertEqual(actual, min(range(len(sites)), key=lambda i: math.dist(q, sites[i])))

	# Verifica archivos, formato y datos derivados
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testFilesTextAndDerived(self):
		request = json.loads((ROOT / 'data/synthetic/strings.input.json').read_text())
		self.assertEqual(run('strings', request['input'], text=True), 'true 13\ntrue 11\nfalse\ntrue 11\ntrue 9\nfalse\n2 8\n7 12\n3 8\n')

		for path in (ROOT / 'data/derived').glob('*.input.json'):
			request = json.loads(path.read_text())
			run(request['mode'], request['input'])
		inspect = json.loads((ROOT / 'data/derived/inspection.json').read_text(encoding='utf-8'))
		self.assertEqual(inspect['counts'], dict(nodes=22, edges=36, demands=462))
		self.assertTrue(all((c['topology_match'] for c in inspect['mapping'])))

	# Comprueba el rechazo de entradas invalidas
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no cumple la propiedad
	def testInvalidInputs(self):
		cases = [('mst', dict(n=0, edges=[])), ('mst', dict(n=2, edges=[dict(u=0,
			v=2, cost=1)])), ('mst', dict(n=1, edges=[dict(u=0, v=0, cost=1)])),
			('mst', dict(n=1.5, edges=[])), ('tsp', dict(n=2, edges=[], selected=[0,
			1])), ('tsp', dict(n=1, edges=[], selected=[0, 0])), ('tsp', dict(n=1,
			edges=[], selected=[])), ('tsp', dict(n=1, edges=[], selected=[0],
			exact_limit=25)), ('max_flow', dict(n=1, edges=[], source=0, sink=0,
			directed=True)), ('max_flow', dict(n=2, edges=[dict(u=0, v=1, capacity=-1)],
			source=0, sink=1, directed=True)), ('voronoi', dict(sites=[], domain=[0,
			0, 1, 1])), ('voronoi', dict(sites=[[0, 0]], domain=[0, 0, 0, 1])),
			('strings', dict(transmissions=['abc', ''], patterns=['', '', ''])),
			('strings', dict(transmissions=['A B', ''], patterns=['', '', ''])),
			('palindrome', dict(transmissions=[{'file': 'missing-file.txt'}, ''])),
			('matching', dict(transmissions=['', ''], patterns=['A'])), ('unknown',
			{})]

		for mode, inputData in cases:
			run(mode, inputData, ok=False)

		for raw in ['', '{}{}', '{"mode":"mst","mode":"tsp"}', '{"x":01}',
			'{"x":1e999}', '{"x":NaN}', '{"x": [1,]}', '[' * 70 + ']' * 70]:
			p = subprocess.run([str(EXE)], input=raw, text=True, capture_output=True)
			self.assertNotEqual(p.returncode, 0)
			self.assertFalse(json.loads(p.stdout)['ok'])
			self.assertTrue(p.stderr)

if __name__ == '__main__':
	started = time.perf_counter()
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(EngineTest)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	report = dict(success=result.wasSuccessful(), test_groups=result.testsRun,
		engine_calls=engineCalls, failures=len(result.failures), errors=len(result.errors),
		elapsed_seconds=time.perf_counter() - started, seeds=[2038, 2039,
		2040, 2041, 2042], executable=str(EXE), executable_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),
		references=['naive string enumeration', 'Prim', 'TSP permutations + Floyd-Warshall',
		'all s-t cuts', 'Voronoi half-plane/area/nearest properties'])
	(ROOT / 'results').mkdir(exist_ok=True)
	(ROOT / 'results/tests.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
	sys.exit(0 if result.wasSuccessful() else 1)


