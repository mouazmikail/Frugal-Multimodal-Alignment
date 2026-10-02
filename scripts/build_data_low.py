#!/usr/bin/env python3
"""Script CLI de construction du corpus Data-Low (pipeline en 6 étapes).

Enchaîne, sur un dossier de sujets numérisés :

1. collecte / numérisation (:mod:`data_low.ingest`) ;
2. OCR contrôlée (:mod:`data_low.ocr`) — pages douteuses marquées à relire ;
3. segmentation en exercices (:mod:`data_low.segment`) ;
4. validation syntaxique du lot (:mod:`data_low.validate`) ;
5. insertion en base SQLite + export JSONL (:func:`loweval.db.charger_jsonl`) ;
6. rapport de construction (pages à relire, exercices valides).

Usage :

    python scripts/build_data_low.py --sources scans/ \
        --discipline mathématiques --annee 2023 --serie SN \
        --base data_low/data_low.db --jsonl data_low/corpus.jsonl

Les exercices annotés (solution de référence + concepts + erreurs) sont
ensuite produits par l'annotation experte ; voir :mod:`data_low.annotate`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_low.ingest import collecter_sources, corpus_valide
from data_low.validate import exporter_jsonl
from Low-Eval-Kit import db as base_de_donnees
from Low-Eval-Kit.logging_utils import configurer_journal, get_logger

log = get_logger("scripts.build_data_low")


def analyser_arguments() -> argparse.Namespace:
    """Définit et parse les arguments de la ligne de commande."""
    parseur = argparse.ArgumentParser(
        description="Construction du corpus Data-Low (collecte → OCR → "
                    "segmentation → validation → SQLite + JSONL).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parseur.add_argument("--sources", required=True,
                         help="Dossier contenant les scans / PDF des sujets")
    parseur.add_argument("--discipline", default="mathématiques")
    parseur.add_argument("--annee", type=int, required=True)
    parseur.add_argument("--serie", required=True, help="Série (ex. SN, C, D)")
    parseur.add_argument("--base", default="data_low/data_low.db",
                         help="Base SQLite de destination")
    parseur.add_argument("--jsonl", default="data_low/corpus.jsonl",
                         help="Export JSONL du corpus validé")
    parseur.add_argument("--strict", action="store_true",
                         help="Refuser toute insertion dont la solution de "
                              "référence ou les concepts sont vides (corpus "
                              "publié). Par défaut, l'insertion est tolérante "
                              "— les avertissements sont journalisés — pour "
                              "permettre l'annotation experte ultérieure.")
    return parseur.parse_args()


def main() -> int:
    """Exécute les étapes 1 à 6 et affiche le bilan de construction."""
    args = analyser_arguments()
    configurer_journal(logging.INFO)

    # -- Étapes 1-3 : collecte, OCR contrôlée, segmentation -------------------
    exercices, rapport = collecter_sources(
        args.sources, args.discipline, args.annee, args.serie,
    )
    log.info("Lot brut : %d exercices candidats (%d valides syntaxiquement).",
             rapport.total, rapport.valides)
    if rapport.erreurs:
        log.warning("Exercices avec avertissements : %d — voir le rapport.",
                    len(rapport.erreurs))

    # -- Étape 4 : filtrage (exclut les pages OCR à relire) --------------------
    valides = corpus_valide(exercices)
    a_relire = [ex for ex in exercices if ex.get("ocr_a_relire")]
    log.info("Corpus retenu : %d exercices ; %d page(s) à relire avant usage.",
             len(valides), len(a_relire))

    # -- Étape 5 : export JSONL puis insertion SQLite (ordre imposé : la
    # fonction charger_jsonl du paquet loweval lit le fichier JSONL) ----------
    if valides:
        n = exporter_jsonl(valides, args.jsonl)
        conn = base_de_donnees.init_db(args.base)
        try:
            inseres = base_de_donnees.charger_jsonl(conn, args.jsonl,
                                                    strict=args.strict)
        finally:
            conn.close()
        log.info("%d exercices exportés vers %s et %d insérés dans %s.",
                 n, args.jsonl, inseres, args.base)
    else:
        log.warning("Aucun exercice valide : corpus vide (vérifier les scans).")

    # -- Étape 6 : bilan ---------------------------------------------------------
    print("\n=== Bilan de construction Data-Low ===")
    print(f"  Exercices candidats        : {rapport.total}")
    print(f"  Valides syntaxiquement     : {rapport.valides}")
    print(f"  Corpus retenu (OCR fiable) : {len(valides)}")
    print(f"  Pages à relire humainement : {len(a_relire)}")
    if a_relire:
        print("  → relire avant d'exporter le corpus définitif :")
        for ex in a_relire[:10]:
            print(f"      {ex['id']} (source : {ex['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
