@echo off
cd /d %~dp0
set "PY=.venv\Scripts\python.exe"

echo =============================================
echo   Inicio bot + consola libre
echo =============================================

if not exist "%PY%" (
    echo ERROR: No existe .venv. Ejecuta instalar.bat primero.
    pause
    exit /b 1
)

"%PY%" -c "import twitchio, dotenv, aiohttp, whisper" >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Faltan dependencias.
    echo Ejecuta primero instalar.bat
    pause
    exit /b 1
)

echo Iniciando bot en otra ventana...
start "Bot Twitch" cmd /k "cd /d %~dp0 && %PY% bot.py"

echo.
echo El bot se esta ejecutando en otra ventana.
echo Este CMD queda libre para tus comandos.
echo.
cmd /k
