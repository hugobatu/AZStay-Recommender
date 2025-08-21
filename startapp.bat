@echo off
SETLOCAL
SET VENV_DIR=venv

echo [+] === Setting up Recommender Services ===

REM Create virtual environment if not exists
IF EXIST %VENV_DIR%\Scripts\activate.bat (
  echo [+] Virtual environment exists.
) ELSE (
  echo [+] Creating virtual environment...
  python -m venv %VENV_DIR%
  IF %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

REM Activate virtual environment
call %VENV_DIR%\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
  echo [!] Failed to activate virtual environment.
  pause
  exit /b 1
)

echo [+] Upgrading pip...
pip install --upgrade pip

echo [+] Installing Python dependencies...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
  echo [!] Failed to install Python dependencies.
  pause
  exit /b 1
)

echo [+] === Start app ===
uvicorn app.main:app --reload --port 10000

echo [+] App setup finished and run successfully.
pause
ENDLOCAL
