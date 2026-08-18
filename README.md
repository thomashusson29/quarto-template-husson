# Quarto Template Husson

Extension Quarto personnelle fournissant deux formats cohérents :

- `husson-pdf` : PDF XeLaTeX A4, code R/Python différencié, tableaux espacés
  et largeurs de colonnes calculées automatiquement ;
- `husson-html` : HTML clair/sombre fondé sur la palette One Dark et suivant
  automatiquement les préférences du système.

## Créer un nouveau projet

```bash
quarto use template thomashusson29/quarto-template-husson
cd <nom-du-projet>
quarto render
```

Le rendu est écrit dans `output/` et contient un fichier HTML et un PDF.

Pour une seule sortie :

```bash
quarto render --to husson-pdf
quarto render --to husson-html
```

## Ajouter les formats à un projet existant

```bash
quarto add thomashusson29/quarto-template-husson
```

Puis, dans le YAML du projet ou du document :

```yaml
format:
  husson-html: default
  husson-pdf: default
```

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
de Garrick Aden-Buie. La palette One Dark et le traitement des figures sont
maintenus par Thomas Husson.

Les attributions détaillées sont conservées dans `THIRD_PARTY_NOTICES.md`.

## Licence

MIT. Voir `LICENSE`.
