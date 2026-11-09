# ==============================================================================
# Lanzador Nativo de HALCÓN AI para PowerShell en Windows
# ==============================================================================
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
Set-Location $scriptDir

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "              INICIANDO HALCÓN AI VOICE OS v5.2                  " -ForegroundColor Cyan
Write-Host "        Ing. Biomedica e IA - Sebastian Giraldo Acosta          " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = $null
if (Test-Path "$scriptDir\.venv\Scripts\python.exe") {
    $pythonCmd = "$scriptDir\.venv\Scripts\python.exe"
} elseif (Test-Path "$scriptDir\venv\Scripts\python.exe") {
    $pythonCmd = "$scriptDir\venv\Scripts\python.exe"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] No se encontro Python en tu sistema." -ForegroundColor Red
    Write-Host "Instala Python desde https://www.python.org/downloads/ marcando 'Add to PATH'." -ForegroundColor Yellow
    Exit 1
}

Write-Host "[*] Entorno detectado: $pythonCmd" -ForegroundColor Green
Write-Host "[*] Levantando HALCÓN con interfaz grafica Stark HUD..." -ForegroundColor Cyan
Write-Host ""

if ($args.Count -gt 0) {
    & $pythonCmd main.py @args
} else {
    & $pythonCmd main.py --hud
}
