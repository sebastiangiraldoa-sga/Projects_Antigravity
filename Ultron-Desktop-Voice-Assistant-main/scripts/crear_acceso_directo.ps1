# ==============================================================================
# Script de Creacion de Acceso Directo de Ultron AI para Windows 11 / 10
# Ingenieria Biomedica & Especializacion en IA - Sebastian Giraldo Acosta
# ==============================================================================

$ErrorActionPreference = "Continue"

# Determinar la raiz del proyecto de forma dinamica
$scriptDir = $PSScriptRoot
if (-not $scriptDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

# 1. Obtener la ruta del Escritorio de Windows (compatible con OneDrive y todas las versiones de PS)
$desktopPath = $null
try {
    $desktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
} catch {
    $desktopPath = $null
}

if (-not $desktopPath -or -not (Test-Path $desktopPath)) {
    try {
        $desktopPath = [System.Environment]::GetFolderPath("Desktop")
    } catch {
        $desktopPath = $null
    }
}

if (-not $desktopPath -or -not (Test-Path $desktopPath)) {
    try {
        $wshTemp = New-Object -ComObject WScript.Shell
        $desktopPath = $wshTemp.SpecialFolders.Item("Desktop")
    } catch {
        $desktopPath = $null
    }
}

if (-not $desktopPath -or -not (Test-Path $desktopPath)) {
    $desktopPath = Join-Path $env:USERPROFILE "Desktop"
}

$iconPath = Join-Path $projectRoot "ultron.ico"
$vbsPath  = Join-Path $projectRoot "Iniciar_Ultron_Silencioso.vbs"
$batPath  = Join-Path $projectRoot "Iniciar_Ultron.bat"
$wscriptExe = Join-Path $env:SystemRoot "System32\wscript.exe"

$wshShell = New-Object -ComObject WScript.Shell

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   CONFIGURANDO ACCESOS DIRECTOS DE ULTRON AI EN TU ESCRITORIO   " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "[*] Raiz del proyecto: $projectRoot" -ForegroundColor DarkGray
Write-Host "[*] Carpeta Escritorio: $desktopPath" -ForegroundColor DarkGray

# Limpiar posibles accesos directos viejos o con caracteres especiales (mojibake)
$oldNames = @(
    "Ultrón AI.lnk",
    "UltrÃ³n AI.lnk",
    "Ultrón AI (Consola).lnk",
    "UltrÃ³n AI (Consola).lnk",
    "Ultron AI.lnk",
    "Ultron AI (Consola).lnk"
)
foreach ($old in $oldNames) {
    $oldFile = Join-Path $desktopPath $old
    if (Test-Path $oldFile) {
        Remove-Item -Path $oldFile -Force -ErrorAction SilentlyContinue
    }
}

# 1. Crear Acceso Directo Principal: Ultron AI (Modo App Stark HUD)
try {
    $mainShortcutPath = Join-Path $desktopPath "Ultron AI.lnk"
    $mainShortcut = $wshShell.CreateShortcut($mainShortcutPath)
    $mainShortcut.TargetPath = $wscriptExe
    $mainShortcut.Arguments = "`"$vbsPath`""
    $mainShortcut.WorkingDirectory = $projectRoot
    $mainShortcut.Description = "Ultron AI Voice OS & Asistente Jarvis - Sebastian Giraldo"
    if (Test-Path $iconPath) {
        $mainShortcut.IconLocation = "$iconPath,0"
    }
    $mainShortcut.Hotkey = "Ctrl+Alt+U"
    $mainShortcut.Save()
    Write-Host "[OK] Creado: Ultron AI.lnk (Modo App Silencioso)" -ForegroundColor Green
    Write-Host "     -> Atajo global asignado: Ctrl + Alt + U" -ForegroundColor Yellow
} catch {
    Write-Host "[!] Error creando acceso directo silencioso: $_" -ForegroundColor Red
}

# 2. Crear Acceso Directo de Depuracion: Ultron AI (Consola)
try {
    $debugShortcutPath = Join-Path $desktopPath "Ultron AI (Consola).lnk"
    $debugShortcut = $wshShell.CreateShortcut($debugShortcutPath)
    $debugShortcut.TargetPath = $batPath
    $debugShortcut.WorkingDirectory = $projectRoot
    $debugShortcut.Description = "Ultron AI Voice OS (Modo Consola con Logs)"
    if (Test-Path $iconPath) {
        $debugShortcut.IconLocation = "$iconPath,0"
    }
    $debugShortcut.Save()
    Write-Host "[OK] Creado: Ultron AI (Consola).lnk (Modo con Terminal)" -ForegroundColor Green
} catch {
    Write-Host "[!] Error creando acceso directo de consola: $_" -ForegroundColor Red
}

# 3. Registrar en el Menu Inicio de Windows (Para que aparezca al presionar tecla Windows y buscar 'Ultron')
try {
    $programsPath = $null
    try {
        $programsPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
    } catch {
        $programsPath = $null
    }
    if (-not $programsPath -or -not (Test-Path $programsPath)) {
        try {
            $programsPath = $wshShell.SpecialFolders.Item("Programs")
        } catch {
            $programsPath = $null
        }
    }
    if (-not $programsPath -or -not (Test-Path $programsPath)) {
        $programsPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    }

    if (Test-Path $programsPath) {
        foreach ($old in $oldNames) {
            $oldStartFile = Join-Path $programsPath $old
            if (Test-Path $oldStartFile) {
                Remove-Item -Path $oldStartFile -Force -ErrorAction SilentlyContinue
            }
        }

        $startMenuShortcutPath = Join-Path $programsPath "Ultron AI.lnk"
        $startShortcut = $wshShell.CreateShortcut($startMenuShortcutPath)
        $startShortcut.TargetPath = $wscriptExe
        $startShortcut.Arguments = "`"$vbsPath`""
        $startShortcut.WorkingDirectory = $projectRoot
        $startShortcut.Description = "Ultron AI Voice OS & Asistente Jarvis - Sebastian Giraldo"
        if (Test-Path $iconPath) {
            $startShortcut.IconLocation = "$iconPath,0"
        }
        $startShortcut.Save()
        Write-Host "[OK] Integrado en Menu Inicio: Ahora puedes buscar 'Ultron' en Windows" -ForegroundColor Green
    }
} catch {
    Write-Host "[!] No se pudo registrar en Menu Inicio (opcional): $_" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [OK] Ultron ahora esta integrado en tu sistema Windows 11:       " -ForegroundColor Green
Write-Host "   - 1 Clic en tu Escritorio (Ultron AI)" -ForegroundColor White
Write-Host "   - Busqueda de Windows (Tecla Win + 'Ultron')" -ForegroundColor White
Write-Host "   - Atajo de teclado global: Ctrl + Alt + U" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
