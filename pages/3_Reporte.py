"""
pages/3_Reporte.py -- Summary report + PDF export.

Runs only when the user clicks "Reporte" in the sidebar or the
"Ver Reporte" button on the homepage. The PDF is only generated when this
page is actually opened, never when app.py first loads.
"""

from datetime import date

import pandas as pd
import streamlit as st

from utils import COMPANY_NAME, build_pdf, init_session_state, money

st.set_page_config(page_title=f"Reporte - {COMPANY_NAME}", page_icon="📊", layout="wide")

init_session_state()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📊 Reporte")
st.caption(f"{COMPANY_NAME} - Reporte contable")

empresa = st.text_input("Nombre de la empresa", value=COMPANY_NAME)
fecha_reporte = st.date_input("Fecha del reporte", value=date.today())

ingresos_df = pd.DataFrame(st.session_state.ingresos)
gastos_df = pd.DataFrame(st.session_state.gastos)

total_ingresos = ingresos_df["Monto"].sum() if not ingresos_df.empty else 0.0
total_gastos = gastos_df["Monto"].sum() if not gastos_df.empty else 0.0
neto = total_ingresos - total_gastos

c1, c2, c3 = st.columns(3)
c1.metric("Total ingresos", money(total_ingresos))
c2.metric("Total gastos", money(total_gastos))
c3.metric("Balance neto", money(neto))

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Ingresos")
    if not ingresos_df.empty:
        st.dataframe(ingresos_df.assign(Monto=ingresos_df["Monto"].apply(money)), use_container_width=True)
    else:
        st.info("Aun no hay ingresos registrados.")
with col_b:
    st.subheader("Gastos")
    if not gastos_df.empty:
        st.dataframe(gastos_df.assign(Monto=gastos_df["Monto"].apply(money)), use_container_width=True)
    else:
        st.info("Aun no hay gastos registrados.")

st.divider()

if ingresos_df.empty:
    ingresos_df = pd.DataFrame(columns=["Concepto", "Fecha", "Monto"])
if gastos_df.empty:
    gastos_df = pd.DataFrame(columns=["Concepto", "Fecha", "Monto"])

pdf_bytes = build_pdf(
    empresa=empresa,
    fecha_reporte=fecha_reporte,
    ingresos_df=ingresos_df,
    gastos_df=gastos_df,
    total_ingresos=total_ingresos,
    total_gastos=total_gastos,
    neto=neto,
)

st.download_button(
    label="Descargar reporte PDF",
    data=pdf_bytes,
    file_name="reporte_contable_clary_albert.pdf",
    mime="application/pdf",
)
