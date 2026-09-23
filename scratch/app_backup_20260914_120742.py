#!/usr/bin/env python3
"""
Quarto Husson Studio
Interface graphique interactive pour configurer et compiler vos documents Quarto
avec le template Husson (PDF, HTML, DOCX, RevealJS, Thèse, Tableaux).
"""

import os
import sys
import re
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import streamlit as st
from ruamel.yaml import YAML

# Initialisation de ruamel.yaml
yaml_parser = YAML()
yaml_parser.preserve_quotes = True
yaml_parser.indent(mapping=2, sequence=4, offset=2)

TEMPLATE_REPO_PATH = Path("/Users/thomashusson/Documents/Projets/quarto-template-husson")
TEMPLATE_EXTENSION_DIR = TEMPLATE_REPO_PATH / "_extensions" / "husson"

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Quarto Husson Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Injection de styles CSS pour un rendu soigné
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #17365D;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .badge-success {
        background-color: #d4edda;
        color: #155724;
        padding: 0.35rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.35rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .terminal-box {
        background-color: #1e1e1e;
        color: #d4d4d4;
        font-family: 'SF Mono', Menlo, Monaco, 'Courier New', monospace;
        font-size: 0.88rem;
        line-height: 1.45;
        padding: 1rem;
        border-radius: 8px;
        max-height: 450px;
        overflow-y: auto;
        white-space: pre-wrap;
        border: 1px solid #333;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def find_recent_qmd_files(base_dir: Path, max_files: int = 15):
    """Recherche les fichiers .qmd récents dans les dossiers de projets."""
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
    """Assure que le dossier _extensions/husson est lié dans le dossier du projet."""
    ext_dir = project_dir / "_extensions"
    husson_link = ext_dir / "husson"
    if not husson_link.exists():
        ext_dir.mkdir(parents=True, exist_ok=True)
        try:
            husson_link.symlink_to(TEMPLATE_EXTENSION_DIR, target_is_directory=True)
            return True, "Lien symbolique vers _extensions/husson créé avec succès."
        except Exception as e:
            return False, f"Erreur lors de la création du lien symbolique : {e}"
    return True, "Extension présente."


def parse_qmd(file_path: Path):
    """Lit un fichier .qmd et sépare son YAML frontmatter du corps Markdown."""
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
                return {}, body_raw, f"YAML invalide ou non parsable : {e}"
    return {}, content, None


def save_qmd_with_backup(file_path: Path, yaml_data: dict, body: str):
    """Sauvegarde le fichier .qmd avec sauvegarde préventive automatique."""
    # Sauvegarde préventive dans scratch/
    scratch_dir = file_path.parent / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = scratch_dir / f"{file_path.stem}_backup_{timestamp}.qmd"
    
    try:
        shutil.copy2(file_path, backup_path)
    except Exception as e:
        return False, f"Échec de la sauvegarde préventive : {e}", None

    # Écriture du nouveau contenu
    try:
        from io import StringIO
        stream = StringIO()
        yaml_parser.dump(yaml_data, stream)
        new_yaml_str = stream.getvalue()
        
        # Réassemblage
        new_content = f"---\n{new_yaml_str}---\n{body.lstrip()}"
        file_path.write_text(new_content, encoding="utf-8")
        return True, f"Fichier sauvegardé avec succès. Copie de sécurité créée dans : {backup_path.name}", backup_path
    except Exception as e:
        return False, f"Erreur lors de l'écriture : {e}", None


# --- EN-TÊTE ---
st.markdown('<div class="main-header">Quarto Husson Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Interface graphique pour configurer, personnaliser et compiler vos documents Quarto en toute simplicité.</div>', unsafe_allow_html=True)

# --- SÉLECTION DU FICHIER ---
st.sidebar.header("Document Quarto")

# Recherche de fichiers récents
recent_files = find_recent_qmd_files(Path("/Users/thomashusson/Documents/Projets"))
options_files = ["-- Sélectionner un fichier récent --"] + recent_files

selected_recent = st.sidebar.selectbox("Fichiers récents :", options=options_files)

# Saisie manuelle de chemin ou uploader
manual_path = st.sidebar.text_input("Ou chemin direct vers le fichier .qmd :", 
    value=selected_recent if selected_recent != options_files[0] else "/Users/thomashusson/Documents/Projets/M2transplantation/docs/M2_transplant_v2.qmd")

uploaded_file = st.sidebar.file_uploader("Ou glisser-déposer un fichier .qmd :", type=["qmd"])

target_path = None
if manual_path and Path(manual_path).exists():
    target_path = Path(manual_path).resolve()
elif uploaded_file is not None:
    # Si uploadé, on le sauve temporairement dans scratch du template
    temp_dir = TEMPLATE_REPO_PATH / "scratch"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / uploaded_file.name
    temp_file.write_bytes(uploaded_file.getvalue())
    target_path = temp_file

if not target_path or not target_path.exists():
    st.info("Veuillez sélectionner ou renseigner un fichier `.qmd` valide dans la barre latérale pour commencer.")
    st.stop()

# Vérification du lien symbolique d'extension
symlink_ok, symlink_msg = ensure_symlink(target_path.parent)

# Affichage des informations sur le fichier
col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    st.markdown(f"**Document actif :** `{target_path.name}` *(dans `{target_path.parent}`)*")
with col_f2:
    if symlink_ok:
        st.markdown('<span class="badge-success">Template lié</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="badge-warning">{symlink_msg}</span>', unsafe_allow_html=True)

# Parse du fichier
yaml_data, markdown_body, err = parse_qmd(target_path)
if err:
    st.error(err)
    st.stop()

# --- SÉLECTEUR DE MODE ---
st.write("")
mode_choice = st.radio("Mode de configuration :", ["Mode Rapide (Profils prêts à l'emploi)", "Mode Avancé (Personnalisation complète)"], horizontal=True)

# Extraction des valeurs existantes du YAML
cur_title = yaml_data.get("title", "")
cur_subtitle = yaml_data.get("subtitle", "")
cur_author = yaml_data.get("author", "Thomas Husson")
cur_lang = yaml_data.get("lang", "fr")
cur_font = yaml_data.get("mainfont", yaml_data.get("font", "Times New Roman"))
cur_fontsize = yaml_data.get("fontsize", "11pt")
cur_linestretch = str(yaml_data.get("linestretch", "1.15"))

# Détection des formats
formats_data = yaml_data.get("format", {})
if isinstance(formats_data, str):
    formats_data = {formats_data: {}}
elif not isinstance(formats_data, dict):
    formats_data = {}

has_pdf = "pdf" in formats_data or "husson-pdf" in formats_data
has_html = "html" in formats_data or "husson-html" in formats_data
has_docx = "docx" in formats_data or "husson-docx" in formats_data
has_reveal = "revealjs" in formats_data or "husson-revealjs" in formats_data

# Thèse
thesis_data = yaml_data.get("thesis", {})
has_thesis = bool(thesis_data)
if not isinstance(thesis_data, dict):
    thesis_data = {}

# --- GESTION DU MODE RAPIDE ---
if "Rapide" in mode_choice:
    st.subheader("Profils recommandés")
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.markdown("### Thèse / Mémoire")
        st.caption("PDF officiel avec page de garde millimétrée, Times 11pt, interligne 1.15, jury, largeurs auto et césures.")
        p_thesis = st.button("Appliquer profil Thèse", use_container_width=True)
        
    with col_p2:
        st.markdown("### Article / Rapport")
        st.caption("PDF + HTML synchronisés, typographie soignée, thème One Dark réactif, sans page de garde de thèse.")
        p_article = st.button("Appliquer profil Article", use_container_width=True)

    with col_p3:
        st.markdown("### Présentation RevealJS")
        st.caption("Diapositives interactives RevealJS avec bascule claire/sombre automatique, adaptée pour soutenance.")
        p_reveal = st.button("Appliquer profil Présentation", use_container_width=True)

    if p_thesis:
        has_pdf = True
        has_html = False
        has_docx = False
        has_reveal = False
        has_thesis = True
        cur_font = "Times New Roman"
        cur_fontsize = "11pt"
        cur_linestretch = "1.15"
        st.success("Profil Thèse / Mémoire sélectionné.")

    if p_article:
        has_pdf = True
        has_html = True
        has_docx = False
        has_reveal = False
        has_thesis = False
        st.success("Profil Article / Rapport sélectionné.")

    if p_reveal:
        has_pdf = False
        has_html = False
        has_docx = False
        has_reveal = True
        has_thesis = False
        st.success("Profil Présentation RevealJS sélectionné.")

# --- FORMULAIRE D'OPTIONS (MODE AVANCÉ & PARAMÈTRES) ---
st.write("---")

tab_formats, tab_typo, tab_thesis, tab_tables = st.tabs([
    "Formats de sortie", 
    "Typographie & Document", 
    "Mode Thèse & Jury", 
    "Tableaux & Optimisations"
])

with tab_formats:
    st.markdown("##### Choisissez les formats à générer :")
    col_fmt1, col_fmt2, col_fmt3, col_fmt4 = st.columns(4)
    with col_fmt1:
        opt_pdf = st.checkbox("PDF (husson-pdf)", value=has_pdf, help="Rendu XeLaTeX de haute qualité avec typographie calibrée.")
    with col_fmt2:
        opt_html = st.checkbox("HTML (husson-html)", value=has_html, help="Rendu Web avec thème One Dark réactif clair/sombre.")
    with col_fmt3:
        opt_docx = st.checkbox("Word (husson-docx)", value=has_docx, help="Fichier Word stylisé avec le modèle embarqué.")
    with col_fmt4:
        opt_reveal = st.checkbox("RevealJS (husson-revealjs)", value=has_reveal, help="Diaporama interactif pour présentation.")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        opt_toc = st.checkbox("Table des matières (TOC)", value=True)
        opt_toc_depth = st.slider("Profondeur de la TOC", min_value=1, max_value=4, value=3)
    with col_meta2:
        opt_num_sections = st.checkbox("Numérotation des sections", value=True)
        opt_lang = st.selectbox("Langue principale :", ["fr", "en"], index=0 if cur_lang == "fr" else 1)

with tab_typo:
    st.markdown("##### Métadonnées du document :")
    in_title = st.text_input("Titre du document :", value=str(cur_title))
    in_subtitle = st.text_input("Sous-titre :", value=str(cur_subtitle))
    in_author = st.text_input("Auteur :", value=str(cur_author))

    st.markdown("##### Paramètres de police et mise en page :")
    col_t1, col_t2, col_t3 = st.columns(3)
    font_options = ["Times New Roman", "Garamond", "Roboto", "Carlito", "Personnalisée..."]
    default_font_idx = 0
    for idx, f in enumerate(font_options):
        if f.lower() in str(cur_font).lower():
            default_font_idx = idx
            break
            
    with col_t1:
        sel_font = st.selectbox("Police de caractères :", font_options, index=default_font_idx)
        if sel_font == "Personnalisée...":
            sel_font = st.text_input("Nom de la police système :", value=str(cur_font))
    with col_t2:
        sel_fontsize = st.selectbox("Taille du texte (corps) :", ["10pt", "11pt", "12pt"], index=1 if cur_fontsize == "11pt" else 0)
    with col_t3:
        sel_linestretch = st.selectbox("Interligne :", ["1.0", "1.15", "1.25", "1.5"], index=1 if cur_linestretch == "1.15" else 0)

with tab_thesis:
    opt_thesis_active = st.checkbox("Activer la page de garde officielle de Thèse / Mémoire", value=has_thesis)
    
    if opt_thesis_active:
        col_th1, col_th2 = st.columns(2)
        with col_th1:
            th_university = st.text_input("Université :", value=thesis_data.get("university", "Université Paris-Saclay"))
            th_faculty = st.text_input("Faculté :", value=thesis_data.get("faculty", "Faculté de Médecine"))
            th_degree = st.text_input("Intitulé du Diplôme :", value=thesis_data.get("degree", "Mémoire de Master 2 Sciences Chirurgicales"))
        with col_th2:
            th_dept = st.text_input("Service / Hôpital :", value=thesis_data.get("department", "Centre Hépato-Biliaire, Hôpital Paul Brousse, AP-HP"))
            th_lab = st.text_input("Laboratoire / Unité :", value=thesis_data.get("laboratory", "Inserm UMR-S 1193, Université Paris-Saclay"))
            th_date = st.text_input("Date de soutenance :", value=thesis_data.get("date", "7 octobre 2026"))

        st.markdown("###### Directeurs de recherche :")
        directors_list = thesis_data.get("directors", [])
        d1_name = directors_list[0].get("name", "Pr Claire GOUMARD") if len(directors_list) > 0 else ""
        d1_title = directors_list[0].get("title", "PU-PH") if len(directors_list) > 0 else ""
        d1_role = directors_list[0].get("role", "Dirigé") if len(directors_list) > 0 else ""

        d2_name = directors_list[1].get("name", "Dr Jérémie GAUTHERON") if len(directors_list) > 1 else ""
        d2_title = directors_list[1].get("title", "CR, Inserm UMR-S 938") if len(directors_list) > 1 else ""
        d2_role = directors_list[1].get("role", "Et co-dirigé") if len(directors_list) > 1 else ""

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            th_d1_name = st.text_input("Directeur 1 - Nom :", value=d1_name)
        with col_d2:
            th_d1_title = st.text_input("Directeur 1 - Titre :", value=d1_title)
        with col_d3:
            th_d1_role = st.text_input("Directeur 1 - Rôle :", value=d1_role)

        col_d2_1, col_d2_2, col_d2_3 = st.columns(3)
        with col_d2_1:
            th_d2_name = st.text_input("Directeur 2 - Nom (optionnel) :", value=d2_name)
        with col_d2_2:
            th_d2_title = st.text_input("Directeur 2 - Titre :", value=d2_title)
        with col_d2_3:
            th_d2_role = st.text_input("Directeur 2 - Rôle :", value=d2_role)

with tab_tables:
    st.markdown("##### Optimisations des tableaux (Husson Engine) :")
    opt_colwidths = st.checkbox("Calcul automatique universel des largeurs de colonnes (Lua)", value=True, 
                                help="Calcule les largeurs relatives en fonction du contenu réel pour éviter tout débordement.")
    opt_hyphenation = st.checkbox("Césures automatiques en français dans les cellules (ragged2e)", value=True,
                                  help="Active la césure native TeX/Babel dans les cellules de tableau.")
    opt_tableau_fr = st.checkbox("Appeler automatiquement 'Tableau' au lieu de 'Table' en français", value=(opt_lang == "fr"),
                                 help="Harmonise les références croisées et titres sous 'Tableau 1' si lang: fr.")
    opt_br_tags = st.checkbox("Convertir automatiquement les balises <br> en retours à la ligne réels", value=True,
                              help="Évite que les lignes séparées par <br> ne soient fusionnées sans espace en LaTeX.")
    opt_gt_fit = st.checkbox("Activer l'ajustement R pour tableaux gt / gtsummary (gt-page-fit.R)", value=False,
                             help="Injecte un chunk R pour initialiser husson_tables_on() au début du document.")


# --- FONCTIONS DE SYNCHRONISATION ---
def build_updated_yaml():
    """Génère la structure YAML mise à jour à partir du formulaire."""
    d = dict(yaml_data)
    d["title"] = in_title
    if in_subtitle:
        d["subtitle"] = in_subtitle
    d["author"] = in_author
    d["lang"] = opt_lang

    # Localisation Tableau si français
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
    if opt_pdf:
        pdf_conf = {
            "toc": opt_toc,
            "toc-depth": opt_toc_depth,
            "number-sections": opt_num_sections,
            "pdf-engine": "xelatex",
            "documentclass": "scrartcl",
            "mainfont": sel_font,
            "fontsize": sel_fontsize,
            "linestretch": float(sel_linestretch),
            "template-partials": ["_extensions/husson/before-body.tex"],
            "filters": ["_extensions/husson/table-column-widths.lua"]
        }
        if opt_lang == "fr" and opt_tableau_fr:
            pdf_conf["language"] = {
                "fr": {
                    "crossref-tbl-title": "Tableau",
                    "crossref-tbl-prefix": "Tableau",
                    "crossref-lot-title": "Liste des tableaux"
                }
            }
        new_formats["pdf"] = pdf_conf

    if opt_html:
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

    if opt_docx:
        new_formats["docx"] = {
            "toc": opt_toc,
            "toc-depth": opt_toc_depth,
            "number-sections": opt_num_sections,
            "reference-doc": "_extensions/husson/template.docx"
        }

    if opt_reveal:
        new_formats["revealjs"] = {
            "theme": ["default", "_extensions/husson/auto-dark-clean.scss"],
            "slide-number": True,
            "transition": "none"
        }

    d["format"] = new_formats

    # Thèse
    if opt_thesis_active:
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
    
    # Intégration dans le header-includes du PDF
    if "pdf" in d["format"]:
        d["format"]["pdf"]["header-includes"] = "\n".join(header_lines) + "\n"

    return d


# --- BARRE D'ACTIONS ---
st.write("")
col_act1, col_act2, col_act3 = st.columns([2, 3, 2])

with col_act1:
    btn_save = st.button("Enregistrer dans le .qmd", use_container_width=True)

with col_act2:
    btn_render = st.button("Lancer la compilation (quarto render)", type="primary", use_container_width=True)

with col_act3:
    auto_open = st.checkbox("Ouvrir le fichier après le rendu", value=True)

# Sauvegarde manuelle
if btn_save:
    new_yaml = build_updated_yaml()
    body_to_save = markdown_body
    
    # Si option gt_fit cochée et absente
    if opt_gt_fit and "husson_tables_on" not in body_to_save:
        r_chunk = "\n```{r setup-husson-tables, include=FALSE}\nif (file.exists(\"_extensions/husson/gt-page-fit.R\")) {\n  source(\"_extensions/husson/gt-page-fit.R\")\n  husson_tables_on()\n}\n```\n\n"
        body_to_save = r_chunk + body_to_save

    ok, msg, bpath = save_qmd_with_backup(target_path, new_yaml, body_to_save)
    if ok:
        st.success(msg)
    else:
        st.error(msg)

# Exécution du Render
if btn_render:
    # 1. Sauvegarde automatique préalable
    new_yaml = build_updated_yaml()
    body_to_save = markdown_body
    if opt_gt_fit and "husson_tables_on" not in body_to_save:
        r_chunk = "\n```{r setup-husson-tables, include=FALSE}\nif (file.exists(\"_extensions/husson/gt-page-fit.R\")) {\n  source(\"_extensions/husson/gt-page-fit.R\")\n  husson_tables_on()\n}\n```\n\n"
        body_to_save = r_chunk + body_to_save
    
    ok, msg, bpath = save_qmd_with_backup(target_path, new_yaml, body_to_save)
    if not ok:
        st.error(f"Impossible de sauvegarder avant le rendu : {msg}")
        st.stop()
    
    st.caption(f"Sauvegarde préventive créée : `{bpath.name}`")

    # 2. Détermination des formats demandés
    target_formats = []
    if opt_pdf:
        target_formats.append("pdf")
    if opt_html:
        target_formats.append("html")
    if opt_docx:
        target_formats.append("docx")
    if opt_reveal:
        target_formats.append("revealjs")

    if not target_formats:
        st.warning("Veuillez cocher au moins un format de sortie.")
        st.stop()

    # 3. Lancement de la commande
    cmd = ["quarto", "render", str(target_path)]
    if len(target_formats) == 1:
        cmd.extend(["--to", target_formats[0]])

    st.markdown(f"**Commande exécutée :** `{' '.join(cmd)}`")
    terminal_placeholder = st.empty()
    status_placeholder = st.empty()
    
    terminal_logs = []
    start_time = time.time()
    
    with status_placeholder:
        st.info("Compilation en cours... Suivi en direct ci-dessous.")

    # Exécution avec streaming du stdout/stderr
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    process = subprocess.Popen(
        cmd,
        cwd=str(target_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            terminal_logs.append(line)
            # Mise à jour périodique de la zone de terminal (dernières 50 lignes)
            visible_logs = "".join(terminal_logs[-60:])
            terminal_placeholder.markdown(
                f'<div class="terminal-box">{visible_logs}</div>', 
                unsafe_allow_html=True
            )
            time.sleep(0.01)

    return_code = process.poll()
    elapsed = time.time() - start_time
    elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s" if elapsed >= 60 else f"{elapsed:.1f}s"

    # Affichage de tous les logs finaux
    all_logs = "".join(terminal_logs)
    terminal_placeholder.markdown(f'<div class="terminal-box">{all_logs}</div>', unsafe_allow_html=True)

    if return_code == 0:
        status_placeholder.success(f"Rendu terminé avec succès en {elapsed_str} !")
        
        # Détection des fichiers produits
        pdf_out = target_path.with_suffix(".pdf")
        html_out = target_path.with_suffix(".html")
        docx_out = target_path.with_suffix(".docx")

        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            if opt_pdf and pdf_out.exists():
                if st.button("Ouvrir le PDF", use_container_width=True):
                    subprocess.run(["open", str(pdf_out)])
        
        with col_res2:
            if opt_html and html_out.exists():
                if st.button("Ouvrir le HTML", use_container_width=True):
                    subprocess.run(["open", str(html_out)])
                    
        with col_res3:
            if st.button("Ouvrir le dossier (Finder)", use_container_width=True):
                subprocess.run(["open", str(target_path.parent)])

        if auto_open:
            if opt_pdf and pdf_out.exists():
                subprocess.run(["open", str(pdf_out)])
            elif opt_html and html_out.exists():
                subprocess.run(["open", str(html_out)])
    else:
        status_placeholder.error(f"Erreur lors de la compilation (code {return_code}) après {elapsed_str}.")
        st.warning("Consultez la boîte de terminal ci-dessus pour identifier la cause exacte de l'erreur.")
