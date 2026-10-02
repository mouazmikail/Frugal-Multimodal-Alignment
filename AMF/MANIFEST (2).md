# MANIFEST — Manifeste d'intégrité de Bench-Low

## 1. Principe

Les chiffres publiés ici sont **régénérables** : chaque fichier dérive d'une
commande du Low-Eval Kit appliquée au référentiel verrouillé, et aucune
valeur n'est éditable à la main. Toute publication suit la checklist
d'intégrité ci-dessous.

## 2. Fichiers et origine

| Fichier | Commande productrice | Verrou |
|---|---|---|
| `results/scores_composites.csv` | `python scripts/compute_scores.py --input results/reference_results.csv` | ECC/S recalculés |
| `results/pareto.json` | idem (export `--pareto`) | front exact testé (`tests/test_pareto.py`) |
| `results/reference_results.csv` | campagne du tableau 4.1 | saisie figée — ne jamais modifier |

## 3. Checklist d'intégrité avant publication

- [ ] Le kit utilisé est tagué (`git describe --exact-match` renvoie un tag).
- [ ] Les révisions HF des poids sont renseignées dans `configs/models.yaml`.
- [ ] La campagne déclare les 8 métadonnées §7.2 (versions, seed, matériel…).
- [ ] CV de répétabilité ≤ 3,2 % (latence et mémoire, n = 10 runs).
- [ ] κ ≥ 0,75 sur l'échantillon annoté, ou mention d'incertitude.
- [ ] Les fichiers sont issus de `compute_scores.py`, sans retouche manuelle.
- [ ] Hash SHA-256 du corpus Data-Low utilisé reporté ci-dessous.
- [ ] `python -m pytest tests/ -v` du kit passe sur le tag utilisé.

## 4. Registre des campagnes

| Date | Modèle(s) | Tag kit | Révision poids | Corpus (hash) | Environnement |
|---|---|---|---|---|---|
| référence | 6 modèles (tableau 4.1) | v2.0.0 | voir `configs/models.yaml` | — | cloud |

## 5. Valeurs verrouillées (toute divergence = entrée au registre §4)

* Qwen2-VL-7B : ECC = 0,876 ; S = 0,787.
* Front de Pareto : {Qwen2-VL-7B, LLaVA-1.5-7B, MiniCPM-V-2.8B}.
* Réduction mémoire NF4 vs baselines : 67,9 – 71,9 % (tableau 3.4).
