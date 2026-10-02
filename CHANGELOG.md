# CHANGELOG

Toutes les modifications notables du kit sont documentées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
versionnement [SemVer](https://semver.org/lang/fr/).

## [2.0.0] — 2026-10-02

Refonte complète (fond et forme) à partir des spécifications du manuscrit.

### Corrigé (fond)

- **Métriques gold contre gold** : l'ancien pipeline comparait la production
  à elle-même (F1 toujours égal à 1.0). Nouveau module `loweval.parser` :
  le feedback du modèle est structuré (types, segments, concepts) puis
  comparé aux annotations humaines du référentiel.
- **Placeholder mémoire terrain** : `run_field_protocol.py` écrivait
  `memory_gb = 0.0`. Désormais les pics RAM/VRAM et la latence proviennent
  de la table `runs` alimentée par `MoniteurRessources` (psutil + CUDA/pynvml).
- **Double invocation Docker** : `ENTRYPOINT` figé de l'image + `command`
  compose dupliqué produisaient `python scripts/run_evaluation.py python
  scripts/run_evaluation.py …`. L'image n'a plus d'ENTRYPOINT ; chaque
  service compose porte sa commande.
- **UP auto-évalué** : le score composite pouvait être calculé sans jugement
  humain. Le pipeline exige désormais un UP explicite et refuse de publier
  un composite absent (circularité interdite, §2.3.2).
- **`torch_dtype` déprécié** : `model_loader` gère la compatibilité dtype
  récente de Transformers.
- **Exigences monolithiques** : `requirements.txt` forçait bitsandbytes
  (GPU-only) pour le simple recalcul CPU. Séparation en
  `requirements.txt` (noyau), `-gpu`, `-dev`, `-dashboard`, extra `ocr`.

### Ajouté

- **Trois artefacts** : `data_low/` (pipeline de corpus en six étapes,
  OCR contrôlée double moteur, taxonomie à cinq types, double annotation
  n = 150 et arbitrage) et `bench_low/` (recalcul CPU des tableaux 4.1 /
  4.2 et de la sensibilité, oracles YAML).
- **Analyse de sensibilité** : 45 combinaisons de poids (pas 0,05), module
  `loweval.sensitivity`.
- **Rapports** : `loweval.report` — CSV, JSON (avec sensibilité), HTML
  (front de Pareto surligné), fiches par modèle (annexe E), PDF optionnel.
- **Métadonnées §7.2** : huit champs de traçabilité (code, poids, décodage,
  prompt, quantification, matériel, exécutions, cache) journalisés en JSON
  dans `runs.metadonnees`.
- **Tests de non-régression** : reproduction exacte des valeurs publiées
  (ECC = 0.876, S = 0.787 ; front à trois modèles ; 45 combinaisons).
- **Architecture injectable** : prédicteur passé au pipeline — tout le kit
  s'exécute et se teste sur CPU sans GPU ni Transformers.
- **CI GitHub Actions** : lint, tests, démonstration bout en bout,
  archivage des artefacts.

### Modifié (forme)

- Code entièrement commenté en français (fonctions, variables, algorithmes) ;
  alias anglais conservés pour la compatibilité avec l'ancien monolithe.
- Noms de fichiers et exports en français, identifiants d'exercices
  canoniques (`DISCIPLINE-ANNEE-SERIE-NNN`).
- Hiérarchie d'exceptions dédiée (`loweval.errors`) avec codes de sortie.
- Documentation : `MANIFEST.md` (reproductibilité), `docs/DEPLOYMENT.md`,
  `docs/REPRODUCIBILITY.md`, `CITATION.cff`.

## [1.0.0] — version initiale (supersédée)

Monolithe « Low-Eval-Kit » : scores, métriques, Pareto, pipeline, SQLite,
scripts d'évaluation, Dockerfile, compose, dashboard Streamlit.
Bugs fond et forme corrigés en 2.0.0 (voir ci-dessus).
