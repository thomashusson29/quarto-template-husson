# Quarto Template Husson

Extension Quarto personnelle fournissant quatre formats cohérents :

- `husson-pdf` : PDF XeLaTeX A4, typographie soignée, tableaux ajustés
  automatiquement, barre de navigation hiérarchique en en-tête et pied de page
  structuré avec auteur, titre et pagination ;
- `husson-html` : HTML clair/sombre fondé sur la palette One Dark et suivant
  automatiquement les préférences du système ;
- `husson-docx` : document Word utilisant automatiquement le modèle éditorial
  embarqué dans l'extension ;
- `husson-revealjs` : présentation RevealJS avec le thème clair
  Auto Dark Clean, fil d'Ariane interactif en haut de diapositive, titre sticky
  pour les diapositives défilables et bascule automatique ou manuelle vers One Dark.

## Créer un nouveau projet

```bash
quarto use template thomashusson29/quarto-template-husson
cd <nom-du-projet>
quarto render
```

Le rendu par défaut est écrit dans `output/` et contient un fichier HTML et un
PDF. Word et RevealJS restent explicites, car HTML et RevealJS produiraient
tous deux un fichier `.html` de même nom.

Pour une seule sortie :

```bash
quarto render --to husson-pdf
quarto render --to husson-html
quarto render --to husson-docx
quarto render --to husson-revealjs
```

## Interface Graphique Interactive : Quarto Husson Studio

Pour configurer visuellement vos options, pré-remplir le YAML, activer les modes Thèse ou Tableaux et visualiser la compilation en streaming temps réel, lancez l'application graphique :

- **Depuis le terminal** : tapez simplement `quarto-gui` (ou `husson-gui`) depuis n'importe quel dossier.
- **Depuis macOS** : double-cliquez sur le fichier lanceur `Quarto GUI.command` situé dans le dossier `gui/`.

L'application Web locale permet de :
1. **Sélectionner ou déposer un `.qmd`** (avec recherche automatique des documents récents).
2. **Choisir un profil prêt à l'emploi** (Thèse universitaire, Rapport académique Computer Modern / LaTeX Default, Article, Présentation RevealJS) ou affiner chaque paramètre en mode avancé.
3. **Sécurité totale** : sauvegarde préventive automatique horodatée avant toute modification du fichier `.qmd`.
4. **Liaison automatique du template** : vérifie et lie `_extensions/husson` dans le projet cible si manquant.
5. **Console en streaming temps réel** : visualisation du terminal au cours de `quarto render`, avec chronomètre et boutons d'ouverture directe du PDF ou HTML produit.

## Ajouter les formats à un projet existant

Exécutez cette commande depuis le dossier qui contient le fichier `.qmd` à
rendre :

```bash
quarto add thomashusson29/quarto-template-husson
```

### Utiliser le template sans le dupliquer (Lien Symbolique)

Par défaut, Quarto copie les fichiers de l'extension pour rendre le projet indépendant (reproductibilité). Si vous l'utilisez fréquemment sur votre propre machine et souhaitez éviter d'avoir le dossier copié des dizaines de fois, utilisez un **lien symbolique**.

Ajoutez cette fonction dans votre fichier `~/.zshrc` (ou `~/.bashrc`) :

```bash
use-quarto-husson() {
  mkdir -p _extensions
  ln -snf /Users/thomashusson/Documents/Projets/quarto-template-husson/_extensions/husson _extensions/husson
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

Après `quarto add` (ou le lien symbolique), l'extension doit se trouver dans le projet cible, par
exemple :

```text
mon-projet/
├── _extensions/
│   └── husson/
└── mon-document.qmd
```

Un dossier contenant une copie (ou un lien) du template placé à côté du projet n'est pas
recherché automatiquement par Quarto. Ainsi, si l'extension est conservée
dans un autre dossier, utilisez le modèle Word directement :

```bash
cd /chemin/vers/mon-projet
quarto render mon-document.qmd \
  --to docx \
  --reference-doc chemin/vers/quarto-template-husson/_extensions/husson/template.docx \
  --output mon-document.docx
```

Le rendu doit être lancé depuis le projet qui contient `mon-document.qmd`, et
non depuis le dépôt `quarto-template-husson`. Le chemin passé à `--output` est
interprété depuis le dossier courant ; avec la commande ci-dessus, le fichier
est donc créé dans `mon-projet/`. Évitez les chemins de sortie pointant vers le
dépôt du template, afin de ne pas y générer accidentellement des documents.

Dans un projet existant, ne déclarez ensemble que les formats qui doivent être
produits par la même commande. Pour éviter une collision de noms, utilisez
habituellement `husson-html` et `husson-pdf` par défaut, puis rendez les deux
autres formats avec `--to`.

## Typographie et choix de police

Le template `husson-pdf` intègre un moteur typographique universel (`typography.lua`) éliminant tout repli vers Computer Modern :

- **Polices disponibles out-of-the-box** :
  - **Times New Roman** (`font: "Times New Roman"` ou par défaut) : standard académique et médical, avec petites capitales véritables via TeX Gyre Termes.
  - **Garamond** (`font: "Garamond"` ou `"EB Garamond"`) : typographie littéraire et soignée via le package OpenType EB Garamond embarqué dans TeX Live.
  - **Roboto** (`font: "Roboto"`) : sans-serif moderne, sobre et hautement lisible.
  - **Carlito** (`font: "Carlito"` ou `"Calibri"`) : sans-serif métriquement compatible avec Microsoft Calibri, embarqué directement dans les ressources du template.
  - **Police personnalisée** (`font: "NomDePolice"` ou `mainfont: "NomDePolice"`).

### Mode Thèse / Mémoire universitaire

L'activation du mode thèse (en définissant le bloc `thesis:` ou `thesis: true` dans le YAML) configure automatiquement :
- La police **Times New Roman** (ou la police choisie via `font:`).
- Une taille de corps de **11pt** (`fontsize: 11pt`).
- Un **interligne de 1,15** (`linestretch: 1.15`).
- Une **géométrie de page calibrée** (`top=3cm, bottom=2.5cm, left=3cm, right=2.5cm`).
- La génération automatique de la page de garde conforme au millimètre au modèle de thèse Sorbonne / Université Paris Cité / Paris-Saclay (ref: thèse S. Tzedakis) :
  - Marges de couverture calibrées (2,2 cm).
  - Centrage sobre du nom du candidat (sans préfixe « par »).
  - Tableau du jury pleine largeur avec alignement dynamique (`\extracolsep{\fill}`) empêchant tout retour à la ligne disgracieux dans les titres, affiliations ou rôles.

Exemple :
```yaml
format:
  husson-pdf:
    font: "Times New Roman" # ou "Garamond", "Roboto", "Carlito"
thesis:
  university: "Université Paris Cité"
  faculty: "Faculté de Médecine"
  degree: "Thèse de doctorat en Médecine"
  date: "7 octobre 2026"
  directors:
    - name: "Pr Claire GOUMARD"
      role: "Directrice de thèse"
  jury:
    - name: "Pr Claire GOUMARD"
      title: "PU-PH"
      role: "Directrice de thèse"
    - name: "Dr Jérémie GAUTHERON"
      title: "CR, Inserm UMR-S 938"
      role: "Co-directeur de recherche"
    - name: "Pr Jean DUPONT"
      title: "PU-PH, Université Paris-Saclay"
      role: "Président du jury"
```

- **Adaptation intelligente aux informations renseignées** :
  - **Sans jury ni date** (ex. mémoire d'étape, document de travail ou rapport préliminaire) : la mention « Présentée et soutenue publiquement le » est automatiquement supprimée. La page de garde s'arrête sobrement après la mention des directeurs.
  - **Avec date seule (sans jury)** : la date apparaît sobrement et directement, sans formule de soutenance solennelle.
  - **Avec jury** : la formule rituelle (« Présentée et soutenue publiquement le [date] devant un jury composé de : ») s'affiche au millimètre au-dessus du tableau du jury.
  - **Accroche personnalisée (`date_prefix`)** : pour modifier ou adapter la formule, précisez `date_prefix: "Soutenue le "` ou `date_prefix: "Date : "` dans le bloc `thesis:`.

### Pages liminaires facultatives

Le mode `thesis` fournit la page de titre. Les autres pages liminaires peuvent
être activées individuellement avec le bloc `frontmatter:` :

```yaml
format:
  husson-pdf:
    toc: false # la table sera placée avec les autres pages liminaires

frontmatter:
  blank-page: true
  summary: |
    Le résumé de la thèse.
  acknowledgements: |
    Les remerciements.
  scientific-valorization: |
    Publications, communications et autres éléments de valorisation.
  table-of-contents: true
  list-of-figures: true
  list-of-tables: true
  abbreviations:
    - term: "NMP"
      definition: "Normothermic machine perfusion"
    - term: "CGR"
      definition: "Concentré de globules rouges"
```

L’ordre PDF est alors : page de titre, page blanche facultative, résumé,
remerciements, valorisation scientifique, table des matières, liste des
figures, liste des tableaux, liste des abréviations, puis le corps du document
à la page 1 en chiffres arabes. Les listes de figures et de tableaux sont
générées par LaTeX et récupèrent automatiquement les légendes et les numéros
de page après compilation.

Les champs `summary`, `acknowledgements`, `scientific-valorization` et
`abbreviations` sont facultatifs. Pour utiliser la table des matières native
de Quarto à son emplacement habituel, conserver `toc: true` et ne pas activer
`frontmatter.table-of-contents`.

#### Rédiger les pages en Markdown

Pour éviter de mettre le contenu dans le YAML, activer
`frontmatter.markdown: true` puis placer les pages sous forme de blocs Markdown
dans le document :

```markdown
::: {.frontmatter-summary}
## Contexte

Le résumé peut contenir plusieurs paragraphes, listes, emphases et références.
:::

::: {.frontmatter-acknowledgements}
Les remerciements peuvent être rédigés normalement en Markdown.
:::

::: {.frontmatter-scientific-valorization}
### Publications

- Article publié : ...
- Communication : ...
:::

::: {.frontmatter-abbreviations}
NMP
: Perfusion normothermique
:::
```

Les classes disponibles sont `frontmatter-summary`,
`frontmatter-acknowledgements`, `frontmatter-scientific-valorization` et
`frontmatter-abbreviations`. Le filtre les déplace automatiquement avant la
table des matières, conserve leur contenu Markdown, puis redémarre le corps du
document à la page 1. Les abréviations utilisent une liste de définitions
Markdown et sont composées en deux colonnes à largeur fixe (libellé et
définition), sans tableau LaTeX.

## Ajustement universel des tableaux (pleine largeur et hauteur minimale)

Le template garantit de façon **systématique et transparente** que tous les tableaux (`gt`, `gtsummary`, `knitr::kable`, tibbles, tableaux Markdown) respectent les contraintes suivantes :
1. **100 % de la largeur utile (`\linewidth`)** : aucun tableau ne déborde dans les marges. Les largeurs fixes (en `px` ou `pt`) sont automatiquement renormalisées en proportions relatives de `\linewidth`.
2. **Hauteur minimale et colonnes équilibrées** : espacement vertical compact (`+2.5pt` de padding de ligne) et répartition automatique des largeurs par le filtre Lua (`table-column-widths.lua`) guidée par la demande réelle en texte afin de minimiser les retours à la ligne inutiles.
3. **Césure automatique universelle en français** : par défaut, LaTeX désactive la césure dans les cellules de tableau (`p{...}`). Le template charge `ragged2e` et redéfinit universellement `\raggedright` en `\RaggedRight\hspace{0pt}`, ce qui restaure les motifs de césure natifs TeX/Babel en français sans nécessiter de liste manuelle de mots.
4. **Sauts de ligne `<br>` préservés** : les balises HTML `<br>` ou `<br/>` présentes dans les cellules de tableaux Markdown sont automatiquement converties en `\newline` LaTeX par le filtre Lua, évitant que les lignes ne soient collées sans espace.
5. **Appellation « Tableau » automatique (`lang: fr`)** : si le document est configuré avec `lang: fr`, les tables sont automatiquement étiquetées « Tableau » (références croisées `@tbl-...`, titres de tableaux, macro `\tablename` et `Liste des tableaux`), au lieu du terme anglais « Table » imposé par défaut par Quarto et Pandoc. En anglais (`lang: en`), l'intitulé « Table » reste préservé.
6. **Indices et symboles scientifiques directs** : prise en charge native sans formule mathématique lourde des indices unicode courants (`₂`, `₁`, `₀`, etc.) et des symboles (`≥`, `≤`, `≈`, `ρ`).
7. **Respect de la typographie du document** : réduction de police plafonnée à 25 % maximum (`\small` ~10pt par défaut, `\footnotesize` ~9pt pour les tableaux $\ge 6$ colonnes).
8. **Zéro configuration requise** : fonctionne nativement au niveau du filtre Pandoc Lua (`table-column-widths.lua`) et du préambule LaTeX (`pdf-header.tex`), sans code R dédié obligatoire.

### Module R avancé : `gt-page-fit.R`

Pour les documents contenant des tableaux R générés par `gt`, `gtsummary`, ou des `data.frame` / `tibble`, le module `gt-page-fit.R` fournit une optimisation typographique poussée dès l'étape d'évaluation knitr.

#### Activation dans le document Quarto

Dans le chunk d'initialisation (`setup`) de votre document :

```r
source("_extensions/husson/gt-page-fit.R")
husson_tables_on()
```

Une fois activé, le module intercepte automatiquement l'impression des tableaux dans les sorties LaTeX/PDF sans nécessiter de retoucher vos chunks existants.

#### Fonctionnalités assurées automatiquement

1. **Interception universelle des tableaux R** :
   - Tableaux `gt` natifs et objets `gtsummary` convertis (`as_gt()`).
   - Objets `data.frame` et `tibble` affichés dans un chunk : automatiquement transformés en tableaux `gt` optimisés pleine page.

2. **Minimisation de la hauteur et équilibrage des en-têtes (2 lignes maximum)** :
   - Analyse combinatoire du texte des en-têtes pour calculer le point de césure optimal en 2 lignes (`best_2line_len`).
   - Détection des sous-lignes multi-mots (`has_multiword_line`) : garantit une largeur suffisante pour que les en-têtes composés (ex. *« Nombre de décharges »*) tiennent sur 2 lignes sans isoler un mot sur une 3e ligne (*Nombre* / *de* / *décharges*).
   - Insertion automatique d'un espace avant les parenthèses d'unités lorsqu'il est omis (ex. `CellSaver(mL)` transformé en `CellSaver (mL)`).

3. **Planchers minimaux garantis par profil de colonne (`min_pcts`)** :
   - **Colonnes descriptives / narratives** (libellés de résection, descriptions cliniques) : plancher garanti ($\ge 23\%-24\%$) pour éviter les retours à la ligne intempestifs dans les cellules de données.
   - **Identifiants courts** (ex. *« Pièce 1 »*, *« Foie 07/07 »*) : plancher dédié ($\ge 8\%$) maintenant l'identifiant sur une seule ligne.
   - **En-têtes longs ou composés** : planchers stricts ($\ge 11\%-15\%$).
   - **Colonnes compactes** (valeurs numériques, pourcentages, délais) : planchers réduits ($\ge 6\%$) libérant de l'espace pour les colonnes complexes.

4. **Allocation entière Hamilton-Hare (100 % strict)** :
   - Répartition du budget résiduel par la méthode des plus forts restes (Hamilton-Hare), produisant des pourcentages strictement entiers dont la somme fait exactement 100 %, sans dérive d'arrondi lors de la conversion en `\linewidth`.

5. **Inférence automatique des alignements typographiques** :
   - Nombres et pourcentages formés (`17,2`, `1 987`, `50 %`) : alignés à droite (`right`).
   - Codes courts, plages de valeurs, stades de fibrose et statuts binaires (`90–120`, `H23`, `F0`, `Oui`, `Non`) : centrés (`center`).
   - Intitulés textuels et termes narratifs : alignés à gauche (`left`).

6. **Neutralisation des largeurs fixes conflictuelles** :
   - Remplacement automatique des largeurs fixes en pixels (`px()`) qui provoquent des débordements hors page en LaTeX par la répartition optimale en pourcentages.
   - Respect strict des pourcentages manuels fournis par l'auteur si leur total équivaut déjà à 100 %.

7. **Désactivation temporaire ou locale** :
   ```r
   husson_tables_off()
   ```


## Navigation d'en-tête et pied de page (PDF & RevealJS)

Le template intègre un système d'orientation élégant et discret, particulièrement adapté aux mémoires universitaires, thèses et rapports volumineux.

### 1. Barre de navigation hiérarchique d'en-tête (PDF et RevealJS)

Une ligne fine placée en haut de chaque page ou diapositive affiche en temps réel le contexte hiérarchique actif sous forme d'un fil d'Ariane sobre (`H1 | H2 › H3`).

- **Principe visuel** :
  - **Chapitre / Partie (H1)** : libellé mis en valeur à gauche en bleu foncé (`headingblue`, `#17365D`), séparé par un filet vertical `|`.
  - **Sous-sections actives (H2 à H5)** : cheminement affiché avec des chevrons fins `›`.
  - **Filet de séparation** : trait continu discret de 0.3 pt en gris doux (`linegray`, `#D0D4D9`), sans filets gras superflus.
- **Titre court pour l'en-tête (`nav-title`)** :
  Pour éviter qu'un intitulé trop long ne déborde dans la barre d'en-tête, spécifiez un libellé court avec l'attribut `nav-title` :
  ```markdown
  # Matériels et méthodes expérimentales {nav-title="MÉTHODES"}

  ## Conservation dynamique hypothermique oxygénée {nav-title="HOPE"}

  ### Cinétiques de relargage de la FMN {nav-title="FMN"}
  ```
  Rendu dans l'en-tête :
  ```text
  MÉTHODES | HOPE › FMN
  ─────────────────────────────────────────────────────────────────────────────
  ```
- **Masquer la barre sur une section ou diapositive spécifique** :
  Ajoutez l'attribut `{nav="false"}` ou la classe `{.unlisted}` (ou `{.nobar}` pour RevealJS) sur le titre :
  ```markdown
  ## Annexe technique hors plan {nav="false"}
  ```
- **Désactiver globalement la barre d'en-tête** :
  Pour désactiver la barre haute sur tout le document, ajoutez dans le frontmatter YAML :
  ```yaml
  ---
  navigation-bar: false # ou navbar: false
  ---
  ```

### 2. Pied de page structuré et élégant (husson-pdf)

Le pied de page offre une structure soignée et symétrique à l'en-tête :
- **Ligne de séparation** : filet continu de 0.3 pt en gris doux `linegray` (`#D0D4D9`), identique à celui du haut.
- **Coin inférieur gauche** : nom de l'auteur en typographie droite suivi du titre du document en italique, séparés par un tiret cadratin fin (`Auteur – *Titre*`), composé en gris anthracite foncé (`headingcharcoal`, `#34383D`, taille `\scriptsize`).
- **Coin inférieur droit** : numéro de page en noir droit (`\scriptsize`), aligné sur la marge droite.
- **Isolation des pages préliminaires** : la page de couverture (`empty`) et la table des matières (`plain`) restent vierges de tout filet intempestif.

#### Définir un titre court dans la barre du bas (`short-title`)
Pour afficher un titre abrégé uniquement dans le pied de page sans altérer le titre complet de votre page de garde ni vos métadonnées :

```yaml
---
title: "Faisabilité et sécurité de l'utilisation de la décharge cave en perfusion normothermique hépatique"
short-title: "Décharge cave en PNH"
author: "Thomas Husson"
---
```
Rendu en bas de page :
```text
─────────────────────────────────────────────────────────────────────────────
Thomas Husson – Décharge cave en PNH                                        4
```
> **Note** : La clé alternative `footer-title: "..."` est également reconnue. Vous pouvez renseigner cette option à la racine du YAML ou directement sous la section `format: husson-pdf:`.

#### Personnaliser l'auteur dans le pied de page (`footer-author`)
Pour abréger le prénom ou modifier la mention de l'auteur en bas de page :
```yaml
---
footer-author: "T. Husson"
---
```

#### Contrôle total du bloc inférieur gauche (`footer-left`)
Pour remplacer intégralement la mention gauche par une chaîne libre (affiliation, date, projet) :
```yaml
---
footer-left: "T. Husson (CHU Bicêtre) – Étude PNH 2026"
---
```

#### Comportement sans auteur
Si aucun auteur n'est déclaré dans le YAML, le moteur Expl3 s'adapte automatiquement : seul le titre en italique est affiché, sans tiret orphelin.

#### Désactivation ou modification du pied de page
- **Vider le bloc gauche** : définissez `footer-left: ""` dans le YAML (conserve le filet et la pagination à droite).
- **Supprimer les filets** : ajoutez dans le YAML sous `format: husson-pdf:` :
  ```yaml
  format:
    husson-pdf:
      header-includes: |
        \KOMAoptions{headsepline=false, footsepline=false}
  ```

### 3. Diapositives RevealJS : Navigation, titre fixe et protection du bas de diapositive

Sur une présentation RevealJS (`husson-revealjs`), le template offre une suite complète d'optimisations ergonomiques et visuelles :

#### A. Titre fixe (sticky) sur contenu défilant
Les diapositives volumineuses munies de l'attribut `{.scrollable}` conservent automatiquement leur titre ancré au sommet de la vue pendant le défilement vertical du contenu :

```markdown
## Décharge cave : recueil brut {.scrollable}

| ID | Volume brut (mL) | Hématocrite (%) |
|---|---|---|
... (long tableau ou figures défilantes) ...
```

- **Ancrage fixe (`sticky`)** : le titre `h1` ou `h2` reste épinglé en haut de l'écran lors du défilement des données.
- **Fond opaque protecteur** : le texte et les tableaux passent sous le titre sans collision optique.
- **Délimitation nette** : un filet fin inférieur sépare discrètement le titre du corps défilant.
- **Support dark / light mode** : les fonds et bordures basculent automatiquement selon le thème sélectionné.
- **Fil d'Ariane cliquable** : les segments du fil d'Ariane en haut de l'écran permettent de naviguer directement vers le début de chaque chapitre ou section.

#### B. Protection automatique contre le chevauchement du bas de diapositive
Pour éviter que les grandes figures ou les graphiques ne viennent rogner le pied de page, les logos institutionnels (`.dual-logo`), la barre de progression ou les numéros de diapositives :

1. **Rapprochement vertical sobre** : la marge supérieure superflue du premier titre (`h1`, `h2`) et l'interligne avec le paragraphe introductif sont optimisés pour supprimer l'effet de vide sous la barre d'en-tête.
2. **Plafonnement dynamique des figures (`max-height`)** :
   - Par défaut, les images sur diapositive non scrollable sont plafonnées à 480 px.
   - Si la diapositive contient à la fois du texte introductif / une liste et une figure, la hauteur maximale de l'image est automatiquement ajustée (410 px pour une diapositive standard, 440 px pour une diapositive `{.smaller}`).
   - La largeur se redimensionne proportionnellement (`width: auto; max-width: 100%`) pour préserver fidèlement le ratio d'aspect sans déformation.
3. **Recommandations de composition** :
   - Pour les diapositives denses (titre long sur 2 lignes, sous-titre explicatif et grand graphique multi-panneaux), ajoutez la classe `{.smaller}` sur le titre : `## Synthèse comparative {.smaller}`.
   - Spécifiez une largeur modérée pour les figures au format 16:9 ou 4:3 (par exemple `width="780"` à `width="840"` au lieu de 950 ou 1000).

## Insertion d'une page en paysage au milieu du document

Pour intégrer une ou plusieurs pages en orientation paysage (idéal pour les grands tableaux ou les figures larges) au sein d'un document PDF par ailleurs composé en portrait, enveloppez simplement votre contenu dans un bloc `::: {.landscape}` :

```markdown
# Page précédente en portrait normal

::: {.landscape}
# Section en paysage

| Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | Col 6 | Col 7 | Col 8 |
|---|---|---|---|---|---|---|---|
| A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |

```{r}
# Un grand tableau gt ou une figure large ggplot2
```
:::

# Reprise immédiate en portrait normal
```

Grâce au package `pdflscape` inclus dans le préambule du template, le lecteur PDF (Acrobat, Aperçu macOS, navigateur) applique **automatiquement une rotation de 90° à la visualisation**, évitant à l'utilisateur d'avoir à faire pivoter l'affichage manuellement.

## Modèle Word embarqué

Le format `husson-docx` référence directement
`_extensions/husson/template.docx`. Aucun chemin externe n'est nécessaire après l'installation de
l'extension : les styles Word du modèle sont appliqués automatiquement.

## Présentations RevealJS

Le format `husson-revealjs` reprend le thème `auto-dark-clean` et ses ressources
locales. Il suit le thème du système au premier chargement, propose une bascule
clair/sombre et mémorise le choix dans le navigateur.

## Exemple R et Python

`examples/r-python-reticulate.qmd` montre un flux complet piloté par `knitr` :

1. création d'un tableau dans R ;
2. déclaration de `statsmodels` avec `reticulate::py_require()` ;
3. accès à l'objet R depuis Python avec `r.model_data` ;
4. estimation dans Python ;
5. récupération dans R avec `py$model_data_py` ;
6. visualisation finale avec `ggplot2`.

Rendu explicite :

```bash
quarto render examples/r-python-reticulate.qmd
```

L'exemple est conservé dans le projet, mais exclu de `quarto render`. Sa
commande explicite produit un HTML autonome et exécute toute la chaîne
R → Python → R.

Dépendances R de cet exemple : `reticulate`, `ggplot2` et `knitr`.

## Bibliographie

Le template prend en charge nativement les deux modes de citation de Quarto :

### 1. Mode Citeproc (avec feuille de style CSL)

Pour utiliser un fichier de style CSL (ex. AMA, Vancouver, Lancet) :
```yaml
bibliography: references.bib
csl: american-medical-association.csl
cite-method: citeproc
```
- **Typographie compacte automatique** : le préambule LaTeX (`pdf-header.tex`) configure automatiquement l'environnement `CSLReferences` en taille `\footnotesize` (9pt), avec un interligne simple et un espacement vertical inter-items compact de `1.5pt` (`\itemsep`). Cela optimise considérablement l'encombrement des références tout en conservant une lisibilité académique rigoureuse.
- **Recommandation pour le style AMA** : tronquer la liste des auteurs à 3 noms suivis de *et al.* (`et-al-min="4" et-al-use-first="3"`) dans le fichier CSL pour éviter que les articles multicentriques comptant des dizaines de co-auteurs n'allongent inutilement la bibliographie.

### 2. Mode Natbib (par défaut)

Par défaut, `husson-pdf` configure `natbib` et le style `unsrturl` :
```yaml
bibliography: references.bib
```
L'espacement entre les entrées (`\bibsep`) est également calibré automatiquement à `1.5pt`.

## Origine du thème HTML

Le thème HTML reprend les ressources du projet
[`quarto_auto_dark_theme`](https://github.com/thomashusson29/quarto_auto_dark_theme).
Le mécanisme de détection du mode sombre reprend une idée du projet
[`gadenbuie/quarto-auto-dark`](https://github.com/gadenbuie/quarto-auto-dark)
de Garrick Aden-Buie.

Les attributions détaillées sont conservées dans `THIRD_PARTY_NOTICES.md`.
