# Clary & Albert Inversiones — Contabilidad

## Project structure

```
clary_albert_app/
  app.py                 <- Homepage ONLY (logo, welcome message, nav buttons)
  utils.py                <- Shared helpers used by every page
  db.py                    <- Permanent storage (SQLite) for Ingresos/Gastos
  data.db                  <- The database file itself (created automatically, not in git)
  requirements.txt
  assets/
    logo.png              <- Real logo
  pages/
    1_Ingresos.py          <- Income entry report
    2_Gastos.py             <- Expense entry report
    3_Reporte.py            <- Summary + PDF export + backup/restore report
```

Streamlit automatically turns every file inside `/pages` into a sidebar
navigation item. The numeric prefix (`1_`, `2_`, `3_`) controls the order
they appear in the sidebar; Streamlit strips the number and underscores
when showing the label (so `1_Ingresos.py` shows as "Ingresos").

## Why the report no longer opens automatically

Before, all of the report code (forms, tables, PDF generation) lived
directly inside `app.py`. Streamlit runs the entire script top to bottom
every time the page loads, so the report logic executed immediately,
before you ever saw a landing page.

Now `app.py` only contains the homepage: logo, welcome message, a quick
totals preview, and three buttons. None of the code inside `/pages` runs
until Streamlit actually navigates to that page — either because the user
clicked "Ingresos" / "Gastos" / "Reporte" in the left sidebar, or clicked
one of the three buttons on the homepage (which call `st.switch_page(...)`
only inside their `if st.button(...):` block).

`app.py` also calls `init_session_state()` from `utils.py` at the top.
That function uses `st.session_state.setdefault(...)`, which only creates
the `ingresos` / `gastos` storage the very first time — it never resets
data and never triggers any report screen. This is the "session_state
check" that keeps the landing page as the first thing you see.

## How to run it

1. Open a terminal in the `clary_albert_app` folder (the one that
   contains `app.py`).
2. Install the required packages (only needed once):
   ```
   python -m pip install -r requirements.txt
   ```
3. Start the app:
   ```
   streamlit run app.py
   ```
4. Your browser should open to the homepage automatically. If it
   doesn't, open the "Local URL" shown in the terminal
   (usually `http://localhost:8501`).

## Replacing the placeholder logo

`assets/logo.png` is a simple placeholder. To use your real logo:
1. Save your logo file as a PNG.
2. Rename it to `logo.png`.
3. Replace the file at `clary_albert_app/assets/logo.png` with it.
4. Refresh the browser tab (no code changes needed).

## Permanent data storage (Ingresos / Gastos)

Ingresos and Gastos are now saved to a small database file, `data.db`,
using `db.py`. This means the numbers survive:

- Navigating between Ingresos, Gastos, Reporte, and the homepage
- Closing the app and reopening it later
- The "this app has gone to sleep" wake-up screen on Streamlit Community
  Cloud (waking it up resumes the same files)

**Important limitation**: Streamlit Community Cloud's free tier does not
guarantee `data.db` survives forever. If the app is redeployed with new
code, or manually rebooted from the dashboard, the database file can be
reset to empty. To protect against that, the Reporte page has a
"Respaldo y restauracion de datos" section:

- **Download a backup**: click "Descargar respaldo de Ingresos (CSV)" and
  "Descargar respaldo de Gastos (CSV)" every so often (e.g. after adding
  a batch of entries) and save those files somewhere safe.
- **Restore from a backup**: if you ever open the app and the numbers are
  unexpectedly empty, upload your most recent backup CSV in that same
  section to bring the data back.

## Notes

- If you ever add a new report, create a new file inside `/pages`
  (e.g. `pages/4_NuevoReporte.py`) instead of adding code to `app.py`.
