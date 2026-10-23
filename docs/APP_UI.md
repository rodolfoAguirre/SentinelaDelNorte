# Sentinela del Norte: documentación de la app y su interfaz

Esta guía describe la interfaz implementada en Streamlit, su uso y los archivos que la construyen. Está dirigida a quienes presentarán la aplicación y a quienes continuarán desarrollándola.

## 1. Propósito y alcance

La app permite explorar escenarios de la red GÉANT y analizar transmisiones hexadecimales. Su prioridad es mostrar **resultados comprensibles y métricas de ejecución** de los siete algoritmos del motor C++.

El usuario configura un escenario, pulsa **Ejecutar análisis** y consulta sus resultados mediante mapas, animaciones, tablas y fragmentos resaltados. También puede descargar la solicitud, la respuesta y sus métricas.

La topología es histórica y los escenarios tienen supuestos documentados. Las transmisiones iniciales son ejemplos ilustrativos. La herramienta permite estudiar esos escenarios; sus resultados deben interpretarse con esa procedencia.

## 2. Instalación y arranque

### En esta computadora

Desde la raíz del proyecto:

```powershell
python iniciar_app.py
```

El lanzador da prioridad al entorno `.venv` cuando se ejecuta desde Python global. También se puede iniciar explícitamente con:

```powershell
.\.venv\Scripts\python.exe iniciar_app.py
```

Abre la dirección que indique la terminal, normalmente `http://127.0.0.1:8501`. Si ese puerto está ocupado, el lanzador busca otro hasta 8510. **Conserva la terminal abierta** mientras uses la app. Para detenerla, pulsa **Ctrl+C** en esa terminal.

El lanzador sirve la aplicación en la computadora local. La dirección `127.0.0.1` apunta a esa misma computadora, no permite entrar desde otra PC.

### En una instalación nueva

Necesitas un motor C++ compilado para el sistema de destino y un entorno Python con las dependencias de `app/requirements.txt`. El entorno utilizado para comprobar esta interfaz es Python 3.12.

Si tienes Python 3.12 registrado en el lanzador de Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements.txt
.\.venv\Scripts\python.exe iniciar_app.py
```

Si `py -3.12` no está disponible, instala esa versión o utiliza su ejecutable mediante una ruta explícita para crear el entorno. La compilación del motor se explica en el [README principal](../README.md).

No copies `.venv` ni `.venv-deps` entre computadoras o versiones de Python. NumPy y otras dependencias contienen módulos compilados: un archivo `cp312` corresponde a CPython 3.12 y no se puede cargar directamente desde Python 3.15. El lanzador solo admite la carpeta alternativa `.venv-deps` cuando su extensión NumPy coincide con el intérprete actual.

## 3. Organización de la pantalla

| Sección | Función |
|---|---|
| Centro de análisis, en la barra lateral | Seleccionar el algoritmo o el análisis conjunto |
| Encabezado | Identificar el proyecto y su propósito |
| Datos y supuestos | Consultar el contexto del escenario de red |
| Configurar escenario | Elegir centrales, origen y destino o textos de entrada |
| Ejecutar análisis | Enviar una nueva solicitud al motor C++ |
| Métricas de ejecución | Mostrar tiempo del algoritmo, tiempo total y memoria |
| Resultados del análisis | Interpretar la solución y explorar sus visualizaciones |
| Detalle del resultado | Consultar tablas con nombres legibles y unidades |
| Entrada utilizada y respuesta completa | Inspeccionar el JSON técnico de esa ejecución |
| Descargar resultado y métricas | Exportar la ejecución en JSON |

En ventanas estrechas, la barra lateral puede aparecer contraída. Utiliza el botón de expansión para cambiar de análisis.

## 4. Flujo de uso

1. Selecciona un análisis en la barra lateral
2. Revisa el escenario y configura los campos disponibles
3. Pulsa **Ejecutar análisis**
4. Consulta las métricas y la interpretación del resultado
5. Explora el mapa, la animación, el diagrama o los fragmentos de texto
6. Revisa la tabla y descarga el JSON si necesitas conservar la ejecución

Los resultados se conservan por análisis durante la sesión. Cambiar una opción del mapa no vuelve a ejecutar el motor. Los campos del formulario se envían al pulsar **Ejecutar análisis**; vuelve a pulsarlo cuando quieras calcular con otros datos.

Las tablas y tarjetas muestran el resultado completo de la última ejecución aunque la animación esté a mitad de su reproducción. El paso de animación solo limita los elementos resaltados en el mapa.

## 5. Vistas disponibles y significado de sus resultados

### Conexiones de menor costo · MST

Utiliza el escenario de costos preparado para GÉANT. El resultado selecciona conexiones que minimizan el costo total sin formar ciclos.

La tarjeta principal muestra el costo total. También aparecen el número de enlaces elegidos y de componentes conectadas. Si la red estuviera desconectada, se informa que el resultado es un bosque mínimo.

| Columna | Significado |
|---|---|
| Orden de selección | Posición del enlace entre las conexiones aceptadas por Kruskal |
| Central A / Central B | Extremos de la conexión, con ubicación e identificador |
| Costo del enlace | Costo asignado a esa conexión en el escenario |
| Costo acumulado | Suma de los costos hasta esa fila |

La unidad monetaria no está especificada en el XML original. La app no etiqueta el costo con una moneda inventada.

### Ruta de mantenimiento · TSP

Permite seleccionar las centrales que deben visitarse. La solución vuelve al origen y muestra distancia total, orden de visita y si el cálculo es exacto o heurístico.

La tabla contiene **Tramo**, **Desde**, **Hasta** y **Distancia (km)**. Cada fila representa una conexión física recorrida. Los nodos intermedios pueden repetirse al trasladarse entre las visitas de mantenimiento.

Las instancias grandes usan una heurística: el resultado es una ruta válida, pero no garantiza la mejor distancia posible. La interfaz comunica esta condición.

### Capacidad de transporte · Flujo máximo

Permite elegir una central de origen y otra de destino. Deben ser distintas. La tarjeta principal indica el máximo flujo que puede transportarse simultáneamente entre ellas, bajo las capacidades del escenario.

| Columna | Significado |
|---|---|
| Desde / Hasta | Dirección real en la que circula el flujo de esa conexión |
| Flujo enviado (Mbit/s) | Magnitud del flujo asignado al enlace |
| Capacidad (Mbit/s) | Máximo permitido por el escenario |
| Uso de capacidad (%) | Flujo enviado dividido entre capacidad, multiplicado por 100 |
| Estado | Si el enlace transporta flujo o permanece sin flujo |

Mbit/s significa megabits por segundo. No sumes todas las filas para obtener el flujo total: un mismo tráfico puede recorrer varios enlaces. Los flujos negativos del contrato se traducen a una dirección comprensible y una magnitud positiva en la tabla.

### Regiones de proximidad · Voronoi

Muestra las regiones del dominio que están más cerca de cada central en el plano del escenario. Cada región recibe un color.

La tabla indica la **Central responsable**, el **Área en el plano (km²)** y su **Estado**. El área se calcula sobre el polígono plano del resultado. La visualización geográfica transforma esas coordenadas a longitud y latitud con la proyección inversa del escenario.

Las regiones representan proximidad geométrica aproximada, no cobertura real de antenas, capacidad de transporte ni distancia de viaje por la red.

### Transmisiones y firmas

Hay cuatro vistas: análisis conjunto, KMP, Manacher y subcadena común. Las vistas individuales permiten medir cada algoritmo por separado.

Se pueden editar las dos transmisiones o cargar archivos TXT. Cuando se carga un archivo, su contenido tiene prioridad sobre el texto del campo correspondiente. Las firmas se introducen en sus campos de texto. La interfaz conserva actualmente esos campos en las cuatro vistas, aunque las firmas solo intervienen en KMP y en el análisis conjunto.

Se acepta hexadecimal en mayúsculas: `0–9 A–F`. Se eliminan CR/LF; se rechazan espacios, minúsculas y BOM.

| Resultado | Lectura de la interfaz |
|---|---|
| Firmas | Transmisión, firma buscada, encontrada o ausente y primera posición |
| Palíndromos | Transmisión, inicio, final incluido y longitud en caracteres |
| Subcadena común | Longitud del fragmento e intervalo en cada transmisión |

Las posiciones empiezan en 1 y los extremos son inclusivos. Por ejemplo, un intervalo 3–6 contiene cuatro caracteres. Los intervalos vacíos del contrato usan 0–0 y longitud 0.

Las coincidencias se resaltan junto con algo de contexto. Se muestran como máximo 160 caracteres del fragmento resaltado; una elipsis indica que la vista previa se truncó. El resultado y la descarga mantienen la longitud completa. Los caracteres del usuario se escapan antes de incluirlos en el HTML de la vista previa.

## 6. Mapa geográfico

El mapa utiliza Pydeck y un fondo CARTO con atribución a OpenStreetMap/CARTO. Las centrales se colocan con sus coordenadas geográficas originales.

| Control o gesto | Comportamiento |
|---|---|
| Arrastrar | Desplazar el mapa |
| Rueda o controles de zoom | Acercar o alejar |
| Encuadre | Centrar Europa, Norteamérica o toda la red |
| Red completa | Mostrar las conexiones de base, además de las resaltadas |
| Etiquetas | Mostrar u ocultar los identificadores de centrales |
| Cursor sobre un elemento | Consultar sus detalles |
| Seleccionar una central | Mostrar su ubicación, coordenadas y función en el escenario |

El verde resalta las conexiones del resultado que ya se revelaron. En flujo, el grosor de los enlaces activos depende de su utilización; el origen es amarillo y el destino rosado. En TSP, la posición actual del recorrido se marca en amarillo. Las regiones Voronoi tienen colores diferenciados.

Las líneas conectan los extremos geográficos; no son trazados medidos de fibra. El encuadre de Europa puede dejar fuera Nueva York: utiliza **Toda la red** o **Norteamérica** para consultarlo.

El fondo cartográfico necesita internet. La pestaña **Diagrama del escenario** conserva una representación SVG del resultado que no necesita descargar ese fondo. El cálculo algorítmico se ejecuta localmente.

## 7. Animación y reproducción por pasos

Después de calcular un resultado de red, comienza su presentación progresiva con aproximadamente 0.7 segundos entre pasos. El ritmo real puede variar por el navegador o la carga del equipo.

| Análisis | Orden de presentación |
|---|---|
| MST | Orden de los enlaces aceptados por Kruskal |
| TSP | Orden de las conexiones del recorrido físico |
| Flujo máximo | Enlaces con flujo distinto de cero, según el orden de la respuesta |
| Voronoi | Regiones en el orden de las centrales |

En flujo y Voronoi se revela el resultado final, sin reproducir las operaciones internas de Dinic o los recortes de polígonos. MST presenta las conexiones aceptadas; no muestra los enlaces descartados durante la búsqueda.

| Botón | Función |
|---|---|
| Reproducir / Pausar | Continuar o detener la presentación |
| Reiniciar | Volver al paso cero y reproducir |
| Anterior | Retroceder un paso y pausar |
| Siguiente | Avanzar un paso y pausar |
| Ver todo | Mostrar el resultado completo y pausar |

Una barra indica **Paso X de Y** y una frase explica la conexión o región actual. Al llegar al último paso, la reproducción termina automáticamente. En TSP, un enlace físico repetido permanece resaltado, mientras que la descripción del paso sigue el recorrido completo.

La animación utiliza fragmentos temporizados de Streamlit: actualiza el mapa y sus controles sin volver a llamar al motor. Su duración no se suma a los tiempos del algoritmo ni de la llamada.

## 8. Métricas de ejecución

| Tarjeta | Qué mide | Unidad |
|---|---|---|
| Tiempo del algoritmo C++ | Cálculo y preparación interna cronometrados en el motor | Milisegundos, ms |
| Tiempo total de la llamada | Llamada desde Python, incluido arranque del proceso y transporte JSON | Milisegundos, ms |
| Pico de memoria del proceso | Máxima memoria del proceso C++ consultada por la API disponible | Mebibytes, MiB |

1000 ms equivalen a 1 segundo. Un MiB equivale a 1 048 576 bytes.

La memoria incluye el proceso completo y no es memoria exclusiva del algoritmo. Si no existe una medición compatible, se muestra **No disponible**. El tiempo total de la llamada no incluye el dibujo del mapa ni la reproducción visual posterior.

En el análisis conjunto de cadenas, el tiempo C++ suma KMP, Manacher y subcadena común. Selecciona una vista individual para comparar sus tiempos por separado. Distintas ejecuciones pueden variar por la carga del equipo y los costos de arranque.

## 9. Exportación y persistencia

**Descargar resultado y métricas** genera `sentinela_<modo>.json` con:

- `request`: modo y datos realmente utilizados
- `response`: respuesta original del motor, incluido `result` y `metrics`
- `total_seconds`: duración total de la llamada Python, en segundos

La exportación conserva las claves técnicas del contrato para permitir reproducir la solicitud. Las tablas de pantalla utilizan etiquetas legibles y no cambian el contrato del backend.

Los resultados y el progreso de reproducción se conservan por modo en `st.session_state`. No hay una base de datos ni un historial persistente: una sesión nueva no garantiza recuperar resultados anteriores. Descarga el JSON para conservarlos.

## 10. Archivos que construyen la interfaz

| Archivo | Responsabilidad |
|---|---|
| `iniciar_app.py` | Elegir el entorno, comprobar dependencias e iniciar el servidor local |
| `app/streamlit_app.py` | Formularios, ejecución, métricas, resultados, tablas y exportación |
| `app/visuals.py` | Estilos, capas geográficas, controles del mapa y animación |
| `app/presentation.py` | Nombres comprensibles de centrales y filas de resultados |
| `app/adapter.py` | Validación del transporte y comunicación JSON con el motor |
| `.streamlit/config.toml` | Tema oscuro, colores principales y tipografía |
| `app/requirements.txt` | Dependencias directas de la interfaz |
| `data/derived/nodes.csv` | IDs y coordenadas de centrales |
| `data/derived/*.input.json` | Escenarios iniciales de los algoritmos de red |
| `data/derived/scenarios.json` | Proyección y supuestos del escenario |
| `data/synthetic/` | Transmisiones y firmas iniciales ilustrativas |

La paleta usa fondo azul oscuro, paneles diferenciados y acentos verdes. Las tarjetas agrupan mediciones con sus unidades. Las tablas traducen índices internos a ubicaciones e identificadores para mantener trazabilidad.

Las claves principales de sesión son `result_<modo>` para entrada, respuesta y tiempo total, y `animation_<modo>` para posición, reproducción y próximo avance. Los controles de mapa tienen claves por modo.

## 11. Cómo continuar el desarrollo

- Para cambiar títulos, explicaciones, formularios o tarjetas, modifica `app/streamlit_app.py`
- Para cambiar columnas o nombres visibles, modifica `resultRows` y `centralName` en `app/presentation.py`
- Para agregar capas o cambiar colores y detalles del mapa, modifica `buildMap` en `app/visuals.py`
- Para modificar controles y reproducción, revisa `showMap` y `animationSequence` en ese mismo archivo
- Para cambiar el estilo general, revisa `.streamlit/config.toml` y `applyTheme`

Mantén las llamadas al motor asociadas al envío del formulario. El movimiento del mapa y los fotogramas deben conservar las métricas de la ejecución original. Al cambiar entradas, conserva su copia junto al resultado para que el usuario pueda saber exactamente qué se calculó.

Las regiones del motor usan coordenadas planas; aplica la transformación inversa definida por `scenarios.json` al dibujarlas. Cambiar el fondo geográfico no modifica el modelo matemático de Voronoi.

## 12. Comprobaciones disponibles

Con las dependencias instaladas y el motor compilado:

```powershell
.\.venv\Scripts\python.exe tests/test_interface.py
.\.venv\Scripts\python.exe tests/test_maps.py
```

La primera suite recorre las ocho vistas con Streamlit AppTest y el motor real, comprueba métricas y un caso inválido de flujo. La segunda verifica coordenadas, capas, fotogramas inicial/intermedio/final y correspondencia de las tablas con los resultados. El reporte de interfaz está en `results/interface_tests.json`.

Para una revisión visual, ejecuta un escenario, observa el avance automático, pausa, avanza y retrocede. Comprueba que las métricas no cambien al usar esos controles. Prueba también selección de una central, encuadres, tablas y descarga del JSON.

## 13. Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| Error de conexión a localhost | Confirma que la terminal siga abierta y utiliza el puerto que imprimió el lanzador |
| Aparece un enlace al puerto 3000 | Usa `iniciar_app.py`, que desactiva el modo de desarrollo de Streamlit |
| NumPy indica módulos `cp312` incompatibles | Ejecuta con el entorno `.venv` de Python 3.12 o reinstala dependencias para el intérprete elegido |
| No se encuentra el motor | Compila C++ o configura `SENTINELA_EXECUTABLE` |
| Mapa sin fondo | Revisa la conexión a internet o utiliza el diagrama |
| No aparece Nueva York | Cambia el encuadre a Toda la red o Norteamérica |
| Solo se resaltan algunos enlaces | La reproducción está en un paso intermedio; pulsa Ver todo |
| Transmisión rechazada | Revisa caracteres permitidos, mayúsculas, espacios, BOM y límites |
| Origen igual al destino | Elige centrales distintas y vuelve a ejecutar |
| Streamlit muestra File change | Pulsa Rerun para cargar los cambios del código |

## 14. Límites actuales y próximos pasos

La interfaz utiliza escenarios de red preparados; todavía no ofrece un editor general de topologías ni importación libre de XML/CSV. TSP permite elegir centrales y flujo permite elegir extremos. La carga de archivos de la UI corresponde a transmisiones TXT.

Las animaciones presentan conexiones y regiones completas por paso. No interpolan el crecimiento de cada línea ni transmiten el estado interno del algoritmo mientras se calcula.

Los siguientes avances pueden incluir edición de capacidades y costos, escenarios oficiales, exportación gráfica, historial persistente y pruebas de instalación en otras computadoras. Esas funciones deben incorporarse conservando la claridad de resultados, unidades y mediciones.

Documentos relacionados: [README general](../README.md), [integración Python](../app/README.md), [contrato del motor](CONTRACT.md), [algoritmos](ALGORITHMS.md) y [procedencia de datos](../data/README.md).
