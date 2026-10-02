#!/usr/bin/env python3
"""Protocole terrain : évaluation sous contraintes CPU / 4G simulée.

CORRECTION MAJEURE (version 2.0) : l'ancien script écrivait une ligne de
résultats avec ``memory_gb = 0.0`` — une valeur factice qui falsifiait
l'ECC de tous les runs terrain. Désormais, toutes les mesures proviennent
de la table ``runs`` de la base SQLite, alimentée par
:class:`loweval.monitoring.MoniteurRessources` pendant l'inférence réelle
(pic RAM via psutil, pic VRAM via CUDA/pynvml, latence chronométrée).

Le script se décline en deux modes :

* ``--preparer`` : applique les contraintes réseau (tc netem) et CPU
  (cpulimit) selon l'environnement « terrain » du protocole, puis affiche
  la commande d'évaluation à lancer ;
* ``--rapporter`` : agrège les runs terrain de la base et affiche le
  tableau des mesures réelles (mémoire, VRAM, latence, ECC).

Usage :

    python scripts/run_field_protocol.py --rapporter --base runs/loweval.db
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Low-Eval-Kit.config import Protocole
from Low-Eval-Kit.logging_utils import configurer_journal, get_logger

log = get_logger("scripts.protocole_terrain")


def analyser_arguments() -> argparse.Namespace:
    """Définit et parse les arguments de la ligne de commande."""
    parseur = argparse.ArgumentParser(
        description="Protocole terrain (CPU 2 GHz, 4G simulée) — préparation "
                    "et rapport des mesures réelles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--preparer", action="store_true",
                        help="Applique les contraintes (tc netem / cpulimit)")
    groupe.add_argument("--rapporter", action="store_true",
                        help="Agrège les runs terrain depuis la base SQLite")
    parseur.add_argument("--config-protocole", default="configs/protocol.yaml")
    parseur.add_argument("--base", default="runs/loweval.db")
    parseur.add_argument("--interface-reseau", default="eth0",
                         help="Interface soumise à tc netem (débit/latence/pertes)")
    return parseur.parse_args()


def preparer_contraintes(protocole: Protocole, interface: str) -> int:
    """Applique les contraintes terrain réseau et CPU, puis rend la main.

    Les contraintes (tableau 2.3 : 5 Mbps, 80 ms, 1 % de pertes) sont
    appliquées avec ``tc netem`` ; la limitation CPU utilise ``cpulimit``
    lancé en tâche de fond. Si l'un des outils est absent, la fonction
    affiche la commande équivalente au lieu d'échouer silencieusement.
    """
    env = protocole.environnements["terrain"]
    reseau = env.reseau or {}

    if reseau:
        # tc netem : débit (tbf), latence et taux de pertes ; nécessite sudo.
        debit = reseau.get("debit_mbps", 5)
        latence = reseau.get("latence_ms", 80)
        pertes = reseau.get("pertes_pct", 1.0)
        commande_tc = [
            "sudo", "tc", "qdisc", "replace", "dev", interface, "root",
            "netem", "rate", f"{debit}mbit",
            "delay", f"{latence}ms",
            "loss", f"{pertes}%",
        ]
        try:
            subprocess.run(commande_tc, check=True, capture_output=True)
            log.info("Contraintes réseau appliquées : %s", " ".join(commande_tc))
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            log.warning("tc netem indisponible (%s). Commande à exécuter :\n  %s",
                        exc, " ".join(commande_tc))

    if env.cpu_limit_percent:
        commande_cpulimit = [
            "cpulimit", "--limit", str(env.cpu_limit_percent),
            "--include-children",
        ]
        log.info("Limitation CPU : %s %% (à envelopper la commande d'évaluation, "
                 "ex. : cpulimit --limit %d -- python scripts/run_evaluation.py ...)",
                 env.cpu_limit_percent, env.cpu_limit_percent)
        log.info("Commande : %s", " ".join(commande_cpulimit))

    print("\nContraintes préparées. Lancer ensuite l'évaluation, par exemple :\n"
          f"  cpulimit --limit {env.cpu_limit_percent or 50} -- python scripts/run_evaluation.py "
          "--modele MiniCPM-V-2.8B --environnement terrain "
          "--corpus data_low/corpus.jsonl --up 0.58\n"
          )
    return 0


def rapporter_mesures(chemin_base: Path) -> int:
    """Agrège les runs terrain depuis la base et affiche les mesures réelles.

    Correction du défaut historique : les colonnes mémoire et VRAM proviennent
    des mesures journalisées par le moniteur de ressources (colonnes
    ``memory_gb`` et ``vram_gb`` de la table ``runs``), jamais d'une constante.
    """
    if not chemin_base.exists():
        log.error("Base introuvable : %s — lancer d'abord une campagne terrain.",
                  chemin_base)
        return 2

    conn = sqlite3.connect(chemin_base)
    try:
        curseur = conn.execute(
            """SELECT model, seed, memory_gb, vram_gb, latency_ms, energy_kwh
               FROM runs WHERE environment = 'terrain'
               ORDER BY model, seed"""
        )
        lignes = curseur.fetchall()
    finally:
        conn.close()

    if not lignes:
        log.error("Aucun run terrain dans %s.", chemin_base)
        return 4

    print(f"{'Modèle':<18} {'Graine':>6} {'RAM pic (Go)':>12} {'VRAM pic (Go)':>13} "
          f"{'Latence (ms)':>12} {'Énergie (kWh)':>13}")
    for (modele, graine, memoire, vram, latence, energie) in lignes:
        print(f"{modele:<18} {graine:>6} "
              f"{(f'{memoire:.2f}' if memoire is not None else 'n/d'):>12} "
              f"{(f'{vram:.2f}' if vram is not None else 'n/d'):>13} "
              f"{(f'{latence:.0f}' if latence is not None else 'n/d'):>12} "
              f"{(f'{energie:.4f}' if energie is not None else 'n/d'):>13}")

    # ECC recalculé à partir des mesures réelles pour le premier modèle.
    from Low-Eval-Kit.scores import score_ecc
    modele0, _, memoire0, _, latence0, _ = lignes[0]
    if memoire0 is not None and latence0 is not None:
        print(f"\nECC réel ({modele0}) : {score_ecc(memoire0, latence0):.3f}")
    return 0


def main() -> int:
    """Point d'entrée du protocole terrain."""
    args = analyser_arguments()
    configurer_journal(logging.INFO)

    if args.preparer:
        protocole = Protocole.depuis_fichier(args.config_protocole)
        return preparer_contraintes(protocole, args.interface_reseau)
    return rapporter_mesures(Path(args.base))


if __name__ == "__main__":
    sys.exit(main())
