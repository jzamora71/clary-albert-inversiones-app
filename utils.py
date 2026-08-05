"""
Shared helpers used across app.py and all pages in /pages.

Keeping this logic in one place means every page (Ingresos, Gastos, Reporte)
formats money and builds PDFs the exact same way, and the session_state keys
that hold the data are only ever created once.
"""

from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from fpdf import FPDF

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

COMPANY_NAME = "Clary & Albert Inversiones"


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


def money(x):
    value = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"RD$ {value:,.2f}"


def money_pdf(x):
    value = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"RD$ {value:,.2f}"


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


def build_pdf(empresa, fecha_reporte, ingresos_df, gastos_df, total_ingresos, total_gastos, neto):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, sanitize_text(f"Reporte Contable - {empresa}"), ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, sanitize_text(f"Fecha del reporte: {fecha_es_larga(fecha_reporte)}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Resumen", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Total ingresos: {money_pdf(total_ingresos)}", ln=True)
    pdf.cell(0, 7, f"Total gastos: {money_pdf(total_gastos)}", ln=True)
    pdf.cell(0, 7, f"Balance neto: {money_pdf(neto)}", ln=True)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Ingresos", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 8, "Concepto", border=1)
    pdf.cell(40, 8, "Fecha", border=1)
    pdf.cell(45, 8, "Monto", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for _, row in ingresos_df.iterrows():
        concepto = sanitize_text(str(row["Concepto"]))[:45]
        fecha_txt = str(row["Fecha"])
        monto_txt = money_pdf(row["Monto"])
        pdf.cell(95, 8, concepto, border=1)
        pdf.cell(40, 8, fecha_txt, border=1)
        pdf.cell(45, 8, monto_txt, border=1, ln=True)

    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Gastos", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 8, "Concepto", border=1)
    pdf.cell(40, 8, "Fecha", border=1)
    pdf.cell(45, 8, "Monto", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for _, row in gastos_df.iterrows():
        concepto = sanitize_text(str(row["Concepto"]))[:45]
        fecha_txt = str(row["Fecha"])
        monto_txt = money_pdf(row["Monto"])
        pdf.cell(95, 8, concepto, border=1)
        pdf.cell(40, 8, fecha_txt, border=1)
        pdf.cell(45, 8, monto_txt, border=1, ln=True)

    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1")

    return pdf_bytes
