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

# Cada vez que cambia el apartamento seleccionado (incluyendo la primera vez
# que carga la pagina), volvemos a leer el directorio de inquilinos para que
# el nombre y telefono siempre reflejen los datos guardados mas recientes,
# en vez de quedarse con un valor vacio que Streamlit recordaba de antes.
if st.session_state.get("pago_apartamento_prev") != apartamento:
    inquilino_actual = db.get_inquilino(apartamento)
    st.session_state[f"pago_nombre_{apartamento}"] = inquilino_actual["nombre"] or ""
    st.session_state[f"pago_telefono_{apartamento}"] = inquilino_actual["telefono"] or ""
    st.session_state["pago_apartamento_prev"] = apartamento

col1, col2 = st.columns(2)
with col1:
    nombre_inquilino = st.text_input(
        "Nombre del inquilino",
        key=f"pago_nombre_{apartamento}",
    )
with col2:
    telefono_inquilino = st.text_input(
        "Numero de contacto",
        key=f"pago_telefono_{apartamento}",
    )

col3, col4, col5 = st.columns(3)
with col3:
    fecha_pago = st.date_input("Fecha de pago (dia/mes/año)", value=date.today(), key="pago_fecha")
with col4:
    monto_pago = money_input("Monto pagado", key=f"pago_monto_{apartamento}")
with col5:
    pendiente_pago = money_input("Pendiente por pagar", key=f"pago_pendiente_{apartamento}")
    st.caption("Deja en 0.00 si el inquilino pago todo.")

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
            pendiente=float(pendiente_pago),
        )
        st.success(f"Pago del apartamento {apartamento} registrado y guardado.")
        # Limpiar los montos para que el siguiente pago (mismo apartamento u
        # otro) siempre empiece en blanco/0, en vez de mostrar estos valores.
        del st.session_state[f"pago_monto_{apartamento}"]
        del st.session_state[f"pago_pendiente_{apartamento}"]
        st.rerun()

st.divider()

# --- Apartamentos pendientes de pago -----------------------------------------
pagos = db.get_pagos_alquiler()
if pagos:
    pagos_df = pd.DataFrame(pagos)[["id", "apartamento", "nombre", "telefono", "fecha", "monto", "pendiente"]]
    pagos_df.columns = ["ID", "Apartamento", "Inquilino", "Telefono", "Fecha", "Monto", "Pendiente"]
else:
    pagos_df = pd.DataFrame(columns=["ID", "Apartamento", "Inquilino", "Telefono", "Fecha", "Monto", "Pendiente"])

# Selector de mes a mostrar: por defecto solo el mes actual, con la opcion de
# ver todos los meses juntos si se necesita. Controla tanto la lista de
# pendientes de aqui abajo como el Historial de pagos mas abajo.
mes_actual = mes_key(date.today().isoformat())
meses_con_datos = set(pagos_df["Fecha"].apply(mes_key)) if not pagos_df.empty else set()
meses_opciones = sorted(
    meses_con_datos | set(rango_meses(atras=12, adelante=2)) | {mes_actual}, reverse=True
)
opciones_selector = ["TODOS"] + meses_opciones
indice_default = opciones_selector.index(mes_actual) if mes_actual in opciones_selector else 0

st.subheader("Apartamentos pendientes de pago")
mes_vista_pagos = st.selectbox(
    "Mes o fecha a revisar",
    options=opciones_selector,
    index=indice_default,
    format_func=lambda clave: "Todos los meses" if clave == "TODOS" else mes_label(clave),
    key="pagos_mes_vista",
)
st.caption(
    "Muestra los apartamentos que aun no tienen un pago registrado en el mes "
    "elegido. La lista se actualiza sola a medida que registras pagos arriba, "
    "y tambien controla el total y la tabla del Historial de pagos."
)

if mes_vista_pagos == "TODOS":
    pagos_vista_df = pagos_df
    titulo_vista_pagos = "Todos los meses"
else:
    pagos_vista_df = (
        pagos_df[pagos_df["Fecha"].apply(mes_key) == mes_vista_pagos] if not pagos_df.empty else pagos_df
    )
    titulo_vista_pagos = mes_label(mes_vista_pagos)

if mes_vista_pagos == "TODOS":
    st.info("Elige un mes especifico (no 'Todos los meses') para ver quien esta pendiente de pago.")
else:
    apartamentos_pagados = (
        set(pagos_vista_df["Apartamento"].astype(int).unique()) if not pagos_vista_df.empty else set()
    )
    todos_los_apartamentos = set(range(1, db.NUM_APARTAMENTOS + 1))
    apartamentos_pendientes = sorted(todos_los_apartamentos - apartamentos_pagados)

    if apartamentos_pendientes:
        directorio_nombres = {row["apartamento"]: row["nombre"] for row in db.get_inquilinos()}
        st.warning(
            f"⚠️ {len(apartamentos_pendientes)} apartamento(s) pendiente(s) de pago en {titulo_vista_pagos}:"
        )
        for i, apto_pend in enumerate(apartamentos_pendientes, start=1):
            nombre_pend = directorio_nombres.get(apto_pend, "") or "(sin nombre asignado)"
            st.write(f"{i}. Apartamento {apto_pend} — {nombre_pend}")
    else:
        st.success(f"✅ Los {db.NUM_APARTAMENTOS} apartamentos ya pagaron en {titulo_vista_pagos}.")

st.divider()

# --- Historial de pagos -----------------------------------------------------
st.subheader("Historial de pagos")

if pagos:
    total_vista_pagos = pagos_vista_df["Monto"].sum()
    total_general_pagos = pagos_df["Monto"].sum()

    c1, c2 = st.columns(2)
    c1.metric(f"Total de {titulo_vista_pagos}", money(total_vista_pagos))
    c2.metric("Total general de pagos (todos los meses)", money(total_general_pagos))

    if not pagos_vista_df.empty:
        st.caption("Toca el icono 🗑️ junto a un pago para eliminarlo (por ejemplo, si tiene un error).")

        header_cols = st.columns([0.7, 1.4, 1.1, 1.0, 1.1, 1.1, 0.6])
        for col, label in zip(header_cols, ["Apto", "Inquilino", "Telefono", "Fecha", "Monto", "Pendiente", ""]):
            col.markdown(f"**{label}**")

        for r in pagos_vista_df.itertuples():
            row_id = r.ID
            with st.container(border=True):
                row_cols = st.columns([0.7, 1.4, 1.1, 1.0, 1.1, 1.1, 0.6])
                row_cols[0].write(r.Apartamento)
                row_cols[1].write(r.Inquilino)
                row_cols[2].write(r.Telefono)
                row_cols[3].write(fecha_dmy(r.Fecha))
                row_cols[4].write(money(r.Monto))
                if r.Pendiente and float(r.Pendiente) > 0:
                    row_cols[5].markdown(f":red[{money(r.Pendiente)}]")
                else:
                    row_cols[5].write("—")
                if row_cols[6].button("🗑️", key=f"borrar_pago_{row_id}", help="Eliminar este pago"):
                    st.session_state["confirmar_borrar_pago_id"] = row_id
                    st.rerun()

                if st.session_state.get("confirmar_borrar_pago_id") == row_id:
                    st.warning(
                        f"¿Seguro que deseas eliminar el pago de **{r.Inquilino}** "
                        f"(Apto {r.Apartamento}) por **{money(r.Monto)}** del "
                        f"{fecha_dmy(r.Fecha)}? Esta accion no se puede deshacer."
                    )
                    confirm_cols = st.columns(2)
                    if confirm_cols[0].button("Si, eliminar", key=f"si_pago_{row_id}", type="primary"):
                        db.delete_ingreso(row_id)
                        st.session_state.pop("confirmar_borrar_pago_id", None)
                        st.success("Pago eliminado.")
                        st.rerun()
                    if confirm_cols[1].button("Cancelar", key=f"no_pago_{row_id}"):
                        st.session_state.pop("confirmar_borrar_pago_id", None)
                        st.rerun()

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
else:
    st.info("Aun no hay pagos de alquiler registrados.")

