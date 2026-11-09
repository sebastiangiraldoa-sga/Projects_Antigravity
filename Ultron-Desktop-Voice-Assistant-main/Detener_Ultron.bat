@echo off
chcp 65001 >nul
title Detener Ultrón AI
cd /d "%~dp0"

echo ====================================================================
echo                 DETENIENDO ULTRÓN AI ASSISTANT
echo ====================================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[OK] Proceso Ultrón detenido (PID ' + $_.ProcessId + ')') -ForegroundColor Green }"

echo.
echo Ultrón ha sido detenido correctamente.
timeout /t 2 >nul
