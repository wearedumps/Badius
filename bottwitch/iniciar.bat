@echo off
cd /d %~dp0

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo ERROR: No existe .venv. Ejecuta instalar.bat primero.
    pause
    exit /b 1
)

"%PY%" --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python de .venv no disponible.
    pause
    exit /b 1
)

"%PY%" -c "import twitchio, requests, dotenv, aiohttp, whisper" >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Faltan dependencias.
    echo Ejecuta primero instalar.bat
    pause
    exit /b 1
)

"%PY%" bot.py
pause