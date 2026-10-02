# Reproductibilité — rejeu des résultats du manuscrit

Ce protocole rejoue, machine à l'appui, les résultats publiés du manuscrit.
Il est exécutable intégralement sur CPU (aucun GPU, aucun modèle, aucune
donnée externe) à l'exception des étapes 6 et 7 signalées.

## R1. Formules de score (§2.3)

```bash
pytest tests/test_scores.py -v
```

Couvre : CA (moyenne F1 / P@k / BERTScore / rappel concepts), UP,
normalisations mémoire `M_norm = 1 − (M−1)/31` et latence
`T_norm = 1 − min(1, T/10000)`, ECC moyenne des deux, composite
`S = 0,4·CA + 0,4·UP + 0,2·ECC`, lisibilité `L = 1 − D/D_max`.

## R2. Tableau 4.1 (scores des six modèles)

```bash
pytest tests/test_reference_repro.py -v
# ou, en direct :
python scripts/compute_scores.py
```

Oracle : Qwen2-VL-7B → ECC = 0.876, S = 0.787 ; InternVL-8B → 0.868 /
0.758 ; LLaVA-1.5-7B → 0.888 / 0.750 ; MiniCPM-V-2.8B → 0.953 / 0.671 ;
Gemma-7B → 0.901 / 0.648 ; Mistral-7B → 0.904 / 0.633.

## R3. Front de Pareto (tableau 4.2)

```bash
pytest tests/test_pareto.py -v
```

Oracle : les trois modèles non dominés sont Qwen2-VL-7B (max CA/UP),
LLaVA-1.5-7B (compromis) et MiniCPM-V-2.8B (max ECC) ; InternVL-8B est
dominé par Qwen2-VL-7B, Gemma-7B et Mistral-7B par MiniCPM-V-2.8B.

## R4. Analyse de sensibilité (§2.3, 45 combinaisons)

```bash
pytest tests/test_sensitivity.py -v
```

Oracle : poids dans [0,2 ; 0,6], pas 0,05, somme = 1 → exactement 45
combinaisons ; Qwen2-VL-7B reste vainqueur sur les 45.

## R5. Pipeline de bout en bout (§2.6.1, les 7 étapes)

```bash
python scripts/run_evaluation.py --modele MiniCPM-V-2.8B \
    --environnement terrain --corpus data_low/sample/corpus_demo.jsonl \
    --up 0.58 --predicteur simule --base runs/loweval.db --sortie runs
python scripts/compute_scores.py --source runs/loweval.db --exports runs/exports
```

Vérifications attendues : la base contient 1 run terrain avec métadonnées
JSON (8 champs §7.2) ; le JSON exporté porte la graine du protocole dans
son nom ; le recalcul depuis la base restitue UP = 0.58 et un composite
identique à l'export.

## R6. Protocole terrain (tableau 2.3) — machine contrainte requise

```bash
sudo ./scripts/simulate_constraints.sh eth0        # 5 Mbps, 80 ms, 1 %, CPU 50 %
cpulimit --limit 50 --include-children -- \
    python scripts/run_evaluation.py --modele MiniCPM-V-2.8B \
    --environnement terrain --corpus data_low/corpus.jsonl \
    --up 0.58 --base runs/loweval.db
python scripts/run_field_protocol.py --rapporter --base runs/loweval.db
```

Le rapport affiche les pics RAM/VRAM et la latence **mesurés** (colonnes
`memory_gb`, `vram_gb`, `latency_ms` de la table `runs`) — correctif du
placeholder 0.0 de la version 1.0.

## R7. Campagne GPU (cloud A100 / local RTX 4060)

```bash
pip install -r requirements-gpu.txt
python scripts/run_evaluation.py --modele Qwen2-VL-7B \
    --environnement local --corpus data_low/corpus.jsonl \
    --up 0.71 --bertscore --base runs/loweval.db --sortie runs
```

Paramètres de décodage, quantification NF4 et révision des poids sont
journalisés automatiquement (métadonnées §7.2). Répéter `n_runs` fois
(protocole : 5) et vérifier CV < 3,2 % (hypothèse H2).

## R8. Chaîne Data-Low (§2.4, six étapes)

```bash
python scripts/build_data_low.py --sources <dossier_scans>/ \
    --discipline mathématiques --annee 2023 --serie SN \
    --base data_low/data_low.db --jsonl data_low/corpus.jsonl
```

Puis annotation experte (solution de référence + concepts, module
`data_low.annotate`), double annotation de 150 exercices et arbitrage
(`data_low.qualite`). Kappas attendus de l'étude pilote (tableau 2.4) :
0.88 / 0.81 / 0.79 / 0.76 / 0.74 — le dernier signale un guide d'annotation
à renforcer (seuil 0.75).

## R9. Accord enseignants–étude (H1, ICC)

```bash
pytest tests/test_metrics.py -k icc -v
```

ICC(2,1) selon Shrout & Fleiss sur les notations croisées ; seuil du
manuscrit : 0.70.

---

**Critère de succès global** : `pytest` entièrement verte + tableaux 4.1 /
4.2 recalculés identiques au manuscrit + campagne de démonstration dont le
recalcul depuis SQLite reproduit l'export JSON. Tout écart est une
régression à traiter avant toute publication.
