"""
db.py -- Permanent storage for Ingresos and Gastos using a small SQLite file
(data.db) instead of st.session_state.

Why this matters: st.session_state only lives for the duration of one
running app process. As soon as Streamlit restarts the app (or you close
and reopen after a while), session_state is wiped. Writing to data.db
means the numbers survive normal restarts and the "app went to sleep"
wake-ups on Streamlit Community Cloud.

Important limitation (be upfront about this with the user): Streamlit
Community Cloud's free tier does not guarantee the local filesystem lasts
forever -- a full redeploy (new code pushed) or a manual "Reboot app" can
wipe data.db. That's why this module is paired with CSV backup/restore
helpers used on the Reporte page, so there's always a way to recover.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concepto TEXT NOT NULL,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concepto TEXT NOT NULL,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL
            )
            """
        )
        conn.commit()


def add_ingreso(concepto, fecha, monto):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ingresos (concepto, fecha, monto) VALUES (?, ?, ?)",
            (concepto, fecha, monto),
        )
        conn.commit()


def add_gasto(concepto, fecha, monto):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gastos (concepto, fecha, monto) VALUES (?, ?, ?)",
            (concepto, fecha, monto),
        )
        conn.commit()


def get_ingresos():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, concepto, fecha, monto FROM ingresos ORDER BY fecha, id"
        ).fetchall()
        return [dict(r) for r in rows]


def get_gastos():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, concepto, fecha, monto FROM gastos ORDER BY fecha, id"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_ingreso(row_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ingresos WHERE id = ?", (row_id,))
        conn.commit()


def delete_gasto(row_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id = ?", (row_id,))
        conn.commit()


def import_ingresos_df(df):
    with get_connection() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT INTO ingresos (concepto, fecha, monto) VALUES (?, ?, ?)",
                (str(row["Concepto"]), str(row["Fecha"]), float(row["Monto"])),
            )
        conn.commit()


def import_gastos_df(df):
    with get_connection() as conn:
        for _, row in df.iterrows():
            conn.execute(
                "INSERT INTO gastos (concepto, fecha, monto) VALUES (?, ?, ?)",
                (str(row["Concepto"]), str(row["Fecha"]), float(row["Monto"])),
            )
        conn.commit()
