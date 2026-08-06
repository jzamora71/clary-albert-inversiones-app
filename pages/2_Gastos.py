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
st.info(
    f"El pago del gerente **{db.MANAGER_NAME}** ya no se registra aqui -- se "
    f"calcula automaticamente como el {int(db.PORCENTAJE_GERENTE * 100)}% del "
    "deposito bancario del mes, en la pagina **Reporte**. Aqui solo se "
    "registran otros gastos (reparaciones, mantenimiento, etc.)."
)

st.subheader("Agregar gastos")

col1, col2, col3 = st.columns(3)
with col1:
    gasto_concepto = st.text_input("Descripcion de gastos", key="gasto_concepto")
with col2:
    gasto_monto = money_input("Monto de gastos", key="gasto_monto")
with col3:
    gasto_fecha = st.date_input("Fecha de gastos (dia/mes/año)", value=date.today(), key="gasto_fecha")

if st.button("Agregar gastos", type="primary"):
    if not gasto_concepto.strip():
        st.error("Escribe una descripcion de gastos.")
    elif gasto_monto <= 0:
        st.error("El monto debe ser mayor que cero.")
    else:
        db.add_gasto(gasto_concepto.strip(), gasto_fecha.isoformat(), float(gasto_monto), categoria=db.TIPO_OTRO_GASTO)
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
    gastos_show = gastos_df.drop(columns=["ID"]).copy()
    gastos_show["Fecha"] = gastos_show["Fecha"].apply(fecha_dmy)
    gastos_show["Monto"] = gastos_show["Monto"].apply(money)
    st.dataframe(gastos_show, use_container_width=True, hide_index=True)
    kpi_card("Total gastos", money(gastos_df["Monto"].sum()), expense=True)

    # --- Corregir o eliminar un gasto ---------------------------------
    st.divider()
    with st.expander("✏️ Corregir o eliminar un gasto"):
        st.caption(
            "Si un gasto se registro por error (monto equivocado, fecha "
            "equivocada, duplicado, etc.), puedes eliminarlo aqui y "
            "volver a registrarlo correctamente arriba."
        )
        opciones_gasto = {
            f"{r.Concepto} - {fecha_dmy(r.Fecha)} - {money(r.Monto)} (registro #{r.ID})": r.ID
            for r in gastos_df.itertuples()
        }
        etiqueta_gasto = st.selectbox(
            "Selecciona el gasto a eliminar", options=list(opciones_gasto.keys()), key="gasto_a_borrar"
        )
        confirmar_borrado_gasto = st.checkbox(
            "Confirmo que quiero eliminar este gasto permanentemente", key="confirmar_borrado_gasto"
        )
        if st.button(
            "🗑️ Eliminar gasto seleccionado",
            disabled=not confirmar_borrado_gasto,
            key="btn_borrar_gasto",
        ):
            db.delete_gasto(opciones_gasto[etiqueta_gasto])
            st.success("Gasto eliminado.")
            del st.session_state["confirmar_borrado_gasto"]
            st.rerun()
else:
    st.info("Aun no hay gastos registrados.")
