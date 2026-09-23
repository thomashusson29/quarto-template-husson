#!/usr/bin/env python3
"""
Test d'integration complet pour Quarto Husson Studio :
1. Verification de l'auto-configuration transparente d'un QMD brut.
2. Verification du deploiement autonome des fichiers environnementaux (extensions, logos, fonts, _quarto.yml).
3. Verification de la preservation totale des metadonnees (jury, laboratory, etc.).
4. Test de l'application Streamlit sans exception via AppTest.
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
sys.path.insert(0, str(REPO_PATH))

from gui.app import (
    ensure_complete_project_environment,
    check_husson_readiness,
    auto_configure_husson_document,
    parse_qmd,
    yaml_parser
)
from streamlit.testing.v1 import AppTest


def test_auto_deployment_and_configuration():
    print("--- Test 1 : Deploiement autonome et auto-configuration sur un QMD brut ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_qmd = tmp_path / "nouveau_rapport.qmd"
        raw_qmd.write_text(
            "---\n"
            "title: Rapport Non Configure\n"
            "author: Thomas Husson\n"
            "format: pdf\n"
            "---\n\n"
            "# Titre 1\n\n"
            "Contenu de test.\n",
            encoding="utf-8"
        )

        # 1. Deploiement autonome de l'environnement
        ok, msg = ensure_complete_project_environment(raw_qmd)
        assert ok, f"Echec deploiement environnement : {msg}"
        print("   -> Environnement complet installe :")
        assert (tmp_path / "_extensions" / "husson").is_dir(), "_extensions/husson manquant"
        assert not (tmp_path / "_extensions" / "husson").is_symlink(), "_extensions/husson ne doit pas etre un symlink"
        assert (tmp_path / "_quarto.yml").exists(), "_quarto.yml manquant"
        assert (tmp_path / "logo-universite-paris-saclay.png").exists(), "Logo racine manquant"
        assert (tmp_path / "images" / "logo-universite-paris-saclay.png").exists(), "Logo images/ manquant"
        print("      * _extensions/husson (physique reel) : OK")
        print("      * _quarto.yml : OK")
        print("      * logos dans racine et images/ : OK")

        # 2. Verification de la non-conformite initiale
        y_data, body, _ = parse_qmd(raw_qmd)
        ready, reasons = check_husson_readiness(y_data)
        assert not ready, "Le document brut ne devrait pas etre considere pret pour Husson"
        print(f"   -> Non-conformite detectee ({len(reasons)} point(s) a adapter)")

        # 3. Auto-configuration autonome
        ok_conv, msg_conv, bpath, y_updated = auto_configure_husson_document(raw_qmd, y_data, body)
        assert ok_conv, f"Echec auto-configuration : {msg_conv}"
        assert bpath.exists(), "Copie preventive scratch/ manquante"
        print(f"   -> Auto-configuration reussie. Sauvegarde : {bpath.name}")

        # 4. Verification de la conformite finale
        ready_after, reasons_after = check_husson_readiness(y_updated)
        assert ready_after, f"Le document devrait etre pret apres auto-configuration : {reasons_after}"
        formats = y_updated.get("format", {})
        first_fmt = next(iter(formats.keys()))
        assert first_fmt == "husson-pdf", f"husson-pdf doit etre premier, obtenu : {first_fmt}"
        assert formats["husson-pdf"]["documentclass"] == "scrartcl", "documentclass doit etre scrartcl"
        assert formats["husson-pdf"]["pdf-engine"] == "xelatex", "pdf-engine doit etre xelatex"
        assert formats["husson-pdf"]["mainfont"] == "Times New Roman", "mainfont doit etre Times New Roman par defaut"
        print("      * Format husson-pdf en premiere position : OK")
        print("      * scrartcl + xelatex + Times New Roman : OK")


def test_metadata_preservation():
    print("\n--- Test 2 : Preservation absolue des metadonnees riches (jury, laboratoire, etc.) ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        thesis_qmd = tmp_path / "these_test.qmd"
        content = (
            "---\n"
            "title: Memoire de Recherche\n"
            "author:\n"
            "  - name: Thomas Husson\n"
            "    affiliations: Hopital Paul Brousse\n"
            "thesis:\n"
            "  university: Universite Paris-Saclay\n"
            "  faculty: Faculte de Medecine\n"
            "  degree: Master 2\n"
            "  laboratory: Inserm UMR-S 1193\n"
            "  logo: _extensions/husson/logo-universite-paris-saclay.png\n"
            "  jury:\n"
            "    - name: Pr Faouzi SALIBA\n"
            "      title: PU-PH\n"
            "      role: President du jury\n"
            "    - name: Dr Jeremie GAUTHERON\n"
            "      title: CR Inserm\n"
            "      role: Co-directeur\n"
            "---\n\n"
            "Corps du texte.\n"
        )
        thesis_qmd.write_text(content, encoding="utf-8")

        y_data, body, _ = parse_qmd(thesis_qmd)
        ok_conv, msg_conv, bpath, y_updated = auto_configure_husson_document(thesis_qmd, y_data, body)
        assert ok_conv

        th = y_updated.get("thesis", {})
        assert th.get("laboratory") == "Inserm UMR-S 1193", "laboratory doit etre preserve"
        assert len(th.get("jury", [])) == 2, "Les 2 membres de jury doivent etre preserves"
        assert th["jury"][0]["name"] == "Pr Faouzi SALIBA"
        assert not th["logo"].startswith("_"), "Le chemin du logo ne doit plus comporter d'underscore"
        assert "images/logo-universite-paris-saclay.png" in th["logo"]
        print("   -> Laboratory et tous les membres du jury preserves : OK")
        print(f"   -> Logo normalise sans underscore : {th['logo']}")


def test_streamlit_apptest():
    print("\n--- Test 3 : Execution de l'interface Streamlit via AppTest ---")
    at = AppTest.from_file("gui/app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"Exception au demarrage de app.py : {at.exception}"

    # Charger le document d'exemple
    sample_qmd = REPO_PATH / "examples" / "these_tzedakis_exemple.qmd"
    if sample_qmd.exists():
        path_input = [t for t in at.text_input if "direct" in t.label.lower()][0]
        path_input.set_value(str(sample_qmd))
        at.run()
        assert not at.exception, f"Exception lors du chargement : {at.exception}"
        print("   -> Chargement document et rendu complet de l'interface sans erreur.")


if __name__ == "__main__":
    test_auto_deployment_and_configuration()
    test_metadata_preservation()
    test_streamlit_apptest()
    print("\nTOUS LES TESTS D'INTEGRATION ONT REUSSI SANS ERREUR.")
