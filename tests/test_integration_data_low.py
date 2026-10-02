"""Tests d'intégration Data-Low — schéma SQL, ingestion réelle, insertion tolérante.

Verrouille les correctifs « fond » de la version 2.0 :

* le miroir Python du schéma (``data_low.schema``) reste synchronisé avec
  le SQL (taxonomie, environnements, colonnes v2.0) ;
* ``charger_jsonl`` accepte un corpus en attente d'annotation (mode
  tolérant) et refuse les doublons dans tous les modes ;
* l'ingestion d'un export brut tchadien produit des identifiants
  canoniques et conserve la traçabilité (``id_source``).
"""

from __future__ import annotations

import json

import pytest

from data_low import schema
from data_low.ingest import collecter_sources, corpus_valide
from Low-Eval-Kit import db as base_de_donnees
from Low-Eval-Kit.errors import DonneeInvalideError

EXERCICE_MINIMAL = {
    "id": "MATH-2023-SN-001",
    "discipline": "mathématiques",
    "statement": "Énoncé.",
    "solution_ref": "Solution.",
    "concepts": ["discriminant"],
}


class TestCoherenceSchema:
    def test_miroir_python_et_sql_synchronises(self):
        assert schema.verifier_coherence_avec_sql() == []

    def test_colonnes_v2_presentes_dans_sql(self):
        sql = schema.lire_schema_sql()
        assert "metadonnees" in sql and "vram_gb" in sql

    def test_tables_attendues(self):
        for table in ("exercises", "annotations", "runs", "results",
                      "double_annotations", "arbitrages"):
            assert table in schema.TABLES


class TestChargerJsonlTolerant:
    def _ecrire(self, tmp_path, exercices):
        chemin = tmp_path / "corpus.jsonl"
        chemin.write_text(
            "".join(json.dumps(ex, ensure_ascii=False) + "\n"
                    for ex in exercices),
            encoding="utf-8",
        )
        return chemin

    def test_mode_tolerant_insere_sans_solution(self, tmp_path):
        ex = dict(EXERCICE_MINIMAL, solution_ref="", concepts=[])
        chemin = self._ecrire(tmp_path, [ex])
        conn = base_de_donnees.init_db(tmp_path / "t.db")
        try:
            n = base_de_donnees.charger_jsonl(conn, chemin, strict=False)
            assert n == 1
        finally:
            conn.close()

    def test_mode_strict_refuse(self, tmp_path):
        ex = dict(EXERCICE_MINIMAL, solution_ref="")
        chemin = self._ecrire(tmp_path, [ex])
        conn = base_de_donnees.init_db(tmp_path / "s.db")
        try:
            with pytest.raises(DonneeInvalideError):
                base_de_donnees.charger_jsonl(conn, chemin, strict=True)
        finally:
            conn.close()

    def test_doublon_rejete_dans_les_deux_modes(self, tmp_path):
        chemin = self._ecrire(tmp_path, [EXERCICE_MINIMAL, dict(EXERCICE_MINIMAL)])
        for strict in (True, False):
            conn = base_de_donnees.init_db(tmp_path / f"d{strict}.db")
            try:
                with pytest.raises(DonneeInvalideError):
                    base_de_donnees.charger_jsonl(conn, chemin, strict=strict)
            finally:
                conn.close()


class TestIngestionTchadienne:
    EXPORT_BRUT = ({
        "id": "TCD_S_1990_S1_E2",
        "year": 1990,
        "session": "S1",
        "exercise_num": 2,
        "statement_text": "Résoudre x^2 - 3x + 2 = 0.",
        "statement_latex": "x^2 - 3x + 2 = 0",
        "domain": "Algèbre",
        "subthemes": ["équation du second degré"],
        "tags": ["second degré"],
        "annotators": [], "reviewed": False, "notes": "",
    })

    def test_identifiants_canonises_et_tracabilite(self, tmp_path):
        (tmp_path / "dataset_all_exercises_C.json").write_text(
            json.dumps(self.EXPORT_BRUT, ensure_ascii=False), encoding="utf-8")
        exercices, rapport = collecter_sources(
            tmp_path, "mathématiques", 2023, "SN")
        assert rapport.total == 1
        assert exercices[0]["id"] == "MATH-1990-C-001"     # motif canonique
        assert exercices[0]["id_source"] == "TCD_S_1990_S1_E2"
        assert exercices[0]["serie"] == "C"                # série devinée
        assert exercices[0]["session"] == "S1"             # session préservée
        assert exercices[0]["statement"].startswith("Résoudre")
        assert "équation du second degré" in exercices[0]["concepts"]
        assert not exercices[0]["ocr_a_relire"]            # source structurée
        assert corpus_valide(exercices) == exercices
