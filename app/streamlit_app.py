# Descripcion: punto de entrada del gemelo digital SENTINEL con sus cuatro modulos
# Autores: Rodolfo Aguirre Revilla, Leandro Lizama Leirana, Andres Maiztegui Martinez | Matriculas: A00839754, A00840242, A01833484
# Modificacion: 2026-10-22

from pathlib import Path
import sys

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from app.adapter import EngineError
from app.state import activeScenario, getAdapter, initState
from app.views import console, explorer, laboratory, manager, mission


PAGES = {
	"Misión": mission,
	"Network Explorer": explorer,
	"Algorithm Laboratory": laboratory,
	"Cybersecurity Console": console,
	"Scenario Manager": manager,
}
STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.kicker { font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; letter-spacing: 0.12em; color: #6F95F7;
	text-transform: uppercase; margin: 1.2rem 0 0.4rem; }
.section-title { font-weight: 800; font-size: 2.3rem; letter-spacing: -0.03em; margin: 0 0 0.3rem; padding: 0; }
.section-subtitle { color: #9AA8BF; font-size: 1.05rem; max-width: 52rem; }
.hero { font-weight: 800; font-size: clamp(3rem, 8vw, 5.6rem); line-height: 0.95; letter-spacing: -0.045em; margin: 0.4rem 0 0.8rem; }
.hero-muted { color: #8C97A8; }
.hero-accent { color: #4C7BF4; }
.hero-tagline { color: #9AA8BF; font-size: 1.35rem; }
.mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; letter-spacing: 0.1em; margin-left: 0.6rem; }
.muted { color: #7F8DA6; }
.accent { color: #6F95F7; }
.card { border: 1px solid #24324A; border-radius: 10px; padding: 0.9rem 1rem; height: 100%; background: #0F1828; }
.card h4 { margin: 0.3rem 0 0.4rem; font-size: 1.05rem; }
.card p { color: #9AA8BF; font-size: 0.9rem; margin: 0; }
.card .mono { margin-left: 0; }
.hexview { font-family: 'IBM Plex Mono', monospace; font-size: 1.05rem; letter-spacing: 0.18em; line-height: 2.1;
	word-break: break-all; background: #0F1828; border: 1px solid #24324A; border-radius: 8px; padding: 0.6rem 0.9rem; }
.sig0 { background: rgba(76,123,244,0.35); border-radius: 3px; }
.sig1 { background: rgba(54,226,172,0.32); border-radius: 3px; }
.sig2 { background: rgba(176,124,255,0.38); border-radius: 3px; }
.pal { border-bottom: 3px solid #FFB547; }
.common { text-decoration: overline #FF5C7A 3px; color: #FFD3DB; }
[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
"""


# Dibuja la barra lateral con navegacion y escenario activo
# Parametros: ninguno
# Retorno: nombre de la pagina elegida
def sidebar() -> str:
	st.sidebar.markdown('<div class="kicker" style="margin-top:0">SENTINELA <span class="accent">DEL NORTE</span></div>',
	                    unsafe_allow_html=True)
	page = st.sidebar.radio("Navegación", list(PAGES), label_visibility="collapsed")
	st.sidebar.divider()
	st.sidebar.selectbox("Escenario activo", list(st.session_state.scenarios), key="activeSelector",
	                     on_change=selectScenario)
	scenario = activeScenario()
	st.sidebar.caption(f"{len(scenario['nodes'])} centrales · {len(scenario['edges'])} enlaces")
	st.sidebar.divider()
	st.sidebar.caption(f"Motor C++: `{getAdapter().executablePath.name}` · contrato provisional-v1")
	st.sidebar.caption("TC2038 · Análisis y Diseño de Algoritmos Avanzados")
	return page


# Sincroniza el escenario activo con el selector lateral
# Parametros: ninguno
# Retorno: sin valor; actualiza session_state
def selectScenario() -> None:
	st.session_state.activeScenario = st.session_state.activeSelector


# Configura la pagina, valida el motor y despacha el modulo elegido
# Parametros: ninguno
# Retorno: sin valor; ejecuta la interfaz
def main() -> None:
	st.set_page_config(page_title="Sentinela del Norte", page_icon="🛰️", layout="wide",
	                   initial_sidebar_state="expanded")
	st.markdown(STYLES, unsafe_allow_html=True)
	try:
		getAdapter()
	except EngineError as error:
		st.error(f"No se encontró el motor C++: {error}")
		st.code("cmake -S . -B build -DCMAKE_BUILD_TYPE=Release\ncmake --build build", language="bash")
		st.stop()
	initState()
	PAGES[sidebar()].render()


main()
