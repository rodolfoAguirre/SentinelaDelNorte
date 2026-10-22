# Mide tiempo y memoria del motor
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-21

"""Mide tiempo y memoria del motor"""
import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

# Genera familias sinteticas reproducibles
# Parametros: ninguno
# Retorno: iterador de configuraciones de prueba
def cases():
	randomGenerator = random.Random(2038)

	for size in (100, 500, 2000):
		edges = [dict(u=i - 1, v=i, cost=randomGenerator.randrange(1000)) for i in range(1, size)]

		for _ in range(3 * size):
			sourceNode, targetNode = randomGenerator.sample(range(size), 2)
			edges.append(dict(u=sourceNode, v=targetNode, cost=randomGenerator.randrange(1000)))
		yield ('mst', size, dict(n=size, edges=edges), 'sparse ~4V')

	for size in (8, 12, 16, 20, 100, 300):
		edges = [dict(u=i, v=(i + 1) % size, distance=randomGenerator.randrange(1, 100)) for i in range(size)]

		for _ in range(size):
			sourceNode, targetNode = randomGenerator.sample(range(size), 2)
			edges.append(dict(u=sourceNode, v=targetNode, distance=randomGenerator.randrange(1, 100)))
		yield ('tsp', size, dict(n=size, edges=edges, selected=list(range(size))),
			'exact' if size <= 16 else 'heuristic')

	for size in (20, 100, 400):
		edges = [dict(u=i - 1, v=i, capacity=100) for i in range(1, size)]

		for _ in range(5 * size):
			sourceNode, targetNode = randomGenerator.sample(range(size), 2)
			edges.append(dict(u=sourceNode, v=targetNode, capacity=randomGenerator.randrange(1000)))
		yield ('max_flow', size, dict(n=size, edges=edges, source=0, sink=size - 1,
			directed=True), 'sparse ~6V')

	for size in (20, 100, 300):
		yield ('voronoi', size, dict(sites=[[randomGenerator.uniform(-100,
			100), randomGenerator.uniform(-100, 100)] for _ in range(size)], domain=[-110,
			-110, 110, 110], queries=[[0, 0]]), 'uniform sites')

	for size in (1000, 10000, 100000):
		firstText, secondText = [''.join(randomGenerator.choices('0123456789ABCDEF',
			k=size)) for _ in range(2)]

		for mode in ('matching', 'palindrome', 'common_substring'):
			inputData = dict(transmissions=[firstText, secondText])
			if mode == 'matching':
				inputData['patterns'] = ['F' * 128, 'A' * 128, 'B' * 128]
			yield (mode, size, inputData, 'random hex; matching patterns intentionally rare')

	for mode in ('matching', 'palindrome', 'common_substring'):
		inputData = dict(transmissions=['A' * 100000, 'A' * 100000])
		if mode == 'matching':
			inputData['patterns'] = ['A' * 127 + 'B', 'A' * 128, 'B']
		yield (mode, 100000, inputData, 'repeated hex')

# Coordina la ejecucion del programa
# Parametros: ninguno
# Retorno: sin valor; guarda resultados o informa errores
def main():
	argumentParser = argparse.ArgumentParser(description=__doc__)
	argumentParser.add_argument('executable', type=Path)
	arguments = argumentParser.parse_args()
	executable = arguments.executable.resolve()
	rows = []

	for mode, size, inputData, kind in cases():
		request = json.dumps(dict(mode=mode, input=inputData, metrics=True))
		samples = []

		for repeat in range(3):
			start = time.perf_counter()
			process = subprocess.run([str(executable)], input=request, text=True,
				capture_output=True, cwd=ROOT, timeout=120)
			wall = (time.perf_counter() - start) * 1000000.0
			response = json.loads(process.stdout)
			if process.returncode or not response['ok']:
				raise RuntimeError(process.stderr + str(response))
			metrics = response['metrics']
			samples.append(dict(repeat=repeat, algorithm_us=metrics['algorithm_us'],
				process_wall_us=wall, peak_process_bytes=metrics['peak_process_bytes']))
		rows.append(dict(mode=mode, size=size, kind=kind, median_algorithm_us=statistics.median((sample['algorithm_us'] for sample in samples)),
			median_process_wall_us=statistics.median((sample['process_wall_us'] for sample in samples)),
			max_peak_process_bytes=max((sample['peak_process_bytes'] for sample in samples if sample['peak_process_bytes'] is not None),
			default=None), samples=samples))
		print(mode, size, kind, round(rows[-1]['median_algorithm_us'], 2), 'us', flush=True)
	cache = (executable.parent / 'CMakeCache.txt').read_text(encoding='utf-8')
	compiler = next((line.split('=', 1)[1] for line in cache.splitlines() if line.startswith('CMAKE_CXX_COMPILER:')))
	version = subprocess.run([compiler, '--version'], text=True, capture_output=True).stdout
	report = dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
		seed=2038, repetitions=3, platform=platform.platform(), processor=platform.processor(),
		cpu_count=os.cpu_count(), python=platform.python_version(), compiler=version,
		options='CMake Release: -O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic',
		executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
		source_sha256={process.name: hashlib.sha256(process.read_bytes()).hexdigest() for process in sorted((ROOT / 'src').glob('*')) if process.is_file()},
		timing='steady_clock around C++ algorithms including validation, allocation, shortest paths; excludes parsing, normalization, file reads and result JSON construction',
		memory='Peak process working set queried before JSON dump; includes runtime, input and result structures. Not isolated algorithm memory; serialization may raise later peak.',
		measurements=rows)
	(ROOT / 'results/benchmarks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

	with (ROOT / 'results/benchmarks.csv').open('w', newline='', encoding='utf-8') as outputFile:
		writer = csv.DictWriter(outputFile, fieldnames=[k for k in rows[0] if k != 'samples'])
		writer.writeheader()
		writer.writerows(({k: targetNode for k, targetNode in row.items() if k != 'samples'} for row in rows))

if __name__ == '__main__':
	main()
