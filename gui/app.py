#!/usr/bin/env python3
"""
Quarto Husson Studio
Espace de travail pour créer, convertir, configurer et compiler des documents
Quarto avec le template Husson (PDF, HTML, DOCX, RevealJS, PPTX).
"""

import os
import sys
import re
import time
import shutil
import linecache
import subprocess
from pathlib import Path

linecache.checkcache(__file__)
import base64
import html
import json
import tempfile
import urllib.request
import urllib.error
from datetime import datetime
from io import StringIO
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from ruamel.yaml import YAML

# Initialisation du chemin système et des utilitaires Quarto / XeLaTeX
EXTRA_SYSTEM_PATHS = [
    "/Applications/quarto/bin",
    "/Library/TeX/texbin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/usr/bin",
    "/bin",
]
for p in EXTRA_SYSTEM_PATHS:
    if Path(p).exists() and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{p}:{os.environ.get('PATH', '')}"

# Initialisation du parseur YAML préservant les commentaires et la structure
yaml_parser = YAML()
yaml_parser.preserve_quotes = True
yaml_parser.indent(mapping=2, sequence=4, offset=2)

TEMPLATE_REPO_PATH = Path(__file__).resolve().parent.parent
REPO_ROOT = TEMPLATE_REPO_PATH
TEMPLATE_EXTENSION_DIR = TEMPLATE_REPO_PATH / "_extensions" / "husson"
PROJECTS_BASE_DIR = TEMPLATE_REPO_PATH.parent

st.set_page_config(
    page_title="Quarto Husson Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Feuille de style sobre et minimale (macOS / Things 3 / Linear en mode clair, 3 panels sans scroll)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F6F7F9;
        color: #242932;
    }
    .stDeployButton,
    div[data-testid="stAppDeployButton"],
    div[data-testid="stToolbarActions"],
    span[data-testid="stMainMenu"] {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 1.1rem !important;
    }
    .block-container {
        padding-top: 0.35rem !important;
        padding-bottom: 0.4rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        max-width: 100% !important;
    }

    /* Suppression de la marge negative native de Streamlit (-1rem) qui provoque des chevauchements verticaux */
    div[data-testid="stMarkdown"],
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stCaptionContainer"],
    div.erovr380 {
        margin-bottom: 0 !important;
    }

    /* Densite verticale compacte sans aucun chevauchement pour tout voir sans scroll */
    div[data-testid="stMainBlockContainer"] div[data-testid="stVerticalBlock"] {
        gap: 0.42rem !important;
    }

    /* Surfaces principales explicites (#FFFFFF sur fond #F6F7F9) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div[class*="st-key-surface_"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E5EA !important;
        border-radius: 7px !important;
        padding: 0.48rem 0.72rem !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03) !important;
    }

    /* Barre laterale : rabattement complet avec la fleche native (aria-expanded="false") */
    section[data-testid="stSidebar"] {
        background-color: #F6F7F9 !important;
        border-right: 1px solid #E2E5EA !important;
    }
    section[data-testid="stSidebar"][aria-expanded="true"] {
        width: 205px !important;
        min-width: 205px !important;
        max-width: 205px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0px !important;
        min-width: 0px !important;
        max-width: 0px !important;
        flex: 0 0 0px !important;
        margin-left: 0px !important;
        border-right: none !important;
        overflow: hidden !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }

    /* Interdiction absolue des mots coupes sur 2 lignes dans les controles */
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label p,
    div[data-testid="stCheckbox"] label span,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    div[role="radiogroup"] label p,
    div[data-testid="stButton"] button p,
    .husson-doc-title,
    .husson-badge,
    .husson-section-label,
    .husson-section-sep {
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
    }

    /* Uniformisation stricte et compacte de tous les boutons (Create, Save, Render, Preview, Open, etc.) */
    div[data-testid="stButton"] button,
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-secondary"],
    .st-key-btn_top_create button,
    .st-key-btn_top_save button,
    .st-key-btn_top_render button,
    .st-key-btn_activate_husson button,
    .st-key-btn_top_quick_preview button,
    .st-key-btn_panel_quick_preview button,
    .st-key-btn_panel_open_ext button,
    .st-key-btn_open_pdf button,
    .st-key-btn_open_html button,
    .st-key-btn_open_docx button,
    .st-key-btn_open_finder button {
        font-size: 0.72rem !important;
        font-weight: 500 !important;
        min-height: 1.48rem !important;
        height: 1.5rem !important;
        padding: 0.02rem 0.45rem !important;
        border-radius: 5px !important;
        line-height: 1.05 !important;
    }
    div[data-testid="stButton"] button p,
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-secondary"] p {
        font-size: 0.72rem !important;
        line-height: 1.05 !important;
    }

    /* Petits boutons de bascule des panels en haut du panel central */
    .st-key-visible_panels button[data-testid="stBaseButton-pills"],
    .st-key-visible_panels button[data-testid="stBaseButton-pillsActive"] {
        font-size: 0.71rem !important;
        min-height: 1.38rem !important;
        height: 1.4rem !important;
        padding: 0.02rem 0.45rem !important;
        border-radius: 5px !important;
    }

    /* Uniformisation stricte de l'ensemble du contenu du panel central sur la taille de Cover / Contents (0.74rem) */
    [data-testid="stWidgetLabel"],
    label[data-testid="stWidgetLabel"] {
        margin-bottom: 0.1rem !important;
        min-height: 0 !important;
        height: auto !important;
        font-size: 0.74rem !important;
    }
    .st-key-surface_editor p,
    .st-key-surface_editor span,
    .st-key-surface_editor label,
    .st-key-surface_editor input,
    .st-key-surface_editor textarea,
    .st-key-surface_editor summary,
    .st-key-surface_editor div[data-testid="stMarkdownContainer"],
    .st-key-surface_editor div[data-testid="stCaptionContainer"],
    [data-testid="stWidgetLabel"] div[data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] span,
    label[data-testid="stWidgetLabel"] p,
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"],
    div[data-testid="stCheckbox"] label p,
    div[data-testid="stCheckbox"] label span,
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary div[data-testid="stMarkdownContainer"],
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span,
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span,
    div[data-testid="stCaptionContainer"] p {
        font-size: 0.74rem !important;
        font-weight: 400 !important;
        line-height: 1.2 !important;
        color: #475467 !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span {
        color: #242932 !important;
    }

    /* Cases a cocher (checkboxes) reduites et proportionnees au texte 0.74rem */
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] {
        align-items: center !important;
        min-height: 1.2rem !important;
    }
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > span:first-of-type {
        width: 0.76rem !important;
        height: 0.76rem !important;
        min-width: 0.76rem !important;
        min-height: 0.76rem !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        border-radius: 3px !important;
        background-size: 0.52rem 0.52rem !important;
    }
    div[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div {
        padding-left: 0.34rem !important;
    }

    /* Champs de saisie (text_input), menus deroulants (selectbox) et accordeons (expander) compacts et proportionnes au texte 0.74rem */
    div[data-testid="stTextInputRootElement"],
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div {
        min-height: 1.48rem !important;
        height: 1.48rem !important;
        max-height: 1.48rem !important;
        font-size: 0.74rem !important;
        border-radius: 5px !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        padding-top: 0.06rem !important;
        padding-bottom: 0.06rem !important;
        padding-left: 0.42rem !important;
        padding-right: 0.42rem !important;
        min-height: 1.42rem !important;
        height: 1.42rem !important;
        line-height: 1.2 !important;
    }
    div[data-baseweb="select"] > div > div {
        padding-top: 0.02rem !important;
        padding-bottom: 0.02rem !important;
        padding-left: 0.42rem !important;
        padding-right: 0.25rem !important;
    }
    div[data-baseweb="select"] svg {
        width: 0.85rem !important;
        height: 0.85rem !important;
    }
    div[data-testid="stExpander"] summary {
        padding: 0.14rem 0.5rem !important;
        min-height: 1.5rem !important;
        height: 1.5rem !important;
        align-items: center !important;
    }

    /* Terminal large en bas et YAML compacts toujours visibles sans scroll de page */
    .st-key-surface_terminal pre {
        max-height: 58px !important;
        overflow-y: auto !important;
        padding: 0.25rem 0.45rem !important;
        font-size: 0.68rem !important;
        line-height: 1.22 !important;
        margin: 0 !important;
    }
    .st-key-surface_preview pre {
        max-height: 235px !important;
        overflow-y: auto !important;
        padding: 0.35rem 0.5rem !important;
        font-size: 0.71rem !important;
        line-height: 1.25 !important;
        margin: 0 !important;
    }

    /* En-tete du document actif sans chevauchement */
    .husson-doc-header {
        display: flex;
        flex-direction: column;
        gap: 0.08rem;
        min-width: 0;
        padding-bottom: 0.05rem;
    }
    .husson-doc-title-row {
        display: flex;
        align-items: center;
        flex-wrap: nowrap;
        gap: 0.28rem;
        overflow: hidden;
    }
    .husson-doc-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #242932;
        letter-spacing: -0.01em;
        margin: 0;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .husson-doc-path {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.68rem;
        color: #687281;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        line-height: 1.2;
    }
    .husson-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.65rem;
        font-weight: 500;
        padding: 0.02rem 0.32rem;
        border-radius: 4px;
        border: 1px solid #E2E5EA;
        background-color: #F6F7F9;
        color: #475467;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    .husson-badge-ok {
        background-color: #EDF4F9;
        border-color: #C7D9E8;
        color: #2B547E;
        font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
    }
    .husson-badge-warn {
        background-color: #FEF6EE;
        border-color: #F3D6B6;
        color: #8F4F12;
        font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
    }

    /* Intitules de sous-sections et separateurs combines sans aucun chevauchement */
    .husson-section-label {
        display: block;
        font-size: 0.66rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.045em;
        color: #687281;
        margin-top: 0.06rem;
        margin-bottom: 0.14rem;
        padding-bottom: 0.06rem;
        line-height: 1.25;
    }
    .husson-section-sep {
        display: block;
        border-top: 1px solid #E2E5EA;
        padding-top: 0.28rem;
        padding-bottom: 0.14rem;
        margin-top: 0.1rem;
        margin-bottom: 0.08rem;
        font-size: 0.66rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.045em;
        color: #687281;
        line-height: 1.25;
    }
    .husson-toolbar-sep {
        border-top: 1px solid #E2E5EA;
        margin: 0.22rem 0;
    }

    /* Onglets sobres et barres d'onglets stateful (memes tailles 0.74rem) */
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.85rem !important;
        border-bottom: 1px solid #E2E5EA !important;
        padding-bottom: 0 !important;
        margin-bottom: 0.12rem !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label {
        background: transparent !important;
        padding: 0.12rem 0.04rem 0.22rem 0.04rem !important;
        margin: 0 !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px !important;
        cursor: pointer !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label p {
        font-size: 0.74rem !important;
        font-weight: 500 !important;
        color: #687281 !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label:hover p {
        color: #242932 !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label:has(input:checked) {
        border-bottom: 2px solid #426B91 !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label:has(input:checked) p {
        color: #426B91 !important;
        font-weight: 600 !important;
    }

    /* Onglets du panel Preview plus resserres pour eviter tout chevauchement avec Preview / Open */
    .st-key-surface_preview div[role="radiogroup"] {
        gap: 0.55rem !important;
        margin-bottom: 0.05rem !important;
    }
    .st-key-surface_preview div[role="radiogroup"] > label {
        padding: 0.1rem 0.02rem 0.2rem 0.02rem !important;
    }
    .st-key-surface_preview div[role="radiogroup"] > label p {
        font-size: 0.74rem !important;
    }

    hr {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
        border-color: #E2E5EA !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_display_path(p: Path) -> str:
    """Formate un chemin absolu avec ~/ pour un affichage compact et lisible."""
    try:
        home = Path.home()
        if str(p).startswith(str(home)):
            return "~/" + str(p.relative_to(home))
    except Exception:
        pass
    return str(p)


@st.cache_data(ttl=60)
def find_recent_qmd_files(base_dir_str: str, max_files: int = 30):
    """Recherche rapide des fichiers .qmd récents avec élagage strict des dossiers lourds."""
    results = []
    ignore_dirs = {
        ".git",
        ".quarto",
        ".Rproj.user",
        ".venv",
        "venv",
        "env",
        "renv",
        "scratch",
        "node_modules",
        "__pycache__",
        "libs",
        "site_libs",
        "_extensions",
        "_freeze",
        "_site",
        "output",
        "docs",
        "data",
        "Data",
        "archives",
        "backup",
        "backups",
        "figures",
        "images",
        "plots",
        "results",
    }
    try:
        for dirpath, dirnames, filenames in os.walk(base_dir_str):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith(".")]
            rel_depth = len(os.path.relpath(dirpath, base_dir_str).split(os.sep))
            if rel_depth > 3:
                dirnames.clear()
                continue
            for f in filenames:
                if f.endswith(".qmd") and not f.startswith(".") and "_backup_" not in f:
                    fp = os.path.join(dirpath, f)
                    try:
                        results.append((os.path.getmtime(fp), fp))
                    except OSError:
                        pass
    except Exception:
        pass
    results.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in results[:max_files]]


@st.cache_data(ttl=60)
def list_project_directories(base_dir_str: str) -> list:
    """Retourne les dossiers de premier et second niveau dans ~/Documents/Projets."""
    base = Path(base_dir_str)
    if not base.exists():
        return [str(TEMPLATE_REPO_PATH)]
    dirs = [str(base)]
    ignore = {".git", ".quarto", "scratch", "node_modules", "venv", ".venv", "__pycache__", "_extensions", "output", "docs"}
    try:
        for child in sorted(base.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and child.name not in ignore:
                dirs.append(str(child))
                for sub in sorted(child.iterdir()):
                    if sub.is_dir() and not sub.name.startswith(".") and sub.name not in ignore:
                        dirs.append(str(sub))
    except Exception:
        pass
    return dirs


def find_project_root(file_path: Path) -> Path:
    """Trouve la racine du projet Quarto (contenant _quarto.yml ou .git) en remontant l'arborescence."""
    curr = file_path.resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / "_quarto.yml").exists() or (parent / ".git").exists():
            return parent
    return curr


def ensure_complete_project_environment(target_path: Path):
    """
    Déploie de façon autonome l'extension _extensions/husson dans le projet
    sans polluer le dossier de travail avec des fichiers .ttf, .png ou .bib détachés.
    """
    if not TEMPLATE_EXTENSION_DIR.exists():
        return False, f"Dossier source de l'extension Husson introuvable : {TEMPLATE_EXTENSION_DIR}"

    project_root = find_project_root(target_path)
    locations = {project_root}
    if target_path.parent.resolve() != project_root.resolve():
        locations.add(target_path.parent)

    for loc in locations:
        ext_dir = loc / "_extensions"
        husson_dir = ext_dir / "husson"

        if not (husson_dir.resolve() == TEMPLATE_EXTENSION_DIR.resolve() and not husson_dir.is_symlink()):
            if husson_dir.is_symlink() or (husson_dir.exists() and not husson_dir.is_dir()):
                try:
                    husson_dir.unlink()
                except Exception:
                    pass
            try:
                ext_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(TEMPLATE_EXTENSION_DIR, husson_dir, dirs_exist_ok=True)
            except Exception as e:
                return False, f"Erreur lors de l'installation de l'extension dans {loc} : {e}"

    return True, "Extension Husson installée."


ensure_extension_installed = ensure_complete_project_environment


def inspect_legacy_tweaks(yaml_data: dict, markdown_body: str) -> list:
    """Detects obsolete manual tweaks in a native .qmd file."""
    findings = []
    body = markdown_body or ""
    if "gt-page-fit.R" in body or "husson_tables_on" in body:
        findings.append("Manual gt-page-fit.R / husson_tables_on() call in body (handled automatically by Lua)")
    if "auto-dark-setup.R" in body or "auto_dark_on" in body:
        findings.append("Manual auto-dark-setup.R / auto_dark_on() call in body (handled automatically by Lua)")

    if isinstance(yaml_data, dict):
        formats = yaml_data.get("format", {})
        if isinstance(formats, dict):
            for fk in ("pdf", "husson-pdf"):
                fval = formats.get(fk)
                if isinstance(fval, dict):
                    if any("husson" in str(p) for p in fval.get("template-partials", [])):
                        findings.append("Redundant template-partials paths in YAML")
                    if any("husson" in str(f) for f in fval.get("filters", [])):
                        findings.append("Redundant Lua filters declared in YAML")
                    raw_inc = fval.get("include-in-header", [])
                    if isinstance(raw_inc, list) and any("pdf-header.tex" in str(h) for h in raw_inc):
                        findings.append("Redundant pdf-header.tex inclusion in YAML")
    return findings


def clean_legacy_markdown_body(markdown_body: str) -> str:
    """
    Supprime chirurgicalement uniquement les appels manuels obsolètes à gt-page-fit.R
    et auto-dark-setup.R sans modifier aucun commentaire ni code métier de l'utilisateur.
    """
    if not markdown_body:
        return markdown_body

    pattern_studio_block = re.compile(
        r"```\{r\s+setup-husson-tables[^}]*\}\s*"
        r"if\s*\(\s*file\.exists\(\"_extensions/husson/gt-page-fit\.R\"\)\s*\)\s*\{\s*"
        r"source\(\"_extensions/husson/gt-page-fit\.R\"\)\s*"
        r"husson_tables_on\(\)\s*\}\s*```\n?",
        re.MULTILINE,
    )
    cleaned = pattern_studio_block.sub("", markdown_body)

    lines = cleaned.splitlines(keepends=True)
    kept_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^source\(["\'].*(_extensions/husson/)?(gt-page-fit|auto-dark-setup)\.R["\']\)$', stripped):
            continue
        if stripped in ("husson_tables_on()", "auto_dark_on()"):
            continue
        kept_lines.append(line)

    cleaned = "".join(kept_lines)
    cleaned = re.sub(r"```\{r[^}]*\}\s*```\n?", "", cleaned)
    return cleaned


def check_husson_readiness(yaml_data: dict, target_path: Path = None) -> tuple:
    """
    Vérifie si le document est prêt pour le rendu avec le template Husson.
    Retourne (est_pret: bool, liste_des_raisons: list[str]).
    """
    if not isinstance(yaml_data, dict):
        return False, ["Structure YAML invalide."]

    reasons = []
    formats = yaml_data.get("format", {})
    if isinstance(formats, str):
        formats = {formats: "default"}
    elif not isinstance(formats, dict):
        formats = {}

    husson_keys = [k for k in formats.keys() if str(k).startswith("husson-")]
    has_project_husson = False
    if target_path is not None:
        proj_root = find_project_root(target_path)
        for q_cand in (target_path.parent / "_quarto.yml", proj_root / "_quarto.yml"):
            if q_cand.exists():
                try:
                    txt = q_cand.read_text(encoding="utf-8")
                    if "husson-" in txt:
                        has_project_husson = True
                except Exception:
                    pass

    if not husson_keys and not has_project_husson:
        reasons.append(
            "Format standard détecté ("
            + (", ".join(str(k) for k in formats.keys()) if formats else "par défaut")
            + ") non converti en format Husson."
        )

    return (len(reasons) == 0), reasons


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
    """Sauvegarde le fichier .qmd avec copie préventive automatique dans scratch/."""
    scratch_dir = file_path.parent / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = scratch_dir / f"{file_path.stem}_backup_{timestamp}.qmd"

    if file_path.exists():
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            return False, f"Échec de la sauvegarde préventive : {e}", None

    try:
        stream = StringIO()
        yaml_parser.dump(yaml_data, stream)
        new_yaml_str = stream.getvalue()
        new_content = f"---\n{new_yaml_str}---\n{body.lstrip()}"
        file_path.write_text(new_content, encoding="utf-8")
        return True, f"Modifications enregistrées (copie de sécurité : {backup_path.name})", backup_path
    except Exception as e:
        return False, f"Erreur d'écriture : {e}", None


def auto_configure_husson_document(
    target_path: Path, yaml_data: dict, markdown_body: str, clean_body: bool = True
):
    """
    Transforme sans perte le YAML d'un document natif pour lui appliquer
    les formats du template Husson (PDF, HTML, DOCX, RevealJS) et nettoie
    optionnellement les appels source() obsolètes. Sauvegarde dans scratch/.
    """
    d = dict(yaml_data) if isinstance(yaml_data, dict) else {}

    if not d.get("lang"):
        d["lang"] = "fr"

    raw_formats = d.get("format", {})
    if isinstance(raw_formats, str):
        raw_formats = {raw_formats: "default"}
    elif not isinstance(raw_formats, dict):
        raw_formats = {}

    new_formats = {}

    has_any_known = any(
        k in raw_formats
        for k in ("pdf", "husson-pdf", "html", "husson-html", "docx", "husson-docx", "revealjs", "husson-revealjs", "pptx", "husson-pptx")
    )

    if not has_any_known:
        new_formats["husson-pdf"] = "default"
        new_formats["husson-html"] = {"embed-resources": True}
    else:
        if "pdf" in raw_formats or "husson-pdf" in raw_formats:
            pdf_base = {}
            if "husson-pdf" in raw_formats and isinstance(raw_formats["husson-pdf"], dict):
                pdf_base = dict(raw_formats["husson-pdf"])
            elif "pdf" in raw_formats and isinstance(raw_formats["pdf"], dict):
                pdf_base = dict(raw_formats["pdf"])
            for k_clean in ("template-partials", "include-in-header", "filters"):
                if k_clean in pdf_base and isinstance(pdf_base[k_clean], list):
                    cleaned_list = [x for x in pdf_base[k_clean] if "husson" not in str(x) and "pdf-header.tex" not in str(x)]
                    if cleaned_list:
                        pdf_base[k_clean] = cleaned_list
                    else:
                        del pdf_base[k_clean]
            new_formats["husson-pdf"] = pdf_base if pdf_base else "default"

        if "html" in raw_formats or "husson-html" in raw_formats:
            html_base = {}
            if "husson-html" in raw_formats and isinstance(raw_formats["husson-html"], dict):
                html_base = dict(raw_formats["husson-html"])
            elif "html" in raw_formats and isinstance(raw_formats["html"], dict):
                html_base = dict(raw_formats["html"])
            if html_base.get("theme") == "cosmo":
                del html_base["theme"]
            html_base["embed-resources"] = True
            new_formats["husson-html"] = html_base

        if "docx" in raw_formats or "husson-docx" in raw_formats:
            docx_base = {}
            if "husson-docx" in raw_formats and isinstance(raw_formats["husson-docx"], dict):
                docx_base = dict(raw_formats["husson-docx"])
            elif "docx" in raw_formats and isinstance(raw_formats["docx"], dict):
                docx_base = dict(raw_formats["docx"])
            new_formats["husson-docx"] = docx_base if docx_base else "default"

        if "revealjs" in raw_formats or "husson-revealjs" in raw_formats:
            rev_base = {}
            if "husson-revealjs" in raw_formats and isinstance(raw_formats["husson-revealjs"], dict):
                rev_base = dict(raw_formats["husson-revealjs"])
            elif "revealjs" in raw_formats and isinstance(raw_formats["revealjs"], dict):
                rev_base = dict(raw_formats["revealjs"])
            new_formats["husson-revealjs"] = rev_base if rev_base else "default"

        if "pptx" in raw_formats or "husson-pptx" in raw_formats:
            pptx_base = raw_formats.get("husson-pptx", raw_formats.get("pptx"))
            new_formats["husson-pptx"] = pptx_base if isinstance(pptx_base, dict) and pptx_base else "default"

    for k, v in raw_formats.items():
        if k not in ("pdf", "html", "docx", "revealjs", "pptx", "husson-pdf", "husson-html", "husson-docx", "husson-revealjs", "husson-pptx"):
            new_formats[k] = v

    d["format"] = new_formats
    updated_body = clean_legacy_markdown_body(markdown_body) if clean_body else markdown_body

    ok, msg, bpath = save_qmd_with_backup(target_path, d, updated_body)
    return ok, msg, bpath, d


def build_new_document_body(
    include_sample_r: bool = True,
    include_frontmatter_blocks: bool = False,
    is_reveal_only: bool = False,
) -> str:
    """Construit le corps Markdown initial d'un nouveau document .qmd basé sur mtcars."""
    body_parts = []
    if is_reveal_only:
        body_parts.append(
            "\n".join(
                [
                    "# Introduction {nav-title=\"INTRODUCTION\"}",
                    "",
                    "## Contexte et objectifs {nav-title=\"Contexte\"}",
                    "",
                    "- Analyse des déterminants mécaniques de la consommation (`mpg`) sur le jeu `mtcars` ($n = 32$)",
                    "- Évaluation de l'effet du poids (`wt`), de la puissance (`hp`) et du nombre de cylindres (`cyl`)",
                    "- Démonstration native du format `husson-revealjs` (barre de navigation haute et thème clair/sombre)",
                    "",
                    "# Méthodes {nav-title=\"MÉTHODES\"}",
                    "",
                    "## Spécification du modèle linéaire {nav-title=\"Modèle OLS\"}",
                    "",
                    "$$\\text{mpg}_i = \\beta_0 + \\beta_1 \\cdot \\text{wt}_i + \\beta_2 \\cdot \\text{hp}_i + \\varepsilon_i$$",
                    "",
                    "- Ajustement par moindres carrés ordinaires (OLS)",
                    "- Stratification descriptive selon la motorisation (4, 6 ou 8 cylindres)",
                    "",
                    "# Résultats {nav-title=\"RÉSULTATS\"}",
                    "",
                    "## Tableau descriptif {.scrollable nav-title=\"Tableau\"}",
                    "",
                    "| Paramètre mesuré | 4 cylindres ($n=11$) | 6 cylindres ($n=7$) | 8 cylindres ($n=14$) | Total ($n=32$) |",
                    "|---|:---:|:---:|:---:|:---:|",
                    "| **Consommation mpg** | 26.7 ± 4.5 | 19.7 ± 1.5 | 15.1 ± 2.6 | 20.1 ± 6.0 |",
                    "| **Cylindrée disp ($\\text{in}^3$)** | 105.1 ± 26.9 | 183.3 ± 41.6 | 353.1 ± 67.8 | 230.7 ± 123.9 |",
                    "| **Puissance hp (ch)** | 82.6 ± 20.9 | 122.3 ± 24.3 | 209.2 ± 51.0 | 146.7 ± 68.6 |",
                    "| **Poids wt (1000 lbs)** | 2.29 ± 0.57 | 3.12 ± 0.36 | 4.00 ± 0.76 | 3.22 ± 0.98 |",
                    "",
                    ": Comparaison des variables de mtcars selon le nombre de cylindres {#tbl-comparatif-cyl}",
                    "",
                ]
            )
        )
        if include_sample_r:
            body_parts.append(
                "\n".join(
                    [
                        "## Relation poids et consommation {nav-title=\"Figure\"}",
                        "",
                        "```{r}",
                        "#| label: fig-reveal-mtcars",
                        '#| fig-cap: "Consommation (mpg) en fonction du poids (wt) et du nombre de cylindres"',
                        "#| echo: false",
                        "#| warning: false",
                        "#| message: false",
                        "#| fig-width: 6.5",
                        "#| fig-height: 3.6",
                        'if (requireNamespace("ggplot2", quietly = TRUE)) {',
                        "  library(ggplot2)",
                        "  mtcars$Cylindres <- factor(mtcars$cyl, labels = c('4 cylindres', '6 cylindres', '8 cylindres'))",
                        "  ggplot(mtcars, aes(x = wt, y = mpg, color = Cylindres)) +",
                        "    geom_point(size = 2.6) +",
                        "    geom_smooth(method = 'lm', se = FALSE, linewidth = 0.9) +",
                        "    scale_color_manual(values = c('#17365D', '#2E8B57', '#B22222')) +",
                        "    labs(x = 'Poids (1000 lbs)', y = 'Consommation (mpg)', color = 'Motorisation') +",
                        "    theme_minimal(base_size = 11) +",
                        "    theme(legend.position = 'top')",
                        "}",
                        "```",
                        "",
                    ]
                )
            )
        body_parts.append(
            "# Conclusion {nav-title=\"CONCLUSION\"}\n\n"
            "## Synthèse {nav-title=\"Synthèse\"}\n\n"
            "- Diminution significative de la consommation (`mpg`) avec l'augmentation du poids (`wt`) et de la puissance (`hp`)\n"
            "- Mise en page académique automatisée par l'extension `_extensions/husson`\n"
        )
    else:
        if include_sample_r:
            body_parts.append(
                "\n".join(
                    [
                        "```{r}",
                        "#| label: setup",
                        "#| include: false",
                        "library(ggplot2)",
                        "data(mtcars)",
                        "df_cars <- mtcars",
                        "df_cars$Cylindres <- factor(df_cars$cyl, labels = c('4 cylindres', '6 cylindres', '8 cylindres'))",
                        "df_cars$Transmission <- factor(df_cars$am, labels = c('Automatique', 'Manuelle'))",
                        "```",
                        "",
                    ]
                )
            )

        body_parts.append(
            "\n".join(
                [
                    "# Introduction générale {nav-title=\"INTRODUCTION\"}",
                    "",
                    "## Présentation du jeu de données mtcars {nav-title=\"Jeu mtcars\"}",
                    "",
                    "Le jeu de données `mtcars` (*Motor Trend Car Road Tests*) rassemble 32 modèles d'automobiles caractérisés par 11 variables quantitatives et qualitatives codées. Il constitue le jeu de référence standard pour illustrer les méthodes de régression linéaire, d'analyse de variance et de visualisation statistique.",
                    "",
                    "## Problématique statistique {nav-title=\"Problématique\"}",
                    "",
                    "L'objectif est de quantifier la part de variance de la consommation (`mpg`) expliquée par les caractéristiques mécaniques et pondérales des véhicules (`wt`, `hp`, `disp`, `cyl`, `am`).",
                    "",
                    "# Matériels et Méthodes {nav-title=\"MÉTHODES\"}",
                    "",
                    "## Dictionnaire des variables {nav-title=\"Variables\"}",
                    "",
                    "Le @tbl-variables détaille la définition et l'unité des principales variables issues de `mtcars`.",
                    "",
                    "| Variable | Libellé | Unité / Codage | Type statistique |",
                    "|---|---|---|---|",
                    "| **mpg** | Consommation | Miles / gallon US | Quantitative continue |",
                    "| **cyl** | Nombre de cylindres | 4, 6 ou 8 | Qualitative ordinale |",
                    "| **disp** | Cylindrée | Pouces cubes ($\\text{in}^3$) | Quantitative continue |",
                    "| **hp** | Puissance brute | Chevaux (ch) | Quantitative continue |",
                    "| **wt** | Poids du véhicule | Milliers de livres (1000 lbs) | Quantitative continue |",
                    "| **qsec** | Temps sur 1/4 de mile | Secondes (s) | Quantitative continue |",
                    "| **am** | Type de transmission | 0 = Automatique, 1 = Manuelle | Binaire |",
                    "",
                    ": Dictionnaire des variables du jeu de données mtcars {#tbl-variables}",
                    "",
                    "## Spécification du modèle linéaire {nav-title=\"Modèle OLS\"}",
                    "",
                    "Le modèle de régression linéaire multiple s'écrit :",
                    "",
                    "$$",
                    "\\text{mpg}_i = \\beta_0 + \\beta_1 \\cdot \\text{wt}_i + \\beta_2 \\cdot \\text{hp}_i + \\varepsilon_i, \\quad \\varepsilon_i \\sim \\mathcal{N}(0, \\sigma^2)",
                    "$$",
                    "",
                    "# Résultats {nav-title=\"RÉSULTATS\"}",
                    "",
                ]
            )
        )

        if include_sample_r:
            body_parts.append(
                "\n".join(
                    [
                        "## Relation entre le poids, la cylindrée et la consommation {nav-title=\"Poids et MPG\"}",
                        "",
                        "La @fig-these-mtcars représente l'évolution de la consommation (`mpg`) en fonction du poids (`wt`) pour chacune des trois catégories de cylindrée.",
                        "",
                        "```{r}",
                        "#| label: fig-these-mtcars",
                        '#| fig-cap: "Consommation (mpg) en fonction du poids (wt) et du nombre de cylindres sur mtcars (n = 32)"',
                        "#| echo: false",
                        "#| warning: false",
                        "#| message: false",
                        "#| fig-width: 6.5",
                        "#| fig-height: 3.8",
                        "ggplot(df_cars, aes(x = wt, y = mpg, color = Cylindres)) +",
                        "  geom_point(size = 2.6) +",
                        "  geom_smooth(method = 'lm', se = FALSE, linewidth = 0.9) +",
                        "  scale_color_manual(values = c('4 cylindres' = '#17365D', '6 cylindres' = '#2E8B57', '8 cylindres' = '#B22222')) +",
                        "  labs(x = 'Poids (1000 lbs)', y = 'Consommation (mpg)', color = 'Motorisation') +",
                        "  theme_minimal(base_size = 11) +",
                        "  theme(legend.position = 'top')",
                        "```",
                        "",
                    ]
                )
            )

        body_parts.append(
            "\n".join(
                [
                    "## Comparaison des caractéristiques par nombre de cylindres {nav-title=\"Comparaison\"}",
                    "",
                    "Le @tbl-comparatif-cyl compare les moyennes et écarts-types des principales variables mécaniques selon le nombre de cylindres.",
                    "",
                    "| Paramètre mesuré | 4 cylindres ($n=11$) | 6 cylindres ($n=7$) | 8 cylindres ($n=14$) | Total ($n=32$) |",
                    "|---|:---:|:---:|:---:|:---:|",
                    "| **Consommation mpg** | 26.7 ± 4.5 | 19.7 ± 1.5 | 15.1 ± 2.6 | 20.1 ± 6.0 |",
                    "| **Cylindrée disp ($\\text{in}^3$)** | 105.1 ± 26.9 | 183.3 ± 41.6 | 353.1 ± 67.8 | 230.7 ± 123.9 |",
                    "| **Puissance hp (ch)** | 82.6 ± 20.9 | 122.3 ± 24.3 | 209.2 ± 51.0 | 146.7 ± 68.6 |",
                    "| **Poids wt (1000 lbs)** | 2.29 ± 0.57 | 3.12 ± 0.36 | 4.00 ± 0.76 | 3.22 ± 0.98 |",
                    "| **Temps 1/4 mile qsec (s)** | 19.1 ± 1.6 | 18.0 ± 1.7 | 16.8 ± 1.2 | 17.8 ± 1.8 |",
                    "",
                    ": Comparaison des variables de mtcars selon le nombre de cylindres {#tbl-comparatif-cyl}",
                    "",
                    "# Discussion {nav-title=\"DISCUSSION\"}",
                    "",
                    "## Interprétation des coefficients {nav-title=\"Interprétation\"}",
                    "",
                    "L'ajustement linéaire sur `mtcars` confirme une diminution significative de la consommation en miles par gallon lorsque le poids (`wt`) et la puissance (`hp`) augmentent.",
                    "",
                    "# Conclusion {nav-title=\"CONCLUSION\"}",
                    "",
                    "Ce document valide le fonctionnement natif de la typographie, de la barre de navigation haute, de l'ajustement automatique des tableaux et des figures.",
                    "",
                ]
            )
        )

    return "\n".join(body_parts)


def create_new_qmd_document(
    dest_dir: Path,
    filename: str,
    profile_key: str,
    title: str,
    subtitle: str,
    author: str,
    include_sample_r: bool = True,
    include_frontmatter_blocks: bool = False,
) -> tuple:
    """
    Crée un nouveau document .qmd (et son dossier si nécessaire), installe
    l'extension _extensions/husson et retourne (succes: bool, message: str, path: Path).
    """
    if not filename.endswith(".qmd"):
        filename = f"{filename}.qmd"
    target_file = dest_dir / filename

    if target_file.exists():
        return False, f"Le fichier {target_file.name} existe déjà dans ce dossier.", target_file

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"Impossible de créer le dossier {dest_dir} : {e}", None

    env_ok, env_msg = ensure_complete_project_environment(target_file)
    if not env_ok:
        return False, env_msg, None

    yaml_dict = {
        "title": title or "Titre du document",
        "author": author or "Thomas Husson",
        "date": "today",
        "lang": "fr",
    }
    if subtitle and subtitle.strip():
        yaml_dict["subtitle"] = subtitle.strip()

    if profile_key == "thesis":
        yaml_dict["font"] = "Times New Roman"
        yaml_dict["thesis"] = {
            "university": "Université Paris-Saclay",
            "faculty": "Faculté de Médecine",
            "degree": "Thèse pour le diplôme d'État de Docteur en Médecine",
            "specialty": "Spécialité",
            "department": "Service / Département",
            "date": "Année universitaire 2025-2026",
            "logo": "logo-universite-paris-saclay.png",
            "directors": [
                {"name": "Pr Nom Prénom", "title": "PU-PH", "role": "Dirigé"},
            ],
            "jury": [
                {"name": "Pr Nom Prénom", "title": "PU-PH", "role": "Président du jury"},
                {"name": "Dr Nom Prénom", "title": "MCU-PH", "role": "Membre du jury"},
            ],
        }
        yaml_dict["frontmatter"] = {
            "table-of-contents": True,
            "list-of-figures": True,
            "list-of-tables": True,
            "keywords": ["Mot-clé 1", "Mot-clé 2"],
            "keywords-en": ["Keyword 1", "Keyword 2"],
        }
        yaml_dict["format"] = {
            "husson-pdf": {
                "toc": False,
                "toc-depth": 3,
                "number-sections": True,
                "fontsize": "11pt",
                "linestretch": 1.15,
            }
        }
    elif profile_key == "master":
        yaml_dict["font"] = "Computer Modern"
        yaml_dict["thesis"] = {
            "university": "Université Paris-Saclay",
            "faculty": "Faculté de Médecine",
            "degree": "Master 2 -- Santé Publique & Méthodologie de la Recherche",
            "specialty": "UE Épidémiologie",
            "department": "Devoir / Rapport",
            "date": "Année universitaire 2025-2026",
            "logo": "logo-universite-paris-saclay.png",
        }
        yaml_dict["format"] = {
            "husson-pdf": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "fontsize": "11pt",
                "linestretch": 1.15,
            }
        }
    elif profile_key == "report_cm":
        yaml_dict["font"] = "Computer Modern"
        yaml_dict["format"] = {
            "husson-pdf": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "fontsize": "11pt",
                "linestretch": 1.15,
            }
        }
    elif profile_key == "revealjs":
        yaml_dict["format"] = {
            "husson-revealjs": {
                "slide-number": True,
                "transition": "none",
            }
        }
    else:
        yaml_dict["font"] = "Times New Roman"
        yaml_dict["format"] = {
            "husson-pdf": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "fontsize": "11pt",
                "linestretch": 1.15,
            },
            "husson-html": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "embed-resources": True,
            },
        }

    body_parts = []
    if include_frontmatter_blocks or profile_key == "thesis":
        body_parts.append(
            "\n".join(
                [
                    "::: {.frontmatter-acknowledgements}",
                    "Vos remerciements ici.",
                    ":::",
                    "",
                    "::: {.frontmatter-abstract}",
                    "**Introduction :** Contexte de l'étude.",
                    "",
                    "**Méthodes :** Schéma d'étude et analyse statistique.",
                    "",
                    "**Résultats :** Principaux résultats.",
                    "",
                    "**Conclusion :** Message principal.",
                    ":::",
                    "",
                    "::: {.frontmatter-abstract-en}",
                    "**Background:** Study background.",
                    "",
                    "**Methods:** Study design and statistical analysis.",
                    "",
                    "**Results:** Main findings.",
                    "",
                    "**Conclusion:** Key message.",
                    ":::",
                    "",
                    "::: {.frontmatter-abbreviations}",
                    "| Abréviation | Définition |",
                    "| :--- | :--- |",
                    "| **IC 95 %** | Intervalle de confiance à 95 % |",
                    "| **OR** | Odds Ratio |",
                    ":::",
                    "",
                ]
            )
        )

    if profile_key == "revealjs":
        body_parts.append(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "## Contexte et objectifs",
                    "",
                    "- Premier point clé de la présentation",
                    "- Deuxième point méthodologique",
                    "",
                ]
            )
        )
    else:
        body_parts.append(
            "\n".join(
                [
                    "# Introduction",
                    "",
                    "Présentation du contexte clinique et de l'objectif principal de l'étude.",
                    "",
                    "# Matériel et méthodes",
                    "",
                    "Description de la population d'étude, des critères d'inclusion et des méthodes statistiques.",
                    "",
                    "# Résultats",
                    "",
                ]
            )
        )

    if include_sample_r:
        body_parts.append(
            "\n".join(
                [
                    "```{r}",
                    "#| label: tbl-descriptif",
                    '#| tbl-cap: "Caractéristiques descriptives de l\'échantillon (mtcars)"',
                    "#| echo: false",
                    "knitr::kable(head(mtcars[, 1:5], 5))",
                    "```",
                    "",
                    "```{r}",
                    "#| label: fig-exemple",
                    '#| fig-cap: "Relation entre le poids et la consommation"',
                    "#| echo: false",
                    'if (requireNamespace("ggplot2", quietly = TRUE)) {',
                    "  library(ggplot2)",
                    "  ggplot(mtcars, aes(x = wt, y = mpg, color = factor(cyl))) +",
                    "    geom_point(size = 2.8) +",
                    '    labs(x = "Poids (1000 lbs)", y = "Miles / Gallon", color = "Cylindres") +',
                    "    theme_minimal()",
                    "}",
                    "```",
                    "",
                ]
            )
        )

    if profile_key != "revealjs":
        body_parts.append("# Discussion\n\nInterprétation des résultats et limites de l'étude.\n")

    stream = StringIO()
    yaml_parser.dump(yaml_dict, stream)
    yaml_str = stream.getvalue()
    full_text = f"---\n{yaml_str}---\n\n" + "\n".join(body_parts)

    try:
        target_file.write_text(full_text, encoding="utf-8")
        find_recent_qmd_files.clear()
        return True, f"Document {target_file.name} créé avec succès.", target_file
    except Exception as e:
        return False, f"Erreur lors de la création du fichier : {e}", None


def find_output_file(target_path: Path, ext: str) -> Path:
    """Localise le fichier produit, que output-dir soit défini ou non dans _quarto.yml."""
    candidate = target_path.with_suffix(ext)
    if candidate.exists():
        return candidate
    curr = target_path.parent
    while curr != curr.parent:
        q_yml = curr / "_quarto.yml"
        if q_yml.exists():
            try:
                y = yaml_parser.load(q_yml.read_text(encoding="utf-8"))
                out_dir = y.get("project", {}).get("output-dir", "") if isinstance(y, dict) else ""
                if out_dir:
                    rel = target_path.relative_to(curr)
                    cand = curr / out_dir / rel.with_suffix(ext)
                    if cand.exists():
                        return cand
            except Exception:
                pass
            break
        if (curr / ".git").exists():
            break
        curr = curr.parent
    return candidate


OLLAMA_API_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@st.cache_data(ttl=15)
def get_ollama_models(base_url: str = OLLAMA_API_URL, only_local: bool = True) -> list:
    """Récupère la liste des modèles disponibles sur le serveur Ollama local."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Quarto-Husson-Studio"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_models = data.get("models", [])
            models = []
            for m in raw_models:
                name = m.get("name", "")
                if not name:
                    continue
                if only_local and ("remote_model" in m or "-cloud" in name):
                    continue
                models.append(name)
            return models
    except Exception:
        return []


def extract_error_snippet(log_lines: list, max_lines: int = 40) -> str:
    """Isole les lignes critiques relatives aux erreurs dans le journal de compilation."""
    if not log_lines:
        return ""
    error_indices = []
    for idx, line in enumerate(log_lines):
        lower = line.lower()
        if any(
            marker in lower
            for marker in [
                "! latex error",
                "! package",
                "! undefined control sequence",
                "pandoc error",
                "quarto error",
                "error:",
                "fatal error",
                "stack traceback:",
                "compilation failed",
                "emergency stop",
                "no such file or directory",
            ]
        ):
            error_indices.append(idx)

    if error_indices:
        start = max(0, error_indices[0] - 4)
        end = min(len(log_lines), error_indices[-1] + 10)
        snippet_lines = log_lines[start:end]
        if len(snippet_lines) > max_lines:
            snippet_lines = snippet_lines[-max_lines:]
        return "".join(snippet_lines).strip()

    return "".join(log_lines[-max_lines:]).strip()


def stream_ollama_response(model: str, prompt: str, base_url: str = OLLAMA_API_URL):
    """Générateur de streaming pour la réponse Ollama via /api/generate."""
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.1},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Quarto-Husson-Studio"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            for raw_line in resp:
                if raw_line:
                    try:
                        data = json.loads(raw_line.decode("utf-8"))
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        yield f"Erreur HTTP Ollama ({e.code} : {e.reason}). Vérifiez que le modèle '{model}' est installé localement."
    except Exception as e:
        yield f"Erreur lors de la communication avec Ollama : {e}"


def stream_ollama_chat_response(model: str, messages: list, system_prompt: str = "", base_url: str = OLLAMA_API_URL):
    """Générateur de streaming pour la conversation multi-tours Ollama via /api/chat."""
    url = f"{base_url.rstrip('/')}/api/chat"
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    for m in messages:
        full_messages.append({"role": m["role"], "content": m["content"]})

    payload = json.dumps(
        {
            "model": model,
            "messages": full_messages,
            "stream": True,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Quarto-Husson-Studio"},
    )

    try:
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            for raw_line in resp:
                if raw_line:
                    try:
                        data = json.loads(raw_line.decode("utf-8"))
                        msg_data = data.get("message", {})
                        token = msg_data.get("content", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        yield f"Erreur HTTP Ollama ({e.code} : {e.reason}). Vérifiez que le modèle '{model}' est disponible localement."
    except Exception as e:
        yield f"Erreur lors de la communication avec Ollama : {e}"


def build_chat_system_prompt(target_path: Path, yaml_data: dict, last_comp: dict = None) -> str:
    """Construit un en-tête système contextualisé pour l'assistant Ollama."""
    stream_yaml = StringIO()
    yaml_parser.dump(yaml_data, stream_yaml)
    curr_yaml_str = stream_yaml.getvalue()

    last_error_info = ""
    if last_comp and last_comp.get("return_code", 0) != 0:
        err_snip = extract_error_snippet(last_comp.get("terminal_lines", []))
        last_error_info = f"\nDernière erreur de compilation Quarto survenue :\n```text\n{err_snip}\n```\n"

    return (
        "Tu es l'assistant integre au Studio Quarto Husson, specialise dans la redaction et la compilation de documents Quarto academiques (theses, rapports, memoires, devoirs).\n"
        "Tu maitrises parfaitement Quarto, Pandoc, XeLaTeX, R, KOMA-Script (scrartcl), natbib, Babel (french) et les filtres Lua du template Husson.\n\n"
        f"Document actif : {target_path.name}\n"
        f"Chemin : {target_path}\n"
        f"En-tete YAML actuel du document :\n```yaml\n{curr_yaml_str}\n```\n"
        f"{last_error_info}"
        "\nConsignes de reponse :\n"
        "1. Reponds toujours en francais avec clarte, rigueur et concision technique.\n"
        "2. Fournis directement le code, les blocs YAML ou les commandes LaTeX necessaires.\n"
        "3. Interdiction absolue d'utiliser des emojis dans tes reponses."
    )


FONT_OPTIONS = [
    "Computer Modern (Latex Default)",
    "Times New Roman",
    "Garamond",
    "Roboto",
    "Carlito",
    "Personnalisee...",
]

LOGO_OPTIONS = [
    "Université Paris-Saclay",
    "Université Paris Cité",
    "Aucun logo",
    "Personnalise...",
]

PROFILE_OPTIONS = [
    "Devoir / Rapport de Master",
    "These / Memoire officiel",
    "Rapport Scientifique Sobre",
    "Article / Rapport Web",
    "Presentation / RevealJS",
]

PROFILE_DISPLAY_LABELS = {
    "Devoir / Rapport de Master": "Master",
    "These / Memoire officiel": "Thesis",
    "Rapport Scientifique Sobre": "Report",
    "Article / Rapport Web": "Article",
    "Presentation / RevealJS": "Presentation",
}

PERSISTED_STATE_KEYS = [
    "visible_panels",
    "preview_view_mode",
    "active_editor_tab",
    "sel_preset_profile",
    "opt_pdf",
    "opt_html",
    "opt_docx",
    "opt_reveal",
    "opt_pptx",
    "opt_toc",
    "opt_toc_depth",
    "opt_num_sections",
    "opt_lang",
    "in_title",
    "in_subtitle",
    "in_author",
    "sel_font",
    "custom_font_name",
    "sel_fontsize",
    "sel_linestretch",
    "opt_pagebreak_h1",
    "opt_heading_colors",
    "opt_thesis_active",
    "th_university",
    "th_faculty",
    "th_degree",
    "th_laboratory",
    "th_specialty",
    "th_dept",
    "th_date",
    "sel_logo",
    "custom_logo_path",
    "th_d1_name",
    "th_d1_title",
    "th_d1_role",
    "th_d2_name",
    "th_d2_title",
    "th_d2_role",
    "jury_rows",
    "fm_toc",
    "fm_lof",
    "fm_lot",
    "fm_keywords_fr",
    "fm_keywords_en",
    "fm_abstract_fr",
    "fm_abstract_en",
    "fm_ack",
    "fm_abbrev",
    "opt_colwidths",
    "opt_hyphenation",
    "opt_tableau_fr",
    "opt_br_tags",
    "opt_gt_fit",
    "auto_open",
    "tab_ollama_model",
]

if "visible_panels" not in st.session_state or st.session_state["visible_panels"] is None:
    st.session_state["visible_panels"] = ["Files", "Preview", "Terminal"]

if "preview_view_mode" not in st.session_state or st.session_state["preview_view_mode"] not in ("PDF", "HTML", "RevealJS", "YAML"):
    st.session_state["preview_view_mode"] = "PDF"

if "active_editor_tab" not in st.session_state:
    st.session_state["active_editor_tab"] = "Formats"

for _k in PERSISTED_STATE_KEYS:
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]

if "Files" not in (st.session_state.get("visible_panels") or []):
    st.markdown(
        "<style>section[data-testid='stSidebar'] { display: none !important; }</style>",
        unsafe_allow_html=True,
    )


# --- COMPACT SIDEBAR (NEW & OPEN) ---
st.sidebar.markdown("### Studio")

if "sidebar_mode_val" not in st.session_state or st.session_state["sidebar_mode_val"] not in ("New", "Open"):
    st.session_state["sidebar_mode_val"] = "New"

sidebar_mode = st.sidebar.radio(
    "Mode",
    options=["New", "Open"],
    index=0 if st.session_state.get("sidebar_mode_val") == "New" else 1,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state["sidebar_mode_val"] = sidebar_mode

recent_files = find_recent_qmd_files(str(PROJECTS_BASE_DIR))
default_fallback = str(TEMPLATE_REPO_PATH / "template.qmd")
initial_default_path = recent_files[0] if recent_files else default_fallback

if "active_file_override" in st.session_state and st.session_state["active_file_override"]:
    initial_default_path = st.session_state["active_file_override"]

target_path = None
is_new_mode = sidebar_mode == "New"

if is_new_mode:
    proj_dirs = list_project_directories(str(PROJECTS_BASE_DIR))
    sel_parent_dir = st.sidebar.selectbox(
        "Folder",
        options=["Custom..."] + proj_dirs,
        index=1 if len(proj_dirs) > 0 else 0,
        format_func=lambda p: p if p == "Custom..." else format_display_path(Path(p)),
    )
    if sel_parent_dir == "Custom...":
        custom_parent_dir = st.sidebar.text_input("Directory", value=str(PROJECTS_BASE_DIR))
        base_dest_dir = Path(custom_parent_dir).expanduser()
    else:
        base_dest_dir = Path(sel_parent_dir)

    new_subfolder = st.sidebar.text_input("Subfolder", value="")
    new_filename = st.sidebar.text_input("Filename", value="document.qmd")

    clean_fname = new_filename.strip() or "document.qmd"
    if not clean_fname.endswith(".qmd"):
        clean_fname = f"{clean_fname}.qmd"
    final_dest = (base_dest_dir / new_subfolder.strip()) if new_subfolder.strip() else base_dest_dir
    target_path = final_dest / clean_fname

    yaml_data = {
        "title": "Document Title",
        "author": "Thomas Husson",
        "date": "today",
        "lang": "fr",
        "font": "Times New Roman",
        "format": {
            "husson-pdf": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "fontsize": "11pt",
                "linestretch": 1.15,
            },
            "husson-html": {
                "toc": True,
                "toc-depth": 3,
                "number-sections": True,
                "embed-resources": True,
            },
        },
    }
    markdown_body = ""
    env_ok = True
    env_msg = ""
    is_ready = True
    readiness_reasons = []
    legacy_tweaks = []

else:
    options_files = ["-- Select --"] + recent_files
    def_rec_idx = 0
    if initial_default_path in recent_files:
        def_rec_idx = recent_files.index(initial_default_path) + 1

    def _on_recent_change():
        sel = st.session_state.get("sidebar_recent_select", "")
        if sel and not sel.startswith("--"):
            st.session_state["active_file_override"] = sel
            st.session_state["sidebar_manual_path"] = sel

    def _on_manual_path_change():
        mp = st.session_state.get("sidebar_manual_path", "").strip()
        if mp and Path(mp).expanduser().exists():
            st.session_state["active_file_override"] = str(Path(mp).expanduser().resolve())

    if "sidebar_manual_path" not in st.session_state or not st.session_state["sidebar_manual_path"]:
        st.session_state["sidebar_manual_path"] = initial_default_path

    selected_recent = st.sidebar.selectbox(
        "Recent",
        options=options_files,
        index=def_rec_idx,
        format_func=lambda p: p if p.startswith("--") else f"{Path(p).name}  ({Path(p).parent.name})",
        key="sidebar_recent_select",
        on_change=_on_recent_change,
    )

    manual_path = st.sidebar.text_input(
        "Path",
        key="sidebar_manual_path",
        on_change=_on_manual_path_change,
    )

    with st.sidebar.expander("Import", expanded=False):
        uploaded_file = st.file_uploader("File", type=["qmd"], label_visibility="collapsed")

    if uploaded_file is not None:
        temp_dir = TEMPLATE_REPO_PATH / "scratch"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / uploaded_file.name
        temp_file.write_bytes(uploaded_file.getvalue())
        target_path = temp_file.resolve()
        st.session_state["active_file_override"] = str(target_path)
        st.session_state["sidebar_manual_path"] = str(target_path)
    elif manual_path and Path(manual_path).expanduser().exists():
        target_path = Path(manual_path).expanduser().resolve()
        st.session_state["active_file_override"] = str(target_path)

    if not target_path or not target_path.exists():
        with st.container(border=True):
            st.markdown("#### No file selected")
            st.info("Select a `.qmd` file in the sidebar or switch to **New**.")
        st.stop()

    env_ok, env_msg = ensure_complete_project_environment(target_path)

    yaml_data, markdown_body, err = parse_qmd(target_path)
    if err:
        st.error(err)
        st.stop()

    is_ready, readiness_reasons = check_husson_readiness(yaml_data, target_path)
    legacy_tweaks = inspect_legacy_tweaks(yaml_data, markdown_body)


# --- INITIALISATION DE L'ÉTAT DE SESSION LORS DU CHANGEMENT DE DOCUMENT ---
def init_document_session_state(file_path: Path, y_data: dict, md_body: str):
    cur_title = y_data.get("title", "")
    cur_subtitle = y_data.get("subtitle", "")
    raw_author = y_data.get("author", "Thomas Husson")
    if isinstance(raw_author, list):
        author_items = []
        for a in raw_author:
            if isinstance(a, dict):
                author_items.append(a.get("name", ""))
            else:
                author_items.append(str(a))
        cur_author = ", ".join(filter(None, author_items))
    elif isinstance(raw_author, dict):
        cur_author = raw_author.get("name", "Thomas Husson")
    else:
        cur_author = str(raw_author or "Thomas Husson")

    cur_lang = str(y_data.get("lang", "fr"))
    cur_font = y_data.get("mainfont", y_data.get("font", None))
    cur_fontsize = str(y_data.get("fontsize", ""))
    cur_linestretch = str(y_data.get("linestretch", ""))

    formats_raw = y_data.get("format", {})
    if isinstance(formats_raw, str):
        formats_raw = {formats_raw: {}}
    elif not isinstance(formats_raw, dict):
        formats_raw = {}

    cur_toc = True
    cur_toc_depth = 3
    cur_num_sec = True

    for fkey in ("husson-pdf", "pdf", "husson-html", "html"):
        if fkey in formats_raw and isinstance(formats_raw[fkey], dict):
            fdict = formats_raw[fkey]
            if not cur_font and "mainfont" in fdict:
                cur_font = fdict.get("mainfont")
            if not cur_fontsize and "fontsize" in fdict:
                cur_fontsize = str(fdict["fontsize"])
            if not cur_linestretch and "linestretch" in fdict:
                cur_linestretch = str(fdict["linestretch"])
            if "toc" in fdict and isinstance(fdict["toc"], bool):
                cur_toc = fdict["toc"]
            if "toc-depth" in fdict:
                try:
                    cur_toc_depth = int(fdict["toc-depth"])
                except Exception:
                    pass
            if "number-sections" in fdict and isinstance(fdict["number-sections"], bool):
                cur_num_sec = fdict["number-sections"]

    if not cur_fontsize:
        cur_fontsize = "11pt"
    if not cur_linestretch:
        cur_linestretch = "1.15"

    init_has_pdf = "pdf" in formats_raw or "husson-pdf" in formats_raw
    init_has_html = "html" in formats_raw or "husson-html" in formats_raw
    init_has_docx = "docx" in formats_raw or "husson-docx" in formats_raw
    init_has_reveal = "revealjs" in formats_raw or "husson-revealjs" in formats_raw
    init_has_pptx = "pptx" in formats_raw or "husson-pptx" in formats_raw
    has_any = init_has_pdf or init_has_html or init_has_docx or init_has_reveal or init_has_pptx

    thesis_data = y_data.get("thesis", {})
    init_has_thesis = bool(thesis_data)
    if not isinstance(thesis_data, dict):
        thesis_data = {}

    init_pagebreak_h1 = y_data.get("pagebreak-h1", y_data.get("chapter-pagebreak", init_has_thesis))
    if isinstance(init_pagebreak_h1, str):
        init_pagebreak_h1 = init_pagebreak_h1.strip().lower() in ("true", "yes", "1")
    else:
        init_pagebreak_h1 = bool(init_pagebreak_h1)

    init_heading_colors = y_data.get("heading-colors", True)
    if isinstance(init_heading_colors, str):
        init_heading_colors = init_heading_colors.strip().lower() in ("true", "yes", "1")
    else:
        init_heading_colors = bool(init_heading_colors)

    cur_font_str = str(cur_font).strip() if cur_font else ""
    default_font_idx = 1  # Times New Roman par défaut
    if cur_font_str:
        c_lower = cur_font_str.lower()
        if "computer" in c_lower or "latin modern" in c_lower or "cmu" in c_lower or c_lower == "default":
            default_font_idx = 0
        elif "times" in c_lower:
            default_font_idx = 1
        elif "garamond" in c_lower:
            default_font_idx = 2
        elif "roboto" in c_lower:
            default_font_idx = 3
        elif "carlito" in c_lower or "calibri" in c_lower:
            default_font_idx = 4
        else:
            default_font_idx = 5

    st.session_state.opt_pdf = init_has_pdf if has_any else True
    st.session_state.opt_html = init_has_html
    st.session_state.opt_docx = init_has_docx
    st.session_state.opt_reveal = init_has_reveal
    st.session_state.opt_pptx = init_has_pptx
    st.session_state.opt_toc = cur_toc
    st.session_state.opt_toc_depth = max(1, min(5, cur_toc_depth))
    st.session_state.opt_num_sections = cur_num_sec
    st.session_state.opt_lang = "en" if cur_lang == "en" else "fr"

    st.session_state.in_title = str(cur_title)
    st.session_state.in_subtitle = str(cur_subtitle)
    st.session_state.in_author = str(cur_author)
    st.session_state.sel_font = FONT_OPTIONS[default_font_idx]
    st.session_state.custom_font_name = cur_font_str if default_font_idx == 5 else ""
    st.session_state.sel_fontsize = cur_fontsize if cur_fontsize in ["10pt", "11pt", "12pt"] else "11pt"
    st.session_state.sel_linestretch = cur_linestretch if cur_linestretch in ["1.0", "1.15", "1.25", "1.5"] else "1.15"
    st.session_state.opt_pagebreak_h1 = init_pagebreak_h1
    st.session_state.opt_heading_colors = init_heading_colors

    st.session_state.opt_thesis_active = init_has_thesis
    st.session_state.th_university = str(thesis_data.get("university") or "Université Paris-Saclay")
    st.session_state.th_faculty = str(thesis_data.get("faculty") or "Faculté de Médecine")
    st.session_state.th_degree = str(
        thesis_data.get("degree") or "Master 2 -- Santé Publique & Méthodologie de la Recherche"
    )
    st.session_state.th_laboratory = str(thesis_data.get("laboratory") or "")
    st.session_state.th_specialty = str(thesis_data.get("specialty") or "UE Épidémiologie")
    st.session_state.th_dept = str(thesis_data.get("department") or "")
    st.session_state.th_date = str(thesis_data.get("date") or "Année universitaire 2025-2026")

    cur_logo = str(thesis_data.get("logo", "logo-universite-paris-saclay.png"))
    if "paris-saclay" in cur_logo.lower():
        st.session_state.sel_logo = LOGO_OPTIONS[0]
        st.session_state.custom_logo_path = ""
    elif "paris-cite" in cur_logo.lower():
        st.session_state.sel_logo = LOGO_OPTIONS[1]
        st.session_state.custom_logo_path = ""
    elif not cur_logo:
        st.session_state.sel_logo = LOGO_OPTIONS[2]
        st.session_state.custom_logo_path = ""
    else:
        st.session_state.sel_logo = LOGO_OPTIONS[3]
        st.session_state.custom_logo_path = cur_logo

    directors_list = thesis_data.get("directors", [])
    if not isinstance(directors_list, list):
        directors_list = []
    d1 = directors_list[0] if len(directors_list) > 0 else {}
    d2 = directors_list[1] if len(directors_list) > 1 else {}
    st.session_state.th_d1_name = d1.get("name", "") if isinstance(d1, dict) else str(d1 or "")
    st.session_state.th_d1_title = d1.get("title", "") if isinstance(d1, dict) else ""
    st.session_state.th_d1_role = d1.get("role", "Directeur de thèse") if isinstance(d1, dict) else "Directeur de thèse"
    st.session_state.th_d2_name = d2.get("name", "") if isinstance(d2, dict) else str(d2 or "")
    st.session_state.th_d2_title = d2.get("title", "") if isinstance(d2, dict) else ""
    st.session_state.th_d2_role = d2.get("role", "Co-directeur de thèse") if isinstance(d2, dict) else "Co-directeur de thèse"

    jury_list = thesis_data.get("jury", [])
    parsed_jury = []
    if isinstance(jury_list, list):
        for item in jury_list:
            if isinstance(item, dict):
                parsed_jury.append(
                    {
                        "name": str(item.get("name", "")),
                        "title": str(item.get("title", "")),
                        "role": str(item.get("role", "")),
                    }
                )
            elif item:
                parsed_jury.append({"name": str(item), "title": "", "role": ""})
    st.session_state.jury_rows = parsed_jury

    fm_data = y_data.get("frontmatter", {})
    if not isinstance(fm_data, dict):
        fm_data = {}
    st.session_state.fm_toc = bool(fm_data.get("table-of-contents", False))
    st.session_state.fm_lof = bool(fm_data.get("list-of-figures", False))
    st.session_state.fm_lot = bool(fm_data.get("list-of-tables", False))

    kw_fr = fm_data.get("keywords", [])
    st.session_state.fm_keywords_fr = ", ".join(str(x) for x in kw_fr) if isinstance(kw_fr, list) else str(kw_fr or "")
    kw_en = fm_data.get("keywords-en", [])
    st.session_state.fm_keywords_en = ", ".join(str(x) for x in kw_en) if isinstance(kw_en, list) else str(kw_en or "")

    st.session_state.fm_abstract_fr = str(fm_data.get("summary") or fm_data.get("abstract") or "")
    st.session_state.fm_abstract_en = str(fm_data.get("abstract-en") or "")
    st.session_state.fm_ack = str(fm_data.get("acknowledgements") or "")
    raw_abbrevs = fm_data.get("abbreviations")
    if isinstance(raw_abbrevs, list):
        abbr_lines = []
        for ab in raw_abbrevs:
            if isinstance(ab, dict) and ab.get("term"):
                abbr_lines.append(f"{ab.get('term')}: {ab.get('definition', '')}")
            elif ab:
                abbr_lines.append(str(ab))
        st.session_state.fm_abbrev = "\n".join(abbr_lines)
    else:
        st.session_state.fm_abbrev = str(raw_abbrevs or "")

    st.session_state.opt_colwidths = True
    st.session_state.opt_hyphenation = True
    st.session_state.opt_tableau_fr = st.session_state.opt_lang == "fr"
    st.session_state.opt_br_tags = True
    st.session_state.opt_gt_fit = False
    if "auto_open" not in st.session_state:
        st.session_state.auto_open = True

    if init_has_reveal and not init_has_pdf:
        st.session_state.sel_preset_profile = "Presentation / RevealJS"
        st.session_state.preview_view_mode = "RevealJS"
    elif init_has_thesis:
        if default_font_idx == 0:
            st.session_state.sel_preset_profile = "Devoir / Rapport de Master"
        else:
            st.session_state.sel_preset_profile = "These / Memoire officiel"
        st.session_state.preview_view_mode = "PDF"
    elif init_has_html:
        st.session_state.sel_preset_profile = "Article / Rapport Web"
        st.session_state.preview_view_mode = "PDF" if init_has_pdf else "HTML"
    elif default_font_idx == 0:
        st.session_state.sel_preset_profile = "Rapport Scientifique Sobre"
        st.session_state.preview_view_mode = "PDF"
    else:
        st.session_state.sel_preset_profile = "Article / Rapport Web"
        st.session_state.preview_view_mode = "PDF"


file_key = "__NEW_DOCUMENT__" if is_new_mode else str(target_path)
if "current_loaded_file" not in st.session_state or st.session_state.current_loaded_file != file_key:
    st.session_state.current_loaded_file = file_key
    init_document_session_state(target_path, yaml_data, markdown_body)
    st.session_state.pop("last_compilation", None)
    st.session_state.pop("last_diagnosis", None)


# --- FONCTION DE CONSTRUCTION DU YAML MIS À JOUR ---
def build_updated_yaml() -> dict:
    d = dict(yaml_data)
    d["title"] = st.session_state.in_title
    if st.session_state.in_subtitle.strip():
        d["subtitle"] = st.session_state.in_subtitle.strip()
    elif "subtitle" in d:
        del d["subtitle"]

    raw_author = yaml_data.get("author", "Thomas Husson")
    if isinstance(raw_author, list):
        orig_author_str = ", ".join(
            filter(None, [a.get("name", "") if isinstance(a, dict) else str(a) for a in raw_author])
        )
    elif isinstance(raw_author, dict):
        orig_author_str = raw_author.get("name", "Thomas Husson")
    else:
        orig_author_str = str(raw_author or "Thomas Husson")

    if st.session_state.in_author.strip() == orig_author_str.strip() and isinstance(raw_author, (list, dict)):
        d["author"] = raw_author
    else:
        d["author"] = st.session_state.in_author.strip()

    d["lang"] = st.session_state.opt_lang

    font_meta = None
    if st.session_state.sel_font == "Computer Modern (Latex Default)":
        font_meta = "Computer Modern"
    elif st.session_state.sel_font == "Personnalisee...":
        custom = st.session_state.get("custom_font_name", "").strip()
        font_meta = custom if custom else None
    else:
        font_meta = st.session_state.sel_font

    if font_meta:
        d["font"] = font_meta
    elif "font" in d:
        del d["font"]

    if "mainfont" in d:
        del d["mainfont"]

    if bool(st.session_state.get("opt_pagebreak_h1")) != bool(st.session_state.get("opt_thesis_active")):
        d["pagebreak-h1"] = bool(st.session_state.get("opt_pagebreak_h1"))
    elif "pagebreak-h1" in d:
        del d["pagebreak-h1"]

    if st.session_state.get("opt_heading_colors"):
        d["heading-colors"] = True
    else:
        d["heading-colors"] = False

    if st.session_state.opt_lang == "fr" and st.session_state.opt_tableau_fr:
        if "language" not in d or not isinstance(d["language"], dict):
            d["language"] = {}
        d["language"]["fr"] = {
            "crossref-tbl-title": "Tableau",
            "crossref-tbl-prefix": "Tableau",
            "crossref-lot-title": "Liste des tableaux",
        }

    if "format" not in d or not isinstance(d["format"], dict):
        d["format"] = {}

    opt_toc = bool(st.session_state.opt_toc)
    opt_toc_depth = int(st.session_state.opt_toc_depth)
    opt_num_sections = bool(st.session_state.opt_num_sections)

    if st.session_state.opt_pdf:
        existing_pdf = {}
        if "husson-pdf" in d["format"] and isinstance(d["format"]["husson-pdf"], dict):
            existing_pdf = dict(d["format"]["husson-pdf"])
        elif "pdf" in d["format"] and isinstance(d["format"]["pdf"], dict):
            existing_pdf = dict(d["format"]["pdf"])

        existing_pdf["toc"] = False if st.session_state.get("fm_toc") else opt_toc
        existing_pdf["toc-depth"] = opt_toc_depth
        existing_pdf["number-sections"] = opt_num_sections
        existing_pdf["fontsize"] = st.session_state.sel_fontsize
        existing_pdf["linestretch"] = float(st.session_state.sel_linestretch)

        partials = [p for p in existing_pdf.get("template-partials", []) if "husson" not in str(p)]
        if partials:
            existing_pdf["template-partials"] = partials
        elif "template-partials" in existing_pdf:
            del existing_pdf["template-partials"]

        raw_headers = existing_pdf.get("include-in-header", [])
        if isinstance(raw_headers, list):
            headers = [h for h in raw_headers if "pdf-header.tex" not in str(h)]
            if headers:
                existing_pdf["include-in-header"] = headers
            elif "include-in-header" in existing_pdf:
                del existing_pdf["include-in-header"]

        flts = [f for f in existing_pdf.get("filters", []) if "husson" not in str(f)]
        if flts:
            existing_pdf["filters"] = flts
        elif "filters" in existing_pdf:
            del existing_pdf["filters"]

        if "mainfont" in existing_pdf:
            del existing_pdf["mainfont"]

        d["format"]["husson-pdf"] = existing_pdf
        if "pdf" in d["format"]:
            del d["format"]["pdf"]
    else:
        d["format"].pop("husson-pdf", None)
        d["format"].pop("pdf", None)

    if st.session_state.opt_html:
        existing_html = {}
        if "husson-html" in d["format"] and isinstance(d["format"]["husson-html"], dict):
            existing_html = dict(d["format"]["husson-html"])
        elif "html" in d["format"] and isinstance(d["format"]["html"], dict):
            existing_html = dict(d["format"]["html"])

        existing_html["toc"] = opt_toc
        existing_html["toc-depth"] = opt_toc_depth
        existing_html["number-sections"] = opt_num_sections
        if existing_html.get("theme") == "cosmo":
            del existing_html["theme"]
        existing_html["embed-resources"] = True

        d["format"]["husson-html"] = existing_html
        if "html" in d["format"]:
            del d["format"]["html"]
    else:
        d["format"].pop("husson-html", None)
        d["format"].pop("html", None)

    if st.session_state.opt_docx:
        existing_docx = {}
        if "husson-docx" in d["format"] and isinstance(d["format"]["husson-docx"], dict):
            existing_docx = dict(d["format"]["husson-docx"])
        elif "docx" in d["format"] and isinstance(d["format"]["docx"], dict):
            existing_docx = dict(d["format"]["docx"])
        existing_docx["toc"] = opt_toc
        existing_docx["toc-depth"] = opt_toc_depth
        existing_docx["number-sections"] = opt_num_sections
        d["format"]["husson-docx"] = existing_docx
        if "docx" in d["format"]:
            del d["format"]["docx"]
    else:
        d["format"].pop("husson-docx", None)
        d["format"].pop("docx", None)

    if st.session_state.opt_reveal:
        existing_reveal = {}
        if "husson-revealjs" in d["format"] and isinstance(d["format"]["husson-revealjs"], dict):
            existing_reveal = dict(d["format"]["husson-revealjs"])
        elif "revealjs" in d["format"] and isinstance(d["format"]["revealjs"], dict):
            existing_reveal = dict(d["format"]["revealjs"])
        existing_reveal["slide-number"] = True
        existing_reveal["transition"] = "none"
        existing_reveal["embed-resources"] = True
        d["format"]["husson-revealjs"] = existing_reveal
        if "revealjs" in d["format"]:
            del d["format"]["revealjs"]
    else:
        d["format"].pop("husson-revealjs", None)
        d["format"].pop("revealjs", None)

    if st.session_state.opt_pptx:
        existing_pptx = d["format"].get("husson-pptx", d["format"].get("pptx", "default"))
        d["format"]["husson-pptx"] = existing_pptx
        d["format"].pop("pptx", None)
    else:
        d["format"].pop("husson-pptx", None)
        d["format"].pop("pptx", None)

    ordered_formats = {}
    if st.session_state.opt_pdf and "husson-pdf" in d["format"]:
        ordered_formats["husson-pdf"] = d["format"]["husson-pdf"]
    if st.session_state.opt_html and "husson-html" in d["format"]:
        ordered_formats["husson-html"] = d["format"]["husson-html"]
    if st.session_state.opt_docx and "husson-docx" in d["format"]:
        ordered_formats["husson-docx"] = d["format"]["husson-docx"]
    if st.session_state.opt_reveal and "husson-revealjs" in d["format"]:
        ordered_formats["husson-revealjs"] = d["format"]["husson-revealjs"]
    if st.session_state.opt_pptx and "husson-pptx" in d["format"]:
        ordered_formats["husson-pptx"] = d["format"]["husson-pptx"]
    for k, v in d["format"].items():
        if k not in ordered_formats:
            ordered_formats[k] = v
    d["format"] = ordered_formats

    if st.session_state.opt_thesis_active:
        thesis_dict = dict(yaml_data.get("thesis", {})) if isinstance(yaml_data.get("thesis"), dict) else {}

        resolved_logo = None
        sel_logo = st.session_state.sel_logo
        custom_logo_path = st.session_state.custom_logo_path
        if "paris-saclay" in sel_logo.lower():
            resolved_logo = "logo-universite-paris-saclay.png"
        elif "paris" in sel_logo.lower() and ("cit" in sel_logo.lower()):
            resolved_logo = "logo-universite-paris-cite.png"
        elif sel_logo == "Personnalise..." and custom_logo_path.strip():
            resolved_logo = custom_logo_path.strip()

        if st.session_state.th_university.strip():
            thesis_dict["university"] = st.session_state.th_university
        if st.session_state.th_faculty.strip():
            thesis_dict["faculty"] = st.session_state.th_faculty
        if st.session_state.th_degree.strip():
            thesis_dict["degree"] = st.session_state.th_degree
        if st.session_state.th_laboratory.strip():
            thesis_dict["laboratory"] = st.session_state.th_laboratory.strip()
        elif "laboratory" in thesis_dict:
            del thesis_dict["laboratory"]
        if st.session_state.th_specialty.strip():
            thesis_dict["specialty"] = st.session_state.th_specialty.strip()
        if st.session_state.th_dept.strip():
            thesis_dict["department"] = st.session_state.th_dept.strip()
        if st.session_state.th_date.strip():
            thesis_dict["date"] = st.session_state.th_date.strip()
        if resolved_logo:
            thesis_dict["logo"] = resolved_logo
        elif sel_logo == "Aucun logo" and "logo" in thesis_dict:
            del thesis_dict["logo"]

        existing_directors = thesis_dict.get("directors", [])
        if not isinstance(existing_directors, list):
            existing_directors = []
        updated_directors = list(existing_directors)

        new_d1 = None
        if st.session_state.th_d1_name.strip():
            new_d1 = {
                "name": st.session_state.th_d1_name.strip(),
                "title": st.session_state.th_d1_title.strip(),
                "role": st.session_state.th_d1_role.strip() or "Directeur de thèse",
            }
        new_d2 = None
        if st.session_state.th_d2_name.strip():
            new_d2 = {
                "name": st.session_state.th_d2_name.strip(),
                "title": st.session_state.th_d2_title.strip(),
                "role": st.session_state.th_d2_role.strip() or "Co-directeur de thèse",
            }

        if new_d1:
            if len(updated_directors) > 0:
                updated_directors[0] = new_d1
            else:
                updated_directors.append(new_d1)
        elif len(updated_directors) == 1 and not new_d2:
            updated_directors = []

        if new_d2:
            if len(updated_directors) > 1:
                updated_directors[1] = new_d2
            else:
                updated_directors.append(new_d2)

        if updated_directors:
            thesis_dict["directors"] = updated_directors
        elif "directors" in thesis_dict:
            del thesis_dict["directors"]

        clean_jury = []
        for row in st.session_state.get("jury_rows", []):
            if isinstance(row, dict) and str(row.get("name", "")).strip():
                j_entry = {"name": str(row.get("name", "")).strip()}
                if str(row.get("title", "")).strip():
                    j_entry["title"] = str(row.get("title", "")).strip()
                if str(row.get("role", "")).strip():
                    j_entry["role"] = str(row.get("role", "")).strip()
                clean_jury.append(j_entry)
        if clean_jury:
            thesis_dict["jury"] = clean_jury
        elif "jury" in thesis_dict:
            del thesis_dict["jury"]

        d["thesis"] = thesis_dict
    elif "thesis" in d:
        del d["thesis"]

    fm_existing = dict(yaml_data.get("frontmatter", {})) if isinstance(yaml_data.get("frontmatter"), dict) else {}
    if st.session_state.get("fm_toc"):
        fm_existing["table-of-contents"] = True
    else:
        fm_existing.pop("table-of-contents", None)

    if st.session_state.get("fm_lof"):
        fm_existing["list-of-figures"] = True
    else:
        fm_existing.pop("list-of-figures", None)

    if st.session_state.get("fm_lot"):
        fm_existing["list-of-tables"] = True
    else:
        fm_existing.pop("list-of-tables", None)

    kw_fr_list = [k.strip() for k in st.session_state.get("fm_keywords_fr", "").split(",") if k.strip()]
    if kw_fr_list:
        fm_existing["keywords"] = kw_fr_list
    else:
        fm_existing.pop("keywords", None)

    kw_en_list = [k.strip() for k in st.session_state.get("fm_keywords_en", "").split(",") if k.strip()]
    if kw_en_list:
        fm_existing["keywords-en"] = kw_en_list
    else:
        fm_existing.pop("keywords-en", None)

    val_sum = st.session_state.get("fm_abstract_fr", "").strip()
    if val_sum:
        fm_existing["summary"] = val_sum
        fm_existing.pop("abstract", None)
    else:
        fm_existing.pop("summary", None)
        fm_existing.pop("abstract", None)

    val_abs_en = st.session_state.get("fm_abstract_en", "").strip()
    if val_abs_en:
        fm_existing["abstract-en"] = val_abs_en
    else:
        fm_existing.pop("abstract-en", None)

    val_ack = st.session_state.get("fm_ack", "").strip()
    if val_ack:
        fm_existing["acknowledgements"] = val_ack
    else:
        fm_existing.pop("acknowledgements", None)

    val_abbrev = st.session_state.get("fm_abbrev", "").strip()
    if val_abbrev:
        parsed_abbr = []
        for line in val_abbrev.splitlines():
            s = line.strip()
            if not s or s.startswith("| :---") or s.startswith("| Abréviation"):
                continue
            if s.startswith("|") and s.endswith("|"):
                parts = [p.strip().strip("*").strip() for p in s.strip("|").split("|")]
                if len(parts) >= 2 and parts[0]:
                    parsed_abbr.append({"term": parts[0], "definition": parts[1]})
            elif ":" in s:
                t, dfn = s.split(":", 1)
                parsed_abbr.append({"term": t.strip(), "definition": dfn.strip()})
            elif " - " in s:
                t, dfn = s.split(" - ", 1)
                parsed_abbr.append({"term": t.strip(), "definition": dfn.strip()})
            else:
                parsed_abbr.append({"term": s, "definition": ""})
        if parsed_abbr:
            fm_existing["abbreviations"] = parsed_abbr
        else:
            fm_existing.pop("abbreviations", None)
    else:
        fm_existing.pop("abbreviations", None)

    if fm_existing:
        d["frontmatter"] = fm_existing
    elif "frontmatter" in d:
        del d["frontmatter"]

    return d


def apply_selected_preset():
    """Applies the selected preset immediately to the UI state and queues a native Quarto preview."""
    selected_profile = st.session_state.get("sel_preset_profile", "")
    st.session_state["auto_trigger_preview"] = True
    if selected_profile == "Devoir / Rapport de Master":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.opt_pptx = False
        st.session_state.sel_font = "Computer Modern (Latex Default)"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = True
        st.session_state.opt_pagebreak_h1 = True
        st.session_state.fm_toc = False
        st.session_state.fm_lof = False
        st.session_state.fm_lot = False
        st.session_state.preview_view_mode = "PDF"
    elif selected_profile == "These / Memoire officiel":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.opt_pptx = False
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = True
        st.session_state.opt_pagebreak_h1 = True
        st.session_state.fm_toc = True
        st.session_state.fm_lof = True
        st.session_state.fm_lot = True
        if not st.session_state.get("th_d1_name", "").strip():
            st.session_state.th_d1_name = "Membre 2"
            st.session_state.th_d1_title = "PU-PH, Hôpital 1"
            st.session_state.th_d1_role = "Directeur de thèse"
        if not st.session_state.get("jury_rows"):
            st.session_state.jury_rows = [
                {"name": "Membre 1", "title": "Hôpital 1, Université 1", "role": "Président du jury"},
                {"name": "Membre 2", "title": "Hôpital 1, Université 1", "role": "Directeur de thèse"},
                {"name": "Membre 3", "title": "Hôpital 2, Université 2", "role": "Rapporteur"},
            ]
        if not st.session_state.get("fm_abstract_fr", "").strip():
            st.session_state.fm_abstract_fr = (
                "Ce document présente la structure complète du mode thèse du template Quarto (husson-pdf) "
                "appliquée au jeu de données mtcars (32 véhicules, 11 variables)."
            )
        if not st.session_state.get("fm_ack", "").strip():
            st.session_state.fm_ack = "Remerciements aux membres du jury et à l'équipe d'encadrement."
        if not st.session_state.get("fm_abbrev", "").strip():
            st.session_state.fm_abbrev = "MPG: Miles per gallon\nWT: Weight (1000 lbs)\nOLS: Ordinary Least Squares"
        st.session_state.preview_view_mode = "PDF"
    elif selected_profile == "Rapport Scientifique Sobre":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.opt_pptx = False
        st.session_state.sel_font = "Computer Modern (Latex Default)"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False
        st.session_state.fm_toc = False
        st.session_state.fm_lof = False
        st.session_state.fm_lot = False
        st.session_state.preview_view_mode = "PDF"
    elif selected_profile == "Article / Rapport Web":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = True
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.opt_pptx = False
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False
        st.session_state.fm_toc = False
        st.session_state.fm_lof = False
        st.session_state.fm_lot = False
        st.session_state.preview_view_mode = "PDF"
    elif selected_profile == "Presentation / RevealJS":
        st.session_state.opt_pdf = False
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = True
        st.session_state.opt_pptx = False
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False
        st.session_state.preview_view_mode = "RevealJS"


# --- NATIVE QUARTO PREVIEW HELPER FUNCTIONS ---
def ensure_live_preview_workspace() -> Path:
    """Ensure scratch/live_preview has its own isolated _quarto.yml (freeze: auto) and _extensions/husson."""
    preview_dir = REPO_ROOT / "scratch" / "live_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    quarto_yml = preview_dir / "_quarto.yml"
    expected_yml = (
        "project:\n"
        "  type: default\n\n"
        "execute:\n"
        "  freeze: auto\n"
        "  warning: false\n"
        "  message: false\n"
    )
    if not quarto_yml.exists() or quarto_yml.read_text(encoding="utf-8", errors="ignore") != expected_yml:
        quarto_yml.write_text(expected_yml, encoding="utf-8")
    ensure_complete_project_environment(preview_dir / "preview.qmd")
    return preview_dir


@st.cache_data(show_spinner=False)
def render_pdf_to_png_data_uris(pdf_path_str: str, mtime: float, max_pages: int = 30) -> list[str]:
    """Convert native Quarto PDF pages to high-DPI PNG data URIs via pdftoppm for in-app viewing."""
    pdftoppm_bin = shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"
    if not Path(pdftoppm_bin).exists():
        return []
    uris: list[str] = []
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = str(Path(tmpdir) / "page")
            subprocess.run(
                [pdftoppm_bin, "-png", "-r", "150", "-l", str(max_pages), pdf_path_str, out_prefix],
                capture_output=True,
                timeout=30,
                check=False,
            )
            page_files = sorted(Path(tmpdir).glob("page-*.png"))
            for pf in page_files:
                b64 = base64.b64encode(pf.read_bytes()).decode("ascii")
                uris.append(f"data:image/png;base64,{b64}")
    except Exception:
        return []
    return uris


def build_pdf_viewer_html(page_uris: list[str], doc_name: str, elapsed_str: str = "") -> str:
    """Build a compact scrollable/zoomable multi-page native PDF viewer from rendered PNG data URIs."""
    total_pages = len(page_uris)
    pages_html = []
    for idx, uri in enumerate(page_uris, start=1):
        pages_html.append(
            f"""
            <div class="pdf-page-wrap" id="qpage-{idx}">
                <div class="pdf-page-badge">{idx}/{total_pages}</div>
                <img src="{uri}" class="pdf-page-img" alt="Page {idx}" loading="lazy" />
            </div>
            """
        )
    pages_joined = "\n".join(pages_html)
    meta_badge = f"{html.escape(elapsed_str)}" if elapsed_str else "XeLaTeX"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
    background: #EAEEF3;
    color: #242932;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .viewer-bar {{
    background: #FFFFFF;
    border-bottom: 1px solid #E2E5EA;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 10.5px;
    color: #687281;
    flex-shrink: 0;
  }}
  .viewer-bar-left {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #242932;
  }}
  .viewer-pill {{
    background: #EEF3F8;
    color: #426B91;
    border: 1px solid #C9D8E8;
    border-radius: 4px;
    padding: 0px 5px;
    font-size: 9.5px;
    font-weight: 600;
  }}
  .viewer-controls {{
    display: flex;
    align-items: center;
    gap: 3px;
  }}
  .z-btn {{
    background: #F6F7F9;
    border: 1px solid #D5DAE1;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10px;
    font-weight: 500;
    color: #242932;
    cursor: pointer;
  }}
  .z-btn:hover {{
    border-color: #426B91;
    color: #426B91;
  }}
  .canvas-scroll {{
    flex: 1;
    overflow-y: auto;
    padding: 5px 6px 10px 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }}
  .pdf-page-wrap {{
    position: relative;
    width: var(--page-width, 68%);
    max-width: 340px;
    background: #FFFFFF;
    border-radius: 3px;
    box-shadow: 0 1px 6px rgba(15, 23, 42, 0.10), 0 0 1px rgba(15, 23, 42, 0.16);
    transition: width 0.12s ease;
  }}
  .pdf-page-badge {{
    position: absolute;
    top: 4px;
    right: 4px;
    background: rgba(36, 41, 50, 0.68);
    color: #FFFFFF;
    font-size: 9px;
    font-weight: 500;
    padding: 1px 5px;
    border-radius: 3px;
    pointer-events: none;
  }}
  .pdf-page-img {{
    display: block;
    width: 100%;
    height: auto;
    border-radius: 3px;
  }}
</style>
</head>
<body>
  <div class="viewer-bar">
    <div class="viewer-bar-left">
      <span>{html.escape(doc_name)}</span>
      <span class="viewer-pill">{total_pages}p</span>
      <span style="font-weight:400;color:#687281;">{meta_badge}</span>
    </div>
    <div class="viewer-controls">
      <button class="z-btn" onclick="setZoom('55%')">55%</button>
      <button class="z-btn" onclick="setZoom('68%')">70%</button>
      <button class="z-btn" onclick="setZoom('85%')">85%</button>
      <button class="z-btn" onclick="setZoom('98%')">100%</button>
    </div>
  </div>
  <div class="canvas-scroll" id="pdfCanvas">
    {pages_joined}
  </div>
  <script>
    function setZoom(w) {{
      document.getElementById('pdfCanvas').style.setProperty('--page-width', w);
    }}
  </script>
</body>
</html>"""


# --- ENSURE PANELS OPEN AUTOMATICALLY WHEN PREVIEW OR RENDER IS CLICKED ---
if st.session_state.get("btn_top_quick_preview") or st.session_state.get("btn_panel_quick_preview"):
    vp = list(st.session_state.get("visible_panels", ["Files", "Preview", "Terminal"]))
    if "Preview" not in vp:
        vp.append("Preview")
    if "Terminal" not in vp:
        vp.append("Terminal")
    st.session_state["visible_panels"] = vp
    if st.session_state.get("preview_view_mode") == "YAML":
        if st.session_state.get("opt_reveal") and not st.session_state.get("opt_pdf"):
            st.session_state["preview_view_mode"] = "RevealJS"
        elif st.session_state.get("opt_html") and not st.session_state.get("opt_pdf"):
            st.session_state["preview_view_mode"] = "HTML"
        else:
            st.session_state["preview_view_mode"] = "PDF"
elif st.session_state.get("btn_top_render"):
    vp = list(st.session_state.get("visible_panels", ["Files", "Preview", "Terminal"]))
    if "Terminal" not in vp:
        vp.append("Terminal")
    st.session_state["visible_panels"] = vp
    if st.session_state.get("preview_view_mode") == "YAML":
        if st.session_state.get("opt_reveal") and not st.session_state.get("opt_pdf"):
            st.session_state["preview_view_mode"] = "RevealJS"
        elif st.session_state.get("opt_html") and not st.session_state.get("opt_pdf"):
            st.session_state["preview_view_mode"] = "HTML"
        else:
            st.session_state["preview_view_mode"] = "PDF"


# --- 3-PANEL HORIZONTAL WORKSPACE + DOCKED TERMINAL (ZERO SCROLL) ---
if "status_toast" in st.session_state and st.session_state["status_toast"]:
    st.success(st.session_state.pop("status_toast"))

show_preview_panel = "Preview" in st.session_state.get("visible_panels", ["Files", "Preview", "Terminal"])
show_terminal_panel = "Terminal" in st.session_state.get("visible_panels", ["Files", "Preview", "Terminal"])

if show_preview_panel:
    col_mid, col_right = st.columns([6.2, 3.8], gap="small")
else:
    col_mid = st.container()
    col_right = None

btn_create_file = False
btn_save = False
btn_render = False
btn_quick_preview = False
btn_panel_preview = False


# ==============================================================================
# MIDDLE PANEL: TINY PANEL TOGGLES + UNIFIED HEADER + COMPACT EDITOR
# ==============================================================================
with col_mid:
    if show_preview_panel:
        st.pills(
            "Panels",
            options=["Files", "Preview", "Terminal"],
            selection_mode="multi",
            label_visibility="collapsed",
            key="visible_panels",
        )
    else:
        top_bar_c1, top_bar_c2 = st.columns([8.2, 1.8], gap="small", vertical_alignment="center")
        with top_bar_c1:
            st.pills(
                "Panels",
                options=["Files", "Preview", "Terminal"],
                selection_mode="multi",
                label_visibility="collapsed",
                key="visible_panels",
            )
        with top_bar_c2:
            btn_quick_preview = st.button(
                "Preview",
                use_container_width=True,
                key="btn_top_quick_preview",
            )

    active_formats_badges = []
    if st.session_state.opt_pdf:
        active_formats_badges.append('<span class="husson-badge">pdf</span>')
    if st.session_state.opt_html:
        active_formats_badges.append('<span class="husson-badge">html</span>')
    if st.session_state.opt_docx:
        active_formats_badges.append('<span class="husson-badge">docx</span>')
    if st.session_state.opt_reveal:
        active_formats_badges.append('<span class="husson-badge">revealjs</span>')
    if st.session_state.opt_pptx:
        active_formats_badges.append('<span class="husson-badge">pptx</span>')

    if is_new_mode:
        status_badge_html = '<span class="husson-badge husson-badge-ok">New</span>'
    elif is_ready and env_ok:
        status_badge_html = '<span class="husson-badge husson-badge-ok">Ready</span>'
    else:
        status_badge_html = '<span class="husson-badge husson-badge-warn">Native</span>'

    # Surface 1: Non-overlapping Compact Document Header, Preset Selector & Small Actions
    with st.container(border=True, key="surface_header"):
        needs_conversion_btn = (not is_new_mode) and ((not is_ready) or bool(legacy_tweaks))
        badges_str = "".join(active_formats_badges)
        short_parent = format_display_path(target_path.parent)
        doc_header_html = f"""
        <div class="husson-doc-header">
            <div class="husson-doc-title-row">
                <span class="husson-doc-title">{target_path.name}</span>
                {status_badge_html}
                {badges_str}
            </div>
            <div class="husson-doc-path" title="{target_path.parent}">{short_parent}</div>
        </div>
        """

        if is_new_mode:
            hd_r1_left, hd_r1_right = st.columns([8.1, 1.9], gap="small", vertical_alignment="center")
            with hd_r1_left:
                st.markdown(doc_header_html, unsafe_allow_html=True)
            with hd_r1_right:
                btn_create_file = st.button("Create", type="primary", use_container_width=True, key="btn_top_create")
        elif needs_conversion_btn:
            hd_r1_left, hd_b1, hd_b2, hd_b3 = st.columns([5.5, 1.5, 1.5, 1.5], gap="small", vertical_alignment="center")
            with hd_r1_left:
                st.markdown(doc_header_html, unsafe_allow_html=True)
            with hd_b1:
                if st.button("Convert", use_container_width=True, key="btn_activate_husson"):
                    conv_ok, conv_msg, conv_bpath, yaml_data = auto_configure_husson_document(
                        target_path, yaml_data, markdown_body, clean_body=True
                    )
                    if conv_ok:
                        st.session_state.current_loaded_file = ""
                        st.session_state["status_toast"] = f"Converted: {target_path.name}"
                        st.rerun()
                    else:
                        st.warning(conv_msg)
            with hd_b2:
                btn_save = st.button("Save", use_container_width=True, key="btn_top_save")
            with hd_b3:
                btn_render = st.button("Render", type="primary", use_container_width=True, key="btn_top_render")
        else:
            hd_r1_left, hd_b1, hd_b2 = st.columns([6.8, 1.6, 1.6], gap="small", vertical_alignment="center")
            with hd_r1_left:
                st.markdown(doc_header_html, unsafe_allow_html=True)
            with hd_b1:
                btn_save = st.button("Save", use_container_width=True, key="btn_top_save")
            with hd_b2:
                btn_render = st.button("Render", type="primary", use_container_width=True, key="btn_top_render")

        hd_r2_left, hd_r2_right = st.columns([7.2, 2.8], gap="small", vertical_alignment="center")
        with hd_r2_left:
            selected_profile = st.selectbox(
                "Preset",
                options=PROFILE_OPTIONS,
                format_func=lambda k: PROFILE_DISPLAY_LABELS.get(k, k),
                label_visibility="collapsed",
                key="sel_preset_profile",
                on_change=apply_selected_preset,
            )
        with hd_r2_right:
            st.checkbox("Auto-open", key="auto_open")

    # Surface 2: Stateful Configuration Editor (Single-line labels, compact vertical density)
    with st.container(border=True, key="surface_editor"):
        active_tab = st.radio(
            "Section",
            options=["Formats", "Typography", "Cover", "Tables", "Assistant"],
            horizontal=True,
            label_visibility="collapsed",
            key="active_editor_tab",
        )

        if active_tab == "Formats":
            col_id1, col_id2, col_id3 = st.columns([2.2, 1.8, 1.5], gap="small")
            with col_id1:
                st.text_input("Title", key="in_title")
            with col_id2:
                st.text_input("Subtitle", key="in_subtitle")
            with col_id3:
                st.text_input("Author", key="in_author")

            st.markdown('<div class="husson-section-sep">Outputs</div>', unsafe_allow_html=True)
            col_fmt1, col_fmt2, col_fmt3, col_fmt4, col_fmt5 = st.columns(5, gap="small")
            with col_fmt1:
                st.checkbox("PDF", key="opt_pdf")
            with col_fmt2:
                st.checkbox("HTML", key="opt_html")
            with col_fmt3:
                st.checkbox("DOCX", key="opt_docx")
            with col_fmt4:
                st.checkbox("RevealJS", key="opt_reveal")
            with col_fmt5:
                st.checkbox("PPTX", key="opt_pptx", help="Exporte le diaporama RevealJS en PowerPoint modifiable.")

            st.markdown('<div class="husson-section-sep">Structure</div>', unsafe_allow_html=True)
            col_st1, col_st2, col_st3, col_st4 = st.columns([1.0, 1.45, 1.35, 1.6], gap="small", vertical_alignment="bottom")
            with col_st1:
                st.checkbox("TOC", key="opt_toc")
            with col_st2:
                st.checkbox("Numbering", key="opt_num_sections")
            with col_st3:
                st.selectbox(
                    "Depth",
                    options=[1, 2, 3, 4, 5],
                    format_func=lambda n: f"H1 – H{n}" if n > 1 else "H1",
                    key="opt_toc_depth",
                )
            with col_st4:
                st.selectbox(
                    "Language",
                    options=["fr", "en"],
                    format_func=lambda x: "French (fr)" if x == "fr" else "English (en)",
                    key="opt_lang",
                )

        elif active_tab == "Typography":
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.selectbox(
                    "Font",
                    FONT_OPTIONS,
                    format_func=lambda f: "Custom..." if f == "Personnalisee..." else ("Computer Modern" if "Computer" in f else f),
                    key="sel_font",
                )
                if st.session_state.sel_font == "Personnalisee...":
                    st.text_input("Custom", key="custom_font_name")
            with col_t2:
                st.selectbox("Size", ["10pt", "11pt", "12pt"], key="sel_fontsize")
            with col_t3:
                st.selectbox("Spacing", ["1.0", "1.15", "1.25", "1.5"], key="sel_linestretch")

            st.markdown('<div class="husson-section-sep">Headings</div>', unsafe_allow_html=True)
            col_hd1, col_hd2 = st.columns(2)
            with col_hd1:
                st.checkbox("Pagebreak", key="opt_pagebreak_h1")
            with col_hd2:
                st.checkbox("Colors", key="opt_heading_colors")

        elif active_tab == "Cover":
            col_cov_top1, col_cov_top2, col_cov_top3, col_cov_top4 = st.columns(4)
            with col_cov_top1:
                st.checkbox("Cover", key="opt_thesis_active")
            with col_cov_top2:
                st.checkbox("Contents", key="fm_toc")
            with col_cov_top3:
                st.checkbox("Figures", key="fm_lof")
            with col_cov_top4:
                st.checkbox("Tables", key="fm_lot")

            if st.session_state.opt_thesis_active:
                st.markdown('<div class="husson-section-sep">Institution</div>', unsafe_allow_html=True)
                col_th1, col_th2, col_th3, col_th4 = st.columns(4)
                with col_th1:
                    st.text_input("University", key="th_university")
                    st.text_input("Specialty", key="th_specialty")
                with col_th2:
                    st.text_input("Faculty", key="th_faculty")
                    st.text_input("Department", key="th_dept")
                with col_th3:
                    st.text_input("Degree", key="th_degree")
                    st.text_input("Date", key="th_date")
                with col_th4:
                    st.text_input("Laboratory", key="th_laboratory")
                    st.selectbox(
                        "Logo",
                        LOGO_OPTIONS,
                        format_func=lambda l: "Custom..." if l == "Personnalise..." else ("None" if l == "Aucun logo" else l),
                        key="sel_logo",
                    )
                if st.session_state.sel_logo == "Personnalise...":
                    st.text_input("Path", key="custom_logo_path")

                with st.expander("Supervisors", expanded=False):
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.text_input("Supervisor", key="th_d1_name")
                    with col_d2:
                        st.text_input("Title", key="th_d1_title")
                    with col_d3:
                        st.text_input("Role", key="th_d1_role")

                    col_d2_1, col_d2_2, col_d2_3 = st.columns(3)
                    with col_d2_1:
                        st.text_input("Co-supervisor", key="th_d2_name")
                    with col_d2_2:
                        st.text_input("Affiliation", key="th_d2_title")
                    with col_d2_3:
                        st.text_input("Label", key="th_d2_role")

                with st.expander("Jury", expanded=False):
                    jury_df_in = pd.DataFrame(
                        st.session_state.get("jury_rows", []),
                        columns=["name", "title", "role"],
                    ).fillna("")
                    edited_jury_df = st.data_editor(
                        jury_df_in,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": st.column_config.TextColumn("Name", required=True),
                            "title": st.column_config.TextColumn("Title"),
                            "role": st.column_config.TextColumn("Role"),
                        },
                        key="jury_editor_widget",
                    )
                    st.session_state.jury_rows = edited_jury_df.fillna("").to_dict("records")

            st.markdown('<div class="husson-section-sep">Frontmatter</div>', unsafe_allow_html=True)
            col_kw1, col_kw2 = st.columns(2)
            with col_kw1:
                st.text_input("Keywords", key="fm_keywords_fr")
            with col_kw2:
                st.text_input("English", key="fm_keywords_en")

            with st.expander("Abstracts", expanded=False):
                col_fma1, col_fma2 = st.columns(2)
                with col_fma1:
                    st.text_area("Abstract", key="fm_abstract_fr", height=75)
                    st.text_area("Acknowledgements", key="fm_ack", height=75)
                with col_fma2:
                    st.text_area("Translation", key="fm_abstract_en", height=75)
                    st.text_area("Abbreviations", key="fm_abbrev", height=75)

        elif active_tab == "Tables":
            col_tb1, col_tb2, col_tb3 = st.columns(3)
            with col_tb1:
                st.checkbox("Widths", key="opt_colwidths")
                st.checkbox("Labels", key="opt_tableau_fr")
            with col_tb2:
                st.checkbox("Hyphenation", key="opt_hyphenation")
                st.checkbox("Linebreaks", key="opt_br_tags")
            with col_tb3:
                st.checkbox("Script", key="opt_gt_fit")

            st.markdown('<div class="husson-section-sep">Diagnostics</div>', unsafe_allow_html=True)
            if not legacy_tweaks:
                st.caption("Clean")
            else:
                for item in legacy_tweaks:
                    st.markdown(f"- {item}")
                if st.button("Clean", key="btn_clean_legacy"):
                    conv_ok, conv_msg, _, yaml_data = auto_configure_husson_document(
                        target_path, yaml_data, markdown_body, clean_body=True
                    )
                    if conv_ok:
                        st.session_state.current_loaded_file = ""
                        st.session_state["status_toast"] = "Legacy calls cleaned."
                        st.rerun()

        elif active_tab == "Assistant":
            ollama_models_tab = get_ollama_models()
            if not ollama_models_tab:
                st.info("Ollama server offline at http://localhost:11434. Run 'ollama serve' in a terminal.")
            else:
                if "chat_messages" not in st.session_state:
                    st.session_state["chat_messages"] = []

                def_idx_tab = 0
                for i, m in enumerate(ollama_models_tab):
                    if "coder" in m.lower():
                        def_idx_tab = i
                        break
                    elif "qwen" in m.lower():
                        def_idx_tab = i

                col_tol1, col_tol2, col_tol3, col_tol4 = st.columns([3, 1.5, 1.5, 1.5], vertical_alignment="bottom")
                with col_tol1:
                    sel_tab_model = st.selectbox(
                        "Model",
                        options=ollama_models_tab,
                        index=def_idx_tab,
                        key="tab_ollama_model",
                    )
                with col_tol2:
                    btn_check_doc = st.button("Check", use_container_width=True, key="btn_check_doc_yaml")
                with col_tol3:
                    last_comp_tab = st.session_state.get("last_compilation")
                    has_error = bool(last_comp_tab and last_comp_tab.get("return_code", 0) != 0)
                    btn_explain_err = st.button(
                        "Explain",
                        use_container_width=True,
                        key="btn_explain_last_err",
                        disabled=not has_error,
                    )
                with col_tol4:
                    btn_clear_chat = st.button("Clear", use_container_width=True, key="btn_clear_chat")

                if btn_clear_chat:
                    st.session_state["chat_messages"] = []
                    st.rerun()

                chat_container = st.container(height=230, border=True)
                with chat_container:
                    if not st.session_state["chat_messages"]:
                        st.caption(f"Context: {target_path.name}")
                    for msg in st.session_state["chat_messages"]:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

                prompt_to_send = None
                if btn_check_doc:
                    prompt_to_send = (
                        "Analyse l'en-tete YAML de mon document Quarto actif et indique-moi si tu reperes des erreurs de syntaxe, "
                        "des options conflictuelles (packages babel, natbib, polices) ou des ameliorations recommandees."
                    )
                elif btn_explain_err and has_error:
                    prompt_to_send = (
                        "La derniere tentative de compilation a echoue. Peux-tu analyser l'extrait d'erreur du journal et m'expliquer "
                        "precisement ce qui bloque et comment corriger le probleme ?"
                    )

                chat_user_input = st.chat_input(
                    "Ask...",
                    key="chat_input_field",
                )
                if chat_user_input and chat_user_input.strip():
                    prompt_to_send = chat_user_input.strip()

                if prompt_to_send:
                    st.session_state["chat_messages"].append({"role": "user", "content": prompt_to_send})
                    with chat_container:
                        with st.chat_message("user"):
                            st.markdown(prompt_to_send)

                        with st.chat_message("assistant"):
                            sys_prompt = build_chat_system_prompt(
                                target_path,
                                yaml_data,
                                st.session_state.get("last_compilation"),
                            )
                            full_response = []

                            def token_generator():
                                for token in stream_ollama_chat_response(
                                    sel_tab_model,
                                    st.session_state["chat_messages"],
                                    sys_prompt,
                                ):
                                    full_response.append(token)
                                    yield token

                            st.write_stream(token_generator())
                            st.session_state["chat_messages"].append({"role": "assistant", "content": "".join(full_response)})
                    st.rerun()

# --- HANDLE CREATE & SAVE ACTIONS ---
if is_new_mode and btn_create_file:
    if target_path.exists():
        st.error(f"File {target_path.name} already exists in {target_path.parent}.")
        st.stop()
    else:
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            st.error(f"Cannot create folder {target_path.parent}: {e}")
            st.stop()

        env_ok_new, env_msg_new = ensure_complete_project_environment(target_path)
        if not env_ok_new:
            st.error(env_msg_new)
            st.stop()

        is_rev_only = (
            bool(st.session_state.get("opt_reveal") or st.session_state.get("opt_pptx"))
            and not bool(st.session_state.get("opt_pdf"))
            and not bool(st.session_state.get("opt_html"))
            and not bool(st.session_state.get("opt_docx"))
        )
        markdown_body = build_new_document_body(
            include_sample_r=True,
            include_frontmatter_blocks=bool(st.session_state.get("opt_thesis_active", False)),
            is_reveal_only=is_rev_only,
        )
        new_yaml = build_updated_yaml()
        ok_new, msg_new, _ = save_qmd_with_backup(target_path, new_yaml, markdown_body)
        if not ok_new:
            st.error(msg_new)
            st.stop()

        find_recent_qmd_files.clear()
        list_project_directories.clear()
        resolved_new_str = str(target_path.resolve())
        st.session_state["active_file_override"] = resolved_new_str
        st.session_state["sidebar_manual_path"] = resolved_new_str
        st.session_state["sidebar_recent_select"] = resolved_new_str
        st.session_state["sidebar_mode_val"] = "Open"
        st.session_state.current_loaded_file = resolved_new_str
        st.session_state["status_toast"] = f"Created: {target_path.name}"
        st.rerun()

if btn_save and not is_new_mode:
    new_yaml = build_updated_yaml()
    body_to_save = markdown_body
    if st.session_state.opt_gt_fit and "husson_tables_on" not in body_to_save:
        r_chunk = (
            "\n```{r setup-husson-tables, include=FALSE}\n"
            'if (file.exists("_extensions/husson/gt-page-fit.R")) {\n'
            '  source("_extensions/husson/gt-page-fit.R")\n'
            "  husson_tables_on()\n"
            "}\n```\n\n"
        )
        body_to_save = r_chunk + body_to_save

    ok, msg, bpath = save_qmd_with_backup(target_path, new_yaml, body_to_save)
    if ok:
        yaml_data = new_yaml
        st.toast(f"Saved: {target_path.name}")
    else:
        st.error(msg)


# ==============================================================================
# RIGHT PANEL: COMPACT NATIVE QUARTO PREVIEW
# ==============================================================================
preview_dir = ensure_live_preview_workspace()
preview_body_slot = None
btn_panel_preview = False

if col_right is not None:
    with col_right:
        with st.container(border=True, key="surface_preview"):
            pr_top1, pr_top2, pr_top3 = st.columns([6.2, 1.9, 1.9], gap="small", vertical_alignment="center")
            with pr_top1:
                preview_mode = st.radio(
                    "Preview",
                    options=["PDF", "HTML", "RevealJS", "YAML"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="preview_view_mode",
                )
            with pr_top2:
                btn_panel_preview = st.button(
                    "Preview",
                    type="primary",
                    use_container_width=True,
                    key="btn_panel_quick_preview",
                )
            with pr_top3:
                active_mode_hdr = st.session_state.get("preview_view_mode", "PDF")
                if is_new_mode:
                    hdr_target = preview_dir / ("preview_reveal.qmd" if active_mode_hdr == "RevealJS" else "preview.qmd")
                else:
                    hdr_target = target_path
                ext_pdf = find_output_file(hdr_target, ".pdf")
                ext_html = find_output_file(hdr_target, ".html")
                has_ext_out = ext_pdf.exists() or ext_html.exists()
                if st.button("Open", use_container_width=True, key="btn_panel_open_ext", disabled=not has_ext_out):
                    if active_mode_hdr == "PDF" and ext_pdf.exists():
                        subprocess.run(["open", str(ext_pdf)])
                    elif ext_html.exists():
                        subprocess.run(["open", str(ext_html)])
                    elif ext_pdf.exists():
                        subprocess.run(["open", str(ext_pdf)])

            preview_body_slot = st.container()


# ==============================================================================
# FULL-WIDTH BOTTOM TERMINAL PANEL: WIDE ACROSS THE WORKSPACE (ZERO SCROLL)
# ==============================================================================
terminal_outer = st.container()

active_preview_mode = st.session_state.get("preview_view_mode", "PDF")
auto_preset_trigger = bool(st.session_state.pop("auto_trigger_preview", False))

if is_new_mode:
    active_compile_target = preview_dir / ("preview_reveal.qmd" if active_preview_mode == "RevealJS" else "preview.qmd")
else:
    active_compile_target = target_path

missing_native_output = False
if show_preview_panel and active_preview_mode in ("PDF", "HTML", "RevealJS"):
    if active_preview_mode == "PDF":
        missing_native_output = not find_output_file(active_compile_target, ".pdf").exists()
    else:
        missing_native_output = not find_output_file(active_compile_target, ".html").exists()

trigger_preview_compile = bool(btn_quick_preview or btn_panel_preview or auto_preset_trigger or missing_native_output)
trigger_full_render = bool(btn_render and not is_new_mode)
terminal_is_visible = bool(trigger_preview_compile or trigger_full_render or show_terminal_panel)

if terminal_is_visible:
    with terminal_outer:
        with st.container(border=True, key="surface_terminal"):
            if trigger_preview_compile or trigger_full_render:
                new_yaml = build_updated_yaml()

                if trigger_preview_compile and not trigger_full_render:
                    if "format" not in new_yaml or not isinstance(new_yaml["format"], dict):
                        new_yaml["format"] = {}
                    if active_preview_mode == "PDF" and "husson-pdf" not in new_yaml["format"]:
                        new_yaml["format"]["husson-pdf"] = "default"
                    elif active_preview_mode == "HTML" and "husson-html" not in new_yaml["format"]:
                        new_yaml["format"]["husson-html"] = {
                            "toc": bool(st.session_state.get("opt_toc", True)),
                            "toc-depth": int(st.session_state.get("opt_toc_depth", 3)),
                            "embed-resources": True,
                        }
                    elif active_preview_mode == "RevealJS" and "husson-revealjs" not in new_yaml["format"]:
                        new_yaml["format"]["husson-revealjs"] = {"embed-resources": True}

                if is_new_mode:
                    compile_target = active_compile_target
                    ensure_live_preview_workspace()
                    is_rev_body = (active_preview_mode == "RevealJS") or (
                        bool(st.session_state.get("opt_reveal") or st.session_state.get("opt_pptx"))
                        and not bool(st.session_state.get("opt_pdf"))
                        and not bool(st.session_state.get("opt_html"))
                        and not bool(st.session_state.get("opt_docx"))
                    )
                    body_to_compile = build_new_document_body(
                        include_sample_r=True,
                        include_frontmatter_blocks=bool(st.session_state.get("opt_thesis_active", False)),
                        is_reveal_only=is_rev_body,
                    )
                    ok_save, msg_save, bpath = save_qmd_with_backup(compile_target, new_yaml, body_to_compile)
                else:
                    compile_target = target_path
                    ensure_complete_project_environment(compile_target)
                    body_to_compile = markdown_body
                    if st.session_state.opt_gt_fit and "husson_tables_on" not in body_to_compile:
                        r_chunk = (
                            "\n```{r setup-husson-tables, include=FALSE}\n"
                            'if (file.exists("_extensions/husson/gt-page-fit.R")) {\n'
                            '  source("_extensions/husson/gt-page-fit.R")\n'
                            "  husson_tables_on()\n"
                            "}\n```\n\n"
                        )
                        body_to_compile = r_chunk + body_to_compile
                    ok_save, msg_save, bpath = save_qmd_with_backup(compile_target, new_yaml, body_to_compile)
                    if ok_save:
                        yaml_data = new_yaml

                if not ok_save:
                    st.error(f"Save failed before rendering: {msg_save}")
                else:
                    target_formats = []
                    if trigger_preview_compile and not trigger_full_render:
                        if active_preview_mode == "RevealJS":
                            target_formats = ["husson-revealjs"]
                        elif active_preview_mode == "HTML":
                            target_formats = ["husson-html"]
                        elif active_preview_mode == "PDF":
                            target_formats = ["husson-pdf"]
                        else:
                            if st.session_state.opt_reveal and not st.session_state.opt_pdf:
                                target_formats = ["husson-revealjs"]
                            elif st.session_state.opt_html and not st.session_state.opt_pdf:
                                target_formats = ["husson-html"]
                            else:
                                target_formats = ["husson-pdf"]
                    else:
                        if st.session_state.opt_pdf:
                            target_formats.append("husson-pdf")
                        if st.session_state.opt_html:
                            target_formats.append("husson-html")
                        if st.session_state.opt_docx:
                            target_formats.append("husson-docx")
                        if st.session_state.opt_reveal:
                            target_formats.append("husson-revealjs")
                        if st.session_state.opt_pptx:
                            target_formats.append("husson-pptx")

                    if not target_formats:
                        st.warning("Select at least one output format.")
                    else:
                        cmd = ["quarto", "render", str(compile_target)]
                        if len(target_formats) == 1:
                            cmd.extend(["--to", target_formats[0]])

                        start_time = time.time()
                        env = os.environ.copy()
                        env["PYTHONUNBUFFERED"] = "1"

                        running_hdr_placeholder = st.empty()
                        running_hdr_placeholder.markdown(
                            '<div class="husson-section-label">Terminal · Running</div>',
                            unsafe_allow_html=True,
                        )
                        log_placeholder = st.empty()

                        process = subprocess.Popen(
                            cmd,
                            cwd=str(compile_target.parent),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            env=env,
                        )

                        terminal_lines = [f"$ {' '.join(cmd)}\n"]
                        while True:
                            line = process.stdout.readline()
                            if not line and process.poll() is not None:
                                break
                            if line:
                                terminal_lines.append(line)
                                log_placeholder.code("".join(terminal_lines[-10:]), language="bash")
                                time.sleep(0.004)

                        return_code = process.poll()
                        elapsed = time.time() - start_time
                        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s" if elapsed >= 60 else f"{elapsed:.1f}s"

                        stream_yaml = StringIO()
                        yaml_parser.dump(new_yaml, stream_yaml)
                        saved_yaml_str = stream_yaml.getvalue()

                        st.session_state["last_compilation"] = {
                            "target_path": str(compile_target),
                            "cmd": cmd,
                            "return_code": return_code,
                            "terminal_lines": terminal_lines,
                            "yaml_str": saved_yaml_str,
                            "elapsed_str": elapsed_str,
                            "backup_name": bpath.name if bpath else "",
                        }
                        st.session_state.pop("last_diagnosis", None)
                        render_pdf_to_png_data_uris.clear()
                        running_hdr_placeholder.empty()
                        log_placeholder.empty()

                        if return_code == 0 and trigger_full_render and st.session_state.auto_open:
                            pdf_out = find_output_file(compile_target, ".pdf")
                            html_out = find_output_file(compile_target, ".html")
                            if st.session_state.opt_pdf and pdf_out.exists():
                                subprocess.run(["open", str(pdf_out)])
                            elif (st.session_state.opt_html or st.session_state.opt_reveal) and html_out.exists():
                                subprocess.run(["open", str(html_out)])
                            elif st.session_state.opt_pptx and find_output_file(compile_target, ".pptx").exists():
                                subprocess.run(["open", str(find_output_file(compile_target, ".pptx"))])

            # Compact, full-width Terminal status + last log lines (zero page scroll required)
            last_comp = st.session_state.get("last_compilation")
            if last_comp:
                ret_c = last_comp.get("return_code")
                comp_path = Path(last_comp.get("target_path", str(target_path)))
                tail_log = "".join(last_comp.get("terminal_lines", [])[-8:]).strip() or "$ quarto render (ready)"

                if ret_c == 0:
                    pdf_out = find_output_file(comp_path, ".pdf")
                    html_out = find_output_file(comp_path, ".html")
                    docx_out = find_output_file(comp_path, ".docx")
                    pptx_out = find_output_file(comp_path, ".pptx")

                    res_c0, res_c1, res_c2, res_c3, res_c4 = st.columns([5.6, 1.1, 1.1, 1.1, 1.1], gap="small", vertical_alignment="center")
                    with res_c0:
                        st.markdown(
                            f'<div class="husson-section-label" style="margin:0;">Terminal · {last_comp.get("elapsed_str", "Ready")}</div>',
                            unsafe_allow_html=True,
                        )
                    with res_c1:
                        if pdf_out.exists():
                            if st.button("PDF", use_container_width=True, key="btn_open_pdf"):
                                subprocess.run(["open", str(pdf_out)])
                    with res_c2:
                        if html_out.exists():
                            if st.button("HTML", use_container_width=True, key="btn_open_html"):
                                subprocess.run(["open", str(html_out)])
                        elif docx_out.exists():
                            if st.button("DOCX", use_container_width=True, key="btn_open_docx"):
                                subprocess.run(["open", str(docx_out)])
                    with res_c3:
                        if pptx_out.exists() and st.session_state.opt_pptx:
                            if st.button("PPTX", use_container_width=True, key="btn_open_pptx"):
                                subprocess.run(["open", str(pptx_out)])
                    with res_c4:
                        if st.button("Folder", use_container_width=True, key="btn_open_finder"):
                            subprocess.run(["open", str(comp_path.parent)])

                    st.code(tail_log, language="bash")
                else:
                    st.markdown(
                        f'<div class="husson-section-label" style="color:#B42318;margin:0;">Terminal · Failed (code {ret_c})</div>',
                        unsafe_allow_html=True,
                    )
                    st.code("".join(last_comp.get("terminal_lines", [])[-12:]), language="bash")

                    ollama_models = get_ollama_models()
                    if ollama_models:
                        default_idx = 0
                        for idx, m in enumerate(ollama_models):
                            if "coder" in m.lower():
                                default_idx = idx
                                break
                            elif "qwen" in m.lower():
                                default_idx = idx

                        col_diag1, col_diag2 = st.columns([2, 2], gap="small", vertical_alignment="bottom")
                        with col_diag1:
                            diag_model = st.selectbox(
                                "Model",
                                options=ollama_models,
                                index=default_idx,
                                key="diag_model_select",
                                label_visibility="collapsed",
                            )
                        with col_diag2:
                            btn_run_diag = st.button(
                                "Diagnose",
                                type="primary",
                                use_container_width=True,
                                key="btn_run_ollama_diagnosis",
                            )

                        if btn_run_diag:
                            err_snip = extract_error_snippet(last_comp.get("terminal_lines", []))
                            diag_prompt = (
                                "Tu es un expert specialise en compilation Quarto, Pandoc, XeLaTeX et mise en page academique.\n"
                                "Un document Quarto vient d'echouer lors de sa compilation avec l'erreur ci-dessous.\n\n"
                                f"Document : {comp_path.name}\n"
                                f"Commande : {' '.join(last_comp.get('cmd', []))}\n\n"
                                "En-tete YAML du document :\n"
                                "```yaml\n"
                                f"{last_comp.get('yaml_str', '')}\n"
                                "```\n\n"
                                "Extrait du journal d'erreur (terminal) :\n"
                                "```text\n"
                                f"{err_snip}\n"
                                "```\n\n"
                                "Consignes de reponse :\n"
                                "1. Diagnostic : Identifie precisement la cause de l'echec.\n"
                                "2. Solution : Explique clairement les etapes pour corriger le probleme.\n"
                                "3. Correction exacte : Fournis le bloc de code ou le YAML exact a utiliser.\n"
                                "Reponds en francais de facon concise, directe et technique sans aucun emoji."
                            )
                            with st.chat_message("assistant"):
                                full_resp = []

                                def token_collector():
                                    for t in stream_ollama_response(diag_model, diag_prompt):
                                        full_resp.append(t)
                                        yield t

                                st.write_stream(token_collector())
                                st.session_state["last_diagnosis"] = "".join(full_resp)
            else:
                pdf_out = find_output_file(active_compile_target, ".pdf")
                html_out = find_output_file(active_compile_target, ".html")
                docx_out = find_output_file(active_compile_target, ".docx")
                res_c0, res_c1, res_c2, res_c3 = st.columns([6.7, 1.1, 1.1, 1.1], gap="small", vertical_alignment="center")
                with res_c0:
                    st.markdown('<div class="husson-section-label" style="margin:0;">Terminal · Ready</div>', unsafe_allow_html=True)
                with res_c1:
                    if pdf_out.exists():
                        if st.button("PDF", use_container_width=True, key="btn_open_pdf"):
                            subprocess.run(["open", str(pdf_out)])
                with res_c2:
                    if html_out.exists():
                        if st.button("HTML", use_container_width=True, key="btn_open_html"):
                            subprocess.run(["open", str(html_out)])
                    elif docx_out.exists():
                        if st.button("DOCX", use_container_width=True, key="btn_open_docx"):
                            subprocess.run(["open", str(docx_out)])
                with res_c3:
                    if st.button("Folder", use_container_width=True, key="btn_open_finder"):
                        subprocess.run(["open", str(active_compile_target.parent)])
                st.code(f"$ quarto render {active_compile_target.name}\nOutput created: {pdf_out.name if pdf_out.exists() else active_compile_target.name}", language="bash")


# ==============================================================================
# POPULATE RIGHT PANEL BODY (COMPACT NATIVE QUARTO RENDERED OUTPUT OR YAML)
# ==============================================================================
if preview_body_slot is not None:
    with preview_body_slot:
        active_preview_mode = st.session_state.get("preview_view_mode", "PDF")
        last_comp = st.session_state.get("last_compilation") or {}
        elapsed_lbl = last_comp.get("elapsed_str", "")
        viewer_height = 240 if terminal_is_visible else 345

        if active_preview_mode == "PDF":
            pdf_target = (preview_dir / "preview.qmd") if is_new_mode else target_path
            pdf_out = find_output_file(pdf_target, ".pdf")
            if pdf_out.exists():
                page_uris = render_pdf_to_png_data_uris(str(pdf_out), pdf_out.stat().st_mtime)
                if page_uris:
                    viewer_html = build_pdf_viewer_html(page_uris, pdf_out.name, elapsed_lbl)
                    components.html(viewer_html, height=viewer_height, scrolling=False)
                else:
                    pdf_b64 = base64.b64encode(pdf_out.read_bytes()).decode("ascii")
                    components.html(
                        f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="{viewer_height - 10}" style="border:none;border-radius:6px;"></iframe>',
                        height=viewer_height,
                    )
            else:
                st.error("PDF compilation failed. Check Terminal below.")

        elif active_preview_mode in ("HTML", "RevealJS"):
            if is_new_mode:
                html_target = preview_dir / ("preview_reveal.qmd" if active_preview_mode == "RevealJS" else "preview.qmd")
            else:
                html_target = target_path
            html_out = find_output_file(html_target, ".html")
            if html_out.exists():
                try:
                    raw_html_doc = html_out.read_text(encoding="utf-8", errors="replace")
                    components.html(
                        raw_html_doc,
                        height=viewer_height,
                        scrolling=(active_preview_mode == "HTML"),
                    )
                except Exception as e:
                    st.error(f"Cannot load compiled {active_preview_mode} output: {e}")
            else:
                st.error(f"{active_preview_mode} compilation failed. Check Terminal below.")

        elif active_preview_mode == "YAML":
            preview_yaml_dict = build_updated_yaml()
            s_io = StringIO()
            yaml_parser.dump(preview_yaml_dict, s_io)
            yaml_str_preview = f"---\n{s_io.getvalue()}---"
            st.code(yaml_str_preview, language="yaml")



