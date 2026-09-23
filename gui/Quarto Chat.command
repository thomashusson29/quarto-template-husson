#!/bin/bash
# Lanceur Quarto Husson Terminal Chat (macOS)
cd "$(dirname "$0")"

PYTHON_BIN="/opt/anaconda3/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(which python3)
fi

"$PYTHON_BIN" chat.py "$@"
