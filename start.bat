@echo off
rem ============================================================================
rem  Time Tracker - one-click setup + launch for Windows
rem
rem  On a CLEAN machine this will:
rem    1. Find Python 3.9+ (installing it via winget if it is missing).
rem    2. Verify tkinter (the GUI toolkit) is available.
rem    3. Create an isolated virtual environment (.venv) and install the app
rem       into it -- only happens the first time.
rem    4. Launch the Time Tracker window.
rem
rem  Just double-click this file. Re-running it later skips straight to step 4.
rem ============================================================================
setlocal enabledelayedexpansion

rem Run from the folder this script lives in, whatever the current directory is.
cd /d "%~dp0"

echo ============================================
echo    Time Tracker - setup ^& launch
echo ============================================
echo.

rem --------------------------------------------------------------------------
rem 1. Locate a Python interpreter (prefer the "py" launcher, then "python").
rem --------------------------------------------------------------------------
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo Python was not found on this machine.
    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo winget is unavailable, so Python cannot be installed automatically.
        echo Please install Python 3.9 or newer from:
        echo     https://www.python.org/downloads/
        echo Tick "Add python.exe to PATH" during setup, then run start.bat again.
        echo.
        pause
        exit /b 1
    )
    echo Installing Python 3.12 via winget ^(this may take a few minutes^)...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    rem PATH often is not refreshed inside this same window, so re-detect.
    py -3 --version >nul 2>&1 && set "PY=py -3"
    if not defined PY (
        python --version >nul 2>&1 && set "PY=python"
    )
    if not defined PY (
        echo.
        echo Python was installed but is not visible in this window yet.
        echo Please CLOSE this window and run start.bat again.
        echo.
        pause
        exit /b 1
    )
)

echo Using Python:
%PY% --version
echo.

rem --------------------------------------------------------------------------
rem 2. Make sure tkinter is present (it ships with the standard installer).
rem --------------------------------------------------------------------------
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo This Python install is missing tkinter, which the app needs for its UI.
    echo Re-install Python from https://www.python.org/downloads/ and keep the
    echo "tcl/tk and IDLE" component selected during setup, then run this again.
    echo.
    pause
    exit /b 1
)

rem --------------------------------------------------------------------------
rem 3. First-run setup: create the virtual environment and install the app.
rem --------------------------------------------------------------------------
set "VENV_PY=.venv\Scripts\python.exe"
set "VENV_PYW=.venv\Scripts\pythonw.exe"

if not exist "%VENV_PY%" (
    echo First run - creating virtual environment ^(.venv^)...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
    echo Installing Time Tracker into the environment...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 (
        echo Failed to install the application.
        pause
        exit /b 1
    )
    echo Setup complete.
    echo.
)

rem If the venv exists but points at a missing base Python, recreate it.
"%VENV_PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo Existing virtual environment is broken - recreating it...
    rmdir /s /q .venv
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Failed to recreate the virtual environment.
        pause
        exit /b 1
    )
    echo Reinstalling Time Tracker into the repaired environment...
    "%VENV_PY%" -m pip install --upgrade pip >nul
    "%VENV_PY%" -m pip install -e .
    if errorlevel 1 (
        echo Failed to reinstall the application.
        pause
        exit /b 1
    )
    echo Repair complete.
    echo.
)

rem --------------------------------------------------------------------------
rem 4. Launch the GUI (pythonw = no lingering console window) and detach.
rem --------------------------------------------------------------------------
echo Starting Time Tracker...
start "Time Tracker" "%VENV_PYW%" -m timetracker

endlocal
exit /b 0
