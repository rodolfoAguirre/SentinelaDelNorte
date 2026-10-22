# Probar el motor en el autograder

El ZIP activa el contrato de la [página Sentinela](https://wagon-wages-83948178.figma.site/#autograder), versión `1.1.0-web`. El ejecutable lee un objeto `{"mode":"mst","input":{...}}` de stdin hasta EOF y devuelve un objeto JSON directo en stdout.

## Ejecutar

1. Genera el paquete con `python tools/package_autograder.py`
2. Arrastra `dist/A0XXXXXX_SENTINEL_DEL_NORTE.zip` al recuadro de la página
3. Escribe **1114129554** como semilla para repetir el reporte anterior
4. Selecciona **normal · 8s** y pulsa **Ejecutar autograder**

Si se deja vacía la semilla, la página genera una y la registra en el reporte. La semilla controla los casos; no se proporciona al ejecutable C++.

La primera ejecución descarga el compilador del sitio. Se suben los fuentes en ZIP, no el ejecutable ni la app Python. Para la entrega formal genera el paquete con `--student-id` y la matrícula de un integrante.

## Contrato de la página

| mode | input | Respuesta |
|---|---|---|
| mst | nodes, edges con u/v/weight | cost, edges como ternas |
| tsp | distances, matriz de costos | cost, route cerrada desde 0 |
| flow | n, edges con u/v/capacity, source, sink | flow |
| voronoi | sites, bounds como [xmin,ymin,xmax,ymax] | cells |
| matching | transmissions, patterns | matches por transmisión y patrón |
| palindrome | transmissions | ranges por transmisión |
| common | transmissions | range en la primera transmisión |

Las posiciones de cadenas son base 1; ausencia se expresa con -1. Las coincidencias usan la primera aparición. `common` y `palindrome` devuelven extremos inclusivos. El adaptador web acepta los textos generales que genera la página y la cantidad variable de patrones.

Ejemplo de entrada:

```json
{"mode":"mst","input":{"nodes":[0,1,2],"edges":[{"u":0,"v":1,"weight":2},{"u":1,"v":2,"weight":3}]}}
```

Respuesta:

```json
{"cost":5,"edges":[[0,1,2],[1,2,3]]}
```

## Diferencia con Streamlit

El ejecutable local conserva el contrato de `docs/CONTRACT.md`, con el sobre `ok/result`, para `app/adapter.py`. Para probar el contrato web localmente, ejecuta `build/sentinela.exe --autograder` y envía el JSON por stdin.

El empaquetador inserta `#define SENTINELA_AUTOGRADER 1` en la copia de `main.cpp` del ZIP. Así el sitio obtiene el contrato web sin argumentos. Los encabezados se copian íntegros. El original local sigue usando el contrato de la app por defecto.

## Diagnóstico y validación

El reporte anterior compiló correctamente pero terminó con `unreachable`. El sitio transforma los `throw` en abortos y elimina los `catch`; nuestro formato provisional rechazaba la primera entrada MST porque esperaba `n` y `cost` en lugar de `nodes` y `weight`.

`results/autograder_native_replay.json` registra 75 casos nativos aprobados usando los generadores y validadores publicados por la página: siete algoritmos, perfil normal y semillas 1114129554, 2038 y 42. Esta reproducción nativa no certifica tiempos ni puntuación del navegador. El contrato final de otro evaluador debe verificarse por separado.

`results/autograder_wasm_replay.json` registra otros 25 casos aprobados con Clang 22.1.8 y el runtime WebAssembly publicados por el sitio, ejecutados desde Node con la semilla 1114129554 y perfil normal. Se aplicaron las mismas transformaciones de encabezados y excepciones de la página. Esto verifica compilación y ejecución WebAssembly; la interfaz del navegador y su puntuación aún requieren una corrida en la página.

Regresiones específicas: `python tests/test_autograder.py`. Incluyen una matriz TSP sin desigualdad triangular, cuatro patrones, texto no hexadecimal contrastado con enumeración y MST de 5000 nodos.

Si falla una corrida, guarda el JSON exportado con la semilla, el perfil y el mensaje completo. Después de cambiar los fuentes, vuelve a generar el ZIP.
