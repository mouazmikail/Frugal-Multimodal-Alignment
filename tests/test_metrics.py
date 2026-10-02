"""Tests unitaires des métriques qualité (§2.3) et de l'accord inter-juges (§4.4)."""

from __future__ import annotations

import pytest

from Low-Eval-Kit.metrics import (
    cohen_kappa,
    f1_macro,
    f1_par_type,
    icc21,
    kappa_est_substantiel,
    precision_at_k,
    rappel_concepts,
)


class TestF1:
    def test_f1_macro_identite(self):
        # Prédiction parfaite → F1 = 1.
        assert f1_macro([1, 0, 1], [1, 0, 1]) == pytest.approx(1.0)

    def test_f1_macro_nulle(self):
        assert f1_macro([1, 1], [0, 0]) == pytest.approx(0.0)

    def test_f1_par_type(self):
        y_vrai = ["conceptuelle", "calculatoire", "conceptuelle"]
        y_pred = ["conceptuelle", "conceptuelle", "conceptuelle"]
        par_type = f1_par_type(y_vrai, y_pred)
        # conceptuelle : TP=2, FP=1, FN=0 → F1 = 4/5 (fausse alerte pénalisée).
        assert par_type["conceptuelle"] == pytest.approx(0.8)
        assert par_type["calculatoire"] == pytest.approx(0.0)

    def test_f1_rejette_longueurs_differentes(self):
        with pytest.raises(ValueError):
            f1_macro([1, 0], [1])


class TestPrecisionAtK:
    def test_ordre_parfait(self):
        # Les segments prédits dans le même ordre que le référentiel.
        assert precision_at_k(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(1.0)

    def test_ordre_sans_effet_meme_ensemble(self):
        # P@k est un ensemble : même segments dans un autre ordre → score identique.
        assert precision_at_k(["c", "b", "a"], ["a", "b", "c"]) == pytest.approx(1.0)

    def test_segments_hors_referentiel_penalises(self):
        assert precision_at_k(["x", "y", "a"], ["a", "b", "c"]) == pytest.approx(1 / 3)

    def test_segments_reels(self):
        # Un seul segment réel : seul le premier segment prédit compte pleinement.
        assert precision_at_k(["x", "y"], ["x"]) == pytest.approx(0.5)


class TestRappelConcepts:
    def test_tous_les_concepts(self):
        assert rappel_concepts({"a", "b"}, ["a", "b", "c"]) == pytest.approx(2 / 3)

    def test_aucun_concept_attendu_rejete(self):
        # Sans référentiel, le rappel n'est pas défini : erreur explicite.
        with pytest.raises(ValueError):
            rappel_concepts({"a"}, [])


class TestKappa:
    def test_accord_parfait(self):
        assert cohen_kappa(["a", "a", "b"], ["a", "a", "b"]) == pytest.approx(1.0)

    def test_desaccord_total_etiquettes_identiques(self):
        # Un seul type partagé avec désaccord total → κ très négatif.
        k = cohen_kappa(["a", "a", "a"], ["a", "b", "b"])
        assert k < 0.5

    def test_cas_degenere_un_seul_type(self):
        # Un seul type identique des deux côtés : accord parfait par convention.
        assert cohen_kappa(["a", "a"], ["a", "a"]) == pytest.approx(1.0)

    def test_seuil_substantiel(self):
        assert kappa_est_substantiel(0.76)
        assert not kappa_est_substantiel(0.74)


class TestICC21:
    """ICC(2,1) de Shrout & Fleiss sur les notations croisées (H1, seuil 0,70)."""

    def _notes(self, accord: float) -> list[list[float]]:
        # 4 sujets × 3 juges ; « accord » calibre l'écart entre juges.
        return [
            [8.0 + accord * i, 8.2 + accord * i, 7.9 + accord * i]
            for i in range(4)
        ]

    def test_icc_fort_quand_les_juges_saccordent(self):
        # Même rangement des sujets par tous les juges → ICC élevé.
        notes = [[1.0, 1.2, 0.9], [5.0, 5.1, 4.8], [9.0, 9.2, 8.9], [3.0, 3.1, 2.9]]
        assert icc21(notes) > 0.70

    def test_icc_faible_quand_les_juges_se_contredisent(self):
        # Ordres inversés → ICC négatif ou nul.
        notes = [[1.0, 9.0, 5.0], [9.0, 1.0, 5.0], [5.0, 5.0, 5.0], [2.0, 8.0, 5.0]]
        assert icc21(notes) < 0.5

    def test_icc_rejette_matrices_incoherentes(self):
        with pytest.raises(ValueError):
            icc21([[1.0, 2.0], [1.0]])  # lignes de longueurs différentes
