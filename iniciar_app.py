# Descripcion: inicia la interfaz Streamlit desde cualquier carpeta
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import os
from pathlib import Path
import socket
import sys


# Localiza dependencias e inicia el servidor de la app
# Parametros: ninguno
# Retorno: codigo de salida de Streamlit
def main():
	projectRoot = Path(__file__).resolve().parent
	os.chdir(projectRoot)
	localDependencies = projectRoot / ".venv-deps"
	if localDependencies.is_dir():
		sys.path.insert(0, str(localDependencies))
	try:
		from streamlit.web import cli
	except ImportError:
		print("Instala las dependencias con: python -m pip install -r app/requirements.txt")
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
