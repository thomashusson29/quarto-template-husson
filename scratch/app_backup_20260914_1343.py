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
import json
import urllib.request
import urllib.error
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


def find_project_root(file_path: Path) -> Path:
    """Trouve la racine du projet Quarto (contenant _quarto.yml ou .git) en remontant l'arborescence."""
    curr = file_path.resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / "_quarto.yml").exists() or (parent / ".git").exists():
            return parent
    return curr


def ensure_extension_installed(target_path: Path):
    """
    Assure que le dossier _extensions/husson est installe en dossier physique reel
    (et non en lien symbolique, que Quarto ignore) dans le dossier du projet et du fichier.
    Cree egalement _quarto.yml a la racine du projet si absent pour que Positron/Quarto
    reconnaisse le projet unifie et les formats husson-*.
    """
    if not TEMPLATE_EXTENSION_DIR.exists():
        return False, f"Dossier source de l'extension introuvable : {TEMPLATE_EXTENSION_DIR}"

    project_root = find_project_root(target_path)
    locations = {project_root}
    if target_path.parent.resolve() != project_root.resolve():
        locations.add(target_path.parent)

    for loc in locations:
        ext_dir = loc / "_extensions"
        husson_dir = ext_dir / "husson"

        if husson_dir.resolve() == TEMPLATE_EXTENSION_DIR.resolve() and not husson_dir.is_symlink():
            continue

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

    q_yml = project_root / "_quarto.yml"
    if not q_yml.exists():
        try:
            default_q_yml = (
                "project:\n"
                "  type: default\n\n"
                "format:\n"
                "  husson-pdf: default\n"
                "  husson-html: default\n"
            )
            q_yml.write_text(default_q_yml, encoding="utf-8")
        except Exception:
            pass

    return True, "Extension Husson physique installee et projet Quarto configure."


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


def find_output_file(target_path: Path, ext: str) -> Path:
    """Localise le fichier produit, que output-dir soit defini ou non dans _quarto.yml."""
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
    """Recupere la liste des modeles disponibles sur le serveur Ollama local."""
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
        if any(marker in lower for marker in [
            "! latex error", "! package", "! undefined control sequence",
            "pandoc error", "quarto error", "error:", "fatal error",
            "stack traceback:", "compilation failed", "emergency stop",
            "no such file or directory"
        ]):
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
    """Generateur de streaming pour la reponse Ollama via /api/generate."""
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.1
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Quarto-Husson-Studio"}
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
        yield f"Erreur HTTP Ollama ({e.code} : {e.reason}). Verifiez que le modele '{model}' est installe localement."
    except Exception as e:
        yield f"Erreur lors de la communication avec Ollama : {e}"


def stream_ollama_chat_response(model: str, messages: list, system_prompt: str = "", base_url: str = OLLAMA_API_URL):
    """Generateur de streaming pour la conversation multi-tours Ollama via /api/chat."""
    url = f"{base_url.rstrip('/')}/api/chat"
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    for m in messages:
        full_messages.append({"role": m["role"], "content": m["content"]})

    payload = json.dumps({
        "model": model,
        "messages": full_messages,
        "stream": True,
        "options": {
            "temperature": 0.2
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Quarto-Husson-Studio"}
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
        yield f"Erreur HTTP Ollama ({e.code} : {e.reason}). Verifiez que le modele '{model}' est disponible localement."
    except Exception as e:
        yield f"Erreur lors de la communication avec Ollama : {e}"


def build_chat_system_prompt(target_path: Path, yaml_data: dict, last_comp: dict = None) -> str:
    """Construit un en-tete systeme contextualise pour l'assistant Ollama."""
    stream_yaml = StringIO()
    yaml_parser.dump(yaml_data, stream_yaml)
    curr_yaml_str = stream_yaml.getvalue()

    last_error_info = ""
    if last_comp and last_comp.get("return_code", 0) != 0:
        err_snip = extract_error_snippet(last_comp.get("terminal_lines", []))
        last_error_info = f"\nDerniere erreur de compilation Quarto survenue :\n```text\n{err_snip}\n```\n"

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

# Verification et installation physique de l'extension Husson
ext_ok, ext_msg = ensure_extension_installed(target_path)

# Informations sur le fichier actif
col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    st.markdown(f"**Document actif :** `{target_path.name}`")
    st.caption(f"Emplacement : `{target_path.parent}`")
with col_info2:
    if ext_ok:
        st.success("Template Husson actif", icon=None)
    else:
        st.warning(ext_msg, icon=None)

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
cur_fontsize = str(yaml_data.get("fontsize", ""))
cur_linestretch = str(yaml_data.get("linestretch", ""))

# Si non trouves a la racine, chercher dans format.husson-pdf ou format.pdf
formats_raw = yaml_data.get("format", {})
if isinstance(formats_raw, dict):
    for fkey in ("husson-pdf", "pdf"):
        if fkey in formats_raw and isinstance(formats_raw[fkey], dict):
            if not cur_font:
                cur_font = formats_raw[fkey].get("mainfont", None)
            if not cur_fontsize and "fontsize" in formats_raw[fkey]:
                cur_fontsize = str(formats_raw[fkey]["fontsize"])
            if not cur_linestretch and "linestretch" in formats_raw[fkey]:
                cur_linestretch = str(formats_raw[fkey]["linestretch"])

if not cur_fontsize:
    cur_fontsize = "11pt"
if not cur_linestretch:
    cur_linestretch = "1.15"

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
    st.session_state.pop("last_compilation", None)
    st.session_state.pop("last_diagnosis", None)

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
tab_formats, tab_typo, tab_cover, tab_tables, tab_ollama = st.tabs([
    "Formats de sortie",
    "Typographie & Metadonnees",
    "Page de Garde & Institution",
    "Tableaux & Options Husson",
    "Assistant Ollama (Local)"
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

with tab_ollama:
    st.markdown("**Assistant conversationnel local (Ollama) :**")
    ollama_models_tab = get_ollama_models()
    if not ollama_models_tab:
        st.info(
            "Le serveur Ollama local n'est pas actif sur http://localhost:11434. "
            "Pour beneficier de l'assistance locale, lancez 'ollama serve' dans votre terminal."
        )
    else:
        # Initialisation de l'historique de conversation
        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = []

        def_idx_tab = 0
        for i, m in enumerate(ollama_models_tab):
            if "coder" in m.lower():
                def_idx_tab = i
                break
            elif "qwen" in m.lower():
                def_idx_tab = i

        col_tol1, col_tol2, col_tol3, col_tol4 = st.columns([3, 2, 2, 2])
        with col_tol1:
            sel_tab_model = st.selectbox(
                "Modele Ollama :",
                options=ollama_models_tab,
                index=def_idx_tab,
                key="tab_ollama_model"
            )
        with col_tol2:
            st.write("")
            btn_check_doc = st.button("Verifier YAML", use_container_width=True, key="btn_check_doc_yaml")
        with col_tol3:
            st.write("")
            last_comp_tab = st.session_state.get("last_compilation")
            has_error = bool(last_comp_tab and last_comp_tab.get("return_code", 0) != 0)
            btn_explain_err = st.button(
                "Expliquer erreur",
                use_container_width=True,
                key="btn_explain_last_err",
                disabled=not has_error
            )
        with col_tol4:
            st.write("")
            btn_clear_chat = st.button("Effacer l'historique", use_container_width=True, key="btn_clear_chat")

        if btn_clear_chat:
            st.session_state["chat_messages"] = []
            st.rerun()

        st.caption(
            f"Modele actif : `{sel_tab_model}` -- "
            f"Document contextuel : `{target_path.name}` ({len(st.session_state['chat_messages'])} message(s) en memoire)"
        )
        st.divider()

        # Zone d'affichage des messages precedents avec defilement
        chat_container = st.container(height=480)
        with chat_container:
            if not st.session_state["chat_messages"]:
                st.info(
                    "Bienvenue dans l'assistant Quarto Husson. Posez vos questions sur la mise en page, "
                    "les options YAML, les tableaux, les erreurs de compilation ou le code R/LaTeX."
                )
            for msg in st.session_state["chat_messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Zone de saisie directe situee immediatement sous le fil de discussion
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
            "Ecrivez votre message a l'assistant Ollama (Appuyez sur Entree pour envoyer)...",
            key="chat_input_field"
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
                        st.session_state.get("last_compilation")
                    )
                    full_response = []
                    def token_generator():
                        for token in stream_ollama_chat_response(
                            sel_tab_model,
                            st.session_state["chat_messages"],
                            sys_prompt
                        ):
                            full_response.append(token)
                            yield token
                    st.write_stream(token_generator())
                    st.session_state["chat_messages"].append({"role": "assistant", "content": "".join(full_response)})
            st.rerun()


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

    # Format PDF : transformation en husson-pdf et preservation de la configuration
    if st.session_state.opt_pdf:
        existing_pdf = {}
        if "husson-pdf" in d["format"] and isinstance(d["format"]["husson-pdf"], dict):
            existing_pdf = dict(d["format"]["husson-pdf"])
        elif "pdf" in d["format"] and isinstance(d["format"]["pdf"], dict):
            existing_pdf = dict(d["format"]["pdf"])

        existing_pdf["pdf-engine"] = "xelatex"
        existing_pdf["documentclass"] = existing_pdf.get("documentclass", "scrartcl")
        existing_pdf["toc"] = opt_toc
        existing_pdf["toc-depth"] = opt_toc_depth
        existing_pdf["number-sections"] = opt_num_sections
        existing_pdf["fontsize"] = st.session_state.sel_fontsize
        existing_pdf["linestretch"] = float(st.session_state.sel_linestretch)

        # Nettoyage des partials redondants qui pointent vers _extensions/husson
        # car l'extension husson-pdf les injecte nativement
        partials = [p for p in existing_pdf.get("template-partials", []) if "husson" not in str(p)]
        if partials:
            existing_pdf["template-partials"] = partials
        elif "template-partials" in existing_pdf:
            del existing_pdf["template-partials"]

        # Nettoyage des headers redondants
        raw_headers = existing_pdf.get("include-in-header", [])
        if isinstance(raw_headers, list):
            headers = [h for h in raw_headers if "pdf-header.tex" not in str(h)]
            if headers:
                existing_pdf["include-in-header"] = headers
            elif "include-in-header" in existing_pdf:
                del existing_pdf["include-in-header"]

        # Nettoyage des filtres redondants deja fournis par l'extension
        flts = [f for f in existing_pdf.get("filters", []) if "husson" not in str(f)]
        if flts:
            existing_pdf["filters"] = flts
        elif "filters" in existing_pdf:
            del existing_pdf["filters"]

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

        d["format"]["husson-pdf"] = existing_pdf
        if "pdf" in d["format"]:
            del d["format"]["pdf"]
    elif "husson-pdf" in d["format"]:
        del d["format"]["husson-pdf"]

    # Format HTML : transformation en husson-html
    if st.session_state.opt_html:
        existing_html = {}
        if "husson-html" in d["format"] and isinstance(d["format"]["husson-html"], dict):
            existing_html = dict(d["format"]["husson-html"])
        elif "html" in d["format"] and isinstance(d["format"]["html"], dict):
            existing_html = dict(d["format"]["html"])

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
        d["format"]["husson-html"] = existing_html
        if "html" in d["format"]:
            del d["format"]["html"]
    elif "husson-html" in d["format"]:
        del d["format"]["husson-html"]

    # Format Word : transformation en husson-docx
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
    elif "husson-docx" in d["format"]:
        del d["format"]["husson-docx"]

    # Format RevealJS : transformation en husson-revealjs
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
    elif "husson-revealjs" in d["format"]:
        del d["format"]["husson-revealjs"]

    # Reordonnancement des formats : husson-pdf EN PREMIER si actif pour Positron/RStudio
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

    # Configuration Page de Garde / These
    if st.session_state.opt_thesis_active:
        thesis_dict = dict(yaml_data.get("thesis", {})) if isinstance(yaml_data.get("thesis"), dict) else {}

        resolved_logo = None
        if sel_logo == "Université Paris-Saclay":
            existing_logo = thesis_dict.get("logo", "")
            if existing_logo and "paris-saclay" in str(existing_logo):
                resolved_logo = existing_logo
            else:
                resolved_logo = "logo-universite-paris-saclay.png"
        elif sel_logo == "Université Paris Cité":
            existing_logo = thesis_dict.get("logo", "")
            if existing_logo and "paris-cite" in str(existing_logo):
                resolved_logo = existing_logo
            else:
                resolved_logo = "logo-universite-paris-cite.png"
        elif sel_logo == "Personnalise..." and custom_logo_path.strip():
            resolved_logo = custom_logo_path.strip()

        if th_university.strip():
            thesis_dict["university"] = th_university
        if th_faculty.strip():
            thesis_dict["faculty"] = th_faculty
        if th_degree.strip():
            thesis_dict["degree"] = th_degree
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
        target_formats.append("husson-pdf")
    if st.session_state.opt_html:
        target_formats.append("husson-html")
    if st.session_state.opt_docx:
        target_formats.append("husson-docx")
    if st.session_state.opt_reveal:
        target_formats.append("husson-revealjs")

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

        stream_yaml = StringIO()
        yaml_parser.dump(new_yaml, stream_yaml)
        saved_yaml_str = stream_yaml.getvalue()

        st.session_state["last_compilation"] = {
            "target_path": str(target_path),
            "cmd": cmd,
            "return_code": return_code,
            "terminal_lines": terminal_lines,
            "yaml_str": saved_yaml_str,
            "elapsed_str": elapsed_str
        }
        st.session_state.pop("last_diagnosis", None)

        if return_code == 0:
            status_box.update(label=f"Compilation terminee avec succes ({elapsed_str})", state="complete", expanded=False)
            st.success(f"Document compile avec succes en {elapsed_str}.")
        else:
            status_box.update(label=f"Erreur de compilation (code {return_code})", state="error", expanded=True)
            st.error(f"Erreur lors de la compilation (code {return_code}). Consultez le journal ci-dessus.")

# --- ACTIONS ET DIAGNOSTIC POST-COMPILATION ---
last_comp = st.session_state.get("last_compilation")
if last_comp and last_comp.get("target_path") == str(target_path):
    ret_c = last_comp.get("return_code")
    if ret_c == 0:
        pdf_out = find_output_file(target_path, ".pdf")
        html_out = find_output_file(target_path, ".html")
        docx_out = find_output_file(target_path, ".docx")

        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        with col_res1:
            if st.session_state.opt_pdf and pdf_out.exists():
                if st.button("Ouvrir le PDF", use_container_width=True, key="btn_open_pdf"):
                    subprocess.run(["open", str(pdf_out)])
        with col_res2:
            if st.session_state.opt_html and html_out.exists():
                if st.button("Ouvrir le HTML", use_container_width=True, key="btn_open_html"):
                    subprocess.run(["open", str(html_out)])
        with col_res3:
            if st.session_state.opt_docx and docx_out.exists():
                if st.button("Ouvrir le document Word", use_container_width=True, key="btn_open_docx"):
                    subprocess.run(["open", str(docx_out)])
        with col_res4:
            if st.button("Ouvrir le dossier (Finder)", use_container_width=True, key="btn_open_finder"):
                subprocess.run(["open", str(target_path.parent)])

        if auto_open:
            if st.session_state.opt_pdf and pdf_out.exists():
                subprocess.run(["open", str(pdf_out)])
            elif st.session_state.opt_html and html_out.exists():
                subprocess.run(["open", str(html_out)])

    else:
        # Code de retour != 0 : Section Diagnostic & Resolution par IA locale (Ollama)
        st.divider()
        st.subheader("Diagnostic et resolution par IA locale (Ollama)")
        ollama_models = get_ollama_models()
        if not ollama_models:
            st.info(
                "Serveur Ollama local non detecte sur http://localhost:11434. "
                "Demarrez Ollama dans votre terminal (ollama serve) pour activer l'analyse automatique d'erreurs."
            )
        else:
            default_idx = 0
            for idx, m in enumerate(ollama_models):
                if "coder" in m.lower():
                    default_idx = idx
                    break
                elif "qwen" in m.lower():
                    default_idx = idx

            col_diag1, col_diag2 = st.columns([2, 3])
            with col_diag1:
                diag_model = st.selectbox(
                    "Modele local pour le diagnostic :",
                    options=ollama_models,
                    index=default_idx,
                    key="diag_model_select"
                )
            with col_diag2:
                st.write("")
                btn_run_diag = st.button(
                    "Analyser l'erreur et proposer une correction",
                    type="primary",
                    use_container_width=True,
                    key="btn_run_ollama_diagnosis"
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
                st.markdown(f"**Analyse de l'erreur en cours par `{diag_model}`...**")
                with st.chat_message("assistant"):
                    full_resp = []
                    def token_collector():
                        for t in stream_ollama_response(diag_model, diag_prompt):
                            full_resp.append(t)
                            yield t
                    diagnosis_str = "".join(full_resp)
                    st.session_state["last_diagnosis"] = diagnosis_str
                    if "chat_messages" not in st.session_state:
                        st.session_state["chat_messages"] = []
                    st.session_state["chat_messages"].append({
                        "role": "user",
                        "content": "J'ai rencontre une erreur lors de la compilation. Peux-tu m'expliquer le probleme et proposer une solution ?"
                    })
                    st.session_state["chat_messages"].append({
                        "role": "assistant",
                        "content": diagnosis_str
                    })
                    st.info("Ce diagnostic a ete ajoute a votre conversation dans l'onglet 'Assistant Ollama (Local)'. Vous pouvez y poursuivre l'echange pour approfondir.")

            elif "last_diagnosis" in st.session_state and st.session_state["last_diagnosis"]:
                st.markdown("**Precedent diagnostic de resolution :**")
                with st.chat_message("assistant"):
                    st.markdown(st.session_state["last_diagnosis"])
