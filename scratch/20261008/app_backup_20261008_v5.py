#!/usr/bin/env python3
"""
Quarto Husson Studio
Espace de travail pour créer, convertir, configurer et compiler des documents
Quarto avec le template Husson (PDF, HTML, DOCX, RevealJS).
"""

import os
import sys
import re
import time
import shutil
import subprocess
from pathlib import Path
import json
import urllib.request
import urllib.error
from datetime import datetime
from io import StringIO
import pandas as pd
import streamlit as st
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

TEMPLATE_REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
TEMPLATE_EXTENSION_DIR = TEMPLATE_REPO_PATH / "_extensions" / "husson"
PROJECTS_BASE_DIR = Path("/Users/thomashusson/Documents/Projets")

st.set_page_config(
    page_title="Quarto Husson Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Feuille de style sobre et minimale (macOS / Things 3 / Linear en mode clair)
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
        height: 1.5rem !important;
    }
    .block-container {
        padding-top: 1.15rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1220px !important;
    }

    /* Surfaces principales de premier niveau uniquement (#FFFFFF sur fond #F6F7F9) */
    div[data-testid="stMainBlockContainer"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E5EA !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03) !important;
    }

    /* Barre latérale en gris clair #F6F7F9 avec séparation fine #E2E5EA */
    section[data-testid="stSidebar"] {
        background-color: #F6F7F9 !important;
        border-right: 1px solid #E2E5EA !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.1rem !important;
        padding-bottom: 1.5rem !important;
    }

    /* En-tête du document actif */
    .husson-doc-header {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        min-width: 0;
    }
    .husson-doc-title-row {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.45rem;
    }
    .husson-doc-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #242932;
        letter-spacing: -0.015em;
        margin: 0;
    }
    .husson-doc-path {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.78rem;
        color: #687281;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }
    .husson-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.72rem;
        font-weight: 500;
        padding: 0.1rem 0.5rem;
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

    /* Intitulés de sous-sections */
    .husson-section-label {
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.045em;
        color: #687281;
        margin-top: 0.35rem;
        margin-bottom: 0.35rem;
    }
    .husson-toolbar-sep {
        border-top: 1px solid #E2E5EA;
        margin: 0.75rem 0;
    }

    /* Onglets sobres et barre d'onglets stateful */
    button[data-baseweb="tab"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        padding-top: 0.45rem !important;
        padding-bottom: 0.6rem !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 1.6rem !important;
        border-bottom: 1px solid #E2E5EA !important;
        padding-bottom: 0 !important;
        margin-bottom: 0.55rem !important;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label {
        background: transparent !important;
        padding: 0.35rem 0.1rem 0.55rem 0.1rem !important;
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
        font-size: 0.9rem !important;
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
    hr {
        margin-top: 0.9rem !important;
        margin-bottom: 0.9rem !important;
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
        for k in ("pdf", "husson-pdf", "html", "husson-html", "docx", "husson-docx", "revealjs", "husson-revealjs")
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

    for k, v in raw_formats.items():
        if k not in ("pdf", "html", "docx", "revealjs", "husson-pdf", "husson-html", "husson-docx", "husson-revealjs"):
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
    """Construit le corps Markdown initial d'un nouveau document .qmd."""
    body_parts = []
    if include_frontmatter_blocks:
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

    if is_reveal_only:
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
        if include_sample_r:
            body_parts.append(
                "\n".join(
                    [
                        "# Résultats",
                        "",
                        "## Tableau descriptif {.scrollable}",
                        "",
                        "```{r}",
                        "#| label: tbl-descriptif",
                        '#| tbl-cap: "Caractéristiques descriptives de l\'échantillon (mtcars)"',
                        "#| echo: false",
                        "knitr::kable(head(mtcars[, 1:5], 5))",
                        "```",
                        "",
                        "## Visualisation",
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
        body_parts.append("# Conclusion\n\n## Messages clés\n\n- Synthèse des résultats principaux\n- Perspectives\n")
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

        body_parts.append("# Discussion\n\nInterprétation des résultats et limites de l'étude.\n")

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
    "active_editor_tab",
    "sel_preset_profile",
    "opt_pdf",
    "opt_html",
    "opt_docx",
    "opt_reveal",
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

if "active_editor_tab" not in st.session_state:
    st.session_state["active_editor_tab"] = "Formats"

for _k in PERSISTED_STATE_KEYS:
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]


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
default_epidemio = "/Users/thomashusson/Documents/Projets/M2biostatistiques/S2/devoir_epidemio/devoir_epidemio.qmd"
initial_default_path = (
    default_epidemio
    if Path(default_epidemio).exists()
    else (recent_files[0] if recent_files else default_fallback)
)

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

    new_subfolder = st.sidebar.text_input(
        "Subfolder",
        value="",
        help="Optional subfolder to create inside the parent folder.",
    )
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
    has_any = init_has_pdf or init_has_html or init_has_docx or init_has_reveal

    thesis_data = y_data.get("thesis", {})
    init_has_thesis = bool(thesis_data)
    if not isinstance(thesis_data, dict):
        thesis_data = {}

    init_pagebreak_h1 = y_data.get("pagebreak-h1", y_data.get("chapter-pagebreak", init_has_thesis))
    if isinstance(init_pagebreak_h1, str):
        init_pagebreak_h1 = init_pagebreak_h1.strip().lower() in ("true", "yes", "1")
    else:
        init_pagebreak_h1 = bool(init_pagebreak_h1)

    init_heading_colors = y_data.get("heading-colors", False)
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
    st.session_state.th_specialty = str(thesis_data.get("specialty") or "UE Épidémiologie -- Groupe 52")
    st.session_state.th_dept = str(thesis_data.get("department") or "Étude observationnelle SUPPORT")
    st.session_state.th_date = str(thesis_data.get("date") or "Année universitaire 2025-2026")

    cur_logo = str(thesis_data.get("logo", "images/logo-universite-paris-saclay.png"))
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
    st.session_state.th_d1_role = d1.get("role", "Dirigé") if isinstance(d1, dict) else "Dirigé"
    st.session_state.th_d2_name = d2.get("name", "") if isinstance(d2, dict) else str(d2 or "")
    st.session_state.th_d2_title = d2.get("title", "") if isinstance(d2, dict) else ""
    st.session_state.th_d2_role = d2.get("role", "Et co-dirigé") if isinstance(d2, dict) else "Et co-dirigé"

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

    st.session_state.fm_abstract_fr = str(fm_data.get("abstract") or "")
    st.session_state.fm_abstract_en = str(fm_data.get("abstract-en") or "")
    st.session_state.fm_ack = str(fm_data.get("acknowledgements") or "")
    st.session_state.fm_abbrev = str(fm_data.get("abbreviations") or "")

    st.session_state.opt_colwidths = True
    st.session_state.opt_hyphenation = True
    st.session_state.opt_tableau_fr = st.session_state.opt_lang == "fr"
    st.session_state.opt_br_tags = True
    st.session_state.opt_gt_fit = False
    if "auto_open" not in st.session_state:
        st.session_state.auto_open = True


    if init_has_reveal and not init_has_pdf:
        st.session_state.sel_preset_profile = "Presentation / RevealJS"
    elif init_has_thesis:
        if default_font_idx == 0:
            st.session_state.sel_preset_profile = "Devoir / Rapport de Master"
        else:
            st.session_state.sel_preset_profile = "These / Memoire officiel"
    elif init_has_html:
        st.session_state.sel_preset_profile = "Article / Rapport Web"
    elif default_font_idx == 0:
        st.session_state.sel_preset_profile = "Rapport Scientifique Sobre"
    else:
        st.session_state.sel_preset_profile = "Article / Rapport Web"


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
    elif "heading-colors" in d:
        del d["heading-colors"]

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

        existing_pdf["toc"] = opt_toc
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
        d["format"]["husson-revealjs"] = existing_reveal
        if "revealjs" in d["format"]:
            del d["format"]["revealjs"]
    else:
        d["format"].pop("husson-revealjs", None)
        d["format"].pop("revealjs", None)

    ordered_formats = {}
    if st.session_state.opt_pdf and "husson-pdf" in d["format"]:
        ordered_formats["husson-pdf"] = d["format"]["husson-pdf"]
    if st.session_state.opt_html and "husson-html" in d["format"]:
        ordered_formats["husson-html"] = d["format"]["husson-html"]
    if st.session_state.opt_docx and "husson-docx" in d["format"]:
        ordered_formats["husson-docx"] = d["format"]["husson-docx"]
    if st.session_state.opt_reveal and "husson-revealjs" in d["format"]:
        ordered_formats["husson-revealjs"] = d["format"]["husson-revealjs"]
    for k, v in d["format"].items():
        if k not in ordered_formats:
            ordered_formats[k] = v
    d["format"] = ordered_formats

    if st.session_state.opt_thesis_active:
        thesis_dict = dict(yaml_data.get("thesis", {})) if isinstance(yaml_data.get("thesis"), dict) else {}

        resolved_logo = None
        sel_logo = st.session_state.sel_logo
        custom_logo_path = st.session_state.custom_logo_path
        if sel_logo == "Université Paris-Saclay":
            existing_logo = thesis_dict.get("logo", "")
            if (
                existing_logo
                and "paris-saclay" in str(existing_logo)
                and not str(existing_logo).startswith("_")
                and "_extensions" not in str(existing_logo)
            ):
                resolved_logo = existing_logo
            else:
                resolved_logo = "images/logo-universite-paris-saclay.png"
        elif sel_logo == "Université Paris Cité":
            existing_logo = thesis_dict.get("logo", "")
            if (
                existing_logo
                and "paris-cite" in str(existing_logo)
                and not str(existing_logo).startswith("_")
                and "_extensions" not in str(existing_logo)
            ):
                resolved_logo = existing_logo
            else:
                resolved_logo = "images/logo-universite-paris-cite.png"
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
                "role": st.session_state.th_d1_role.strip(),
            }
        new_d2 = None
        if st.session_state.th_d2_name.strip():
            new_d2 = {
                "name": st.session_state.th_d2_name.strip(),
                "title": st.session_state.th_d2_title.strip(),
                "role": st.session_state.th_d2_role.strip(),
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

    for fm_key, state_key in [
        ("abstract", "fm_abstract_fr"),
        ("abstract-en", "fm_abstract_en"),
        ("acknowledgements", "fm_ack"),
        ("abbreviations", "fm_abbrev"),
    ]:
        val = st.session_state.get(state_key, "").strip()
        if val:
            fm_existing[fm_key] = val
        else:
            fm_existing.pop(fm_key, None)

    if fm_existing:
        d["frontmatter"] = fm_existing
    elif "frontmatter" in d:
        del d["frontmatter"]

    return d


def apply_selected_preset():
    """Applies the selected preset immediately to the UI state without writing to disk."""
    selected_profile = st.session_state.get("sel_preset_profile", "")
    if selected_profile == "Devoir / Rapport de Master":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.sel_font = "Computer Modern (Latex Default)"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = True
        st.session_state.opt_pagebreak_h1 = True
    elif selected_profile == "These / Memoire officiel":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = True
        st.session_state.opt_pagebreak_h1 = True
    elif selected_profile == "Rapport Scientifique Sobre":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.sel_font = "Computer Modern (Latex Default)"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False
    elif selected_profile == "Article / Rapport Web":
        st.session_state.opt_pdf = True
        st.session_state.opt_html = True
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = False
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False
    elif selected_profile == "Presentation / RevealJS":
        st.session_state.opt_pdf = False
        st.session_state.opt_html = False
        st.session_state.opt_docx = False
        st.session_state.opt_reveal = True
        st.session_state.sel_font = "Times New Roman"
        st.session_state.sel_fontsize = "11pt"
        st.session_state.sel_linestretch = "1.15"
        st.session_state.opt_thesis_active = False
        st.session_state.opt_pagebreak_h1 = False


# --- 1, 2 & 3. MAIN HEADER SURFACE: ACTIVE DOCUMENT, ACTIONS & PRESETS ---
if "status_toast" in st.session_state and st.session_state["status_toast"]:
    st.success(st.session_state.pop("status_toast"))

active_formats_badges = []
if st.session_state.opt_pdf:
    active_formats_badges.append('<span class="husson-badge">pdf</span>')
if st.session_state.opt_html:
    active_formats_badges.append('<span class="husson-badge">html</span>')
if st.session_state.opt_docx:
    active_formats_badges.append('<span class="husson-badge">docx</span>')
if st.session_state.opt_reveal:
    active_formats_badges.append('<span class="husson-badge">revealjs</span>')

if is_new_mode:
    status_badge_html = '<span class="husson-badge husson-badge-ok">New</span>'
elif is_ready and env_ok:
    status_badge_html = '<span class="husson-badge husson-badge-ok">Ready</span>'
else:
    status_badge_html = '<span class="husson-badge husson-badge-warn">Native</span>'

btn_create_file = False
btn_save = False
btn_render = False

with st.container(border=True):
    col_doc_info, col_main_actions = st.columns([7.1, 2.9], vertical_alignment="center")

    with col_doc_info:
        badges_str = "".join(active_formats_badges)
        short_parent = format_display_path(target_path.parent)
        st.markdown(
            f"""
            <div class="husson-doc-header">
                <div class="husson-doc-title-row">
                    <span class="husson-doc-title">{target_path.name}</span>
                    {status_badge_html}
                    {badges_str}
                </div>
                <div class="husson-doc-path" title="{target_path.parent}">{short_parent}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_main_actions:
        if is_new_mode:
            _, act_c_new = st.columns([0.85, 1.3], vertical_alignment="center")
            with act_c_new:
                btn_create_file = st.button("Create", type="primary", use_container_width=True, key="btn_top_create")
        else:
            act_c1, act_c2 = st.columns([1, 1.15], vertical_alignment="center")
            with act_c1:
                btn_save = st.button("Save", use_container_width=True, key="btn_top_save")
            with act_c2:
                btn_render = st.button("Render", type="primary", use_container_width=True, key="btn_top_render")

    st.markdown('<div class="husson-toolbar-sep"></div>', unsafe_allow_html=True)

    needs_conversion_btn = (not is_new_mode) and ((not is_ready) or bool(legacy_tweaks))
    if needs_conversion_btn:
        tb_c1, tb_c2, tb_c3 = st.columns([6.0, 2.0, 2.0], vertical_alignment="center")
    else:
        tb_c1, tb_c2 = st.columns([7.2, 2.8], vertical_alignment="center")
        tb_c3 = None

    with tb_c1:
        selected_profile = st.selectbox(
            "Preset",
            options=PROFILE_OPTIONS,
            format_func=lambda k: PROFILE_DISPLAY_LABELS.get(k, k),
            label_visibility="collapsed",
            key="sel_preset_profile",
            on_change=apply_selected_preset,
        )
    with tb_c2:
        st.checkbox("Auto-open", key="auto_open", help="Automatically open rendered output after compilation.")
    if tb_c3 is not None:
        with tb_c3:
            if st.button("Convert", use_container_width=True, key="btn_activate_husson", help="Convert YAML and clean legacy tweaks for Husson template."):
                conv_ok, conv_msg, conv_bpath, yaml_data = auto_configure_husson_document(
                    target_path, yaml_data, markdown_body, clean_body=True
                )
                if conv_ok:
                    st.session_state.current_loaded_file = ""
                    st.session_state["status_toast"] = f"Converted: {target_path.name}"
                    st.rerun()
                else:
                    st.warning(conv_msg)


# Handle new file creation (single "Create" button)
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
            bool(st.session_state.get("opt_reveal"))
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


# Handle Save action
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
        st.success(f"Saved: {target_path.name}")
    else:
        st.error(msg)


# --- 5. COMPILATION & RESULTS ---
if btn_render:
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
    if not ok:
        st.error(f"Save failed before rendering: {msg}")
        st.stop()

    yaml_data = new_yaml
    target_formats = []
    if st.session_state.opt_pdf:
        target_formats.append("husson-pdf")
    if st.session_state.opt_html:
        target_formats.append("husson-html")
    if st.session_state.opt_docx:
        target_formats.append("husson-docx")
    if st.session_state.opt_reveal:
        target_formats.append("husson-revealjs")

    if not target_formats:
        st.warning("Select at least one output format before rendering.")
    else:
        cmd = ["quarto", "render", str(target_path)]
        if len(target_formats) == 1:
            cmd.extend(["--to", target_formats[0]])

        start_time = time.time()
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        with st.status("Rendering...", expanded=True) as status_box:
            st.code(" ".join(cmd), language="bash")
            log_placeholder = st.empty()

            process = subprocess.Popen(
                cmd,
                cwd=str(target_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )

            terminal_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    terminal_lines.append(line)
                    log_placeholder.code("".join(terminal_lines[-25:]), language="bash")
                    time.sleep(0.01)

            return_code = process.poll()
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s" if elapsed >= 60 else f"{elapsed:.1f}s"
            log_placeholder.empty()

            stream_yaml = StringIO()
            yaml_parser.dump(new_yaml, stream_yaml)
            saved_yaml_str = stream_yaml.getvalue()

            st.session_state["last_compilation"] = {
                "target_path": str(target_path),
                "cmd": cmd,
                "return_code": return_code,
                "terminal_lines": terminal_lines,
                "yaml_str": saved_yaml_str,
                "elapsed_str": elapsed_str,
                "backup_name": bpath.name if bpath else "",
            }
            st.session_state.pop("last_diagnosis", None)

            if return_code == 0:
                status_box.update(
                    label=f"Completed ({elapsed_str})",
                    state="complete",
                    expanded=False,
                )
                if st.session_state.auto_open:
                    pdf_out = find_output_file(target_path, ".pdf")
                    html_out = find_output_file(target_path, ".html")
                    if st.session_state.opt_pdf and pdf_out.exists():
                        subprocess.run(["open", str(pdf_out)])
                    elif (st.session_state.opt_html or st.session_state.opt_reveal) and html_out.exists():
                        subprocess.run(["open", str(html_out)])
            else:
                status_box.update(
                    label=f"Failed (code {return_code})",
                    state="error",
                    expanded=False,
                )

last_comp = st.session_state.get("last_compilation")
if last_comp and last_comp.get("target_path") == str(target_path):
    ret_c = last_comp.get("return_code")
    terminal_log = "".join(last_comp.get("terminal_lines", []))

    with st.container(border=True):
        if ret_c == 0:
            pdf_out = find_output_file(target_path, ".pdf")
            html_out = find_output_file(target_path, ".html")
            docx_out = find_output_file(target_path, ".docx")

            res_c0, res_c1, res_c2, res_c3, res_c4 = st.columns([3.2, 1.7, 1.7, 1.7, 1.7], vertical_alignment="center")
            with res_c0:
                st.markdown(f"**Rendered** ({last_comp.get('elapsed_str', '')})")
            with res_c1:
                if st.session_state.opt_pdf and pdf_out.exists():
                    if st.button("PDF", use_container_width=True, key="btn_open_pdf"):
                        subprocess.run(["open", str(pdf_out)])
            with res_c2:
                if (st.session_state.opt_html or st.session_state.opt_reveal) and html_out.exists():
                    if st.button("HTML", use_container_width=True, key="btn_open_html"):
                        subprocess.run(["open", str(html_out)])
            with res_c3:
                if st.session_state.opt_docx and docx_out.exists():
                    if st.button("DOCX", use_container_width=True, key="btn_open_docx"):
                        subprocess.run(["open", str(docx_out)])
            with res_c4:
                if st.button("Folder", use_container_width=True, key="btn_open_finder"):
                    subprocess.run(["open", str(target_path.parent)])

            with st.expander("Logs", expanded=False):
                st.code(terminal_log, language="bash")
        else:
            st.error(f"Failed (code {ret_c}).")
            with st.expander("Logs", expanded=True):
                st.code(terminal_log, language="bash")

            ollama_models = get_ollama_models()
            if not ollama_models:
                st.caption("Ollama server offline at http://localhost:11434.")
            else:
                default_idx = 0
                for idx, m in enumerate(ollama_models):
                    if "coder" in m.lower():
                        default_idx = idx
                        break
                    elif "qwen" in m.lower():
                        default_idx = idx

                col_diag1, col_diag2 = st.columns([2, 3], vertical_alignment="bottom")
                with col_diag1:
                    diag_model = st.selectbox(
                        "Model",
                        options=ollama_models,
                        index=default_idx,
                        key="diag_model_select",
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
                        f"Document : {target_path.name}\n"
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
                        "1. Diagnostic : Identifie precisement la cause de l'echec (erreur XeLaTeX, package conflictuel, chemin manquant, citation invalide, etc.).\n"
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
                        diagnosis_str = "".join(full_resp)
                        st.session_state["last_diagnosis"] = diagnosis_str
                        if "chat_messages" not in st.session_state:
                            st.session_state["chat_messages"] = []
                        st.session_state["chat_messages"].append(
                            {
                                "role": "user",
                                "content": "J'ai rencontré une erreur lors de la compilation. Peux-tu m'expliquer le problème et proposer une solution ?",
                            }
                        )
                        st.session_state["chat_messages"].append({"role": "assistant", "content": diagnosis_str})
                elif "last_diagnosis" in st.session_state and st.session_state["last_diagnosis"]:
                    with st.chat_message("assistant"):
                        st.markdown(st.session_state["last_diagnosis"])


# --- 4. CONFIGURATION EDITOR SURFACE ---
with st.container(border=True):
    active_tab = st.radio(
        "Section",
        options=["Formats", "Typography", "Cover", "Tables", "Assistant"],
        horizontal=True,
        label_visibility="collapsed",
        key="active_editor_tab",
    )

    if active_tab == "Formats":
        st.markdown('<div class="husson-section-label">Identity</div>', unsafe_allow_html=True)
        col_id1, col_id2 = st.columns([3, 2])
        with col_id1:
            st.text_input("Title", key="in_title")
        with col_id2:
            st.text_input("Author", key="in_author")
        st.text_input("Subtitle", key="in_subtitle")

        st.divider()
        st.markdown('<div class="husson-section-label">Outputs</div>', unsafe_allow_html=True)
        col_fmt1, col_fmt2, col_fmt3, col_fmt4 = st.columns(4)
        with col_fmt1:
            st.checkbox("PDF", key="opt_pdf", help="XeLaTeX PDF output (husson-pdf).")
        with col_fmt2:
            st.checkbox("HTML", key="opt_html", help="Standalone Web output with light/dark switch (husson-html).")
        with col_fmt3:
            st.checkbox("DOCX", key="opt_docx", help="Word document output (husson-docx).")
        with col_fmt4:
            st.checkbox("RevealJS", key="opt_reveal", help="Interactive HTML slides (husson-revealjs).")

        st.divider()
        st.markdown('<div class="husson-section-label">Structure</div>', unsafe_allow_html=True)
        col_st1, col_st2, col_st3, col_st4 = st.columns([1, 1, 1.5, 1.5], vertical_alignment="bottom")
        with col_st1:
            st.checkbox("TOC", key="opt_toc", help="Generate a Table of Contents.")
        with col_st2:
            st.checkbox("Numbering", key="opt_num_sections", help="Number headings automatically.")
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
        st.markdown('<div class="husson-section-label">Style</div>', unsafe_allow_html=True)
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

        st.divider()
        st.markdown('<div class="husson-section-label">Headings</div>', unsafe_allow_html=True)
        col_hd1, col_hd2 = st.columns(2)
        with col_hd1:
            st.checkbox(
                "Pagebreak",
                key="opt_pagebreak_h1",
                help="Start each H1 chapter on a new page (pagebreak-h1: true).",
            )
        with col_hd2:
            st.checkbox(
                "Colors",
                key="opt_heading_colors",
                help="Apply Husson color palette to headings (heading-colors: true).",
            )

    elif active_tab == "Cover":
        st.checkbox(
            "Cover",
            key="opt_thesis_active",
            help="Enable official cover page (Thesis, Master, University report).",
        )

        if st.session_state.opt_thesis_active:
            st.markdown('<div class="husson-section-label">Institution</div>', unsafe_allow_html=True)
            col_th1, col_th2 = st.columns(2)
            with col_th1:
                st.text_input("University", key="th_university")
                st.text_input("Faculty", key="th_faculty")
                st.text_input("Degree", key="th_degree")
                st.text_input("Laboratory", key="th_laboratory")
            with col_th2:
                st.text_input("Specialty", key="th_specialty")
                st.text_input("Department", key="th_dept")
                st.text_input("Date", key="th_date")
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

        st.divider()
        st.markdown('<div class="husson-section-label">Frontmatter</div>', unsafe_allow_html=True)
        col_fm1, col_fm2, col_fm3 = st.columns(3)
        with col_fm1:
            st.checkbox("Contents", key="fm_toc", help="Include Table of Contents in Roman-numeral frontmatter.")
        with col_fm2:
            st.checkbox("Figures", key="fm_lof", help="Include List of Figures in frontmatter.")
        with col_fm3:
            st.checkbox("Tables", key="fm_lot", help="Include List of Tables in frontmatter.")

        col_kw1, col_kw2 = st.columns(2)
        with col_kw1:
            st.text_input("Keywords", key="fm_keywords_fr", help="Comma-separated primary keywords.")
        with col_kw2:
            st.text_input("English", key="fm_keywords_en", help="Comma-separated English keywords.")

        has_div_ack = "frontmatter-acknowledgements" in (markdown_body or "")
        has_div_abs = "frontmatter-abstract" in (markdown_body or "")
        has_div_abv = "frontmatter-abbreviations" in (markdown_body or "")

        with st.expander("Abstracts", expanded=False):
            if has_div_ack or has_div_abs or has_div_abv:
                st.caption("Blocks ::: {.frontmatter-*} are present in the document body.")
            else:
                if st.button("Insert", key="btn_insert_fm_divs", help="Insert ::: {.frontmatter-*} blocks into the document body."):
                    fm_template_blocks = (
                        "\n::: {.frontmatter-acknowledgements}\n"
                        "Vos remerciements ici.\n"
                        ":::\n\n"
                        "::: {.frontmatter-abstract}\n"
                        "Résumé en français.\n"
                        ":::\n\n"
                        "::: {.frontmatter-abstract-en}\n"
                        "Abstract in English.\n"
                        ":::\n\n"
                        "::: {.frontmatter-abbreviations}\n"
                        "| Abréviation | Définition |\n"
                        "| :--- | :--- |\n"
                        "| **IC 95 %** | Intervalle de confiance à 95 % |\n"
                        ":::\n\n"
                    )
                    new_y = build_updated_yaml()
                    ok_ins, msg_ins, _ = save_qmd_with_backup(target_path, new_y, fm_template_blocks + markdown_body.lstrip())
                    if ok_ins:
                        st.session_state["status_toast"] = "Frontmatter blocks inserted."
                        st.rerun()

            col_fma1, col_fma2 = st.columns(2)
            with col_fma1:
                st.text_area("Abstract", key="fm_abstract_fr", height=90)
                st.text_area("Acknowledgements", key="fm_ack", height=90)
            with col_fma2:
                st.text_area("Translation", key="fm_abstract_en", height=90)
                st.text_area("Abbreviations", key="fm_abbrev", height=90)

    elif active_tab == "Tables":
        st.markdown('<div class="husson-section-label">Automation</div>', unsafe_allow_html=True)
        col_tb1, col_tb2 = st.columns(2)
        with col_tb1:
            st.checkbox(
                "Widths",
                key="opt_colwidths",
                help="Automatic column widths and alignments across PDF, HTML, and DOCX (Lua).",
            )
            st.checkbox(
                "Hyphenation",
                key="opt_hyphenation",
                help="Automatic hyphenation inside table cells (ragged2e).",
            )
            st.checkbox(
                "Labels",
                key="opt_tableau_fr",
                help="Use 'Tableau' instead of 'Table' when document language is French.",
            )
        with col_tb2:
            st.checkbox(
                "Linebreaks",
                key="opt_br_tags",
                help="Convert HTML <br> tags into LaTeX linebreaks inside PDF tables.",
            )
            st.checkbox(
                "Script",
                key="opt_gt_fit",
                help="Inject gt-page-fit.R setup chunk into the document (optional).",
            )

        st.divider()
        st.markdown('<div class="husson-section-label">Diagnostics</div>', unsafe_allow_html=True)
        if not legacy_tweaks:
            st.caption("Clean")
        else:
            for item in legacy_tweaks:
                st.markdown(f"- {item}")
            if st.button("Clean", key="btn_clean_legacy", help="Remove obsolete manual calls (backed up in scratch/)."):
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

            col_tol1, col_tol2, col_tol3, col_tol4 = st.columns([3, 2, 2, 2], vertical_alignment="bottom")
            with col_tol1:
                sel_tab_model = st.selectbox(
                    "Model",
                    options=ollama_models_tab,
                    index=def_idx_tab,
                    key="tab_ollama_model",
                )
            with col_tol2:
                btn_check_doc = st.button("Check", use_container_width=True, key="btn_check_doc_yaml", help="Check active YAML configuration.")
            with col_tol3:
                last_comp_tab = st.session_state.get("last_compilation")
                has_error = bool(last_comp_tab and last_comp_tab.get("return_code", 0) != 0)
                btn_explain_err = st.button(
                    "Explain",
                    use_container_width=True,
                    key="btn_explain_last_err",
                    disabled=not has_error,
                    help="Explain last compilation error.",
                )
            with col_tol4:
                btn_clear_chat = st.button("Clear", use_container_width=True, key="btn_clear_chat")

            if btn_clear_chat:
                st.session_state["chat_messages"] = []
                st.rerun()

            chat_container = st.container(height=420, border=True)
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
