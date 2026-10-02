"""Tests du pipeline Data-Low (étapes 1 à 5 du manuscrit, §2.4)."""

from __future__ import annotations

import pytest

from data_low.annotate import completer_annotation_exercice, controler_annotations
from data_low.qualite import N_DOUBLE_ANNOTATION, conduire_double_annotation
from data_low.segment import numeroter_exercices, segmenter_sujet
from data_low.taxonomie import (
    KAPPA_PILOTE,
    SEUIL_KAPPA,
    TYPES_ERREUR,
    types_a_renforcer,
)
from data_low.validate import exporter_jsonl, valider_corpus, valider_exercice
from Low-Eval-Kit.errors import DonneeInvalideError


class TestTaxonomie:
    def test_cinq_types_canoniques(self):
        assert TYPES_ERREUR == (
            "conceptuelle", "procedurale", "visuo-spatiale",
            "linguistique", "calculatoire",
        )

    def test_kappas_pilote_sous_seuil_uniquement_calculatoire(self):
        # Tableau 2.4 : seul le type calculatoire (0,74) est sous le seuil 0,75.
        assert types_a_renforcer(KAPPA_PILOTE) == ["calculatoire"]
        assert KAPPA_PILOTE["conceptuelle"] == 0.88 > SEUIL_KAPPA


class TestValidation:
    def test_exercice_valide(self):
        ex = {
            "id": "MATH-2023-SN-001", "discipline": "mathématiques",
            "statement": "Énoncé.", "solution_ref": "Solution.",
            "concepts": ["discriminant"],
        }
        assert valider_exercice(ex) == []

    def test_exercice_sans_id_canonique(self):
        ex = {"id": "exercice 1", "discipline": "mathématiques",
              "statement": "É.", "solution_ref": "S.", "concepts": ["c"]}
        assert any("identifiant" in p for p in valider_exercice(ex))

    def test_doublon_id_rejete(self):
        ex = {"id": "MATH-2023-SN-001", "discipline": "mathématiques",
              "statement": "É.", "solution_ref": "S.", "concepts": ["c"]}
        with pytest.raises(DonneeInvalideError):
            valider_corpus([ex, dict(ex)])


class TestSegmentation:
    SUJET = (
        "1. Résoudre x^2 - 3x + 2 = 0. (4 points)\n"
        "2. Démontrer que u_n est arithmétique. (3 points)\n"
        "3. Calculer BC dans le triangle ABC. (3 points)"
    )

    def test_trois_exercices_detectes(self):
        segments = segmenter_sujet(self.SUJET)
        assert len(segments) == 3
        assert [s.numero for s in segments] == [1, 2, 3]

    def test_baremes_extraits(self):
        segments = segmenter_sujet(self.SUJET)
        assert [s.bareme for s in segments] == [4.0, 3.0, 3.0]

    def test_numerotation_canonique(self):
        segments = segmenter_sujet(self.SUJET)
        exercices = numeroter_exercices(segments, "mathématiques", 2023, "SN")
        assert [e["id"] for e in exercices] == [
            "MATH-2023-SN-001", "MATH-2023-SN-002", "MATH-2023-SN-003",
        ]

    def test_sans_marqueur_conservé_entier(self):
        segments = segmenter_sujet("Texte continu sans aucun numéro d'exercice.")
        assert len(segments) == 1
        assert segments[0].a_verifier


class TestAnnotation:
    def test_completer_solution_et_concepts(self):
        ex = {"id": "MATH-2023-SN-001"}
        complete = completer_annotation_exercice(ex, "Solution rédigée.",
                                                 ["discriminant"])
        assert complete["solution_ref"] == "Solution rédigée."
        assert complete["concepts"] == ["discriminant"]
        assert "solution_ref" not in ex  # l'entrée n'est pas mutée

    def test_solution_vide_rejetee(self):
        with pytest.raises(DonneeInvalideError):
            completer_annotation_exercice({"id": "X"}, "   ", ["c"])

    def test_span_absent_signale(self):
        annotations = [{"error_type": "calculatoire", "span": "delta = 9 - 4 = 5"}]
        problemes = controler_annotations(annotations, "production sans ce texte")
        assert problemes  # le span n'existe pas dans la production

    def test_span_visuel_sans_verification_textuelle(self):
        annotations = [{"error_type": "visuo-spatiale", "span": "figure 2, zone A"}]
        assert controler_annotations(annotations, "") == []


class TestQualite:
    def _paires(self, n_accord: int, n_desaccord: int):
        return [
            {"exercise_id": f"EX-{i:03d}", "error_type": "calculatoire",
             "type_a": "calculatoire", "type_b": "calculatoire"}
            for i in range(n_accord)
        ] + [
            {"exercise_id": f"DX-{i:03d}", "error_type": "calculatoire",
             "type_a": "calculatoire", "type_b": "conceptuelle"}
            for i in range(n_desaccord)
        ]

    def test_accord_parfait(self):
        rapport = conduire_double_annotation(self._paires(10, 0))
        assert rapport.accord_brut == 1.0
        assert rapport.conforme()

    def test_seuil_depassement_rejete(self):
        with pytest.raises(ValueError):
            conduire_double_annotation(self._paires(N_DOUBLE_ANNOTATION + 1, 0))


class TestExportJSONL:
    def test_export_jsonl(self, tmp_path):
        exercices = [{
            "id": "MATH-2023-SN-001", "discipline": "mathématiques",
            "statement": "É.", "solution_ref": "S.", "concepts": ["c"],
        }]
        chemin = tmp_path / "corpus.jsonl"
        assert exporter_jsonl(exercices, chemin) == 1
        assert chemin.read_text(encoding="utf-8").count("\n") == 1
