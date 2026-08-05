"""
pages/3_Reporte.py -- Summary report + PDF export + backup/restore.

Runs only when the user clicks "Reporte" in the sidebar or the
"Ver Reporte" button on the homepage. The PDF is only generated when this
page is actually opened, never when app.py first loads.

Ingresos/Gastos are read from data.db (see db.py), which survives normal
app restarts. As a safety net -- since Streamlit's free hosting doesn't
guarantee the database file survives a full redeploy or manual reboot --
this page also offers a CSV backup download and a CSV restore uploader.
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import COMPANY_NAME, build_pdf, init_session_state, money

st.set_page_config(page_title=f"Reporte - {COMPANY_NAME}", page_icon="📊", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📊 Reporte")
st.caption(f"{COMPANY_NAME} - Reporte contable")

empresa = st.text_input("Nombre de la empresa", value=COMPANY_NAME)
fecha_reporte = st.date_input("Fecha del reporte", value=date.today())

ingresos_raw = db.get_ingresos()
gastos_raw = db.get_gastos()

ingresos_df = (
    pd.DataFrame(ingresos_raw)[["concepto", "fecha", "monto"]].rename(
        columns={"concepto": "Concepto", "fecha": "Fecha", "monto": "Monto"}
    )
    if ingresos_raw
    else pd.DataFrame(columns=["Concepto", "Fecha", "Monto"])
)
gastos_df = (
    pd.DataFrame(gastos_raw)[["concepto", "fecha", "monto"]].rename(
        columns={"concepto": "Concepto", "fecha": "Fecha", "monto": "Monto"}
    )
    if gastos_raw
    else pd.DataFrame(columns=["Concepto", "Fecha", "Monto"])
)

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

st.divider()

# --- Backup / restore -------------------------------------------------
# Safety net in case the app's database file is ever wiped by a Streamlit
# Cloud reboot or redeploy: download a CSV copy regularly, and restore
# from it here if the numbers ever come back empty unexpectedly.
with st.expander("💾 Respaldo y restauracion de datos"):
    st.markdown(
        "Descarga una copia de tus datos de vez en cuando. Si alguna vez "
        "la app reinicia y los datos aparecen vacios, puedes restaurarlos "
        "aqui subiendo el ultimo respaldo que descargaste."
    )

    back_col1, back_col2 = st.columns(2)
    with back_col1:
        st.download_button(
            "Descargar respaldo de Ingresos (CSV)",
            data=ingresos_df.to_csv(index=False).encode("utf-8"),
            file_name="respaldo_ingresos.csv",
            mime="text/csv",
        )
    with back_col2:
        st.download_button(
            "Descargar respaldo de Gastos (CSV)",
            data=gastos_df.to_csv(index=False).encode("utf-8"),
            file_name="respaldo_gastos.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.markdown("**Restaurar desde un respaldo:**")

    restore_col1, restore_col2 = st.columns(2)
    with restore_col1:
        ingresos_upload = st.file_uploader("Subir respaldo de Ingresos (CSV)", type="csv", key="ingresos_upload")
        if ingresos_upload is not None:
            if st.button("Restaurar Ingresos desde este archivo"):
                restore_df = pd.read_csv(ingresos_upload)
                db.import_ingresos_df(restore_df)
                st.success("Ingresos restaurados. Recarga la pagina para verlos.")
    with restore_col2:
        gastos_upload = st.file_uploader("Subir respaldo de Gastos (CSV)", type="csv", key="gastos_upload")
        if gastos_upload is not None:
            if st.button("Restaurar Gastos desde este archivo"):
                restore_df = pd.read_csv(gastos_upload)
                db.import_gastos_df(restore_df)
                st.success("Gastos restaurados. Recarga la pagina para verlos.")
