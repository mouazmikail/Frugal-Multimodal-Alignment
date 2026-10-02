# MANIFEST — Manifeste de reproductibilité du Low-Eval Kit (v2.0.0)

Ce fichier est le contrat de reproductibilité du kit. Toute campagne
publiée doit pouvoir être régénérée à partir des seules informations de ce
manifeste et des dépôts `Low-Eval-Kit`, `Data-Low` et `Bench-Low`.

## 1. Périmètre et versionnement

| Élément | Valeur verrouillée |
|---|---|
| Version du kit (`loweval.__version__`) | 2.0.0 |
| Version du schéma Data-Low (`DATA_LOW_SCHEMA_VERSION`) | 2.0 |
| Version du schéma SQLite (annexe C) | 1.0 (fichier `data/schema.sql`) |
| Template de prompt (`template_id`) | `enseignant_stem_analyse` |
| Version du template | 1.1.0 (semver, inchangée = prompt inchangé) |

Toute modification du prompt **doit** incrémenter la version du template ;
le hachage SHA-256 du prompt complet est journalisé par campagne (§7.2).

## 2. Environnements reconnus (configs/protocol.yaml)

Trois environnements sont déclarés et validés : `cloud`, `local`, `terrain`.
L'environnement `terrain` impose CPU plafonné à 50 % et réseau limité à
5 Mbps / 80 ms de latence / 1 % de perte (`scripts/simulate_constraints.sh`
et `scripts/run_field_protocol.py`). Une campagne n'est valide que si elle
déclare l'un de ces trois environnements.

## 3. Modules et responsabilités (annexe F du manuscrit)

| Module | Responsabilité | Couverture de référence |
|---|---|---|
| `loweval.ingest_corpus` | Lecture/validation JSONL, alias v1, identifiants uniques | 90 % |
| `loweval.annotation_store` | Schéma SQLite, campagne `double_annotation_2026`, κ ≥ 0,75 | 87 % |
| `loweval.model_loader` | Chargement NF4, résolution de révision HF | 84 % |
| `loweval.quant_nf4` | Aide quantification NF4, réduction mémoire vs baselines | 81 % |
| `loweval.inference_runner` | Inférence, reprise sur incident, métriques par exercice | 83 % |
| `loweval.instrumentation` | Matériel, version git, RSS, énergie, timer | 74 % |
| `loweval.scoring` | CA/UP/ECC/lisibilité/score S | 92 % |
| `loweval.pareto` | Dominance, front de Pareto, matrice | 81 % |

Modules complémentaires : `config` (validation YAML), `metrics`
(F1/P@k/rappel/κ/BERTScore), `prompt_engine` (versionnage des prompts),
`report_builder` (exports consolidés).

## 4. Métadonnées journalisées par campagne (§7.2 — 8 exigées)

1. version du code (git `describe --exact-match` ou `rev-parse --short`) ;
2. version des poids (révision Hugging Face résolue, jamais inventée) ;
3. paramètres de décodage complets (temperature, top_p, top_k, tokens) ;
4. prompt complet et son hachage SHA-256 ;
5. schéma de quantification (nf4 / float16 / double_quant) ;
6. matériel (CPU, RAM, GPU si présent) ;
7. nombre d'échauffements exclus de la mesure (`n_warmup`) ;
8. politique de cache (HF ou désactivée).

Ces métadonnées sont stockées dans la table `runs` et reprises dans
`campaign.json` (clé `metadata`).

## 5. Paramètres verrouillés

| Paramètre | Valeur | Source |
|---|---|---|
| Graine (`seed`) | 42 | configs/protocol.yaml |
| Répétitions (`n_runs`) | 10 | §3.1 (répétabilité) |
| Échauffements (`n_warmup`) | 2 | §3.1 |
| Température | 0,2 | §3.1 |
| CV de répétabilité max | 3,2 % | §3.1 |
| Seuil κ de Cohen | 0,75 | §3.2 (κ = 0,74 visuo-spatiale → mention d'incertitude obligatoire) |
| Lisibilité `D_max` | 2 niveaux | §3.1, `L = 1 − D/D_max` |
| Mémoire normalisée | 1 → 32 Go | §3.1 |
| Latence de référence | 10 000 ms | §3.1 |
| Poids S | CA 0,4 / UP 0,4 / ECC 0,2 | §3.1 |

## 6. Valeurs de référence verrouillées (tests unitaires)

| Modèle | CA | UP | ECC | S | Statut |
|---|---|---|---|---|---|
| Qwen2-VL-7B | 0,82 | 0,71 | 0,876 | 0,787 | verrouillé (test_scoring) |
| LLaVA-1.5-7B | — | — | — | — | front de Pareto (test_pareto) |
| MiniCPM-V-2.8B | — | — | — | — | front de Pareto (test_pareto) |

Le front de Pareto exact `{Qwen2-VL-7B, LLaVA-1.5-7B, MiniCPM-V-2.8B}` est
verrouillé par `tests/test_pareto.py` sur le référentiel
`data/reference_results.csv` (6 modèles, tableau 4.1).

## 7. Chaîne canonique (§7.1) — commandes de régénération

```bash
# 0. Préparer l'environnement
python -m venv .venv && source .venv/bin/activate   # hors sandbox
pip install pyyaml pandas psutil pytest             # noyau minimal

# 1. Valider le corpus (Data-Low v2)
python scripts/ingest_data_low.py --data ../Data-Low/data/full/exercises.jsonl

# 2. Campagne (dry-run reproductible sans GPU)
python scripts/run_evaluation.py --model Qwen2-VL-7B --env local --dry-run

# 3. Consolidation des scores
python scripts/compute_scores.py --input runs/Qwen2-VL-7B_local_seed42/campaign.json

# 4. Vérifications
python -m pytest tests/ -v
```

## 8. Reprise sur incident (§2.4)

`predictions.jsonl` est écrit en **append immédiat** après chaque exercice.
Relancer la même commande reprend les exercices manquants sans jamais
recommencer au début ; les doublons sont détectés par identifiant unique.

## 9. Checklist avant publication d'une campagne (annexe D)

- [ ] Les 8 métadonnées §7.2 sont présentes dans `campaign.json`.
- [ ] `code_version` et `weights_version` sont des valeurs réelles (git/HF).
- [ ] Les échauffements sont exclus des latences mesurées.
- [ ] CV de répétabilité ≤ 3,2 % sur latence et mémoire.
- [ ] κ ≥ 0,75 ou mention explicite d'incertitude (cas visuo-spatial).
- [ ] Le front de Pareto est recalculé, non recopié.
- [ ] `python -m pytest tests/ -v` passe intégralement.
- [ ] Le référentiel `data/reference_results.csv` n'a pas été modifié.

## 10. Journal des versions

| Version | Date | Changement |
|---|---|---|
| 2.0.0 | 2026 | Alignement fond/forme sur le manuscrit : schéma v2, annexe C, 8 métadonnées, reprise sur incident, modules renommés annexe F. |
| 1.x | antérieur | Version initiale (pipeline monolithique, non conforme). |
