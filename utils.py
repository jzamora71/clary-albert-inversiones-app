"""
Shared helpers used across app.py and all pages in /pages.

Keeping this logic in one place means every page (Ingresos, Gastos, Reporte)
formats money and builds PDFs the exact same way, and the session_state keys
that hold the data are only ever created once.
"""

import os
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from fpdf import FPDF


def resource_path(*parts) -> str:
    """Build an absolute path to a bundled file (image, logo, etc.).

    Works both when running the app normally from source AND when it has
    been packaged into a standalone .exe with PyInstaller. PyInstaller
    extracts bundled data files into a temporary folder at runtime and
    exposes that folder's path via sys._MEIPASS -- when that attribute is
    missing we're running from source, so we fall back to the folder that
    contains this file.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


LOGO_PATH = resource_path("assets", "logo.jpg")
EDIFICIO_PATH = resource_path("assets", "edificio.jpg")

MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

COMPANY_NAME = "Administración de Propiedades y Finanzas"


def init_session_state():
    """Create every session_state key the app needs, exactly once per session.

    Call this at the top of app.py AND at the top of every page in /pages.
    Because st.session_state.setdefault(...) only sets a value the first
    time, this never resets data the user already entered, and it never
    triggers any report logic by itself -- it only prepares empty storage.
    """
    st.session_state.setdefault("app_initialized", True)


def fecha_es_larga(fecha):
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


def fecha_dmy(fecha_valor):
    """Format a stored date (ISO string 'YYYY-MM-DD' or a date object) as
    dia/mes/anio for display -- e.g. '2026-08-05' -> '05/08/2026'.

    Every table and PDF in the app shows dates through this helper so the
    stored value stays ISO (sorts correctly) while what the user sees is
    always day/month/year.
    """
    if fecha_valor is None or str(fecha_valor).strip() == "":
        return ""
    texto = str(fecha_valor)[:10]
    try:
        d = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return str(fecha_valor)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def mes_key(fecha_valor):
    """Return a sortable 'YYYY-MM' key for grouping entries by month."""
    return str(fecha_valor)[:7]


def mes_label(year_month_key):
    """Turn a 'YYYY-MM' key into a Spanish label, e.g. '2026-08' -> 'Agosto 2026'."""
    try:
        year_str, month_str = year_month_key.split("-")
        return f"{MESES_ES[int(month_str)].capitalize()} {year_str}"
    except (ValueError, KeyError):
        return year_month_key


def rango_meses(atras=12, adelante=2, referencia=None):
    """List of 'YYYY-MM' keys from `atras` months before today to
    `adelante` months after -- used to populate month-picker dropdowns
    (e.g. for registering a bank deposit for a given month)."""
    ref = referencia or datetime.today().date()
    base = ref.year * 12 + (ref.month - 1)
    meses = []
    for offset in range(-atras, adelante + 1):
        idx = base + offset
        year, month = divmod(idx, 12)
        meses.append(f"{year:04d}-{month + 1:02d}")
    return meses


def money(x):
    value = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"RD$ {value:,.2f}"


def money_pdf(x):
    value = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"RD$ {value:,.2f}"


def money_input(label, key, default=0.0, help=None):
    """Amount field that starts empty (showing a faint '0.00' placeholder
    instead of a real 0) and, once you finish typing and move to the next
    field, reformats what you typed with thousands separators -- e.g.
    typing 9000 becomes 9,000.00. Always returns a plain float (0.0 if the
    box is left empty or has stray characters), so the rest of the app
    never has to think about text parsing.

    `default` pre-fills the field (formatted) -- used on the Reporte page
    so a previously saved deposit shows up already filled in.
    """
    if key not in st.session_state:
        st.session_state[key] = f"{default:,.2f}" if default else ""

    raw = st.session_state[key]
    cleaned = raw.replace("RD$", "").replace(",", "").replace(" ", "").strip()
    value = 0.0
    if cleaned:
        try:
            value = float(cleaned)
        except ValueError:
            value = 0.0
        else:
            if value < 0:
                value = 0.0
            formatted = f"{value:,.2f}"
            if raw != formatted:
                st.session_state[key] = formatted

    st.text_input(label, key=key, placeholder="0.00", help=help)
    return value


def kpi_card(label, value, expense=False):
    """Compact, professionally-sized number card (replaces st.metric, whose
    default value text is very large/oversized for this app). Income and
    balance figures render in the normal dark text color; pass
    expense=True for anything that represents money going out (gastos,
    manager payment) so it renders in red -- makes it easy to see at a
    glance what's being spent versus what's coming in.
    """
    color = "#B91C1C" if expense else "#28251D"
    st.markdown(
        f"""
        <div style="border:1px solid #D4D1CA; border-radius:8px;
                    padding:12px 16px; background:#F9F8F5; margin-bottom:8px;">
            <div style="font-size:13px; color:#7A7974; margin-bottom:4px;
                        line-height:1.3;">{label}</div>
            <div style="font-size:22px; font-weight:700; color:{color};
                        line-height:1.25;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sanitize_text(text):
    if text is None:
        return ""
    replacements = {
        "á": "a", "à": "a", "ä": "a", "â": "a",
        "é": "e", "è": "e", "ë": "e", "ê": "e",
        "í": "i", "ì": "i", "ï": "i", "î": "i",
        "ó": "o", "ò": "o", "ö": "o", "ô": "o",
        "ú": "u", "ù": "u", "ü": "u", "û": "u",
        "ñ": "n",
        "Á": "A", "À": "A", "Ä": "A", "Â": "A",
        "É": "E", "È": "E", "Ë": "E", "Ê": "E",
        "Í": "I", "Ì": "I", "Ï": "I", "Î": "I",
        "Ó": "O", "Ò": "O", "Ö": "O", "Ô": "O",
        "Ú": "U", "Ù": "U", "Ü": "U", "Û": "U",
        "Ñ": "N",
        "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
        "\u2013": "-", "\u2014": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def build_pdf(
    empresa,
    fecha_reporte,
    ingresos_df,
    gastos_df,
    total_ingresos,
    total_gastos,
    neto,
    resumen_mensual_df=None,
    pendientes_df=None,
    total_pendiente=0.0,
    total_ingresos_periodo=None,
    periodo_label=None,
    anio_ytd=None,
    total_gerente=None,
    total_otros=None,
    manager_name="",
    total_otros_ingresos=0.0,
    total_nomina=None,
    total_admin=None,
    total_electricidad=None,
    total_reparaciones=None,
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=163, y=8, w=34)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Registro Contable", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, sanitize_text(f"Fecha del reporte: {fecha_es_larga(fecha_reporte)}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Resumen", ln=True)

    pdf.set_font("Helvetica", "", 11)
    if periodo_label is not None and total_ingresos_periodo is not None:
        pdf.cell(
            0,
            7,
            sanitize_text(f"Total Pagos de Alquiler ({periodo_label}): {money_pdf(total_ingresos_periodo)}"),
            ln=True,
        )
    etiqueta_ytd = f" (A\u00f1o {anio_ytd} hasta la fecha)" if anio_ytd is not None else ""
    pdf.cell(0, 7, f"Total Pagos de Alquiler{etiqueta_ytd}: {money_pdf(total_ingresos)}", ln=True)
    pdf.cell(0, 7, f"Total Gastos{etiqueta_ytd}: {money_pdf(total_gastos)}", ln=True)
    pdf.cell(0, 7, f"Balance Neto{etiqueta_ytd}: {money_pdf(neto)}", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Pendientes por Pagar", ln=True)

    tiene_pendientes = pendientes_df is not None and not pendientes_df.empty

    if tiene_pendientes:
        pdf.set_text_color(200, 0, 0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(25, 8, "Apto", border=1)
        pdf.cell(75, 8, "Inquilino", border=1)
        pdf.cell(35, 8, "Fecha", border=1)
        pdf.cell(40, 8, "Pendiente", border=1, ln=True)

        pdf.set_font("Helvetica", "", 10)
        for _, row in pendientes_df.iterrows():
            apto_txt = str(row["Apartamento"]) if str(row["Apartamento"]) != "nan" else ""
            inquilino_txt = sanitize_text(str(row["Concepto"]))[:38]
            fecha_txt = fecha_dmy(row["Fecha"])
            pendiente_txt = money_pdf(row["Pendiente"])
            pdf.cell(25, 8, apto_txt, border=1)
            pdf.cell(75, 8, inquilino_txt, border=1)
            pdf.cell(35, 8, fecha_txt, border=1)
            pdf.cell(40, 8, pendiente_txt, border=1, ln=True)

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, sanitize_text(f"Total Pendiente por Pagar: {money_pdf(total_pendiente)}"), ln=True)
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "No hay pagos pendientes.", ln=True)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, sanitize_text(f"Total Pendiente por Pagar: {money_pdf(total_pendiente)}"), ln=True)

    if resumen_mensual_df is not None and not resumen_mensual_df.empty:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Resumen Mensual", ln=True)

        has_depositado = "Monto Depositado" in resumen_mensual_df.columns
        gerente_col = "Pago al Gerente" if "Pago al Gerente" in resumen_mensual_df.columns else "Pago del Gerente"

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(32, 8, "Mes", border=1)
        pdf.cell(29, 8, "Alquiler", border=1)
        if has_depositado:
            pdf.cell(29, 8, "Depositado", border=1)
        pdf.cell(29, 8, "Gerente", border=1)
        pdf.cell(29, 8, "Otros", border=1)
        pdf.cell(29 if has_depositado else 34, 8, "Balance", border=1, ln=True)

        pdf.set_font("Helvetica", "", 9)
        for _, row in resumen_mensual_df.iterrows():
            is_total = str(row["Mes"]).strip().lower().startswith("total")
            pdf.set_font("Helvetica", "B" if is_total else "", 9)
            pdf.cell(32, 8, sanitize_text(str(row["Mes"]))[:18], border=1)
            pdf.cell(29, 8, money_pdf(row["Pagos de Alquiler"]), border=1)
            if has_depositado:
                pdf.cell(29, 8, money_pdf(row["Monto Depositado"]), border=1)
            pdf.cell(29, 8, money_pdf(row[gerente_col]), border=1)
            pdf.cell(29, 8, money_pdf(row["Otros Gastos"]), border=1)
            pdf.cell(29 if has_depositado else 34, 8, money_pdf(row["Balance del Mes"]), border=1, ln=True)

    if anio_ytd is not None:
        pdf.ln(10)

        label_w = 130
        amount_w = 50
        row_h = 8
        teal = (1, 105, 111)
        light_fill = (247, 246, 242)
        gray_line = (190, 188, 182)

        # --- Titulo con banda de color ---------------------------------
        pdf.set_fill_color(*teal)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            label_w + amount_w,
            10,
            f"  Estado de Resultados (A\u00f1o {anio_ytd} hasta la fecha)",
            fill=True,
            ln=True,
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        # --- Ingresos ---------------------------------------------------
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w + amount_w, row_h, "  Ingresos", ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(label_w, row_h, "     Ingresos por alquiler", border=0)
        pdf.cell(amount_w, row_h, money_pdf(total_ingresos), border=0, align="R", ln=True)
        pdf.cell(label_w, row_h, "     Otros ingresos", border=0)
        pdf.cell(amount_w, row_h, money_pdf(total_otros_ingresos), border=0, align="R", ln=True)

        y_line_ingresos = pdf.get_y() + 1
        pdf.set_draw_color(*gray_line)
        pdf.line(10, y_line_ingresos, 10 + label_w + amount_w, y_line_ingresos)
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w, row_h, "  Total de ingresos", border=0)
        pdf.cell(amount_w, row_h, money_pdf(total_ingresos + total_otros_ingresos), border=0, align="R", ln=True)
        pdf.ln(4)

        # --- Gastos -------------------------------------------------------
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w + amount_w, row_h, "  Gastos", ln=True)
        pdf.set_font("Helvetica", "", 11)
        if total_gerente is not None:
            etiqueta_gerente = f"Pago a {manager_name}" if manager_name else "Pago al gerente"
            pdf.cell(label_w, row_h, sanitize_text(f"     {etiqueta_gerente}"), border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_gerente), border=0, align="R", ln=True)
        if total_nomina is not None:
            pdf.cell(label_w, row_h, "     N\u00f3mina", border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_nomina), border=0, align="R", ln=True)
        if total_admin is not None:
            pdf.cell(label_w, row_h, "     Gastos administrativos", border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_admin), border=0, align="R", ln=True)
        if total_electricidad is not None:
            pdf.cell(label_w, row_h, "     Electricidad", border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_electricidad), border=0, align="R", ln=True)
        if total_reparaciones is not None:
            pdf.cell(label_w, row_h, "     Reparaciones y otros gastos", border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_reparaciones), border=0, align="R", ln=True)
        elif total_otros is not None:
            pdf.cell(label_w, row_h, "     Reparaciones y otros gastos", border=0)
            pdf.cell(amount_w, row_h, money_pdf(total_otros), border=0, align="R", ln=True)

        y_line = pdf.get_y() + 1
        pdf.set_draw_color(*gray_line)
        pdf.line(10, y_line, 10 + label_w + amount_w, y_line)
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(label_w, row_h, "  Total de gastos", border=0)
        pdf.cell(amount_w, row_h, money_pdf(total_gastos), border=0, align="R", ln=True)
        pdf.ln(4)

        # --- Utilidad neta, destacada ------------------------------------
        pdf.set_fill_color(*light_fill)
        pdf.set_draw_color(*teal)
        pdf.set_line_width(0.6)
        pdf.set_text_color(*teal)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(label_w, 11, "  Utilidad neta", border="TB", fill=True)
        pdf.cell(amount_w, 11, money_pdf(neto) + "  ", border="TB", fill=True, align="R", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_line_width(0.2)

    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")

    return pdf_bytes


def build_pagos_pdf(empresa, fecha_reporte, titulo_periodo, pagos_df, total_periodo):
    # noqa: force-redeploy-refresh
    """One-page, printable PDF with just the rent-payment detail table and
    its total for whichever month (or 'Todos los meses') the user picked on
    the Pagos de Alquiler page -- so they can save/print a record for a
    single month without pulling in expenses or the full monthly summary.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sanitize_text(f"Pagos de Alquiler - {empresa}"), ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, sanitize_text(f"Fecha del reporte: {fecha_es_larga(fecha_reporte)}"), ln=True)
    pdf.cell(0, 8, sanitize_text(f"Periodo: {titulo_periodo}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Detalle de pagos", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(20, 8, "Apto", border=1)
    pdf.cell(55, 8, "Inquilino", border=1)
    pdf.cell(35, 8, "Telefono", border=1)
    pdf.cell(35, 8, "Fecha", border=1)
    pdf.cell(35, 8, "Monto", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for _, row in pagos_df.iterrows():
        pdf.cell(20, 8, str(row["Apartamento"]), border=1)
        pdf.cell(55, 8, sanitize_text(str(row["Inquilino"]))[:28], border=1)
        pdf.cell(35, 8, sanitize_text(str(row.get("Telefono", "")))[:18], border=1)
        pdf.cell(35, 8, fecha_dmy(row["Fecha"]), border=1)
        pdf.cell(35, 8, money_pdf(row["Monto"]), border=1, ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, sanitize_text(f"Total {titulo_periodo}: {money_pdf(total_periodo)}"), ln=True)

    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")

    return pdf_bytes


