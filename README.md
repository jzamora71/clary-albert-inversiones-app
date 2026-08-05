# Clary & Albert Inversiones — Contabilidad

## Project structure

```
clary_albert_app/
  app.py                 <- Homepage ONLY (logo, welcome message, nav buttons)
  utils.py                <- Shared helpers used by every page
  db.py                    <- Permanent storage for Inquilinos/Pagos de Alquiler/Gastos
  data.db                  <- Local fallback database file (created automatically, not in git)
  requirements.txt
  assets/
    logo.png              <- Real logo
  pages/
    1_Pagos_de_Alquiler.py <- Tenant directory + monthly rent payment tracker (13 apartments)
    2_Gastos.py             <- Expense entry report
    3_Reporte.py            <- Summary + PDF export + backup/restore report
```

Streamlit automatically turns every file inside `/pages` into a sidebar
navigation item. The numeric prefix (`1_`, `2_`, `3_`) controls the order
they appear in the sidebar; Streamlit strips the number and underscores
when showing the label (so `1_Pagos_de_Alquiler.py` shows as "Pagos de
Alquiler").

## Pagos de Alquiler (rent payments)

The old generic "Agregar ingreso" form was replaced with a page built
specifically for this 13-apartment building:

- **Directorio de inquilinos** — an editable table (apartments 1-13) that
  stores each tenant's name and contact number, so the payment form can
  remember who lives where.
- **Registrar pago de alquiler** — select the apartment (1-13), confirm or
  update the tenant's name/phone, pick the payment date, enter the amount,
  and click "Registrar pago". This is saved permanently and also counts as
  income everywhere else in the app (homepage totals, Reporte, PDF export).
- **Historial de pagos** — every payment ever registered, with apartment
  number, tenant name, phone, date, and amount.

Under the hood this still uses the same `ingresos` table as before (with
two new columns, `apartamento` and `telefono`), so no existing data is
lost and the rest of the app (Reporte totals, PDF, CSV backup/restore)
keeps working without any extra setup.

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

Ingresos and Gastos are saved through `db.py`. There are two modes:

- **Local fallback (default, NOT permanent on Streamlit Cloud)** -- writes
  to a local file `data.db`. Fine for testing on your own computer, but
  Streamlit Community Cloud's free tier does not guarantee this file
  survives an app restart, reboot, or redeploy -- it can silently reset to
  empty.
- **Supabase (permanent, recommended for the live app)** -- writes to a
  free hosted Postgres database that lives outside of Streamlit entirely,
  so your data survives no matter what happens to the app container.

The app automatically uses Supabase once it's configured, and otherwise
quietly falls back to the local file. The homepage shows a small caption
telling you which mode is currently active.

### One-time Supabase setup (do this once for the live app)

1. Go to [supabase.com](https://supabase.com) and sign up for a free
   account (you can sign up with your GitHub account -- the same
   `jzamora71` account already used for this project).
2. Click **New project**. Give it any name (e.g. `clary-albert-inversiones`),
   choose any region close to you, and set a database password -- write
   this password down somewhere safe, you'll need it in the next step.
3. Wait about 1-2 minutes for the project to finish setting up.
4. In the left sidebar, click the **Connect** button (or go to
   **Project Settings > Database**). Look for the **Connection string**
   section and copy the **URI** under "Session pooler" (recommended for
   Streamlit Cloud). It looks like:
   `postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-region.pooler.supabase.com:5432/postgres`
5. Replace `[YOUR-PASSWORD]` in that string with the real database
   password you set in step 2.
6. Go to your app on [share.streamlit.io](https://share.streamlit.io),
   click the **⋮** menu next to your app, then **Settings > Secrets**.
7. Paste the following into the Secrets box, using your real connection
   string from step 5:

   ```toml
   [connections.supabase_db]
   url = "postgresql://postgres.xxxxx:YOUR-PASSWORD@aws-0-region.pooler.supabase.com:5432/postgres"
   ```
8. Click **Save**. The app will automatically restart and reconnect --
   the homepage caption should switch to "Almacenamiento permanente
   activo (Supabase)".

**Never commit the real connection string to GitHub** -- it only goes
into Streamlit's Secrets box, which is private and separate from the
code repository.

### Backup and restore (safety net either way)

The Reporte page always has a "Respaldo y restauracion de datos" section,
regardless of which storage mode is active:

- **Download a backup**: click "Descargar respaldo de Ingresos (CSV)" and
  "Descargar respaldo de Gastos (CSV)" every so often and save those
  files somewhere safe.
- **Restore from a backup**: if the numbers are ever unexpectedly empty,
  upload your most recent backup CSV in that same section to bring the
  data back.

## Notes

- If you ever add a new report, create a new file inside `/pages`
  (e.g. `pages/4_NuevoReporte.py`) instead of adding code to `app.py`.
