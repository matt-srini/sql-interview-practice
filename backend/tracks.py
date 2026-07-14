"""
Track registry — single authoritative source for all track metadata.

Adding a new track is:
  1. An entry in TRACKS (here) with its catalog module, content dir, and rules.
  2. The catalog loader module (e.g. data_engineering_questions.py).
  3. The content directory (e.g. content/data_engineering_questions/).
  4. A matching entry in frontend/src/trackRegistry.js.

After that, unlock logic, mock routing, insights, sample, and content
validation all pick it up automatically. No other file should hardcode
the track list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import data_engineering_questions
import data_modeling_questions
import experimentation_questions
import ml_fundamentals_questions
import pandas_questions
import product_sense_questions
import python_questions
import pyspark_questions
import questions as sql_questions
import statistics_questions

BACKEND_ROOT = Path(__file__).resolve().parent


@dataclass
class TrackConfig:
    """All per-track metadata in one place."""

    slug: str
    """URL/API slug, e.g. 'pandas'.  Matches :topic route param."""

    db_topic: str
    """Topic string stored in user_progress / submissions tables.
    Equals slug for all tracks."""

    catalog_module: Any
    """Module exposing get_questions_by_difficulty(), get_mock_questions_by_difficulty(),
    get_public_question(), etc."""

    label: str
    """Human-readable display name, e.g. 'Pandas'."""

    eval_kind: str
    """How submissions are evaluated.
    'sql' | 'python' | 'pandas' | 'mcq' | 'mixed'"""

    unlock_profile: str
    """Which free-tier threshold table to use.
    'code'  → SQL/Python/Pandas thresholds (requires writing code)
    'mcq'   → PySpark/MCQ thresholds (higher, because MCQ is lower-effort)"""

    content_dir: Path
    """Absolute path to the questions directory for this track."""

    concept_blocklist: set[str]
    """Lowercase concept strings that are too API/syntax-level (validator rejects them)."""

    hint_rules: dict[str, tuple[int, int]]
    """Per-difficulty (min, max) hint count rules, e.g. {'easy': (2, 2), ...}"""

    first_hint_leak_patterns: tuple[re.Pattern, ...]
    """Regex patterns that, if matched in the first hint, flag it as too implementation-specific."""

    in_mixed_mock: bool
    """Whether this track is included in the 'mixed' mock pool."""

    mixed_subtype: bool = False
    """True only for Statistics (Phase D): the question payload's 'subtype' field
    determines whether to render MCQ or code editor per question."""


TRACKS: tuple[TrackConfig, ...] = (
    TrackConfig(
        slug="sql",
        db_topic="sql",
        catalog_module=sql_questions,
        label="SQL",
        eval_kind="sql",
        unlock_profile="code",
        content_dir=BACKEND_ROOT / "content" / "questions",
        concept_blocklist={
            "select",
            "where",
            "order by",
            "group by",
            "join",
            "inner join",
            "left join",
            "right join",
            "full outer join",
            "having",
            "count",
            "sum",
            "avg",
            "average",
            "min",
            "max",
            "case when",
            "row number",
            "row_number",
            "rank",
            "dense rank",
            "dense_rank",
            "lag",
            "lead",
            "cte introduction",
            "named temporary result set",
            "with clause syntax",
        },
        hint_rules={"easy": (2, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bwhere\b", re.IGNORECASE),
            re.compile(r"\bgroup by\b", re.IGNORECASE),
            re.compile(r"\border by\b", re.IGNORECASE),
            re.compile(r"\bjoin\b", re.IGNORECASE),
            re.compile(r"\bhaving\b", re.IGNORECASE),
            re.compile(r"\bdistinct\b", re.IGNORECASE),
            re.compile(r"\b(count|max|min|avg|sum)\s*\(", re.IGNORECASE),
            re.compile(r"\b(row_number|dense_rank|rank|lag|lead)\b", re.IGNORECASE),
        ),
        in_mixed_mock=True,
    ),
    TrackConfig(
        slug="python",
        db_topic="python",
        catalog_module=python_questions,
        label="Python",
        eval_kind="python",
        unlock_profile="code",
        content_dir=BACKEND_ROOT / "content" / "python_questions",
        concept_blocklist={
            # Mechanic names / syntactic constructs (from docs/concept-taxonomy.md § Python blocklist)
            "dict",
            "dictionary",
            "set",
            "heapq",
            "bisect",
            "for loop",
            "while loop",
            "if/else",
            "conditional",
            "function",
            "def",
            "array",
            "string",           # exact "string" alone; "string manipulation" is fine
            "tuple",
            "lambda",
            "sort",
            "sorted",
            "iteration",
            "sorting",
        },
        hint_rules={"easy": (2, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bdictionary\b", re.IGNORECASE),
            re.compile(r"\bdict\b", re.IGNORECASE),
            re.compile(r"\bset\b", re.IGNORECASE),
            re.compile(r"\bdeque\b", re.IGNORECASE),
            re.compile(r"\bheap(q)?\b", re.IGNORECASE),
            re.compile(r"\bstack\b", re.IGNORECASE),
            re.compile(r"\bqueue\b", re.IGNORECASE),
            re.compile(r"\[::?-?1\]"),
        ),
        in_mixed_mock=True,
    ),
    TrackConfig(
        slug="pandas",
        db_topic="pandas",
        catalog_module=pandas_questions,
        label="Pandas",
        eval_kind="pandas",
        unlock_profile="code",
        content_dir=BACKEND_ROOT / "content" / "pandas_questions",
        concept_blocklist={
            "groupby",
            "merge",
            "dropna",
            "fillna",
            "sort values",
            "sort_values",
            "rename",
            "resample",
            "pivot table",
            "pivot_table",
            "str accessor",
            "str split",
            "str.split",
            "copy",
            "size",
            "nunique",
        },
        hint_rules={"easy": (2, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bgroupby\b", re.IGNORECASE),
            re.compile(r"\bmerge\b", re.IGNORECASE),
            re.compile(r"\bdropna\b", re.IGNORECASE),
            re.compile(r"\bfillna\b", re.IGNORECASE),
            re.compile(r"\bsort_values\b", re.IGNORECASE),
            re.compile(r"\brename\b", re.IGNORECASE),
            re.compile(r"\btransform\b", re.IGNORECASE),
            re.compile(r"\brolling\b", re.IGNORECASE),
            re.compile(r"\bcumsum\b", re.IGNORECASE),
            re.compile(r"\brank\b", re.IGNORECASE),
            re.compile(r"\bto_datetime\b", re.IGNORECASE),
            re.compile(r"\bpivot(_table)?\b", re.IGNORECASE),
            re.compile(r"\.dt\b", re.IGNORECASE),
            re.compile(r"\.str\b", re.IGNORECASE),
        ),
        in_mixed_mock=True,
    ),
    TrackConfig(
        slug="pyspark",
        db_topic="pyspark",
        catalog_module=pyspark_questions,
        label="PySpark",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "pyspark_questions",
        concept_blocklist={
            "filter",
            "filter()",
            "repartition",
            "repartition()",
            "withcolumn",
            "withcolumn()",
            "collect",
            "collect()",
            "cache",
            "cache()",
            "merge",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bcollect\s*\(", re.IGNORECASE),
            re.compile(r"\bcount\s*\(", re.IGNORECASE),
            re.compile(r"\bfilter\s*\(", re.IGNORECASE),
            re.compile(r"\bwithcolumn\b", re.IGNORECASE),
            re.compile(r"\brepartition\b", re.IGNORECASE),
            re.compile(r"\bcoalesce\b", re.IGNORECASE),
            re.compile(r"\bcache\s*\(", re.IGNORECASE),
            re.compile(r"\bbroadcast\b", re.IGNORECASE),
            re.compile(r"\bcreateorreplace(temp)?view\b", re.IGNORECASE),
        ),
        in_mixed_mock=True,
    ),
    TrackConfig(
        slug="data-engineering",
        db_topic="data-engineering",
        catalog_module=data_engineering_questions,
        label="Data Engineering",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "data_engineering_questions",
        concept_blocklist={
            "airflow",
            "spark",
            "kafka",
            "flink",
            "dbt",
            "s3",
            "glue",
            "task",
            "operator",
            "sensor",
            "trigger",
            "pipeline",
            "etl",
            "elt",
            "cron",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bidempoten\w*\b", re.IGNORECASE),
            re.compile(r"\bwatermark\w*\b", re.IGNORECASE),
            re.compile(r"\bexactly[_\s-]once\b", re.IGNORECASE),
            re.compile(r"\bSCD\b"),
            re.compile(r"\bchange\s+data\s+capture\b", re.IGNORECASE),
            re.compile(r"\bbackfill\b", re.IGNORECASE),
            re.compile(r"\bat[_\s-]least[_\s-]once\b", re.IGNORECASE),
            re.compile(r"\bat[_\s-]most[_\s-]once\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
    ),
    TrackConfig(
        slug="data-modeling",
        db_topic="data-modeling",
        catalog_module=data_modeling_questions,
        label="Data Modeling",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "data_modeling_questions",
        concept_blocklist={
            "star schema",
            "snowflake schema",
            "fact table",
            "dimension table",
            "foreign key",
            "primary key",
            "scd",
            "surrogate key",
            "natural key",
            "dbt",
            "hub",
            "link",
            "satellite",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bstar\s+schema\b", re.IGNORECASE),
            re.compile(r"\bsnowflake\s+schema\b", re.IGNORECASE),
            re.compile(r"\bslowly\s+changing\b", re.IGNORECASE),
            re.compile(r"\bSCD\s+type\b", re.IGNORECASE),
            re.compile(r"\bsurrogate\s+key\b", re.IGNORECASE),
            re.compile(r"\bdata\s+vault\b", re.IGNORECASE),
            re.compile(r"\bgrain\b", re.IGNORECASE),
            re.compile(r"\bconformed\s+dimension\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
    ),
    TrackConfig(
        slug="statistics",
        db_topic="statistics",
        catalog_module=statistics_questions,
        label="Statistics",
        eval_kind="mixed",
        unlock_profile="code",
        content_dir=BACKEND_ROOT / "content" / "statistics_questions",
        concept_blocklist={
            "mean",
            "median",
            "variance",
            "standard deviation",
            "p-value",
            "t-test",
            "chi-squared",
            "z-score",
            "normal distribution",
            "binomial distribution",
            "scipy",
            "numpy",
            "statsmodels",
            "r-squared",
            "pearson",
            "spearman",
        },
        hint_rules={"easy": (2, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bp[\-\s]?value\b", re.IGNORECASE),
            re.compile(r"\bnull\s+hypothesis\b", re.IGNORECASE),
            re.compile(r"\bcentral\s+limit\s+theorem\b", re.IGNORECASE),
            re.compile(r"\bconfidence\s+interval\b", re.IGNORECASE),
            re.compile(r"\bbayes\w*\b", re.IGNORECASE),
            re.compile(r"\btype\s+[12]\s+error\b", re.IGNORECASE),
            re.compile(r"\bstatistical\s+power\b", re.IGNORECASE),
            re.compile(r"\bsimpson'?s\s+paradox\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
        mixed_subtype=True,
    ),
    TrackConfig(
        slug="experimentation",
        db_topic="experimentation",
        catalog_module=experimentation_questions,
        label="Experimentation",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "experimentation_questions",
        concept_blocklist={
            "a/b test",
            "control group",
            "treatment group",
            "randomization",
            "p-value",
            "null hypothesis",
            "alpha",
            "beta",
            "bootstrap",
            "permutation test",
            "z-test",
            "t-test",
            "chi-square",
            "sample size",
            "significance",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bcuped\b", re.IGNORECASE),
            re.compile(r"\bsample\s+ratio\s+mismatch\b", re.IGNORECASE),
            re.compile(r"\b(bonferroni|benjamini.hochberg|holm)\b", re.IGNORECASE),
            re.compile(r"\bswitchback\b", re.IGNORECASE),
            re.compile(r"\bdifference[_\s-]in[_\s-]differences\b", re.IGNORECASE),
            re.compile(r"\bregression\s+discontinuity\b", re.IGNORECASE),
            re.compile(r"\bthompson\s+sampling\b", re.IGNORECASE),
            re.compile(r"\bnovelt\w+\s+effect\b", re.IGNORECASE),
            re.compile(r"\bsutva\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
    ),
    TrackConfig(
        slug="ml-fundamentals",
        db_topic="ml-fundamentals",
        catalog_module=ml_fundamentals_questions,
        label="ML Fundamentals",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "ml_fundamentals_questions",
        concept_blocklist={
            "sklearn",
            "tensorflow",
            "pytorch",
            "keras",
            # Library names are blocklisted as concept tags per the cross-track
            # concept-tag contract ("Mechanic-name tags as concepts values").
            # Library names appear as patterns under BOOSTING MECHANICS in
            # concept_families.py for RESOLUTION (questions whose content
            # mentions XGBoost route to the family), but the authored
            # concept tag must be the family name BOOSTING MECHANICS itself.
            # Decision locked 2026-05-26 (F2 from ML Stage C).
            "xgboost",
            "lightgbm",
            "catboost",
            "fit",
            "predict",
            "transform",
            "pipeline",
            "gridsearchcv",
            "randomizedsearchcv",
            "relu",
            "sigmoid",
            "softmax",
            "tanh",
            "adam",
            "sgd",
            "rmsprop",
            "dropout",
            "batchnorm",
            "random_forest",
            "logistic_regression",
            "svm",
            "kmeans",
            "pca",
            "tsne",
            "umap",
            "precision_score",
            "recall_score",
            "f1_score",
            "roc_auc_score",
            "cross_val_score",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bbias[_\s-]variance\b", re.IGNORECASE),
            re.compile(r"\boverfitting\b", re.IGNORECASE),
            re.compile(r"\bregulariz\w*\b", re.IGNORECASE),
            re.compile(r"\bdropout\b", re.IGNORECASE),
            re.compile(r"\bbatch\s*norm\w*\b", re.IGNORECASE),
            re.compile(r"\bgradient\s+vanish\w*\b", re.IGNORECASE),
            re.compile(r"\bgradient\s+explo\w*\b", re.IGNORECASE),
            re.compile(r"\bdata\s+leak\w*\b", re.IGNORECASE),
            re.compile(r"\bclass\s+imbalance\b", re.IGNORECASE),
            re.compile(r"\bcross[_\s-]entrop\w*\b", re.IGNORECASE),
            re.compile(r"\btransfer\s+learn\w*\b", re.IGNORECASE),
            re.compile(r"\bconcept\s+drift\b", re.IGNORECASE),
            re.compile(r"\btraining[_\s-]serving\b", re.IGNORECASE),
            re.compile(r"\bfeature\s+importan\w*\b", re.IGNORECASE),
            re.compile(r"\bcalibrat\w*\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
    ),
    TrackConfig(
        slug="product-sense",
        db_topic="product-sense",
        catalog_module=product_sense_questions,
        label="Product Sense",
        eval_kind="mcq",
        unlock_profile="mcq",
        content_dir=BACKEND_ROOT / "content" / "product_sense_questions",
        concept_blocklist={
            # Framework-name recall is this track's signature anti-pattern — the
            # frameworks scaffold a candidate's reasoning, they are never the
            # answer. Block the acronyms so they can't be smuggled in as a tag.
            "heart",
            "aarrr",
            "circles",
            "rice",
            "ice",
            "north star",
            "jtbd",
            "okr",
            # Bare metric abbreviations are not reasoning families — they must be
            # tagged under ENGAGEMENT & STICKINESS REASONING or BUSINESS-MODEL
            # METRIC FLUENCY, never as a standalone concept.
            "dau",
            "wau",
            "mau",
            "dau/mau",
            "ctr",
            "gmv",
            "nps",
            "ltv",
            "cac",
            "aov",
            "mrr",
            "arr",
            "roas",
            "cpm",
        },
        hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
        first_hint_leak_patterns=(
            re.compile(r"\bgoodhart\b", re.IGNORECASE),
            re.compile(r"\bgaming\b", re.IGNORECASE),
            re.compile(r"\bgameable\b", re.IGNORECASE),
            re.compile(r"\bnovelty\s+effect\b", re.IGNORECASE),
            re.compile(r"\bsimpson'?s\b", re.IGNORECASE),
            re.compile(r"\bself[_\s-]selection\b", re.IGNORECASE),
            re.compile(r"\bconfound\w*\b", re.IGNORECASE),
            re.compile(r"\binstrumentation\b", re.IGNORECASE),
            re.compile(r"\bvanity\s+metric\b", re.IGNORECASE),
            re.compile(r"\bcannibaliz\w*\b", re.IGNORECASE),
        ),
        in_mixed_mock=False,
    ),
)

# ── Fast lookup tables ────────────────────────────────────────────────────────

_BY_SLUG: dict[str, TrackConfig] = {t.slug: t for t in TRACKS}
_BY_DB_TOPIC: dict[str, TrackConfig] = {t.db_topic: t for t in TRACKS}


def get_track(slug: str) -> TrackConfig:
    """Look up a track by its URL slug. Raises ValueError for unknown slugs."""
    try:
        return _BY_SLUG[slug]
    except KeyError:
        raise ValueError(f"Unknown track slug: {slug!r}")


def get_track_by_db_topic(db_topic: str) -> TrackConfig:
    """Look up a track by its DB topic string (e.g. 'pandas')."""
    try:
        return _BY_DB_TOPIC[db_topic]
    except KeyError:
        raise ValueError(f"Unknown db_topic: {db_topic!r}")


def all_slugs() -> list[str]:
    """All registered track slugs in registry order."""
    return [t.slug for t in TRACKS]


def mixed_mock_slugs() -> list[str]:
    """Track slugs eligible for the 'mixed' mock pool (all currently)."""
    return [t.slug for t in TRACKS if t.in_mixed_mock]


# Role → tracks mapping for Mixed mock sessions.
# Each role defines the pool of tracks drawn from in benchmark and custom drill.
# CANONICAL role→track mapping — this MUST stay identical to the curriculum SoT
# in frontend/src/roleRegistry.js (same sets, same order). The mock pool is no
# longer a divergent subset: a role's Mixed benchmark and custom drill cover
# exactly the tracks the role page lists. Keep these four in lockstep with
# roleRegistry.js, ProgressDashboard ROLE_TRACK_FILTERS, MockHub MOCK_ROLES, and
# docs/specs/platform-north-star.md § Role-to-track framing. See DECISIONS.md
# 2026-06-26 (one-mapping reconciliation).
_ROLE_TRACKS: dict[str, list[str]] = {
    "data_analyst":        ["sql", "statistics", "product-sense", "pandas", "python"],
    "data_engineer":       ["python", "sql", "pyspark", "data-engineering", "data-modeling"],
    "analytics_engineer":  ["sql", "data-modeling", "pandas", "python"],
    "data_scientist":      ["ml-fundamentals", "statistics", "experimentation", "product-sense", "python", "pandas", "sql"],
}

VALID_MOCK_ROLES = set(_ROLE_TRACKS)


def role_tracks(role: str) -> list[str]:
    """Return track slugs for a given role. Raises ValueError for unknown roles."""
    if role not in _ROLE_TRACKS:
        raise ValueError(f"Unknown mock role: {role!r}")
    return _ROLE_TRACKS[role]
