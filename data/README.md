# DATA-LOW — corpus de productions d'élèves STEM contextualisées

Corpus construit pour l'évaluation de modèles vision-langage légers en
contextes éducatifs contraints (chapitre 2, section 2.4 du manuscrit).

## Contenu

| Élément | Description |
|---|---|
| Sources | Sujets d'examens et concours francophones (contexte tchadien), numérisés et contrôlés |
| Unité | Exercice : identifiant unique, source, année, série, discipline, énoncé, images, solution de référence, concepts attendus |
| Annotations | Erreurs d'élèves selon la taxonomie STEM à cinq types, double annotation de 150 productions |

## Taxonomie des erreurs (tableau 2.4 du manuscrit)

| Type | Part indicative dans l'échantillon initial |
|---|---:|
| Conceptuelle | 25 % |
| Procédurale | 30 % |
| Visuo-spatiale | 20 % |
| Linguistique | 15 % |
| Calculatoire | 10 % |

## Accord inter-annotateur (tableau 2.5 et figure 2.3)

Double annotation, n = 150, κ de Cohen par type d'erreur :

| Type d'erreur | κ |
|---|---:|
| Calculatoire | 0,88 |
| Conceptuelle | 0,81 |
| Procédurale | 0,79 |
| Linguistique | 0,76 |
| Visuo-spatiale | 0,74 (sous le seuil substantiel de 0,75) |

## Fichiers

- `schema.sql` — schéma SQLite complet (annexe B du manuscrit) ;
- `sample/exercises.sample.jsonl` — deux exercices d'exemple au format JSONL ;
- `reference_results.csv` — mesures CA/UP/latence/mémoire du tableau 4.1,
  permettant de reproduire les scores composites sans réexécuter les modèles.

## Chargement

```python
from loweval import db

conn = db.init_db("data_low.sqlite")
n = db.load_jsonl(conn, "data/sample/exercises.sample.jsonl")
print(f"{n} exercices chargés")
```

## Éthique et limites (sections 2.4.4 et 2.8)

Corpus centré sur le contexte tchadien : la généralisation externe exige une
extension à d'autres pays francophones. Les productions sont anonymisées ;
aucune donnée personnelle d'élève n'est conservée. Le corpus brut n'est pas
versionné dans ce dépôt (voir `.gitignore`) : déposer `data/raw/` séparément
et générer la base avec `schema.sql`.
