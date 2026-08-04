"""
pages/1_Ingresos.py -- Income entry report.

Streamlit only runs this file when the user clicks "Ingresos" in the
sidebar, or clicks the "Ver Ingresos" button on the homepage (which calls
st.switch_page). It never runs automatically when app.py loads.
"""

from datetime import date

import pandas as pd
import streamlit as st

from utils import COMPANY_NAME, init_session_state, money

st.set_page_config(page_title=f"Ingresos - {COMPANY_NAME}", page_icon="📥", layout="wide")

# Safe to call again here: it only fills in keys that don't exist yet, so
# opening this page directly (e.g. a bookmarked/refreshed URL) still works
# without wiping any data already entered.
init_session_state()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📥 Ingresos")
st.caption(f"{COMPANY_NAME} - Registro de ingresos")

st.subheader("Agregar ingreso")

col1, col2, col3 = st.columns(3)
with col1:
    ingreso_concepto = st.text_input("Concepto del ingreso", key="ingreso_concepto")
with col2:
    ingreso_monto = st.number_input(
        "Monto del ingreso",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="ingreso_monto",
    )
with col3:
    ingreso_fecha = st.date_input("Fecha ingreso", value=date.today(), key="ingreso_fecha")

if st.button("Agregar ingreso"):
    if ingreso_concepto.strip() and ingreso_monto > 0:
        st.session_state.ingresos.append(
            {
                "Concepto": ingreso_concepto.strip(),
                "Fecha": ingreso_fecha.isoformat(),
                "Monto": float(ingreso_monto),
            }
        )
        st.success("Ingreso agregado.")
    else:
        st.error("Escribe un concepto y un monto mayor que cero.")

st.divider()
st.subheader("Ingresos registrados")

ingresos_df = pd.DataFrame(st.session_state.ingresos)
if not ingresos_df.empty:
    ingresos_show = ingresos_df.copy()
    ingresos_show["Monto"] = ingresos_show["Monto"].apply(money)
    st.dataframe(ingresos_show, use_container_width=True)
else:
    st.info("Aun no hay ingresos registrados.")
