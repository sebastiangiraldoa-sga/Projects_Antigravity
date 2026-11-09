#!/usr/bin/env bash
# ==============================================================================
# Lanzador de HALCÓN AI para Linux
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detectar entorno virtual
if [ -f "$SCRIPT_DIR/../.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/../.venv/bin/python3"
elif [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python3"
elif [ -f "$HOME/.venv/bin/python3" ]; then
    PYTHON="$HOME/.venv/bin/python3"
else
    PYTHON="python3"
fi

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
exec "$PYTHON" "$SCRIPT_DIR/main.py" "$@"
