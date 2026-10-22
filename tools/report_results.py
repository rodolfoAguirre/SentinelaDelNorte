# Resume las mediciones registradas
# Autores: pendientes | Matriculas: pendientes
# Modificacion: 2026-10-21

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
benchmarkReport = json.loads((ROOT/'results/benchmarks.json').read_text(encoding='utf-8'))
testReport = json.loads((ROOT/'results/tests.json').read_text(encoding='utf-8'))
rows = benchmarkReport['measurements']
summary = f'''# Resultados reales del avance

## Pruebas

Estado: **{'PASS' if testReport['success'] else 'FAIL'}**, {testReport['test_groups']} grupos, {testReport['engine_calls']} invocaciones del motor mediante el helper (más ocho entradas JSON malformadas), {testReport['failures']} fallos y {testReport['errors']} errores. Tiempo total de suite: {testReport['elapsed_seconds']:.3f} s. Semillas: {testReport['seeds']}. Detalle en `tests.json`, salida de CTest en `ctest.log` y compilación en `build.log`. Los hashes identifican el ejecutable y los fuentes medidos; los tiempos varían entre corridas.

Referencias independientes: enumeración de subcadenas y `str.find`, Prim, permutaciones TSP con Floyd–Warshall, enumeración de cortes s-testReport, y propiedades de región/cercanía/área para Voronoi. Incluye casos vacíos, empates, duplicados, desconexión, enlaces paralelos/antiparalelos, flujo firmado, errores de archivos, formato texto y datos de trabajo GÉANT.

## Entorno y procedimiento

- Sistema: {benchmarkReport['platform']}.
- Procesador reportado por el sistema: {benchmarkReport['processor']}; {benchmarkReport['cpu_count']} procesadores lógicos.
- Compilador: GNU 15.2.0 (MinGW incluido en CLion); C++17, Release `-O3 -DNDEBUG -Wall -Wextra -Wpedantic`.
- Python: {benchmarkReport['python']}. Benchmark generado en UTC: {benchmarkReport['timestamp_utc']}.
- Semilla {benchmarkReport['seed']}; {benchmarkReport['repetitions']} procesos nuevos por configuración; {len(rows)} configuraciones. No se descarta calentamiento: se reporta mediana de las tres corridas. No se controla afinidad ni carga externa.
- Ejecutar `python tools/benchmark.py build/sentinela.exe`; `benchmarks.json` conserva muestras crudas, `benchmarks.csv` el resumen.
- `algorithm_us`: reloj C++ `steady_clock` alrededor del algoritmo; incluye validación interna, estructuras temporales y caminos mínimos del TSP. Excluye stdin, JSON, normalización y construcción de objetos de respuesta.
- `process_wall_us`: tiempo Python de arranque, I/O, cálculo y cierre completo; no debe confundirse con algoritmo.
- Memoria: pico de working set del proceso consultado antes de imprimir JSON. Incluye runtime, entrada y objetos de resultado; no es memoria auxiliar aislada. No captura un eventual pico posterior de serialización ni memoria de Python. Se mide, no se estima mediante fórmulas.

## Mediciones

Tiempos en microsegundos (mediana); memoria en MiB (máximo de tres picos).

| Algoritmo | Tamaño | Familia | Tiempo algoritmo µs | Pico proceso MiB |

'''
for measurement in rows:
    memoryLabel = 'no disponible' if measurement['max_peak_process_bytes'] is None else f"{measurement['max_peak_process_bytes']/1048576:.2f}"
    summary += f"| {measurement['mode']} | {measurement['size']} | {measurement['kind']} | {measurement['median_algorithm_us']:.2f} | {memoryLabel} |\n"
summary += '''
Tamaño significa V para grafos, centrales seleccionadas para TSP, sitios para Voronoi y caracteres por transmisión para cadenas. El benchmark usa grafos sintéticos dispersos; las tres series del TSP exacto y las tres del heurístico son comparables dentro de cada familia, no como calidad sobre una misma instancia. KMP usa firmas raras para evitar que el algoritmo siempre termine al principio del texto. Las cadenas uniformes son una familia adicional.

## Comparación con el análisis teórico

Held–Karp aumenta mucho más rápido que los métodos de cadenas al crecer su entrada: la tabla exponencial domina a partir de k mayores. La heurística permite llegar a 300 centrales, pero el tiempo depende del número de mejoras y no garantiza el óptimo. No se extrapolan estos tiempos a k enormes.

En cadenas, la cota es lineal en tamaño, pero los cocientes medidos no son exactamente 10 por cada aumento de 10 veces. La construcción del autómata tiene constantes altas, más estados/transiciones y efectos de caché; cadenas repetitivas producen menos estados que aleatorias. Los tiempos muy pequeños también sufren ruido del sistema. Las mediciones no prueban una complejidad distinta de la deducida del código.

Kruskal sobre grafos dispersos refleja principalmente ordenar aristas; Dinic sobre estos grafos no alcanza necesariamente su peor caso O(V²E). Voronoi crece más rápido que lineal y su cota conservadora de recortes es cúbica; los sitios uniformes suelen mantener polígonos pequeños y no demuestran esa cota ajustada. El baseline de memoria del proceso oculta diferencias pequeñas, por lo que no se interpreta como memoria auxiliar de los algoritmos.

Estas son mediciones de laboratorio en este equipo, sin repeticiones suficientes para inferencia estadística ni garantías de rendimiento en el autograder. No se midieron WebAssembly, otros compiladores, datos oficiales ausentes ni memoria aislada por algoritmo.

## Ejecuciones sobre los archivos de trabajo

Los archivos `*.geant.output.json` conservan resultados reales. Con un módulo
 **supuesto** por enlace: MST de 21 enlaces con costo total 16246 
 (unidades de costo no especificadas); flujo Austria→Alemania 160000 Mbit/s en 
 escenario no dirigido; TSP de 22 centrales heurístico con distancia aproximada 
 29760.148 km por caminos existentes. No son mediciones de una red instalada ni 
 resultados oficiales del profesor. Voronoi devuelve polígonos del dominio rectangular 
 derivado.
'''
(ROOT/'results/README.md').write_text(summary, encoding='utf-8')
print('Wrote results/README.md from recorded measurements.')

