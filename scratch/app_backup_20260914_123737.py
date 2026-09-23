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


def find_recent_qmd_files(base_dir: Path, max_files: int = 15):
    """Recherche les fichiers .qmd recents dans les dossiers de projets."""
    results = []
    try:
        for p in base_dir.rglob("*.qmd"):
            if ".quarto" in p.parts or "scratch" in p.parts or ".git" in p.parts:
                continue
            try:
                mtime = p.stat().st_mtime
                results.append((mtime, p))
            except OSError:
                continue
    except Exception:
        pass
    results.sort(key=lambda x: x[0], reverse=True)
    return [str(p) for _, p in results[:max_files]]


def ensure_symlink(project_dir: Path):
    """Assure que le dossier _extensions/husson est lie dans le dossier du projet."""
    ext_dir = project_dir / "_extensions"
    husson_link = ext_dir / "husson"
    if not husson_link.exists():
        ext_dir.mkdir(parents=True, exist_ok=True)
        try:
            husson_link.symlink_to(TEMPLATE_EXTENSION_DIR, target_is_directory=True)
            return True, "Lien symbolique vers _extensions/husson etabli."
        except Exception as e:
            return False, f"Erreur lors de la creation du lien symbolique : {e}"
    return True, "Extension presente."


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

default_path = "/Users/thomashusson/Documents/Projets/M2transplantation/docs/M2_transplant_v2.qmd"
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
        st.warning("Template non lie", icon=None)

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

# Analyse de la structure these
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
    st.session_state.opt_pdf = init_has_pdf
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
            st.markdown("**These / Memoire**")
            st.caption("PDF officiel avec page de garde millimetree, Times 11pt, interligne 1.15, jury.")
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

    with col_p2:
        with st.container(border=True):
            st.markdown("**Rapport Scientifique**")
            st.caption("PDF academique sobre avec Computer Modern (LaTeX default), 11pt, tableau optimise.")
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

    with col_p3:
        with st.container(border=True):
            st.markdown("**Article / Rapport**")
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

    with col_p4:
        with st.container(border=True):
            st.markdown("**Presentation RevealJS**")
            st.caption("Diapositives interactives RevealJS adaptees aux soutenances.")
            if st.button("Appliquer ce profil", key="prof_reveal", use_container_width=True):
                st.session_state.opt_pdf = False
                st.session_state.opt_html = False
                st.session_state.opt_docx = False
                st.session_state.opt_reveal = True
                st.session_state.opt_thesis_active = False
                st.rerun()

# --- ONGLETS DE CONFIGURATION DETAILLEE ---
tab_formats, tab_typo, tab_thesis, tab_tables = st.tabs([
    "Formats de sortie",
    "Typographie & Metadonnees",
    "These & Jury",
    "Tableaux & Options Husson"
])

with tab_formats:
    st.markdown("**Selection des formats cibles :**")
    col_fmt1, col_fmt2, col_fmt3, col_fmt4 = st.columns(4)
    with col_fmt1:
        st.checkbox("PDF (husson-pdf)", key="opt_pdf", help="Rendu XeLaTeX avec typographie calibree.")
    with col_fmt2:
        st.checkbox("HTML (husson-html)", key="opt_html", help="Rendu Web avec theme reactif clair/sombre.")
    with col_fmt3:
        st.checkbox("Word (husson-docx)", key="opt_docx", help="Document Word stylise selon le modele embarque.")
    with col_fmt4:
        st.checkbox("RevealJS (husson-revealjs)", key="opt_reveal", help="Diaporama interactif.")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        opt_toc = st.checkbox("Table des matieres", value=True)
        opt_toc_depth = st.slider("Profondeur de la table des matieres", min_value=1, max_value=4, value=3)
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

with tab_thesis:
    st.checkbox("Activer la page de garde officielle de These / Memoire", key="opt_thesis_active")

    if st.session_state.opt_thesis_active:
        col_th1, col_th2 = st.columns(2)
        with col_th1:
            th_university = st.text_input("Universite :", value=thesis_data.get("university", "Universite Paris-Saclay"))
            th_faculty = st.text_input("Faculte :", value=thesis_data.get("faculty", "Faculte de Medecine"))
            th_degree = st.text_input("Intitule du Diplome :", value=thesis_data.get("degree", "Memoire de Master 2 Sciences Chirurgicales"))
        with col_th2:
            th_dept = st.text_input("Service / Hopital :", value=thesis_data.get("department", "Centre Hepato-Biliaire, Hopital Paul Brousse, AP-HP"))
            th_lab = st.text_input("Laboratoire / Unite :", value=thesis_data.get("laboratory", "Inserm UMR-S 1193, Universite Paris-Saclay"))
            th_date = st.text_input("Date de soutenance :", value=thesis_data.get("date", "7 octobre 2026"))

        st.markdown("**Directeurs de recherche :**")
        directors_list = thesis_data.get("directors", [])
        d1_name = directors_list[0].get("name", "Pr Claire GOUMARD") if len(directors_list) > 0 else ""
        d1_title = directors_list[0].get("title", "PU-PH") if len(directors_list) > 0 else ""
        d1_role = directors_list[0].get("role", "Dirige") if len(directors_list) > 0 else ""

        d2_name = directors_list[1].get("name", "Dr Jeremie GAUTHERON") if len(directors_list) > 1 else ""
        d2_title = directors_list[1].get("title", "CR, Inserm UMR-S 938") if len(directors_list) > 1 else ""
        d2_role = directors_list[1].get("role", "Et co-dirige") if len(directors_list) > 1 else ""

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            th_d1_name = st.text_input("Directeur 1 - Nom :", value=d1_name)
        with col_d2:
            th_d1_title = st.text_input("Directeur 1 - Titre :", value=d1_title)
        with col_d3:
            th_d1_role = st.text_input("Directeur 1 - Role :", value=d1_role)

        col_d2_1, col_d2_2, col_d2_3 = st.columns(3)
        with col_d2_1:
            th_d2_name = st.text_input("Directeur 2 - Nom (optionnel) :", value=d2_name)
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


# --- GENERATION DU YAML MIS A JOUR ---
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

    # Formats
    new_formats = {}
    if st.session_state.opt_pdf:
        pdf_conf = {
            "toc": opt_toc,
            "toc-depth": opt_toc_depth,
            "number-sections": opt_num_sections,
            "pdf-engine": "xelatex",
            "documentclass": "scrartcl",
            "fontsize": st.session_state.sel_fontsize,
            "linestretch": float(st.session_state.sel_linestretch),
            "template-partials": ["_extensions/husson/before-body.tex"],
            "filters": ["_extensions/husson/table-column-widths.lua"]
        }
        if chosen_font:
            pdf_conf["mainfont"] = chosen_font
        if opt_lang == "fr" and opt_tableau_fr:
            pdf_conf["language"] = {
                "fr": {
                    "crossref-tbl-title": "Tableau",
                    "crossref-tbl-prefix": "Tableau",
                    "crossref-lot-title": "Liste des tableaux"
                }
            }
        new_formats["pdf"] = pdf_conf

    if st.session_state.opt_html:
        new_formats["html"] = {
            "toc": opt_toc,
            "toc-depth": opt_toc_depth,
            "number-sections": opt_num_sections,
            "theme": "cosmo",
            "embed-resources": True
        }
        if opt_lang == "fr" and opt_tableau_fr:
            new_formats["html"]["language"] = {
                "fr": {
                    "crossref-tbl-title": "Tableau",
                    "crossref-tbl-prefix": "Tableau",
                    "crossref-lot-title": "Liste des tableaux"
                }
            }

    if st.session_state.opt_docx:
        new_formats["docx"] = {
            "toc": opt_toc,
            "toc-depth": opt_toc_depth,
            "number-sections": opt_num_sections,
            "reference-doc": "_extensions/husson/template.docx"
        }

    if st.session_state.opt_reveal:
        new_formats["revealjs"] = {
            "theme": ["default", "_extensions/husson/auto-dark-clean.scss"],
            "slide-number": True,
            "transition": "none"
        }

    d["format"] = new_formats

    # Configuration These
    if st.session_state.opt_thesis_active:
        directors = [{"name": th_d1_name, "title": th_d1_title, "role": th_d1_role}]
        if th_d2_name:
            directors.append({"name": th_d2_name, "title": th_d2_title, "role": th_d2_role})

        d["thesis"] = {
            "university": th_university,
            "faculty": th_faculty,
            "degree": th_degree,
            "department": th_dept,
            "laboratory": th_lab,
            "date": th_date,
            "directors": directors
        }
    elif "thesis" in d:
        del d["thesis"]

    # Header-includes (ragged2e, unicode, hook tablename)
    header_lines = [
        "\\usepackage{fvextra}",
        "\\fvset{breaklines,breakanywhere,breaknonspaceingroup}",
        "\\usepackage{float}",
        "\\floatplacement{figure}{H}",
        "\\floatplacement{table}{H}",
        "\\addtokomafont{disposition}{\\rmfamily}",
        "\\usepackage{newunicodechar}",
        "\\newunicodechar{₂}{\\textsubscript{2}}",
        "\\newunicodechar{₁}{\\textsubscript{1}}",
        "\\newunicodechar{₀}{\\textsubscript{0}}",
        "\\newunicodechar{₃}{\\textsubscript{3}}",
        "\\newunicodechar{₄}{\\textsubscript{4}}",
        "\\newunicodechar{≥}{\\ensuremath{\\geq}}",
        "\\newunicodechar{≤}{\\ensuremath{\\leq}}",
        "\\newunicodechar{≈}{\\ensuremath{\\approx}}",
    ]
    if opt_hyphenation:
        header_lines.extend([
            "\\usepackage{ragged2e}",
            "\\AtBeginDocument{",
            "  \\renewcommand{\\raggedright}{\\RaggedRight\\hspace{0pt}}",
            "}"
        ])
    if opt_lang == "fr" and opt_tableau_fr:
        header_lines.extend([
            "\\AddToHook{begindocument/end}{%",
            "  \\renewcommand{\\tablename}{Tableau}%",
            "}"
        ])

    if "pdf" in d["format"]:
        d["format"]["pdf"]["header-includes"] = "\n".join(header_lines) + "\n"

    return d


# --- BARRE D'ACTIONS ---
st.divider()
col_act1, col_act2, col_act3 = st.columns([2, 3, 2])

with col_act1:
    btn_save = st.button("Enregistrer les reglages", use_container_width=True)

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
