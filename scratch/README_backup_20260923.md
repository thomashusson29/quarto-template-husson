# Quarto Template Husson

Extension Quarto personnelle fournissant quatre formats cohérents :

- `husson-pdf` : PDF XeLaTeX A4, code R/Python différencié, tableaux espacés
  et largeurs de colonnes calculées automatiquement ;
- `husson-html` : HTML clair/sombre fondé sur la palette One Dark et suivant
  automatiquement les préférences du système ;
- `husson-docx` : document Word utilisant automatiquement le modèle éditorial
  embarqué dans l'extension ;
- `husson-revealjs` : présentation RevealJS avec le thème clair
  Auto Dark Clean et bascule automatique ou manuelle vers One Dark.

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

Pour un contrôle encore plus fin à l'évaluation R (avec `gt` et `gtsummary`), le module `gt-page-fit.R` peut être activé :
```r
source("_extensions/husson/gt-page-fit.R")
husson_tables_on()
```

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

Le format PDF configure `natbib` et le style `unsrturl`, mais n'impose aucun
fichier bibliographique. Chaque document peut déclarer son propre fichier :

```yaml
bibliography: references.bib
```

## Origine du thème HTML

Le thème HTML reprend les ressources du projet
[`quarto_auto_dark_theme`](https://github.com/thomashusson29/quarto_auto_dark_theme).
Le mécanisme de détection du mode sombre reprend une idée du projet
[`gadenbuie/quarto-auto-dark`](https://github.com/gadenbuie/quarto-auto-dark)
de Garrick Aden-Buie.

Les attributions détaillées sont conservées dans `THIRD_PARTY_NOTICES.md`.
