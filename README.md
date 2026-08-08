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

## Gastos: solo "Otros gastos" now (manager pay moved to Reporte)

The **Gastos** page is only for expenses other than the manager's pay --
repairs, maintenance, supplies, etc. All entries are saved with the
category "Otro gasto" and get subtracted from rent income like before.

Manually registering the manager's payment as a Gasto is now
**deprecated**. Any old "Pago del gerente" entries created before this
change still count (for backward compatibility), but going forward the
manager's pay is calculated automatically -- see the next section.

## Pago automatico al gerente (10% del deposito bancario)

The manager, **Rafael Guerrero**, is paid **10% of whatever amount was
deposited into the bank account that month** -- not 10% of rent
collected. Because the deposit total does not always match the sum of
that month's rent payments exactly, it's entered separately:

- On the **Reporte** page, under "Deposito bancario mensual y pago a
  Rafael Guerrero", pick a month and type in the amount deposited into
  the bank that month, then click "Guardar deposito de este mes".
- The 10% commission is calculated instantly and shown live as you type
  (`Pago a Rafael Guerrero`), and is saved permanently once you click
  save (in the new `depositos` table in `db.py`).
- This calculated amount is automatically treated as an expense and
  subtracted from the balance everywhere in the app -- top metrics,
  monthly summary, and PDF report -- with no need to also add it as a
  Gasto.

## Resumen mensual y gran total (Reporte)

The Reporte page includes a **Resumen mensual** table that groups every
rent payment, bank deposit, and expense by calendar month, showing for
each month: total rent collected, the amount deposited in the bank, the
automatic 10% payment to Rafael Guerrero, other expenses, and the
balance left over. The last row, **Total general**, adds up every month
into a single grand total -- i.e. all rent income minus the manager's
pay and all other expenses, across the whole history of the app. This
same table is also printed at the end of the downloadable PDF report.

## Dates shown as dia/mes/año

Every table and the PDF report display dates as **dia/mes/año**
(e.g. `05/08/2026` for August 5th, 2026) no matter how they're stored
internally, through the `fecha_dmy()` helper in `utils.py`.

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

### Supabase project (already created for this app)

A Supabase project named **clary-albert-inversiones** has already been
created (project ref `wkxrayfxrhagshoixcxh`, region `us-east-1`), and all
four tables (`ingresos`, `gastos`, `inquilinos`, `depositos`) already
exist in it with the 13 apartments pre-loaded. The only remaining step is
getting the database password into Streamlit's Secrets -- this has to be
done by you directly, since it's a private credential:

1. Go to
   [this project's database settings](https://supabase.com/dashboard/project/wkxrayfxrhagshoixcxh/settings/database)
   (sign in with the same account you just used to connect Supabase).
2. Look for **Database password**. If you don't already have it saved
   from creation, click **Reset database password** (or **Generate a new
   password**) -- this shows the password once, so copy it immediately.
3. On the same page, find the **Connection string** section, switch to
   the **Session pooler** tab, and copy the URI. It should look like:
   `postgresql://postgres.wkxrayfxrhagshoixcxh:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres`
4. Replace `[YOUR-PASSWORD]` in that string with the real password from
   step 2.
5. Go to your app on [share.streamlit.io](https://share.streamlit.io),
   click the **⋮** menu next to your app, then **Settings > Secrets**.
6. Paste the following into the Secrets box, using your real connection
   string from step 4:

   ```toml
   [connections.supabase_db]
   url = "postgresql://postgres.wkxrayfxrhagshoixcxh:YOUR-PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
   ```
7. Click **Save**. The app will automatically restart and reconnect --
   the homepage caption should switch to "Almacenamiento permanente
   activo (Supabase)".

If you'd rather start fresh or create your own project instead, the
general steps are the same: sign up at [supabase.com](https://supabase.com),
click **New project**, wait for it to finish setting up, then follow
steps 3-7 above using your own project's ref and region.

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

## Building a standalone Windows .exe (optional, for personal/offline use)

This project can also be packaged into a standalone Windows desktop app
that runs without a browser or an internet connection, using the
`streamlit-desktop-app` + PyInstaller tools. This is separate from the
live web app at streamlit.app -- it is meant for a personal, offline
copy with its own local database, not for sharing real tenant/financial
data publicly.

**Requirements on the Windows PC that builds it:** Python 3.10-3.13
installed from python.org, with "Add python.exe to PATH" checked during
install.

**Steps:**

1. Open PowerShell and go to the project folder, e.g.:
   ```
   cd C:\Users\jzamo\OneDrive\Desktop\clary-albert-inversiones-app
   ```
2. Make sure you have the latest code: `git pull`
3. Double-click `build_exe.bat` in File Explorer (or run `.\build_exe.bat`
   from PowerShell). It installs the extra build-only packages listed in
   `requirements-desktop.txt` and then runs the PyInstaller build. This
   takes a few minutes.
4. When it finishes, look inside the new `dist\ClaryAlbertInversiones\`
   folder. It contains `ClaryAlbertInversiones.exe` plus supporting
   files it needs sitting right next to it.
5. To share it: right-click the `dist\ClaryAlbertInversiones` folder ->
   "Send to" -> "Compressed (zipped) folder", then share that .zip.
   Whoever receives it should extract the whole folder before running
   the .exe inside it -- the .exe will not work on its own, separated
   from its folder.

**Where its data is stored:** this desktop build always uses its own
local SQLite database at `%APPDATA%\ClaryAlbertInversiones\data.db` on
whichever Windows PC runs it. That file persists across restarts (it is
not deleted when the app closes), so it is safe to use for real personal
record-keeping on that PC. It is completely separate from the live web
app's data -- entries made in one will never appear in the other.

**First-run security warning:** since this .exe is not digitally signed,
Windows SmartScreen (or your antivirus) may show a warning like
"Windows protected your PC" the first time it runs. Click "More info"
then "Run anyway" to proceed -- this is expected for any unsigned
homemade .exe, not a sign of a real problem.

## Notes

- If you ever add a new report, create a new file inside `/pages`
  (e.g. `pages/4_NuevoReporte.py`) instead of adding code to `app.py`.
