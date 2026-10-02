# Guide de déploiement GitHub — Low-Eval Kit, Data-Low, Bench-Low

Guide opérationnel pour publier et maintenir les trois dépôts de
l'écosystème Low-Eval. Chaque section est autonome ; l'ordre global
reflète la logique de mise en ligne : **le kit d'abord** (codes + tests),
**puis le corpus** (données + annotation), **puis les résultats** (chiffres
verrouillés). Prérequis : Git ≥ 2.40, un compte GitHub, et — pour les
gros fichiers — Git LFS.

---

## 1. Low-Eval Kit (codes et protocole)

### 1.1 Préparation locale

```bash
cd Low-Eval-Kit
git init -b main                       # dépôt principal sur « main »
git add .
git commit -m "Low-Eval Kit v2.0.0 — alignement manuscrit (schéma v2, annexe C, 8 métadonnées)"
git tag -a v2.0.0 -m "Verrouillage des valeurs de référence (ECC=0,876, S=0,787)"
```

Le tag est **fonctionnel**, pas décoratif : `loweval.instrumentation.
code_version()` le lit pour journaliser la version du code (métadonnée 1/8,
§7.2). Toute campagne publiée doit citer un tag existant.

### 1.2 Dépôt GitHub et protections

```bash
gh repo create low-eval-kit --public --source . --push   # ou création via l'interface
git push -u origin main
git push origin v2.0.0
```

Dans **Settings → Branches**, ajouter une règle sur `main` :
« Require pull request before merging » + « Require status checks to pass »
en sélectionnant le job `tests` du workflow CI (`.github/workflows/ci.yml`,
fourni). La CI exécute : tests verrouillés, campagne dry-run bout en bout,
consolidation des scores, ingestion SQLite — sur Python 3.10 / 3.11 / 3.12.

### 1.3 Conteneur (optionnel mais recommandé)

```bash
docker build -t low-eval-kit:2.0.0 .
docker compose --profile eval up          # évaluation sèche
docker compose --profile terrain up       # protocole de terrain (tc, CPU 50 %)
docker compose --profile dashboard up     # tableau de bord sur http://localhost:8501
```

Publication d'images : créer les secrets `DOCKERHUB_USERNAME` et
`DOCKERHUB_TOKEN` (Settings → Secrets and variables → Actions), pousser
l'image taguée, et citer son empreinte (`docker inspect --format
'{{.Id}}'`) dans le MANIFEST de la campagne.

### 1.4 Secrets

Le kit n'exige aucun secret pour le mode dry-run. Pour l'inférence réelle :
`HF_TOKEN` (lecture de poids privés HF) en secret de dépôt ou
`huggingface-cli login` en local — **jamais** dans les fichiers versionnés.

---

## 2. Data-Low (corpus et annotation)

### 2.1 Préparation locale

```bash
cd Data-Low
git init -b main
git add .
git commit -m "Data-Low v2.0 — schéma 2.0 (tableau 2.6), pipeline corrigé, guide d'annotation"
git tag -a v2.0.0 -m "Schéma v2.0 verrouillé"
```

### 2.2 Les PDF scannés : Git LFS, jamais le dépôt

Les sujets d'examen sont la propriété de l'État tchadien (voir LICENSE) :
**ils ne sont pas redistribués**. Deux options :

* **Option recommandée** : héberger les PDF sur un espace d'archives
  institutionnel (serveur de laboratoire, OSF, Zenodo en accès restreint)
  et ne versionner dans Data-Low que le script de téléchargement.
* Si les PDF doivent transiter par Git : Git LFS avec quota privé —

```bash
git lfs install
echo "*.pdf filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
git add .gitattributes sujets/*.pdf
```

### 2.3 Dépôt GitHub, versionnement du corpus

```bash
gh repo create data-low --public --source . --push
```

Chaque livraison de corpus suit le MANIFEST de Data-Low : validation
`lire_jsonl` sans erreur, identifiants uniques, `arbitre`/campagne présents,
hash SHA-256 du JSONL reporté dans le registre Bench-Low. Les sorties
intermédiaires (`work/`, `processed_*/`) sont exclues par `.gitignore`.

### 2.4 Page de documentation

Activer **Settings → Pages** (branche `main`, dossier `/ (root)`) si un
`index.html` de documentation est ajouté ; sinon le README suffit.

---

## 3. Bench-Low (résultats verrouillés)

```bash
cd Bench-Low
git init -b main
git add .
git commit -m "Bench-Low — référentiel tableau 4.1, scores et Pareto régénérés par le kit v2.0.0"
git tag -a v2.0.0 -m "Valeurs verrouillées : ECC=0,876, S=0,787 (Qwen2-VL-7B)"
gh repo create bench-low --public --source . --push
```

Règles du dépôt : les fichiers de `results/` ne se modifient que par
régénération (`compute_scores.py`) ; toute divergence avec les valeurs
verrouillées s'inscrit au registre des campagnes du MANIFEST. Activer les
mêmes protections de branche que le kit.

---

## 4. Publications et cycles de version

1. **Releases GitHub** : pour chaque dépôt, `Releases → Draft new release`
   en choisissant le tag. Joindre au kit : l'archive du code et le
   `campaign.json` de la campagne de référence ; à Bench-Low : les exports
   CSV/JSON et le PDF du tableau 4.1.
2. **CI Data-Low** (à ajouter) : valider chaque JSONL poussé avec
   `lire_jsonl` — copier `.github/workflows/ci.yml` du kit en n'y gardant
   que l'appel à `ingest_data_low.py`.
3. **DOI** : lier les releases stables à Zenodo (compte GitHub connecté)
   pour obtenir un DOI citable dans le manuscrit.
4. **Synchronisation des trois dépôts** : le MANIFEST de Bench-Low cite le
   tag du kit et le hash du corpus ; le MANIFEST du kit cite le schéma
   Data-Low. Ces références se mettent à jour **ensemble** à chaque
   campagne.

---

## 5. Sécurité et bonnes pratiques

* Aucun poids de modèle, aucun PDF d'examen, aucune donnée personnelle
  d'élève dans les dépôts publics.
* `HF_TOKEN` et jetons Docker en secrets GitHub uniquement.
* Les identifiants d'annotateurs restent pseudonymisés (`expert_1`, …).
* Avant chaque publication : passage complet de la checklist annexe D
  (reprise §9 du MANIFEST du kit).
