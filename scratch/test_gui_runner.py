#!/usr/bin/env python3
"""
Test de validation complete de l'application Quarto Husson Studio (gui/app.py)
avec un document Quarto (.qmd).
"""

import os
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, "/Users/thomashusson/Documents/Projets/quarto-template-husson")
from streamlit.testing.v1 import AppTest
from gui.app import find_output_file

def run_gui_test():
    test_qmd = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson/scratch/test_gui_comprehensive.qmd")
    assert test_qmd.exists(), f"Fichier de test introuvable : {test_qmd}"

    print(f"1. Lancement de l'application Streamlit avec {test_qmd.name}...")
    at = AppTest.from_file("gui/app.py", default_timeout=20)
    at.run()
    assert not at.exception, f"Exceptions au demarrage : {at.exception}"

    print("2. Definition du fichier cible dans l'interface...")
    # Saisir le chemin direct dans le text_input
    path_input = [t for t in at.text_input if "direct" in t.label.lower()][0]
    path_input.set_value(str(test_qmd))
    at.run()
    assert not at.exception, f"Exceptions apres saisie chemin : {at.exception}"

    # Verifier que le document est actif
    active_docs = [m.value for m in at.markdown if "Document actif" in m.value]
    assert len(active_docs) > 0, "Le document n'a pas ete detecte comme actif."
    print(f"   -> {active_docs[0]}")

    print("3. Application du profil 'Devoir / Rapport de Master'...")
    # Trouver le bouton du profil devoir
    btn_devoir = at.button(key="prof_devoir")
    btn_devoir.click()
    at.run()
    assert not at.exception, f"Exceptions apres application du profil : {at.exception}"

    # Verifier les options du profil
    assert at.session_state["opt_thesis_active"] is True, "Le mode page de garde devrait etre actif."
    assert at.session_state["sel_font"] == "Computer Modern (Latex Default)", "La police devrait etre Computer Modern."
    assert at.session_state["opt_pdf"] is True, "Le format PDF devrait etre coche."
    print("   -> Profil applique avec succes : Page de garde activee, Computer Modern selectionnee.")

    print("4. Enregistrement des parametres dans le document .qmd...")
    btn_save = [b for b in at.button if "Enregistrer" in b.label][0]
    btn_save.click()
    at.run()
    assert not at.exception, f"Exceptions apres enregistrement : {at.exception}"

    # Verifier les messages de succes
    success_msgs = [s.value for s in at.success]
    print(f"   -> Message Streamlit : {success_msgs[-1] if success_msgs else 'Aucun'}")

    # Verifier le contenu du fichier .qmd sur le disque
    content = test_qmd.read_text(encoding="utf-8")
    assert "thesis:" in content, "La section thesis doit etre presente dans le YAML."
    assert "Université Paris-Saclay" in content, "L'universite Paris-Saclay doit etre presente."
    assert "before-body.tex" in content, "before-body.tex doit etre dans template-partials."
    assert "typography.lua" in content, "typography.lua doit etre dans filters."
    assert "pdf-header.tex" in content, "pdf-header.tex doit etre dans include-in-header."
    print("   -> YAML du document mis a jour avec succes et structure complete validee.")

    print("5. Test de compilation (quarto render) avec le template Husson...")
    cmd = ["/Applications/quarto/bin/quarto", "render", str(test_qmd), "--to", "pdf"]
    res = subprocess.run(
        cmd,
        cwd=str(test_qmd.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f"   -> Code de retour : {res.returncode}")
    if res.returncode != 0:
        print("Journal d'erreur :\n", res.stdout[-2000:])
        sys.exit(1)

    pdf_out = find_output_file(test_qmd, ".pdf")
    assert pdf_out.exists(), f"Le fichier PDF {pdf_out} n'a pas ete genere."
    pdf_size = pdf_out.stat().st_size
    print(f"   -> PDF genere avec succes : {pdf_out.name} ({pdf_size:,} octets a l'emplacement {pdf_out}).")

    # Verifier le nombre de pages du PDF avec pdfinfo si disponible
    try:
        info_res = subprocess.run(["pdfinfo", str(pdf_out)], stdout=subprocess.PIPE, text=True)
        if info_res.returncode == 0:
            for line in info_res.stdout.splitlines():
                if "Pages:" in line or "Title:" in line:
                    print(f"      {line.strip()}")
    except Exception:
        pass

    print("6. Test d'un second profil : 'Article / Rapport Web' (PDF + HTML synchronises)...")
    btn_article = at.button(key="prof_article")
    btn_article.click()
    at.run()
    assert not at.exception, f"Exceptions apres profil article : {at.exception}"
    assert at.session_state["opt_pdf"] is True
    assert at.session_state["opt_html"] is True
    assert at.session_state["opt_thesis_active"] is False
    print("   -> Profil Article applique : PDF + HTML actifs, page de garde desactivee.")

    btn_save = [b for b in at.button if "Enregistrer" in b.label][0]
    btn_save.click()
    at.run()

    # Rendu HTML
    cmd_html = ["/Applications/quarto/bin/quarto", "render", str(test_qmd), "--to", "html"]
    res_html = subprocess.run(
        cmd_html,
        cwd=str(test_qmd.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    assert res_html.returncode == 0, f"Echec du rendu HTML : {res_html.stdout[-1000:]}"
    html_out = find_output_file(test_qmd, ".html")
    assert html_out.exists(), "Le fichier HTML n'a pas ete genere."
    print(f"   -> HTML genere avec succes : {html_out.name} ({html_out.stat().st_size:,} octets a l'emplacement {html_out}).")

    print("\nTous les tests de l'application graphique avec le document Quarto ont REUSSI avec succes.")

if __name__ == "__main__":
    run_gui_test()
