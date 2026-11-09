@echo off
chcp 65001 >nul
title Instalador de Acceso Directo — Ultrón AI
cd /d "%~dp0"

echo ====================================================================
echo        INSTALADOR DE ACCESO DIRECTO PARA ULTRÓN AI EN WINDOWS
echo ====================================================================
echo.
echo Creando los accesos directos en tu Escritorio de Windows...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\crear_acceso_directo.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al ejecutar el script de PowerShell.
    echo Codigo de error: %errorlevel%
    echo.
)

pause
