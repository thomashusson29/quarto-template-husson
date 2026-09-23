#!/usr/bin/env python3
"""
Quarto Husson Studio
Interface graphique sobre et native Streamlit pour configurer et compiler
vos documents Quarto avec le template Husson (PDF, HTML, DOCX, RevealJS).
"""

import os
import sys
import re
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from io import StringIO
import streamlit as st
from ruamel.yaml import YAML

# Initialisation du parseur YAML preservant les commentaires et la structure
yaml_parser = YAML()
yaml_parser.preserve_quotes = True
yaml_parser.indent(mapping=2, sequence=4, offset=2)

TEMPLATE_REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
TEMPLATE_EXTENSION_DIR = TEMPLATE_REPO_PATH / "_extensions" / "husson"

# Configuration sobre de la page Streamlit
st.set_page_config(
    page_title="Quarto Husson Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=60)
def find_recent_qmd_files(base_dir_str: str, max_files: int = 20):
    """Recherche rapide des fichiers .qmd recents avec elagage des dossiers lourds."""
    results = []
    ignore_dirs = {'.git', '.quarto', 'scratch', 'renv', 'node_modules', 'venv', '__pycache__', 'libs'}
    try:
        for dirpath, dirnames, filenames in os.walk(base_dir_str):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
            rel_depth = len(os.path.relpath(dirpath, base_dir_str).split(os.sep))
            if rel_depth > 4:
                dirnames.clear()
                continue
            for f in filenames:
                if f.endswith(".qmd") and not f.startswith("."):
                    fp = os.path.join(dirpath, f)
                    try:
                        results.append((os.path.getmtime(fp), fp))
                    except OSError:
                        pass
    except Exception:
        pass
    results.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in results[:max_files]]


def ensure_symlink(project_dir: Path):
    """Assure que le dossier _extensions/husson est lie dans le dossier du projet ou ses parents."""
    # Verifier si deja accessible localement
    ext_dir = project_dir / "_extensions"
    husson_link = ext_dir / "husson"
    if husson_link.exists():
        return True, "Extension presente dans le dossier courant."

    # Verifier si present dans un parent jusqu'a la racine du depot
    curr = project_dir
    while curr != curr.parent:
        candidate = curr / "_extensions" / "husson"
        if candidate.exists():
            return True, f"Extension detectee dans le dossier parent : {curr.name}"
        if (curr / ".git").exists():
            break
        curr = curr.parent

    # Sinon, creer le lien symbolique dans le dossier du fichier
    ext_dir.mkdir(parents=True, exist_ok=True)
    try:
        husson_link.symlink_to(TEMPLATE_EXTENSION_DIR, target_is_directory=True)
        return True, "Lien symbolique vers _extensions/husson etabli."
    except Exception as e:
        return False, f"Erreur lors de la creation du lien symbolique : {e}"


def parse_qmd(file_path: Path):
    """Lit un fichier .qmd et extrait son YAML frontmatter et son contenu markdown."""
    if not file_path.exists():
        return None, None, "Fichier introuvable"
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, None, f"Erreur de lecture : {e}"

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_raw = parts[1]
            body_raw = parts[2]
            try:
                yaml_data = yaml_parser.load(yaml_raw) or {}
                return yaml_data, body_raw, None
            except Exception as e:
                return {}, body_raw, f"YAML non parsable : {e}"
    return {}, content, None


def save_qmd_with_backup(file_path: Path, yaml_data: dict, body: str):
    """Sauvegarde le fichier .qmd avec copie preventive automatique dans scratch/."""
    scratch_dir = file_path.parent / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = scratch_dir / f"{file_path.stem}_backup_{timestamp}.qmd"

    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        return False, f"Echec de la sauvegarde preventive : {e}", None

    try:
        stream = StringIO()
        yaml_parser.dump(yaml_data, stream)
        new_yaml_str = stream.getvalue()
        new_content = f"---\n{new_yaml_str}---\n{body.lstrip()}"
        file_path.write_text(new_content, encoding="utf-8")
        return True, f"Fichier enregistre. Copie de securite : {backup_path.name}", backup_path
    except Exception as e:
        return False, f"Erreur d'ecriture : {e}", None


# --- EN-TETE SOBRE ---
st.title("Quarto Husson Studio")
st.caption("Interface de configuration et de compilation pour documents Quarto avec le template Husson.")

# --- BARRE LATERALE (SELECTION DU DOCUMENT) ---
st.sidebar.subheader("Document Quarto")

recent_files = find_recent_qmd_files(Path("/Users/thomashusson/Documents/Projets"))
options_files = ["-- Selectionner un document recent --"] + recent_files

selected_recent = st.sidebar.selectbox("Documents recents :", options=options_files)

default_path = "/Users/thomashusson/Documents/Projets/M2biostatistiques/S2/devoir_epidemio/devoir_epidemio.qmd"
manual_path = st.sidebar.text_input(
    "Chemin d'acces direct :",
    value=selected_recent if selected_recent != options_files[0] else default_path
)

uploaded_file = st.sidebar.file_uploader("Glisser-deposer un fichier .qmd :", type=["qmd"])

target_path = None
if manual_path and Path(manual_path).exists():
    target_path = Path(manual_path).resolve()
elif uploaded_file is not None:
    temp_dir = TEMPLATE_REPO_PATH / "scratch"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / uploaded_file.name
    temp_file.write_bytes(uploaded_file.getvalue())
    target_path = temp_file

if not target_path or not target_path.exists():
    st.info("Veuillez selectionner un document .qmd valide dans la barre laterale pour commencer.")
    st.stop()

# Verification de l'extension Husson
symlink_ok, symlink_msg = ensure_symlink(target_path.parent)

# Informations sur le fichier actif
col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    st.markdown(f"**Document actif :** `{target_path.name}`")
    st.caption(f"Emplacement : `{target_path.parent}`")
with col_info2:
    if symlink_ok:
        st.success("Template lie", icon=None)
    else:
        st.warning(symlink_msg, icon=None)

# Lecture du document .qmd
yaml_data, markdown_body, err = parse_qmd(target_path)
if err:
    st.error(err)
    st.stop()

# Extraction des donnees YAML existantes
cur_title = yaml_data.get("title", "")
cur_subtitle = yaml_data.get("subtitle", "")
cur_author = yaml_data.get("author", "Thomas Husson")
cur_lang = yaml_data.get("lang", "fr")
cur_font = yaml_data.get("mainfont", yaml_data.get("font", None))
cur_fontsize = str(yaml_data.get("fontsize", "11pt"))
cur_linestretch = str(yaml_data.get("linestretch", "1.15"))

# Analyse des formats existants
formats_data = yaml_data.get("format", {})
if isinstance(formats_data, str):
    formats_data = {formats_data: {}}
elif not isinstance(formats_data, dict):
    formats_data = {}

init_has_pdf = "pdf" in formats_data or "husson-pdf" in formats_data
init_has_html = "html" in formats_data or "husson-html" in formats_data
init_has_docx = "docx" in formats_data or "husson-docx" in formats_data
init_has_reveal = "revealjs" in formats_data or "husson-revealjs" in formats_data

# Analyse de la structure these / page de garde
thesis_data = yaml_data.get("thesis", {})
init_has_thesis = bool(thesis_data)
if not isinstance(thesis_data, dict):
    thesis_data = {}

# Options de polices disponibles
FONT_OPTIONS = [
    "Computer Modern (Latex Default)",
    "Times New Roman",
    "Garamond",
    "Roboto",
    "Carlito",
    "Personnalisee..."
]

# Detection de la police par defaut
cur_font_str = str(cur_font).strip() if cur_font else ""
default_font_idx = 0
if cur_font_str:
    c_lower = cur_font_str.lower()
    if "computer" in c_lower or "latin modern" in c_lower or "cmu" in c_lower:
        default_font_idx = 0
    elif "times" in c_lower:
        default_font_idx = 1
    elif "garamond" in c_lower:
        default_font_idx = 2
    elif "roboto" in c_lower:
        default_font_idx = 3
    elif "carlito" in c_lower:
        default_font_idx = 4
    else:
        default_font_idx = 5
else:
    default_font_idx = 0

# Initialisation securisee de l'etat de session Streamlit
file_key = str(target_path)
if "current_loaded_file" not in st.session_state or st.session_state.current_loaded_file != file_key:
    st.session_state.current_loaded_file = file_key
    st.session_state.opt_pdf = init_has_pdf if (init_has_pdf or init_has_html or init_has_docx or init_has_reveal) else True
    st.session_state.opt_html = init_has_html
    st.session_state.opt_docx = init_has_docx
    st.session_state.opt_reveal = init_has_reveal
    st.session_state.sel_font = FONT_OPTIONS[default_font_idx]
    st.session_state.custom_font_name = cur_font_str if default_font_idx == 5 else ""
    st.session_state.sel_fontsize = cur_fontsize if cur_fontsize in ["10pt", "11pt", "12pt"] else "11pt"
    st.session_state.sel_linestretch = cur_linestretch if cur_linestretch in ["1.0", "1.15", "1.25", "1.5"] else "1.15"
    st.session_state.opt_thesis_active = init_has_thesis

# --- SELECTION DU MODE DE REGLAGE ---
st.divider()
mode_choice = st.radio(
    "Mode de configuration",
    ["Profils types", "Configuration avancee"],
    horizontal=True,
    label_visibility="collapsed"
)

# --- MODE PROFILS TYPES ---
if mode_choice == "Profils types":
    st.subheader("Profils recommandes")
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)

    with col_p1:
        with st.container(border=True):
            st.markdown("**Devoir / Rapport de Master**")
            st.caption("PDF officiel Paris-Saclay, Computer Modern, page de garde sans jury, interligne 1.15.")
            if st.button("Appliquer ce profil", key="prof_devoir", use_container_width=True):
                st.session_state.opt_pdf = True
                st.session_state.opt_html = False
                st.session_state.opt_docx = False
                st.session_state.opt_reveal = False
                st.session_state.sel_font = "Computer Modern (Latex Default)"
                st.session_state.sel_fontsize = "11pt"
                st.session_state.sel_linestretch = "1.15"
                st.session_state.opt_thesis_active = True
                st.rerun()

    with col_p2:
        with st.container(border=True):
            st.markdown("**These / Memoire officiel**")
            st.caption("PDF officiel avec page de garde millimetree, jury, directeurs, Times 11pt.")
            if st.button("Appliquer ce profil", key="prof_thesis", use_container_width=True):
                st.session_state.opt_pdf = True
                st.session_state.opt_html = False
                st.session_state.opt_docx = False
                st.session_state.opt_reveal = False
                st.session_state.sel_font = "Times New Roman"
                st.session_state.sel_fontsize = "11pt"
                st.session_state.sel_linestretch = "1.15"
                st.session_state.opt_thesis_active = True
                st.rerun()

    with col_p3:
        with st.container(border=True):
            st.markdown("**Rapport Scientifique Sobre**")
            st.caption("PDF academique sans page de garde, Computer Modern, 11pt.")
            if st.button("Appliquer ce profil", key="prof_cm", use_container_width=True):
                st.session_state.opt_pdf = True
                st.session_state.opt_html = False
                st.session_state.opt_docx = False
                st.session_state.opt_reveal = False
                st.session_state.sel_font = "Computer Modern (Latex Default)"
                st.session_state.sel_fontsize = "11pt"
                st.session_state.sel_linestretch = "1.15"
                st.session_state.opt_thesis_active = False
                st.rerun()

    with col_p4:
        with st.container(border=True):
            st.markdown("**Article / Rapport Web**")
            st.caption("PDF + HTML synchronises, typographie soignee, theme clair/sombre.")
            if st.button("Appliquer ce profil", key="prof_article", use_container_width=True):
                st.session_state.opt_pdf = True
                st.session_state.opt_html = True
                st.session_state.opt_docx = False
                st.session_state.opt_reveal = False
                st.session_state.sel_font = "Times New Roman"
                st.session_state.sel_fontsize = "11pt"
                st.session_state.sel_linestretch = "1.15"
                st.session_state.opt_thesis_active = False
                st.rerun()

# --- ONGLETS DE CONFIGURATION DETAILLEE ---
tab_formats, tab_typo, tab_cover, tab_tables = st.tabs([
    "Formats de sortie",
    "Typographie & Metadonnees",
    "Page de Garde & Institution",
    "Tableaux & Options Husson"
])

with tab_formats:
    st.markdown("**Selection des formats cibles :**")
    col_fmt1, col_fmt2, col_fmt3, col_fmt4 = st.columns(4)
    with col_fmt1:
        st.checkbox("PDF (moteur Husson / XeLaTeX)", key="opt_pdf", help="Rendu XeLaTeX avec typographie calibree.")
    with col_fmt2:
        st.checkbox("HTML (moteur Husson Web)", key="opt_html", help="Rendu Web avec theme reactif clair/sombre.")
    with col_fmt3:
        st.checkbox("Word (modele Husson DOCX)", key="opt_docx", help="Document Word stylise selon le modele embarque.")
    with col_fmt4:
        st.checkbox("RevealJS (diaporama interactif)", key="opt_reveal", help="Diaporama interactif.")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        opt_toc = st.checkbox("Table des matieres", value=True)
        opt_toc_depth = st.slider("Profondeur de la table des matieres", min_value=1, max_value=5, value=3)
    with col_meta2:
        opt_num_sections = st.checkbox("Numerotation des sections", value=True)
        opt_lang = st.selectbox("Langue principale :", ["fr", "en"], index=0 if cur_lang == "fr" else 1)

with tab_typo:
    st.markdown("**Metadonnees du document :**")
    in_title = st.text_input("Titre du document :", value=str(cur_title))
    in_subtitle = st.text_input("Sous-titre :", value=str(cur_subtitle))
    in_author = st.text_input("Auteur :", value=str(cur_author))

    st.markdown("**Typographie et corps :**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.selectbox("Police de caracteres :", FONT_OPTIONS, key="sel_font")
        if st.session_state.sel_font == "Personnalisee...":
            st.text_input("Nom de la police systeme :", key="custom_font_name")
    with col_t2:
        st.selectbox("Taille du corps de texte :", ["10pt", "11pt", "12pt"], key="sel_fontsize")
    with col_t3:
        st.selectbox("Interligne :", ["1.0", "1.15", "1.25", "1.5"], key="sel_linestretch")

with tab_cover:
    st.checkbox("Activer la page de garde officielle (Mode Thèse / Mémoire / Devoir)", key="opt_thesis_active")

    if st.session_state.opt_thesis_active:
        col_th1, col_th2 = st.columns(2)
        with col_th1:
            th_university = st.text_input("Universite :", value=thesis_data.get("university", "Université Paris-Saclay"))
            th_faculty = st.text_input("Faculte :", value=thesis_data.get("faculty", "Faculté de Médecine"))
            th_degree = st.text_input("Intitule du Diplome / Formation :", value=thesis_data.get("degree", "Master 2 -- Santé Publique & Méthodologie de la Recherche"))
        with col_th2:
            th_specialty = st.text_input("Specialite / UE / Groupe :", value=thesis_data.get("specialty", "UE Épidémiologie -- Groupe 52"))
            th_dept = st.text_input("Departement / Service / Context :", value=thesis_data.get("department", "Étude observationnelle SUPPORT"))
            th_date = st.text_input("Date / Annee universitaire :", value=thesis_data.get("date", "Année universitaire 2025-2026"))

        col_logo1, col_logo2 = st.columns([2, 2])
        with col_logo1:
            LOGO_OPTIONS = ["Université Paris-Saclay", "Université Paris Cité", "Aucun logo", "Personnalise..."]
            cur_logo = str(thesis_data.get("logo", "logo-universite-paris-saclay.png"))
            default_logo_idx = 0
            if "paris-saclay" in cur_logo.lower():
                default_logo_idx = 0
            elif "paris-cite" in cur_logo.lower():
                default_logo_idx = 1
            elif not cur_logo:
                default_logo_idx = 2
            else:
                default_logo_idx = 3
            sel_logo = st.selectbox("Logo institutionnel :", LOGO_OPTIONS, index=default_logo_idx)
        with col_logo2:
            if sel_logo == "Personnalise...":
                custom_logo_path = st.text_input("Chemin vers l'image du logo :", value=cur_logo)
            else:
                custom_logo_path = ""

        with st.expander("Directeurs de recherche et encadrement (optionnel pour les devoirs)") :
            directors_list = thesis_data.get("directors", [])
            d1_name = directors_list[0].get("name", "") if len(directors_list) > 0 else ""
            d1_title = directors_list[0].get("title", "") if len(directors_list) > 0 else ""
            d1_role = directors_list[0].get("role", "Dirigé") if len(directors_list) > 0 else "Dirigé"

            d2_name = directors_list[1].get("name", "") if len(directors_list) > 1 else ""
            d2_title = directors_list[1].get("title", "") if len(directors_list) > 1 else ""
            d2_role = directors_list[1].get("role", "Et co-dirigé") if len(directors_list) > 1 else "Et co-dirigé"

            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                th_d1_name = st.text_input("Directeur 1 - Nom :", value=d1_name)
            with col_d2:
                th_d1_title = st.text_input("Directeur 1 - Titre :", value=d1_title)
            with col_d3:
                th_d1_role = st.text_input("Directeur 1 - Role :", value=d1_role)

            col_d2_1, col_d2_2, col_d2_3 = st.columns(3)
            with col_d2_1:
                th_d2_name = st.text_input("Directeur 2 - Nom :", value=d2_name)
            with col_d2_2:
                th_d2_title = st.text_input("Directeur 2 - Titre :", value=d2_title)
            with col_d2_3:
                th_d2_role = st.text_input("Directeur 2 - Role :", value=d2_role)

with tab_tables:
    st.markdown("**Moteur de mise en page des tableaux (Husson Engine) :**")
    opt_colwidths = st.checkbox(
        "Calcul automatique universel des largeurs de colonnes (Lua)",
        value=True,
        help="Calcule les largeurs relatives selon le contenu reel pour eviter tout debordement."
    )
    opt_hyphenation = st.checkbox(
        "Cesures automatiques en francais dans les cellules (ragged2e)",
        value=True,
        help="Active la cesure native TeX/Babel dans les cellules de tableau."
    )
    opt_tableau_fr = st.checkbox(
        "Appeler automatiquement 'Tableau' au lieu de 'Table' en francais",
        value=(opt_lang == "fr"),
        help="Harmonise les references croisees et titres sous 'Tableau 1' lorsque lang: fr."
    )
    opt_br_tags = st.checkbox(
        "Convertir automatiquement les balises <br> en retours a la ligne reels",
        value=True,
        help="Evite que les lignes separees par <br> ne soient fusionnees sans espace en LaTeX."
    )
    opt_gt_fit = st.checkbox(
        "Activer l'ajustement R pour tableaux gt / gtsummary (gt-page-fit.R)",
        value=False,
        help="Injecte un chunk R initialisant husson_tables_on() au debut du document."
    )


# --- GENERATION DU YAML MIS A JOUR (AVEC PRESERVATION TOTALE DE L'EXISTANT) ---
def build_updated_yaml():
    d = dict(yaml_data)
    d["title"] = in_title
    if in_subtitle:
        d["subtitle"] = in_subtitle
    d["author"] = in_author
    d["lang"] = opt_lang

    # Gestion de la police
    chosen_font = None
    if st.session_state.sel_font == "Computer Modern (Latex Default)":
        chosen_font = None
    elif st.session_state.sel_font == "Personnalisee...":
        custom = st.session_state.get("custom_font_name", "").strip()
        chosen_font = custom if custom else None
    else:
        chosen_font = st.session_state.sel_font

    if chosen_font:
        d["mainfont"] = chosen_font
    elif "mainfont" in d:
        del d["mainfont"]

    # Localisation Tableau si francais
    if opt_lang == "fr" and opt_tableau_fr:
        if "language" not in d or not isinstance(d["language"], dict):
            d["language"] = {}
        d["language"]["fr"] = {
            "crossref-tbl-title": "Tableau",
            "crossref-tbl-prefix": "Tableau",
            "crossref-lot-title": "Liste des tableaux"
        }

    # Initialisation securisee de format
    if "format" not in d or not isinstance(d["format"], dict):
        d["format"] = {}

    # Format PDF : preservation de la configuration existante
    if st.session_state.opt_pdf:
        existing_pdf = {}
        if "pdf" in d["format"] and isinstance(d["format"]["pdf"], dict):
            existing_pdf = dict(d["format"]["pdf"])
        elif "husson-pdf" in d["format"] and isinstance(d["format"]["husson-pdf"], dict):
            existing_pdf = dict(d["format"]["husson-pdf"])

        existing_pdf["pdf-engine"] = "xelatex"
        existing_pdf["documentclass"] = existing_pdf.get("documentclass", "scrartcl")
        existing_pdf["toc"] = opt_toc
        existing_pdf["toc-depth"] = opt_toc_depth
        existing_pdf["number-sections"] = opt_num_sections
        existing_pdf["fontsize"] = st.session_state.sel_fontsize
        existing_pdf["linestretch"] = float(st.session_state.sel_linestretch)

        # Template partials
        partials = list(existing_pdf.get("template-partials", []))
        if "_extensions/husson/before-body.tex" not in partials:
            partials.append("_extensions/husson/before-body.tex")
        existing_pdf["template-partials"] = partials

        # Filtres Lua Husson
        flts = list(existing_pdf.get("filters", []))
        if "_extensions/husson/typography.lua" not in flts:
            flts.append("_extensions/husson/typography.lua")
        if "_extensions/husson/table-column-widths.lua" not in flts:
            flts.append("_extensions/husson/table-column-widths.lua")
        existing_pdf["filters"] = flts

        # Localisation francais pour les tableaux
        if opt_lang == "fr" and opt_tableau_fr:
            if "language" not in existing_pdf or not isinstance(existing_pdf["language"], dict):
                existing_pdf["language"] = {}
            existing_pdf["language"]["fr"] = {
                "crossref-tbl-title": "Tableau",
                "crossref-tbl-prefix": "Tableau",
                "crossref-lot-title": "Liste des tableaux"
            }

        # Police principale
        if chosen_font:
            existing_pdf["mainfont"] = chosen_font
        elif "mainfont" in existing_pdf:
            del existing_pdf["mainfont"]

        d["format"]["pdf"] = existing_pdf

    # Format HTML : preservation de l'existant
    if st.session_state.opt_html:
        existing_html = {}
        if "html" in d["format"] and isinstance(d["format"]["html"], dict):
            existing_html = dict(d["format"]["html"])
        elif "husson-html" in d["format"] and isinstance(d["format"]["husson-html"], dict):
            existing_html = dict(d["format"]["husson-html"])

        existing_html["toc"] = opt_toc
        existing_html["toc-depth"] = opt_toc_depth
        existing_html["number-sections"] = opt_num_sections
        if "theme" not in existing_html:
            existing_html["theme"] = "cosmo"
        existing_html["embed-resources"] = True

        if opt_lang == "fr" and opt_tableau_fr:
            if "language" not in existing_html or not isinstance(existing_html["language"], dict):
                existing_html["language"] = {}
            existing_html["language"]["fr"] = {
                "crossref-tbl-title": "Tableau",
                "crossref-tbl-prefix": "Tableau",
                "crossref-lot-title": "Liste des tableaux"
            }
        d["format"]["html"] = existing_html

    # Format Word
    if st.session_state.opt_docx:
        existing_docx = {}
        if "docx" in d["format"] and isinstance(d["format"]["docx"], dict):
            existing_docx = dict(d["format"]["docx"])
        existing_docx["toc"] = opt_toc
        existing_docx["toc-depth"] = opt_toc_depth
        existing_docx["number-sections"] = opt_num_sections
        if "_extensions/husson/template.docx" not in existing_docx.get("reference-doc", ""):
            existing_docx["reference-doc"] = "_extensions/husson/template.docx"
        d["format"]["docx"] = existing_docx

    # Format RevealJS
    if st.session_state.opt_reveal:
        existing_reveal = {}
        if "revealjs" in d["format"] and isinstance(d["format"]["revealjs"], dict):
            existing_reveal = dict(d["format"]["revealjs"])
        existing_reveal["slide-number"] = True
        existing_reveal["transition"] = "none"
        d["format"]["revealjs"] = existing_reveal

    # Configuration Page de Garde / These
    if st.session_state.opt_thesis_active:
        resolved_logo = None
        if sel_logo == "Université Paris-Saclay":
            resolved_logo = "_extensions/husson/logo-universite-paris-saclay.png"
        elif sel_logo == "Université Paris Cité":
            resolved_logo = "_extensions/husson/logo-universite-paris-cite.png"
        elif sel_logo == "Personnalise..." and custom_logo_path.strip():
            resolved_logo = custom_logo_path.strip()

        thesis_dict = {
            "university": th_university,
            "faculty": th_faculty,
            "degree": th_degree,
        }
        if th_specialty.strip():
            thesis_dict["specialty"] = th_specialty.strip()
        if th_dept.strip():
            thesis_dict["department"] = th_dept.strip()
        if th_date.strip():
            thesis_dict["date"] = th_date.strip()
        if resolved_logo:
            thesis_dict["logo"] = resolved_logo

        # Directeurs (uniquement si renseignes)
        directors = []
        if th_d1_name.strip():
            directors.append({"name": th_d1_name.strip(), "title": th_d1_title.strip(), "role": th_d1_role.strip()})
        if th_d2_name.strip():
            directors.append({"name": th_d2_name.strip(), "title": th_d2_title.strip(), "role": th_d2_role.strip()})
        if directors:
            thesis_dict["directors"] = directors

        d["thesis"] = thesis_dict
    elif "thesis" in d:
        del d["thesis"]

    return d


# --- BARRE D'ACTIONS ---
st.divider()
col_act1, col_act2, col_act3 = st.columns([2, 3, 2])

with col_act1:
    btn_save = st.button("Enregistrer les reglages dans le .qmd", use_container_width=True)

with col_act2:
    btn_render = st.button("Lancer la compilation (quarto render)", type="primary", use_container_width=True)

with col_act3:
    auto_open = st.checkbox("Ouvrir apres compilation", value=True)

# Sauvegarde sans compilation
if btn_save:
    new_yaml = build_updated_yaml()
    body_to_save = markdown_body

    if opt_gt_fit and "husson_tables_on" not in body_to_save:
        r_chunk = "\n```{r setup-husson-tables, include=FALSE}\nif (file.exists(\"_extensions/husson/gt-page-fit.R\")) {\n  source(\"_extensions/husson/gt-page-fit.R\")\n  husson_tables_on()\n}\n```\n\n"
        body_to_save = r_chunk + body_to_save

    ok, msg, bpath = save_qmd_with_backup(target_path, new_yaml, body_to_save)
    if ok:
        st.success(msg)
    else:
        st.error(msg)

# Execution de quarto render avec terminal integre
if btn_render:
    new_yaml = build_updated_yaml()
    body_to_save = markdown_body
    if opt_gt_fit and "husson_tables_on" not in body_to_save:
        r_chunk = "\n```{r setup-husson-tables, include=FALSE}\nif (file.exists(\"_extensions/husson/gt-page-fit.R\")) {\n  source(\"_extensions/husson/gt-page-fit.R\")\n  husson_tables_on()\n}\n```\n\n"
        body_to_save = r_chunk + body_to_save

    ok, msg, bpath = save_qmd_with_backup(target_path, new_yaml, body_to_save)
    if not ok:
        st.error(f"Impossible d'enregistrer avant la compilation : {msg}")
        st.stop()

    st.caption(f"Copie preventive sauvegardee : `{bpath.name}`")

    target_formats = []
    if st.session_state.opt_pdf:
        target_formats.append("pdf")
    if st.session_state.opt_html:
        target_formats.append("html")
    if st.session_state.opt_docx:
        target_formats.append("docx")
    if st.session_state.opt_reveal:
        target_formats.append("revealjs")

    if not target_formats:
        st.warning("Veuillez cocher au moins un format de sortie.")
        st.stop()

    cmd = ["quarto", "render", str(target_path)]
    if len(target_formats) == 1:
        cmd.extend(["--to", target_formats[0]])

    start_time = time.time()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    with st.status("Compilation en cours...", expanded=True) as status_box:
        st.write(f"Commande executee : `{' '.join(cmd)}`")
        log_placeholder = st.empty()

        process = subprocess.Popen(
            cmd,
            cwd=str(target_path.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )

        terminal_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                terminal_lines.append(line)
                log_placeholder.code("".join(terminal_lines[-40:]), language="bash")
                time.sleep(0.01)

        return_code = process.poll()
        elapsed = time.time() - start_time
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s" if elapsed >= 60 else f"{elapsed:.1f}s"

        # Affichage du journal integral final
        log_placeholder.code("".join(terminal_lines), language="bash")

        if return_code == 0:
            status_box.update(label=f"Compilation terminee avec succes ({elapsed_str})", state="complete", expanded=False)
            st.success(f"Document compile avec succes en {elapsed_str}.")
        else:
            status_box.update(label=f"Erreur de compilation (code {return_code})", state="error", expanded=True)
            st.error(f"Erreur lors de la compilation (code {return_code}). Consultez le journal ci-dessus.")

    if return_code == 0:
        pdf_out = target_path.with_suffix(".pdf")
        html_out = target_path.with_suffix(".html")
        docx_out = target_path.with_suffix(".docx")

        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        with col_res1:
            if st.session_state.opt_pdf and pdf_out.exists():
                if st.button("Ouvrir le PDF", use_container_width=True):
                    subprocess.run(["open", str(pdf_out)])
        with col_res2:
            if st.session_state.opt_html and html_out.exists():
                if st.button("Ouvrir le HTML", use_container_width=True):
                    subprocess.run(["open", str(html_out)])
        with col_res3:
            if st.session_state.opt_docx and docx_out.exists():
                if st.button("Ouvrir le document Word", use_container_width=True):
                    subprocess.run(["open", str(docx_out)])
        with col_res4:
            if st.button("Ouvrir le dossier (Finder)", use_container_width=True):
                subprocess.run(["open", str(target_path.parent)])

        if auto_open:
            if st.session_state.opt_pdf and pdf_out.exists():
                subprocess.run(["open", str(pdf_out)])
            elif st.session_state.opt_html and html_out.exists():
                subprocess.run(["open", str(html_out)])
