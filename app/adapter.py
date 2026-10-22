# Descripcion: conecta Python con el motor C++ mediante JSON
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-21

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any


CONTRACT_VERSION = "provisional-v1"
MAX_REQUEST_BYTES = 64_000_000
MAX_HEX_LENGTH = 2_000_000
HEX_CHARACTERS = frozenset("0123456789ABCDEF")
SUPPORTED_MODES = frozenset({
	"mst", "tsp", "max_flow", "voronoi",
	"matching", "palindrome", "common_substring", "strings",
})


class EngineError(RuntimeError):
	# Conserva un error y los diagnosticos del motor
	# Parametro self: instancia del error
	# Parametro message: descripcion para el consumidor
	# Parametro kind: categoria del fallo
	# Parametro diagnostics: texto recibido por stderr
	# Parametro returnCode: codigo de salida si hubo proceso
	# Parametro response: respuesta JSON si pudo interpretarse
	# Retorno: instancia inicializada
	def __init__(
		self,
		message: str,
		*,
		kind: str,
		diagnostics: str = "",
		returnCode: int | None = None,
		response: dict[str, Any] | None = None,
	) -> None:
		super().__init__(message)

		self.kind = kind
		self.diagnostics = diagnostics
		self.returnCode = returnCode
		self.response = response


# Rechaza numeros especiales ajenos al formato JSON
# Parametro value: literal numerico encontrado
# Retorno: sin retorno; lanza una excepcion
def rejectJsonConstant(value: str) -> None:
	raise ValueError(f"Literal JSON no permitido: {value}")


# Rechaza claves repetidas al interpretar un objeto JSON
# Parametro entries: pares de claves y valores leidos
# Retorno: objeto sin claves duplicadas
def uniqueJsonObject(entries: list[tuple[str, Any]]) -> dict[str, Any]:
	result = {}
	for key, value in entries:
		if key in result:
			raise ValueError(f"Clave JSON repetida: {key}")

		result[key] = value

	return result


# Convierte una carga de Streamlit en hexadecimal normalizado
# Parametro content: bytes obtenidos del archivo subido
# Retorno: cadena validada sin saltos de linea
def hexFromBytes(content: bytes) -> str:
	if not isinstance(content, bytes):
		raise EngineError("La carga debe proporcionarse como bytes", kind="input")

	if len(content) > MAX_REQUEST_BYTES:
		raise EngineError("El archivo supera 64 MB", kind="input")

	try:
		normalized = content.decode("ascii").replace("\r", "").replace("\n", "")
	except UnicodeDecodeError as error:
		raise EngineError("El archivo debe contener solo 0-9, A-F y saltos de linea", kind="input") from error

	if len(normalized) > MAX_HEX_LENGTH:
		raise EngineError("La secuencia supera 2000000 caracteres", kind="input")

	if any(character not in HEX_CHARACTERS for character in normalized):
		raise EngineError("El archivo debe contener solo 0-9, A-F y saltos de linea", kind="input")

	return normalized


# Decodifica diagnosticos incluso cuando el proceso falla al iniciar
# Parametro content: salida capturada del proceso
# Retorno: texto disponible para diagnostico
def diagnosticText(content: bytes | str | None) -> str:
	if isinstance(content, bytes):
		return content.decode("utf-8", errors="replace").strip()

	return content.strip() if isinstance(content, str) else ""


class EngineAdapter:
	# Configura las rutas y el tiempo maximo de ejecucion
	# Parametro self: instancia del adaptador
	# Parametro executablePath: ejecutable opcional, relativo al proyecto
	# Parametro projectRoot: raiz opcional del repositorio
	# Parametro timeoutSeconds: tiempo maximo por solicitud
	# Retorno: instancia lista para ejecutar el motor
	def __init__(
		self,
		executablePath: str | Path | None = None,
		*,
		projectRoot: str | Path | None = None,
		timeoutSeconds: float = 30.0,
	) -> None:
		if (
			isinstance(timeoutSeconds, bool)
			or not isinstance(timeoutSeconds, (int, float))
			or not math.isfinite(timeoutSeconds)
			or timeoutSeconds <= 0
		):
			raise EngineError("timeoutSeconds debe ser positivo y finito", kind="configuration")

		try:
			self.projectRoot = (
				Path(projectRoot).expanduser().resolve()
				if projectRoot is not None
				else Path(__file__).resolve().parents[1]
			)
		except (TypeError, ValueError, OSError) as error:
			raise EngineError("La raiz del proyecto no es una ruta valida", kind="configuration") from error

		if not self.projectRoot.is_dir():
			raise EngineError("No existe la raiz del proyecto", kind="configuration")

		self.timeoutSeconds = float(timeoutSeconds)
		self.executablePath = self.resolveExecutable(executablePath)

	# Localiza un ejecutable sin depender del directorio de Streamlit
	# Parametro self: instancia del adaptador
	# Parametro executablePath: ruta explicita o None para buscar
	# Retorno: ruta absoluta del ejecutable
	def resolveExecutable(self, executablePath: str | Path | None) -> Path:
		configuredPath = executablePath
		if configuredPath is None:
			configuredPath = os.environ.get("SENTINELA_EXECUTABLE") or None

		if configuredPath is not None:
			try:
				candidate = Path(configuredPath).expanduser()
				if not candidate.is_absolute():
					candidate = self.projectRoot / candidate

				candidate = candidate.resolve()
			except (TypeError, ValueError, OSError) as error:
				raise EngineError("La ruta del motor no es valida", kind="configuration") from error

			if not candidate.is_file():
				raise EngineError(f"No existe el ejecutable: {candidate}", kind="configuration")

			return candidate

		executableName = "sentinela.exe" if os.name == "nt" else "sentinela"
		candidateFolders = (
			"build", "build/Release", "build/Debug",
			"cmake-build-release", "cmake-build-debug",
		)

		for folder in candidateFolders:
			candidate = self.projectRoot / folder / executableName
			if candidate.is_file():
				return candidate.resolve()

		raise EngineError(
			"No se encontro el motor compilado; ejecuta cmake --build build "
			"o configura SENTINELA_EXECUTABLE",
			kind="configuration",
		)

	# Lee una solicitud guardada sin ejecutarla
	# Parametro self: instancia del adaptador
	# Parametro requestPath: archivo JSON relativo al proyecto o absoluto
	# Retorno: solicitud editable con mode e input
	def loadRequest(self, requestPath: str | Path) -> dict[str, Any]:
		try:
			path = Path(requestPath)
			if not path.is_absolute():
				path = self.projectRoot / path

			with path.open("rb") as requestFile:
				content = requestFile.read(MAX_REQUEST_BYTES + 1)

			if len(content) > MAX_REQUEST_BYTES:
				raise EngineError("La solicitud supera 64 MB", kind="input")

			request = json.loads(
				content.decode("utf-8"), parse_constant=rejectJsonConstant,
				object_pairs_hook=uniqueJsonObject,
			)
		except (OSError, UnicodeDecodeError, ValueError, TypeError, RecursionError) as error:
			raise EngineError(f"No se pudo leer la solicitud: {error}", kind="input") from error

		self.validateRequest(request)
		return request

	# Valida el sobre del contrato antes de iniciar el proceso
	# Parametro self: instancia del adaptador
	# Parametro request: solicitud que se enviara al motor
	# Retorno: sin valor; lanza error si el sobre es invalido
	def validateRequest(self, request: dict[str, Any]) -> None:
		if not isinstance(request, dict):
			raise EngineError("La solicitud debe ser un objeto JSON", kind="input")

		mode = request.get("mode")
		if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
			raise EngineError("El modo solicitado no esta soportado", kind="input")

		if not isinstance(request.get("input"), dict):
			raise EngineError("input debe ser un objeto JSON", kind="input")

		if "metrics" in request and not isinstance(request["metrics"], bool):
			raise EngineError("metrics debe ser un booleano", kind="input")

	# Construye una solicitud a partir del modo y sus datos
	# Parametro self: instancia del adaptador
	# Parametro mode: uno de los modos soportados
	# Parametro inputData: datos especificos del algoritmo
	# Parametro metrics: solicita mediciones internas del motor
	# Retorno: respuesta JSON completa con result
	def run(
		self,
		mode: str,
		inputData: dict[str, Any],
		*,
		metrics: bool = False,
	) -> dict[str, Any]:
		return self.runRequest({"mode": mode, "input": inputData, "metrics": metrics})

	# Ejecuta una solicitud y cierra stdin al enviar sus datos
	# Parametro self: instancia del adaptador
	# Parametro request: objeto con mode, input y metrics opcional
	# Retorno: respuesta JSON completa o excepcion EngineError
	def runRequest(self, request: dict[str, Any]) -> dict[str, Any]:
		self.validateRequest(request)

		try:
			requestBytes = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
		except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
			raise EngineError(f"La solicitud no se puede serializar: {error}", kind="input") from error

		if len(requestBytes) > MAX_REQUEST_BYTES:
			raise EngineError("La solicitud supera 64 MB", kind="input")

		try:
			process = subprocess.run(
				[str(self.executablePath)],
				input=requestBytes,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				cwd=str(self.projectRoot),
				timeout=self.timeoutSeconds,
				check=False,
				shell=False,
				creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
			)
		except subprocess.TimeoutExpired as error:
			raise EngineError(
				f"El motor supero {self.timeoutSeconds:g} segundos",
				kind="timeout",
				diagnostics=diagnosticText(error.stderr),
			) from error
		except OSError as error:
			raise EngineError(f"No se pudo iniciar el motor: {error}", kind="process") from error

		return self.decodeResponse(process, request)

	# Comprueba la respuesta y distingue errores del motor y del proceso
	# Parametro self: instancia del adaptador
	# Parametro process: proceso terminado con salida capturada
	# Parametro request: solicitud original para comprobar el modo
	# Retorno: respuesta JSON validada
	def decodeResponse(
		self,
		process: subprocess.CompletedProcess,
		request: dict[str, Any],
	) -> dict[str, Any]:
		diagnostics = diagnosticText(process.stderr)

		try:
			response = json.loads(
				process.stdout.decode("utf-8"), parse_constant=rejectJsonConstant,
				object_pairs_hook=uniqueJsonObject,
			)
		except (UnicodeDecodeError, ValueError, RecursionError) as error:
			raise EngineError(
				"El motor no produjo una respuesta JSON valida; comprueba el ejecutable y sus bibliotecas",
				kind="process" if process.returncode != 0 else "protocol",
				diagnostics=diagnostics,
				returnCode=process.returncode,
			) from error

		if (
			not isinstance(response, dict)
			or response.get("contract") != CONTRACT_VERSION
			or not isinstance(response.get("ok"), bool)
		):
			raise EngineError(
				"La respuesta no cumple el contrato provisional-v1",
				kind="protocol", diagnostics=diagnostics, returnCode=process.returncode,
			)

		if not response["ok"]:
			if process.returncode == 0 or not isinstance(response.get("error"), str):
				raise EngineError("La respuesta de error es inconsistente", kind="protocol")

			raise EngineError(
				response["error"], kind="engine", diagnostics=diagnostics,
				returnCode=process.returncode, response=response,
			)

		if process.returncode != 0:
			raise EngineError(
				"El motor termino con un codigo de salida inesperado",
				kind="process", diagnostics=diagnostics, returnCode=process.returncode,
				response=response,
			)

		if response.get("mode") != request["mode"] or not isinstance(response.get("result"), dict):
			raise EngineError("El modo o resultado de la respuesta es invalido", kind="protocol")

		if request.get("metrics", False):
			self.validateMetrics(response.get("metrics"))

		return response

	# Comprueba las mediciones opcionales sin convertir sus unidades
	# Parametro self: instancia del adaptador
	# Parametro metrics: objeto de mediciones devuelto por C++
	# Retorno: sin valor; lanza error si las mediciones son invalidas
	def validateMetrics(self, metrics: Any) -> None:
		if not isinstance(metrics, dict):
			raise EngineError("Faltan las mediciones solicitadas", kind="protocol")

		algorithmTime = metrics.get("algorithm_us")
		peakMemory = metrics.get("peak_process_bytes")
		if (
			isinstance(algorithmTime, bool)
			or not isinstance(algorithmTime, (int, float))
			or not math.isfinite(algorithmTime)
			or algorithmTime < 0
			or "peak_process_bytes" not in metrics
		):
			raise EngineError("El tiempo del algoritmo es invalido", kind="protocol")

		if peakMemory is not None and (
			isinstance(peakMemory, bool)
			or not isinstance(peakMemory, (int, float))
			or not math.isfinite(peakMemory)
			or peakMemory < 0
		):
			raise EngineError("La medicion de memoria es invalida", kind="protocol")
