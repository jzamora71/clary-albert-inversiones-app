"""
app.py -- Homepage / landing page ONLY.

This file must never contain report logic (forms to add ingresos/gastos,
PDF generation, etc). All of that lives in separate files inside /pages,
which Streamlit automatically turns into sidebar navigation. Because each
page in /pages only runs when the user actually clicks it (either in the
sidebar or via the buttons below), nothing under /pages executes just from
opening this landing page.
"""

import streamlit as st

from utils import COMPANY_NAME, init_session_state, money

st.set_page_config(
    page_title=f"{COMPANY_NAME} - Contabilidad",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- Session state check --------------------------------------------------
# init_session_state() uses st.session_state.setdefault(...), so it only
# creates the "ingresos" / "gastos" storage the FIRST time the app runs in
# a session. On every later rerun (e.g. clicking a button) it does nothing,
# so the landing page below is always what renders first -- reports never
# auto-launch, they only open when a nav button is explicitly clicked.
init_session_state()

st.markdown(
    """
    <style>
    .stApp { background-color: #eaf4fb; }
    .main-header { text-align: center; padding: 10px 0 4px 0; }
    .main-header h1 { color: #1f4e79; font-size: 40px; margin-bottom: 0; }
    .main-header p { color: #34608f; font-size: 18px; margin-top: 6px; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #cfe3f5;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0px 2px 6px rgba(31, 78, 121, 0.08);
    }
    .stButton>button {
        background-color: #1f4e79;
        color: #ffffff;
        border-radius: 8px;
        padding: 0.6em 1em;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {
        background-color: #163a5c;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Logo + welcome message ------------------------------------------------
logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
with logo_col2:
    st.image("assets/logo.png", width=260)

st.markdown(
    f"""
    <div class="main-header">
        <h1>{COMPANY_NAME}</h1>
        <p>Panel de Contabilidad</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <p style="text-align:center; color:#475569; font-size:16px; max-width:520px; margin:0 auto 24px auto;">
        Bienvenido. Desde aqui puedes registrar ingresos, registrar gastos y
        generar el reporte contable en PDF. Usa los botones abajo o el menu
        de la izquierda para navegar.
    </p>
    """,
    unsafe_allow_html=True,
)

# --- Quick summary (read-only preview, does not open any report) ----------
total_ingresos = sum(item["Monto"] for item in st.session_state.ingresos)
total_gastos = sum(item["Monto"] for item in st.session_state.gastos)
neto = total_ingresos - total_gastos

c1, c2, c3 = st.columns(3)
c1.metric("Ingresos totales", money(total_ingresos))
c2.metric("Gastos totales", money(total_gastos))
c3.metric("Balance neto", money(neto))

st.divider()

# --- Navigation buttons -----------------------------------------------------
# Each button only navigates when clicked -- st.switch_page runs exclusively
# inside the "if st.button(...)" block, so nothing here fires on page load.
nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    if st.button("📥 Ver Ingresos", use_container_width=True):
        st.switch_page("pages/1_Ingresos.py")

with nav_col2:
    if st.button("📤 Ver Gastos", use_container_width=True):
        st.switch_page("pages/2_Gastos.py")

with nav_col3:
    if st.button("📊 Ver Reporte", use_container_width=True):
        st.switch_page("pages/3_Reporte.py")

st.caption(
    "Tambien puedes usar el menu de navegacion en la barra lateral izquierda "
    "para ir directamente a Ingresos, Gastos o Reporte."
)
