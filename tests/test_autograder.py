# Descripcion: verifica diferencias entre el contrato web y el local
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-21

import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else (ROOT / ("build/sentinela.exe" if os.name == "nt" else "build/sentinela"))


# Ejecuta una solicitud bajo el contrato web
# Parametros mode e inputData: algoritmo y datos del caso
# Retorno: objeto JSON directo del motor
def runCase(mode, inputData):
	result = subprocess.run(
		[str(EXE), "--autograder"], input=json.dumps({"mode": mode, "input": inputData}),
		text=True, capture_output=True, check=True, timeout=20,
	)
	return json.loads(result.stdout)


class AutograderTest(unittest.TestCase):
	# Verifica costos directos sin aplicar cierre metrico
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida el tour
	def testMatrixCosts(self):
		result = runCase("tsp", {"distances": [[0, 100, 1], [100, 0, 1], [1, 1, 0]]})
		self.assertEqual(result["cost"], 102)
		self.assertEqual(sorted(result["route"][:-1]), [0, 1, 2])
		self.assertEqual(result["route"][0], result["route"][-1])

	# Comprueba los cuatro patrones y textos generales del sitio
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida posiciones y ausencias
	def testVariablePatterns(self):
		self.assertEqual(runCase("matching", {
			"transmissions": ["XXABCYYABC", "ZZXYZ"], "patterns": ["ABC", "XY", "ZZ", "NONE"],
		}), {"matches": [[3, -1, -1, -1], [-1, 3, 1, -1]]})

	# Contrasta el automata general contra enumeracion independiente
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida longitud y desempate
	def testGeneralCommon(self):
		rng = random.Random(1114129554)
		for index in range(40):
			firstText = "".join(rng.choices("XYZ012", k=rng.randrange(1, 25)))
			secondText = "".join(rng.choices("XYZ012", k=rng.randrange(1, 25)))
			bestStart, bestLength = 0, 0
			for start in range(len(firstText)):
				for length in range(1, len(firstText) - start + 1):
					if length > bestLength and firstText[start:start + length] in secondText:
						bestStart, bestLength = start, length
			expected = [bestStart + 1, bestStart + bestLength] if bestLength else [0, 0]
			with self.subTest(index=index):
				self.assertEqual(runCase("common", {"transmissions": [firstText, secondText]}), {"range": expected})

	# Comprueba el limite de nodos del perfil huge
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida el arbol completo
	def testLargeMst(self):
		result = runCase("mst", {"nodes": list(range(5000)), "edges": [
			{"u": index - 1, "v": index, "weight": 1} for index in range(1, 5000)
		]})
		self.assertEqual(result["cost"], 4999)
		self.assertEqual(len(result["edges"]), 4999)


if __name__ == "__main__":
	unittest.main(verbosity=2)
