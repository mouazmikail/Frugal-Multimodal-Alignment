"""Tableau de bord Streamlit du journal des runs Low-Eval (§3.2.3).

Lit la base SQLite produite par les campagnes (table ``runs`` + agrégats de
``results``) et présente :

* le tableau 4.1 recalculé par environnement ;
* le front de Pareto qualité/coût ;
* le détail des runs (métadonnées §7.2, mesures réelles RAM/VRAM/latence).

Lancement :  streamlit run dashboard/app.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Racine du dépôt, quel que soit le répertoire de lancement.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from bench_low.runner import charger_reference  # noqa: E402
from Low-Eval-Kit.pareto import matrice_dominance  # noqa: E402
from Low-Eval-Kit.scores import ResultatModele  # noqa: E402

st.set_page_config(page_title="Low-Eval — Tableau de bord", layout="wide")
st.title("Low-Eval — suivi des campagnes d'évaluation")
st.caption("Scores recalculés depuis la base SQLite des runs (mesures réelles).")

# ---------------------------------------------------------------------------
# Chargement de la base (sidebar)
# ---------------------------------------------------------------------------
def _agregats(chemin: str) -> list[dict]:
    """Agrégats par (modèle, environnement) depuis la base des runs."""
    from Low-Eval-Kit.db import resultats_agreges
    conn = sqlite3.connect(chemin)
    try:
        return resultats_agreges(conn)
    finally:
        conn.close()


def _vers_resultats(lignes: list[dict], environnement: str) -> list[ResultatModele]:
    """Convertit les agrégats SQL en ResultatModele (ECC/composite recalculés).

    La CA est reconstruite comme la moyenne des composantes disponibles
    (BERTScore compté 0 s'il n'a pas été calculé), conformément à la formule
    du manuscrit (§2.3).
    """
    resultats = []
    for l in lignes:
        if l["environment"] != environnement:
            continue
        composantes = [l.get("f1"), l.get("precision_at_k"),
                       l.get("bertscore_f1"), l.get("concept_recall")]
        connues = [c for c in composantes if c is not None]
        ca = sum(connues) / 4.0 if connues else 0.0
        resultats.append(ResultatModele(
            modele=l["model"], ca=round(ca, 3),
            up=round(l.get("actionable") or 0.0, 3),
            memoire_go=float(l["memory_gb"] or 0.0),
            latence_ms=float(l["latency_ms"] or 0.0),
            environnement=l["environment"],
        ))
    return resultats


chemin_base = st.sidebar.text_input("Base SQLite des runs",
                                    value="runs/loweval.db")
if not Path(chemin_base).exists():
    st.info(f"Base introuvable : {chemin_base}. Lancez d'abord une campagne "
            "(scripts/run_evaluation.py). Affichage du référentiel Bench-Low.")
    resultats = charger_reference()
    environnement = "référence"
    df_runs = pd.DataFrame()
else:
    conn = sqlite3.connect(chemin_base)
    df_runs = pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC", conn)
    conn.close()
    environnement = st.sidebar.selectbox(
        "Environnement", sorted(df_runs["environment"].unique().tolist())
    )
    resultats = _vers_resultats(_agregats(chemin_base), environnement) \
        or charger_reference()

# ---------------------------------------------------------------------------
# Tableau 4.1 recalculé
# ---------------------------------------------------------------------------
st.subheader(f"Tableau des scores — {environnement}")
if resultats:
    lignes = sorted(resultats, key=lambda r: r.composite, reverse=True)
    st.dataframe(
        pd.DataFrame([{
            "Modèle": r.modele, "CA": round(r.ca, 2), "UP": round(r.up, 2),
            "Latence (ms)": round(r.latence_ms), "Mémoire (Go)": r.memoire_go,
            "ECC": round(r.ecc, 3), "Score composite": round(r.composite, 3),
        } for r in lignes]).set_index("Modèle"),
        use_container_width=True,
    )

    st.subheader("Front de Pareto (CA, UP, ECC — tous maximisés)")
    st.dataframe(pd.DataFrame(matrice_dominance([
        {"model": r.modele, "ca": r.ca, "up": r.up, "ecc": r.ecc}
        for r in resultats
    ])).set_index("Modèle"), use_container_width=True)

# ---------------------------------------------------------------------------
# Journal des runs (métadonnées §7.2, mesures réelles)
# ---------------------------------------------------------------------------
if df_runs is not None and not df_runs.empty:
    st.subheader("Journal des runs (mesures réelles)")
    st.dataframe(
        df_runs[["id", "model", "environment", "seed", "memory_gb", "vram_gb",
                 "latency_ms", "energy_kwh", "metadonnees"]],
        use_container_width=True,
    )
