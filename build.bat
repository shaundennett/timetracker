@echo off
rem ============================================================================
rem  Build a single distributable Time Tracker executable (Windows).
rem
rem  Produces dist\TimeTracker.exe — one self-contained file that bundles
rem  Python, tkinter, and fpdf2. The recipient just double-clicks it; no
rem  Python installation is required on their machine.
rem
rem  Run start.bat once first (it creates the .venv this build uses).
rem ============================================================================
setlocal
cd /d "%~dp0"

set "PYW=.venv\Scripts\python.exe"
if not exist "%PYW%" (
    echo Virtual environment not found. Run start.bat once first to create it.
    pause
    exit /b 1
)

echo Installing build tooling ^(PyInstaller^)...
"%PYW%" -m pip install --upgrade pip >nul
"%PYW%" -m pip install -e ".[build]"
if errorlevel 1 (
    echo Failed to install build dependencies.
    pause
    exit /b 1
)

echo.
echo Building single-file executable...
"%PYW%" -m PyInstaller --noconfirm --clean ^
    --onefile --windowed --name TimeTracker ^
    --collect-all fpdf ^
    run_app.py
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done. Distributable file:
echo     %CD%\dist\TimeTracker.exe
echo ============================================================
pause
