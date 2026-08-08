@echo off
REM ============================================================
REM  Builds a standalone Windows desktop app (.exe) from this
REM  Streamlit project. Run this by double-clicking it from
REM  inside the project folder (the same folder as app.py).
REM
REM  What you get: a folder named
REM     dist\ClaryAlbertInversiones\
REM  containing ClaryAlbertInversiones.exe plus the files it
REM  needs next to it. Zip that WHOLE folder to share it -- the
REM  .exe will not work if separated from the rest of the folder.
REM
REM  This exe uses its OWN local database (separate from the
REM  online/live app), stored at:
REM     %%APPDATA%%\ClaryAlbertInversiones\data.db
REM  Data you enter there stays on that PC and is never lost
REM  between runs, but it will NOT show up on the live web app,
REM  and vice versa -- they are two separate copies of the app.
REM ============================================================

echo.
echo Step 1 of 2: Installing required packages (this can take a few minutes)...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-desktop.txt

echo.
echo Step 2 of 2: Building ClaryAlbertInversiones.exe (this can take a few minutes)...
echo.
streamlit-desktop-app build app.py --name "ClaryAlbertInversiones" --icon assets\app_icon.ico --pyinstaller-options --noconfirm --add-data "pages;pages" --add-data "assets;assets" --collect-all streamlit --copy-metadata streamlit

echo.
echo ============================================================
echo  DONE.
echo  Your app is in:  dist\ClaryAlbertInversiones\
echo  Zip that ENTIRE folder to share it or move it elsewhere.
echo  Double-click ClaryAlbertInversiones.exe inside it to run.
echo ============================================================
echo.
pause
