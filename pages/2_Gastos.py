"""
pages/2_Gastos.py -- Expense entry report.

Runs only when the user clicks "Gastos" in the sidebar or the "Ver Gastos"
button on the homepage. Never runs automatically on app.py load.

Data is saved permanently to data.db (see db.py) instead of only living in
st.session_state, so it survives closing the app and reopening it later.
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import COMPANY_NAME, init_session_state, money

st.set_page_config(page_title=f"Gastos - {COMPANY_NAME}", page_icon="📤", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📤 Gastos")
st.caption(f"{COMPANY_NAME} - Registro de gastos (guardado permanentemente)")

st.subheader("Agregar gasto")

col1, col2, col3 = st.columns(3)
with col1:
    gasto_concepto = st.text_input("Concepto del gasto", key="gasto_concepto")
with col2:
    gasto_monto = st.number_input(
        "Monto del gasto",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="gasto_monto",
    )
with col3:
    gasto_fecha = st.date_input("Fecha gasto", value=date.today(), key="gasto_fecha")

if st.button("Agregar gasto"):
    if gasto_concepto.strip() and gasto_monto > 0:
        db.add_gasto(gasto_concepto.strip(), gasto_fecha.isoformat(), float(gasto_monto))
        st.success("Gasto agregado y guardado.")
    else:
        st.error("Escribe un concepto y un monto mayor que cero.")

st.divider()
st.subheader("Gastos registrados")

gastos = db.get_gastos()
if gastos:
    gastos_df = pd.DataFrame(gastos)[["concepto", "fecha", "monto"]]
    gastos_df.columns = ["Concepto", "Fecha", "Monto"]
    gastos_show = gastos_df.copy()
    gastos_show["Monto"] = gastos_show["Monto"].apply(money)
    st.dataframe(gastos_show, use_container_width=True)
else:
    st.info("Aun no hay gastos registrados.")
