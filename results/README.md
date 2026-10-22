# Resultados reales del avance

## Pruebas

Estado: **PASS**, 7 grupos, 846 invocaciones del motor mediante el helper (más ocho entradas JSON malformadas), 0 fallos y 0 errores. Tiempo total de suite: 56.014 s. Semillas: [2038, 2039, 2040, 2041, 2042]. Detalle en `tests.json`, salida de CTest en `ctest.log` y compilación en `build.log`. Los hashes identifican el ejecutable y los fuentes medidos; los tiempos varían entre corridas.

Referencias independientes: enumeración de subcadenas y `str.find`, Prim, permutaciones TSP con Floyd–Warshall, enumeración de cortes s-testReport, y propiedades de región/cercanía/área para Voronoi. Incluye casos vacíos, empates, duplicados, desconexión, enlaces paralelos/antiparalelos, flujo firmado, errores de archivos, formato texto y datos de trabajo GÉANT.

## Entorno y procedimiento

- Sistema: Windows-11-10.0.26300-SP0.
- Procesador reportado por el sistema: Intel64 Family 6 Model 154 Stepping 3, GenuineIntel; 12 procesadores lógicos.
- Compilador: GNU 15.2.0 (MinGW incluido en CLion); C++17, Release `-O3 -DNDEBUG -Wall -Wextra -Wpedantic`.
- Python: 3.12.14. Benchmark generado en UTC: 2026-10-21T23:34:29.600517+00:00.
- Semilla 2038; 3 procesos nuevos por configuración; 27 configuraciones. No se descarta calentamiento: se reporta mediana de las tres corridas. No se controla afinidad ni carga externa.
- Ejecutar `python tools/benchmark.py build/sentinela.exe`; `benchmarks.json` conserva muestras crudas, `benchmarks.csv` el resumen.
- `algorithm_us`: reloj C++ `steady_clock` alrededor del algoritmo; incluye validación interna, estructuras temporales y caminos mínimos del TSP. Excluye stdin, JSON, normalización y construcción de objetos de respuesta.
- `process_wall_us`: tiempo Python de arranque, I/O, cálculo y cierre completo; no debe confundirse con algoritmo.
- Memoria: pico de working set del proceso consultado antes de imprimir JSON. Incluye runtime, entrada y objetos de resultado; no es memoria auxiliar aislada. No captura un eventual pico posterior de serialización ni memoria de Python. Se mide, no se estima mediante fórmulas.

## Mediciones

Tiempos en microsegundos (mediana); memoria en MiB (máximo de tres picos).

| Algoritmo | Tamaño | Familia | Tiempo algoritmo µs | Pico proceso MiB |
|---|---:|---|---:|---:|
| mst | 100 | sparse ~4V | 25.00 | 4.77 |
| mst | 500 | sparse ~4V | 147.00 | 5.62 |
| mst | 2000 | sparse ~4V | 670.40 | 8.87 |
| tsp | 8 | exact | 43.50 | 4.58 |
| tsp | 12 | exact | 718.40 | 4.86 |
| tsp | 16 | exact | 15145.80 | 10.57 |
| tsp | 20 | heuristic | 65.30 | 4.59 |
| tsp | 100 | heuristic | 1015.40 | 4.84 |
| tsp | 300 | heuristic | 18967.70 | 6.55 |
| max_flow | 20 | sparse ~6V | 73.90 | 4.75 |
| max_flow | 100 | sparse ~6V | 248.00 | 5.59 |
| max_flow | 400 | sparse ~6V | 778.50 | 8.38 |
| voronoi | 20 | uniform sites | 292.90 | 4.65 |
| voronoi | 100 | uniform sites | 3582.50 | 4.94 |
| voronoi | 300 | uniform sites | 13582.20 | 5.84 |
| matching | 1000 | random hex; matching patterns intentionally rare | 31.70 | 4.55 |
| palindrome | 1000 | random hex; matching patterns intentionally rare | 32.30 | 4.54 |
| common_substring | 1000 | random hex; matching patterns intentionally rare | 134.20 | 4.64 |
| matching | 10000 | random hex; matching patterns intentionally rare | 149.50 | 4.61 |
| palindrome | 10000 | random hex; matching patterns intentionally rare | 274.50 | 4.68 |
| common_substring | 10000 | random hex; matching patterns intentionally rare | 1305.60 | 5.74 |
| matching | 100000 | random hex; matching patterns intentionally rare | 1365.40 | 5.26 |
| palindrome | 100000 | random hex; matching patterns intentionally rare | 2520.20 | 6.02 |
| common_substring | 100000 | random hex; matching patterns intentionally rare | 13069.50 | 16.03 |
| matching | 100000 | repeated hex | 1146.50 | 5.27 |
| palindrome | 100000 | repeated hex | 4922.60 | 6.02 |
| common_substring | 100000 | repeated hex | 5221.80 | 13.14 |

Tamaño significa V para grafos, centrales seleccionadas para TSP, sitios para Voronoi y caracteres por transmisión para cadenas. El benchmark usa grafos sintéticos dispersos; las tres series del TSP exacto y las tres del heurístico son comparables dentro de cada familia, no como calidad sobre una misma instancia. KMP usa firmas raras para evitar que el algoritmo siempre termine al principio del texto. Las cadenas uniformes son una familia adicional.

## Comparación con el análisis teórico

Held–Karp aumenta mucho más rápido que los métodos de cadenas al crecer su entrada: la tabla exponencial domina a partir de k mayores. La heurística permite llegar a 300 centrales, pero el tiempo depende del número de mejoras y no garantiza el óptimo. No se extrapolan estos tiempos a k enormes.

En cadenas, la cota es lineal en tamaño, pero los cocientes medidos no son exactamente 10 por cada aumento de 10 veces. La construcción del autómata tiene constantes altas, más estados/transiciones y efectos de caché; cadenas repetitivas producen menos estados que aleatorias. Los tiempos muy pequeños también sufren ruido del sistema. Las mediciones no prueban una complejidad distinta de la deducida del código.

Kruskal sobre grafos dispersos refleja principalmente ordenar aristas; Dinic sobre estos grafos no alcanza necesariamente su peor caso O(V²E). Voronoi crece más rápido que lineal y su cota conservadora de recortes es cúbica; los sitios uniformes suelen mantener polígonos pequeños y no demuestran esa cota ajustada. El baseline de memoria del proceso oculta diferencias pequeñas, por lo que no se interpreta como memoria auxiliar de los algoritmos.

Estas son mediciones de laboratorio en este equipo, sin repeticiones suficientes para inferencia estadística ni garantías de rendimiento en el autograder. No se midieron WebAssembly, otros compiladores, datos oficiales ausentes ni memoria aislada por algoritmo.

## Ejecuciones sobre los archivos de trabajo

`python tests/stress_algorithms.py` lleva los siete algoritmos hasta los límites del contrato, con certificados de correctitud, casos adversariales, rechazos y ajuste de escalabilidad; guarda cada ejecución en `results/stress_tests.json` y `results/stress_tests.csv`. `python tests/stress_autograder.py` replica el autograder web (perfiles `lite`, `normal`, `huge`) y guarda `results/stress_autograder.json`. Los tiempos de proceso incluyen el inicio del ejecutable y el transporte JSON, a diferencia del benchmark interno de este documento. Detalles y limitaciones en [docs/STRESS.md](../docs/STRESS.md). Las mediciones de memoria en Linux anteriores a la corrección de `src/metrics.h` (ver ese documento) heredaban el pico del proceso padre.

Los archivos `*.geant.output.json` conservan resultados reales. Con un módulo **supuesto** por enlace: MST de 21 enlaces con costo total 16246 (unidades de costo no especificadas); flujo Austria→Alemania 160000 Mbit/s en escenario no dirigido; TSP de 22 centrales heurístico con distancia aproximada 29760.148 km por caminos existentes. No son mediciones de una red instalada ni resultados oficiales del profesor. Voronoi devuelve polígonos del dominio rectangular derivado.
