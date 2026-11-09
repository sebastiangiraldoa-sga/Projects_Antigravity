#!/usr/bin/env bash
# ==============================================================================
# Instalador de Acceso Directo de HALCÓN AI para Linux (GNOME / KDE / XFCE)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_PATH="$SCRIPT_DIR/ultron.ico"
RUNNER_PATH="$SCRIPT_DIR/iniciar_halcon.sh"

chmod +x "$RUNNER_PATH"

# 1. Determinar directorio de Escritorio (Desktop / Escritorio)
DESKTOP_DIR=""
if [ -n "$XDG_DESKTOP_DIR" ] && [ -d "$XDG_DESKTOP_DIR" ]; then
    DESKTOP_DIR="$XDG_DESKTOP_DIR"
elif command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi

if [ -z "$DESKTOP_DIR" ] || [ ! -d "$DESKTOP_DIR" ]; then
    if [ -d "$HOME/Desktop" ]; then
        DESKTOP_DIR="$HOME/Desktop"
    elif [ -d "$HOME/Escritorio" ]; then
        DESKTOP_DIR="$HOME/Escritorio"
    else
        DESKTOP_DIR="$HOME/Desktop"
        mkdir -p "$DESKTOP_DIR"
    fi
fi

SHORTCUT_FILE="$DESKTOP_DIR/HALCÓN AI.desktop"

# 2. Generar archivo .desktop
cat <<EOF > "$SHORTCUT_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=HALCÓN AI
GenericName=Asistente de Voz y Telemetría
Comment=Asistente Inteligente de Voz y Escritorio para Sebastián Giraldo Acosta
Exec="$RUNNER_PATH"
Icon=$ICON_PATH
Path=$SCRIPT_DIR
Terminal=true
Categories=Utility;Development;AudioVideo;
StartupNotify=true
Keywords=halcon;ultron;asistente;jarvis;ia;gemini;
EOF

chmod +x "$SHORTCUT_FILE"

# Confianza de escritorio en GNOME / Ubuntu / Debian si está disponible gio
if command -v gio >/dev/null 2>&1; then
    gio set "$SHORTCUT_FILE" metadata::trusted true 2>/dev/null || true
fi

# 3. También registrar en el menú de aplicaciones (~/.local/share/applications)
APP_MENU_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_MENU_DIR"
cp "$SHORTCUT_FILE" "$APP_MENU_DIR/halcon_ai.desktop"
chmod +x "$APP_MENU_DIR/halcon_ai.desktop"

echo "=================================================================="
echo " [OK] Acceso directo de HALCÓN AI instalado exitosamente:"
echo "   - Escritorio: $SHORTCUT_FILE"
echo "   - Menú de Aplicaciones: $APP_MENU_DIR/halcon_ai.desktop"
echo "=================================================================="
