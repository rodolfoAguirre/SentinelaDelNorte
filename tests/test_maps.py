# Descripcion: verifica coordenadas y capas de los mapas
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import csv
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / ".venv-deps").is_dir():
	sys.path.insert(0, str(ROOT / ".venv-deps"))

from app import EngineAdapter
from app.visuals import ACCENT, animationSequence, buildMap, geographicPoint
from app.presentation import resultRows


class MapTest(unittest.TestCase):
	# Verifica coordenadas y enlaces con respuestas reales del motor
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si la representacion altera el resultado
	def testCoordinatesAndLayers(self):
		with (ROOT / "data/derived/nodes.csv").open(encoding="utf-8", newline="") as source:
			nodes = list(csv.DictReader(source))
		projection = json.loads((ROOT / "data/derived/scenarios.json").read_text())["projection"]
		for node in nodes:
			longitude, latitude = geographicPoint([float(node["x_km"]), float(node["y_km"])], projection)
			self.assertAlmostEqual(longitude, float(node["longitude_deg"]))
			self.assertAlmostEqual(latitude, float(node["latitude_deg"]))
		adapter = EngineAdapter()
		for mode in ("mst", "tsp", "max_flow", "voronoi"):
			request = adapter.loadRequest(f"data/derived/{mode}.input.json")
			result = adapter.runRequest(request)["result"]
			options = {"region": "Europa", "base": True, "labels": True, "step": None}
			deck = json.loads(buildMap(nodes, request, result, projection, options).to_json())
			layers = {layer["id"]: layer for layer in deck["layers"]}
			self.assertEqual(len(layers["nodes"]["data"]), len(nodes))
			if mode == "mst":
				self.assertEqual(sum(edge["color"] == ACCENT for edge in layers["links"]["data"]), len(result["edge_indices"]))
			if mode == "voronoi":
				self.assertEqual(len(layers["regions"]["data"]), sum(bool(cell) for cell in result["cells"]))
			if mode == "tsp":
				options["step"] = 0
				empty = json.loads(buildMap(nodes, request, result, projection, options).to_json())
				self.assertTrue(all(edge["color"] != ACCENT for edge in empty["layers"][0]["data"]))
			sequence = animationSequence(request, result, nodes)
			for position in (0, 1, len(sequence)):
				options["step"] = position
				frame = json.loads(buildMap(nodes, request, result, projection, options).to_json())
				frameLayers = {layer["id"]: layer for layer in frame["layers"]}
				if mode == "voronoi":
					self.assertEqual(len(frameLayers["regions"]["data"]), position)
				else:
					expected = len(set(result["physical_edge_indices"][:position])) if mode == "tsp" else position
					self.assertEqual(sum(edge["color"] == ACCENT for edge in frameLayers["links"]["data"]), expected)
			rows = resultRows(request, result, nodes)
			self.assertTrue(rows)
			self.assertFalse({"u", "v", "cost", "flow", "edge_index"}.intersection(rows[0]))
			if mode == "mst":
				self.assertEqual(rows[-1]["Costo acumulado"], result["total_cost"])
			if mode == "tsp":
				self.assertAlmostEqual(sum(row["Distancia (km)"] for row in rows), result["total_distance"])


if __name__ == "__main__":
	unittest.main(verbosity=2)
