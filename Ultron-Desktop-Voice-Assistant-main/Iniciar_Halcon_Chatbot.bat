@echo off
setlocal
chcp 65001 >nul
title HALCÓN AI — Modo Chatbot (Reuniones / Spotify)
cd /d "%~dp0"

echo ====================================================================
echo             INICIANDO HALCÓN AI — MODO CHATBOT
echo     (Microfono liberado y voz silenciada para reuniones y musica)
echo         Ing. Biomedica e IA - Sebastian Giraldo Acosta
echo ====================================================================
echo.

:: 1. Verificar si existe entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    set RUN_CMD="%~dp0.venv\Scripts\python.exe"
    goto :run
)
if exist "%~dp0venv\Scripts\python.exe" (
    set RUN_CMD="%~dp0venv\Scripts\python.exe"
    goto :run
)

:: 2. Verificar py de Windows
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set RUN_CMD=py -3
    goto :run
)

:: 3. Verificar python en PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set RUN_CMD=python
    goto :run
)

set RUN_CMD=python

:run
echo [*] Iniciando HALCÓN en Modo Chatbot...
%RUN_CMD% main.py --hud --chatbot %*

if errorlevel 1 (
    echo.
    echo [!] HALCÓN finalizo con codigo de error %errorlevel%.
    pause
)
