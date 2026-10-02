"""Tests des exports (CSV, JSON, HTML) et des fiches de supervision."""

from __future__ import annotations

import json

import pytest

from Low-Eval-Kit.report import ecrire_csv, ecrire_fiches, ecrire_html, ecrire_json
from Low-Eval-Kit.scores import ResultatModele


@pytest.fixture()
def resultats():
    return [
        ResultatModele("Qwen2-VL-7B", ca=0.82, up=0.71,
                       memoire_go=4.3, latence_ms=1420.0),
        ResultatModele("MiniCPM-V-2.8B", ca=0.62, up=0.58,
                       memoire_go=1.8, latence_ms=680.0),
    ]


def test_ecrire_csv(resultats, tmp_path):
    chemin = ecrire_csv(resultats, tmp_path / "t41.csv")
    lignes = chemin.read_text(encoding="utf-8").strip().splitlines()
    assert len(lignes) == 3            # en-tête + 2 modèles
    assert "Qwen2-VL-7B" in lignes[1]


def test_ecrire_json_avec_sensibilite(resultats, tmp_path):
    chemin = ecrire_json(resultats, tmp_path / "r.json", avec_sensibilite=True)
    doc = json.loads(chemin.read_text(encoding="utf-8"))
    assert doc["sensibilite"]["nb_combinaisons"] == 45
    assert "Qwen2-VL-7B" in doc["non_domines"]


def test_ecrire_html_surligne_le_front(resultats, tmp_path):
    chemin = ecrire_html(resultats, tmp_path / "r.html")
    html = chemin.read_text(encoding="utf-8")
    assert "Qwen2-VL-7B" in html
    assert "★" in html                  # marqueur du front de Pareto


def test_ecrire_fiches(resultats, tmp_path):
    # La fonction retourne la liste des fiches écrites (une par modèle).
    fiches = ecrire_fiches(resultats, tmp_path / "fiches")
    assert len(fiches) == 2
    assert any("Qwen2-VL-7B" in f.read_text(encoding="utf-8") for f in fiches)
