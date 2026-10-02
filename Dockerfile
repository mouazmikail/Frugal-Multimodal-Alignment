# =============================================================================
# Low-Eval Kit — image de déploiement (chapitre 3, figure 3.3)
#
# La même base sert la référence cloud (A100), la référence locale (RTX 4060)
# et l'environnement terrain contraint (CPU seul) ; la variante GPU ajoute
# uniquement les dépendances lourdes (PyTorch CUDA, Transformers, NF4).
#
# CORRECTION MAJEURE (version 2.0) : l'image n'a plus d'ENTRYPOINT figé.
# L'ancienne image définissait ENTRYPOINT ["python", "scripts/run_evaluation.py"]
# que docker-compose redoublait par un « command: python scripts/run_evaluation.py »,
# produisant l'invocation cassée « python scripts/run_evaluation.py python
# scripts/run_evaluation.py … ». Désormais chaque service compose précise sa
# propre commande, et le conteneur par défaut affiche l'aide.
#
# Construction CPU :   docker build -t low-eval-kit:2.0 .
# Construction GPU :   docker build --target gpu -t low-eval-kit:2.0-gpu .
# Usage :              docker compose --profile eval up
# =============================================================================

# ---------------------------------------------------------------------------
# Étape 1 — image de base CPU : tout le kit sauf l'inférence GPU
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOWEVAL_HOME=/app

WORKDIR /app

# Outils système du protocole de tests dégradés (tableau 3.4) et de la
# chaîne Data-Low : tesseract pour l'OCR contrôlée, tc/cpulimit pour le
# terrain, git pour la métadonnée « commit » (section 7.2).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git iproute2 cpulimit \
        tesseract-ocr tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

# Dépendances CPU uniquement : l'image de base reste utilisable sur toute
# machine, y compris sans GPU (recalcul Bench-Low, Data-Low, rapports).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code des trois artefacts du dépôt mono-référentiel.
COPY loweval/   ./loweval/
COPY data_low/  ./data_low/
COPY bench_low/ ./bench_low/
COPY scripts/   ./scripts/
COPY configs/   ./configs/
COPY dashboard/ ./dashboard/
COPY pyproject.toml ./

RUN chmod +x scripts/*.sh && \
    useradd --create-home --uid 10001 loweval && \
    mkdir -p /app/runs && chown -R loweval /app/runs

# Volumes : corpus Data-Low et journal des exécutions.
VOLUME ["/app/data", "/app/runs"]

# Sans commande explicite, le conteneur affiche l'aide du script principal
# (aucune évaluation n'est lancée par défaut).
CMD ["python", "scripts/run_evaluation.py", "--help"]

# ---------------------------------------------------------------------------
# Étape 2 — variante GPU : ajoute PyTorch CUDA, Transformers et la NF4
# ---------------------------------------------------------------------------
FROM base AS gpu

COPY requirements-gpu.txt ./
RUN pip install --no-cache-dir -r requirements-gpu.txt
