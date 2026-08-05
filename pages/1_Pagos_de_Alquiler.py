"""
pages/1_Pagos_de_Alquiler.py -- Monthly rent payment tracker for the 13
apartments.

Runs only when the user clicks "Pagos de Alquiler" in the sidebar or the
"Ver Pagos de Alquiler" button on the homepage. Never runs automatically
when app.py loads.

Two things are saved permanently through db.py:
  - The tenant directory (apartment 1-13 -> name + contact number), so the
    form can remember who lives where and pre-fill it next month.
  - Every rent payment (apartment, tenant name, contact number, date paid,
    amount paid), which also counts as "Ingresos" everywhere else in the
    app (homepage totals, Reporte, PDF export).
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import COMPANY_NAME, init_session_state, money

st.set_page_config(page_title=f"Pagos de Alquiler - {COMPANY_NAME}", page_icon="🏠", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("🏠 Pagos de Alquiler")
st.caption(f"{COMPANY_NAME} - Registro de pagos mensuales de los 13 apartamentos")

# --- Directorio de inquilinos (editable) -----------------------------------
with st.expander("👤 Directorio de inquilinos (nombre y telefono por apartamento)"):
    st.caption(
        "Actualiza aqui el nombre y numero de contacto de cada apartamento. "
        "Estos datos se usan para llenar automaticamente el formulario de pago."
    )
    inquilinos_df = pd.DataFrame(db.get_inquilinos())[["apartamento", "nombre", "telefono"]]
    inquilinos_df.columns = ["Apartamento", "Nombre", "Telefono"]

    edited_df = st.data_editor(
        inquilinos_df,
        column_config={
            "Apartamento": st.column_config.NumberColumn(disabled=True),
            "Nombre": st.column_config.TextColumn(),
            "Telefono": st.column_config.TextColumn(),
        },
        hide_index=True,
        use_container_width=True,
        key="inquilinos_editor",
    )

    if st.button("Guardar directorio de inquilinos"):
        for _, row in edited_df.iterrows():
            db.upsert_inquilino(int(row["Apartamento"]), str(row["Nombre"]).strip(), str(row["Telefono"]).strip())
        st.success("Directorio actualizado.")
        st.rerun()

st.divider()

# --- Registrar un pago ------------------------------------------------------
st.subheader("Registrar pago de alquiler")

apartamento = st.selectbox("Apartamento", options=list(range(1, db.NUM_APARTAMENTOS + 1)), key="pago_apartamento")
inquilino_actual = db.get_inquilino(apartamento)

col1, col2 = st.columns(2)
with col1:
    nombre_inquilino = st.text_input(
        "Nombre del inquilino",
        value=inquilino_actual["nombre"] or "",
        key=f"pago_nombre_{apartamento}",
    )
with col2:
    telefono_inquilino = st.text_input(
        "Numero de contacto",
        value=inquilino_actual["telefono"] or "",
        key=f"pago_telefono_{apartamento}",
    )

col3, col4 = st.columns(2)
with col3:
    fecha_pago = st.date_input("Fecha de pago", value=date.today(), key="pago_fecha")
with col4:
    monto_pago = st.number_input(
        "Monto pagado",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="pago_monto",
    )

if st.button("Registrar pago", type="primary"):
    if not nombre_inquilino.strip():
        st.error("Escribe el nombre del inquilino.")
    elif monto_pago <= 0:
        st.error("El monto pagado debe ser mayor que cero.")
    else:
        db.add_pago_alquiler(
            apartamento=apartamento,
            nombre=nombre_inquilino.strip(),
            telefono=telefono_inquilino.strip(),
            fecha=fecha_pago.isoformat(),
            monto=float(monto_pago),
        )
        st.success(f"Pago del apartamento {apartamento} registrado y guardado.")
        st.rerun()

st.divider()

# --- Historial de pagos -----------------------------------------------------
st.subheader("Historial de pagos")

pagos = db.get_pagos_alquiler()
if pagos:
    pagos_df = pd.DataFrame(pagos)[["apartamento", "nombre", "telefono", "fecha", "monto"]]
    pagos_df.columns = ["Apartamento", "Inquilino", "Telefono", "Fecha", "Monto"]
    pagos_show = pagos_df.copy()
    pagos_show["Monto"] = pagos_show["Monto"].apply(money)
    st.dataframe(pagos_show, use_container_width=True, hide_index=True)
else:
    st.info("Aun no hay pagos de alquiler registrados.")
