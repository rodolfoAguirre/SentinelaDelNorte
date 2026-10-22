# Verifica la integracion Python con el motor C++
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-21

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
EXE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else ROOT / "build/sentinela.exe"
sys.path.insert(0, str(ROOT))

from app import EngineAdapter, EngineError, hexFromBytes
from app.adapter import CONTRACT_VERSION


# Construye una respuesta de proceso para probar fallos de integracion
# Parametro response: objeto simulado del motor
# Parametro returnCode: codigo de salida simulado
# Retorno: proceso terminado con JSON serializado
def completedResponse(response, returnCode=0):
	return subprocess.CompletedProcess(
		[str(EXE)], returnCode, json.dumps(response).encode("utf-8"), b"diagnostic",
	)


class AdapterTest(unittest.TestCase):
	# Configura un adaptador real y una solicitud pequena
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; prepara los datos de prueba
	def setUp(self):
		self.adapter = EngineAdapter(EXE, projectRoot=ROOT)
		self.request = json.loads((ROOT / "examples/mst.input.json").read_text())
		self.expected = json.loads((ROOT / "examples/mst.output.json").read_text())

	# Contrasta los ocho modos con respuestas guardadas del motor real
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si alguna respuesta cambia
	def testRealExamples(self):
		paths = sorted((ROOT / "examples").glob("*.input.json"))
		self.assertEqual(len(paths), 8)
		for path in paths:
			with self.subTest(mode=path.name):
				request = self.adapter.loadRequest(path)
				expected = json.loads(path.with_name(path.name.replace(".input.", ".output.")).read_text())
				self.assertEqual(self.adapter.runRequest(request), expected)

	# Comprueba la API breve y las mediciones del motor real
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si falta un resultado o cambia la entrada
	def testRunAndMetrics(self):
		inputData = self.request["input"]
		original = copy.deepcopy(inputData)
		response = self.adapter.run("mst", inputData, metrics=True)

		self.assertEqual(response["result"], self.expected["result"])
		self.assertEqual(response["contract"], CONTRACT_VERSION)
		self.assertGreaterEqual(response["metrics"]["algorithm_us"], 0)
		self.assertIn("peak_process_bytes", response["metrics"])
		self.assertEqual(inputData, original)

	# Verifica archivos relativos aun desde otra carpeta de trabajo
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si las rutas dependen de la terminal
	def testIndependentWorkingDirectory(self):
		previousDirectory = Path.cwd()
		with tempfile.TemporaryDirectory() as folder:
			try:
				os.chdir(folder)
				adapter = EngineAdapter(EXE)
				request = adapter.loadRequest("data/synthetic/strings.input.json")
				response = adapter.runRequest(request)
			finally:
				os.chdir(previousDirectory)

		self.assertEqual(response["result"]["matches"][0]["position"], 13)
		self.assertEqual(response["result"]["common"]["length"], 6)

	# Comprueba cargas de archivos y posiciones normalizadas
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si se modifican las reglas hexadecimales
	def testUploadedHex(self):
		firstText = hexFromBytes(b"AABCDCBA\r\n12FFABBA\n")
		secondText = hexFromBytes(b"00BCDCBAFFABBA77")
		response = self.adapter.run("strings", {
			"transmissions": [firstText, secondText],
			"patterns": ["ABBA", "FF", "DEAD"],
		})

		self.assertEqual(response["result"]["palindromes"][0], {"start": 2, "end": 8, "length": 7})
		self.assertEqual(hexFromBytes(b"\r\n"), "")
		for invalid in (b"abc", b"AB CD", b"AB\tCD", b"\xef\xbb\xbfAB", "AB", b"G"):
			with self.subTest(invalid=invalid), self.assertRaises(EngineError) as raised:
				hexFromBytes(invalid)

			self.assertEqual(raised.exception.kind, "input")

		with self.assertRaises(EngineError):
			hexFromBytes(b"A" * 2_000_001)

	# Conserva el error del motor y permite otra solicitud despues
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si se pierde el diagnostico del motor
	def testRealEngineErrorAndRecovery(self):
		with self.assertRaises(EngineError) as raised:
			self.adapter.run("mst", {"n": 0, "edges": []})

		error = raised.exception
		self.assertEqual(error.kind, "engine")
		self.assertEqual(error.returnCode, 1)
		self.assertFalse(error.response["ok"])
		self.assertIn("Graph limits", str(error))
		self.assertIn("sentinela:", error.diagnostics)
		self.assertEqual(self.adapter.runRequest(self.request), self.expected)

	# Rechaza sobres invalidos antes de lanzar procesos
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si se ejecuta una solicitud invalida
	def testInputValidation(self):
		invalidRequests = [
			None, [], {}, {"mode": [], "input": {}},
			{"mode": "unknown", "input": {}}, {"mode": "mst", "input": []},
			{"mode": "mst", "input": {}, "metrics": "true"},
			{"mode": "mst", "input": {"cost": float("nan")}},
			{"mode": "mst", "input": {"values": {1, 2}}},
		]

		with patch("app.adapter.subprocess.run") as runProcess:
			for request in invalidRequests:
				with self.subTest(request=request), self.assertRaises(EngineError) as raised:
					self.adapter.runRequest(request)

				self.assertEqual(raised.exception.kind, "input")
			runProcess.assert_not_called()

		with patch("app.adapter.MAX_REQUEST_BYTES", 10), self.assertRaises(EngineError):
			self.adapter.runRequest(self.request)

	# Rechaza rutas y tiempos de espera invalidos
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si acepta una configuracion invalida
	def testConfigurationValidation(self):
		for timeout in (0, -1, True, float("nan"), float("inf"), "30"):
			with self.subTest(timeout=timeout), self.assertRaises(EngineError) as raised:
				EngineAdapter(EXE, timeoutSeconds=timeout)

			self.assertEqual(raised.exception.kind, "configuration")

		with self.assertRaises(EngineError):
			EngineAdapter("missing-sentinela.exe", projectRoot=ROOT)

		with self.assertRaises(EngineError):
			EngineAdapter(EXE, projectRoot=ROOT / "missing-root")

	# Comprueba busqueda automatica y prioridad de rutas explicitas
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si cambia la prioridad documentada
	def testExecutableDiscovery(self):
		name = "sentinela.exe" if os.name == "nt" else "sentinela"
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			target = root / "build/Release" / name
			target.parent.mkdir(parents=True)
			target.touch()
			with patch.dict(os.environ, {"SENTINELA_EXECUTABLE": ""}):
				self.assertEqual(EngineAdapter(projectRoot=root).executablePath, target.resolve())

			with patch.dict(os.environ, {"SENTINELA_EXECUTABLE": str(EXE)}):
				self.assertEqual(EngineAdapter(projectRoot=root).executablePath, EXE)
				self.assertEqual(
					EngineAdapter(target.relative_to(root), projectRoot=root).executablePath,
					target.resolve(),
				)

			target.unlink()
			with patch.dict(os.environ, {"SENTINELA_EXECUTABLE": ""}), self.assertRaises(EngineError):
				EngineAdapter(projectRoot=root)

	# Comprueba el cierre de stdin y las opciones del proceso
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si cambia el transporte esperado
	def testProcessTransport(self):
		with patch("app.adapter.subprocess.run", return_value=completedResponse(self.expected)) as runProcess:
			self.assertEqual(self.adapter.runRequest(self.request), self.expected)

		options = runProcess.call_args.kwargs
		self.assertFalse(options["shell"])
		self.assertEqual(options["cwd"], str(ROOT))
		self.assertEqual(options["timeout"], 30.0)
		self.assertEqual(json.loads(options["input"]), self.request)
		self.assertIsInstance(options["input"], bytes)

	# Conserva diagnosticos en un tiempo de espera agotado
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si no se propaga la categoria timeout
	def testTimeout(self):
		failure = subprocess.TimeoutExpired([str(EXE)], 30, stderr=b"partial diagnostic")
		with patch("app.adapter.subprocess.run", side_effect=failure), self.assertRaises(EngineError) as raised:
			self.adapter.runRequest(self.request)

		self.assertEqual(raised.exception.kind, "timeout")
		self.assertEqual(raised.exception.diagnostics, "partial diagnostic")

	# Distingue fallos del sistema al iniciar o terminar el proceso
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si el error se confunde con el algoritmo
	def testProcessFailure(self):
		with patch("app.adapter.subprocess.run", side_effect=OSError("missing runtime")):
			with self.assertRaises(EngineError) as raised:
				self.adapter.runRequest(self.request)

		self.assertEqual(raised.exception.kind, "process")
		process = subprocess.CompletedProcess([str(EXE)], 123, b"", b"runtime unavailable")
		with patch("app.adapter.subprocess.run", return_value=process), self.assertRaises(EngineError) as raised:
			self.adapter.runRequest(self.request)

		self.assertEqual(raised.exception.returnCode, 123)
		self.assertEqual(raised.exception.kind, "process")
		self.assertEqual(raised.exception.diagnostics, "runtime unavailable")

	# Rechaza respuestas corruptas o incompatibles
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si acepta un sobre incorrecto
	def testInvalidResponses(self):
		responses = [
			[], {**self.expected, "contract": "other"}, {**self.expected, "ok": 1},
			{**self.expected, "mode": "tsp"}, {**self.expected, "result": []},
			{"contract": CONTRACT_VERSION, "ok": False, "error": "invalid"},
		]
		for response in responses:
			with self.subTest(response=response):
				with patch("app.adapter.subprocess.run", return_value=completedResponse(response)):
					with self.assertRaises(EngineError) as raised:
						self.adapter.runRequest(self.request)

				self.assertEqual(raised.exception.kind, "protocol")

		for content in (b"bad json", b"{}{}", b"\xff", b'{"x":NaN}', b'{"ok":true,"ok":false}'):
			process = subprocess.CompletedProcess([str(EXE)], 0, content, b"")
			with patch("app.adapter.subprocess.run", return_value=process), self.assertRaises(EngineError) as raised:
				self.adapter.runRequest(self.request)

			self.assertEqual(raised.exception.kind, "protocol")

		with patch("app.adapter.subprocess.run", return_value=completedResponse(self.expected, 2)):
			with self.assertRaises(EngineError) as raised:
				self.adapter.runRequest(self.request)

		self.assertEqual(raised.exception.kind, "process")

	# Valida la presencia y las unidades de las mediciones opcionales
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si acepta tiempos o memoria invalidos
	def testMetricsValidation(self):
		invalidMetrics = [
			None, {}, {"algorithm_us": True, "peak_process_bytes": 10},
			{"algorithm_us": -1, "peak_process_bytes": None},
			{"algorithm_us": 1, "peak_process_bytes": -1},
			{"algorithm_us": 1, "peak_process_bytes": False},
		]

		for metrics in invalidMetrics:
			response = {**self.expected, "metrics": metrics}
			with patch("app.adapter.subprocess.run", return_value=completedResponse(response)):
				with self.assertRaises(EngineError):
					self.adapter.run("mst", self.request["input"], metrics=True)

		response = {**self.expected, "metrics": {"algorithm_us": 1.5, "peak_process_bytes": None}}
		with patch("app.adapter.subprocess.run", return_value=completedResponse(response)):
			self.assertEqual(self.adapter.run("mst", self.request["input"], metrics=True), response)

	# Rechaza archivos ausentes, JSON invalido y claves repetidas
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; falla si acepta solicitudes corruptas
	def testRequestFiles(self):
		with self.assertRaises(EngineError):
			self.adapter.loadRequest("missing-request.json")

		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / "request.json"
			for content in (b"[]", b"not-json", b"\xff", b'{"mode":"mst","mode":"tsp"}'):
				path.write_bytes(content)
				with self.subTest(content=content), self.assertRaises(EngineError) as raised:
					self.adapter.loadRequest(path)

				self.assertEqual(raised.exception.kind, "input")


if __name__ == "__main__":
	started = time.perf_counter()
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTest)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	report = {
		"success": result.wasSuccessful(),
		"tests": result.testsRun,
		"failures": len(result.failures),
		"errors": len(result.errors),
		"elapsedSeconds": time.perf_counter() - started,
		"executable": str(EXE),
		"executableSha256": hashlib.sha256(EXE.read_bytes()).hexdigest(),
		"adapterSha256": hashlib.sha256((ROOT / "app/adapter.py").read_bytes()).hexdigest(),
		"coverage": [
			"eight real engine modes", "real engine errors", "relative file paths",
			"uploaded hex", "configuration", "timeouts", "process failures", "protocol validation",
		],
	}
	(ROOT / "results").mkdir(exist_ok=True)
	(ROOT / "results/adapter_tests.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

	sys.exit(0 if result.wasSuccessful() else 1)
