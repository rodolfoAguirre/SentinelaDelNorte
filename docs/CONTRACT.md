# Contrato provisional v1

Una solicitud `{"mode":"...","input":{...},"metrics":false}`. `metrics` es opcional. Respuesta exitosa `{"ok":true,"contract":"provisional-v1","mode":"...","result":{...}}`. Campos adicionales desconocidos se ignoran; campos requeridos ausentes y tipos incorrectos producen error. Se rechazan claves JSON duplicadas, números no finitos, contenido después del primer objeto y profundidad superior a 64. Máximo 64 MB de stdin/archivo. El codec propio soporta escapes JSON y pares sustitutos Unicode; espera bytes UTF-8 válidos en strings literales, sin verificar esa codificación por separado. Los contenidos hexadecimales sí se validan estrictamente.

## Grafos

`n`: entero 1..2000. Nodos 0..n-1. `edges`: lista de hasta 200000 objetos; sus posiciones definen los identificadores de enlace. Se permiten enlaces paralelos y antiparalelos; no autoenlaces. Pesos finitos de magnitud <=1e12. No se deduplican enlaces. Los costos negativos están permitidos para MST; distancias y capacidades deben ser no negativas.

### mst

Entrada: `n`, `edges:[{"u":0,"v":1,"cost":4}]`. Grafo no dirigido.

Resultado: `edge_indices`, `total_cost`, `connected`, `components`, `algorithm`. Si el grafo está desconectado, devuelve bosque mínimo, `connected:false` y número de componentes; no lo presenta como árbol que conecta todos los nodos. Un único nodo devuelve árbol vacío de costo cero. Empates por índice de enlace.

### tsp

Entrada: `n`, `edges:[{"u":0,"v":1,"distance":4}]`, `selected:[0,1,...]`, opcionales `exact_limit:16`, `max_passes:100`. Grafo físico no dirigido. De 1 a 500 centrales distintas; comienza y termina en la primera central de `selected`. `exact_limit` 1..18 y `max_passes` 0..1000. Las unidades de distancia las define la entrada (km en los archivos derivados).

Resultado: `tour`, `total_distance`, `exact`, `algorithm`, `physical_nodes`, `physical_edge_indices`, `improvements` (reversiones 2-opt aceptadas). `tour` contiene cada central una vez y repite el origen para cerrar. Una central: `[v,v]`, distancia 0, recorrido físico `[v]`. Centrales desconectadas: error. El recorrido físico concatena caminos mínimos sobre enlaces existentes: **puede repetir centrales e intermedios**. La restricción de visita única se aplica al tour de servicios, no al tránsito físico. No resuelve un ciclo hamiltoniano sobre enlaces físicos. Los costos no se usan como distancias.

Se escoge un resultado determinista según orden de entrada y comparaciones estrictas; no se promete el tour lexicográficamente mínimo. `exact:true` significa óptimo sobre la matriz de caminos mínimos. La heurística termina cuando no detecta mejora >1e-10 o consume el límite de pases: no promete optimalidad ni haber alcanzado un óptimo local cuando agota el presupuesto.

### max_flow

Entrada: `n`, `edges:[{"u":0,"v":1,"capacity":4}]`, `source`, `sink`, `directed` booleano obligatorio. Origen/destino distintos.

Resultado: `value`, `flows:[{"edge_index":0,"flow":4}]`, `source_side` (lado del origen del corte mínimo), `algorithm`. Dirigido: 0 <= flujo <= capacidad. No dirigido: flujo **neto con signo** positivo u→v y negativo v→u; |flujo| <= capacidad compartida. No son dos capacidades independientes instaladas. Un grafo sin ruta devuelve 0. Las demandas no son entradas de este problema.

Capacidades son `double`; Dinic considera agotados residuos <=1e-9, así que valores de ese orden pueden dar cero. Para capacidades extremadamente pequeñas, escala unidades antes de ejecutar. Las verificaciones numéricas deben usar tolerancia. Los Mbit/s de trabajo son enteros y no sufren esa pérdida de escala.

## voronoi

Entrada: `sites:[[x,y],...]`, `domain:[xmin,ymin,xmax,ymax]`, `queries:[[x,y],...]` opcional. Coordenadas **planas**, en una unidad común. Entre 1 y 1000 sitios, hasta 100000 consultas; |coordenada| <=1e7; dominio rectangular de área positiva. No interpreta longitudes/latitudes automáticamente; el conversor documenta su proyección.

Resultado: `cells:[[[x,y],...],...]` en orden de sitios, `nearest:[indice,...]` en orden de consultas. Polígonos convexos en orden antihorario, sin repetir obligatoriamente el primer vértice al final; pueden tener vértices redundantes en degeneraciones. Sitios duplicados exactos: el primer índice conserva la región, los demás reciben `[]`. Las fronteras entre sitios distintos pertenecen a ambos polígonos cerrados; las consultas equidistantes se asignan al menor índice por comparación de distancias cuadradas. Puntos muy próximos a la frontera están sujetos al redondeo de `double`. Consultas fuera del dominio también devuelven el sitio más cercano; el dominio limita los polígonos, no las consultas. Sitios fuera del dominio están permitidos.

## Cadenas

`transmissions` siempre contiene exactamente dos entradas. Cada entrada es una cadena hexadecimal o `{"file":"ruta"}`. `matching` y `strings` requieren además exactamente tres `patterns` con la misma representación. `palindrome` y `common_substring` no requieren firmas. Máximo 2000000 caracteres normalizados por secuencia. Precondición de las funciones internas: cadenas ya normalizadas y de tamaño válido.

Se ignoran CR y LF; **no** espacios ni tabuladores. Solo `0-9 A-F`, sin conversión silenciosa de minúsculas. Se cuentan caracteres hexadecimales, no bytes binarios ni bits. Índices de resultado base 1, finales inclusivos.

| Modo | Campo de resultado |
|---|---|
| `matching` | `matches`: seis objetos `{transmission,pattern,found,position}`; primero tres de T1, luego tres de T2 |
| `palindrome` | `palindromes`: dos `{start,end,length}` |
| `common_substring` | `common:{start,end,start2,end2,length}` |
| `strings` | Los tres campos anteriores |

Ausencia de firma: `found:false, position:0`. Patrón vacío: coincide en posición 1 incluso en transmisión vacía. Palíndromo vacío o ninguna subcadena común: todos los índices y longitud son 0. Empates: menor inicio; en subcadena común, menor inicio en T1 y después menor inicio en T2. Estas convenciones de vacío y ausencia son provisionales.

`--text` solamente con modo `strings`: seis líneas `true posicion` o `false`; dos líneas `inicio fin` de palíndromos; una línea `inicio fin` de subcadena común en T1. Sin encabezados. Intervalo vacío: `0 0`. Coincide con el formato descrito en páginas 13–14 del PDF para casos no vacíos.

## Mediciones y adaptación

`metrics:true` agrega `metrics.algorithm_us` y `metrics.peak_process_bytes` (null si no hay API compatible). Tiempo: llamadas C++ incluyendo validación interna, asignaciones y Dijkstra del TSP; excluye lectura, parseo JSON, normalización y construcción de salida JSON. Memoria: pico del **proceso** hasta antes de imprimir JSON, no memoria aislada del algoritmo.

El PDF solo muestra el sobre `mode`/`input`, sin esquemas completos. Al recibir contrato oficial habrá que mapear nombres de modos, forma del grafo, dirección/capacidades, índices, intervalos, vacíos, desempates, dominio geométrico y errores. Cambios en `protocol.h` y `main.cpp` deben preservar funciones internas; si el modelo oficial difiere (p.ej. TSP dirigido), hará falta también adaptar el algoritmo. Ninguno de estos ejemplos constituye certificación del autograder.
