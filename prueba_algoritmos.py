# Descripcion: prueba los siete algoritmos desde Python
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-21

import json
import sys

from app import EngineAdapter, EngineError


EXAMPLES = [
	("mst", {"cost": 5, "connected": True}),
	("tsp", {"distance": 10, "exact": True}),
	("max_flow", {"flow": 11}),
	("voronoi", {"nearest": [0, 1]}),
	("matching", {
		"positions": [13, 11, 0, 11, 9, 0],
		"found": [True, True, False, True, True, False],
	}),
	("palindrome", {"intervals": [[2, 8], [7, 12]]}),
	("common_substring", {"interval": [3, 8], "length": 6}),
]


# Selecciona los datos principales para mostrar el resultado
# Parametro mode: algoritmo ejecutado
# Parametro result: resultado devuelto por el motor
# Retorno: resumen comparable con el ejemplo esperado
def summarizeResult(mode, result):
	if mode == "mst":
		return {"cost": result["total_cost"], "connected": result["connected"]}

	if mode == "tsp":
		return {"distance": result["total_distance"], "exact": result["exact"]}

	if mode == "max_flow":
		return {"flow": result["value"]}

	if mode == "voronoi":
		return {"nearest": result["nearest"]}

	if mode == "matching":
		return {
			"positions": [match["position"] for match in result["matches"]],
			"found": [match["found"] for match in result["matches"]],
		}

	if mode == "palindrome":
		return {
			"intervals": [
				[palindrome["start"], palindrome["end"]]
				for palindrome in result["palindromes"]
			],
		}

	if mode == "common_substring":
		common = result["common"]
		return {"interval": [common["start"], common["end"]], "length": common["length"]}

	raise ValueError(f"Modo sin resumen: {mode}")


# Ejecuta los casos pequenos mediante el adaptador real
# Parametros: ninguno
# Retorno: cero si todos coinciden o uno si alguna prueba falla
def main():
	try:
		adapter = EngineAdapter()
		print(f"Motor: {adapter.executablePath}\n")

		for mode, expected in EXAMPLES:
			request = adapter.loadRequest(f"examples/{mode}.input.json")
			response = adapter.runRequest(request)
			actual = summarizeResult(mode, response["result"])

			if actual != expected:
				raise ValueError(f"{mode}: se esperaba {expected}, se obtuvo {actual}")

			print(f"[OK] {mode}: {json.dumps(actual)}")

		print("\nLas 7 pruebas pasaron")
		return 0
	except (EngineError, ValueError, KeyError) as error:
		print(f"[ERROR] {error}", file=sys.stderr)
		if isinstance(error, EngineError) and error.diagnostics:
			print(error.diagnostics, file=sys.stderr)

		return 1


if __name__ == "__main__":
	sys.exit(main())
