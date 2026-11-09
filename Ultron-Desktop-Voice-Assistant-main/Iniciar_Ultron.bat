@echo off
setlocal
chcp 65001 >nul
title ULTRÓN AI Assistant — Stark Voice OS
cd /d "%~dp0"

echo ====================================================================
echo               INICIANDO ULTRON AI VOICE OS v5.2
echo           Ing. Biomedica & IA: Sebastian Giraldo Acosta
echo ====================================================================
echo.

:: 1. Verificar si existe entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    echo [*] Detectado entorno virtual (.venv)
    set "RUN_CMD="%~dp0.venv\Scripts\python.exe""
    goto :check_deps
)
if exist "%~dp0venv\Scripts\python.exe" (
    echo [*] Detectado entorno virtual (venv)
    set "RUN_CMD="%~dp0venv\Scripts\python.exe""
    goto :check_deps
)

:: 2. Verificar lanzador py de Windows
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Detectado lanzador Python (py -3)
    set "RUN_CMD=py -3"
    goto :check_deps
)

:: 3. Verificar python en PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Detectado Python en PATH
    set "RUN_CMD=python"
    goto :check_deps
)

:: Si llego aqui, no se encontro Python
echo.
echo ====================================================================
echo [ERROR] No se encontro Python en tu sistema ni en .venv/venv.
echo.
echo Para solucionarlo:
echo  1. Instala Python 3.10 o superior desde https://www.python.org/downloads/
echo  2. Asegurate de marcar la casilla: 'Add python.exe to PATH'
echo ====================================================================
echo.
pause
exit /b 1

:check_deps
:: Verificar si falta la libreria requests u otras basicas en el entorno
%RUN_CMD% -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [*] Detectamos que faltan librerias en este entorno de Python.
    echo [*] Instalando dependencias automaticamente desde requirements.txt...
    echo     (Esto solo se hace una vez, por favor espera un momento...)
    echo.
    %RUN_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Fallo la instalacion automatica de librerias.
        echo Por favor ejecuta manualmente en tu terminal:
        echo     pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencias instaladas con exito.
    echo.
)

:run
if "%~1"=="" (
    set "ARGS=--hud"
) else (
    set "ARGS=%*"
)

echo [*] Ejecutando: %RUN_CMD% main.py %ARGS%
echo.

%RUN_CMD% main.py %ARGS%

if %errorlevel% neq 0 (
    echo.
    echo ====================================================================
    echo [!] Ultrón finalizo con codigo de salida %errorlevel%.
    echo Si falta alguna libreria, ejecuta en tu terminal:
    echo     pip install -r requirements.txt
    echo ====================================================================
    echo.
    pause
)
