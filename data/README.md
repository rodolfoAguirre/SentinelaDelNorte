# Trazabilidad de los datos de trabajo

El XML y mapping se inspeccionaron antes de implementar. El PDF suministrado permanece en `../sentinelaDelNorte.pdf`: es una exportación de 20 páginas con texto rasterizado, leída mediante extracción de sus imágenes. Sus páginas 5–7 describen algoritmos, 11 incluye el ejemplo de cadenas, 12–14 los datos y formatos, 15 experimentos, 17 el sobre JSON y 19 la estructura.

## Originales

`original/geant.xml` y `original/mapping.csv` son copias byte por byte de los archivos suministrados, con SHA-256 en `derived/inspection.json`. No se editan sus valores. El XML usa namespace `http://sndlib.zib.de/network`, codificación ISO-8859-1 y coordenadas `geographical`: x=longitud, y=latitud en grados.

Se verificaron **22 nodos, 36 enlaces, 462 demandas**. Metadatos: año 2005, granularidad 4month, unidad MBITPERSEC y matriz de demanda de pico dirigida. El origen textual menciona 3 Tbps; se conserva como metadato del proveedor, no como medición de este proyecto. No hay atributo que fije la dirección de los enlaces físicos ni campos de capacidad instalada en esta instancia. El escenario de trabajo los modela no dirigidos.

Cada enlace tiene `source`, `target` y un `additionalModules/addModule` con `capacity=40000` y su `cost`. Son **módulos adicionales instalables**: no demuestran qué infraestructura está instalada. No hay `preInstalledModule`. La unidad monetaria de `cost` no se especifica; no se etiqueta como km ni como una moneda inventada. Las demandas tienen `source`, `target`, `demandValue`; constituyen tráfico requerido por par dirigido, no capacidad de enlace.

## Transformaciones y supuestos

| Archivo | Contenido y procedencia |
|---|---|
| `derived/nodes.csv` | ID, índice en orden XML, latitud/longitud originales y x/y derivados en km |
| `derived/edges.csv` | Topología original, costo por módulo original, costo de trabajo según módulos supuestos, distancia haversine derivada |
| `derived/capacities.csv` | Capacidad de módulo original, número supuesto de módulos, capacidad de escenario sintética; instalada marcada `unknown` |
| `derived/demands.csv` | Los 462 valores originales de demanda dirigida, Mbit/s |
| `derived/scenarios.json` | Selección TSP, origen/destino, proyección y dominio sintéticos, parámetros reproducibles |
| `derived/*.input.json` | Solicitudes al motor construidas a partir de estos archivos de trabajo |
| `synthetic/*.txt` | Ejemplo ilustrativo del PDF p.11, claramente separado de transmisiones y firmas oficiales |

Regla predeterminada: **suponer un módulo adicional instalado por enlace**; capacidad=40000 Mbit/s y costo de instalación=1×cost. El parámetro `--modules` cambia ambos factores, sin afirmar que esa instalación ocurrió. No se deducen capacidades de demandas ni del tamaño de tráfico. No se calculan aquí flujos multicommodity para satisfacer todas las demandas.

Distancias de enlaces: haversine entre coordenadas de sus extremos, radio esférico 6371.0088 km. Son aproximaciones geográficas, no longitud real de fibra ni costo de instalación. Solo existen donde el XML contiene un enlace. TSP usa caminos mínimos sobre esas longitudes; la matriz completa entre centrales es una distancia de viaje por la topología, no nuevas conexiones físicas.

Proyección de trabajo para Voronoi: equirectangular, `x=R*(lon-lon0)*cos(lat0)`, `y=R*(lat-lat0)` con ángulos en radianes; predeterminados lat0=50°, lon0=10°, R=6371.0088 km. El dominio es el rectángulo envolvente de sitios con 100 km de margen, configurable. No es una proyección de precisión geodésica: las regiones son euclidianas en ese plano y tienen distorsión, especialmente por el nodo de Nueva York y otras ubicaciones alejadas. No usar esta asignación como cobertura operacional. Se mantiene Nueva York porque sí está en el XML, sin recortar arbitrariamente la topología a Europa. El paquete oficial puede cambiar proyección y dominio.

## Comprobación del mapping

Austria–Suiza corresponde a `at1.at_ch1.ch` (índices 0,2); Austria–Alemania corresponde a `at1.at_de1.de` (0,4). Ambas conexiones existen: **no se detectaron discrepancias topológicas**. El estado sigue `pending` y las transmisiones oficiales no están disponibles. Las etiquetas benigno/DDoS se preservan como contexto de simulación, no se atribuyen al ejemplo sintético ni confirman ataques en GÉANT.

## Reemplazo por datos oficiales

Conservar los nuevos originales y su procedencia. Adaptar el conversor si el XML incorpora varios tipos de módulos o capacidad preinstalada: el conversor actual rechaza ese modelo para evitar elegir silenciosamente. Sustituir escenario, costos, capacidades, distancias, dominio y selección TSP por los oficiales cuando lleguen. Los archivos oficiales de transmisión se pueden apuntar directamente mediante `{"file":"..."}`; no necesitan conversión si respetan el formato hexadecimal. No se descargaron datasets adicionales.
