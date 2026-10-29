# Quarto Template Husson

Extension Quarto universitaire et scientifique fournissant cinq formats prêts à l'emploi à partir d'un unique fichier `.qmd` natif :

| Format | Usage principal | Ce qui est géré automatiquement (sans configuration) |
| :--- | :--- | :--- |
| **`husson-pdf`** | Thèses, mémoires, devoirs, rapports et articles imprimables (A4, XeLaTeX) | Police **Times New Roman** par défaut, tableaux (`kable`, `gt`, `gtsummary`, Markdown) ajustés à 100 % de la largeur sans débordement, barre de navigation haute, pied de page paginé, symboles grecs/cliniques (`≥`, `±`, `α`, `₀`) natifs. |
| **`husson-html`** | Rapports web interactifs et articles scientifiques | Thème clair/sombre automatique (**One Dark Pro**), figures `ggplot2` / `matplotlib` / `plotly` adaptées au mode sombre sans code R/Python requis, sommaire flottant. |
| **`husson-docx`** | Documents Word partageables pour relecture clinique ou académique | Application automatique de la feuille de styles embarquée (`template.docx`), tableaux proportionnels et intitulés francisés (« Tableau »). |
| **`husson-revealjs`** | Diaporamas de soutenance, d'enseignement et de staff | Fil d'Ariane cliquable en haut de diapositive, titres fixes (*sticky*) sur diapositives défilables (`.scrollable`), bascule clair/sombre automatique. |
| **`husson-pptx`** | Export PowerPoint modifiable d’un diaporama RevealJS | Conversion de la mise en page calculée en thème clair en textes et formes PowerPoint, avec images pour les schémas et démonstrations. |

---

## Installation et premier rendu

### Prérequis

- [Quarto](https://quarto.org/docs/get-started/) **1.8 ou plus récent** pour tous les formats.
- Pour `husson-pptx` : [Node.js avec npm](https://nodejs.org/en/download/) et Chromium. Sur macOS, l'export cherche Chromium ou Google Chrome aux emplacements habituels ; ailleurs, indiquez le navigateur avec `CHROMIUM_PATH=/chemin/vers/chromium`.
- Pour `husson-pdf` : une distribution TeX avec XeLaTeX, par exemple MacTeX ou TeX Live. Elle n'est pas requise pour RevealJS, HTML, DOCX ou PPTX.
- Pour l'interface graphique, facultative : Python 3, `streamlit`, `pandas` et `ruamel.yaml`.

Carlito est fournie dans l'extension : aucun téléchargement de police n'est nécessaire. R ou Python ne sont nécessaires que si votre document exécute des blocs de code dans ces langages.

### Cloner et essayer RevealJS

```bash
git clone https://github.com/thomashusson29/quarto-template-husson.git
cd quarto-template-husson
quarto render examples/exemple-pptx.qmd --to husson-revealjs
```

Ouvrez `output/examples/exemple-pptx.html`. Cet exemple utilise des cartes, images, SVG, flèches, onglets et diapositives défilables. Pour exporter le même fichier vers PowerPoint :

```bash
npm ci --prefix _extensions/husson/pptx
quarto render examples/exemple-pptx.qmd --to husson-pptx
```

Le résultat est `output/examples/exemple-pptx.pptx`. Si Chromium n'est pas trouvé, définissez `CHROMIUM_PATH` avant la seconde commande. L'export PPTX utilise le rendu RevealJS clair et transforme les textes et formes compatibles en objets modifiables ; les limites sont détaillées dans [Export PPTX](#export-pptx-modifiable-depuis-revealjs).

### Lancer l'interface graphique (facultatif)

Depuis la racine du clone :

```bash
python3 -m pip install streamlit pandas ruamel.yaml
python3 -m streamlit run gui/app.py
```

Dans **Formats**, choisissez RevealJS et, si souhaité, PPTX. L'interface utilise le dossier où le dépôt a été cloné. Sur macOS, vous pouvez également utiliser [`gui/Quarto GUI.command`](gui/Quarto%20GUI.command) si `streamlit` est disponible dans le `PATH`.

## Démarrage rapide (3 méthodes au choix)

Vous n'avez besoin d'ajouter **aucun script R ni code LaTeX** dans votre document : un fichier `.qmd` standard fonctionne immédiatement.

### Méthode 1 : Avec l'interface graphique Quarto Husson Studio (recommandé pour débuter)

L'application locale **Quarto Husson Studio** est organisée en **3 panneaux horizontaux + 1 panneau Terminal inférieur** (chacun affichable ou masquable via les petits boutons **`Files`**, **`Preview`** et **`Terminal`** situés tout en haut du panneau central) :

1. **Lancement** :
   - Sur macOS : double-cliquez sur [`gui/Quarto GUI.command`](gui/Quarto%20GUI.command).
   - Ou depuis un terminal :
     ```bash
     python3 -m streamlit run gui/app.py
     ```
2. **Panneau de gauche (`Files`, rétractable) — Créer ou Ouvrir** :
   - **New** (par défaut à l'ouverture) : choisissez le dossier (`Folder` / `Subfolder`) et le nom du fichier (`Filename`), puis cliquez sur **Create** dans le panneau central pour créer le `.qmd` et installer automatiquement `_extensions/husson`.
   - **Open** : sélectionnez un document existant (`Recent`, `Path` ou `Import`) et cliquez sur **Convert** si vous souhaitez convertir un `.qmd` natif vers le template Husson (avec sauvegarde automatique dans `scratch/`).
3. **Panneau central — Configuration par onglets (`Formats`, `Typography`, `Cover`, `Tables`, `Assistant`)** :
   - Choisissez un préréglage rapide (*Master*, *Thesis*, *Report*, *Article*, *Presentation*) ou ajustez chaque option (polices, couleurs de titres, saut de page H1, page de garde, jury interactif, pages liminaires, tableaux). La navigation conserve l'onglet actif à chaque modification.
   - Dans **Formats**, cochez **PPTX** avec **RevealJS** pour exporter le même `.qmd` en diaporama web et en PowerPoint modifiable. **Render** produit les formats sélectionnés et propose l'ouverture du PPTX.
4. **Panneau de droite (`Preview`, rétractable) & Panneau inférieur (`Terminal`, rétractable)** :
   - Cliquez sur le bouton **`Preview`** (ou changez de préréglage) pour exécuter une véritable compilation `quarto render`, suivre le journal d'exécution en direct dans le panneau **`Terminal`** en bas d'écran, et visualiser le rendu natif dans le panneau de droite :
   - **`PDF`** : visualisation multi-pages haute définition (avec zoom `75%` / `100%` / `Fit`) du véritable fichier `.pdf` compilé par Quarto et XeLaTeX (`_extensions/husson/`).
   - **`HTML`** : affichage interactif du véritable document web `husson-html` compilé (avec bascule clair/sombre One Dark Pro, sommaire flottant et adaptation automatique des figures).
   - **`RevealJS`** : affichage interactif du véritable diaporama `husson-revealjs` compilé (navigation entre diapositives, barre de progression haute cliquable et thème clair/sombre).
   - **`YAML`** : inspection en direct de l'en-tête YAML exact généré.

---

### Méthode 2 : Convertir manuellement un fichier `.qmd` existant (en 2 étapes)

Si vous avez déjà un fichier `mon_document.qmd` dans un dossier :

**Étape 1 — Installer l'extension dans le dossier du document** (une seule fois par projet) :
```bash
cd /chemin/vers/mon-dossier
quarto add thomashusson29/quarto-template-husson
```

**Étape 2 — Remplacer `format: pdf` ou `format: html` dans l'en-tête YAML de votre `.qmd`** :
```yaml
---
title: "Titre de mon étude"
author: "Prénom Nom"
date: today
lang: fr
format:
  husson-pdf: default
  husson-html: default
---
```

Puis compilez normalement depuis RStudio, Positron, VS Code ou le terminal :
```bash
quarto render mon_document.qmd
```

---

### Méthode 3 : Créer un nouveau projet complet en ligne de commande

```bash
quarto use template thomashusson29/quarto-template-husson
cd <nom-du-projet>
quarto render
```

Pour compiler vers un format unique :
```bash
quarto render --to husson-pdf
quarto render --to husson-html
quarto render --to husson-docx
quarto render --to husson-revealjs
quarto render --to husson-pptx
```

---

## Modèles d'en-têtes YAML prêts à copier-coller

Voici les configurations types selon la nature de votre document.

### Cas 1 : Rapport ou Article standard (PDF + HTML)

Les chapitres `# H1` s'enchaînent sur la même page sans laisser de grands espaces blancs. Si vous souhaitez au contraire un saut de page avant chaque `# H1`, ajoutez `pagebreak-h1: true`.

```yaml
---
title: "Analyse des facteurs pronostiques"
subtitle: "Étude de cohorte rétrospective"
author: "Prénom Nom"
date: today
lang: fr
font: "Times New Roman"       # ou "Computer Modern", "Garamond", "Roboto", "Carlito"
pagebreak-h1: false           # mettre true pour forcer un saut de page à chaque # H1
bibliography: references.bib  # optionnel
format:
  husson-pdf:
    toc: true
    number-sections: true
  husson-html:
    toc: true
    number-sections: true
    embed-resources: true
---
```

### Cas 2 : Devoir ou Rapport de Master (avec page de garde universitaire, sans jury)

Génère une page de garde officielle avec logo universitaire, diplôme et unité d'enseignement, sans formule solennelle de soutenance ni tableau de jury.

```yaml
---
title: "Devoir d'Épidémiologie Clinique"
subtitle: "Analyse de survie sur les données SUPPORT"
author: "Prénom Nom"
lang: fr
font: "Computer Modern"       # ou "Times New Roman"
thesis:
  university: "Université Paris-Saclay"
  faculty: "Faculté de Médecine"
  degree: "Master 2 — Santé Publique et Méthodologie de la Recherche"
  specialty: "UE Épidémiologie"
  department: "Étude observationnelle"
  date: "Année universitaire 2025-2026"
  logo: "logo-universite-paris-saclay.png"
format:
  husson-pdf:
    toc: true
    number-sections: true
---
```

### Cas 3 : Thèse ou Mémoire officiel (page de garde, jury et pages liminaires)

En mode thèse (`thesis:`), chaque chapitre `# H1` commence automatiquement sur une nouvelle page, les pages liminaires (résumé, remerciements, table des matières, listes des figures et tableaux) sont numérotées en chiffres romains (`I`, `II`, `III`...), et l'introduction démarre en page `1` en chiffres arabes.

```yaml
---
title: "Titre complet de la thèse"
subtitle: "Sous-titre de l'étude"
author: "Prénom Nom"
lang: fr
font: "Times New Roman"
thesis:
  university: "Université Paris-Saclay"
  faculty: "Faculté de Médecine"
  degree: "Thèse pour le diplôme d'État de Docteur en Médecine"
  specialty: "DES d'Anesthésie-Réanimation"
  date: "15 octobre 2026"
  logo: "logo-universite-paris-saclay.png"
  directors:
    - name: "Pr Prénom Nom"
      title: "PU-PH"
      role: "Dirigé"
  jury:
    - name: "Pr Prénom Nom"
      title: "PU-PH, Université Paris-Saclay"
      role: "Président du jury"
    - name: "Dr Prénom Nom"
      title: "MCU-PH, Université Paris Cité"
      role: "Membre du jury"
frontmatter:
  table-of-contents: true
  list-of-figures: true
  list-of-tables: true
  keywords: ["Mot-clé 1", "Mot-clé 2", "Mot-clé 3"]
  keywords-en: ["Keyword 1", "Keyword 2", "Keyword 3"]
format:
  husson-pdf:
    number-sections: true
---
```

### Cas 4 : Présentation RevealJS (diaporama clair/sombre)

```yaml
---
title: "Titre de la soutenance"
subtitle: "Présentation des résultats"
author: "Prénom Nom"
date: today
lang: fr
heading-colors: true
format:
  husson-revealjs:
    slide-number: true
    transition: none
---
```

---

## Interface Graphique Interactive : Quarto Husson Studio

L'application [`gui/app.py`](gui/app.py) offre un espace de travail sobre et complet (inspiré des applications natives macOS) permettant de gérer tout le cycle de vie d'un document Quarto :

- **Lancement rapide** :
  - Double-clic sur [`gui/Quarto GUI.command`](gui/Quarto%20GUI.command) sous macOS.
  - Ou commande `streamlit run gui/app.py` (ou alias `quarto-gui`).
- **Fonctionnalités intégrées** :
  1. **Création directe de documents et de projets (`Nouveau document`)** : choix du dossier parent, création éventuelle d'un sous-dossier projet, choix du modèle initial (*Article*, *Master*, *Thèse*, *Rapport*, *RevealJS*), injection automatique de l'extension `_extensions/husson` et génération d'un squelette `.qmd` prêt à compiler.
  2. **Conversion automatique d'un `.qmd` natif existant (`Ouvrir / Convertir`)** : détection des formats standards (`pdf`, `html`, `docx`, `revealjs`) et des anciens appels manuels devenus inutiles (`source("gt-page-fit.R")`, `source("auto-dark-setup.R")`), conversion sans perte vers `husson-*` et sauvegarde préventive systématique dans `scratch/`.
  3. **Sélecteur de préréglages et éditeur complet** :
     - Application en un clic des 4 profils types (*Devoir / Rapport de Master*, *Thèse / Mémoire officiel*, *Rapport Scientifique Sobre*, *Article / Rapport Web*).
     - Onglets dédiés : **Formats & Rendu**, **Métadonnées & Typographie**, **Page de garde & Préambule** (avec éditeur de tableau interactif pour ajouter/modifier/supprimer les membres du **jury** et configurer toutes les options `frontmatter`), **Tableaux & Options Husson**.
  4. **Compilation et ouverture directe** : exécution de `quarto render` depuis l'en-tête principal, accès direct aux fichiers PDF, HTML, Word et au dossier Finder, journal technique repliable.
  5. **Assistant et diagnostic IA local (Ollama)** : analyse automatique des erreurs de compilation LaTeX/Pandoc/R et assistant conversationnel contextuel lorsque `ollama serve` est actif en local.

---

## Galerie et Démonstrations en Ligne (GitHub Pages)

Une galerie complète présentant chaque format en conditions réelles est intégrée dans le dossier `docs/` et déployée automatiquement sur GitHub Pages :

- **Rendu HTML statique (`exemple-article.html`)** : page web complète avec table des matières dynamique, bascule clair/sombre One Dark automatique (adaptée aux préférences système), équations LaTeX, encadrés Quarto (callouts), tableaux pleine page et graphiques R intégrés ;
- **Rendu RevealJS (`exemple-revealjs.html`)** : présentation interactive avec diaporama complet, fil d'Ariane hiérarchique en haut d'écran, titre sticky sur diapositive défilable, bascule One Dark Pro et graphiques R ggplot2 à fond transparent avec images compagnes automatiques ; le thème, les titres, le bandeau et les éléments hors des diapositives utilisent Carlito (repli Open Sans, puis Arial) en modes clair et sombre ;
- **Rendu PDF Thèse complet (`exemple-these.pdf`)** : document de 16 pages au format thèse universitaire (A4, XeLaTeX, Times New Roman 11pt, interligne 1.15) comprenant la page de garde officielle conforme, le jury complet, les pages liminaires (résumé, remerciements, valorisation scientifique, table des matières, liste des figures, liste des tableaux, abréviations), la reprise à la page 1 en chiffres arabes, les tableaux optimisés à 100 % de la largeur utile et l'insertion d'une planche en paysage ;
- **Rendu Word DOCX (`exemple-article.docx`)** : document Word appliquant directement le modèle éditorial embarqué (`template.docx`), avec styles typographiques calibrés, alignements de tableaux et légendes francisées ;
- **Rendu R vers Python (`exemple-r-python.html`)** : pipeline de modélisation bidirectionnel avec `reticulate` sur le jeu de données `mtcars` (transfert R → Python → R, régression OLS et analyse des résidus avec `ggplot2`).

L'index d'accueil (`docs/index.html`) est conçu de façon sobre et épurée (sans CSS lourd ni artifice externe, compatible avec les modes clair et sombre du système) pour explorer directement les démonstrations et télécharger leurs codes sources `.qmd`.

Pour prévisualiser la galerie localement, ouvrez simplement le fichier `docs/index.html` dans un navigateur.

### Configuration du Déploiement GitHub Pages

Dans les paramètres de votre dépôt GitHub (**Settings > Pages > Build and deployment**) :

- **Méthode 1 : Déploiement direct par branche (Simple et immédiat)** :
  Sélectionnez la source **Deploy from a branch**, choisissez la branche `main` et le dossier `/docs`.
  Le fichier `docs/.nojekyll` inclus à la racine de `docs/` désactive le traitement Jekyll par défaut, garantissant que les répertoires d'extensions (`_extensions/`) et de ressources ne soient pas ignorés ou rejetés lors de la mise en ligne.
- **Méthode 2 : Déploiement par GitHub Actions** :
  Sélectionnez la source **GitHub Actions**. Le fichier de workflow `.github/workflows/pages.yml` se charge alors de publier automatiquement le dossier `docs/` à chaque commit sur `main`.

```bash
# Commandes de régénération des démonstrations pour GitHub Pages
quarto render examples/exemple-article.qmd --to husson-html --output-dir docs --output exemple-article.html
quarto render examples/exemple-revealjs.qmd --to husson-revealjs --output-dir docs --output exemple-revealjs.html
quarto render examples/exemple-these.qmd --to husson-pdf --output-dir docs --output exemple-these.pdf
quarto render examples/exemple-article.qmd --to husson-docx --output-dir docs --output exemple-article.docx
quarto render examples/r-python-reticulate.qmd --output-dir docs --output exemple-r-python.html
```

---

## Ajouter les formats à un projet existant

Exécutez cette commande depuis le dossier qui contient le fichier `.qmd` à rendre :

```bash
quarto add thomashusson29/quarto-template-husson
```

### Utiliser le template sans le dupliquer (Lien Symbolique)

Par défaut, Quarto copie les fichiers de l'extension pour rendre le projet indépendant (reproductibilité). Si vous l'utilisez fréquemment sur votre propre machine et souhaitez éviter d'avoir le dossier copié des dizaines de fois, utilisez un **lien symbolique**.

Ajoutez cette fonction dans votre fichier `~/.zshrc` (ou `~/.bashrc`) :

```bash
use-quarto-husson() {
  mkdir -p _extensions
  ln -snf /chemin/vers/quarto-template-husson/_extensions/husson _extensions/husson
  echo "Thème Husson activé dans ce dossier (zéro copie !)"
}
```

Désormais, tapez simplement `use-quarto-husson` dans n'importe quel projet pour activer l'extension. Quarto pointera vers la source originale sans aucune copie physique.

Puis, dans le YAML du projet ou du document :

```yaml
format:
  husson-html: default
  husson-pdf: default
  husson-docx: default
  husson-revealjs: default
```

Après `quarto add` (ou le lien symbolique), l'extension doit se trouver dans le projet cible, par exemple :

```text
mon-projet/
├── _extensions/
│   └── husson/
└── mon-document.qmd
```

Dans un projet existant, ne déclarez ensemble que les formats qui doivent être produits par la même commande. Pour éviter une collision de noms (`.html` entre page web et diaporama), utilisez habituellement `husson-html` et `husson-pdf` par défaut, puis rendez les autres formats avec `--to`.

---

## Export PPTX modifiable depuis RevealJS

`husson-pptx` prend le `.qmd` comme source unique. Le projet Quarto rend d’abord `husson-revealjs`, puis l’adaptateur Husson prépare chaque vue dans Chromium (1600 × 900, thème clair, fragments visibles) et la convertit avec [dom-to-pptx 2.1.2](https://github.com/atharva9167j/dom-to-pptx). Le PPTX intermédiaire natif de Quarto est remplacé par cet export. [PptxGenJS](https://github.com/gitbrent/PptxGenJS) est utilisé par le moteur.

**Installation.** Quarto ≥ 1.8, Node.js, Chromium et les dépendances npm de l’adaptateur sont nécessaires. Les quatre variantes de [Carlito](https://github.com/googlefonts/carlito) se trouvent dans `_extensions/husson/fonts/` avec leur [licence](_extensions/husson/fonts/OFL.txt). `husson-revealjs` les charge depuis le clone, même hors ligne ; aucune installation de police ni connexion à Google Fonts n’est nécessaire. L’export PPTX intègre aussi les quatre variantes dans le fichier produit. Open Sans puis Arial restent des replis pour les caractères non couverts. Dans le dossier du projet contenant `_extensions/husson/` :

```bash
npm ci --prefix _extensions/husson/pptx
```

Par défaut, l’adaptateur lance `/Applications/Chromium.app/Contents/MacOS/Chromium` sur macOS. Sur un autre système, définir `CHROMIUM_PATH` vers le binaire Chromium.

Pour relier la commande Quarto à la conversion, ajouter à `_quarto.yml` du projet :

```yaml
project:
  type: default
  post-render: node _extensions/husson/pptx/post-render.mjs
```

Conserver `format: husson-revealjs` dans le `.qmd`, puis exécuter :

```bash
quarto render mon_diaporama.qmd --to husson-pptx
```

Le fichier `mon_diaporama.pptx` est créé à côté de la sortie Quarto. Le [diaporama de perfusion](https://github.com/Nurserie-Pitie/HOPE_COR_NMP/blob/main/diaporama_perfusion/README.md) utilise ce branchement. Pour un exemple autonome sans dépendance R, depuis la racine de ce template :

```bash
quarto render examples/exemple-pptx.qmd --to husson-pptx
# résultat : output/examples/exemple-pptx.pptx
```

Le [deck d’essai complexe](examples/test-pptx-complex.qmd), créé via **New → Presentation** dans l’interface, contient cinq diapositives sources : colonnes et images, tableau et SVG, boîtes et flèches CSS, diapositive défilante, puis trois onglets. Commande reproductible :

```bash
quarto render examples/test-pptx-complex.qmd --to husson-pptx
# résultat : output/examples/test-pptx-complex.pptx (8 diapositives)
```

Les titres, textes, cartes, encadrés, listes, tableaux et décorations CSS textuelles (`::before`, `::after`, `counter()`, `attr()`) restent modifiables. L’adaptateur mesure dans Chromium la géométrie du texte, puis tient compte de l’échelle RevealJS sans modifier la mise en page source. Chaque liste textuelle devient une seule zone de texte avec des paragraphes à puces ou une numérotation PowerPoint natives, y compris les niveaux imbriqués et les flèches de sous-listes Husson. Les lignes restent dans la même zone avec des retours natifs ; les paragraphes de texte consécutifs sont regroupés lorsque leur disposition le permet. Le gras, les liens, les capitales CSS et les espacements de caractères sont conservés. Les fragments de tailles différentes sur une même ligne conservent leurs espaces et leurs marges inline : un libellé en gras suivi d’un pourcentage ne doit pas être collé à celui-ci. Les espacements mesurés deviennent des espaces éditables dans la zone de texte. Chaque tableau textuel reste un véritable tableau PowerPoint (`a:tbl`) : cellules modifiables ensemble, fusions, couleurs et alignements conservés. Les largeurs de colonnes et hauteurs de lignes sont mesurées dans Chromium ; le cadre du tableau correspond à sa grille et ses identifiants sont uniques dans la diapositive. Il matérialise les décorations générées en éléments DOM avant conversion ; pour leurs chiffres et flèches, il vérifie la couverture réelle des caractères dans l’ordre **Carlito, Open Sans, Arial**. Lorsque le texte inline est plus grand que l’interligne du paragraphe, il impose dans PowerPoint un interligne minimal pour éviter un décalage vertical. Aucune règle ne cible une diapositive d’essai ou un numéro de diapositive. Quand `husson-revealjs` affiche sa barre de navigation, l’adaptateur copie son DOM et la convertit en fond, bordure et libellés PowerPoint modifiables. Le numéro de diapositive RevealJS est omis du PPTX : aucun numéro figé en image n’est ajouté. Une ligne de texte dans un conteneur flex peut utiliser l’espace restant pour éviter un retour ajouté par PowerPoint. La bascule clair/sombre et le menu interactif sont masqués dans le PPTX clair.

La langue effective du QMD (y compris celle héritée du projet Quarto) est reprise depuis le rendu HTML pour les textes, les styles et les métadonnées du PPTX. `lang: fr` donne la langue de correction `fr-FR`, tandis que les variantes explicites comme `fr-CA` ou `en-GB` sont conservées.

Le test `node tests/test_pptx_native_text.mjs` vérifie ces propriétés dans le XML d’exports Quarto français et anglais, sans contrôle par images.

Les fragments apparaissent dans leur état final. Pour une diapositive [`.scrollable`](https://quarto.org/docs/presentations/revealjs/#content-overflow), l’adaptateur mesure les blocs dans Chromium et crée autant de diapositives de suite que nécessaire, sans couper un bloc entre deux pages. Pour un [`.panel-tabset`](https://quarto.org/docs/presentations/revealjs/#tabsets), il crée une diapositive par onglet, dans l’ordre, et mesure le texte de chaque panneau activé avant conversion ; plusieurs ensembles d’onglets produisent toutes leurs combinaisons, avec une limite explicite de 100. Les photos, QR codes, SVG complexes et iframes de démonstration restent des images ; les iframes sont figées à l’export. Les animations et interactions RevealJS ne sont pas transférées. Carlito est intégré au PPTX produit ; si un autre diaporama utilise une police personnalisée, sa présence dans le PPTX dépend d’une déclaration `@font-face` accessible au navigateur. Une équivalence parfaite pour tout HTML/CSS futur ne peut pas être garantie, donc vérifier les nouveaux types de composants avant diffusion.

L’adaptateur retire aussi la capture pleine page parasite ajoutée par le moteur derrière les objets modifiables. Il arrête l’export si une image est introuvable ou si un contenu CSS généré ne peut pas être converti ; aucun élément de ce type n’est omis silencieusement. Les variantes claires des images `-auto-dark` facultatives sont utilisées pour cet export fixe. L’export applique en mémoire un correctif à [dom-to-pptx 2.1.2](https://github.com/atharva9167j/dom-to-pptx) pour les conteneurs `inline-block` et utilise [JSZip](https://github.com/Stuk/jszip) pour ajuster les tailles de police au facteur RevealJS. Les [notices de provenance et licences](_extensions/husson/THIRD_PARTY_NOTICES.md) détaillent ces adaptations, [PptxGenJS](https://github.com/gitbrent/PptxGenJS), et distinguent les dépendances utilisées des projets consultés comme [HTMLtoPPTX](https://github.com/mmoollee101-lab/HTMLtoPPTX) et [revealjs-to-pptx](https://github.com/ddzeeuw1-ai/revealjs-to-pptx).

---

## Typographie, sauts de page et choix de police

Le template `husson-pdf` intègre un moteur typographique universel (`typography.lua`) et charge directement ses polices, logos et bibliographies depuis `_extensions/husson/` sans jamais copier de fichiers parasites dans le dossier de travail :

- **Polices disponibles out-of-the-box** :
  - **Times New Roman** (appliquée **par défaut** sur tous les documents `husson-pdf`, ou via `font: "Times New Roman"`) : standard académique et médical, avec petites capitales véritables via TeX Gyre Termes.
  - **Computer Modern / Latin Modern** (`font: "Computer Modern"` ou `font: "default"`) : police mathématique classique de LaTeX.
  - **Garamond** (`font: "Garamond"` ou `"EB Garamond"`) : typographie littéraire et soignée via le package OpenType EB Garamond embarqué dans TeX Live.
  - **Roboto** (`font: "Roboto"`) : sans-serif moderne, sobre et hautement lisible.
  - **Carlito** (`font: "Carlito"` ou `"Calibri"`) : sans-serif métriquement compatible avec Microsoft Calibri, chargé directement depuis `_extensions/husson/fonts/`.
  - **Police personnalisée** (`font: "NomDePolice"` ou `mainfont: "NomDePolice"`).

- **Sauts de page des chapitres de niveau 1 (`# H1`)** :
  - **En mode Thèse (`thesis:`)** : chaque titre de niveau 1 (`# H1`) commence **systématiquement sur une nouvelle page** (`\clearpage`).
  - **En mode Rapport / Article / Devoir standard** : les sections `# H1` s'enchaînent de manière fluide avec une réserve d'espace anti-veuve (`\Needspace{8\baselineskip}`), évitant de laisser la première page quasi vide sous le titre.
  - **Option globale (`pagebreak-h1`)** : ajoutez `pagebreak-h1: true` dans le YAML d'un rapport standard pour forcer un saut de page avant chaque `# H1` (ou `pagebreak-h1: false` en mode thèse pour le désactiver).
  - **Contrôle titre par titre** : ajoutez la classe `{.pagebreak}` ou `{.no-pagebreak}` sur un titre `# H1` spécifique.

- **Couleurs des titres (`heading-colors`)** :
  - **En PDF (`husson-pdf`)** : par défaut (`heading-colors: true`), les titres utilisent la palette hiérarchique du template (bleu marine `#17365D` pour `# H1`, bordeaux `#7A1F2B` pour `## H2`, vert forêt `#1F5A3A` pour `### H3`, anthracite `#34383D` pour `H4`–`H5`). Ajoutez `heading-colors: false` dans le YAML (ou décochez `Colors` dans l'onglet `Typography`) pour composer tous les titres en noir (`#000000`).
  - **En HTML et RevealJS (`husson-html`, `husson-revealjs`)** : ajoutez `heading-colors: true` pour appliquer les couleurs d'accentuation aux titres `H1`–`H3` avec adaptation automatique au mode clair/sombre, ou `heading-colors: false` pour conserver la couleur du texte courant.

### Mode Thèse / Mémoire universitaire

L'activation du mode thèse (en définissant le bloc `thesis:` ou `thesis: true` dans le YAML) configure automatiquement :
- La police **Times New Roman** (ou la police choisie via `font:`).
- Le **saut de page systématique** avant chaque chapitre `# H1`.
- Une taille de corps de **11pt** (`fontsize: 11pt`).
- Un **interligne de 1,15** (`linestretch: 1.15`).
- Une **géométrie de page calibrée** (`top=3cm, bottom=2.5cm, left=3cm, right=2.5cm`).
- La génération automatique de la page de garde conforme au modèle de thèse universitaire :
  - Marges de couverture calibrées (2,2 cm).
  - Centrage sobre du nom du candidat (sans préfixe « par »).
  - Tableau du jury pleine largeur avec alignement dynamique (`\extracolsep{\fill}`) empêchant tout retour à la ligne disgracieux dans les titres, affiliations ou rôles.

Exemple :
```yaml
format:
  husson-pdf:
    font: "Times New Roman" # ou "Garamond", "Roboto", "Carlito"
thesis:
  university: "Université 1"
  faculty: "Faculté 1"
  degree: "Thèse de doctorat"
  date: "3 octobre 2026"
  directors:
    - name: "Membre 1"
      role: "Directeur de thèse"
  jury:
    - name: "Membre 1"
      title: "Hôpital 1, Université 1"
      role: "Directeur de thèse"
    - name: "Membre 2"
      title: "Hôpital 2, Université 2"
      role: "Rapporteur"
    - name: "Membre 3"
      title: "Hôpital 1, Université 1"
      role: "Président du jury"
```

- **Adaptation intelligente aux informations renseignées** :
  - **Sans jury ni date** (ex. mémoire d'étape, document de travail ou rapport préliminaire) : la mention « Présentée et soutenue publiquement le » est automatiquement supprimée. La page de garde s'arrête sobrement après la mention des directeurs.
  - **Avec date seule (sans jury)** : la date apparaît sobrement et directement, sans formule de soutenance solennelle.
  - **Avec jury** : la formule rituelle (« Présentée et soutenue publiquement le [date] devant un jury composé de : ») s'affiche au millimètre au-dessus du tableau du jury.
  - **Accroche personnalisée (`date_prefix`)** : pour modifier ou adapter la formule, précisez `date_prefix: "Soutenue le "` ou `date_prefix: "Date : "` dans le bloc `thesis:`.

### Pages liminaires facultatives (`frontmatter`)

Les pages liminaires peuvent être activées individuellement avec le bloc `frontmatter:` (en mode thèse comme dans un rapport standard) :

```yaml
frontmatter:
  blank-page: true
  abstract: |
    Résumé en français.
  abstract-en: |
    Abstract in English.
  keywords: ["Mot-clé 1", "Mot-clé 2"]
  keywords-en: ["Keyword 1", "Keyword 2"]
  acknowledgements: |
    Les remerciements (Membre 1, Membre 2, Hôpital 1, Hôpital 2).
  scientific-valorization: |
    Publications, communications et autres éléments de valorisation.
  table-of-contents: true
  list-of-figures: true
  list-of-tables: true
  abbreviations:
    - term: "MPG"
      definition: "Miles per gallon"
    - term: "WT"
      definition: "Weight (1000 lbs)"
```

L'ordre PDF est alors : page de titre, page blanche facultative, remerciements, résumé français, abstract anglais, valorisation scientifique, table des matières, liste des figures, liste des tableaux, liste des abréviations (numérotés en chiffres romains `I`, `II`...), puis le corps du document qui démarre automatiquement à la page `1` en chiffres arabes. Lorsque `frontmatter.table-of-contents: true` est activé, le sommaire natif Quarto est automatiquement désactivé afin d'éviter tout doublon.

#### Rédiger les pages liminaires directement en Markdown dans le corps du `.qmd`

Pour rédiger vos textes liminaires avec toute la richesse de Markdown (gras, listes, tableaux) sans alourdir l'en-tête YAML, placez simplement des blocs `::: {.frontmatter-*}` au début de votre document `.qmd` (ils sont détectés automatiquement sur tous les formats) :

```markdown
::: {.frontmatter-acknowledgements}
Les remerciements peuvent être rédigés normalement en Markdown.
:::

::: {.frontmatter-abstract}
**Introduction :** Contexte de l'étude.

**Méthodes :** Schéma d'étude et analyse statistique.
:::

::: {.frontmatter-abstract-en}
**Background:** Study background.

**Methods:** Study design and statistical analysis.
:::

::: {.frontmatter-scientific-valorization}
- Article publié : ...
- Communication : ...
:::

::: {.frontmatter-abbreviations}
| Abréviation | Définition |
| :--- | :--- |
| **MPG** | Miles per gallon |
:::
```

---

## Ajustement universel des tableaux (pleine largeur et hauteur minimale)

Le template garantit de façon **systématique, native et transparente** que tous les tableaux (`gt`, `gtsummary`, `knitr::kable`, `data.frame` / `tibble` via `df-print: kable`, tableaux Markdown) respectent les contraintes suivantes **sans aucun chunk de configuration requis** :
1. **100 % de la largeur utile (`\linewidth`)** : aucun tableau ne déborde dans les marges. Les spécifications brutes (`{lccc}`) ou en pixels/points (`px()`, `pt`) générées par `gt` ou `kable` sont automatiquement converties en colonnes `p{...}` proportionnelles de `\linewidth` (méthode Hamilton-Hare totalisant exactement 100 %).
2. **Hauteur minimale et en-têtes équilibrés sur 2 lignes** : espacement vertical compact (`+2.5pt` de padding de ligne) et répartition optimale des largeurs par le filtre Lua (`table-column-widths.lua`) calculant le point de coupe optimal en 2 lignes (`best_2line_len`), protégeant les identifiants courts et insérant automatiquement un espace avant les parenthèses d'unités (`CellSaver(mL)` $\rightarrow$ `CellSaver (mL)`).
3. **Inférence automatique des alignements** : valeurs numériques, estimations et $p$-values alignées à droite (`\raggedleft`), codes courts et stades (`F0`–`F4`, `Oui`/`Non`, plages) centrés (`\centering`), libellés descriptifs alignés à gauche (`\raggedright`).
4. **Césure automatique universelle en français** : par défaut, LaTeX désactive la césure dans les cellules de tableau (`p{...}`). Le template charge `ragged2e` et redéfinit universellement `\raggedright` en `\RaggedRight\hspace{0pt}`, ce qui restaure les motifs de césure natifs TeX/Babel en français sans nécessiter de liste manuelle de mots.
5. **Sauts de ligne `<br>` préservés** : les balises HTML `<br>` ou `<br/>` présentes dans les cellules de tableaux Markdown sont automatiquement converties en `\newline` LaTeX par le filtre Lua, évitant que les lignes ne soient collées sans espace.
6. **Appellation « Tableau » automatique (`lang: fr`)** : si le document est configuré avec `lang: fr`, les tables sont automatiquement étiquetées « Tableau » (références croisées `@tbl-...`, titres de tableaux, macro `\tablename` et `Liste des tableaux`), au lieu du terme anglais « Table » imposé par défaut par Quarto et Pandoc. En anglais (`lang: en`), l'intitulé « Table » reste préservé.
7. **Indices, exposants et symboles scientifiques directs** : prise en charge native sans formule mathématique lourde des indices et exposants unicode (`₀`–`₉`, `⁰`–`⁹`, `⁺`, `⁻`), des lettres grecques (`α`–`ω`, `Δ`, `Σ`, `Ω`) et des opérateurs cliniques/statistiques (`≥`, `≤`, `≈`, `≠`, `±`, `×`, `÷`, `−`, `→`, `∞`).
8. **Respect de la typographie du document** : réduction de police adaptative selon la densité (`10pt` pour $< 6$ colonnes, `9pt` pour $6$ à $9$ colonnes, `8pt` pour $\ge 10$ colonnes).
9. **Zéro configuration requise** : fonctionne nativement au niveau du filtre Pandoc Lua (`table-column-widths.lua`) et du préambule LaTeX (`pdf-header.tex`), même sur un fichier `.qmd` natif ne contenant aucun appel à `gt-page-fit.R`.

### Module R optionnel : `gt-page-fit.R`

Le filtre Lua `table-column-widths.lua` applique déjà l'intégralité de l'algorithme de calibrage à tous les tableaux lors du rendu Pandoc. Pour les utilisateurs souhaitant que l'objet R `gt_tbl` lui-même porte ces options dès l'évaluation `knitr` (ou que les `data.frame` soient convertis en `gt` plutôt qu'en `kable`), le module `gt-page-fit.R` reste disponible en option :

```r
source("_extensions/husson/gt-page-fit.R")
husson_tables_on()
```

---

## Navigation d'en-tête et pied de page (PDF & RevealJS)

Le template intègre un système d'orientation discret, particulièrement adapté aux mémoires universitaires, thèses et rapports volumineux.

### 1. Barre de navigation hiérarchique d'en-tête (PDF et RevealJS)

Une ligne fine placée en haut de chaque page ou diapositive affiche en temps réel le contexte hiérarchique actif sous forme d'un fil d'Ariane sobre (`H1 | H2 › H3`).

- **Titre court pour l'en-tête (`nav-title`)** :
  Pour éviter qu'un intitulé trop long ne déborde dans la barre d'en-tête, spécifiez un libellé court avec l'attribut `nav-title` :
  ```markdown
  # Matériels et méthodes expérimentales {nav-title="MÉTHODES"}

  ## Conservation dynamique hypothermique oxygénée {nav-title="HOPE"}

  ### Cinétiques de relargage de la FMN {nav-title="FMN"}
  ```
- **Masquer la barre sur une section ou diapositive spécifique** :
  Ajoutez l'attribut `{nav="false"}` ou la classe `{.unlisted}` (ou `{.nobar}` pour RevealJS) sur le titre.
- **Désactiver globalement la barre d'en-tête** :
  ```yaml
  ---
  navigation-bar: false # ou navbar: false
  ---
  ```

### 2. Pied de page structuré (husson-pdf)

Le pied de page affiche à gauche le nom de l'auteur suivi du titre en italique (`Auteur – *Titre*`), et à droite le numéro de page.

- **Définir un titre court dans le pied de page (`short-title` ou `footer-title`)** :
  ```yaml
  title: "Modélisation statistique et analyse multivariée du jeu de données mtcars"
  short-title: "Analyse mtcars"
  ```
- **Personnaliser l'auteur dans le pied de page (`footer-author`)** ou remplacer toute la mention gauche (`footer-left`).

### 3. Diapositives RevealJS : Navigation, titre fixe et protection du bas de diapositive

- **Titre fixe (`sticky`) sur contenu défilant** : ajoutez `{.scrollable}` sur un titre `##` pour que l'intitulé reste épinglé en haut pendant le défilement vertical d'un grand tableau.
- **Hauteur de barre réservée** : tant que la barre de navigation est affichée, `navigation-reveal.js` pose `husson-nav-visible` sur `<body>` et la zone des diapositives commence sous la barre (`--husson-nav-h`, 42 px). La barre ne peut donc pas recouvrir un titre, quelle que soit la taille de la fenêtre.
- **Plafonnement dynamique des figures (`max-height`)** : les figures se redimensionnent proportionnellement pour ne jamais chevaucher le pied de page ni les numéros de diapositives.

---

## Insertion d'une page en paysage au milieu du document

Pour intégrer une ou plusieurs pages en orientation paysage (idéal pour les grands tableaux ou les figures larges) au sein d'un document PDF par ailleurs composé en portrait, enveloppez simplement votre contenu dans un bloc `::: {.landscape}` :

````markdown
# Page précédente en portrait normal

::: {.landscape}
# Section en paysage

```{r}
# Un grand tableau gt ou une figure large ggplot2
```
:::

# Reprise immédiate en portrait normal
````

Grâce au package `pdflscape`, le lecteur PDF applique automatiquement une rotation de 90° à la visualisation de la page concernée.

---

## Graphiques R, Python et compatibilité One Dark Pro (HTML & RevealJS)

En HTML et RevealJS, toutes les figures s'adaptent automatiquement lors du passage entre le mode clair et le mode sombre One Dark Pro :

1. **Fonctionnement natif sans configuration (`auto-dark.lua` + `_extension.yml`)** :
   - Les formats `husson-html` et `husson-revealjs` configurent automatiquement `knitr` (`fig.bg = "transparent"`) et la palette discrète `ggplot2` One Dark Pro.
   - Même sur un fichier `.qmd` natif n'appelant pas `auto_dark_on()` (et même avec `+ theme_minimal()` ou `+ theme_bw()`), le filtre Lua `auto-dark.lua` rend le fond blanc `#FFFFFF` transparent, génère la variante sombre `*-auto-dark.*` et l'embarque en `data-URI` base64 (100 % compatible avec `embed-resources: true`).
2. **Graphiques 2D et 3D interactifs (`plotly` en R et Python)** :
   - `auto-dark-renderings.js` intercepte les graphiques `Plotly` côté navigateur pour adapter dynamiquement les couleurs des séries, des axes et des grilles WebGL 3D au thème clair ou sombre actif.
3. **Hook R optionnel (`auto-dark-setup.R`)** :
   ```r
   source("_extensions/husson/auto-dark-setup.R")
   auto_dark_on(transparent_figures = TRUE)
   ```

---

## Exemples et démonstrations inclus dans le dépôt

Le dossier `examples/` contient des cas d'usage génériques. Les documents personnels, les brouillons et les sorties de compilation sont exclus du dépôt public par `.gitignore` :

1. **[`examples/exemple-article.qmd`](examples/exemple-article.qmd)** : rendu HTML (`husson-html`) et Word (`husson-docx`).
2. **[`examples/exemple-revealjs.qmd`](examples/exemple-revealjs.qmd)** : présentation RevealJS (`husson-revealjs`).
3. **[`examples/exemple-these.qmd`](examples/exemple-these.qmd)** : thèse PDF complète (`husson-pdf`) avec page de garde, jury, pages liminaires et page paysage.
4. **[`examples/r-python-reticulate.qmd`](examples/r-python-reticulate.qmd)** : transfert bidirectionnel R $\leftrightarrow$ Python avec `reticulate`.

---

## Bibliographie

Le template prend en charge les deux modes de citation de Quarto. Ajoutez votre propre fichier `.bib` au projet. Une bibliographie locale facultative `_extensions/husson/biblio_shared.bib` est également reconnue si vous en utilisez une ; elle n'est pas distribuée avec le dépôt public.

1. **Mode Citeproc (par défaut sur tous les formats)** :
   ```yaml
   bibliography: references.bib
   csl: american-medical-association.csl # optionnel
   ```
   En PDF, l'environnement `CSLReferences` est automatiquement composé en taille compacte (`\footnotesize`, interligne simple, espacement `1.5pt`).
2. **Mode Natbib (sur option en PDF)** :
   ```yaml
   bibliography: references.bib
   cite-method: natbib
   ```

---

## Origine du thème HTML

Le thème HTML reprend les ressources du projet [`quarto_auto_dark_theme`](https://github.com/thomashusson29/quarto_auto_dark_theme). Le mécanisme de détection du mode sombre reprend une idée du projet [`gadenbuie/quarto-auto-dark`](https://github.com/gadenbuie/quarto-auto-dark) de Garrick Aden-Buie. Les attributions détaillées sont conservées dans [`THIRD_PARTY_NOTICES.md`](_extensions/husson/THIRD_PARTY_NOTICES.md).
