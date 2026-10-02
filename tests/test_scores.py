"""Tests unitaires des formules de score (section 2.3 du manuscrit).

Oracles : valeurs limites des normalisations, pondération officielle
0,4 / 0,4 / 0,2 et reproduction des bornes du tableau 4.1.
"""

from __future__ import annotations

import pytest

from Low-Eval-Kit.scores import (
    ResultatModele,
    latence_norm,
    memoire_norm,
    score_ca,
    score_composite,
    score_ecc,
    score_lisibilite,
    score_up,
)


class TestNormalisations:
    """Les normalisations bornent ECC dans [0, 1] par construction."""

    def test_memoire_minimale_vaut_un(self):
        # M = 1 Go (borne inférieure) → M_norm = 1 : coût nul.
        assert memoire_norm(1.0) == pytest.approx(1.0)

    def test_memoire_maximale_vaut_zero(self):
        # M = 32 Go (borne supérieure) → M_norm = 0 : coût maximal.
        assert memoire_norm(32.0) == pytest.approx(0.0)

    def test_memoire_intermediaire(self):
        # M = 4,3 Go → 1 − (4,3−1)/31 ≈ 0,8935 (valeur du tableau 4.1, Qwen2-VL-7B).
        assert memoire_norm(4.3) == pytest.approx(1 - 3.3 / 31, rel=1e-3)

    def test_memoire_hors_borne_bornee(self):
        # Au-delà de 32 Go, la normalisation reste à 0 (pas de valeur négative).
        assert memoire_norm(64.0) == 0.0

    def test_latence_nulle_vaut_un(self):
        assert latence_norm(0.0) == pytest.approx(1.0)

    def test_latence_au_dela_de_la_reference_vaut_zero(self):
        # T ≥ 10 000 ms → coût maximal (min(1, T/10000)).
        assert latence_norm(20000.0) == pytest.approx(0.0)


class TestCAetUP:
    """CA : moyenne arithmétique des quatre composantes ; UP : actionnabilité."""

    def test_ca_moyenne_quatre_composantes(self):
        assert score_ca(0.8, 0.6, 0.7, 0.9) == pytest.approx(0.75)

    def test_ca_composantes_identiques(self):
        assert score_ca(0.5, 0.5, 0.5, 0.5) == pytest.approx(0.5)

    def test_up_moyenne_quatre_indicateurs(self):
        # UP = moyenne actionnabilité/clarté/lisibilité/adaptabilité (tableau 2.2).
        assert score_up(0.7, 0.7, 0.7, 0.7) == pytest.approx(0.7)
        assert score_up(0.8, 0.6, 0.8, 0.6) == pytest.approx(0.7)


class TestECCetComposite:
    """ECC moyenne M_norm et T_norm ; composite pondéré 0,4/0,4/0,2."""

    def test_ecc_moyenne_des_deux_normalisations(self):
        # M = 1 Go → 1,0 ; T = 0 ms → 1,0 → ECC = 1,0.
        assert score_ecc(1.0, 0.0) == pytest.approx(1.0)

    def test_composite_pondere_officiel(self):
        # Pondération du manuscrit : S = 0,4·CA + 0,4·UP + 0,2·ECC.
        assert score_composite(0.8, 0.6, 0.5) == pytest.approx(0.66)

    def test_composite_poids_custom_somme_un(self):
        assert score_composite(0.8, 0.6, 0.5, 0.2, 0.3, 0.5) == pytest.approx(0.59)

    def test_composite_rejette_poids_invalides(self):
        with pytest.raises(ValueError):
            score_composite(0.8, 0.6, 0.5, 0.5, 0.5, 0.5)  # somme ≠ 1


class TestLisibilite:
    """L = 1 − D/D_max : un écart nul est parfaitement lisible."""

    def test_ecart_nul(self):
        assert score_lisibilite(0.0, 10.0) == pytest.approx(1.0)

    def test_ecart_maximal(self):
        assert score_lisibilite(10.0, 10.0) == pytest.approx(0.0)

    def test_ecart_borne_a_maximum(self):
        # Au-delà de D_max, la lisibilité reste à 0.
        assert score_lisibilite(25.0, 10.0) == pytest.approx(0.0)


class TestResultatModele:
    """Le dataclass dérive ECC et composite à la construction."""

    def test_derivation_automatique(self):
        r = ResultatModele(modele="X", ca=0.82, up=0.71,
                           memoire_go=4.3, latence_ms=1420.0)
        assert r.ecc == pytest.approx(score_ecc(4.3, 1420.0))
        assert r.composite == pytest.approx(score_composite(0.82, 0.71, r.ecc))

    def test_ligne_export_avec_arrondis_manuscrit(self):
        r = ResultatModele(modele="X", ca=0.82, up=0.71,
                           memoire_go=4.3, latence_ms=1420.0)
        ligne = r.en_ligne()
        assert ligne["ECC"] == round(r.ecc, 3)
        assert ligne["Score composite"] == round(r.composite, 3)
