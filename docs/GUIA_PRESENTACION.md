# Sentinela del Norte: guía de estudio para la presentación

Esta guía explica el proyecto y prepara respuestas para preguntas técnicas. Describe lo que está implementado: motor C++, adaptador Python, datos y pruebas. La interfaz Streamlit todavía está pendiente. El equipo confirmó una puntuación de **100 en el autograder web**.

## 1. Lo que deben poder explicar en un minuto

> Sentinela del Norte es un proyecto académico que aplica siete algoritmos al análisis de una red y de transmisiones hexadecimales. El motor está desarrollado en C++17. Resuelve conexiones de menor costo, rutas entre centrales, flujo máximo, zonas de proximidad y tres problemas de cadenas. Python comunica ese motor con la futura interfaz Streamlit mediante JSON. Conservamos los datos originales de GÉANT y documentamos por separado los escenarios que dependen de supuestos. El motor y su integración están probados; el evaluador web nos dio 100. Falta construir y probar la interfaz completa.

No memoricen únicamente los nombres: para cada algoritmo deben explicar **qué recibe, qué devuelve, por qué se eligió y qué no garantiza**.

## 2. Mapa del sistema

```text
Datos de red o transmisiones
           |
           v
Solicitud JSON con mode e input
           |
           v
Adaptador Python                 app/adapter.py
           | inicia un proceso y envía la solicitud
           v
Punto de entrada C++              src/main.cpp
           |
           v
Validación y contrato             src/protocol.h
           |
           v
Algoritmos                       network.h / geometry.h / strings.h
           |
           v
Respuesta JSON -> Python -> futura pantalla Streamlit
```

**Separación de responsabilidades:** los algoritmos internos reciben estructuras de datos y devuelven resultados. No dibujan pantallas ni necesitan conocer Streamlit. El contrato traduce JSON a esas estructuras. El adaptador ejecuta el programa, controla el tiempo y convierte sus fallos en errores manejables desde Python.

Cada solicitud inicia un proceso C++ independiente. No es un servidor que se quede escuchando ni una API HTTP. El ejecutable recibe un objeto JSON, responde y termina.

**¿Por qué parece que no hace nada al abrirlo?** Porque espera datos por `stdin` y su cierre, llamado EOF. No tiene menú. Python envía la solicitud y cierra esa entrada automáticamente.

## 3. Vocabulario que conviene dominar

| Término | Explicación sencilla |
|---|---|
| Grafo | Conjunto de nodos y conexiones entre ellos |
| Nodo o vértice | Una central o ubicación |
| Enlace o arista | Conexión entre dos nodos |
| Peso | Valor asociado a un enlace; su significado depende del problema |
| Costo | Valor que minimiza MST; no necesariamente dinero con una moneda conocida |
| Distancia | Longitud utilizada para calcular recorridos |
| Capacidad | Máximo flujo permitido por un enlace |
| Demanda | Tráfico solicitado entre dos nodos; no es capacidad instalada |
| Camino | Secuencia de enlaces que permite llegar de un nodo a otro |
| Ciclo | Recorrido que regresa al nodo inicial |
| Componente | Grupo de nodos conectados entre sí |
| Heurística | Método que busca una buena solución sin garantizar que sea óptima |
| Subcadena | Fragmento continuo de un texto |
| Subsecuencia | Caracteres en orden que pueden tener separaciones; no es lo que calculamos |
| JSON | Formato de intercambio con objetos, listas, números y texto |

No intercambien costo, distancia, capacidad y demanda: representan magnitudes distintas, aunque internamente un algoritmo utilice un campo numérico común.

## 4. Los siete algoritmos

### 4.1 MST: Kruskal

**Pregunta:** ¿qué enlaces conectan la red con el menor costo total, sin ciclos?

**Entrada:** nodos y enlaces no dirigidos con costo. **Salida:** enlaces elegidos, costo total, componentes y señal de conectividad.

Pasos:

1. Ordenar los enlaces de menor a mayor costo
2. Revisar si sus extremos ya pertenecen al mismo grupo conectado
3. Aceptar el enlace únicamente si une grupos distintos
4. Unir esos grupos y continuar

La estructura **DSU**, o conjuntos disjuntos, permite consultar y unir componentes eficientemente mediante compresión de caminos y unión por tamaño.

**Ejemplo:** A–B cuesta 2, B–C cuesta 3 y A–C cuesta 9. Se eligen los dos primeros: costo 5. Agregar el tercero formaría un ciclo y aumentaría el costo.

**¿Por qué es correcto?** Por la propiedad del corte: un enlace de costo mínimo que une componentes puede formar parte de una solución óptima. Al elegirlo sin cerrar ciclos mantenemos la posibilidad de completar un árbol mínimo.

**¿Por qué Kruskal y no Prim?** La entrada ya es una lista de enlaces y la red es dispersa. Kruskal permite conservar fácilmente el identificador de cada enlace. Prim también sería válido; se usa como referencia independiente en las pruebas.

**Límite importante:** si la red está desconectada, no inventa conexiones. Devuelve un **bosque mínimo** y `connected:false`. Un MST conectado con V nodos tiene V−1 enlaces.

### 4.2 TSP: Held–Karp y heurística con 2-opt

**Pregunta:** ¿en qué orden visitar las centrales seleccionadas y regresar al origen con poca distancia total?

En el contrato de la app, primero se calcula la distancia de viaje entre las centrales usando **Dijkstra sobre los enlaces físicos existentes**. Después se resuelve el orden de visita sobre esa matriz de caminos mínimos.

**Casos pequeños:** Held–Karp, programación dinámica exacta. Un estado guarda el menor costo de visitar un subconjunto de centrales y terminar en una central concreta. Se prueban las posibles visitas anteriores y se conserva la mejor. Al final se suma el regreso al origen.

**Casos grandes:** vecino más cercano para obtener un tour inicial y **2-opt** para mejorarlo. 2-opt cambia dos conexiones y revierte un segmento cuando eso reduce la distancia. En esta implementación se busca la mejor mejora de cada pase, con un presupuesto predeterminado de 100 pases.

**¿Por qué dos métodos?** Held–Karp garantiza el óptimo, pero sus estados crecen exponencialmente. Por defecto se utiliza hasta 16 centrales; el contrato local permite configurar el umbral hasta 18. La heurística permite trabajar con más centrales sin ese crecimiento exponencial.

**¿Es siempre óptimo?** Solo cuando el resultado indica `exact:true`. La heurística no garantiza el óptimo ni una proporción fija respecto al óptimo. Si se agotan sus pases, tampoco se promete que no existan mejoras pendientes.

**Diferencia que pueden preguntar:** el tour visita una vez cada central como servicio, pero el recorrido físico puede repetir nodos intermedios e incluso atravesar otra central antes de atenderla. No estamos exigiendo un ciclo hamiltoniano directamente sobre la topología física.

En el escenario GÉANT actual se seleccionan las 22 centrales: supera el umbral exacto predeterminado y utiliza la heurística.

**Contrato web:** el autograder entrega directamente una matriz simétrica de costos. Allí se usa esa matriz sin aplicar Dijkstra ni modificarla mediante cierre de caminos mínimos.

### 4.3 Flujo máximo: Dinic

**Pregunta:** ¿cuál es el mayor flujo total que puede salir de un origen y llegar a un destino sin superar capacidades?

**Entrada:** red, capacidades, origen, destino y si los enlaces son dirigidos. **Salida:** valor máximo, flujo por enlace y nodos del lado del origen en un corte mínimo.

Conceptos esenciales:

- **Conservación:** en un nodo intermedio, lo que entra debe igualar lo que sale
- **Red residual:** representa cuánto flujo adicional podemos enviar y cuánto podemos cancelar de decisiones previas
- **Arco inverso:** permite deshacer o redirigir flujo; no significa necesariamente un enlace físico nuevo

Dinic construye niveles con BFS y envía flujos bloqueantes usando DFS. Repite mientras el destino siga siendo alcanzable en la red residual.

**¿Cómo sabemos que terminó con el máximo?** Cuando ya no existe camino residual del origen al destino, los nodos alcanzables definen un corte cuya capacidad coincide con el flujo. El teorema de flujo máximo y corte mínimo certifica la optimalidad.

**Dirigido:** el flujo respeta la orientación del enlace. **No dirigido:** se representa un flujo neto con signo; positivo es u→v y negativo v→u. Su valor absoluto no puede superar la capacidad compartida.

**Límites:** resuelve un problema de un origen y un destino. No distribuye simultáneamente las 462 demandas ni resuelve flujo multicommodity. Si no hay ruta, un flujo cero es una respuesta válida.

### 4.4 Voronoi: recorte con semiplanos

**Pregunta:** ¿qué puntos de una región están más cerca de cada central?

**Entrada:** coordenadas planas de sitios y dominio rectangular. **Salida:** un polígono por sitio y, si se solicitan, los sitios más cercanos a ciertos puntos.

Para cada sitio, el algoritmo comienza con todo el rectángulo. Lo compara con cada otro sitio y conserva el lado de la mediatriz donde el sitio actual es igual o más cercano. La intersección de esos semiplanos es su celda de Voronoi.

**Ejemplo:** con dos sitios, una línea mediatriz separa sus zonas de proximidad dentro del rectángulo.

**¿Por qué ese método?** Es directo, permite recortar al dominio y resulta razonable para los 22 sitios de la instancia. Fortune tiene mejor complejidad asintótica para grandes cantidades de sitios, pero es más complejo de implementar y de manejar ante degeneraciones.

**Límites:** usa distancia euclidiana sobre un plano proyectado, no tiempos de viaje por la red ni cobertura física real de antenas. El dominio limita los polígonos. Sitios duplicados exactos se asignan al primero y los siguientes reciben celdas vacías; consultas empatadas eligen el menor índice.

### 4.5 Búsqueda de firmas: KMP

**Pregunta:** ¿dónde aparece por primera vez una firma dentro de una transmisión?

KMP prepara una tabla de prefijos del patrón. Si una comparación falla, utiliza lo que ya sabe de los prefijos y sufijos para decidir cuánto patrón puede conservar sin retroceder el cursor del texto.

**Ejemplo:** en `AA12BC12`, el patrón `12` aparece por primera vez en posición **3**, contando desde 1.

En el contrato de la app se buscan tres firmas en cada una de dos transmisiones: seis resultados. Si no aparece una firma, devuelve `found:false` y posición 0.

**¿Por qué KMP?** Ofrece tiempo lineal y usa memoria proporcional al patrón. Para miles de firmas podría convenir Aho–Corasick; para tres firmas, KMP es una elección sencilla y eficiente.

**Límite:** reporta coincidencia textual. Una firma encontrada no demuestra por sí sola que exista un ataque.

### 4.6 Palíndromo más largo: Manacher

**Pregunta:** ¿cuál es el fragmento continuo más largo que se lee igual de izquierda a derecha y de derecha a izquierda?

**Ejemplo:** `ABCCBA` es un palíndromo de longitud 6.

Manacher calcula radios de palíndromos alrededor de centros pares e impares. Aprovecha la simetría del palíndromo que llega más a la derecha para evitar repetir comparaciones ya conocidas.

**¿Por qué es lineal?** Las comparaciones que amplían la frontera la desplazan hacia la derecha. Esa frontera solo puede avanzar una cantidad proporcional al tamaño del texto; las simetrías evitan repetir desde cero el trabajo interior.

Se devuelve un intervalo por transmisión. En empate se elige el de menor inicio. Se analizan caracteres hexadecimales; no se convierten a bits.

### 4.7 Subcadena común más larga: autómata de sufijos

**Pregunta:** ¿cuál es el fragmento continuo más largo que aparece en las dos transmisiones?

**Ejemplo:** `AB12CD` y `FF12EE` comparten la subcadena `12`. En el primer texto ocupa el intervalo 3–4.

Se construye un autómata a partir de la primera transmisión. Sus estados agrupan subcadenas con los mismos conjuntos de posiciones finales. Las transiciones extienden coincidencias y los enlaces de sufijo permiten reducirlas cuando el siguiente carácter no encaja.

Después se recorre la segunda transmisión, manteniendo la coincidencia válida más larga y registrando el mejor resultado. Los estados conservan información para recuperar las posiciones más tempranas en la primera transmisión.

**¿Por qué no programación dinámica de una tabla completa?** La tabla tradicional necesita tiempo O(NM), demasiado para textos largos. Con alfabeto hexadecimal fijo, el autómata trabaja en O(N+M).

**Límite:** tiempo lineal no significa memoria pequeña. El autómata puede tener cerca de 2N estados y cada uno guarda transiciones y metadatos. Textos de millones de caracteres pueden consumir cientos de MB.

**Empates:** menor inicio en la primera transmisión y después en la segunda. Es subcadena continua, no subsecuencia. Para los ejemplos no hexadecimales del autograder existe una variante con transiciones mediante mapas.

## 5. Complejidades que pueden preguntar

V = nodos, E = enlaces, k = centrales seleccionadas, P = pases de 2-opt, n = sitios de Voronoi, q = consultas, N y M = longitudes de textos o patrón según la fila.

| Algoritmo | Tiempo | Memoria auxiliar o de trabajo |
|---|---|---|
| Kruskal | O(E log E + V), dominado por ordenar | O(V+E) |
| Dijkstra para preparar TSP | O(k(V+E) log(E+1)) con el heap utilizado | O(kV+V+E), aparte del solucionador y salida |
| Held–Karp | O(k² · 2^k) | O(k · 2^k) |
| Vecino más cercano y 2-opt | O(k² + Pk²) | O(k) para el tour; matriz de distancias aparte |
| Dinic, caso general | O(V²E) | O(V+E), incluida una pila de profundidad O(V) |
| Voronoi implementado | O(n³ + qn), cota conservadora | O(n²), cota conservadora para polígonos |
| KMP por texto y patrón | O(N+M) | O(M) |
| Manacher | O(N) | O(N) |
| Autómata de sufijos hexadecimal | O(N+M) | O(N) |

La variante de subcadena común para texto general usa mapas y tiene tiempo O((N+M) log A), donde A es el tamaño del alfabeto. No confundan la complejidad del algoritmo central con lectura de archivos, transporte, construcción de JSON o preparación adicional de TSP.

**Cómo explicarlo sin fórmulas:** lineal crece aproximadamente con la cantidad de datos; ordenar añade un factor logarítmico; cuadrático compara muchas parejas; exponencial crece tan rápido que exige limitar el tamaño de los casos exactos.

## 6. Datos reales, derivados y supuestos

### Datos originales

El XML GÉANT suministrado contiene 22 nodos, 36 enlaces y 462 demandas dirigidas. Se conservan IDs, coordenadas, conexiones, demandas, costos y capacidades descritos para módulos adicionales. Los originales no se modifican.

**Advertencia esencial para explicar los datos:** que el XML ofrezca un módulo instalable de 40000 Mbit/s no significa que ese módulo esté instalado en la red real.

### Escenario de trabajo actual

| Elemento | Decisión o transformación |
|---|---|
| Dirección de enlaces físicos | Se modelan como no dirigidos; el XML no fija esa dirección en esta instancia |
| Capacidad de escenario | Se supone un módulo adicional instalado por enlace: 40000 Mbit/s |
| Costo de escenario | Costo original por módulo multiplicado por módulos supuestos; moneda no especificada |
| Distancias | Haversine entre extremos de enlaces existentes, en km; no longitud medida de fibra |
| Centrales TSP | Las 22 centrales, índices 0 a 21 |
| Flujo máximo | Origen 0 y destino 4, elegidos para el escenario |
| Proyección de Voronoi | Equirectangular, referencia 50° de latitud y 10° de longitud |
| Dominio | Rectángulo envolvente con 100 km de margen |
| Transmisiones y firmas disponibles | Ejemplos ilustrativos, no archivos oficiales de tráfico |

**¿Por qué son aceptables esos supuestos?** Permiten construir casos reproducibles para desarrollar y demostrar el motor. Están identificados para no presentar resultados de simulación como mediciones reales. Cuando lleguen escenarios oficiales, deben sustituirse y volver a ejecutarse las pruebas.

Las demandas se conservan como información original y **no se convierten en capacidades**. El nodo de Nueva York se mantiene porque está en el XML; su presencia también aumenta la distorsión de la proyección plana de trabajo.

## 7. Qué significa la validación

No solo revisamos que el programa compile. Se contrastan resultados con métodos independientes:

| Parte | Comprobación |
|---|---|
| MST | Comparación con Prim, costo, componentes y ausencia de ciclos |
| TSP exacto | Permutaciones pequeñas y Floyd–Warshall para las distancias de referencia |
| TSP heurístico | Validez del tour, recorrido físico y mejora respecto al recorrido inicial |
| Flujo | Enumeración de cortes pequeños, conservación y capacidades |
| Voronoi | Área total, semiplanos, consultas y casos degenerados |
| Cadenas | Enumeración, búsqueda directa y casos aleatorios con empates |
| Adaptador | Ejecución real, rutas, validaciones, recuperación y fallos simulados |
| Autograder | 100 confirmado por el equipo; además, registros de reproducción nativa y WebAssembly |

**¿El 100 demuestra que nunca fallará?** No. Demuestra que superó los casos del evaluador ejecutado. No prueba todos los casos posibles ni valida una interfaz que aún no está construida.

**¿Cómo se midió el rendimiento?** Hay benchmarks y registros en `results/`. El tiempo interno C++ excluye arranque, transporte y JSON; la memoria es el pico del proceso completo. No inventen tiempos ni comparaciones: consulten el archivo del caso y la máquina antes de citar una cifra.

## 8. App, archivos y contratos

El adaptador busca el ejecutable respecto a la carpeta del proyecto y permite configurarlo mediante `SENTINELA_EXECUTABLE`. Mover la carpeta no exige conservar el nombre de usuario ni las rutas de la computadora del autor.

Para otra PC se necesita un ejecutable compatible y Python. Si se compila con MinGW en Windows, se conservan las DLL necesarias junto al `.exe`. Para Linux o macOS se recompila; un ejecutable de Windows no es universal.

**Dos contratos:** la app usa `provisional-v1` y una respuesta con `ok/result`. El evaluador web usa `1.1.0-web` y espera un resultado directo. El empaquetador activa el segundo en la copia del código incluida en el ZIP. No se debe conectar el adaptador de la app al binario configurado únicamente para el evaluador.

En la app los nodos y enlaces son base 0; los intervalos de cadenas son base 1 e inclusivos. Para resaltar un intervalo en Python se usa `texto[inicio - 1:fin]`. Primero hay que comprobar que no sea vacío. Una firma ausente en el contrato local tiene posición 0; en el contrato web la ausencia de coincidencia se expresa con −1.

La app acepta texto hexadecimal estricto: `0–9 A–F`, ignorando CR/LF. No convierte silenciosamente minúsculas ni acepta espacios o BOM. Los ejemplos de texto general del evaluador se manejan en su adaptador específico.

## 9. Preguntas probables y respuestas breves

**¿Por qué C++ y Python?** C++ implementa los algoritmos y sus estructuras; Python facilita integrar formularios, archivos y resultados en Streamlit. La comunicación JSON mantiene separadas ambas partes.

**¿Usaron librerías que ya resolvían los siete problemas?** Los algoritmos y el codec JSON son código propio apoyado en contenedores y utilidades de la biblioteca estándar. Python no sustituye esos cálculos.

**¿Por qué no usar solo Python?** La decisión del proyecto es mantener un motor C++17 y consumirlo desde una capa de interfaz. No afirmamos que otro lenguaje sea incapaz de resolverlo ni que toda operación C++ sea siempre más rápida.

**¿MST encuentra la ruta más corta entre dos nodos?** No. Minimiza el costo total de una estructura que conecta la red. Para distancias de viaje de TSP usamos Dijkstra.

**¿TSP agrega enlaces que no existen?** En la app, la matriz conecta conceptualmente centrales mediante caminos de la topología. El recorrido final se expande a enlaces existentes; no instala enlaces físicos nuevos.

**¿Por qué la ruta física repite nodos?** Porque las conexiones entre visitas pueden compartir nodos intermedios. Visitar una central para servicio y transitar por ella son conceptos diferentes.

**¿Por qué 22 centrales no se resuelven exactamente por defecto?** El costo exponencial aumenta rápido. El umbral de 16 limita tiempo y memoria; para 22 usamos la heurística e indicamos `exact:false`.

**¿El flujo máximo satisface toda la matriz de demandas?** No. Optimiza una sola pareja origen–destino con capacidades dadas. Resolver múltiples demandas simultáneas sería otro modelo.

**¿Una celda Voronoi garantiza cobertura de red?** No. Solo representa cercanía geométrica en el plano y dominio definidos. No incorpora obstáculos, señales, capacidad ni rutas físicas.

**¿Qué pasa con coordenadas geográficas?** Se proyectan antes del cálculo plano. La proyección usada tiene distorsión y se documenta como aproximación de trabajo.

**¿Por qué no comparar todas las subcadenas?** Sirve como referencia en textos pequeños, pero no escala. KMP, Manacher y el autómata evitan repetir gran parte del trabajo.

**¿Cómo manejan empates?** MST usa el orden de los enlaces para desempatar costos iguales. En cadenas se prefiere el inicio más temprano; en subcadena común se prioriza la primera transmisión y luego la segunda.

**¿Qué pasa con datos incorrectos?** Se validan estructura, tipos y límites. El motor local produce errores y el adaptador los comunica como `EngineError`; la futura interfaz debe capturarlos y mostrarlos.

**¿Puede quedarse ejecutando indefinidamente desde Python?** Hay un tiempo máximo configurable por solicitud, de 30 segundos por defecto. Si se agota, el adaptador termina y espera al proceso antes de comunicar el error.

**¿Por qué fallaba antes con `unreachable`?** Había una incompatibilidad entre los campos esperados por el motor y los enviados por el evaluador. El sitio transforma excepciones en abortos. Se añadió un adaptador para su contrato y después pasó con 100.

**¿Hay archivos oficiales de ataques?** Las transmisiones disponibles para demostración son ilustrativas. No debemos atribuirles una captura real ni afirmar que identificamos un ataque en GÉANT.

**¿Qué falta?** Las pantallas y visualizaciones Streamlit, la prueba completa de interfaz y distribución, los datos oficiales pendientes y los entregables académicos adicionales.

## 10. Guion de demostración

Antes de presentar, compilen y prueben en la computadora que utilizarán. No dependan de instalar herramientas durante la exposición.

Desde la raíz del proyecto:

```powershell
python prueba_algoritmos.py
```

Expliquen que Python llama al motor C++ real y compara ejemplos con resultados conocidos. La salida esperada termina con `Las 7 pruebas pasaron`.

Para mostrar una solicitud y una respuesta concretas:

```powershell
Get-Content examples/mst.input.json
Get-Content -Raw examples/mst.input.json | .\build\sentinela.exe
```

En ese ejemplo el costo esperado es 5. Identifiquen entrada, selección de enlaces y salida. No abran únicamente el `.exe` con doble clic: esperará datos y parecerá detenido.

Si preguntan por la app, muestren `app/adapter.py` y expliquen la integración implementada. No presenten una pantalla propuesta como si ya estuviera terminada. Para resultados GÉANT, revisen primero las entradas `data/derived/*.input.json` y los supuestos de este documento.

## 11. Ruta de lectura y reparto del estudio

1. Todos: resumen, arquitectura, vocabulario y datos/supuestos
2. Redes: Kruskal, TSP, Dinic y sus diferencias
3. Geometría: semiplanos, proyección y límites de Voronoi
4. Cadenas: KMP, Manacher, autómata y convenciones de posiciones
5. Integración: JSON, adaptador, rutas, errores y dos contratos
6. Todos: preguntas probables y ensayo de la demostración

Cada integrante debe poder explicar al menos la arquitectura y las limitaciones generales, aunque tenga una parte asignada.

## 12. Lista final para repasar

- Distinguir costo, distancia, capacidad y demanda
- Explicar por qué Kruskal evita ciclos
- Distinguir TSP exacto, heurístico y recorrido físico
- Explicar red residual y corte mínimo en Dinic
- Explicar que Voronoi mide proximidad geométrica
- Distinguir firma, palíndromo y subcadena común
- Recordar índices base 0 frente a posiciones base 1
- Identificar datos originales, transformaciones y supuestos
- Explicar qué acredita el 100 y qué no acredita
- Tener claro que la interfaz Streamlit sigue pendiente
- Ensayar la prueba en la computadora de presentación

Para profundizar: [algoritmos](ALGORITHMS.md), [contrato local](CONTRACT.md), [datos](../data/README.md), [integración Python](../app/README.md) y [README principal](../README.md).
