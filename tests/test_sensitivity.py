"""Tests de l'analyse de sensibilité (§2.3) — 45 combinaisons, stabilité."""

from __future__ import annotations

import pytest

from Low-Eval-Kit.scores import ResultatModele
from Low-Eval-Kit.sensitivity import analyser_sensibilite, combinaisons_poids


def test_nb_combinaisons_est_45():
    # Oracle du manuscrit : pas 0,05 dans [0,2 ; 0,6], somme = 1 → 45.
    assert len(combinaisons_poids()) == 45


def test_toutes_les_combinaisons_sont_valides():
    for w_ca, w_up, w_ecc in combinaisons_poids():
        assert abs(w_ca + w_up + w_ecc - 1.0) < 1e-9
        assert 0.2 <= w_ca <= 0.6
        assert 0.2 <= w_up <= 0.6
        assert 0.2 <= w_ecc <= 0.6


def test_combinaisons_deterministes():
    assert combinaisons_poids() == combinaisons_poids()


def test_vainqueur_stable_sur_le_referentiel():
    # Sur le tableau 4.1, Qwen2-VL-7B domine quel que soit le poids plausible.
    from bench_low.runner import charger_reference
    rapport = analyser_sensibilite(charger_reference())
    assert rapport.nb_combinaisons == 45
    assert rapport.vainqueurs["Qwen2-VL-7B"] == 45
    assert rapport.marge_min_vainqueur > 0


def test_analyse_exige_au_moins_un_modele():
    with pytest.raises(ValueError):
        analyser_sensibilite([])


def test_analyse_tolerise_un_seul_modele():
    # Campagne SQLite à un seul modèle : marge nulle, podium triviallement stable.
    r = ResultatModele("Seul", ca=0.5, up=0.5, memoire_go=4.0, latence_ms=1000.0)
    rapport = analyser_sensibilite([r])
    assert rapport.vainqueurs == {"Seul": 45}
    assert rapport.podium_stable
