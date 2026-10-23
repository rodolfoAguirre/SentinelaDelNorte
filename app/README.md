# Consumir el motor desde Streamlit

La [documentación de la app y su interfaz](../docs/APP_UI.md) explica navegación, controles, mapas, animación, resultados, métricas, instalación y archivos del UI.

La primera interfaz está implementada en `app/streamlit_app.py` y consume el motor C++ mediante `app/adapter.py`. Incluye los siete algoritmos y un análisis conjunto de cadenas, resultados, diagramas, tablas, tiempo C++, tiempo total, memoria y descarga JSON. Instala `app/requirements.txt` y ejecuta `python -m streamlit run app/streamlit_app.py` desde la raíz.

La visualización geográfica usa Pydeck (`app/visuals.py`) con fondo CARTO, coordenadas originales de nodos y transformación inversa de la proyección para las celdas. Admite selección de centrales, detalles al pasar el cursor, zoom y recorrido TSP por pasos. El diagrama SVG sigue disponible en otra pestaña. El fondo de mapa requiere internet; los cálculos se mantienen en el motor local. El tema oscuro está en `.streamlit/config.toml` y los estilos comunes en `applyTheme`.

```text
Widgets de Streamlit
        |
        v
EngineAdapter.run(mode, inputData)
        |
        v
Ejecutable C++: JSON por stdin -> algoritmos -> JSON por stdout
        |
        v
Diccionario Python con result -> tablas, mapas y graficas
```

Cada llamada inicia un proceso, envía una solicitud, cierra stdin, recoge la respuesta y termina. El adaptador comprueba el contrato y transforma fallos en `EngineError`. Los siete algoritmos se ejecutan en C++. No hay que configurar endpoints HTTP para usar esta integración.

## 1. Preparar el proyecto

Trabaja desde la **raíz del repositorio**, donde está `CMakeLists.txt`. Para esta integración usa Python **3.10 o superior**. Para compilar el motor necesitas C++17 y CMake >=3.16.

En CLion, compila el target `sentinela` con MinGW. Desde terminal, con compilador, CMake y Ninja en PATH:

```powershell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

El adaptador solo usa la biblioteca estándar: **puedes probarlo antes de instalar Streamlit**.

```powershell
python -c "from app import EngineAdapter; a = EngineAdapter(); r = a.runRequest(a.loadRequest('examples/mst.input.json')); print(r['result'])"
```

Debe imprimir un resultado con `connected: True`, `total_cost: 5` y `edge_indices: [0, 1]`.

Para desarrollar la interfaz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements.txt
```

En Linux/macOS utiliza `.venv/bin/python`. El ejecutable C++ debe corresponder al sistema y arquitectura donde corre el **servidor Python de Streamlit**; el navegador de los usuarios no necesita compilador.

## 2. Primera llamada

Para probar los siete algoritmos con un solo comando desde la raíz:

```powershell
python prueba_algoritmos.py
```

El script ejecuta casos pequeños de `examples/`, compara sus resultados con valores conocidos y muestra una línea `[OK]` por algoritmo. Al terminar debe decir `Las 7 pruebas pasaron`. Usa el adaptador y el motor C++ real; no requiere Streamlit ni paquetes de Python adicionales. Si modificas las entradas de esos ejemplos, sus resultados esperados también pueden cambiar.

```python
from app import EngineAdapter, EngineError

adapter = EngineAdapter(timeoutSeconds=30)

inputData = {
	"n": 3,
	"edges": [
		{"u": 0, "v": 1, "cost": 2},
		{"u": 1, "v": 2, "cost": 3},
		{"u": 0, "v": 2, "cost": 9},
	],
}

try:
	response = adapter.run("mst", inputData)
	print(response["result"]["total_cost"])
except EngineError as error:
	print(error.kind, str(error))
	print(error.diagnostics)
```

La respuesta completa del ejemplo es:

```json
{
  "ok": true,
  "contract": "provisional-v1",
  "mode": "mst",
  "result": {
    "connected": true,
    "components": 1,
    "edge_indices": [0, 1],
    "total_cost": 5,
    "algorithm": "kruskal"
  }
}
```

**`run` devuelve el sobre completo**, no solamente `result`. Una llamada correcta devuelve `ok:true`; los fallos lanzan `EngineError`.

## 3. API y configuración

| Llamada | Uso |
|---|---|
| `EngineAdapter()` | Busca el motor en las carpetas habituales |
| `EngineAdapter(executablePath="build/sentinela.exe")` | Usa un ejecutable explícito |
| `EngineAdapter(projectRoot="C:/ruta/Midterm")` | Configura la raíz del proyecto |
| `EngineAdapter(timeoutSeconds=60)` | Cambia el máximo de segundos por solicitud |
| `adapter.run(mode, inputData, metrics=False)` | Construye y ejecuta una solicitud |
| `adapter.loadRequest("examples/mst.input.json")` | Lee y valida una solicitud sin ejecutarla |
| `adapter.runRequest(request)` | Ejecuta un objeto con `mode`, `input` y `metrics` opcional |
| `hexFromBytes(upload.getvalue())` | Valida y normaliza un archivo subido |

`adapter.projectRoot` y `adapter.executablePath` son rutas absolutas `Path`. El adaptador no modifica `inputData`, no cambia el directorio global de Python y no conserva resultados entre llamadas.

Prioridad para encontrar el ejecutable:

1. Argumento `executablePath`
2. Variable de entorno `SENTINELA_EXECUTABLE`
3. Primera coincidencia en `build`, `build/Release`, `build/Debug`, `cmake-build-release`, `cmake-build-debug`

Busca `sentinela.exe` en Windows y `sentinela` en otros sistemas. Si hay varias compilaciones, utiliza una ruta explícita para escoger una. El adaptador no compila automáticamente.

```powershell
$env:SENTINELA_EXECUTABLE = "C:\ruta\con espacios\sentinela.exe"
```

Las rutas relativas de ejecutable, solicitudes y archivos dentro de las solicitudes se interpretan respecto a **`projectRoot`**. Por defecto es la raíz que contiene esta carpeta `app`, independientemente de la carpeta desde la que se lance Streamlit.

## 4. Qué enviar y qué dibujar

Construye `inputData` según la pantalla y llama a `adapter.run(mode, inputData)`:

| `mode` | Campos de `inputData` | Campos principales de `response["result"]` |
|---|---|---|
| `mst` | `n`, `edges:[{u,v,cost}]` | `connected`, `components`, `edge_indices`, `total_cost` |
| `tsp` | `n`, `edges:[{u,v,distance}]`, `selected:[indices]` | `tour`, `physical_nodes`, `physical_edge_indices`, `total_distance`, `exact` |
| `max_flow` | `n`, `edges:[{u,v,capacity}]`, `source`, `sink`, `directed` | `value`, `flows:[{edge_index,flow}]`, `source_side` |
| `voronoi` | `sites:[[x,y]]`, `domain:[xmin,ymin,xmax,ymax]`, `queries:[[x,y]]` opcional | `cells`, `nearest` |
| `matching` | `transmissions:[texto1,texto2]`, `patterns:[firma1,firma2,firma3]` | `matches` |
| `palindrome` | `transmissions:[texto1,texto2]` | `palindromes` |
| `common_substring` | `transmissions:[texto1,texto2]` | `common` |
| `strings` | Dos transmisiones y tres firmas | `matches`, `palindromes`, `common` |

Cada modo tiene entrada completa y respuesta real en `../examples/`. Para probar cualquiera antes de construir sus widgets:

```python
from app import EngineAdapter

adapter = EngineAdapter()
mode = "tsp"
request = adapter.loadRequest(f"examples/{mode}.input.json")
response = adapter.runRequest(request)
print(response["result"])
```

Para trabajar con GÉANT, hay solicitudes en `data/derived/`: `mst.input.json`, `tsp.input.json`, `max_flow.input.json` y `voronoi.input.json`. Son escenarios de trabajo identificados, con algunos parámetros sintéticos. Puedes modificar una solicitud antes de ejecutarla:

```python
request = adapter.loadRequest("data/derived/tsp.input.json")
request["input"]["selected"] = [0, 2, 4]
response = adapter.runRequest(request)
```

Se preparan con `python tools/prepare_data.py`. El adaptador no convierte automáticamente CSV/XML.

### Reglas de interpretación

- Nodos y enlaces usan índices **base 0**. `edge_indices` y `edge_index` apuntan a posiciones de la lista `edges` enviada: conserva su orden al dibujar. `data/derived/nodes.csv` relaciona índices con IDs originales.
- MST desconectado devuelve un bosque con `connected:false`; es un resultado válido.
- En TSP, `tour` indica el orden de servicio; `physical_nodes` y `physical_edge_indices` indican el recorrido por enlaces. Puede repetir intermedios. Muestra `exact` para distinguir óptimo de heurístico. Opcionales: `exact_limit` (predeterminado 16, máximo 18) y `max_passes` (predeterminado 100).
- En flujo no dirigido, un flujo negativo indica dirección v→u. La capacidad limita el valor absoluto del flujo neto. El flujo cero es válido. No uses demandas como capacidades.
- Voronoi recibe coordenadas planas, todas en la misma unidad. `cells[i]` pertenece a `sites[i]`; `nearest` contiene índices. Las celdas vacías por sitios duplicados son válidas.
- En cadenas, las posiciones son **base 1** y los finales inclusivos sobre el texto sin CR/LF. Para resaltar: `normalizedText[start - 1:end]`; si `length` es cero, no resaltes un intervalo.
- Una firma ausente devuelve `found:false, position:0`. Los seis `matches` son primero las tres firmas de T1 y luego las tres de T2. Los dos palíndromos siguen el orden de transmisiones.
- Empates de cadenas: menor inicio; en subcadena común se prioriza T1 y luego T2. Patrón vacío coincide en posición 1. Intervalos vacíos usan 0,0.

Límites actuales: 64 MB por solicitud serializada, hasta 2000 nodos y 200000 enlaces, TSP de hasta 500 centrales, Voronoi de hasta 1000 sitios y hasta 2000000 caracteres normalizados por secuencia. El contrato detallado está en [CONTRACT.md](../docs/CONTRACT.md).

## 5. Archivos subidos en Streamlit

Un `UploadedFile` vive en Python. **Su propiedad `name` no es una ruta al archivo en el servidor.** Lee sus bytes y envía el contenido:

```python
from app import EngineAdapter, hexFromBytes

adapter = EngineAdapter()
inputData = {
	"transmissions": [
		hexFromBytes(transmission1.getvalue()),
		hexFromBytes(transmission2.getvalue()),
	],
	"patterns": [
		hexFromBytes(mcode1.getvalue()),
		hexFromBytes(mcode2.getvalue()),
		hexFromBytes(mcode3.getvalue()),
	],
}

response = adapter.run("strings", inputData)
```

Este fragmento supone que los cinco widgets ya devolvieron archivos: verifica que no sean `None`. `hexFromBytes` elimina CR/LF y valida `0–9 A–F`. Rechaza espacios, tabuladores, minúsculas y BOM; no convierte silenciosamente a mayúsculas. Un archivo vacío produce una cadena vacía conforme al contrato provisional.

Para archivos ya presentes en el servidor se acepta `{"file":"data/synthetic/transmission1.txt"}` en lugar del texto. Los ejemplos sintéticos **no son transmisiones ni firmas oficiales**.

## 6. Ejemplo mínimo para la futura pantalla

La interfaz actual está en `app/streamlit_app.py`. Este fragmento reducido sirve como ejemplo de integración para desarrollar otras pantallas:

```python
import streamlit as st

from app import EngineAdapter, EngineError


st.title("Sentinela del Norte")

try:
	adapter = EngineAdapter(timeoutSeconds=30)
except EngineError as error:
	st.error(str(error))
	st.stop()

with st.form("algorithmForm"):
	mode = st.selectbox("Algoritmo", [
		"mst", "tsp", "max_flow", "voronoi",
		"matching", "palindrome", "common_substring", "strings",
	])
	submitted = st.form_submit_button("Ejecutar ejemplo")

if submitted:
	try:
		request = adapter.loadRequest(f"examples/{mode}.input.json")
		request["metrics"] = True

		with st.spinner("Calculando..."):
			response = adapter.runRequest(request)

		st.session_state["lastResponse"] = response
		st.session_state["lastRequest"] = request
		st.session_state["engineError"] = None
	except EngineError as error:
		st.session_state["lastResponse"] = None
		st.session_state["engineError"] = str(error)

if st.session_state.get("engineError"):
	st.error(st.session_state["engineError"])

if st.session_state.get("lastResponse") is not None:
	response = st.session_state["lastResponse"]
	st.caption(f"Último resultado: {response['mode']}")
	st.json(response["result"])
	st.metric("Tiempo del algoritmo en microsegundos", response["metrics"]["algorithm_us"])
```

Lánzalo desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

Invoca el motor al pulsar un botón o enviar un formulario. Streamlit vuelve a ejecutar el script al interactuar con widgets; el formulario agrupa parámetros y `session_state` conserva el resultado, identificado con la solicitud que lo produjo. El adaptador no aplica caché: cada llamada vuelve a calcular.

Referencias oficiales: [formularios](https://docs.streamlit.io/develop/concepts/architecture/forms), [carga de archivos](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) y [estado de sesión](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).

## 7. Errores y mediciones

| `error.kind` | Significado | Qué revisar |
|---|---|---|
| `configuration` | Rutas o timeout inválidos | Compilación y configuración |
| `input` | Sobre, serialización, archivo JSON o carga hexadecimal inválidos | Datos de los widgets |
| `engine` | El motor respondió `ok:false` | Mensaje de validación del algoritmo |
| `timeout` | Se agotó el tiempo configurado | Tamaño del caso y presupuesto |
| `process` | El proceso no arrancó o terminó de forma anormal | Sistema, permisos y bibliotecas |
| `protocol` | La respuesta no cumple el contrato | Versiones del adaptador y motor |

`str(error)` contiene el mensaje. `error.diagnostics` conserva stderr cuando está disponible; `error.returnCode` y `error.response` proporcionan detalles cuando se pudieron obtener. En timeout, `subprocess.run` termina y espera al proceso antes de propagar el error. El transporte usa UTF-8, argumentos como lista y `shell=False`.

Ausencia de firma, bosque desconectado o flujo cero son resultados válidos, no fallos de comunicación.

```python
response = adapter.run("mst", inputData, metrics=True)
algorithmMicroseconds = response["metrics"]["algorithm_us"]
peakProcessBytes = response["metrics"]["peak_process_bytes"]
```

`algorithm_us` mide el cálculo C++ y su preparación interna, excluyendo arranque, JSON y transporte. `peak_process_bytes` es el pico del proceso completo hasta antes de imprimir JSON y puede ser `None`. No lo presentes como memoria exclusiva del algoritmo ni como tiempo total de respuesta de la app.

## 8. Pruebas y distribución

```powershell
python tests/test_adapter.py build/sentinela.exe
ctest --test-dir build -R adapter --output-on-failure
```

Si el test no está registrado, vuelve a configurar CMake con Python >=3.10; se puede seleccionar con `-DPython3_EXECUTABLE=C:/ruta/python.exe`. En Linux/macOS usa `build/sentinela`. La evidencia se guarda en `results/adapter_tests.json`.

Las 14 pruebas cubren los ocho modos con el motor real, rutas desde otra carpeta, archivos subidos, errores de C++, recuperación y configuración. Los timeouts y fallos de proceso/protocolo se simulan para reproducirlos. La interfaz se verifica adicionalmente con `python tests/test_interface.py`, que recorre sus ocho vistas usando Streamlit AppTest y el motor real, comprueba métricas y el manejo de un origen igual al destino.

Para Windows/MinGW conserva juntos `sentinela.exe`, `libstdc++-6.dll`, `libgcc_s_seh-1.dll` y `libwinpthread-1.dll`. CMake copia las DLL junto al binario. Incluye también `app/`, los datos y los ejemplos que use la interfaz. Para otro sistema hay que compilar el motor en ese entorno y configurar el ejecutable correspondiente.

## 9. Qué sigue pendiente

La primera versión incluye formularios, selección de centrales y extremos de flujo, carga de transmisiones, diagramas, tablas y métricas. Queda ampliar escenarios oficiales, validar distribución en otras computadoras y refinar las visualizaciones.

Siguen pendientes transmisiones, firmas, escenarios y contrato oficial. Los datos derivados contienen supuestos identificados en [data/README.md](../data/README.md). Si cambia el contrato, adapta `src/protocol.h`, `app/adapter.py` y sus pruebas. `CONTRACT_VERSION` detecta respuestas de versiones incompatibles.
