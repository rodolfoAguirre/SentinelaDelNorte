# Pendientes

Estado al 2026-10-22, rama `feature/interfaz-visual`, todavía sin merge a `main`.

## Interfaz (hecho)
- Cinco páginas en `app/streamlit_app.py` y `app/views/`: Misión, Network Explorer, Algorithm Laboratory, Cybersecurity Console y Scenario Manager
- Mapa Plotly con capas MST, TSP, flujo con corte mínimo y Voronoi; inspector de nodos y consultas de ubicación
- Laboratorio: exacto contra heurístico, comparación entre escenarios, escalabilidad y medición en vivo
- Escenarios: fallas de enlaces, factor de capacidad, redes sintéticas e importación y exportación JSON validada
- `tests/test_interface.py`: 7 pruebas con AppTest y el motor real. Requiere `.venv` con `app/requirements.txt` (`streamlit>=1.66`, `plotly>=6`)

## Falta
1. Actualizar el README: las secciones "Estado del proyecto" y "Construir la interfaz Streamlit" todavía describen la versión anterior. Documentar también `app/README.md`
2. Probar `iniciar_app.py` en Windows y en otra computadora. El mapa base de Plotly necesita internet
3. Revisar la interfaz con transmisiones de 2M caracteres cargadas desde archivo (rendimiento del resaltado)
4. Registrar `test_interface.py` en CTest cuando el Python que use CMake tenga Streamlit instalado
5. Hacer merge de `feature/interfaz-visual` a `main` después de revisarla
6. Completar las contribuciones de Andrés en `team.txt` (y del cuarto integrante, si lo hay)
7. Entregable académico `ReflexSENTINEL_A0XXXXXXX.pdf`: modelos, alternativas, correctitud, complejidad, experimentos y estándares
8. Generar el ZIP final con `python tools/package_autograder.py --student-id <matrícula>`
