#!/usr/bin/env python3
"""Script CLI d'évaluation complète d'un modèle (les 7 étapes du chapitre 2).

Usage (GPU, modèle réel) :

    python scripts/run_evaluation.py --modele Qwen2-VL-7B \
        --environnement local --corpus data_low/corpus.jsonl --up 0.71

Usage (démonstration CPU, sans dépendance lourde) :

    python scripts/run_evaluation.py --modele MiniCPM-V-2.8B \
        --environnement terrain --corpus data_low/corpus.jsonl \
        --up 0.58 --predicteur simule

Les sept étapes orchestées (section 2.6.1 du manuscrit) :

1. chargement du corpus Data-Low (JSONL validé) ;
2. construction du prompt versionné (prompt_id « analyse_formative.v1.2 ») ;
3. chargement du modèle quantifié NF4 (ou prédicteur injecté) ;
4. inférence sur le corpus, sauvegarde des feedbacks en JSON ;
5. calcul des métriques CA (F1, P@k, BERTScore optionnel, rappel concepts) ;
6. insertion des mesures dans SQLite (journal des runs, métadonnées §7.2) ;
7. export JSON + rapports (CSV, HTML, fiches de supervision).

Correction majeure par rapport à la version 1.0 : l'UP est désormais *toujours*
fourni explicitement (annotation humaine ou grille) via ``--up`` ; le script
refuse de publier un score composite sans UP plutôt que d'en inventer un.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Le dépôt n'est pas nécessairement « installé » : on ajoute sa racine au
# chemin de recherche pour que les imports loweval/data_low fonctionnent
# quel que soit le répertoire de lancement.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Low-Eval-Kit.config import PanelModeles, Protocole
from Low-Eval-Kit.instrumentation import construire_metadonnees
from Low-Eval-Kit.logging_utils import configurer_journal, get_logger
from Low-Eval-Kit.pipeline import PipelineEvaluation
from Low-Eval-Kit.prompts import PROMPT_ID, construire_prompt_analyse

log = get_logger("scripts.evaluation")


# ---------------------------------------------------------------------------
# Prédicteur de démonstration (CPU) — déterministe, sans modèle ni GPU.
# Il reproduit un feedback « plausible » à partir des annotations de
# référence de l'exercice, ce qui permet de tester toute la chaîne de
# scoring sur n'importe quelle machine (y compris la CI GitHub Actions).
# ---------------------------------------------------------------------------

def _construire_predicteur_simule(taux_rappel: float = 0.8):
    """Retourne un Predictor qui cite une partie des erreurs du référentiel.

    Le taux de rappel fixe la proportion d'annotations de référence citées,
    en suivant l'ordre du référentiel (déterministe grâce à la graine) :
    ainsi le F1 de démonstration est stable d'une exécution à l'autre.
    """
    def predictor(exercice: dict) -> str:
        annotations = exercice.get("annotations", [])
        retenues = annotations[: max(1, int(len(annotations) * taux_rappel))]
        lignes = [
            f"- [{a['error_type']}] « {a.get('span', 'segment non localisé')} »"
            for a in retenues
        ]
        if not lignes:
            lignes = ["- [correct] la production ne présente pas d'erreur détectée"]
        concepts = exercice.get("concepts", [])
        if concepts:
            lignes.append("Concepts mobilisés : " + ", ".join(concepts))
        return "\n".join(lignes)
    return predictor


def _construire_predicteur_hf(modele, processeur, generation: dict):
    """Prédicteur réel : encapsule un modèle Hugging Face chargé en mémoire.

    Le prompt est construit avec le gabarit versionné ; seule la chaîne de
    caractères est transmise au modèle (les images, présentes, seraient
    encodées ici pour les VLM — voir la documentation de chaque processeur).
    """
    def predictor(exercice: dict) -> str:
        # Prompt complet : énoncé + corrigé + production de l'élève,
        # gabarit versionné « analyse_formative.v1.2 ».
        prompt: str = construire_prompt_analyse(exercice)
        entrees = processeur(text=prompt, return_tensors="pt")
        sortie = modele.generate(**entrees, **generation)
        return processeur.decode(sortie[0], skip_special_tokens=True)
    return predictor


def analyser_arguments() -> argparse.Namespace:
    """Définit et parse les arguments de la ligne de commande."""
    parseur = argparse.ArgumentParser(
        description="Évaluation Low-Eval d'un modèle (7 étapes, chapitre 2).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parseur.add_argument("--modele", required=True,
                         help="Nom du modèle dans configs/models.yaml")
    parseur.add_argument("--environnement", default="local",
                         choices=("cloud", "local", "terrain"),
                         help="Environnement d'évaluation (tableau 2.3)")
    parseur.add_argument("--corpus", default="data_low/corpus.jsonl",
                         help="Chemin du corpus Data-Low (JSONL validé)")
    parseur.add_argument("--up", type=float, default=None,
                         help="Score UP (jugement humain indépendant) — requis "
                              "pour le score composite")
    parseur.add_argument("--predicteur", choices=("auto", "simule"),
                         default="auto",
                         help="auto = modèle HF réel ; simule = démonstration CPU")
    parseur.add_argument("--bertscore", action="store_true",
                         help="Activer le calcul BERTScore (lourd, GPU conseillé)")
    parseur.add_argument("--config-protocole", default="configs/protocol.yaml")
    parseur.add_argument("--config-modeles", default="configs/models.yaml")
    parseur.add_argument("--base", default="runs/loweval.db",
                         help="Chemin de la base SQLite journalisant les runs")
    parseur.add_argument("--sortie", default="runs",
                         help="Dossier des exports JSON et rapports")
    return parseur.parse_args()


def main() -> int:
    """Point d'entrée : orchestre les 7 étapes et retourne un code de sortie."""
    args = analyser_arguments()
    configurer_journal(logging.INFO)

    # -- Étape 0 (amont) : configuration du protocole et du panel ------------
    protocole = Protocole.depuis_fichier(args.config_protocole)
    panel = PanelModeles.depuis_fichier(args.config_modeles)
    fiche = panel.trouver(args.modele)

    # -- Validation précoce : sans UP, pas de composite publié ---------------
    if args.up is None:
        log.warning("Aucun UP fourni (--up absent) : CA, ECC et métriques "
                    "seront calculés, mais le score composite restera absent.")

    # BERTScore (optionnel) : la fonction de similarité est injectée dans
    # le pipeline ; sans elle, la composante est exclue de la CA plutôt
    # que d'être remplacée par une valeur inventée.
    fonction_bertscore = None
    if args.bertscore:
        from Low-Eval-Kit.metrics import bertscore_f1

        def fonction_bertscore(prediction: str, reference: str) -> float:
            return bertscore_f1([prediction], [reference])

    pipeline = PipelineEvaluation(protocole, args.environnement,
                                  dossier_sortie=args.sortie,
                                  fonction_bertscore=fonction_bertscore)

    # -- Étape 1 : chargement du corpus ---------------------------------------
    corpus = pipeline.charger_corpus(args.corpus)

    # -- Étape 3 : chargement du modèle (ou prédicteur injecté) ---------------
    if args.predicteur == "simule":
        log.info("Prédicteur de démonstration CPU (aucun modèle chargé).")
        predictor = _construire_predicteur_simule()
        hf_id = f"simule://{fiche.nom}"
    else:
        from Low-Eval-Kit.model_loader import charger_modele
        quantification = protocole.quantification
        modele, processeur = charger_modele(
            fiche.hf_id,
            type_modele=fiche.type,
            dtype_calcul=str(quantification.get("dtype_calcul", "float16")),
            quantifier=bool(quantification.get("methode") != "aucune"),
        )
        predictor = _construire_predicteur_hf(modele, processeur,
                                              protocole.generation)
        hf_id = fiche.hf_id

    # -- Étapes 2, 4 et 5 : prompts, inférence, métriques ---------------------
    agrege = pipeline.evaluer(fiche.nom, corpus, predictor)

    # -- Étape 6 (scores composites) -------------------------------------------
    resultat = pipeline.scores(agrege, up=args.up)
    log.info("CA=%.3f | UP=%s | ECC=%.3f | composite=%s",
             resultat["ca"], args.up, resultat["ecc"],
             f"{resultat['composite']:.3f}" if "composite" in resultat else "absent")

    # -- Métadonnées de traçabilité (section 7.2) -------------------------------
    # Les huit métadonnées (code, poids, décodage, prompt, quantification,
    # matériel, exécutions, cache) sont détectées automatiquement ; seules
    # les valeurs propres à la campagne sont passées explicitement.
    # Le prompt complet journalisé est celui du premier exercice (tous
    # partagent le même gabarit, seules les variables changent).
    prompt_complet = (construire_prompt_analyse(corpus[0])
                      if corpus else "")
    metadonnees = construire_metadonnees(
        modele=hf_id,
        parametres_decodage=protocole.generation,
        prompt_id=PROMPT_ID,
        prompt_complet=prompt_complet,
        quantification=str(protocole.quantification.get("methode", "nf4")),
        nb_executions=protocole.nb_repetitions,
        nb_echauffements=1,
    ).en_dict()

    # -- Étape 7 : journalisation SQLite + export JSON --------------------------
    pipeline.exporter(resultat, args.base, metadonnees=metadonnees)
    print(json.dumps({k: v for k, v in resultat.items() if k != "lignes"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
