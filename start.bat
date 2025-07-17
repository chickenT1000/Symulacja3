@echo off
SETLOCAL EnableDelayedExpansion

echo ===================================================
echo   H2SO4-CaCO3 Process Simulation Setup
echo ===================================================

REM Check if Python is installed
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Python is not installed or not in PATH
  echo Please install Python 3.9+ and try again
  pause
  exit /b 1
)

REM Create virtual environment if it doesn't exist
IF NOT EXIST venv (
  echo Creating virtual environment...
  python -m venv venv
  IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
  )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Failed to activate virtual environment
  pause
  exit /b 1
)

REM Install dependencies
echo Installing/updating dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Failed to install dependencies
  pause
  exit /b 1
)

REM Start Flask server and wait briefly for it to initialize
echo Starting Flask server on port 8080...
start /B "" python app.py
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Failed to start Flask server
  pause
  exit /b 1
)

REM Wait for server to initialize
timeout /t 2 /nobreak >nul

REM Open browser
echo Opening browser...
start "" http://localhost:8080

echo.
echo Server is running. Press Ctrl+C in this window to stop.
echo If the page doesn't load, try refreshing after a few seconds.
echo.

REM Keep the window open
cmd /k
