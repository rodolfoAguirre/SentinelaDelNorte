# Decisiones y análisis del motor

Este documento describe el avance del motor, no el reporte final de la materia. Fuente de requisitos: PDF suministrado, principalmente páginas 5–7, 13–15 y 17–19; las decisiones aún no fijadas por el paquete oficial están marcadas en `data/README.md` y `CONTRACT.md`.

## Separación y modelo

Un único `main.cpp` enlaza headers C++17. Las funciones del namespace `engine` reciben estructuras simples y devuelven resultados sin JSON, archivos ni impresión. `protocol.h` normaliza entradas, transforma índices y serializa. `json.h` es código propio; no hay biblioteca JSON de terceros cuya licencia deba incorporarse. Solo se enlazan biblioteca estándar y, en Windows, Psapi para medir memoria. Python estándar convierte datos y ejecuta referencias de pruebas; no reemplaza el motor.

Las funciones de grafos validan sus estructuras. Las funciones de cadenas reciben secuencias hexadecimales previamente normalizadas; `normalizeHex` es la frontera de validación. El grafo distingue `cost`, `distance` y `capacity` en el adaptador, aunque el algoritmo reutiliza `Edge.weight`. Los índices de enlace siempre apuntan a la lista de entrada, por lo que se distinguen enlaces paralelos. Las demandas permanecen separadas y no participan en el flujo máximo s-t.

## Archivo de cada algoritmo

| Algoritmo | Archivo `.h` | Funcion principal |
|---|---|---|
| Arbol de expansion minima (Kruskal) | `src/network.h` | `engine::kruskal` |
| Ruta de centrales (TSP): Held-Karp y vecino mas cercano con 2-opt | `src/network.h` | `engine::tsp`, `engine::heldKarp`, `engine::heuristicTour` |
| Flujo maximo (Dinic) | `src/network.h` | `engine::dinic` |
| Regiones de Voronoi | `src/geometry.h` | `engine::voronoi` |
| Busqueda de firmas (KMP) | `src/strings.h` | `engine::kmp` |
| Palindromo mas largo (Manacher) | `src/strings.h` | `engine::manacher` |
| Subcadena comun mas larga (automata de sufijos) | `src/strings.h` | `engine::longestCommon` |

Las funciones de `src/protocol.h` preparan datos y respuestas para el programa, pero las implementaciones algorítmicas están en los encabezados de la tabla.

## 1. Árbol de expansión mínima

**Problema:** seleccionar enlaces físicos no dirigidos que conecten todos los vértices minimizando la suma de costos, sin ciclos. Para componentes desconectadas no existe árbol global: devolver bosque mínimo y señal explícita.

**Alternativas:** Prim con heap crece desde un vértice, O((V+E) log V) y O(V+E) incluyendo adyacencias; con matriz O(V²). Kruskal ordena enlaces, O(E log E + V), con DSU y O(V+E) espacio auxiliar. Se elige Kruskal porque la red es dispersa, el input es una lista de enlaces y es sencillo conservar sus identificadores y detectar componentes. No se requiere que los costos sean positivos.

**Correctitud:** procesar enlaces en orden no decreciente y aceptar únicamente los que unen componentes distintas evita ciclos. El enlace elegido es mínimo para un corte entre componentes; por la propiedad del corte, puede pertenecer a algún bosque óptimo. Repetir mantiene esa posibilidad hasta obtener un árbol en cada componente. DSU usa compresión de caminos y unión por tamaño; empates por índice garantizan repetibilidad. Validación independiente: Prim en 70 grafos pequeños aleatorios; aciclicidad, número de componentes, costo sumado y preservación de conectividad del bosque.

## 2. Ruta de mantenimiento (TSP)

**Modelo:** servicio exactamente una vez en cada central seleccionada y regreso al origen, sobre la métrica de caminos mínimos del grafo físico no dirigido. Dijkstra desde cada una de k centrales construye distancias y predecesores. La expansión del tour puede transitar varias veces por una central, incluso antes de su servicio. Esta distinción es indispensable: no se exige un ciclo hamiltoniano en la topología. Pesos no negativos; se rechaza desconexión entre centrales.

**Exacto:** Held–Karp guarda `DP[S,j]`, costo mínimo desde el origen que visita el subconjunto S de centrales no iniciales y termina en j. Base: distancia origen→j. Transición: mínimo de `DP[S\{j},h]+d(h,j)`. Cerrar con j→origen y reconstruir padres. Por inducción sobre |S|, quitar la última visita de cualquier tour parcial deja una solución a la subinstancia; probar todas las penúltimas visitas incluye la óptima. Tiempo O(k²2^k), espacio O(k2^k). Por defecto k<=16; límite configurable hasta 18 para contener memoria. Branch and Bound también sería exacto, pero sus podas dependen mucho de la instancia; Held–Karp ofrece costo más previsible.

**Grandes:** vecino más cercano, seguido por 2-opt de mejor mejora por pase. La primera fase construye una permutación O(k²); cada reversión conserva todos los nodos y el cierre, y reduce el costo en una métrica simétrica. Con P pases, O(Pk²), espacio de tour O(k). Presupuesto predeterminado 100; umbral de ganancia 1e-10. Es heurístico, no se promete óptimo ni razón constante de aproximación. No se usa la fórmula 2-opt para un grafo dirigido.

**Costo total adicional:** k Dijkstra con heap de entradas duplicadas, O(k(V+E) log(E+1)); memoria O(kV+V+E) para distancias, padres y adyacencias, más estado del solver y recorrido de salida (hasta O(kV)). Las asignaciones y esta preparación están incluidas en el cronómetro del algoritmo. Las distancias derivadas en km no son costos SNDlib. Validación: permutaciones de hasta siete centrales usando Floyd–Warshall independiente; comprobación de tour, enlaces físicos y longitud; comparación de 2-opt con vecino más cercano sin pases.

## 3. Flujo máximo

**Problema:** maximizar salida neta del origen respetando conservación en otros vértices y capacidades. **Edmonds–Karp** usa BFS por camino aumentante, O(VE²); es simple y adecuado como referencia. **Dinic**, elegido, usa niveles BFS y flujos bloqueantes con punteros de arista actual: O(V²E) general y O(V+E) espacio, más pila DFS O(V). No se asumen las cotas mejoradas de redes unitarias.

Cada arco residual tiene su reverso. En el modo dirigido el reverso comienza en 0; en no dirigido ambos residuos comienzan en c, representando un solo flujo neto con signo y capacidad |f|<=c. Para enlaces paralelos o antiparalelos cada pareja residual se conserva separada. Se obtiene el flujo original como c-residuo(u→v).

**Correctitud:** aumentar por una ruta residual conserva balance interno y respeta los límites; la actualización inversa permite cancelar decisiones previas. Un flujo bloqueante elimina los caminos del nivel actual. Al no haber camino residual s→t, el conjunto alcanzable define un corte cuya capacidad iguala el flujo; por max-flow/min-cut el resultado es máximo. Las pruebas enumeran todos los cortes en grafos pequeños, una referencia independiente más directa que duplicar Dinic. También verifican límites y conservación para dirigidos/no dirigidos, ceros, desconexión y multienlaces.

**Límites:** `double` y tolerancia residual 1e-9; escalar capacidades menores que esa magnitud. No es flujo multicommodity ni resuelve la matriz de demandas. Hasta 2000 nodos para limitar recursos y profundidad de DFS; implementaciones iterativas serían preferibles para cadenas muchísimo más largas.

## 4. Regiones de Voronoi

Para cada sitio i se inicia el dominio rectangular y se intersecta con todos los semiplanos donde `dist(x,i) <= dist(x,j)`. La frontera es la mediatriz entre i,j, implementada con normal unitaria y punto medio para evitar restas de cuadrados grandes. Sutherland–Hodgman recorta cada polígono convexo. **Correctitud:** cada recorte conserva exactamente los puntos que satisfacen una de las desigualdades de cercanía; su intersección final es por definición la celda restringida al dominio.

Se elige por facilidad de explicación, clipping directo y tamaño de la instancia (22 sitios). Con n sitios y q consultas, cota conservadora O(n³ + qn) de tiempo: n celdas, n recortes, hasta O(n) vértices por polígono. Espacio auxiliar por celda O(n), almacenamiento conservador de todos los polígonos O(n²). Para sitios distintos no degenerados, el diagrama planar tiene complejidad global lineal; esa observación no elimina el costo de los recortes de esta implementación.

**Alternativa:** barrido de Fortune O(n log n), O(n) espacio para el diagrama no degenerado, más recorte al dominio. Es más eficiente para grandes n pero complejo ante eventos simultáneos, aristas infinitas y precisión; no se implementa en este avance. Consultas actuales O(n); podría añadirse índice espacial para muchas consultas.

Duplicados exactos se asignan al primer índice; las otras celdas son vacías. Fronteras son compartidas entre polígonos cerrados, pero la consulta desempata por índice. Se aceptan colinealidad y sitios fuera del dominio. Se usan doubles, no predicados exactos: casi coincidencias pueden generar vértices redundantes o diferencias minúsculas de frontera. Pruebas: áreas sumadas iguales al dominio, vértices dentro de todos los semiplanos, consultas por distancia, duplicados, colineales y sitios externos. La proyección equirectangular es un supuesto de trabajo, no distancia geodésica exacta.

## 5. Búsqueda de firmas

KMP construye la función prefijo de cada patrón y recorre la transmisión sin retroceder su cursor. Cuando falla una comparación, el prefijo más largo que también es sufijo preserva todas las posibles coincidencias todavía viables. La primera coincidencia completa es la de menor inicio. Tiempo O(N+M) y espacio O(M) por pareja; seis comparaciones en total, con tres firmas constantes. Se devuelve existencia y posición, sin inferir la categoría de seguridad de la transmisión.

**Alternativas:** Z sobre patrón+separador+texto es O(N+M), pero requiere vector proporcional a texto y patrón; Aho–Corasick procesa muchos patrones juntos en O(suma de patrones + texto + coincidencias), con autómata y mayor complejidad de implementación. Para tres firmas, KMP es claro y de memoria pequeña; si crece el catálogo convendría Aho–Corasick. Patrones vacíos coinciden en posición 1, por convenio provisional. Pruebas con `str.find`, repeticiones, patrones ausentes, vacíos y saltos de línea.

## 6. Palíndromo continuo más largo

Manacher calcula radios pares e impares en arreglos separados. Dentro del palíndromo más a la derecha, el radio reflejado proporciona un límite seguro; solo se comparan caracteres adicionales al expandir fuera de lo conocido. Cada expansión que extiende la frontera la mueve hacia la derecha, dando O(N) tiempo total y O(N) espacio. Elegir el mayor radio convertido a longitud, con menor inicio en empates, cubre todos los centros posibles, pares e impares.

**Alternativa:** expansión independiente desde cada centro usa O(1) espacio y O(N²) tiempo en cadenas uniformes; adecuada para validar instancias pequeñas. La suite enumera todas las subcadenas y compara con su reversa, referencia aún más simple. Se trabaja sobre dígitos hexadecimales, no se decodifica ni convierte a bits. Vacío produce intervalo 0,0.

## 7. Subcadena común más larga

Se construye un **autómata de sufijos** de T1 con hasta 2N estados, transiciones en arreglo fijo de 16 caracteres, links de sufijo y clones. Cada estado representa una clase de subcadenas con los mismos finales. Se calcula el menor final de cada clase propagando mínimos por links de mayor a menor longitud. Un counting sort ordena estados por longitud en O(N); no se usa un sort O(N log N).

Se recorre T2 manteniendo la subcadena sufijo más larga que reconoce el autómata. Ante un fallo se siguen links hasta poder extender; los caracteres descartados se amortizan contra extensiones previas. El estado alcanzado proporciona la menor posición final en T1, y por tanto el menor inicio para la longitud actual. Comparar `(longitud, -inicio1, -inicio2)` implementa los desempates. Se inspecciona cada final en T2, así que cualquier óptimo está entre los candidatos examinados. **Es subcadena continua**, nunca subsecuencia.

Tiempo O(N+M) con alfabeto fijo, espacio O(N) (16 transiciones y metadatos por estado, más arreglos de orden). Constante de memoria mayor que Manacher: en el límite de dos millones de caracteres puede ocupar cientos de MB. El benchmark mide proceso completo, no solo autómata.

**Alternativa:** programación dinámica `dp[i,j] = dp[i-1,j-1]+1` si caracteres iguales, 0 si no; O(NM) tiempo y O(min(N,M)) memoria con filas rodantes, fácil de explicar pero inadecuada para transmisiones largas. Un arreglo de sufijos generalizado con LCP es otra opción escalable. Se elige autómata por tiempo lineal en hexadecimal. Validación mediante enumeración independiente, pares exhaustivos de cadenas binarias de longitud <=3 y aleatorios con empates/repeticiones.

## Alcance experimental y pendientes

El contrato web 1.1.0-web se implementa en `src/autograder.h`. Su TSP opera directamente sobre la matriz recibida, sin aplicar cierre métrico, y MST acepta hasta 5000 nodos para el perfil huge. Los límites y la semántica del contrato local se conservan. Para los ejemplos web no hexadecimales, `longestCommonText` usa transiciones con `std::map`: O((N+M) log A) para alfabeto de tamaño A; el camino hexadecimal conserva el autómata de transiciones fijas.

`tests/` valida referencias y propiedades; `results/` contiene mediciones reales y procedimiento. No se promete que pruebas finitas demuestren ausencia de defectos, ni compatibilidad con el autograder. Los benchmarks de red son dispersos y los de geometría mayormente uniformes: no representan todos los peores casos. Los límites explícitos evitan asignaciones exponenciales descontroladas en TSP; no constituyen límites oficiales.

Faltan datos oficiales de cadenas y escenarios. El contrato de la página se verificó con sus generadores y validadores, en ejecución nativa y con su compilador WebAssembly desde Node; la puntuación desde la interfaz web sigue pendiente. La interfaz Streamlit, presentación y PDF final están pendientes conforme al alcance solicitado. No se ha cargado el ZIP en servicios externos.

