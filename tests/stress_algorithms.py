# Descripcion: prueba siete algoritmos con cargas aleatorias crecientes
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT / ("build/sentinela.exe" if os.name == "nt" else "build/sentinela"))
SEED = 20261022


# Ejecuta una solicitud y mide el proceso completo
# Parametros mode e inputData: modo y datos de entrada
# Retorno: resultado y tiempo en segundos
def runCase(mode, inputData):
	started = time.perf_counter()
	process = subprocess.run(
		[str(EXE)], input=json.dumps({"mode": mode, "input": inputData}),
		text=True, capture_output=True, cwd=ROOT, timeout=90,
	)
	if process.returncode != 0:
		raise RuntimeError(f"{mode}: {process.stderr or process.stdout}")
	return json.loads(process.stdout)["result"], time.perf_counter() - started


# Genera una red conectada con pesos aleatorios
# Parametros size e density: nodos y probabilidad de enlaces extra
# Retorno: lista de enlaces
def randomGraph(size, density, generator):
	edges = []
	for node in range(1, size):
		edges.append({"u": node - 1, "v": node, "cost": generator.randint(1, 1000),
		              "distance": generator.randint(1, 1000), "capacity": generator.randint(1, 1000)})
	for source in range(size):
		for target in range(source + 2, size):
			if generator.random() < density:
				edges.append({"u": source, "v": target, "cost": generator.randint(1, 1000),
				              "distance": generator.randint(1, 1000), "capacity": generator.randint(1, 1000)})
	return edges


# Verifica que el orden de visita sea un ciclo valido
# Parametros result y size: respuesta y nodos esperados
# Retorno: sin valor; lanza error ante una ruta invalida
def checkTour(result, size):
	route = result["tour"]
	assert route[0] == route[-1] == 0
	assert sorted(route[:-1]) == list(range(size))
	assert math.isfinite(result["total_distance"])
	assert result["total_distance"] >= 0


# Verifica intervalos de texto y posiciones de patrones
# Parametros results, texts y patterns: respuestas y entradas
# Retorno: sin valor; lanza error ante un intervalo incorrecto
def checkStrings(results, texts, patterns):
	for text, palindrome in zip(texts, results["palindromes"]):
		start, end, length = palindrome["start"], palindrome["end"], palindrome["length"]
		assert length == end - start + 1 if length else (start == end == 0)
		if length:
			fragment = text[start - 1:end]
			assert fragment == fragment[::-1]
	for match in results["matches"]:
		text = texts[match["transmission"] - 1]
		pattern = patterns[match["pattern"] - 1]
		assert (match["found"] and text[match["position"] - 1:].startswith(pattern)) or (
			not match["found"] and pattern not in text)
	common = results["common"]
	if common["length"]:
		fragment = texts[0][common["start"] - 1:common["end"]]
		assert len(fragment) == common["length"] and fragment in texts[1]
	if len(texts[0]) <= 100:
		for text, result in zip(texts, results["palindromes"]):
			valid = [text[start:end] for start in range(len(text))
			         for end in range(start + 1, len(text) + 1)
			         if text[start:end] == text[start:end][::-1]]
			assert result["length"] == max(map(len, valid), default=0)
		commonLength = max((length for start in range(len(texts[0]))
		                    for length in range(1, len(texts[0]) - start + 1)
		                    if texts[0][start:start + length] in texts[1]), default=0)
		assert results["common"]["length"] == commonLength


# Prueba todos los modos con tres escalas reproducibles
# Parametros generator e records: generador y mediciones acumuladas
# Retorno: sin valor; falla si una propiedad del motor se rompe
def stressScale(label, size, generator, records):
	edges = randomGraph(size, min(0.15, 8 / max(1, size)), generator)
	nodes = list(range(size))
	result, seconds = runCase("mst", {"n": size, "edges": edges})
	assert result["connected"] and len(result["edge_indices"]) == size - 1
	assert math.isfinite(result["total_cost"])
	assert result["total_cost"] == sum(edges[index]["cost"] for index in result["edge_indices"])
	records.append({"scale": label, "mode": "mst", "size": size, "edges": len(edges), "seconds": seconds})

	tspSize = 8 if size <= 12 else size // 2
	tspEdges = randomGraph(tspSize, 0.12, generator)
	result, seconds = runCase("tsp", {"n": tspSize, "edges": tspEdges,
	                                  "selected": nodes[:tspSize], "exact_limit": 8})
	checkTour(result, tspSize)
	if size <= 12:
		assert result["exact"]
	records.append({"scale": label, "mode": "tsp", "size": tspSize,
	                "edges": len(tspEdges), "exact": result["exact"], "seconds": seconds})

	flowEdges = [{key: edge[key] for key in ("u", "v", "capacity")} for edge in edges]
	result, seconds = runCase("max_flow", {"n": size, "edges": flowEdges,
	                                      "source": 0, "sink": size - 1, "directed": True})
	assert math.isfinite(result["value"]) and result["value"] >= 0
	assert len(result["flows"]) == len(flowEdges)
	cutCapacity = sum(edge["capacity"] for edge in flowEdges
	                   if edge["u"] in result["source_side"] and edge["v"] not in result["source_side"])
	assert math.isclose(cutCapacity, result["value"])
	records.append({"scale": label, "mode": "max_flow", "size": size,
	                "edges": len(flowEdges), "seconds": seconds})

	pointCount = min(size, 300)
	sites = [[generator.uniform(0, 1000), generator.uniform(0, 1000)] for _ in range(pointCount)]
	result, seconds = runCase("voronoi", {"sites": sites, "domain": [0, 0, 1000, 1000],
	                                      "queries": [[500, 500], [0, 0], [1000, 1000]]})
	assert len(result["cells"]) == pointCount and len(result["nearest"]) == 3
	assert all(0 <= index < pointCount for index in result["nearest"])
	cellArea = sum(abs(sum((polygon[index][0] * polygon[(index + 1) % len(polygon)][1] -
	                        polygon[index][1] * polygon[(index + 1) % len(polygon)][0])
	                       for index in range(len(polygon)))) / 2
	                for polygon in result["cells"] if polygon)
	assert math.isclose(cellArea, 1000000, rel_tol=1e-7, abs_tol=0.1)
	records.append({"scale": label, "mode": "voronoi", "size": pointCount, "seconds": seconds})

	textSize = min(size * 200, 250000) if size > 12 else 80
	texts = ["".join(generator.choices("0123456789ABCDEF", k=textSize)) for _ in range(2)]
	pattern = texts[0][textSize // 3:textSize // 3 + min(32, textSize // 4)]
	patterns = [pattern, "F" * 40, "0123456789ABCDEF"]
	result, seconds = runCase("strings", {"transmissions": texts, "patterns": patterns})
	checkStrings(result, texts, patterns)
	records.append({"scale": label, "mode": "strings", "size": textSize, "seconds": seconds})


# Ejecuta escalas pequena, mediana y grande con semilla fija
# Parametros: ninguno
# Retorno: cero si todas las propiedades se cumplen
def main():
	generator = random.Random(SEED)
	records = []
	for label, size in (("pequena", 12), ("mediana", 120), ("grande", 600)):
		stressScale(label, size, generator, records)
		print(f"[OK] {label}: nodos={size}")

	report = {"seed": SEED, "executable": EXE.name, "success": True, "records": records}
	output = ROOT / "results/stress_tests.json"
	output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
	print(f"Prueba completada: {len(records)} ejecuciones; resultados en {output}")
	for record in records:
		print(f"{record['scale']:8} {record['mode']:10} {record['seconds']:.3f}s")
	return 0


if __name__ == "__main__":
	sys.exit(main())
