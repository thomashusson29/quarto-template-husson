# Directives et Règles de Développement

## 1. Règle Doc-First : Lecture et Respect du README
- **Consultation préalable obligatoire** : Avant de vouloir modifier ou déboguer une fonction, vérifier systématiquement s'il existe un `README.md` (ou documentation de référence) dans le projet ou le template.
- **Lecture et analyse de la spécification** : Lire attentivement le README pour comprendre l'architecture, le contrat d'interface et le comportement attendu avant d'intervenir sur le code.
- **Correction guidée par la spécification** : Chercher à corriger la fonction défaillante en se basant sur ce que stipule le README plutôt que de modifier le comportement de façon ad hoc.
- **Mise à jour chirurgicale et cohérente** : Après toute modification ou ajout de fonctionnalité, mettre à jour le README de manière ordonnée. Ne jamais injecter de texte en vrac ou le placer n'importe où : l'insertion doit s'intégrer harmonieusement à l'endroit logique du plan, en respectant la structure, le niveau de détail et le style du document existant.

## 2. Règles de Sécurité Critiques (Anti-Destruction)
- **Interdiction d'écraser/remplacer globalement** : Ne jamais remplacer le contenu complet d'un fichier de travail (notamment les fichiers `.qmd`, `.R`, `.py`) par un fichier de sauvegarde ou une version antérieure sans accord explicite.
- **Vérification systématique de l'état Git** : Toujours vérifier le statut Git (`git status`, diff) avant toute modification ou restauration.
- **Sauvegarde préventive obligatoire** : En cas de modification majeure, copier systématiquement le fichier d'origine dans `scratch/` sous un nom daté.
- **Respect du travail de l'utilisateur** : Préserver intégralement les commentaires cliniques, interprétations et structures introduites par l'utilisateur.

## 3. Rigueur Factuelle et Interdiction Absolue des Émojis
- **Honnêteté des actions** : Ne jamais prétendre avoir exécuté une action sans appel d'outil réel.
- **Transparence sur les erreurs** : Reconnaître immédiatement toute erreur ou manque d'information sans inventer d'hypothèses.
- **Aucun émoji** : Strictement aucun émoji dans les réponses, le code, les commentaires, les scripts, la documentation ou les commits.
