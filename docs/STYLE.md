# Aplicación del estándar de programación

Se revisaron las dos páginas de `Estandar Programacion.pdf` proporcionado por el usuario. El estándar se aplica a los archivos propios del motor y a sus scripts auxiliares, junto con estas preferencias del usuario: comentarios sin acentos, cortos, descriptivos y sin punto final; espacios visuales entre funciones y bloques lógicos.

## Cambios

- Variables y funciones propias en camelCase; tipos en PascalCase singular; constantes con nombres en mayúsculas
- Nombres descriptivos para grafos, distancias, estados, flujos y posiciones
- Tabulaciones de cuatro columnas, llaves en la misma línea y una instrucción por línea
- Líneas en blanco entre funciones, validaciones, recorridos y resultados
- Encabezados con descripción, autores, matrículas y fecha de modificación
- Documentación de propósito, parámetros y retorno antes de cada función
- Inicialización de campos y buffers; contenedores inicializados por constructor o con llaves
- Ciclos sin `break` ni `continue`, usando condiciones y bloques equivalentes
- Funciones separadas para Held–Karp, heurística TSP y adaptación de cada modo JSON
- Configuración persistente en `.clang-format` para conservar el formato en el IDE

Las claves del contrato JSON, columnas CSV y nombres de APIs externas conservan su escritura: son parte de formatos o bibliotecas existentes, no identificadores locales que se puedan renombrar sin alterar la integración. Las rutas de archivos también se conservan.


La evidencia de revisión está en `results/style_audit.json`; la compilación y las pruebas funcionales en `results/build.log`, `results/ctest.log` y `results/tests.json`. La revisión automatizada cubre encabezados, contratos de funciones, comentarios y saltos de control; no sustituye la revisión manual de nombres y organización.
