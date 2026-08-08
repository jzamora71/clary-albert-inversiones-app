"""
db.py -- Permanent storage for the app's data:
  - inquilinos: the tenant directory (13 apartments, name + contact number)
  - ingresos: rent payments (used to be a generic "income" table; now every
    row represents one tenant's monthly rent payment -- apartment number,
    tenant name, contact number, date paid, and amount paid)
  - gastos: expenses (unchanged)

IMPORTANT BACKGROUND: Streamlit Community Cloud's free hosting does not
guarantee local files survive app restarts/reboots/redeploys -- the
container filesystem is wiped and rebuilt from the GitHub repo each time.
That means a plain local SQLite file (data.db) is NOT truly permanent
storage on the deployed app, even though it works fine for local testing.

The real fix: connect to an external database that lives outside of
Streamlit's own servers -- in this project, a free Supabase Postgres
database. Once the connection details are added to Streamlit's "Secrets"
(see README.md for the exact setup steps), every payment/expense is
written straight to Supabase and will never be lost by an app restart.

This module automatically uses Supabase when the secret is configured,
and quietly falls back to a local data.db file otherwise (this fallback
is what keeps local development/testing working without needing Supabase
credentials -- it is NOT persistent when deployed).
"""

from pathlib import Path

import streamlit as st
from sqlalchemy import text

DB_PATH = Path(__file__).parent / "data.db"
CONNECTION_NAME = "supabase_db"
NUM_APARTAMENTOS = 13

# Expense categories. "Pago del gerente" is kept as a label for backward
# compatibility with any expense rows entered manually before the
# automatic commission below existed -- the manager's pay is calculated
# automatically (see MANAGER_NAME / PORCENTAJE_GERENTE) from the monthly
# bank deposit instead of being typed in as a plain expense. The Gastos
# page lets the user pick one of the four categories below for every
# other expense; TIPO_OTRO_GASTO also acts as the catch-all bucket for any
# expense rows saved before these categories existed (old "Otros gastos"
# rows still show up correctly grouped under it in the income statement).
TIPO_PAGO_GERENTE = "Pago del gerente"
TIPO_NOMINA = "Nómina"
TIPO_ADMIN = "Gastos administrativos"
TIPO_ELECTRICIDAD = "Electricidad"
TIPO_OTRO_GASTO = "Reparaciones y otros gastos"
TIPOS_GASTO = [TIPO_NOMINA, TIPO_ADMIN, TIPO_ELECTRICIDAD, TIPO_OTRO_GASTO]

# Every row in "ingresos" is tagged with tipo_ingreso so rent payments and
# "Otros ingresos" (any other income that isn't rent -- a refund, a one-time
# sale, etc.) can share the same table without mixing into each other's
# totals. Existing rows saved before this column existed have tipo_ingreso
# = NULL; they are always treated as rent (see COALESCE usage below) so no
# historical rent total silently changes because of this update.
TIPO_INGRESO_ALQUILER = "alquiler"
TIPO_INGRESO_OTRO = "otro"

# The building manager is paid a commission of whatever gets deposited
# into the bank account each month. PORCENTAJE_GERENTE below is only the
# default used the very first time the app runs -- once someone saves a
# new percentage from the Reporte page (see get/set_porcentaje_gerente),
# that saved value is used instead, so it survives app restarts.
MANAGER_NAME = "Rafael Guerrero"
PORCENTAJE_GERENTE = 0.10
CONFIG_PORCENTAJE_GERENTE = "porcentaje_gerente"


def _has_supabase_secret():
    try:
        return "connections" in st.secrets and CONNECTION_NAME in st.secrets["connections"]
    except Exception:
        return False


def using_supabase():
    """True if the app is configured to use permanent Supabase storage."""
    return _has_supabase_secret()


def get_conn():
    if _has_supabase_secret():
        return st.connection(CONNECTION_NAME, type="sql")
    # Local fallback only -- not persistent when deployed on Streamlit Cloud.
    return st.connection("local_fallback_db", type="sql", url=f"sqlite:///{DB_PATH}")


def _id_column_sql(dialect_name):
    if dialect_name == "sqlite":
        return "id INTEGER PRIMARY KEY AUTOINCREMENT"
    return "id SERIAL PRIMARY KEY"


def _add_column_if_missing(session, table, column, coltype):
    try:
        session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
        session.commit()
    except Exception:
        session.rollback()


def init_db():
    conn = get_conn()
    dialect = conn.engine.dialect.name
    id_col = _id_column_sql(dialect)

    with conn.session as s:
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS ingresos ("
            f"{id_col}, concepto TEXT NOT NULL, fecha TEXT NOT NULL, monto REAL NOT NULL)"
        ))
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS gastos ("
            f"{id_col}, concepto TEXT NOT NULL, fecha TEXT NOT NULL, monto REAL NOT NULL)"
        ))
        s.execute(text(
            "CREATE TABLE IF NOT EXISTS inquilinos ("
            "apartamento INTEGER PRIMARY KEY, nombre TEXT, telefono TEXT)"
        ))
        s.execute(text(
            "CREATE TABLE IF NOT EXISTS depositos ("
            "mes TEXT PRIMARY KEY, monto REAL NOT NULL DEFAULT 0)"
        ))
        s.execute(text(
            "CREATE TABLE IF NOT EXISTS configuracion ("
            "clave TEXT PRIMARY KEY, valor REAL NOT NULL)"
        ))
        s.commit()

    # Rent payments now need apartment number + contact number too. These
    # ALTERs only ever run once each -- if the columns already exist, the
    # error is caught and ignored (see _add_column_if_missing).
    with conn.session as s:
        _add_column_if_missing(s, "ingresos", "apartamento", "INTEGER")
        _add_column_if_missing(s, "ingresos", "telefono", "TEXT")
        _add_column_if_missing(s, "ingresos", "pendiente", "REAL")
        _add_column_if_missing(s, "ingresos", "tipo_ingreso", "TEXT")
        _add_column_if_missing(s, "gastos", "categoria", "TEXT")

    # Make sure all 13 apartments exist in the tenant directory so the
    # payment form always has something to show, even before any tenant
    # info has been entered.
    with conn.session as s:
        for apt in range(1, NUM_APARTAMENTOS + 1):
            try:
                if dialect == "sqlite":
                    s.execute(
                        text("INSERT OR IGNORE INTO inquilinos (apartamento, nombre, telefono) VALUES (:a, '', '')"),
                        {"a": apt},
                    )
                else:
                    s.execute(
                        text(
                            "INSERT INTO inquilinos (apartamento, nombre, telefono) VALUES (:a, '', '') "
                            "ON CONFLICT (apartamento) DO NOTHING"
                        ),
                        {"a": apt},
                    )
            except Exception:
                s.rollback()
        s.commit()


# --- Inquilinos (tenant directory) -----------------------------------------

def get_inquilinos():
    conn = get_conn()
    df = conn.query(
        "SELECT apartamento, nombre, telefono FROM inquilinos ORDER BY apartamento", ttl=0
    )
    return df.to_dict("records")


def get_inquilino(apartamento):
    for row in get_inquilinos():
        if int(row["apartamento"]) == int(apartamento):
            return row
    return {"apartamento": apartamento, "nombre": "", "telefono": ""}


def upsert_inquilino(apartamento, nombre, telefono):
    conn = get_conn()
    dialect = conn.engine.dialect.name
    with conn.session as s:
        if dialect == "sqlite":
            s.execute(
                text(
                    "INSERT INTO inquilinos (apartamento, nombre, telefono) VALUES (:a, :n, :t) "
                    "ON CONFLICT(apartamento) DO UPDATE SET nombre = :n, telefono = :t"
                ),
                {"a": apartamento, "n": nombre, "t": telefono},
            )
        else:
            s.execute(
                text(
                    "INSERT INTO inquilinos (apartamento, nombre, telefono) VALUES (:a, :n, :t) "
                    "ON CONFLICT (apartamento) DO UPDATE SET nombre = EXCLUDED.nombre, telefono = EXCLUDED.telefono"
                ),
                {"a": apartamento, "n": nombre, "t": telefono},
            )
        s.commit()


# --- Depositos bancarios mensuales / pago al gerente -----------------------

def get_depositos():
    """All monthly bank-deposit amounts, keyed by 'YYYY-MM'."""
    conn = get_conn()
    df = conn.query("SELECT mes, monto FROM depositos ORDER BY mes", ttl=0)
    return df.to_dict("records")


def get_deposito(mes):
    """Deposit amount registered for one month ('YYYY-MM'), or 0.0."""
    for row in get_depositos():
        if row["mes"] == mes:
            return float(row["monto"])
    return 0.0


def upsert_deposito(mes, monto):
    """Save/update the amount deposited in the bank for one month. The
    manager's pay for that month is always PORCENTAJE_GERENTE of this
    value -- it is computed on the fly wherever it's needed, never stored
    as a separate number, so it's always in sync with the deposit."""
    conn = get_conn()
    dialect = conn.engine.dialect.name
    with conn.session as s:
        if dialect == "sqlite":
            s.execute(
                text(
                    "INSERT INTO depositos (mes, monto) VALUES (:m, :v) "
                    "ON CONFLICT(mes) DO UPDATE SET monto = :v"
                ),
                {"m": mes, "v": monto},
            )
        else:
            s.execute(
                text(
                    "INSERT INTO depositos (mes, monto) VALUES (:m, :v) "
                    "ON CONFLICT (mes) DO UPDATE SET monto = EXCLUDED.monto"
                ),
                {"m": mes, "v": monto},
            )
        s.commit()


# --- Configuracion (porcentaje de pago automatico al gerente) -------------

def get_porcentaje_gerente():
    """Current percentage (as a decimal, e.g. 0.10 = 10%) used to calculate
    the automatic manager commission from the monthly bank deposit. Falls
    back to the PORCENTAJE_GERENTE default if nothing was saved yet."""
    conn = get_conn()
    df = conn.query(
        f"SELECT valor FROM configuracion WHERE clave = '{CONFIG_PORCENTAJE_GERENTE}'",
        ttl=0,
    )
    if df.empty:
        return PORCENTAJE_GERENTE
    return float(df.iloc[0]["valor"])


def set_porcentaje_gerente(valor):
    """Save a new percentage (decimal, e.g. 0.12 = 12%) for the automatic
    manager commission calculation. Persists across restarts."""
    conn = get_conn()
    dialect = conn.engine.dialect.name
    with conn.session as s:
        if dialect == "sqlite":
            s.execute(
                text(
                    "INSERT INTO configuracion (clave, valor) VALUES (:c, :v) "
                    "ON CONFLICT(clave) DO UPDATE SET valor = :v"
                ),
                {"c": CONFIG_PORCENTAJE_GERENTE, "v": valor},
            )
        else:
            s.execute(
                text(
                    "INSERT INTO configuracion (clave, valor) VALUES (:c, :v) "
                    "ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor"
                ),
                {"c": CONFIG_PORCENTAJE_GERENTE, "v": valor},
            )
        s.commit()


# --- Ingresos / pagos de alquiler ------------------------------------------

def add_pago_alquiler(apartamento, nombre, telefono, fecha, monto, pendiente=0.0):
    """Register one tenant's rent payment for the given date/amount.

    `pendiente` is however much of that period's rent is still owed (0 if
    the tenant paid in full). It is saved alongside the payment so the
    Reporte page can show who still owes money.
    """
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "INSERT INTO ingresos (concepto, fecha, monto, apartamento, telefono, pendiente, tipo_ingreso) "
                "VALUES (:c, :f, :m, :a, :t, :p, :ti)"
            ),
            {
                "c": nombre,
                "f": fecha,
                "m": monto,
                "a": apartamento,
                "t": telefono,
                "p": pendiente or 0.0,
                "ti": TIPO_INGRESO_ALQUILER,
            },
        )
        s.commit()
    # Keep the tenant directory in sync so next month's form is pre-filled.
    upsert_inquilino(apartamento, nombre, telefono)


def add_ingreso(concepto, fecha, monto):
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text("INSERT INTO ingresos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
            {"c": concepto, "f": fecha, "m": monto},
        )
        s.commit()


def add_otro_ingreso(concepto, fecha, monto):
    """Register a non-rent income entry (a refund, a one-time sale, etc.).
    Saved in the same 'ingresos' table as rent payments, but tagged with
    tipo_ingreso='otro' and no apartment/tenant info, so it never mixes
    into the rent-only totals used across the rest of the app."""
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text(
                "INSERT INTO ingresos (concepto, fecha, monto, tipo_ingreso) "
                "VALUES (:c, :f, :m, :ti)"
            ),
            {"c": concepto, "f": fecha, "m": monto, "ti": TIPO_INGRESO_OTRO},
        )
        s.commit()


def add_gasto(concepto, fecha, monto, categoria=TIPO_OTRO_GASTO):
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text("INSERT INTO gastos (concepto, fecha, monto, categoria) VALUES (:c, :f, :m, :cat)"),
            {"c": concepto, "f": fecha, "m": monto, "cat": categoria or TIPO_OTRO_GASTO},
        )
        s.commit()


def get_ingresos():
    conn = get_conn()
    df = conn.query(
        f"SELECT id, concepto, fecha, monto FROM ingresos "
        f"WHERE COALESCE(tipo_ingreso, '{TIPO_INGRESO_ALQUILER}') = '{TIPO_INGRESO_ALQUILER}' "
        f"ORDER BY fecha, id",
        ttl=0,
    )
    return df.to_dict("records")


def get_pagos_alquiler():
    """Rent payments with apartment number and contact number included.
    Rows saved before tipo_ingreso existed (NULL) are treated as rent too,
    so no historical total changes because of the 'Otros ingresos' feature.
    """
    conn = get_conn()
    df = conn.query(
        f"SELECT id, apartamento, concepto AS nombre, telefono, fecha, monto, "
        f"COALESCE(pendiente, 0) AS pendiente "
        f"FROM ingresos WHERE COALESCE(tipo_ingreso, '{TIPO_INGRESO_ALQUILER}') = '{TIPO_INGRESO_ALQUILER}' "
        f"ORDER BY fecha DESC, id DESC",
        ttl=0,
    )
    return df.to_dict("records")


def get_otros_ingresos():
    """Non-rent income entries only (tipo_ingreso='otro')."""
    conn = get_conn()
    df = conn.query(
        f"SELECT id, concepto, fecha, monto FROM ingresos "
        f"WHERE tipo_ingreso = '{TIPO_INGRESO_OTRO}' ORDER BY fecha DESC, id DESC",
        ttl=0,
    )
    return df.to_dict("records")


def get_gastos():
    conn = get_conn()
    df = conn.query(
        "SELECT id, concepto, fecha, monto, "
        "COALESCE(categoria, 'Otros gastos') AS categoria "
        "FROM gastos ORDER BY fecha DESC, id DESC",
        ttl=0,
    )
    return df.to_dict("records")


def delete_ingreso(row_id):
    conn = get_conn()
    with conn.session as s:
        s.execute(text("DELETE FROM ingresos WHERE id = :id"), {"id": row_id})
        s.commit()


def delete_gasto(row_id):
    conn = get_conn()
    with conn.session as s:
        s.execute(text("DELETE FROM gastos WHERE id = :id"), {"id": row_id})
        s.commit()


def import_ingresos_df(df):
    conn = get_conn()
    has_apt = "Apartamento" in df.columns
    has_tel = "Telefono" in df.columns
    with conn.session as s:
        for _, row in df.iterrows():
            if has_apt or has_tel:
                s.execute(
                    text(
                        "INSERT INTO ingresos (concepto, fecha, monto, apartamento, telefono) "
                        "VALUES (:c, :f, :m, :a, :t)"
                    ),
                    {
                        "c": str(row["Concepto"]) if "Concepto" in df.columns else str(row.get("nombre", "")),
                        "f": str(row["Fecha"]),
                        "m": float(row["Monto"]),
                        "a": int(row["Apartamento"]) if has_apt and str(row["Apartamento"]).strip() != "" else None,
                        "t": str(row["Telefono"]) if has_tel else "",
                    },
                )
            else:
                s.execute(
                    text("INSERT INTO ingresos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
                    {"c": str(row["Concepto"]), "f": str(row["Fecha"]), "m": float(row["Monto"])},
                )
        s.commit()


def import_gastos_df(df):
    conn = get_conn()
    cat_col = "Categoria" if "Categoria" in df.columns else ("Tipo" if "Tipo" in df.columns else None)
    with conn.session as s:
        for _, row in df.iterrows():
            categoria = str(row[cat_col]).strip() if cat_col else ""
            categoria = categoria if categoria in TIPOS_GASTO else TIPO_OTRO_GASTO
            s.execute(
                text("INSERT INTO gastos (concepto, fecha, monto, categoria) VALUES (:c, :f, :m, :cat)"),
                {
                    "c": str(row["Concepto"]),
                    "f": str(row["Fecha"]),
                    "m": float(row["Monto"]),
                    "cat": categoria,
                },
            )
        s.commit()
