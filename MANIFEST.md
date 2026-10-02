# MANIFEST — Guide de reproductibilité des modules

Ce fichier est le **point d'entrée de la reproductibilité** du dépôt
mono-référentiel Low-Eval. Il décrit, module par module : ce que fait le
code, la section du manuscrit qui le spécifie, comment le relire, comment
le vérifier automatiquement et comment le rejouer.

## Vue d'ensemble du dépôt

```
low-eval-kit/                    ← dépôt racine (mono-référentiel)
├── loweval/                     ← Artefact 1 : Low-Eval kit (pipeline)
├── data_low/                    ← Artefact 2 : Data-Low (construction du corpus)
├── bench_low/                   ← Artefact 3 : Bench-Low (recalcul des scores)
├── scripts/                     ← Piliers en ligne de commande
├── configs/                     ← Protocole, panel, oracle Bench-Low (YAML)
├── tests/                       ← Suite de tests CPU (non-régression)
├── dashboard/                   ← Tableau de bord Streamlit (optionnel)
├── data_low/sample/             ← Corpus de démonstration annoté (JSONL)
└── MANIFEST.md                  ← Ce fichier
```

Trois artefacts, un seul dépôt : c'est le choix retenu pour satisfaire la
demande « déployer le Low-Eval kit, le Data-Low et le Bench-Low sur GitHub »
tout en garantissant la cohérence des versions (les trois partagent
`loweval/scores.py`, source unique des formules).

---

## Artefact 1 — Low-Eval kit (`loweval/`)

| Module | Rôle | Manuscrit | Vérification |
|---|---|---|---|
| `scores.py` | Formules CA, UP, ECC, composite, lisibilité | §2.3 (formules 2.1–2.6) | `tests/test_scores.py`, `tests/test_reference_repro.py` |
| `metrics.py` | F1, P@k, rappel concepts, BERTScore, κ de Cohen, ICC(2,1) | §2.3, §4.4 | `tests/test_metrics.py` |
| `pareto.py` | Dominance de Pareto, front, matrice | §4.2 (tableau 4.2) | `tests/test_pareto.py`, `tests/test_reference_repro.py` |
| `sensitivity.py` | 45 combinaisons de poids (pas 0,05) | §2.3, §4.4 | `tests/test_sensitivity.py` |
| `prompts.py` | PromptEngine : gabarit versionné `analyse_formative.v1.2` | §2.6 | `tests/test_pipeline.py` |
| `parser.py` | Analyse structurée des feedbacks (types, segments, concepts) | §2.3 (CA) | `tests/test_parser.py` |
| `pipeline.py` | Les 7 étapes (chargement → export) | §2.6.1 | `tests/test_pipeline.py` |
| `db.py` | Persistance SQLite (journal des runs) | Annexe B | `tests/test_db_data_low.py` |
| `monitoring.py` | Mesures RAM/VRAM/temps (ECC) | §2.3 (ECC) | `tests/test_monitoring.py` |
| `instrumentation.py` | 8 métadonnées de traçabilité | §7.2 | `tests/test_instrumentation.py` |
| `model_loader.py` | Chargement HF + compatibilité dtype | §3.2 | test GPU manuel |
| `quantization.py` | Configuration NF4, taux de réduction | §3.4 (tableau 3.4) | test GPU manuel |
| `config.py` | Protocole et panel depuis YAML | Annexe A | chargement dans chaque test |
| `report.py` | Rapports CSV/JSON/HTML/PDF + fiches (annexe E) | §3.2.3, annexe E | `tests/test_report.py` |
| `errors.py` | Hiérarchie d'exceptions | — | propagée partout |
| `version.py` | Version + commit git (métadonnée n°1) | §7.2 | `tests/test_instrumentation.py` |

**Comment rejouer sans GPU** : le prédicteur est injectable
(`PipelineEvaluation.evaluer(..., predictor=...)`), donc toute la chaîne
s'exécute sur CPU avec `scripts/run_evaluation.py --predicteur simule`.
L'ancien défaut « métriques calculées or contre or (F1 toujours à 1,0) » est
corrigé : `parser.py` structure le feedback du modèle (types, segments,
concepts), puis `pipeline.py` le compare aux annotations humaines.

## Artefact 2 — Data-Low (`data_low/`)

| Module / fichier | Rôle | Manuscrit | Vérification |
|---|---|---|---|
| `schema.sql` | Schéma SQLite (exercices, annotations, runs, résultats) | Annexe B | `tests/test_db_data_low.py`, `tests/test_integration_data_low.py` |
| `schema.py` | Miroir Python du schéma, vérification croisée SQL | Annexe B | `tests/test_integration_data_low.py` |
| `ingest.py` | Étape 1 : collecte / numérisation, ids canoniques | §2.4 | `tests/test_data_low.py`, `tests/test_integration_data_low.py` |
| `ocr.py` | Étape 2 : OCR contrôlée (double moteur, seuil 0,90) | §2.4 | `tests/test_data_low.py` |
| `segment.py` | Étape 3 : segmentation en exercices | §2.4 | `tests/test_data_low.py` |
| `annotate.py` | Étape 4 : solution de référence + concepts + contrôle de spans | §2.4–2.5 | `tests/test_data_low.py` |
| `taxonomie.py` | 5 types d'erreur, κ par type, seuil 0,75 | §2.4 (tableau 2.4) | `tests/test_data_low.py` |
| `qualite.py` | Étape 5 : double annotation n = 150, arbitrage | §2.4 | `tests/test_data_low.py` |
| `validate.py` | Validation + export JSONL | Annexe B | `tests/test_data_low.py` |

**Pipeline complet** : `scripts/build_data_low.py --sources <scans> …`.
**Taxonomie** : les cinq types (`conceptuelle`, `procedurale`,
`visuo-spatiale`, `linguistique`, `calculatoire`) sont contraints par la
base SQLite (clé `CHECK`) : toute valeur hors taxonomie est rejetée à
l'insertion. Le type `calculatoire` (κ pilote = 0,74 < 0,75) est signalé
comme « à renforcer » par `taxonomie.types_a_renforcer`.

## Artefact 3 — Bench-Low (`bench_low/`)

| Fichier | Rôle | Manuscrit | Vérification |
|---|---|---|---|
| `reference_results.csv` | Tableau 4.1 publié (CA, UP, latence, mémoire) | §4.1 | lu par tous les tests de non-régression |
| `runner.py` | Recalcul ECC/composite, front, tableau 4.1 | §4.1–4.2 | `tests/test_reference_repro.py` |
| `configs/bench_low.yaml` | Oracles : front attendu, 45 combinaisons, ECC/S de référence | §2.3, §4 | `tests/test_reference_repro.py` |

**Rejeu en une commande** :

```bash
python scripts/compute_scores.py            # tableau 4.1, Pareto, sensibilité
```

C'est la preuve publique que les formules implémentées produisent
exactement les valeurs publiées du manuscrit (ECC = 0.876, S = 0.787 pour
Qwen2-VL-7B ; front = {Qwen2-VL-7B, LLaVA-1.5-7B, MiniCPM-V-2.8B} ;
45 combinaisons de poids).

---

## Protocole de reproductibilité complet (ordre recommandé)

1. **Environnement** — `pip install -r requirements-dev.txt` (CPU).
2. **Non-régression** — `pytest` : doit être 100 % vert, y compris
   `test_reference_repro.py` (oracles du manuscrit).
3. **Bench-Low** — `python scripts/compute_scores.py` : vérifier visuellement
   le tableau 4.1 recalculé.
4. **Démonstration bout en bout** —
   `python scripts/run_evaluation.py --predicteur simule …` puis
   `python scripts/compute_scores.py --source runs/loweval.db` :
   les scores de la campagne doivent se recalculer depuis la base.
5. **Protocole terrain** — `scripts/simulate_constraints.sh` (tc netem +
   cpulimit) puis évaluation réelle ; le rapport lit les mesures réelles :
   `python scripts/run_field_protocol.py --rapporter --base runs/loweval.db`.
6. **Campagnes GPU** (cloud/local) — `pip install -r requirements-gpu.txt`,
   puis `scripts/run_evaluation.py` sans `--predicteur simule`.
7. **Corpus réel** — `scripts/build_data_low.py` sur les scans, annotation
   experte, double annotation n = 150, arbitrage (§2.4).

Les huit métadonnées de traçabilité (§7.2) sont journalisées en JSON dans
la colonne `runs.metadonnees` à chaque run ; la politique de cache, le
commit, la révision des poids et les paramètres de décodage s'y retrouvent
sans configuration supplémentaire.
