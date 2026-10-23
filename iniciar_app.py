# Descripcion: inicia la interfaz Streamlit desde cualquier carpeta
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

from pathlib import Path
import socket
import subprocess
import sys
import sysconfig


# Localiza dependencias e inicia el servidor de la app
# Parametros: ninguno
# Retorno: codigo de salida de Streamlit
def main():
	projectRoot = Path(__file__).resolve().parent
	venvPython = projectRoot / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
	if venvPython.is_file() and sys.prefix == sys.base_prefix:
		print("Usando el entorno Python del proyecto (.venv)", flush=True)
		return subprocess.call([str(venvPython), str(Path(__file__).resolve())])
	localDependencies = projectRoot / ".venv-deps"
	extensionSuffix = sysconfig.get_config_var("EXT_SUFFIX")
	numpyCore = localDependencies / "numpy/_core"
	compatible = extensionSuffix and any(path.name.endswith(extensionSuffix) for path in numpyCore.glob("_multiarray_umath*"))
	if localDependencies.is_dir() and compatible and sys.prefix == sys.base_prefix:
		sys.path.insert(0, str(localDependencies))
	try:
		import numpy
		import pandas
		import pydeck
		from streamlit.web import cli
	except ImportError as error:
		print(f"No se pudieron cargar las dependencias de Python {sys.version_info.major}.{sys.version_info.minor}: {error}")
		print(f'Instala las dependencias para este interprete: "{sys.executable}" -m pip install -r "{projectRoot / "app/requirements.txt"}"')
		return 1
	port = 8501
	available = False
	while port <= 8510 and not available:
		try:
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
				probe.bind(("127.0.0.1", port))
			available = True
		except OSError:
			port += 1
	if not available:
		print("No hay un puerto disponible entre 8501 y 8510")
		return 1
	print(f"Iniciando Sentinela en http://127.0.0.1:{port}", flush=True)
	print("Conserva esta terminal abierta mientras uses la app", flush=True)
	sys.argv = [
		"streamlit", "run", str(projectRoot / "app/streamlit_app.py"),
		"--global.developmentMode=false", "--server.address=127.0.0.1",
		f"--server.port={port}", "--browser.serverAddress=127.0.0.1",
		f"--browser.serverPort={port}", "--server.headless=true",
		"--browser.gatherUsageStats=false",
	]
	return cli.main()


if __name__ == "__main__":
	sys.exit(main())
