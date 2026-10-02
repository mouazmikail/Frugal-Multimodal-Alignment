#!/usr/bin/env bash
# =============================================================================
# Simulation des contraintes « terrain » (tableau 2.3 du manuscrit)
#
#   CPU    : 2 GHz (limitation via cpulimit, en pourcent d'un cœur)
#   Réseau : 4G simulée — 5 Mbps, 80 ms de latence, 1 % de pertes (tc netem)
#
# Usage : ./scripts/simulate_constraints.sh [INTERFACE_RESEAU]
#   puis lancer l'évaluation dans le même shell.
# Restauration : ./scripts/simulate_constraints.sh --reset [INTERFACE_RESEAU]
# =============================================================================
set -euo pipefail

INTERFACE="${2:-eth0}"
ACTION="${1:-apply}"

appliquer() {
    # --- Réseau : file netem avec débit, latence et pertes ------------------
    if command -v tc >/dev/null 2>&1; then
        sudo tc qdisc replace dev "$INTERFACE" root netem \
            rate 5mbit delay 80ms loss 1%
        echo "[terrain] tc netem appliqué sur $INTERFACE (5 Mbps, 80 ms, 1 %)."
    else
        echo "[terrain] ATTENTION : 'tc' introuvable — contraintes réseau non appliquées." >&2
    fi

    # --- CPU : consigne d'enveloppement par cpulimit ------------------------
    if command -v cpulimit >/dev/null 2>&1; then
        echo "[terrain] Enveloppez l'évaluation ainsi :"
        echo "          cpulimit --limit 50 --include-children -- \\"
        echo "              python scripts/run_evaluation.py --environnement terrain ..."
    else
        echo "[terrain] ATTENTION : 'cpulimit' introuvable — limitation CPU manuelle." >&2
    fi
}

restaurer() {
    if command -v tc >/dev/null 2>&1; then
        sudo tc qdisc del dev "$INTERFACE" root 2>/dev/null || true
        echo "[terrain] Contraintes réseau supprimées sur $INTERFACE."
    fi
}

case "$ACTION" in
    apply)  appliquer ;;
    --reset) restaurer ;;
    *) echo "Usage : $0 [--reset] [interface] (défaut : eth0)" >&2; exit 2 ;;
esac
