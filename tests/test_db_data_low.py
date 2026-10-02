"""Tests de la persistance SQLite (schéma Data-Low + journal des runs)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from Low-Eval-Kit import db as base_de_donnees

EXERCICE = {
    "id": "MATH-2023-SN-001",
    "source": "test",
    "year": 2023,
    "serie": "SN",
    "discipline": "mathématiques",
    "statement": "Énoncé de test.",
    "solution_ref": "Solution de test.",
    "concepts": ["discriminant"],
}


@pytest.fixture()
def conn(tmp_path):
    connexion = base_de_donnees.init_db(tmp_path / "test.db")
    yield connexion
    connexion.close()


def test_schema_contient_tables_attendues(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"exercises", "annotations", "runs", "results",
            "double_annotations", "arbitrages"} <= tables


def test_runs_portent_metadonnees_et_vram(conn):
    # Correctif v2.0 : colonnes metadonnees (JSON §7.2) et vram_gb réelles.
    colonnes = {r[1] for r in conn.execute("PRAGMA table_info(runs)")}
    assert "metadonnees" in colonnes
    assert "vram_gb" in colonnes


def test_type_hors_taxonomie_rejete(conn):
    base_de_donnees.inserer_exercice(conn, EXERCICE)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO annotations (exercise_id, annotator, error_type) "
            "VALUES (?, ?, ?)", ("MATH-2023-SN-001", "A", "metaphysique"))
        conn.commit()


def test_run_complet_avec_mesures_reelles(conn):
    base_de_donnees.inserer_exercice(conn, EXERCICE)
    meta = {"version_code": "2.0.0", "commit": "abc1234",
            "parametres_decodage": {"temperature": 0.1}}
    run_id = base_de_donnees.ouvrir_run(
        conn, "modele-test", "terrain", graine=42, metadonnees=meta)
    base_de_donnees.inserer_resultat(conn, run_id, EXERCICE["id"], "feedback",
                                     {"f1": 1.0, "precision_at_k": 1.0,
                                      "concept_recall": 1.0, "actionable": 0.75})
    base_de_donnees.cloturer_run(conn, run_id, memoire_go=3.2,
                                 latence_ms=680.0, vram_go=1.8)

    run = conn.execute(
        "SELECT metadonnees, memory_gb, vram_gb, latency_ms "
        "FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert json.loads(run[0])["commit"] == "abc1234"
    assert run[1] == pytest.approx(3.2)    # mémoire réelle, jamais un placeholder
    assert run[2] == pytest.approx(1.8)

    agregats = base_de_donnees.resultats_agreges(conn)
    assert len(agregats) == 1
    assert agregats[0]["actionable"] == pytest.approx(0.75)
    assert agregats[0]["memory_gb"] == pytest.approx(3.2)


def test_environnement_controle(conn):
    # L'INSERT avec un environnement invalide échoue dès l'ouverture du run.
    with pytest.raises(sqlite3.IntegrityError):
        base_de_donnees.ouvrir_run(conn, "m", "mars", graine=1)
    # Et une modification ultérieure vers une valeur invalide est bloquée.
    run_id = base_de_donnees.ouvrir_run(conn, "m", "terrain", graine=1)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE runs SET environment = 'mars' WHERE id = ?", (run_id,))
        conn.commit()
