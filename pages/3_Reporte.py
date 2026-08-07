"""
pages/3_Reporte.py -- Summary report + PDF export + backup/restore.

Runs only when the user clicks "Reporte" in the sidebar or the
"Ver Reporte" button on the homepage. The PDF is only generated when this
page is actually opened, never when app.py first loads.

Pagos de alquiler / Gastos are read through db.py, which uses Supabase
(permanent) once configured, or a local file (not persistent when
deployed) otherwise. As a safety net either way, this page also offers a
CSV backup download and a CSV restore uploader.

The manager's pay is calculated automatically here: each month you enter
how much was deposited into the bank account, and the report computes
PORCENTAJE_GERENTE (10%) of that as the amount owed to db.MANAGER_NAME
(Rafael Guerrero). That amount is treated as an expense and subtracted
from the balance, right alongside any other expenses entered on the
Gastos page. The monthly summary table shows rent collected, the amount
deposited, the manager's cut, other expenses, and the balance left over
each month, ending with a running "Total general" row.
"""

from datetime import date

import pandas as pd
import streamlit as st

import db
from utils import (
    COMPANY_NAME,
    build_pdf,
    fecha_dmy,
    init_session_state,
    kpi_card,
    mes_key,
    mes_label,
    money,
    money_input,
    rango_meses,
)

st.set_page_config(page_title=f"Reporte - {COMPANY_NAME}", page_icon="📊", layout="wide")

init_session_state()
db.init_db()

st.page_link("app.py", label="🏠 Volver al inicio", icon=None)

st.title("📊 Reporte")
st.caption(f"{COMPANY_NAME} - Reporte contable")

empresa = st.text_input("Nombre de la empresa", value=COMPANY_NAME)
fecha_reporte = st.date_input("Fecha del reporte (dia/mes/año)", value=date.today())

# --- Load everything needed for the totals and the monthly summary --------
pagos_raw = db.get_pagos_alquiler()
gastos_raw = db.get_gastos()
depositos_raw = {row["mes"]: float(row["monto"]) for row in db.get_depositos()}

ingresos_df = (
    pd.DataFrame(pagos_raw)[["apartamento", "nombre", "telefono", "fecha", "monto", "pendiente"]].rename(
        columns={
            "apartamento": "Apartamento",
            "nombre": "Concepto",
            "telefono": "Telefono",
            "fecha": "Fecha",
            "monto": "Monto",
            "pendiente": "Pendiente",
        }
    )
    if pagos_raw
    else pd.DataFrame(columns=["Apartamento", "Concepto", "Telefono", "Fecha", "Monto", "Pendiente"])
)
gastos_df = (
    pd.DataFrame(gastos_raw)[["categoria", "concepto", "fecha", "monto"]].rename(
        columns={"categoria": "Categoria", "concepto": "Concepto", "fecha": "Fecha", "monto": "Monto"}
    )
    if gastos_raw
    else pd.DataFrame(columns=["Categoria", "Concepto", "Fecha", "Monto"])
)

# --- Group everything by month ---------------------------------------------
ingresos_por_mes = (
    ingresos_df.assign(Mes=ingresos_df["Fecha"].apply(mes_key)).groupby("Mes")["Monto"].sum()
    if not ingresos_df.empty
    else pd.Series(dtype=float)
)
# Legacy manual "Pago del gerente" expense rows -- kept so nothing entered
# before this automatic calculation existed silently disappears.
gerente_manual_por_mes = (
    gastos_df.loc[gastos_df["Categoria"] == db.TIPO_PAGO_GERENTE]
    .assign(Mes=lambda d: d["Fecha"].apply(mes_key))
    .groupby("Mes")["Monto"]
    .sum()
    if not gastos_df.empty
    else pd.Series(dtype=float)
)
otros_por_mes = (
    gastos_df.loc[gastos_df["Categoria"] != db.TIPO_PAGO_GERENTE]
    .assign(Mes=lambda d: d["Fecha"].apply(mes_key))
    .groupby("Mes")["Monto"]
    .sum()
    if not gastos_df.empty
    else pd.Series(dtype=float)
)

meses = sorted(
    set(ingresos_por_mes.index)
    | set(otros_por_mes.index)
    | set(gerente_manual_por_mes.index)
    | set(depositos_raw.keys())
)

filas_resumen = []
for clave in meses:
    ingreso_mes = float(ingresos_por_mes.get(clave, 0.0))
    depositado_mes = float(depositos_raw.get(clave, 0.0))
    pago_gerente_mes = depositado_mes * db.PORCENTAJE_GERENTE + float(gerente_manual_por_mes.get(clave, 0.0))
    otros_mes = float(otros_por_mes.get(clave, 0.0))
    filas_resumen.append(
        {
            "Mes": mes_label(clave),
            "Pagos de Alquiler": ingreso_mes,
            "Monto Depositado": depositado_mes,
            "Pago al Gerente": pago_gerente_mes,
            "Otros Gastos": otros_mes,
            "Balance del Mes": ingreso_mes - pago_gerente_mes - otros_mes,
        }
    )

resumen_mensual_df = pd.DataFrame(
    filas_resumen,
    columns=["Mes", "Pagos de Alquiler", "Monto Depositado", "Pago al Gerente", "Otros Gastos", "Balance del Mes"],
)

# --- Overall totals (derived from the monthly breakdown above) ------------
total_ingresos = ingresos_df["Monto"].sum() if not ingresos_df.empty else 0.0
total_gerente = resumen_mensual_df["Pago al Gerente"].sum() if not resumen_mensual_df.empty else 0.0
total_otros_gastos = resumen_mensual_df["Otros Gastos"].sum() if not resumen_mensual_df.empty else 0.0
total_gastos = total_gerente + total_otros_gastos
neto = total_ingresos - total_gastos

# --- Selector de mes a mostrar ----------------------------------------------
# Por defecto el reporte muestra solo el mes actual (totales y detalles de
# abajo). El cuadro "Resumen mensual" mas abajo es la unica seccion que
# siempre muestra todos los meses juntos, para quien quiera verlos todos.
mes_actual_key = mes_key(date.today().isoformat())
meses_vista_opciones = sorted(
    set(meses) | set(rango_meses(atras=12, adelante=2)) | {mes_actual_key}, reverse=True
)
opciones_selector_vista = ["TODOS"] + meses_vista_opciones
indice_default_vista = (
    opciones_selector_vista.index(mes_actual_key) if mes_actual_key in opciones_selector_vista else 0
)

mes_vista = st.selectbox(
    "Mes a mostrar",
    options=opciones_selector_vista,
    index=indice_default_vista,
    format_func=lambda clave: "Todos los meses" if clave == "TODOS" else mes_label(clave),
    key="reporte_mes_vista",
)
st.caption(
    "Los totales y las tablas de Pagos de Alquiler / Gastos de abajo muestran "
    "solo el mes seleccionado. El cuadro 'Resumen mensual' mas abajo siempre "
    "muestra todos los meses juntos, sin importar lo que elijas aqui."
)

ver_todos_los_meses = mes_vista == "TODOS"

if ver_todos_los_meses:
    ingresos_vista_df = ingresos_df
    gastos_vista_df = gastos_df
    total_ingresos_vista = total_ingresos
    total_gerente_vista = total_gerente
    total_otros_vista = total_otros_gastos
    total_gastos_vista = total_gastos
    neto_vista = neto
    titulo_vista = "Todos los meses"
else:
    ingresos_vista_df = (
        ingresos_df[ingresos_df["Fecha"].apply(mes_key) == mes_vista]
        if not ingresos_df.empty
        else ingresos_df
    )
    gastos_vista_df = (
        gastos_df[gastos_df["Fecha"].apply(mes_key) == mes_vista]
        if not gastos_df.empty
        else gastos_df
    )
    ingreso_mes_vista = float(ingresos_por_mes.get(mes_vista, 0.0))
    depositado_mes_vista = float(depositos_raw.get(mes_vista, 0.0))
    gerente_mes_vista = depositado_mes_vista * db.PORCENTAJE_GERENTE + float(
        gerente_manual_por_mes.get(mes_vista, 0.0)
    )
    otros_mes_vista = float(otros_por_mes.get(mes_vista, 0.0))
    total_ingresos_vista = ingreso_mes_vista
    total_gerente_vista = gerente_mes_vista
    total_otros_vista = otros_mes_vista
    total_gastos_vista = gerente_mes_vista + otros_mes_vista
    neto_vista = ingreso_mes_vista - gerente_mes_vista - otros_mes_vista
    titulo_vista = mes_label(mes_vista)

c1, c2, c3 = st.columns(3)
with c1:
    kpi_card(f"Total pagos de alquiler ({titulo_vista})", money(total_ingresos_vista))
with c2:
    kpi_card(f"Total gastos ({titulo_vista})", money(total_gastos_vista), expense=True)
with c3:
    kpi_card(f"Balance neto ({titulo_vista})", money(neto_vista))

c4, c5 = st.columns(2)
with c4:
    kpi_card(f"De los cuales: Pago a {db.MANAGER_NAME} ({titulo_vista})", money(total_gerente_vista), expense=True)
with c5:
    kpi_card(f"De los cuales: Otros gastos ({titulo_vista})", money(total_otros_vista), expense=True)

st.divider()

# --- Deposito bancario mensual -> pago automatico al gerente --------------
st.subheader(f"Deposito bancario mensual y pago a {db.MANAGER_NAME}")
st.caption(
    f"El pago de {db.MANAGER_NAME} se calcula automaticamente: "
    f"{int(db.PORCENTAJE_GERENTE * 100)}% de lo que se deposito en el banco "
    "ese mes. Registra aqui el monto depositado de cada mes."
)

meses_opciones = sorted(rango_meses(atras=12, adelante=2), reverse=True)
mes_actual_key = mes_key(date.today().isoformat())
indice_default = meses_opciones.index(mes_actual_key) if mes_actual_key in meses_opciones else 0

col_dep1, col_dep2 = st.columns(2)
with col_dep1:
    mes_seleccionado = st.selectbox(
        "Mes", options=meses_opciones, index=indice_default, format_func=mes_label, key="mes_deposito_sel"
    )
with col_dep2:
    monto_deposito = money_input(
        "Monto depositado en el banco ese mes",
        key=f"monto_deposito_{mes_seleccionado}",
        default=float(depositos_raw.get(mes_seleccionado, 0.0)),
    )

pago_gerente_preview = monto_deposito * db.PORCENTAJE_GERENTE
kpi_card(
    f"Pago a {db.MANAGER_NAME} ({int(db.PORCENTAJE_GERENTE * 100)}% de {mes_label(mes_seleccionado)})",
    money(pago_gerente_preview),
    expense=True,
)

if st.button("Guardar deposito de este mes", type="primary"):
    db.upsert_deposito(mes_seleccionado, float(monto_deposito))
    st.success(
        f"Deposito de {mes_label(mes_seleccionado)} guardado: {money(monto_deposito)}. "
        f"Pago a {db.MANAGER_NAME}: {money(pago_gerente_preview)}."
    )
    st.rerun()

st.divider()

# --- Resumen mensual: total por mes y gran total al final -----------------
st.subheader("Resumen mensual")
st.caption(
    "Pagos de alquiler, monto depositado, pago al gerente y otros gastos "
    "por mes. La ultima fila es el gran total acumulado."
)

if not resumen_mensual_df.empty:
    fila_total = {
        "Mes": "Total general",
        "Pagos de Alquiler": resumen_mensual_df["Pagos de Alquiler"].sum(),
        "Monto Depositado": resumen_mensual_df["Monto Depositado"].sum(),
        "Pago al Gerente": resumen_mensual_df["Pago al Gerente"].sum(),
        "Otros Gastos": resumen_mensual_df["Otros Gastos"].sum(),
        "Balance del Mes": resumen_mensual_df["Balance del Mes"].sum(),
    }
    resumen_mensual_completo = pd.concat(
        [resumen_mensual_df, pd.DataFrame([fila_total])], ignore_index=True
    )
    resumen_show = resumen_mensual_completo.copy()
    for col in ["Pagos de Alquiler", "Monto Depositado", "Pago al Gerente", "Otros Gastos", "Balance del Mes"]:
        resumen_show[col] = resumen_show[col].apply(money)
    st.dataframe(resumen_show, use_container_width=True, hide_index=True)
else:
    resumen_mensual_completo = resumen_mensual_df
    st.info("Aun no hay pagos, gastos ni depositos registrados para calcular un resumen mensual.")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader(f"Pagos de alquiler ({titulo_vista})")
    if not ingresos_vista_df.empty:
        display_df = ingresos_vista_df.rename(columns={"Concepto": "Inquilino"}).copy()
        display_df["Fecha"] = display_df["Fecha"].apply(fecha_dmy)
        st.dataframe(
            display_df.assign(Monto=display_df["Monto"].apply(money)),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aun no hay pagos de alquiler registrados en este mes.")
with col_b:
    st.subheader(f"Gastos ({titulo_vista})")
    if not gastos_vista_df.empty:
        display_gastos = gastos_vista_df.rename(columns={"Categoria": "Tipo"}).copy()
        display_gastos["Fecha"] = display_gastos["Fecha"].apply(fecha_dmy)
        st.dataframe(
            display_gastos.assign(Monto=display_gastos["Monto"].apply(money)),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aun no hay gastos registrados en este mes.")

st.divider()

# La seccion de "Pendientes por Pagar" del PDF siempre muestra TODOS los
# inquilinos que deben dinero, sin importar el mes seleccionado arriba --
# quien debe dinero es un estado actual, no algo que deba desaparecer del
# reporte solo porque se esta viendo un mes distinto.
pendientes_vista_df = (
    ingresos_df[ingresos_df["Pendiente"] > 0] if not ingresos_df.empty else ingresos_df
)
total_pendiente_vista = float(pendientes_vista_df["Pendiente"].sum()) if not pendientes_vista_df.empty else 0.0

# --- Totales "Ano hasta la fecha" para el Resumen del PDF ------------------
# El Resumen del PDF muestra: (1) el total del mes actual/seleccionado como
# dato informativo, y (2) los totales acumulados del ano en curso (ingresos,
# gastos y balance), sin importar el mes elegido arriba en "Mes a mostrar".
anio_ytd = fecha_reporte.year
meses_ytd = [clave for clave in meses if clave.startswith(f"{anio_ytd}-")]
ingreso_ytd = sum(float(ingresos_por_mes.get(clave, 0.0)) for clave in meses_ytd)
depositado_ytd = sum(float(depositos_raw.get(clave, 0.0)) for clave in meses_ytd)
gerente_manual_ytd = sum(float(gerente_manual_por_mes.get(clave, 0.0)) for clave in meses_ytd)
otros_ytd = sum(float(otros_por_mes.get(clave, 0.0)) for clave in meses_ytd)
gerente_ytd = depositado_ytd * db.PORCENTAJE_GERENTE + gerente_manual_ytd
gastos_ytd = gerente_ytd + otros_ytd
neto_ytd = ingreso_ytd - gastos_ytd

# El mes del que se informa en la linea aparte: si se eligio "Todos los
# meses" arriba, se usa el mes real de hoy; si no, el mes seleccionado.
mes_periodo_key = mes_actual_key if ver_todos_los_meses else mes_vista
total_ingresos_periodo = float(ingresos_por_mes.get(mes_periodo_key, 0.0))
periodo_label = mes_label(mes_periodo_key)

pdf_bytes = build_pdf(
    empresa=empresa,
    fecha_reporte=fecha_reporte,
    ingresos_df=ingresos_vista_df,
    gastos_df=gastos_vista_df,
    total_ingresos=ingreso_ytd,
    total_gastos=gastos_ytd,
    neto=neto_ytd,
    resumen_mensual_df=resumen_mensual_completo,
    pendientes_df=pendientes_vista_df,
    total_pendiente=total_pendiente_vista,
    total_ingresos_periodo=total_ingresos_periodo,
    periodo_label=periodo_label,
    anio_ytd=anio_ytd,
)

sufijo_archivo = "todos_los_meses" if ver_todos_los_meses else mes_vista
st.download_button(
    label=f"Descargar reporte PDF ({titulo_vista})",
    data=pdf_bytes,
    file_name=f"reporte_contable_clary_albert_{sufijo_archivo}.pdf",
    mime="application/pdf",
)

st.divider()

# --- Backup / restore -------------------------------------------------
# Safety net either way: download a CSV copy regularly, and restore from
# it here if the numbers ever come back empty unexpectedly (e.g. before
# Supabase was configured, or if a secret gets misconfigured).
with st.expander("💾 Respaldo y restauracion de datos"):
    st.markdown(
        "Descarga una copia de tus datos de vez en cuando. Si alguna vez "
        "la app reinicia y los datos aparecen vacios, puedes restaurarlos "
        "aqui subiendo el ultimo respaldo que descargaste."
    )

    back_col1, back_col2 = st.columns(2)
    with back_col1:
        st.download_button(
            "Descargar respaldo de Pagos de Alquiler (CSV)",
            data=ingresos_df.to_csv(index=False).encode("utf-8"),
            file_name="respaldo_pagos_alquiler.csv",
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
        ingresos_upload = st.file_uploader(
            "Subir respaldo de Pagos de Alquiler (CSV)", type="csv", key="ingresos_upload"
        )
        if ingresos_upload is not None:
            if st.button("Restaurar Pagos de Alquiler desde este archivo"):
                restore_df = pd.read_csv(ingresos_upload)
                db.import_ingresos_df(restore_df)
                st.success("Pagos de alquiler restaurados. Recarga la pagina para verlos.")
    with restore_col2:
        gastos_upload = st.file_uploader("Subir respaldo de Gastos (CSV)", type="csv", key="gastos_upload")
        if gastos_upload is not None:
            if st.button("Restaurar Gastos desde este archivo"):
                restore_df = pd.read_csv(gastos_upload)
                db.import_gastos_df(restore_df)
                st.success("Gastos restaurados. Recarga la pagina para verlos.")
