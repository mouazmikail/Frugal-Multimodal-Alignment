# Déploiement — GitHub, Docker et environnements d'évaluation

Ce document décrit les outils et les étapes pour développer et déployer le
Low-Eval kit, le Data-Low et le Bench-Low. Il complète le
[MANIFEST.md](../MANIFEST.md) (reproductibilité du code) par la mise en
ligne du dépôt et l'exécution conteneurisée.

## 1. Prérequis

| Outil | Version | Usage |
|---|---|---|
| Python | ≥ 3.10 | tout le kit (borne du protocole, tableau 3.2) |
| Git | ≥ 2.30 | versionnement, métadonnée « commit » (§7.2) |
| Docker | ≥ 24 + Compose v2 | images CPU/GPU, services eval/terrain/dashboard |
| CUDA | 12.1+ (optionnel) | environnements cloud/local (GPU NVIDIA) |
| tc / cpulimit | — (optionnel) | contraintes terrain (scripts/simulate_constraints.sh) |
| Tesseract OCR | ≥ 5 | chaîne Data-Low (étape 2, OCR contrôlée) |

## 2. Déploiement sur GitHub (création du dépôt)

```bash
# 1. Initialiser le dépôt local (à la racine du kit).
git init
git add .
git commit -m "Low-Eval kit v2.0.0 : loweval + data_low + bench_low"

# 2. Créer le dépôt distant (gh CLI ou interface web), puis lier et pousser.
gh repo create low-eval-kit --public --description \
  "Évaluation de VLM en environnement à ressources limitées (Low-Eval, Data-Low, Bench-Low)"
git branch -M main
git remote add origin https://github.com/<organisation>/low-eval-kit.git
git push -u origin main

# 3. Étiqueter la version (les métadonnées de run embarquent ce tag).
git tag -a v2.0.0 -m "Version 2.0.0 — correction fond+forme (voir CHANGELOG)"
git push origin v2.0.0
```

Après le premier push, la CI GitHub Actions (`.github/workflows/ci.yml`)
s'exécute automatiquement : lint, tests unitaires CPU, non-régression des
valeurs du manuscrit, démonstration bout en bout et archivage des artefacts.

**Branches protégées recommandées** : `main` protégée par la CI (statut
requis avant fusion) ; les campagnes longues passent par des branches
`campagne/<modele>-<environnement>`.

## 3. Installation locale (développement)

```bash
git clone https://github.com/<organisation>/low-eval-kit.git
cd low-eval-kit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt        # CPU : tests + Bench-Low
pip install -e .                            # paquets loweval/data_low/bench_low
pytest                                      # non-régression (doit être verte)
```

Optionnel, selon la machine :

```bash
pip install -r requirements-gpu.txt        # évaluation réelle de modèles
pip install -r requirements-dashboard.txt  # tableau de bord
pip install -e ".[ocr]"                    # OCR contrôlée Data-Low
```

## 4. Déploiement Docker

### 4.1 Image CPU (Bench-Low, Data-Low, terrain, rapports)

```bash
docker build -t low-eval-kit:2.0 .
docker run --rm -v "$PWD/runs:/app/runs" low-eval-kit:2.0 \
    python scripts/compute_scores.py --exports /app/runs/exports
```

### 4.2 Variante GPU (cloud/local)

```bash
docker build --target gpu -t low-eval-kit:2.0-gpu .
docker run --gpus all --rm \
    -v "$PWD/data:/app/data" -v "$PWD/runs:/app/runs" \
    low-eval-kit:2.0-gpu \
    python scripts/run_evaluation.py --modele Qwen2-VL-7B \
        --environnement cloud --corpus /app/data/corpus.jsonl \
        --up 0.71 --base /app/runs/loweval.db --sortie /app/runs
```

> La variante GPU suppose un hôte avec pilotes NVIDIA + container toolkit.
> Sur la plupart des hôtes cloud (A100), utiliser l'image de base
> `nvidia/cuda:12.1-runtime-ubuntu22.04` comme parent éventuel.

### 4.3 Compose (les quatre profils)

```bash
docker compose --profile bench up          # recalcul Bench-Low → runs/exports
docker compose --profile eval up           # évaluation GPU (cible gpu)
docker compose --profile terrain up        # préparation contraintes (NET_ADMIN)
docker compose --profile dashboard up      # Streamlit http://localhost:8501
```

Variables d'environnement du profil `eval` : `LOWEVAL_MODEL`,
`LOWEVAL_ENV` (`cloud`/`local`), `LOWEVAL_UP` (jugement humain de
l'actionnabilité).

## 5. Publication des résultats

1. **Rapports** : `python scripts/compute_scores.py --exports runs/exports`
   produit `tableau_41.csv`, `resultats.json` (avec sensibilité détaillée)
   et `front_pareto.csv` — publiables tels quels en annexe de publication.
2. **Fiches de supervision** : `loweval.report.ecrire_fiches` génère une
   fiche par modèle (annexe E du manuscrit) pour l'arbitrage humain.
3. **Tableau de bord** : `streamlit run dashboard/app.py` pour l'exploration
   interactive de la base des runs.
4. **Citation** : voir [CITATION.cff](../CITATION.cff) (métadonnées
   Citation File Format, intégrées nativement par GitHub).

## 6. Vérification du déploiement

```bash
pytest                                     # 1. non-régression CPU
python scripts/compute_scores.py           # 2. tableaux du manuscrit recalculés
docker compose --profile bench up          # 3. même recalcul conteneurisé
```

Les trois étapes doivent converger vers les mêmes valeurs (ECC = 0.876,
S = 0.787 pour Qwen2-VL-7B ; front de Pareto à trois modèles ; 45
combinaisons de poids). Tout écart signale une régression : ouvrir une
issue en joignant `runs/exports/resultats.json`.
