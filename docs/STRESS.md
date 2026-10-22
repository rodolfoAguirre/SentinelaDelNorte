# Pruebas de estrés

Este documento cubre la fase IV del hackathon (*Stress Testing: evalúa el desempeño con distintas instancias y documenta limitaciones*) y la parte de benchmarks de la rúbrica: instancias pequeñas, medianas y grandes, correctitud, tiempo, memoria, escalabilidad y casos límite, de forma reproducible.

Hay dos suites complementarias:

| Suite | Qué prueba | Evidencia |
|---|---|---|
| `tests/stress_algorithms.py` | Contrato local de la app, hasta los **límites máximos** del contrato, con certificados de correctitud | `results/stress_tests.json`, `results/stress_tests.csv` |
| `tests/stress_autograder.py` | Réplica nativa de los casos funcionales y de estrés del autograder web 1.1.0, perfiles `lite`, `normal` y `huge` | `results/stress_autograder.json` |

```bash
python tests/stress_algorithms.py            # completa, ~40 s
python tests/stress_algorithms.py --quick    # sin escala límite ni escalabilidad, ~8 s, no escribe reporte
python tests/stress_autograder.py            # 3 perfiles x 3 semillas, ~20 s
python tests/stress_autograder.py --profiles huge --seeds 1114129554
```

Ambas aceptan la ruta del ejecutable como primer argumento y están registradas en CTest (`stress` en modo rápido y `stress_autograder` con el perfil `huge`).

## Entorno de la corrida registrada

| Elemento | Valor |
|---|---|
| CPU | Intel Core i5-11400H, 12 hilos |
| Sistema | Linux (Fedora), 16 GB RAM |
| Compilador | g++ 16.2.1, CMake Release (`-O3 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic`) |
| Python | 3.14 |
| Semillas | 20261022 (local); 1114129554, 2038 y 42 (autograder) |

## Diseño de `stress_algorithms.py`

Cada caso se ejecuta como proceso independiente con `metrics:true` y debe cumplir tres condiciones: respuesta correcta, menos de **10 s** de reloj y menos de **1 GiB** de pico de memoria del proceso.

### 1. Escalas con certificado de correctitud

| Escala | Nodos | Enlaces | Centrales TSP (heurístico / exacto) | Sitios / consultas Voronoi | Caracteres por transmisión |
|---|---|---|---|---|---|
| pequeña | 12 | 30 | 8 / 8 | 12 / 200 | 80 |
| mediana | 200 | 2 000 | 60 / 12 | 150 / 5 000 | 20 000 |
| grande | 1 000 | 50 000 | 250 / 16 | 500 / 50 000 | 250 000 |
| **límite** | **2 000** | **200 000** | **500 / 18** | **1 000 / 100 000** | **2 000 000** |

La escala límite coincide con los máximos de `docs/CONTRACT.md`. No basta con que el motor responda; cada resultado se verifica con un certificado independiente del código C++:

- **MST:** el conjunto elegido es acíclico, su costo coincide con la suma reportada y con Kruskal escrito en Python; también se comprueban `components` y `connected`. Los costos incluyen negativos.
- **TSP:** el tour visita cada central una vez y cierra en el origen; el recorrido físico usa enlaces que existen, entre nodos consecutivos y en el orden del tour; la suma de distancias físicas es igual a `total_distance`. Con 8 centrales o menos se compara contra fuerza bruta (Floyd–Warshall + permutaciones). Cuando el exacto y el heurístico resuelven el mismo conjunto, se exige exacto ≤ heurístico. También se comprueba que 2-opt converja antes de agotar sus 1000 pases.
- **Flujo máximo (dirigido y no dirigido):** capacidades respetadas, conservación en cada nodo intermedio y **valor del flujo = capacidad del corte** `source_side`. Por el teorema flujo máximo–corte mínimo, esa igualdad demuestra optimalidad sin depender de otra implementación.
- **Voronoi:** las celdas son antihorarias y su área suma la del dominio (tolerancia 1e-7). En 60 celdas muestreadas, cada vértice está al menos tan cerca de su sitio como de cualquier otro. En 2 000 consultas muestreadas, incluidas algunas fuera del dominio, se compara contra fuerza bruta con desempate por menor índice.
- **Cadenas:** las firmas se comparan con `str.find`; los palíndromos con un Manacher independiente sobre texto intercalado con `#` (otra formulación distinta a la del motor), incluido el desempate. La subcadena común se verifica con *hashing* rodante: no existe una común de longitud L+1, el inicio reportado en T1 es la primera ventana de longitud L presente en T2 y el inicio en T2 es la primera aparición. Así quedan comprobados la maximalidad y los dos desempates.

### 2. Casos adversariales

| Caso | Qué fuerza |
|---|---|
| MST con 1 000 componentes | Bosque, `connected:false` |
| MST en grafo completo de 300 nodos con pesos iguales | Desempate estable por índice (44 850 empates) |
| 2 000 enlaces paralelos con costos negativos | Multigrafo y negativos |
| TSP en línea de 2 000 nodos con 500 centrales | Tránsito físico repetido; óptimo conocido (ir y volver) |
| TSP en estrella con 18 centrales | Held–Karp en su límite, óptimo conocido |
| Flujo en cadena de 2 000 nodos | Profundidad máxima de la recursión de Dinic |
| Flujo en 39 capas de 50 nodos con capacidades unitarias (95k enlaces) | Muchos caminos de aumento de igual longitud |
| Flujo sin camino | Valor 0 |
| Voronoi con 1 000 sitios colineales | Celdas degeneradas en franjas; 999 consultas exactamente equidistantes |
| Voronoi en rejilla de 992 sitios | Vértices donde coinciden 4 regiones |
| Voronoi con 1 000 sitios, solo 2 distintos | Duplicados exactos: solo el primero conserva región |
| Un sitio en la coordenada máxima 1e7 | Magnitudes extremas |
| `A` × 2M en ambas transmisiones | Palíndromo y subcadena común de longitud total; peor caso de KMP (`A…AB`) |
| `ABAB…` frente a `BABA…`, 2M | Empates de longitud n−1 en palíndromo y subcadena común |
| Transmisiones vacías, patrón vacío, patrón más largo que el texto | Convenciones de vacío |
| Texto periódico `ABC…` de 250k | Autómata con muchas transiciones compartidas |

### 3. Rechazo de entradas fuera del contrato

Trece entradas exceden cada límite por una unidad: 2 001 nodos, 200 001 enlaces, peso 1e13, 501 centrales, `exact_limit` 19, centrales desconectadas, capacidad negativa, 1 001 sitios, 100 001 consultas, coordenada 1e8, 2 000 001 caracteres, minúsculas y espacios. En todos los casos el motor responde `ok:false` con un mensaje, código de salida 1 y sin colapsar.

### 4. Escalabilidad frente a la complejidad teórica

Se duplica el tamaño cuatro veces y se ajusta la pendiente de log(tiempo) contra log(tamaño), usando la mediana de 3 repeticiones del tiempo interno `algorithm_us`. Una pendiente de 1 corresponde a crecimiento lineal y una de 2, cuadrático.

| Algoritmo | Tamaños | Tiempo interno (s) | Pendiente | Teoría |
|---|---|---|---|---|
| MST (Kruskal) | E = 25k → 200k | 0.002 → 0.027 | 1.19 | O(E log E) → ≈1.1 |
| Flujo (Dinic) | E = 25k → 200k | 0.004 → 0.026 | 0.97 | O(V²E) peor caso; en grafos aleatorios pocas fases |
| TSP heurístico | k = 62 → 500 | 0.040 → 0.318 | 1.00 | O(k(V+E) log V) domina los Dijkstra |
| TSP Held–Karp | k = 12 → 18 | 0.008 → 0.093 | — | O(2^k k²): ×3.3 por cada 2 centrales |
| Voronoi | n = 125 → 1000 | 0.001 → 0.070 | 1.96 | O(n²·m), m = vértices por celda ≈ constante |
| Firmas (KMP) | 250k → 2M | 0.002 → 0.012 | 1.00 | O(n + m) |
| Palíndromo (Manacher) | 250k → 2M | 0.004 → 0.036 | 1.02 | O(n) |
| Subcadena común (autómata) | 250k → 2M | 0.105 → 1.48 | 1.21 | O(n·σ), σ = 16 |

Las pendientes coinciden con la teoría. La excepción moderada es el autómata de sufijos: es lineal en operaciones, pero cada estado ocupa 76 bytes y el acceso a ~4M estados es aleatorio, por lo que el tiempo crece algo más que linealmente debido a fallos de caché.

## Resultados

- **`stress_algorithms.py`:** 155 ejecuciones aprobadas en ~40 s. La más lenta fue el TSP heurístico con 500 centrales sobre 200k enlaces (1.6–2.1 s, de los cuales ~1.9 s son 500 Dijkstra). El mayor pico de memoria fue el flujo máximo con 200k enlaces (279 MB).
- **`stress_autograder.py`:** 225/225 casos aprobados (3 perfiles × 3 semillas × 25 casos). En el perfil `huge`, el caso más lento tardó 0.08 s frente al límite de 18 s del sitio.

Escala límite, en una corrida:

| Caso | Reloj del proceso | Algoritmo | Pico de memoria | Tamaño del JSON |
|---|---|---|---|---|
| MST 2 000 / 200k | 0.16 s | 0.02 s | 102 MB | 6.8 MB |
| TSP heurístico 500 centrales | 2.08 s | 1.94 s | 119 MB | 7.6 MB |
| TSP exacto 18 centrales | 0.29 s | 0.13 s | 131 MB | 7.6 MB |
| Flujo dirigido 200k | 0.53 s | 0.02 s | 278 MB | 7.6 MB |
| Voronoi 1 000 sitios / 100k consultas | 0.33 s | 0.22 s | 47 MB | 3.9 MB |
| Cadenas 2 × 2M | 1.51 s | 1.48 s | 233 MB | 3.8 MB |

## Hallazgo corregido durante las pruebas

En Linux, `peak_process_bytes` usaba `getrusage(RUSAGE_SELF).ru_maxrss`. Ese valor **se hereda del proceso padre a través de `exec`**: un caso trivial lanzado desde Python con cadenas grandes en memoria reportaba 298 MB en lugar de 4 MB. `src/metrics.h` ahora lee `VmHWM` de `/proc/self/status`, que se reinicia con cada imagen del proceso, y conserva `getrusage` como respaldo. Windows (`PeakWorkingSetSize`) no tenía este problema. Las mediciones de memoria anteriores en Linux deben descartarse.

## Limitaciones documentadas

1. **El JSON domina la memoria y el tiempo en grafos grandes.** Con 200k enlaces, Dinic tarda 18 ms, pero el proceso completo tarda 0.5 s y alcanza 278 MB. El costo principal está en el árbol JSON (`std::map` y `std::variant` por objeto) de entrada y en los 200k objetos `flows` de salida, no en el algoritmo. Un lector en streaming o un formato columnar reduciría ese costo si los límites crecieran.
2. **Memoria del autómata de sufijos.** A 2M caracteres usa ~4M estados × 76 B ≈ 230 MB y 1.5 s. Un arreglo de sufijos (SA-IS) + LCP sobre la concatenación usaría ~50 MB, a cambio de un desempate más complejo de implementar. Con los límites actuales cabe holgadamente en el presupuesto.
3. **TSP heurístico.** Con 500 centrales, el 85 % del tiempo corresponde a los k Dijkstra que construyen la matriz de caminos mínimos. 2-opt converge en todos los casos medidos antes del límite de pases, pero no garantiza el óptimo ni una cota de aproximación.
4. **Held–Karp es exponencial.** 18 centrales es el máximo del contrato (≈0.1 s y ~28 MB de tabla). Cada central adicional duplica la memoria y más que duplica el tiempo, por lo que no conviene subir `exact_limit`.
5. **Voronoi es cuadrático.** Con 1 000 sitios toma 0.07–0.2 s. Para decenas de miles de sitios se necesitaría Fortune, O(n log n), o una triangulación de Delaunay.
6. **Alcance de la medición.** `algorithm_us` excluye el parseo y la serialización JSON, mientras que el reloj del proceso los incluye. El pico de memoria corresponde al proceso, no aislado por algoritmo. Las mediciones son de un solo equipo; el autograder corre en WebAssembly dentro del navegador, normalmente más lento que el binario nativo. En el perfil `huge`, el margen frente a sus límites supera 200×.
