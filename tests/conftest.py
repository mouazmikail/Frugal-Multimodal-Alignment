"""Configuration partagée de la suite de tests.

Ajoute la racine du dépôt au chemin de recherche pour que les paquets
``loweval``, ``data_low`` et ``bench_low`` soient importables sans
installation préalable (``pip install -e .`` reste recommandé en usage
réel, mais la CI et les relecteurs peuvent lancer pytest directement).
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
