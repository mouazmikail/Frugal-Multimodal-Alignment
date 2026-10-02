"""Non-régression : le code reproduit-il exactement les valeurs publiées ?

C'est le test le plus important du dépôt : toute modification des formules
de ``loweval.scores`` ou de la logique Pareto doit faire échouer ce fichier
si elle change les résultats du manuscrit (tableaux 4.1 et 4.2, §2.3).
"""

from __future__ import annotations

import pytest

from bench_low.runner import (
    FRONT_PARETO_REFERENCE,
    charger_reference,
    front_reference,
    rapport_tableau_41,
)
from Low-Eval-Kit.sensitivity import analyser_sensibilite

# Oracle complet du tableau 4.1 (modèle → CA, UP, ECC, S), arrondis du manuscrit.
TABLEAU_41_ATTENDU = {
    "Qwen2-VL-7B":    (0.82, 0.71, 0.876, 0.787),
    "InternVL-8B":    (0.79, 0.67, 0.868, 0.758),
    "LLaVA-1.5-7B":   (0.78, 0.65, 0.888, 0.750),
    "MiniCPM-V-2.8B": (0.62, 0.58, 0.953, 0.671),
    "Gemma-7B":       (0.61, 0.56, 0.901, 0.648),
    "Mistral-7B":     (0.59, 0.54, 0.904, 0.633),
}


def test_tableau_41_reproduit_exactement():
    resultats = charger_reference()
    assert len(resultats) == 6
    for r in resultats:
        ca, up, ecc, s = TABLEAU_41_ATTENDU[r.modele]
        assert r.ca == pytest.approx(ca, abs=1e-9)
        assert r.up == pytest.approx(up, abs=1e-9)
        assert round(r.ecc, 3) == ecc, f"ECC de {r.modele}"
        assert round(r.composite, 3) == s, f"S de {r.modele}"


def test_qwen2_vl_7b_valeurs_cles():
    # Les deux valeurs les plus citées du manuscrit, vérifiées isolément.
    qwen = next(r for r in charger_reference() if r.modele == "Qwen2-VL-7B")
    assert round(qwen.ecc, 3) == 0.876
    assert round(qwen.composite, 3) == 0.787


def test_front_pareto_a_trois_modeles():
    front = tuple(r.modele for r in front_reference(charger_reference()))
    assert front == FRONT_PARETO_REFERENCE


def test_dominance_internvl_par_qwen():
    # InternVL-8B est dominé par Qwen2-VL-7B (CA, UP et ECC inférieurs).
    from Low-Eval-Kit.pareto import domine
    res = {r.modele: r for r in charger_reference()}
    assert domine(res["Qwen2-VL-7B"], res["InternVL-8B"])


def test_sensibilite_45_combinaisons():
    rapport = analyser_sensibilite(charger_reference())
    assert rapport.nb_combinaisons == 45


def test_rapport_tableau_41_trie_par_composite():
    lignes = rapport_tableau_41(charger_reference())
    scores = [l["Score composite"] for l in lignes]
    assert scores == sorted(scores, reverse=True)
