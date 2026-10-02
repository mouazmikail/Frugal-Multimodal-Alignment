"""Tests du parseur de feedbacks — correctif central de la version 2.0.

Avant : les métriques comparaient la production au référentiel d'or,
donnant un F1 toujours égal à 1,0. Désormais : le feedback brut du modèle
est structuré (types d'erreur, segments, concepts, marqueur « correct »)
puis comparé aux annotations humaines.
"""

from __future__ import annotations

from Low-Eval-Kit.parser import analyser_feedback


class TestTypesDetectes:
    def test_type_entre_crochets(self):
        a = analyser_feedback("[conceptuelle] incompréhension du discriminant")
        assert a.types_detectes == ["conceptuelle"]

    def test_plusieurs_types(self):
        texte = ("[conceptuelle] …\n[calculatoire] …\n[visuo-spatiale] …")
        a = analyser_feedback(texte)
        assert set(a.types_detectes) == {
            "conceptuelle", "calculatoire", "visuo-spatiale",
        }

    def test_type_accent_insensible(self):
        # Les formes accentuées ou non sont reconnues (OCR peu fiable).
        a = analyser_feedback("erreur proceduralle détectée")
        assert "procedurale" in a.types_detectes

    def test_guillemets_francais_acceptes(self):
        a = analyser_feedback("« linguistique » consigne mal comprise")
        assert "linguistique" in a.types_detectes

    def test_type_inconnu_ignore(self):
        a = analyser_feedback("[metaphysique] …")
        assert a.types_detectes == []


class TestSegments:
    def test_segment_guillemets(self):
        a = analyser_feedback('[calculatoire] « delta = 9 - 4 = 5 » est faux')
        assert "delta = 9 - 4 = 5" in a.segments

    def test_segment_crochets(self):
        a = analyser_feedback("[conceptuelle] le segment [la suite est géométrique]")
        assert any("géométrique" in s for s in a.segments)


class TestConcepts:
    def test_concepts_mentionnes_filtres(self):
        attendus = ["discriminant", "suite arithmétique"]
        a = analyser_feedback(
            "Le discriminant est mal calculé.", concepts_attendus=attendus
        )
        assert a.concepts == ["discriminant"]

    def test_aucun_concept_attendu(self):
        a = analyser_feedback("tout va bien", concepts_attendus=[])
        assert a.concepts == []


class TestCorrect:
    def test_mention_correct(self):
        a = analyser_feedback("[correct] la production est juste")
        assert a.mentionne_correct

    def test_sans_mention_correct(self):
        a = analyser_feedback("[calculatoire] erreur de signe")
        assert not a.mentionne_correct
