# Third-party notices

The Auto Dark and Auto Dark Clean RevealJS resources in this extension come from
[`thomashusson29/quarto_auto_dark_theme`](https://github.com/thomashusson29/quarto_auto_dark_theme),
copyright © 2026 Thomas Husson.

That source project acknowledges Garrick Aden-Buie's
[`gadenbuie/quarto-auto-dark`](https://github.com/gadenbuie/quarto-auto-dark)
for the system colour-scheme design. This extension loads its own CSS directly;
it does not bundle the upstream Lua filter or its CSS-inversion implementation.

This notice records provenance and third-party credits only. It does not grant
a license for this extension or repository.

## Export PPTX (ajout 2026-10-14)

| Composant | Auteur et source | Version / licence | Fichiers concernés et adaptation |
|---|---|---|---|
| `dom-to-pptx` | Atharva Dharmendra Jagtap et contributeurs, [dépôt](https://github.com/atharva9167j/dom-to-pptx) | 2.1.2, MIT ([licence](https://github.com/atharva9167j/dom-to-pptx/blob/master/LICENSE)) | Dépendance npm déclarée dans `pptx/package.json` et verrouillée dans `pptx/package-lock.json`. `pptx/export.mjs` charge son bundle distribué et modifie **en mémoire**, avec vérification de la chaîne source, le test `isBlockDisplay` pour traiter `display:inline-block` comme un conteneur. Aucun fichier du paquet npm n'est modifié ni redistribué. L'adaptateur reconstruit aussi les listes à partir des lignes mesurées par Chromium, capture en pixels à leur géométrie Chromium les petites décorations CSS générées, y compris `counter()` et `attr()`, retire après conversion une capture pleine page parasite qui pourrait masquer les objets modifiables, et signale les formes de contenu non prises en charge avant l'appel à son API. |
| `PptxGenJS` | Brent Ely et contributeurs, [dépôt](https://github.com/gitbrent/PptxGenJS) | 4.0.1, MIT ([licence](https://github.com/gitbrent/PptxGenJS/blob/master/LICENSE)) | Dépendance transitive de `dom-to-pptx`, verrouillée dans `pptx/package-lock.json`. Génération des formes et textes PowerPoint ; aucun fichier source repris ni modifié. |
| `JSZip` | Stuart Knightley et contributeurs, [dépôt](https://github.com/Stuk/jszip) | 3.10.2, MIT OU GPL-3.0-or-later ([licences](https://github.com/Stuk/jszip/blob/main/LICENSE.markdown)) | Dépendance directe déclarée dans `pptx/package.json` et verrouillée dans `pptx/package-lock.json`. `pptx/export.mjs` ouvre le PPTX produit pour ajuster les tailles de caractères et les espacements de paragraphes au facteur RevealJS mesuré ; aucun code source copié ni modifié. |
| `Puppeteer` | The Chromium Authors, [dépôt](https://github.com/puppeteer/puppeteer) | 25.1.0, Apache-2.0 ([licence](https://github.com/puppeteer/puppeteer/blob/main/LICENSE)) | Dépendance directe de `pptx/export.mjs` pour piloter Chromium ; aucun code source repris ni modifié. Le navigateur lui-même est une installation locale, pas un fichier redistribué avec ce template. |
| Quarto Auto Dark Theme | Thomas Husson, [dépôt](https://github.com/thomashusson29/quarto_auto_dark_theme), référence amont examinée au commit `31d06b1e8b3ae2bf84cd9daa12e21b4a0534b594` | MIT ([licence](https://github.com/thomashusson29/quarto_auto_dark_theme/blob/main/LICENSE)). Le commit exact de la copie initiale n'est pas consigné. | Ressources Auto Dark déjà présentes dans `_extensions/husson/` (notamment `auto-dark-clean.scss`, `auto-dark*.css`, `auto-dark.lua`) et adaptées auparavant au template. L'export PPTX les consomme via le rendu RevealJS ; il force le thème clair, masque la bascule clair/sombre sans fonction dans PowerPoint et fournit un repli pour les images compagnons sombres absentes. |

L'adaptateur Husson (`pptx/export.mjs`, `pptx/post-render.mjs`) est du code original écrit pour ce template. Il applique la modification du bundle `dom-to-pptx` décrite ci-dessus uniquement pendant l'exécution et ne copie pas les projets seulement consultés. Les quatre fichiers Carlito version 1.103 présents dans `fonts/` sont chargés localement par `auto-dark-reveal.css` et intégrés au PPTX (`autoEmbedFonts: true`). Carlito est publié par The Carlito Project Authors, avec Łukasz Dziedzic / tyPoland également crédité dans les TTF ([projet source](https://github.com/googlefonts/carlito)), sous [SIL Open Font License 1.1](fonts/OFL.txt). La provenance exacte du commit initial des TTF n'est pas consignée.

### Projets consultés sans reprise de code

- [HTMLtoPPTX](https://github.com/mmoollee101-lab/HTMLtoPPTX), auteur `mmoollee101-lab` : exemple d'orchestration HTML → Chromium → PPTX en ligne de commande. Aucun fichier, algorithme ou règle de mise en page copié.
- [revealjs-to-pptx](https://github.com/ddzeeuw1-ai/revealjs-to-pptx), auteur `ddzeeuw1-ai` : exemple d'ajustements propres à un autre diaporama RevealJS. Aucun code ni règle de thème copié.
- [Retour d'expérience Quarto](https://blenback.github.io/posts/2026-06-04-quarto-presentation-templates.html) : comparaison des rendus RevealJS et PPTX natifs consultée pour le choix d'architecture ; aucun code repris.
