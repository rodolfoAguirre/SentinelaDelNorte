# Sentinela del Norte

Proyecto académico de análisis de redes y transmisiones mediante siete algoritmos. Permite calcular conexiones de menor costo, rutas entre centrales, flujo máximo, regiones de proximidad y coincidencias en textos hexadecimales.

El cálculo se realiza en **C++17**. Un adaptador en **Python** permite consumirlo desde la futura interfaz de **Streamlit**, sin reescribir los algoritmos ni montar un servidor HTTP.

## Estado del proyecto

| Componente | Estado |
|---|---|
| Motor C++ con los siete algoritmos | Implementado y probado |
| Comunicación mediante JSON | Implementada |
| Adaptador Python para la app | Implementado y probado |
| Ejemplos y prueba sencilla desde Python | Disponibles |
| Preparación de datos GÉANT | Implementada, con supuestos documentados |
| Integración con el autograder web | **100 puntos obtenidos**, según la corrida confirmada por el equipo |
| Pantallas y visualizaciones de Streamlit | Primera versión implementada |
| Instalador y distribución de la app | Pendientes |

La interfaz está implementada en `app/streamlit_app.py`: ejecuta los siete algoritmos, presenta resultados, diagramas, tablas y métricas, y permite descargar cada ejecución en JSON. También puedes utilizar Python o la terminal.

El resultado del autograder corresponde al contrato de ese evaluador. La interfaz completa y el funcionamiento en otros sistemas operativos requieren sus propias pruebas.

## Qué problema resuelve

El proyecto combina dos tipos de información:

- **Una red:** nodos que representan centrales o ubicaciones, enlaces entre ellas y valores de costo, distancia o capacidad
- **Transmisiones:** secuencias de caracteres hexadecimales y firmas que se buscan dentro de ellas

Los algoritmos responden preguntas específicas sobre esos datos:

| Función | Pregunta que responde | Algoritmo utilizado |
|---|---|---|
| Árbol de expansión mínima, MST | ¿Qué enlaces conectan todos los nodos con el menor costo total? | Kruskal |
| Recorrido de centrales, TSP | ¿En qué orden visitar las centrales seleccionadas y regresar al origen? | Held–Karp para casos pequeños; vecino más cercano y 2-opt para casos grandes |
| Flujo máximo | ¿Cuánto flujo puede pasar desde un origen hasta un destino con las capacidades dadas? | Dinic |
| Regiones de Voronoi | ¿Qué zona del dominio está más cerca de cada central? | Intersección de semiplanos |
| Búsqueda de firmas | ¿Dónde aparece por primera vez cada firma en cada transmisión? | KMP |
| Palíndromo más largo | ¿Cuál es el fragmento más largo que se lee igual en ambos sentidos? | Manacher |
| Subcadena común más larga | ¿Cuál es el fragmento continuo más largo compartido por dos transmisiones? | Autómata de sufijos |

Una subcadena es un fragmento **continuo**. Encontrar una firma indica una coincidencia de texto; por sí solo no demuestra un ataque real. El proyecto no captura tráfico en vivo ni funciona como un sistema de detección desplegado en una red.

Si la red está desconectada, MST devuelve un bosque e informa que no todos los nodos están conectados. En TSP, los casos grandes usan una heurística: producen una ruta válida, pero no garantizan la mejor ruta posible.

## Cómo se conectan las partes

```text
Usuario
  |
  v
Interfaz Streamlit                  Implementada
  |
  v
Adaptador Python: app/adapter.py     Implementado
  | envía una solicitud JSON
  v
Motor C++: sentinela                 Implementado
  | ejecuta el algoritmo y devuelve JSON
  v
Python recibe el resultado
  |
  v
La interfaz mostrará tablas, rutas y gráficos
```

Cada llamada del adaptador inicia un proceso C++, envía los datos, cierra su entrada, recibe la respuesta y espera a que termine. Los algoritmos se ejecutan en C++; Python se encarga de la integración y del manejo de errores.

No hace falta que el usuario tenga el ejecutable abierto previamente. Tampoco hay endpoints REST que configurar.

## Requisitos

Para compilar el motor y ejecutar la integración necesitas:

| Herramienta | Requisito |
|---|---|
| Compilador C++ | Compatible con C++17; se ha probado MinGW en Windows |
| CMake | 3.16 o superior |
| Python | 3.10 o superior para el adaptador y la futura app |
| Ninja | Necesario si utilizas los comandos de compilación con `-G Ninja` |
| Streamlit | Solo para desarrollar o ejecutar la futura interfaz |

El adaptador y la prueba sencilla usan únicamente la biblioteca estándar de Python. No necesitas instalar Streamlit para comprobar los algoritmos.

Ejecuta los comandos siguientes desde la **raíz del proyecto**, la carpeta que contiene este README y `CMakeLists.txt`.

## Inicio rápido en Windows

### 1. Obtener el proyecto

Descarga o clona el repositorio y abre una terminal en su carpeta. Conserva la estructura de directorios.

Las carpetas `build/`, `cmake-build-*/`, `.venv/`, `tmp/` y `dist/` están excluidas por `.gitignore`. Por eso, después de clonar el repositorio, normalmente tendrás que compilar el motor y regenerar el ZIP si lo necesitas.

### 2. Compilar el motor

En Linux o macOS basta con `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release` y `cmake --build build`; el ejecutable queda en `build/sentinela`. Sin CMake también funciona `g++ -std=c++17 -O2 src/main.cpp -o build/sentinela`.

Con CMake, Ninja y MinGW disponibles en `PATH`:

```powershell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

El ejecutable esperado es `build/sentinela.exe`. CMake copia las DLL necesarias del runtime MinGW junto a él.

Si utilizas **CLion**, abre la carpeta como proyecto CMake, selecciona el toolchain MinGW, el perfil Release y compila el target `sentinela`. El adaptador también busca en las carpetas habituales de compilación de CLion.

No necesitas copiar las rutas personales de otra computadora. El compilador y las herramientas deben estar instalados o configurados en tu equipo.

### 3. Probar los siete algoritmos

```powershell
python prueba_algoritmos.py
```

El script localiza el motor, ejecuta los ejemplos pequeños de los siete algoritmos y compara sus resultados con valores conocidos. Debe mostrar una línea `[OK]` por algoritmo y terminar con:

```text
Las 7 pruebas pasaron
```

Esto confirma el funcionamiento del motor y su conexión con Python. No abre una ventana de Streamlit.

### 4. Ejecutar un caso desde la terminal

```powershell
Get-Content -Raw examples/mst.input.json | .\build\sentinela.exe
```

El resultado se imprime como JSON. Para probar el formato de texto del análisis conjunto de cadenas:

```powershell
Get-Content -Raw data/synthetic/strings.input.json | .\build\sentinela.exe --text
```

**Si abres `sentinela.exe` con doble clic y no aparece nada, está esperando una entrada.** El programa no tiene menú: lee un JSON de la entrada estándar (`stdin`) hasta su cierre (`EOF`), escribe la respuesta en la salida estándar (`stdout`) y termina. El adaptador Python gestiona ese intercambio automáticamente.

## Ejecutarlo en otra PC

Las rutas del adaptador se calculan a partir de la ubicación del proyecto. No dependen del nombre de usuario ni de una ruta como `C:\Users\...` de la computadora donde se desarrolló.

Para moverlo:

1. Copia o clona el proyecto conservando su estructura
2. Instala Python y las herramientas de compilación que correspondan
3. Compila el motor en esa computadora
4. Ejecuta `python prueba_algoritmos.py`

En Windows/MinGW, si distribuyes un binario ya compilado, conserva juntos `sentinela.exe`, `libstdc++-6.dll`, `libgcc_s_seh-1.dll` y `libwinpthread-1.dll`. El binario debe ser compatible con el sistema y la arquitectura de destino.

El adaptador busca `sentinela.exe` en Windows y `sentinela` en otros sistemas. Revisa las carpetas `build`, `build/Release`, `build/Debug`, `cmake-build-release` y `cmake-build-debug`. Si el ejecutable está en otra ubicación, puedes indicarla:

```powershell
$env:SENTINELA_EXECUTABLE = "C:\ruta\del\proyecto\build\sentinela.exe"
python prueba_algoritmos.py
```

En Linux/macOS, con CMake y un compilador C++17 instalados, la compilación puede realizarse con:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
python3 prueba_algoritmos.py
```

Esos sistemas aún requieren verificación propia. No se puede ejecutar un `.exe` de Windows directamente en Linux o macOS. Al cambiar de computadora o compilador, genera una carpeta de compilación nueva; no reutilices la caché CMake de otro equipo.

Cuando exista la app, el motor se ejecutará en la computadora que aloje el servidor Python de Streamlit. Las personas que entren desde un navegador no necesitarán instalar C++.

## Consumir el backend desde Python

Este ejemplo puede guardarse como un script en la raíz del proyecto:

```python
from app import EngineAdapter, EngineError

adapter = EngineAdapter(timeoutSeconds=30)

try:
	response = adapter.run("mst", {
		"n": 3,
		"edges": [
			{"u": 0, "v": 1, "cost": 2},
			{"u": 1, "v": 2, "cost": 3},
			{"u": 0, "v": 2, "cost": 9},
		],
	})
	print(response["result"]["total_cost"])
except EngineError as error:
	print(error.kind, str(error))
```

El resultado esperado es `5`. `run()` devuelve el objeto completo de respuesta; los resultados del algoritmo están dentro de `response["result"]`. Los errores de una llamada se comunican mediante `EngineError`. La creación del adaptador también puede lanzar ese error si no encuentra un motor válido.

También puedes cargar una solicitud existente:

```python
from app import EngineAdapter

adapter = EngineAdapter()
request = adapter.loadRequest("examples/tsp.input.json")
response = adapter.runRequest(request)
print(response["result"])
```

La [guía de integración](app/README.md) explica toda la API, la carga de archivos, los errores, las métricas y un ejemplo de pantalla para comenzar Streamlit.

## Formato de entrada y salida de la app

Una solicitud contiene el nombre del modo y sus datos:

```json
{
  "mode": "mst",
  "input": {
    "n": 3,
    "edges": [
      {"u": 0, "v": 1, "cost": 2},
      {"u": 1, "v": 2, "cost": 3}
    ]
  }
}
```

Una respuesta exitosa incluye `ok`, `contract`, `mode` y `result`. La versión actual del contrato de la app se llama `provisional-v1`; es el identificador que utiliza el adaptador para comprobar compatibilidad.

| Modo de la app | Datos principales | Resultado principal |
|---|---|---|
| `mst` | Número de nodos y enlaces con costo | Enlaces elegidos, costo total y conectividad |
| `tsp` | Red con distancias y centrales seleccionadas | Tour, recorrido físico, distancia y condición de solución exacta |
| `max_flow` | Capacidades, origen, destino y dirección | Valor máximo, flujo por enlace y corte mínimo |
| `voronoi` | Sitios y dominio rectangular | Polígonos y sitios más cercanos a las consultas |
| `matching` | Dos transmisiones y tres firmas | Primera aparición de cada firma |
| `palindrome` | Dos transmisiones | Intervalo del mayor palíndromo de cada una |
| `common_substring` | Dos transmisiones | Intervalo de la mayor subcadena compartida |
| `strings` | Dos transmisiones y tres firmas | Los tres análisis de cadenas en una llamada |

Reglas que debe respetar la interfaz:

- Los índices de nodos y enlaces comienzan en **0**
- Las posiciones de cadenas comienzan en **1** y los extremos de intervalos son inclusivos
- El contrato de la app acepta cadenas con `0–9` y `A–F` en mayúsculas; elimina saltos CR/LF y rechaza espacios, minúsculas y BOM
- Las cadenas pueden enviarse como texto o como `{"file":"ruta/al/archivo.txt"}` para archivos existentes en el servidor
- Mediante el adaptador, las rutas relativas se resuelven respecto a la raíz del proyecto; ejecutando C++ directamente, respecto al directorio de trabajo del proceso
- Un archivo subido desde Streamlit debe leerse como bytes y convertirse con `hexFromBytes`; su nombre no es una ruta del servidor

Límites del contrato local: 64 MB por solicitud, 2000 nodos, 200000 enlaces, 500 centrales seleccionadas en TSP, 1000 sitios de Voronoi y 2000000 caracteres normalizados por secuencia. Revisa las restricciones y los campos completos en [CONTRACT.md](docs/CONTRACT.md).

## Contrato de la app y contrato del autograder

Existen dos formas de entrada y salida, porque la app y el evaluador esperan estructuras distintas:

| Uso | Cómo se activa | Formato |
|---|---|---|
| App Python/Streamlit | Ejecución local sin argumentos mediante `EngineAdapter` | Contrato `provisional-v1`, respuesta con `ok/result` |
| Autograder web | ZIP generado por el empaquetador, o `--autograder` en el ejecutable local | Contrato web `1.1.0-web`, resultado directo |

Por ejemplo, la app usa `max_flow` y `common_substring`; el evaluador usa `flow` y `common`. También cambian algunos campos de entrada y salida. **Para construir la app, utiliza el contrato del adaptador Python.**

El equipo confirmó una puntuación de **100** en el autograder. Como evidencia adicional, el repositorio incluye registros de 75 casos nativos y 25 casos ejecutados localmente con el compilador WebAssembly del sitio.

Para regenerar el paquete de evaluación:

```powershell
python tools/package_autograder.py
```

Genera `dist/A0XXXXXX_SENTINEL_DEL_NORTE.zip`. Para la entrega identificada usa `--student-id` con la matrícula de un integrante, por ejemplo `--student-id A00840242`. Las instrucciones completas están en [AUTOGRADER.md](docs/AUTOGRADER.md).

## Datos incluidos

La red GÉANT suministrada contiene **22 nodos, 36 enlaces y 462 demandas**. Los archivos originales se conservan y las transformaciones se documentan por separado.

| Carpeta | Contenido |
|---|---|
| `data/original/` | Copias de los datos originales |
| `data/derived/` | Tablas y solicitudes JSON preparadas para el motor |
| `data/synthetic/` | Transmisiones y firmas ilustrativas para pruebas |
| `examples/` | Casos pequeños de entrada y salida por modo |

Puedes regenerar los datos de trabajo con:

```powershell
python tools/prepare_data.py
```

Este conversor prepara solicitudes JSON; el motor C++ no interpreta directamente XML o CSV. Algunos valores, como la instalación supuesta de módulos, la selección de centrales y el dominio de Voronoi, son parámetros de trabajo, no mediciones verificadas de infraestructura instalada. Las demandas de tráfico no se usan como capacidades de enlace.

Consulta [data/README.md](data/README.md) antes de interpretar o modificar esos escenarios. Las transmisiones y firmas sintéticas no sustituyen los archivos oficiales pendientes.

## Pruebas y mediciones

Después de compilar, puedes ejecutar:

```powershell
python prueba_algoritmos.py
python tests/test_engine.py build/sentinela.exe
python tests/test_adapter.py build/sentinela.exe
python tests/test_autograder.py
python tests/stress_algorithms.py
python tests/stress_autograder.py
```

La primera es la comprobación rápida. Las suites restantes contrastan los algoritmos con referencias independientes, verifican la integración Python y cubren diferencias específicas del contrato web. `stress_algorithms.py` lleva los siete algoritmos hasta los límites del contrato (2 000 nodos, 200 000 enlaces, 2 000 000 de caracteres), verifica cada resultado con un certificado independiente, prueba casos adversariales y rechazos, y mide la escalabilidad frente a la complejidad teórica. `stress_autograder.py` replica los casos funcionales y de estrés del autograder web en sus perfiles `lite`, `normal` y `huge`. La metodología, los resultados y las limitaciones están en [STRESS.md](docs/STRESS.md). Todas las suites buscan `build/sentinela.exe` en Windows y `build/sentinela` en Linux o macOS; también aceptan la ruta del ejecutable como primer argumento.

CMake registra las suites del motor, del adaptador, del contrato web y de estrés (en modo rápido) si encuentra una versión adecuada de Python:

```powershell
ctest --test-dir build --output-on-failure
```

Para regenerar ejemplos y benchmarks:

```powershell
python tools/examples.py build/sentinela.exe
python tools/benchmark.py build/sentinela.exe
```

Los resultados y sus límites de interpretación están en [results/README.md](results/README.md). El tiempo interno del algoritmo no incluye todo el tiempo de respuesta de la app; el pico de memoria corresponde al proceso completo, no únicamente a una estructura del algoritmo.

## Construir la interfaz Streamlit

La interfaz incluye escenarios GÉANT para MST, TSP, flujo y Voronoi, así como análisis de transmisiones de ejemplo o archivos TXT cargados. Selecciona un análisis en la barra lateral y pulsa **Ejecutar análisis**. Cada resultado conserva su entrada: vuelve a ejecutar al cambiar parámetros.

Para preparar un entorno Python separado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements.txt
```

En Linux/macOS utiliza `.venv/bin/python`. La instalación de dependencias no crea ni abre la interfaz.

Inicia la interfaz desde la raíz con:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

También puedes ejecutar `python iniciar_app.py` con el Python donde instalaste las dependencias. El lanzador localiza la app respecto al proyecto y admite la carpeta local de dependencias `.venv-deps` si está disponible.

El lanzador muestra la dirección exacta, normalmente `http://127.0.0.1:8501`, y usa el siguiente puerto disponible hasta 8510 si está ocupado. Abre esa dirección y conserva la terminal abierta. Desactiva explícitamente el modo de desarrollo de Streamlit para evitar enlaces al puerto 3000 sin un servidor de interfaz.

La interfaz conserva resultados entre interacciones, captura `EngineError` y distingue TSP exacto de heurístico. Presenta tiempo del algoritmo C++, tiempo total de la llamada y pico de memoria del proceso, con unidades y alcance de cada medición. La distribución en otras computadoras sigue pendiente.

## Problemas frecuentes

| Síntoma | Causa o acción a revisar |
|---|---|
| El ejecutable abre una ventana vacía | Está esperando JSON y el cierre de stdin; utiliza la prueba Python o una tubería |
| No se encuentra el motor | Compila primero o configura `SENTINELA_EXECUTABLE` |
| Windows indica que falta una DLL | Conserva las DLL del runtime junto al ejecutable o recompila con CMake |
| `cmake`, `ninja`, `g++` o `python` no se reconoce | Instala la herramienta o configura su ubicación en el entorno |
| CMake señala rutas de otra PC | Genera una carpeta de compilación nueva |
| No se encuentra un archivo de datos | Comprueba su ruta y desde dónde se resuelve; no uses rutas personales del autor |
| El motor rechaza una transmisión | Revisa mayúsculas, caracteres permitidos, BOM y límites de tamaño |
| La solicitud supera el tiempo máximo | Revisa el tamaño del caso; el adaptador usa 30 segundos por defecto y permite configurarlo |
| La respuesta del autograder no tiene `result` | Es otro contrato; utiliza el ejecutable local normal para la app |
| Streamlit no encuentra `app/streamlit_app.py` | Ejecuta el comando desde la raíz del proyecto |

## Estructura del repositorio

```text
Sentinela del Norte/
├── README.md                  Guía general del proyecto
├── CMakeLists.txt             Configuración de compilación C++
├── prueba_algoritmos.py       Prueba sencilla de los siete algoritmos
├── team.txt                   Integrantes y matrículas
├── src/
│   ├── main.cpp               Entrada y salida del proceso
│   ├── network.h              MST, TSP y flujo máximo
│   ├── geometry.h             Voronoi
│   ├── strings.h              Algoritmos de cadenas
│   ├── protocol.h             Contrato local de la app
│   ├── autograder.h           Contrato del evaluador web
│   ├── json.h                 Lectura y escritura de JSON
│   └── metrics.h              Medición de memoria
├── app/
│   ├── adapter.py             Integración Python con el ejecutable
│   ├── requirements.txt       Dependencias para la futura interfaz
│   └── README.md              Guía técnica para desarrollar Streamlit
├── examples/                  Entradas y salidas pequeñas
├── data/                      Datos originales, derivados y sintéticos
├── tools/                     Preparación, empaquetado y benchmarks
├── tests/                     Pruebas automatizadas
├── results/                   Evidencia de pruebas y mediciones
└── docs/                      Contratos, algoritmos y estándar
```

## Documentación complementaria

Para preparar la exposición y practicar preguntas técnicas, consulta la [guía de estudio para la presentación](docs/GUIA_PRESENTACION.md). Incluye explicaciones de los siete algoritmos, complejidades, supuestos, respuestas frecuentes y un guion de demostración.

| Documento | Cuándo consultarlo |
|---|---|
| [Integración Python y Streamlit](app/README.md) | Para construir la interfaz y consumir el backend |
| [Contrato de la app](docs/CONTRACT.md) | Para conocer campos, límites, índices y respuestas exactas |
| [Algoritmos y decisiones](docs/ALGORITHMS.md) | Para estudiar correctitud, complejidad y limitaciones |
| [Pruebas de estrés](docs/STRESS.md) | Para revisar casos límite, escalabilidad, memoria y limitaciones medidas |
| [Datos y supuestos](data/README.md) | Para entender la procedencia de los escenarios |
| [Autograder](docs/AUTOGRADER.md) | Para generar y ejecutar el paquete de evaluación |
| [Pruebas y mediciones](results/README.md) | Para interpretar la evidencia y los benchmarks |
| [Estándar de programación](docs/STYLE.md) | Para mantener las convenciones del código |

## Pendientes del equipo

- Ampliar los escenarios y las opciones de visualización de Streamlit
- Probar la app completa y su instalación en otra computadora
- Incorporar las transmisiones, firmas y escenarios oficiales cuando estén disponibles
- Completar autores y matrículas en `team.txt` y los encabezados
- Preparar los entregables académicos adicionales que correspondan

El código sigue las convenciones documentadas en `docs/STYLE.md`: tabulaciones, nombres consistentes, separación visual y comentarios cortos sin acentos ni puntos finales. Al modificar el contrato de la app, actualiza también el adaptador, sus pruebas y la documentación.
