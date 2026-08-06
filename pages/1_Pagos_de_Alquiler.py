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
from utils import (
    COMPANY_NAME,
    build_pagos_pdf,
    fecha_dmy,
    init_session_state,
    mes_key,
    mes_label,
    money,
    money_input,
    rango_meses,
)

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
    fecha_pago = st.date_input("Fecha de pago (dia/mes/año)", value=date.today(), key="pago_fecha")
with col4:
    monto_pago = money_input("Monto pagado", key=f"pago_monto_{apartamento}")

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
        # Limpiar el monto para que el siguiente pago (mismo apartamento u
        # otro) siempre empiece en blanco/0, en vez de mostrar este monto.
        del st.session_state[f"pago_monto_{apartamento}"]
        st.rerun()

st.divider()

# --- Historial de pagos -----------------------------------------------------
st.subheader("Historial de pagos")

pagos = db.get_pagos_alquiler()
if pagos:
    pagos_df = pd.DataFrame(pagos)[["id", "apartamento", "nombre", "telefono", "fecha", "monto"]]
    pagos_df.columns = ["ID", "Apartamento", "Inquilino", "Telefono", "Fecha", "Monto"]

    # Selector de mes a mostrar: por defecto solo el mes actual, con la
    # opcion de ver todos los meses juntos si se necesita. Esto controla el
    # cuadro de total y la tabla de abajo, y tambien el PDF para imprimir.
    mes_actual = mes_key(date.today().isoformat())
    meses_con_datos = set(pagos_df["Fecha"].apply(mes_key))
    meses_opciones = sorted(
        meses_con_datos | set(rango_meses(atras=12, adelante=2)) | {mes_actual}, reverse=True
    )
    opciones_selector = ["TODOS"] + meses_opciones
    indice_default = opciones_selector.index(mes_actual) if mes_actual in opciones_selector else 0

    mes_vista_pagos = st.selectbox(
        "Mes a mostrar",
        options=opciones_selector,
        index=indice_default,
        format_func=lambda clave: "Todos los meses" if clave == "TODOS" else mes_label(clave),
        key="pagos_mes_vista",
    )
    st.caption(
        "El total y la tabla de abajo muestran solo el mes seleccionado. "
        "Elige 'Todos los meses' para ver el historial completo."
    )

    if mes_vista_pagos == "TODOS":
        pagos_vista_df = pagos_df
        titulo_vista_pagos = "Todos los meses"
    else:
        pagos_vista_df = pagos_df[pagos_df["Fecha"].apply(mes_key) == mes_vista_pagos]
        titulo_vista_pagos = mes_label(mes_vista_pagos)

    total_vista_pagos = pagos_vista_df["Monto"].sum()
    total_general_pagos = pagos_df["Monto"].sum()

    c1, c2 = st.columns(2)
    c1.metric(f"Total de {titulo_vista_pagos}", money(total_vista_pagos))
    c2.metric("Total general de pagos (todos los meses)", money(total_general_pagos))

    if not pagos_vista_df.empty:
        pagos_show = pagos_vista_df.drop(columns=["ID"]).copy()
        pagos_show["Fecha"] = pagos_show["Fecha"].apply(fecha_dmy)
        pagos_show["Monto"] = pagos_show["Monto"].apply(money)
        st.dataframe(pagos_show, use_container_width=True, hide_index=True)

        pdf_pagos_bytes = build_pagos_pdf(
            empresa=COMPANY_NAME,
            fecha_reporte=date.today(),
            titulo_periodo=titulo_vista_pagos,
            pagos_df=pagos_vista_df,
            total_periodo=total_vista_pagos,
        )
        sufijo_pdf = (
            "todos_los_meses" if mes_vista_pagos == "TODOS" else mes_vista_pagos
        )
        st.download_button(
            f"Descargar / imprimir PDF ({titulo_vista_pagos})",
            data=pdf_pagos_bytes,
            file_name=f"pagos_alquiler_{sufijo_pdf}.pdf",
            mime="application/pdf",
        )
    else:
        st.info(f"No hay pagos de alquiler registrados en {titulo_vista_pagos}.")

    # --- Corregir o eliminar un pago -------------------------------------
    st.divider()
    with st.expander("✏️ Corregir o eliminar un pago"):
        st.caption(
            "Si un pago se registro por error (monto equivocado, fecha "
            "equivocada, duplicado, etc.), puedes eliminarlo aqui y "
            "volver a registrarlo correctamente arriba."
        )
        opciones_pago = {
            f"Apto {r.Apartamento} - {r.Inquilino} - {fecha_dmy(r.Fecha)} - {money(r.Monto)} (registro #{r.ID})": r.ID
            for r in pagos_df.itertuples()
        }
        etiqueta_pago = st.selectbox(
            "Selecciona el pago a eliminar", options=list(opciones_pago.keys()), key="pago_a_borrar"
        )
        confirmar_borrado_pago = st.checkbox(
            "Confirmo que quiero eliminar este pago permanentemente", key="confirmar_borrado_pago"
        )
        if st.button(
            "🗑️ Eliminar pago seleccionado",
            disabled=not confirmar_borrado_pago,
            key="btn_borrar_pago",
        ):
            db.delete_ingreso(opciones_pago[etiqueta_pago])
            st.success("Pago eliminado.")
            del st.session_state["confirmar_borrado_pago"]
            st.rerun()
else:
    st.info("Aun no hay pagos de alquiler registrados.")
