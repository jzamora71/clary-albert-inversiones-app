"""
pages/2_Gastos.py -- Expense entry report.

Runs only when the user clicks "Gastos" in the sidebar or the "Ver Gastos"
button on the homepage. Never runs automatically on app.py load.

Every expense is tagged with a "Tipo de gasto": either "Pago del gerente"
(the manager's payment) or "Otro gasto" (anything else). Both are still
gastos and both subtract from the rent income in the Reporte page -- the
category just lets the report show how much went to the manager vs.
everything else.

Data is saved permanently to data.db (see db.py) instead of only living in
st.session_state, so it survives closing the app and reopening it later.
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import COMPANY_NAME, fecha_dmy, init_session_state, money

st.set_page_config(page_title=f"Gastos - {COMPANY_NAME}", page_icon="📤", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📤 Gastos")
st.caption(f"{COMPANY_NAME} - Registro de gastos (guardado permanentemente)")

st.subheader("Agregar gasto")

col0, col1 = st.columns(2)
with col0:
    gasto_tipo = st.selectbox("Tipo de gasto", db.TIPOS_GASTO, key="gasto_tipo")
with col1:
    etiqueta_concepto = (
        "Descripcion del gasto" if gasto_tipo == db.TIPO_OTRO_GASTO else "Nota (opcional)"
    )
    gasto_concepto = st.text_input(etiqueta_concepto, key="gasto_concepto")

col2, col3 = st.columns(2)
with col2:
    gasto_monto = st.number_input(
        "Monto del gasto",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="gasto_monto",
    )
with col3:
    gasto_fecha = st.date_input("Fecha del gasto (dia/mes/año)", value=date.today(), key="gasto_fecha")

if st.button("Agregar gasto", type="primary"):
    if gasto_monto <= 0:
        st.error("El monto debe ser mayor que cero.")
    else:
        concepto_final = gasto_concepto.strip() or gasto_tipo
        db.add_gasto(concepto_final, gasto_fecha.isoformat(), float(gasto_monto), categoria=gasto_tipo)
        st.success(f"Gasto de tipo '{gasto_tipo}' registrado y guardado.")
        st.rerun()

st.divider()
st.subheader("Gastos registrados")

gastos = db.get_gastos()
if gastos:
    gastos_df = pd.DataFrame(gastos)[["categoria", "concepto", "fecha", "monto"]]
    gastos_df.columns = ["Tipo", "Concepto", "Fecha", "Monto"]
    gastos_show = gastos_df.copy()
    gastos_show["Fecha"] = gastos_show["Fecha"].apply(fecha_dmy)
    gastos_show["Monto"] = gastos_show["Monto"].apply(money)
    st.dataframe(gastos_show, use_container_width=True, hide_index=True)

    total_gerente = gastos_df.loc[gastos_df["Tipo"] == db.TIPO_PAGO_GERENTE, "Monto"].sum()
    total_otros = gastos_df.loc[gastos_df["Tipo"] != db.TIPO_PAGO_GERENTE, "Monto"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Pago del gerente (total)", money(total_gerente))
    c2.metric("Otros gastos (total)", money(total_otros))
    c3.metric("Total gastos", money(total_gerente + total_otros))
else:
    st.info("Aun no hay gastos registrados.")
