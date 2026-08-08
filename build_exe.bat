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
if errorlevel 1 goto :pip_failed

python -m pip install -r requirements.txt
if errorlevel 1 goto :pip_failed

python -m pip install -r requirements-desktop.txt
if errorlevel 1 goto :pip_failed

echo.
echo Step 2 of 2: Building ClaryAlbertInversiones.exe (this can take a few minutes)...
echo.
streamlit-desktop-app build app.py --name "ClaryAlbertInversiones" --icon assets\app_icon.ico --pyinstaller-options --noconfirm --add-data "pages;pages" --add-data "assets;assets" --collect-all streamlit --copy-metadata streamlit
if errorlevel 1 goto :build_failed

if not exist "dist\ClaryAlbertInversiones\ClaryAlbertInversiones.exe" goto :build_failed

echo.
echo ============================================================
echo  DONE.
echo  Your app is in:  dist\ClaryAlbertInversiones\
echo  Zip that ENTIRE folder to share it or move it elsewhere.
echo  Double-click ClaryAlbertInversiones.exe inside it to run.
echo ============================================================
echo.
pause
goto :eof

:pip_failed
echo.
echo ============================================================
echo  SOMETHING WENT WRONG installing packages (see the red text
echo  above this box). The app was NOT built. Take a screenshot
echo  of this whole window and send it back for help.
echo ============================================================
echo.
pause
goto :eof

:build_failed
echo.
echo ============================================================
echo  SOMETHING WENT WRONG building the app (see the text above
echo  this box). The app was NOT built successfully. Take a
echo  screenshot of this whole window and send it back for help.
echo ============================================================
echo.
pause
goto :eof
