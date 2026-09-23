#!/bin/bash
# Lanceur Quarto Husson Studio macOS
cd "$(dirname "$0")"

# Vérification de streamlit dans anaconda
STREAMLIT_BIN="/opt/anaconda3/bin/streamlit"

if [ ! -f "$STREAMLIT_BIN" ]; then
    STREAMLIT_BIN=$(which streamlit)
fi

if [ -z "$STREAMLIT_BIN" ]; then
    echo "Erreur : Streamlit n'a pas été trouvé. Veuillez l'installer avec : pip install streamlit"
    read -p "Appuyez sur Entrée pour quitter..."
    exit 1
fi

echo "Lancement de Quarto Husson Studio..."
"$STREAMLIT_BIN" run app.py --server.headless false --server.runOnSave true --browser.gatherUsageStats false
