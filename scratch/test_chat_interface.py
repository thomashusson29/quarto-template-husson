#!/usr/bin/env python3
"""
Test de l'interface chat multi-tours avec Ollama dans Quarto Husson Studio.
"""

import sys
from pathlib import Path

REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
sys.path.insert(0, str(REPO_PATH))

from streamlit.testing.v1 import AppTest

def test_multi_turn_chat():
    test_qmd = REPO_PATH / "scratch" / "test_gui_comprehensive.qmd"
    print("1. Initialisation de l'AppTest avec app.py...")
    at = AppTest.from_file("gui/app.py", default_timeout=40)
    at.run()
    assert not at.exception, f"Exception au demarrage : {at.exception}"

    # Charger le document
    path_input = [t for t in at.text_input if "direct" in t.label.lower()][0]
    path_input.set_value(str(test_qmd))
    at.run()
    assert not at.exception, f"Exception apres selection fichier : {at.exception}"

    # Verifier la presence de st.chat_input
    assert len(at.chat_input) > 0, "Le widget st.chat_input devrait etre present dans l'interface."
    chat_input = at.chat_input[0]
    print(f"   -> Widget chat_input detecte (placeholder: '{chat_input.placeholder}')")

    print("2. Envoi de la premiere question dans le chat...")
    q1 = "Comment creer un tableau avec reference croisee dans Quarto ?"
    chat_input.set_value(q1)
    at.run()
    assert not at.exception, f"Exception apres la premiere question : {at.exception}"

    assert "chat_messages" in at.session_state, "chat_messages doit exister dans session_state."
    msgs = at.session_state["chat_messages"]
    assert len(msgs) == 2, f"Attendu 2 messages (user + assistant), obtenu {len(msgs)}"
    assert msgs[0]["role"] == "user" and msgs[0]["content"] == q1
    assert msgs[1]["role"] == "assistant" and len(msgs[1]["content"]) > 0
    print(f"   -> Reponse 1 reçue ({len(msgs[1]['content'])} caracteres) :\n      '{msgs[1]['content'][:120]}...'")

    print("3. Envoi d'une deuxieme question pour tester la memoire multi-tours...")
    q2 = "Et comment fait-on pour que ce soit appele Tableau au lieu de Table ?"
    # Re-recuperer le chat_input mis a jour
    chat_input = at.chat_input[0]
    chat_input.set_value(q2)
    at.run()
    assert not at.exception, f"Exception apres la deuxieme question : {at.exception}"

    msgs2 = at.session_state["chat_messages"]
    assert len(msgs2) == 4, f"Attendu 4 messages dans l'historique, obtenu {len(msgs2)}"
    assert msgs2[2]["role"] == "user" and msgs2[2]["content"] == q2
    assert msgs2[3]["role"] == "assistant" and len(msgs2[3]["content"]) > 0
    print(f"   -> Reponse 2 reçue avec contexte ({len(msgs2[3]['content'])} caracteres) :\n      '{msgs2[3]['content'][:120]}...'")

    print("4. Test du bouton 'Effacer l'historique'...")
    btn_clear = [b for b in at.button if b.key == "btn_clear_chat"][0]
    btn_clear.click()
    at.run()
    assert not at.exception, f"Exception apres effacement : {at.exception}"
    assert len(at.session_state["chat_messages"]) == 0, "L'historique devrait etre vide apres reset."
    print("   -> Historique efface avec succes (0 message restant).")

    print("\nLe test complet de l'interface conversationnelle multi-tours a REUSSI.")

if __name__ == "__main__":
    test_multi_turn_chat()
