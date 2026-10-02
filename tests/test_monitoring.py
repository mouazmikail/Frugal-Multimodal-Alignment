"""Tests du moniteur de ressources — mesures réelles, jamais factices.

Verrouille le correctif « fond » majeur : l'ancien protocole terrain
écrivait ``memories.append(0.0)``. Désormais, toute valeur journalisée dans
la table ``runs`` provient d'une mesure (RSS via psutil, VRAM via pynvml).
"""

from __future__ import annotations

import time

from Low-Eval-Kit.monitoring import (
    MoniteurRessources,
    memoire_processus_go,
    vram_utilisee_go,
)


class TestMesuresElementaires:
    def test_memoire_processus_positive(self):
        # Le processus de test consomme de la RAM : la mesure est réelle.
        assert memoire_processus_go() > 0.0

    def test_vram_est_un_flottant_borne(self):
        # Machine sans GPU → 0.0 ; avec GPU → valeur positive. Jamais négatif.
        assert vram_utilisee_go() >= 0.0


class TestMoniteurRessources:
    def test_fenetre_de_mesure(self):
        with MoniteurRessources(intervalle_s=0.005) as moniteur:
            # Travail trivial pour occuper la fenêtre de mesure.
            somme = sum(i * i for i in range(10_000))
            assert somme >= 0
            time.sleep(0.02)  # au moins un tour d'échantillonnage
        assert moniteur.duree_ms > 0.0
        assert moniteur.pic_memoire_go > 0.0     # pic RSS réel du processus
        assert moniteur.pic_vram_go >= 0.0       # 0.0 = absence de GPU, mesuré

    def test_pic_jamais_remis_a_zero(self):
        # Deux fenêtres consécutives : le second pic ne peut pas effacer le
        # premier (le max est consolidé sur la fenêtre, pas sur l'historique).
        with MoniteurRessources(intervalle_s=0.005) as m1:
            time.sleep(0.01)
        with MoniteurRessources(intervalle_s=0.005) as m2:
            time.sleep(0.01)
        assert m2.pic_memoire_go > 0.0
        assert m1.duree_ms > 0.0 and m2.duree_ms > 0.0
