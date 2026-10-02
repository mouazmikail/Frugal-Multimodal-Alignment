"""Tests de l'instrumentation : métadonnées §7.2, version, moniteur."""

from __future__ import annotations

import time

from Low-Eval-Kit.instrumentation import (
    MetadonneesExecution,
    construire_metadonnees,
    infos_gpu,
    memoire_totale_go,
)
from Low-Eval-Kit.monitoring import MoniteurRessources
from Low-Eval-Kit.version import __version__, get_version


def test_huit_metadonnees_presentes():
    meta = MetadonneesExecution()
    d = meta.en_dict()
    # Les huit familles de la section 7.2.
    for cle in ("version_code", "commit",                 # 1. code
                "revision_poids",                         # 2. poids
                "parametres_decodage",                    # 3. décodage
                "prompt_id", "prompt_complet",            # 4. prompt
                "quantification",                         # 5. quantification
                "processeur", "ram_totale_go",            # 6. matériel
                "nb_executions", "nb_echauffements",      # 7. exécutions
                "politique_cache"):                       # 8. cache
        assert cle in d, f"métadonnée manquante : {cle}"


def test_construire_metadonnees_prefabrique():
    meta = construire_metadonnees(
        modele="test/model",
        parametres_decodage={"temperature": 0.1},
        prompt_id="analyse_formative.v1.2",
        prompt_complet="prompt complet…",
        nb_executions=5,
    )
    assert meta.modele == "test/model"
    assert meta.nb_executions == 5
    assert meta.version_code == get_version()


def test_gpu_detecte_ou_none():
    # CPU pur : infos_gpu retourne (None, None) sans lever d'erreur.
    nom, _pilote = infos_gpu()
    assert nom is None or isinstance(nom, str)


def test_memoire_totale_positive():
    assert memoire_totale_go() is None or memoire_totale_go() > 0


def test_version_semver():
    parties = __version__.split(".")
    assert len(parties) == 3 and all(p.isdigit() for p in parties)


def test_moniteur_mesure_la_duree():
    with MoniteurRessources(intervalle_s=0.02) as moniteur:
        time.sleep(0.1)
    assert moniteur.duree_ms >= 100.0
    assert moniteur.pic_memoire_go > 0.0   # le processus courant consomme
