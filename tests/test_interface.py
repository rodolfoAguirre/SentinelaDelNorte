# Descripcion: comprueba formularios, resultados y metricas de Streamlit
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-22

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".venv-deps").is_dir():
	sys.path.insert(0, str(ROOT / ".venv-deps"))

from streamlit.testing.v1 import AppTest


# Recorre las vistas y verifica el manejo de un caso invalido
# Parametros: ninguno
# Retorno: sin valor; falla si faltan resultados o metricas
def main():
	app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60).run()
	assert not app.exception
	records = []
	for name in app.sidebar.selectbox[0].options:
		app.sidebar.selectbox[0].set_value(name).run()
		app.button[0].click().run()
		assert not app.exception and not app.error
		assert len(app.metric) >= 3
		records.append({"view": name, "metrics": [{"label": item.label, "value": item.value} for item in app.metric]})
		print(f"[OK] {name}")
	app.sidebar.selectbox[0].set_value("Capacidad de transporte · Flujo máximo").run()
	app.main.selectbox[1].set_value(app.main.selectbox[0].value)
	app.button[0].click().run()
	assert app.error and not app.exception
	report = {"success": True, "method": "Streamlit AppTest with real C++ engine", "views": records, "invalidSourceSinkHandled": True}
	(ROOT / "results/interface_tests.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
	main()
