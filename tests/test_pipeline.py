"""Tests du pipeline complet — avec prédicteur injecté (CPU, déterministe).

Vérifie les 7 étapes (§2.6.1) sans GPU : les métriques comparent le feedback
structuré aux annotations humaines (correctif du F1 or-contre-or), et
l'export SQLite/JSON est rejoué.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from Low-Eval-Kit.config import Protocole
from Low-Eval-Kit.pipeline import ETAPES, PipelineEvaluation

# Corpus de test : deux exercices, l'un avec une erreur calculatoire annotée,
# l'autre sans annotation (production correcte).
CORPUS = [
    {
        "id": "MATH-2023-SN-001",
        "discipline": "mathématiques",
        "statement": "Résoudre x^2 - 3x + 2 = 0.",
        "solution_ref": "delta = 1 ; racines 1 et 2.",
        "concepts": ["discriminant"],
        "production": "delta = 9 - 4 = 5",
        "annotations": [
            {"error_type": "calculatoire", "span": "delta = 9 - 4 = 5",
             "concept": "discriminant"},
        ],
    },
    {
        "id": "MATH-2023-SN-002",
        "discipline": "mathématiques",
        "statement": "Démontrer que u_n = 2n+1 est arithmétique.",
        "solution_ref": "u_{n+1} - u_n = 2 constant.",
        "concepts": ["suite arithmétique"],
        "production": "u_{n+1} - u_n = 2",
        "annotations": [],
    },
]


def _predictor_cite_tout(exercice: dict) -> str:
    """Prédicteur parfait : cite toutes les annotations du référentiel."""
    lignes = [f"- [{a['error_type']}] « {a.get('span', '')} »"
              for a in exercice.get("annotations", [])]
    if not lignes:
        lignes = ["- [correct] production conforme à la solution de référence"]
    if exercice.get("concepts"):
        lignes.append("Concepts : " + ", ".join(exercice["concepts"]))
    return "\n".join(lignes)


def _predictor_aveugle(exercice: dict) -> str:
    """Prédicteur nul : ne détecte rien, jamais."""
    return "Analyse terminée. Aucune erreur détectée."


@pytest.fixture()
def protocole(tmp_path):
    chemin = tmp_path / "protocole.yaml"
    chemin.write_text(
        "seed: 42\n"
        "n_runs: 1\n"
        "generation: {max_new_tokens: 128}\n"
        "quantization: {methode: nf4}\n"
        "statistics: {seuil_kappa: 0.75}\n"
        "environments:\n"
        "  terrain:\n"
        "    label: 'terrain de test'\n"
        "    gpu: false\n"
        "    ram_gb: 32\n",
        encoding="utf-8",
    )
    return Protocole.depuis_fichier(chemin)


def test_les_sept_etapes_sont_documentees():
    assert len(ETAPES) == 7


def test_f1_parfait_quand_le_predicteur_cite_tout(protocole, tmp_path):
    pipe = PipelineEvaluation(protocole, "terrain", dossier_sortie=tmp_path)
    agrege = pipe.evaluer("modele-test", CORPUS, _predictor_cite_tout)
    # Le type et le segment de la seule annotation sont retrouvés → F1 = 1.
    assert agrege["f1"] == pytest.approx(1.0)
    assert agrege["concept_recall"] == pytest.approx(1.0)
    assert agrege["ca"] > 0.7


def test_f1_nul_avec_predicteur_aveugle(protocole, tmp_path):
    pipe = PipelineEvaluation(protocole, "terrain", dossier_sortie=tmp_path)
    agrege = pipe.evaluer("modele-test", CORPUS, _predictor_aveugle)
    # Détection d'erreur nulle : le type annoté n'est jamais cité.
    assert agrege["f1"] == pytest.approx(0.0)


def test_scores_exige_un_up_humain(protocole, tmp_path):
    pipe = PipelineEvaluation(protocole, "terrain", dossier_sortie=tmp_path)
    agrege = pipe.evaluer("modele-test", CORPUS, _predictor_cite_tout)
    sans_up = pipe.scores(agrege)
    assert "composite" not in sans_up        # pas d'UP → pas de composite
    avec_up = pipe.scores(agrege, up=0.75)
    assert avec_up["composite"] == pytest.approx(
        0.4 * avec_up["ca"] + 0.4 * 0.75 + 0.2 * avec_up["ecc"]
    )


def test_export_sqlite_et_json(protocole, tmp_path):
    pipe = PipelineEvaluation(protocole, "terrain", dossier_sortie=tmp_path)
    corpus = pipe.charger_corpus(_ecrire_corpus(tmp_path))
    agrege = pipe.evaluer("modele-test", corpus, _predictor_cite_tout)
    resultat = pipe.scores(agrege, up=0.75)

    chemin_db = tmp_path / "campagne.db"
    sortie = pipe.exporter(resultat, chemin_db,
                           metadonnees={"version_code": "test"})

    # JSON : clés essentielles présentes, sans le détail des lignes.
    document = json.loads(sortie.read_text(encoding="utf-8"))
    for cle in ("model", "ca", "up", "ecc", "composite", "latence_ms"):
        assert cle in document
    assert "lignes" not in document

    # SQLite : run journalisé avec métadonnées + résultats par exercice.
    conn = sqlite3.connect(chemin_db)
    try:
        run = conn.execute("SELECT metadonnees, memory_gb FROM runs").fetchone()
        assert json.loads(run[0])["version_code"] == "test"
        n = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        assert n == len(CORPUS)
    finally:
        conn.close()


def _ecrire_corpus(tmp_path) -> str:
    chemin = tmp_path / "corpus.jsonl"
    with chemin.open("w", encoding="utf-8") as flux:
        for ex in CORPUS:
            flux.write(json.dumps(ex, ensure_ascii=False) + "\n")
    return str(chemin)
