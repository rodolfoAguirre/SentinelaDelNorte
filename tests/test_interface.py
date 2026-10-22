# Descripcion: comprueba los cuatro modulos de la interfaz Streamlit con el motor C++ real
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

import json
from pathlib import Path
import sys
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.scenarios import geantScenario, scenarioToJson, syntheticScenario, validateScenario


APP = str(ROOT / "app/streamlit_app.py")
PAGES = ["Misión", "Network Explorer", "Algorithm Laboratory", "Cybersecurity Console", "Scenario Manager"]
OFFICIAL_SAMPLE = "true 13\ntrue 11\nfalse\ntrue 11\ntrue 9\nfalse\n2 8\n7 12\n3 8\n"
records = []


# Abre la app y navega a una pagina
# Parametro page: nombre de la pagina en la barra lateral
# Retorno: AppTest ya ejecutado en esa pagina
def openPage(page):
	app = AppTest.from_file(APP, default_timeout=120).run()
	app.sidebar.radio[0].set_value(page).run()
	return app


# Verifica que la ejecucion no tenga excepciones
# Parametros test y app: caso de prueba y aplicacion
# Retorno: sin valor; falla si hubo excepciones
def assertClean(test, app):
	test.assertFalse(app.exception, [item.message for item in app.exception])


class InterfaceTest(unittest.TestCase):
	# Recorre las cinco paginas con el escenario base
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida render y metricas
	def testAllPagesRender(self):
		app = AppTest.from_file(APP, default_timeout=120).run()
		for page in PAGES:
			app.sidebar.radio[0].set_value(page).run()
			assertClean(self, app)
			self.assertFalse(app.error, [item.value for item in app.error])
			records.append({"page": page, "metrics": len(app.metric), "charts": len(app.get("plotly_chart"))})
		self.assertGreaterEqual(records[-3]["metrics"], 15)

	# Comprueba los resultados del laboratorio contra valores conocidos de GEANT
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida MST, TSP y flujo
	def testLaboratoryResults(self):
		app = openPage("Algorithm Laboratory")
		assertClean(self, app)
		values = {metric.label: metric.value for metric in app.metric}
		self.assertEqual(values["Costo total del árbol"], "16,246")
		self.assertEqual(values["Flujo máximo"], "160,000 Mbit/s")
		self.assertEqual(values["Método"], "Exacto · Held–Karp")

	# Comprueba que un flujo con origen igual a destino se rechaza en la interfaz
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida el mensaje de error
	def testFlowSameSourceSink(self):
		app = openPage("Algorithm Laboratory")
		source = next(box for box in app.selectbox if box.key == "labSource")
		next(box for box in app.selectbox if box.key == "labSink").set_value(source.value).run()
		assertClean(self, app)
		self.assertTrue(any("distintos" in item.value for item in app.error))

	# Reproduce la salida oficial del ejemplo del PDF en la consola
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida las nueve lineas
	def testConsoleOfficialOutput(self):
		app = openPage("Cybersecurity Console")
		assertClean(self, app)
		self.assertIn(OFFICIAL_SAMPLE.rstrip("\n"), [block.value.rstrip("\n") for block in app.code])

	# Rechaza texto no hexadecimal y un numero incorrecto de firmas
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida los mensajes de error
	def testConsoleInvalidInput(self):
		app = openPage("Cybersecurity Console")
		app.text_area(key="transmission0").set_value("ABCxyz").run()
		self.assertTrue(any("0-9 y A-F" in item.value for item in app.error))
		app.text_area(key="transmission0").set_value("ABCDEF").run()
		app.text_input[0].set_value("AB, CD").run()
		self.assertTrue(any("exactamente tres" in item.value for item in app.error))
		assertClean(self, app)

	# Crea escenarios sintetico y con fallas y verifica que se activen
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida el administrador y el explorador
	def testScenarioManagerFlow(self):
		app = openPage("Scenario Manager")
		next(button for button in app.button if button.label == "Generar red sintética").click().run()
		assertClean(self, app)
		self.assertEqual(len(app.session_state.scenarios), 2)
		self.assertTrue(app.session_state.activeScenario.startswith("Sintética 40 nodos"))
		self.assertTrue(any("creado y activado" in item.value for item in app.success))

		baseBox = next(box for box in app.selectbox if box.label == "Escenario base")
		baseBox.set_value("GÉANT base").run()
		failures = next(box for box in app.multiselect if box.label == "Enlaces fuera de servicio")
		failures.set_value([3, 29, 30]).run()
		next(button for button in app.button if button.label == "Crear escenario derivado").click().run()
		assertClean(self, app)
		self.assertEqual(len(app.session_state.scenarios), 3)
		self.assertTrue(any("componentes" in item.value for item in app.success), "Israel debe quedar aislado")

		for page in ["Network Explorer", "Algorithm Laboratory"]:
			app.sidebar.radio[0].set_value(page).run()
			assertClean(self, app)

	# Exporta e importa un escenario sin perder datos
	# Parametro self: instancia de la prueba
	# Retorno: sin valor; valida la ida y vuelta
	def testScenarioRoundTrip(self):
		for scenario in (geantScenario(), syntheticScenario(25, 1.0, 7)):
			restored = validateScenario(json.loads(scenarioToJson(scenario)))
			self.assertEqual(len(restored["nodes"]), len(scenario["nodes"]))
			self.assertEqual(restored["edges"], scenario["edges"])
			for original, copy in zip(scenario["nodes"], restored["nodes"]):
				self.assertAlmostEqual(original["x"], copy["x"], places=6)
		with self.assertRaises(ValueError):
			validateScenario({"name": "x", "nodes": [{"lon": 0, "lat": 0}], "edges": [{"u": 0, "v": 0}]})


if __name__ == "__main__":
	result = unittest.main(exit=False, verbosity=2).result
	report = {"success": result.wasSuccessful(), "tests": result.testsRun, "failures": len(result.failures),
	          "errors": len(result.errors), "method": "Streamlit AppTest con el motor C++ real", "pages": records}
	(ROOT / "results/interface_tests.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	sys.exit(0 if result.wasSuccessful() else 1)
