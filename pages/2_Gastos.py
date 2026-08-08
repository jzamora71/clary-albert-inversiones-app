"""
pages/2_Gastos.py -- Expense entry report.

Runs only when the user clicks "Gastos" in the sidebar or the "Ver Gastos"
button on the homepage. Never runs automatically on app.py load.

The manager's payment is NOT entered here anymore -- it's calculated
automatically as a percentage of the monthly bank deposit on the Reporte
page (see pages/3_Reporte.py and db.MANAGER_NAME / db.PORCENTAJE_GERENTE).
This page is only for other expenses (repairs, maintenance, supplies,
etc.), which still subtract from the rent income in the Reporte page.

Data is saved permanently to data.db (see db.py) instead of only living in
st.session_state, so it survives closing the app and reopening it later.
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import COMPANY_NAME, fecha_dmy, init_session_state, kpi_card, money, money_input

st.set_page_config(page_title=f"Gastos - {COMPANY_NAME}", page_icon="📤", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📤 Gastos")
st.caption(f"{COMPANY_NAME} - Registro de gastos (guardado permanentemente)")

st.subheader("Agregar gastos")

col1, col2, col3, col4 = st.columns(4)
with col1:
    gasto_fecha = st.date_input("Fecha (dia/mes/año)", value=date.today(), key="gasto_fecha")
with col2:
    gasto_categoria = st.selectbox("Tipo de gasto", options=db.TIPOS_GASTO, key="gasto_categoria")
with col3:
    gasto_monto = money_input("Monto de gastos", key="gasto_monto")
with col4:
    gasto_concepto = st.text_input("Descripcion de gastos", key="gasto_concepto")

if st.button("Agregar gastos", type="primary"):
    if not gasto_concepto.strip():
        st.error("Escribe una descripcion de gastos.")
    elif gasto_monto <= 0:
        st.error("El monto debe ser mayor que cero.")
    else:
        db.add_gasto(gasto_concepto.strip(), gasto_fecha.isoformat(), float(gasto_monto), categoria=gasto_categoria)
        st.success("Gastos registrados y guardados.")
        # Limpiar la descripcion y el monto para que el siguiente gasto
        # empiece en blanco, en vez de mostrar los datos del anterior.
        del st.session_state["gasto_concepto"]
        del st.session_state["gasto_monto"]
        st.rerun()

st.divider()
st.subheader("Gastos registrados")

gastos = db.get_gastos()
if gastos:
    gastos_df = pd.DataFrame(gastos)[["id", "categoria", "concepto", "fecha", "monto"]]
    gastos_df.columns = ["ID", "Tipo", "Concepto", "Fecha", "Monto"]

    st.caption("Toca el icono 🗑️ junto a un gasto para eliminarlo (por ejemplo, si tiene un error).")

    header_cols = st.columns([1.3, 2.2, 1.2, 1.3, 0.7])
    for col, label in zip(header_cols, ["Tipo", "Concepto", "Fecha", "Monto", ""]):
        col.markdown(f"**{label}**")

    for r in gastos_df.itertuples():
        row_id = r.ID
        with st.container(border=True):
            row_cols = st.columns([1.3, 2.2, 1.2, 1.3, 0.7])
            row_cols[0].write(r.Tipo)
            row_cols[1].write(r.Concepto)
            row_cols[2].write(fecha_dmy(r.Fecha))
            row_cols[3].write(money(r.Monto))
            if row_cols[4].button("🗑️", key=f"borrar_gasto_{row_id}", help="Eliminar este gasto"):
                st.session_state["confirmar_borrar_gasto_id"] = row_id
                st.rerun()

            if st.session_state.get("confirmar_borrar_gasto_id") == row_id:
                st.warning(
                    f"¿Seguro que deseas eliminar el gasto **{r.Concepto}** "
                    f"por **{money(r.Monto)}** del {fecha_dmy(r.Fecha)}? "
                    "Esta accion no se puede deshacer."
                )
                confirm_cols = st.columns(2)
                if confirm_cols[0].button("Si, eliminar", key=f"si_gasto_{row_id}", type="primary"):
                    db.delete_gasto(row_id)
                    st.session_state.pop("confirmar_borrar_gasto_id", None)
                    st.success("Gasto eliminado.")
                    st.rerun()
                if confirm_cols[1].button("Cancelar", key=f"no_gasto_{row_id}"):
                    st.session_state.pop("confirmar_borrar_gasto_id", None)
                    st.rerun()

    kpi_card("Total Gastos", money(gastos_df["Monto"].sum()), expense=True)
else:
    st.info("Aun no hay gastos registrados.")
