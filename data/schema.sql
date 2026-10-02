-- =============================================================================
-- DATA-LOW — schéma de données (annexe B du manuscrit)
-- Corpus de productions d'élèves STEM contextualisées + journal Low-Eval Kit
-- =============================================================================
PRAGMA foreign_keys = ON;

-- Exercices collectés (section 2.5 : un identifiant unique par exercice)
CREATE TABLE IF NOT EXISTS exercises (
    id            TEXT PRIMARY KEY,        -- ex. « MATH-2023-SN-012 »
    source        TEXT NOT NULL,           -- examen / manuel / concours
    year          INTEGER,
    serie         TEXT,
    discipline    TEXT NOT NULL,           -- mathématiques, physique, SNT…
    statement     TEXT NOT NULL,           -- énoncé (OCR contrôlé)
    images        TEXT,                    -- chemins des images associées (JSON)
    solution_ref  TEXT NOT NULL,           -- solution de référence
    concepts      TEXT NOT NULL,           -- concepts STEM attendus (JSON)
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Annotations d'erreurs (taxonomie du tableau 2.4 ; double annotation n = 150)
CREATE TABLE IF NOT EXISTS annotations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id   TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    annotator     TEXT NOT NULL,
    error_type    TEXT NOT NULL CHECK (error_type IN
                  ('conceptuelle', 'procedurale', 'visuo-spatiale',
                   'linguistique', 'calculatoire')),
    span          TEXT,                    -- segment textuel ou visuel localisé
    concept       TEXT,
    rationale     TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (exercise_id, annotator, error_type, span)
);

-- Journal des exécutions (reproductibilité : versions, graines, mesures)
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model         TEXT NOT NULL,
    environment   TEXT NOT NULL CHECK (environment IN ('cloud', 'local', 'terrain')),
    quantization  TEXT NOT NULL DEFAULT 'nf4',
    seed          INTEGER NOT NULL,
    started_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    memory_gb     REAL,                    -- pic mesuré (psutil)
    latency_ms    REAL,
    energy_kwh    REAL                     -- estimation CodeCarbon
);

-- Résultats par exercice (métriques CA et UP du chapitre 2)
CREATE TABLE IF NOT EXISTS results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    exercise_id    TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    prediction     TEXT,
    f1             REAL,                   -- détection d'erreur
    precision_at_k REAL,                   -- localisation
    bertscore_f1   REAL,                   -- diagnostic causal (contrôle humain requis)
    concept_recall REAL,                   -- couverture des concepts
    actionable     INTEGER,                -- actionnabilité (0/1, jugement humain)
    clarity        REAL,                   -- clarté (échelle humaine)
    readability    REAL,                   -- lisibilité (écart à la cible)
    adaptability   REAL                    -- adaptabilité au profil
);

CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_model_env ON runs(model, environment);
