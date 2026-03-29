@echo off
cd /d %~dp0

python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python no encontrado en PATH.
    pause
    exit /b 1
)

python -c "import twitchio, dotenv, aiohttp" >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Faltan dependencias.
    echo Ejecuta primero instalar.bat
    pause
    exit /b 1
)

python probar_twitch_cmd.py
pause
