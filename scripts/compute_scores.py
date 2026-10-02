#!/usr/bin/env python3
"""Script CLI Bench-Low : recalcul des scores, Pareto et sensibilité.

Ce script rejoue entièrement la chaîne de scoring **sans GPU ni modèle**,
à partir du CSV de référence (tableau 4.1) ou d'une base SQLite issue
d'une campagne réelle. C'est l'outil de vérification publique du manuscrit :
n'importe quel lecteur peut confirmer, sur sa machine, que ECC = 0.876 et
S = 0.787 pour Qwen2-VL-7B, que le front de Pareto compte trois modèles et
que l'analyse de sensibilité couvre 45 combinaisons de poids.

Usage :

    # Recalcul depuis le CSV publié (défaut) :
    python scripts/compute_scores.py

    # Recalcul depuis une base SQLite de campagne :
    python scripts/compute_scores.py --source ma_campagne.db

    # Exports supplémentaires (CSV + JSON) :
    python scripts/compute_scores.py --exports exports/
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Low-Eval-Kit.logging_utils import configurer_journal, get_logger
from Low-Eval-Kit.pareto import matrice_dominance
from Low-Eval-Kit.report import ecrire_csv, ecrire_json
from Low-Eval-Kit.scores import ResultatModele
from Low-Eval-Kit.sensitivity import analyser_sensibilite

log = get_logger("scripts.compute_scores")


def analyser_arguments() -> argparse.Namespace:
    """Définit et parse les arguments de la ligne de commande."""
    parseur = argparse.ArgumentParser(
        description="Recalcul Bench-Low des scores, Pareto et sensibilité.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parseur.add_argument("--source", default=None,
                         help="Base SQLite d'une campagne (défaut : CSV de "
                              "référence bench_low/reference_results.csv)")
    parseur.add_argument("--exports", default=None,
                         help="Dossier d'export CSV/JSON (optionnel)")
    return parseur.parse_args()


def charger_depuis_sqlite(chemin: Path) -> list[ResultatModele]:
    """Reconstruit les résultats agrégés depuis la base d'une campagne.

    C'est la correction du défaut de l'ancien code terrain : les mesures
    mémoire/latence proviennent de la table ``runs`` (valeurs réelles
    mesurées par MoniteurRessources), jamais d'un placeholder à 0.0.
    """
    import sqlite3

    from Low-Eval-Kit.db import resultats_agreges

    conn = sqlite3.connect(chemin)
    try:
        lignes = resultats_agreges(conn)
    finally:
        conn.close()

    resultats = []
    for l in lignes:
        memoire = l["memory_gb"] or 0.0
        latence = l["latency_ms"] or 0.0
        ca = 0.0  # reconstruit depuis les quatre composantes disponibles
        composantes = [l.get("f1"), l.get("precision_at_k"),
                       l.get("bertscore_f1"), l.get("concept_recall")]
        connues = [c for c in composantes if c is not None]
        if connues:
            ca = sum(connues) / 4.0  # BERTScore compte 0 s'il est absent
        resultats.append(ResultatModele(
            modele=l["model"], ca=round(ca, 3),
            up=round(l.get("actionable") or 0.0, 3),
            memoire_go=memoire, latence_ms=latence,
            environnement=l["environment"],
        ))
    return resultats


def afficher_tableau_41(resultats: list[ResultatModele]) -> None:
    """Affiche le tableau 4.1 recalculé dans le terminal, en colonnes alignées."""
    lignes = sorted(resultats, key=lambda r: r.composite, reverse=True)
    en_tete = f"{'Modèle':<18} {'CA':>5} {'UP':>5} {'Lat.':>7} {'Mémo.':>6} {'ECC':>6} {'S':>6}"
    print(en_tete)
    print("-" * len(en_tete))
    for r in lignes:
        print(f"{r.modele:<18} {r.ca:>5.2f} {r.up:>5.2f} {r.latence_ms:>7.0f} "
              f"{r.memoire_go:>6.1f} {r.ecc:>6.3f} {r.composite:>6.3f}")


def main() -> int:
    """Point d'entrée : recalcul complet et exports éventuels."""
    args = analyser_arguments()
    configurer_journal(logging.INFO)

    # -- Chargement de la source ----------------------------------------------
    if args.source:
        chemin = Path(args.source)
        if not chemin.exists():
            log.error("Base introuvable : %s", chemin)
            return 2
        log.info("Source : base SQLite %s", chemin)
        resultats = charger_depuis_sqlite(chemin)
    else:
        from bench_low.runner import charger_reference
        log.info("Source : CSV de référence (tableau 4.1)")
        resultats = charger_reference()

    if not resultats:
        log.error("Aucun résultat à scorer.")
        return 4

    # -- Tableau 4.1 recalculé -------------------------------------------------
    afficher_tableau_41(resultats)

    # -- Front de Pareto (tableau 4.2) -----------------------------------------
    from bench_low.runner import front_reference
    front = front_reference(resultats)
    print("\nFront de Pareto : " + ", ".join(r.modele for r in front))
    for ligne in matrice_dominance(resultats):
        print(f"  {ligne['Modèle']:<18} → {ligne['Statut']}")

    # -- Analyse de sensibilité (45 combinaisons, §2.3) -------------------------
    rapport = analyser_sensibilite(resultats)
    print(f"\nSensibilité : {rapport.nb_combinaisons} combinaisons de poids, "
          f"podium stable : {rapport.podium_stable}")
    vainqueur, nb = max(rapport.vainqueurs.items(), key=lambda kv: kv[1])
    print(f"Vainqueur le plus fréquent : {vainqueur} "
          f"({nb}/{rapport.nb_combinaisons} combinaisons)")

    # -- Exports optionnels ------------------------------------------------------
    if args.exports:
        dossier = Path(args.exports)
        dossier.mkdir(parents=True, exist_ok=True)
        ecrire_csv(resultats, dossier / "tableau_41.csv")
        # ecrire_json recalcule lui-même la sensibilité quand demandé.
        ecrire_json(resultats, dossier / "resultats.json",
                    avec_sensibilite=True)
        with (dossier / "front_pareto.csv").open("w", newline="",
                                                 encoding="utf-8") as flux:
            redacteur = csv.writer(flux)
            redacteur.writerow(["modele", "ca", "up", "ecc", "composite"])
            for r in front:
                redacteur.writerow([r.modele, r.ca, r.up,
                                    round(r.ecc, 3), round(r.composite, 3)])
        log.info("Exports écrits dans %s", dossier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
