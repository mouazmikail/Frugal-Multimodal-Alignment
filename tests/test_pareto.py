"""Tests du front de Pareto (§4.2) — dominance, non-dominance, matrice."""

from __future__ import annotations

from Low-Eval-Kit.pareto import domine, front_pareto, matrice_dominance
from Low-Eval-Kit.scores import ResultatModele


def _panel() -> list[ResultatModele]:
    # Mini-panel : A excellent partout, B dominé par A, C meilleur sur ECC seul.
    return [
        ResultatModele("A", ca=0.9, up=0.9, memoire_go=2.0, latence_ms=500.0),
        ResultatModele("B", ca=0.8, up=0.8, memoire_go=8.0, latence_ms=2000.0),
        ResultatModele("C", ca=0.5, up=0.5, memoire_go=1.0, latence_ms=300.0),
    ]


def test_dominance_simple():
    a, b, _ = _panel()
    assert domine(a, b)


def test_non_dominance_mutuelle():
    # A meilleur en CA/UP, C meilleur en ECC → aucun ne domine l'autre.
    a, _, c = _panel()
    assert not domine(a, c)
    assert not domine(c, a)


def test_egalite_ne_dominera_pas():
    a = ResultatModele("X", ca=0.8, up=0.8, memoire_go=4.0, latence_ms=1000.0)
    b = ResultatModele("Y", ca=0.8, up=0.8, memoire_go=4.0, latence_ms=1000.0)
    assert not domine(a, b)  # égalité stricte : pas de domination


def test_front_pareto():
    front = {r.modele for r in front_pareto(_panel())}
    assert front == {"A", "C"}


def test_matrice_dominance():
    matrice = matrice_dominance(_panel())
    par_modele = {l["Modèle"]: l["Statut"] for l in matrice}
    assert par_modele["A"] == "Non dominé"
    assert par_modele["B"].startswith("Dominé par")
    assert par_modele["C"] == "Non dominé"


def test_front_accepts_dicts():
    # Compatibilité dictionnaires (exports JSON de l'ancien code).
    points = [{"model": "A", "ca": 0.9, "up": 0.9, "ecc": 0.9},
              {"model": "B", "ca": 0.8, "up": 0.8, "ecc": 0.8}]
    assert [p["model"] for p in front_pareto(points)] == ["A"]
