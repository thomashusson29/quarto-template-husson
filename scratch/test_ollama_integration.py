#!/usr/bin/env python3
"""
Test automatisé de l'intégration Ollama dans Quarto Husson Studio (gui/app.py).
"""

import sys
from pathlib import Path

REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
sys.path.insert(0, str(REPO_PATH))

from gui.app import get_ollama_models, extract_error_snippet, stream_ollama_response
from streamlit.testing.v1 import AppTest

def test_ollama_helpers():
    print("1. Test de get_ollama_models()...")
    models = get_ollama_models()
    assert len(models) > 0, "Aucun modele Ollama detecte alors que le serveur est actif."
    print(f"   -> Modeles detectes ({len(models)}) : {', '.join(models)}")

    print("2. Test de extract_error_snippet()...")
    mock_log = [
        "rendering pdf...",
        "running xelatex - 1",
        "loading fontspec",
        "! Package babel Error: Conflicting language options: french.",
        "See the babel package documentation for explanation.",
        "Type  H <return>  for immediate help.",
        " ... ",
        "l.45 \\begin{document}",
        "Emergency stop.",
        "compilation failed"
    ]
    snip = extract_error_snippet(mock_log)
    assert "babel Error" in snip, "Le snippet devrait contenir l'erreur babel."
    print(f"   -> Snippet extrait correctement ({len(snip.splitlines())} lignes).")

    print("3. Test de stream_ollama_response()...")
    chosen_model = "qwen2.5-coder:latest" if "qwen2.5-coder:latest" in models else models[0]
    prompt = "Tu es un expert Quarto. Reponds en un seul mot : FONCTIONNEL"
    tokens = list(stream_ollama_response(chosen_model, prompt))
    full_text = "".join(tokens).strip()
    assert len(full_text) > 0, "Aucune reponse reçue de Ollama."
    print(f"   -> Reponse reçue du modele {chosen_model} : '{full_text[:40]}'")

def test_ollama_gui_workflow():
    print("4. Test de l'interface Streamlit avec l'onglet Assistant Ollama...")
    test_qmd = REPO_PATH / "scratch" / "test_gui_comprehensive.qmd"
    at = AppTest.from_file("gui/app.py", default_timeout=25)
    at.run()
    assert not at.exception, f"Exception au demarrage : {at.exception}"

    # Charger le document
    path_input = [t for t in at.text_input if "direct" in t.label.lower()][0]
    path_input.set_value(str(test_qmd))
    at.run()
    assert not at.exception, f"Exception apres chargement fichier : {at.exception}"

    # Verifier la presence du selectbox tab_ollama_model
    select_models = [s for s in at.selectbox if s.key == "tab_ollama_model"]
    assert len(select_models) > 0, "Le selecteur de modele Ollama dans l'onglet devrait exister."
    print(f"   -> Selecteur Ollama actif avec valeur par defaut : {select_models[0].value}")

    # Cliquer sur 'Analyser la syntaxe YAML'
    btn_check = [b for b in at.button if b.key == "btn_check_doc_yaml"][0]
    btn_check.click()
    at.run()
    assert not at.exception, f"Exception lors de l'analyse YAML par Ollama : {at.exception}"
    print("   -> Analyse de syntaxe YAML executee sans erreur Streamlit.")

    print("5. Test de la resolution d'erreur lors d'une compilation echouee...")
    # Injecter un etat de compilation simule echouee dans la session
    at.session_state["last_compilation"] = {
        "target_path": str(test_qmd),
        "cmd": ["quarto", "render", str(test_qmd), "--to", "pdf"],
        "return_code": 1,
        "terminal_lines": [
            "! LaTeX Error: File 'nonexistent_package.sty' not found.",
            "Type X to quit or <RETURN> to proceed",
            "compilation failed with exit code 1"
        ],
        "yaml_str": "title: Test\nformat: pdf\n",
        "elapsed_str": "1.2s"
    }
    at.run()
    assert not at.exception, f"Exception lors du rendu de l'etat d'erreur : {at.exception}"

    # Verifier que la section Ollama de diagnostic apparait
    btn_diag = [b for b in at.button if b.key == "btn_run_ollama_diagnosis"]
    assert len(btn_diag) > 0, "Le bouton de diagnostic Ollama doit apparaitre en cas d'erreur de compilation."
    print("   -> Bouton 'Analyser l'erreur et proposer une correction' present.")

    # Declencher le diagnostic Ollama
    btn_diag[0].click()
    at.run()
    assert not at.exception, f"Exception lors du diagnostic Ollama : {at.exception}"
    assert "last_diagnosis" in at.session_state, "Le diagnostic doit etre enregistre dans session_state."
    diag_text = at.session_state["last_diagnosis"]
    assert len(diag_text) > 0, "Le texte du diagnostic ne doit pas etre vide."
    print(f"   -> Diagnostic genere par Ollama ({len(diag_text)} caracteres) :\n")
    print("--- DEBUT DIAGNOSTIC OLLAMA ---")
    print(diag_text[:400] + ("..." if len(diag_text) > 400 else ""))
    print("--- FIN DIAGNOSTIC OLLAMA ---\n")

    print("Tous les tests d'integration Ollama ont REUSSI avec succes.")

if __name__ == "__main__":
    test_ollama_helpers()
    test_ollama_gui_workflow()
