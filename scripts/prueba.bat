@echo off
chcp 65001 >nul
title Prueba local del bot (sin Twitch)
echo.
echo  Iniciando prueba local...
echo  Asegurate de que Ollama este corriendo antes de continuar.
echo.
C:\Python\Python310\python.exe "%~dp0prueba.py"
echo.
pause
