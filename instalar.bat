@echo off
echo ============================================
echo  Instalador - Bot de Twitch + Ollama
echo ============================================
echo.

py --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python no encontrado.
    echo Descargalo en https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual .venv...
    py -m venv .venv
) else (
    echo [1/3] Entorno virtual .venv detectado.
)

echo [2/3] Instalando dependencias Python...
.venv\Scripts\python.exe -m pip install -r requirements.txt openai-whisper

echo.
echo [3/3] Listo.
echo.
echo Pasos siguientes:
echo  1. Edita config.env con tus datos de Twitch
echo  2. Asegurate de tener Ollama corriendo (ollama serve)
echo  3. Ejecuta el bot con: iniciar.bat
echo.
pause
