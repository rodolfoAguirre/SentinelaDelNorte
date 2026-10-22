# Descripcion: prepara un ZIP de fuentes para probar el autograder
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-21

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDENT_ID = "A0XXXXXX"
MAX_ZIP_BYTES = 25_000_000
MAX_FILE_COUNT = 300


# Activa el contrato web en la copia del punto de entrada
# Parametro sourcePath: archivo fuente original
# Retorno: contenido que se incluye en el ZIP
def packageSource(sourcePath):
	content = sourcePath.read_bytes()
	if sourcePath.name == "main.cpp":
		content = content.replace(b'#include "metrics.h"', b'#define SENTINELA_AUTOGRADER 1\n\n#include "metrics.h"', 1)
	return content


# Empaqueta fuentes y metadatos con una carpeta superior
# Parametro studentId: matricula o marcador del nombre del paquete
# Retorno: ruta del ZIP y resumen de verificacion
def buildPackage(studentId):
	if not re.fullmatch(r"[A-Za-z0-9_-]+", studentId):
		raise ValueError("El identificador solo permite letras, numeros, guion y guion bajo")

	sourceFiles = [ROOT / "src/main.cpp"] + sorted((ROOT / "src").glob("*.h"))
	if not sourceFiles[0].is_file() or not all(path.is_file() for path in sourceFiles):
		raise ValueError("Faltan archivos fuente del motor")

	packageName = f"{studentId}_SENTINEL_DEL_NORTE"
	outputDirectory = ROOT / "dist"
	outputDirectory.mkdir(exist_ok=True)
	archivePath = outputDirectory / f"{packageName}.zip"

	readme = (
		"# Sentinela del Norte: prueba del motor en el autograder\n\n"
		"Fuentes C++17 con un unico src/main.cpp y encabezados locales\n\n"
		"El programa lee UN objeto JSON de stdin hasta EOF y escribe UN objeto JSON en stdout. "
		"Los diagnosticos van a stderr. Se ejecuta sin argumentos para el modo JSON.\n\n"
		"Este paquete activa el contrato del autograder web 1.1.0-web con "
		"SENTINELA_AUTOGRADER. Devuelve resultados directos, sin el sobre del adaptador Python.\n\n"
		"Autores y matriculas pendientes. Sustituir el marcador del nombre del paquete "
		"y completar team.txt antes de una entrega formal.\n\n"
		"Compilacion local en MinGW: "
		"`g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic src/main.cpp -o sentinela.exe -lpsapi`\n\n"
		"En otros entornos la medicion de memoria usa una API local cuando esta disponible "
		"o devuelve null. El paquete contiene fuentes; el autograder los compila.\n\n"
	) + (ROOT / "docs/AUTOGRADER.md").read_text(encoding="utf-8")

	with zipfile.ZipFile(archivePath, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		for sourcePath in sourceFiles:
			archive.writestr(f"{packageName}/src/{sourcePath.name}", packageSource(sourcePath))

		archive.writestr(f"{packageName}/README.md", readme)
		archive.write(ROOT / "team.txt", f"{packageName}/team.txt")

	with zipfile.ZipFile(archivePath) as archive:
		entries = archive.namelist()
		if archive.testzip() is not None:
			raise ValueError("El ZIP no paso la verificacion de integridad")

		if len(entries) > MAX_FILE_COUNT or archivePath.stat().st_size > MAX_ZIP_BYTES:
			raise ValueError("El ZIP supera los limites de la pantalla del autograder")

		for sourcePath in sourceFiles:
			if archive.read(f"{packageName}/src/{sourcePath.name}") != packageSource(sourcePath):
				raise ValueError(f"La copia de {sourcePath.name} no coincide con el original")

	report = {
		"archive": archivePath.relative_to(ROOT).as_posix(),
		"sha256": hashlib.sha256(archivePath.read_bytes()).hexdigest(),
		"bytes": archivePath.stat().st_size,
		"files": len(entries),
		"entries": entries,
		"structureVerified": True,
		"officialCompatibilityVerified": False,
		"webContractVersion": "1.1.0-web",
		"entryPointDefine": "SENTINELA_AUTOGRADER",
		"studentIdPending": studentId == DEFAULT_STUDENT_ID,
		"teamFile": "team.txt",
	}

	return archivePath, report


# Genera un paquete de prueba con nombre configurable
# Parametros: ninguno
# Retorno: sin valor; guarda el ZIP y su verificacion
def main():
	argumentParser = argparse.ArgumentParser(description="Empaqueta el motor para probar el autograder")
	argumentParser.add_argument("--student-id", default=DEFAULT_STUDENT_ID)
	arguments = argumentParser.parse_args()

	archivePath, report = buildPackage(arguments.student_id)
	(ROOT / "results").mkdir(exist_ok=True)
	(ROOT / "results/autograder_package.json").write_text(
		json.dumps(report, indent=2) + "\n", encoding="utf-8",
	)

	print(f"ZIP: {archivePath}")
	print(f"Verificado: {report['files']} archivos, {report['bytes']} bytes")
	print("Contrato web 1.1.0-web activado; consulta results para las verificaciones realizadas")
	if report["studentIdPending"]:
		print("Sustituye A0XXXXXX por tu matricula y completa team.txt para la entrega formal")


if __name__ == "__main__":
	main()
