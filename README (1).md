<div align="center">

# Frugal Multimodal Alignment

**Évaluation frugale de modèles multimodaux pour l'éducation — Bench-Low · Data-Low · Low-Eval Kit**

[![Thèse](https://img.shields.io/badge/Thèse-CY%20Cergy%20Paris%20Université-blue)](https://www.u-cergy.fr/)
[![Version](https://img.shields.io/badge/version-v2.0.0-green)](https://github.com/mouazmikail/low-eval-kit/releases/tag/v2.0.0)
[![Licence codes](https://img.shields.io/badge/licence-recherche-lightgrey)](./LICENSE)
[![Licence corpus](https://img.shields.io/badge/corpus-CC%20BY--NC%204.0-orange)](https://creativecommons.org/licenses/by-nc/4.0/)
[![CI](https://github.com/mouazmikail/low-eval-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/mouazmikail/low-eval-kit/actions)

*Mouaz Mikail — manuscrit « Frugal Multimodal Alignment », CY Cergy Paris Université.*

</div>

---

## Le projet en un coup d'œil

Ce dépôt racine est la **page de garde** du projet : il oriente vers les trois
dépôts qui composent le protocole complet d'évaluation frugale de modèles
vision-langage (VLM) appliqué à l'analyse d'exercices mathématiques de
contextes à ressources limitées.

| Dépôt | Rôle | Contenu clé |
|---|---|---|
| [**low-eval-kit**](https://github.com/mouazmikail/low-eval-kit) | Codes du protocole | Chaîne canonique 7 étapes (§7.1), 12 modules commentés (annexe F), 8 métadonnées journalisées (§7.2), reprise sur incident, tests verrouillés, CI, Docker |
| [**data-low**](https://github.com/mouazmikail/data-low) | Corpus annoté | Sujets du baccalauréat tchadien (séries C, D, E), schéma v2.0 (tableau 2.6), taxonomie des 5 familles d'erreurs (κ ≥ 0,75), pipeline scan → annotation, CC BY-NC 4.0 |
| [**bench-low**](https://github.com/mouazmikail/bench-low) | Résultats verrouillés | Référentiel tableau 4.1 (6 modèles), scores régénérés par le kit — jamais édités à la main — front de Pareto, registre d'intégrité |

## Le score composite

```
S = 0,4·CA + 0,4·UP + 0,2·ECC
```

- **CA** — exactitude d'analyse : F1 macro, Precision@k, BERTScore F1, rappel de concepts.
- **UP** — utilité pédagogique : actionnabilité, clarté, lisibilité, adaptabilité (jugement humain, référence principale).
- **ECC** — sobriété : mémoire normalisée (1 → 32 Go) et latence (réf. 10 000 ms).

## Valeurs de référence verrouillées

| Modèle | CA | UP | ECC | S | Front de Pareto |
|---|---|---|---|---|---|
| **Qwen2-VL-7B** | 0,82 | 0,71 | **0,876** | **0,787** | ★ |
| LLaVA-1.5-7B | 0,78 | 0,65 | 0,888 | 0,750 | ★ |
| MiniCPM-V-2.8B | 0,62 | 0,58 | 0,953 | 0,671 | ★ |

Ces valeurs sont reproduites par les tests unitaires du kit (`tests/`),
qui échouent si une modification les fait dériver.

## Démarrage rapide

```bash
git clone https://github.com/mouazmikail/low-eval-kit.git
cd low-eval-kit
pip install pyyaml pandas psutil pytest
python -m pytest tests/ -v                                   # 32 tests verrouillés
python scripts/run_evaluation.py --model Qwen2-VL-7B --env local --dry-run
python scripts/compute_scores.py --input data/reference_results.csv
```

## Reproductibilité

Chaque dépôt embarque un **`MANIFEST.md`** : paramètres verrouillés (graine 42,
n = 10 runs, n = 150 double annotation, κ ≥ 0,75, CV ≤ 3,2 %), commandes de
régénération et checklist annexe D. Les références croisées entre dépôts
(tag du kit, hash du corpus, registre des campagnes) garantissent qu'aucun
chiffre publié ne l'est sans traçabilité complète.

## Citation

```bibtex
@phdthesis{mikail2026frugal,
  author = {Mikail, Mouaz},
  title  = {Frugal Multimodal Alignment},
  school = {CY Cergy Paris Université},
  year   = {2026},
  note   = {Bench-Low + Data-Low + Low-Eval Kit, v2.0.0}
}
```

## Licence

Codes du kit : usage libre pour la recherche avec citation. Corpus et
annotations Data-Low : [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
Les sujets d'examen scannés restent la propriété de l'État tchadien
(diffusion à des fins de recherche uniquement).
