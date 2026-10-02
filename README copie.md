# Low-Eval Kit — évaluation de VLM en environnement à ressources limitées

Kit de recherche pour évaluer des modèles de langage multimodaux (VLM) dans
des environnements à ressources contraintes (cloud A100, local RTX 4060,
terrain CPU/4G), appliqué à la correction formative de productions d'élèves
en mathématiques. Spécifié par le manuscrit de thèse joint (`main.pdf`).

## Les trois artefacts

| Artefact | Dossier | Rôle |
|---|---|---|
| **Low-Eval kit** | `loweval/` | Pipeline d'évaluation : prompts, inférence, métriques CA/UP, ECC, rapports |
| **Data-Low** | `data_low/` | Construction contrôlée du corpus (OCR, segmentation, annotation, qualité) |
| **Bench-Low** | `bench_low/` | Recalcul indépendant des scores publiés (non-régression) |

Un seul dépôt GitHub, trois paquets Python cohérents par construction — voir
[MANIFEST.md](MANIFEST.md) pour la carte complète des modules.

## Installation

```bash
# Noyau CPU (scores, Bench-Low, Data-Low, rapports, tests)
pip install -r requirements-dev.txt

# + évaluation réelle de modèles (GPU NVIDIA requis)
pip install -r requirements-gpu.txt

# + tableau de bord
pip install -r requirements-dashboard.txt
```

## Démarrage rapide (sans GPU)

```bash
# 1. Non-régression : reproduit ECC = 0.876 et S = 0.787 (Qwen2-VL-7B),
#    le front de Pareto à 3 modèles et les 45 combinaisons de poids.
pytest

# 2. Tableau 4.1 recalculé + Pareto + sensibilité, sans modèle.
python scripts/compute_scores.py

# 3. Campagne de démonstration bout en bout (prédicteur simulé déterministe).
python scripts/run_evaluation.py --modele MiniCPM-V-2.8B \
    --environnement terrain --corpus data_low/sample/corpus_demo.jsonl \
    --up 0.58 --predicteur simule --base runs/loweval.db --sortie runs

# 4. Recalcul Bench-Low à partir de la base réellement produite.
python scripts/compute_scores.py --source runs/loweval.db --exports runs/exports
```

## Campagne réelle (GPU)

```bash
python scripts/run_evaluation.py --modele Qwen2-VL-7B \
    —— environnement local —— corpus data_low/corpus.jsonl —— up 0.71 --bertscore
```

L'UP est **toujours** un jugement humain fourni via `--up` : le kit refuse
de publier un score composite sans UP plutôt que d'en estimer un
(circularité interdite, §2.3.2 du manuscrit).

## Protocole terrain (CPU 2 GHz, 4G simulée)

```bash
sudo ./scripts/simulate_constraints.sh            # tc netem + consignes cpulimit
cpulimit --limit 50 -- python scripts/run_evaluation.py \
    --modele MiniCPM-V-2.8B --environnement terrain \
    --corpus data_low/corpus.jsonl --up 0.58 --base runs/loweval.db
python scripts/run_field_protocol.py --rapporter --base runs/loweval.db
```

Contrairement à la version 1.0, le rapport terrain lit les pics RAM/VRAM et
la latence **mesurés** dans la base SQLite — jamais de valeur factice.

## Docker

```bash
docker build -t low-eval-kit:2.0 .                 # image CPU
docker build --target gpu -t low-eval-kit:2.0-gpu . # variante GPU
docker compose --profile bench up                  # recalcul Bench-Low
docker compose --profile eval up                   # évaluation GPU
docker compose --profile terrain up                # préparation terrain (NET_ADMIN)
docker compose --profile dashboard up              # Streamlit sur :8501
```

L'image n'a plus d'ENTRYPOINT figé (correctif du double appel de la
version 1.0) ; chaque service compose précise sa commande.

## Documentation

- [MANIFEST.md](MANIFEST.md) — reproductibilité module par module ;
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — déploiement GitHub + Docker ;
- [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) — protocole de rejeu
  complet des tableaux du manuscrit ;
- [CHANGELOG.md](CHANGELOG.md) — corrections de fond et de forme (v1.0 → v2.0).
