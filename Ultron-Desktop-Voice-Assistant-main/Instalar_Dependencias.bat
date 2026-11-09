@echo off
setlocal
chcp 65001 >nul
title Instalador de Dependencias — Ultrón AI
cd /d "%~dp0"

echo ====================================================================
echo        INSTALADOR DE DEPENDENCIAS PARA ULTRÓN AI (WINDOWS)
echo ====================================================================
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    echo [*] Detectado entorno virtual (.venv)
    set "RUN_CMD="%~dp0.venv\Scripts\python.exe""
) else if exist "%~dp0venv\Scripts\python.exe" (
    echo [*] Detectado entorno virtual (venv)
    set "RUN_CMD="%~dp0venv\Scripts\python.exe""
) else (
    echo [*] Usando Python del sistema
    set "RUN_CMD=python"
)

echo [*] Instalando librerias desde requirements.txt...
echo.
%RUN_CMD% -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ====================================================================
    echo [OK] Todas las librerias se instalaron correctamente.
    echo Ahora ya puedes abrir Iniciar_Ultron.bat o el acceso directo.
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo [ERROR] Hubo un problema al instalar las dependencias.
    echo Revisa tu conexion a Internet o intenta ejecutar en tu terminal:
    echo     pip install -r requirements.txt
    echo ====================================================================
)

echo.
pause
