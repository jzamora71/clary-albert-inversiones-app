"""
db.py -- Permanent storage for Ingresos and Gastos.

IMPORTANT BACKGROUND: Streamlit Community Cloud's free hosting does not
guarantee local files survive app restarts/reboots/redeploys -- the
container filesystem is wiped and rebuilt from the GitHub repo each time.
That means a plain local SQLite file (data.db) is NOT truly permanent
storage on the deployed app, even though it works fine for local testing.

The real fix: connect to an external database that lives outside of
Streamlit's own servers -- in this project, a free Supabase Postgres
database. Once the connection details are added to Streamlit's "Secrets"
(see README.md for the exact setup steps), every Ingreso/Gasto is written
straight to Supabase and will never be lost by an app restart.

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


def init_db():
    conn = get_conn()
    id_col = _id_column_sql(conn.engine.dialect.name)
    with conn.session as s:
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS ingresos ("
            f"{id_col}, concepto TEXT NOT NULL, fecha TEXT NOT NULL, monto REAL NOT NULL)"
        ))
        s.execute(text(
            f"CREATE TABLE IF NOT EXISTS gastos ("
            f"{id_col}, concepto TEXT NOT NULL, fecha TEXT NOT NULL, monto REAL NOT NULL)"
        ))
        s.commit()


def add_ingreso(concepto, fecha, monto):
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text("INSERT INTO ingresos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
            {"c": concepto, "f": fecha, "m": monto},
        )
        s.commit()


def add_gasto(concepto, fecha, monto):
    conn = get_conn()
    with conn.session as s:
        s.execute(
            text("INSERT INTO gastos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
            {"c": concepto, "f": fecha, "m": monto},
        )
        s.commit()


def get_ingresos():
    conn = get_conn()
    df = conn.query(
        "SELECT id, concepto, fecha, monto FROM ingresos ORDER BY fecha, id", ttl=0
    )
    return df.to_dict("records")


def get_gastos():
    conn = get_conn()
    df = conn.query(
        "SELECT id, concepto, fecha, monto FROM gastos ORDER BY fecha, id", ttl=0
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
    with conn.session as s:
        for _, row in df.iterrows():
            s.execute(
                text("INSERT INTO ingresos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
                {"c": str(row["Concepto"]), "f": str(row["Fecha"]), "m": float(row["Monto"])},
            )
        s.commit()


def import_gastos_df(df):
    conn = get_conn()
    with conn.session as s:
        for _, row in df.iterrows():
            s.execute(
                text("INSERT INTO gastos (concepto, fecha, monto) VALUES (:c, :f, :m)"),
                {"c": str(row["Concepto"]), "f": str(row["Fecha"]), "m": float(row["Monto"])},
            )
        s.commit()
