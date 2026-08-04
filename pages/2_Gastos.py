"""
pages/2_Gastos.py -- Expense entry report.

Runs only when the user clicks "Gastos" in the sidebar or the "Ver Gastos"
button on the homepage. Never runs automatically on app.py load.
"""

from datetime import date

import pandas as pd
import streamlit as st

from utils import COMPANY_NAME, init_session_state, money

st.set_page_config(page_title=f"Gastos - {COMPANY_NAME}", page_icon="📤", layout="wide")

init_session_state()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📤 Gastos")
st.caption(f"{COMPANY_NAME} - Registro de gastos")

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
        st.session_state.gastos.append(
            {
                "Concepto": gasto_concepto.strip(),
                "Fecha": gasto_fecha.isoformat(),
                "Monto": float(gasto_monto),
            }
        )
        st.success("Gasto agregado.")
    else:
        st.error("Escribe un concepto y un monto mayor que cero.")

st.divider()
st.subheader("Gastos registrados")

gastos_df = pd.DataFrame(st.session_state.gastos)
if not gastos_df.empty:
    gastos_show = gastos_df.copy()
    gastos_show["Monto"] = gastos_show["Monto"].apply(money)
    st.dataframe(gastos_show, use_container_width=True)
else:
    st.info("Aun no hay gastos registrados.")
