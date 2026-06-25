/**
 * Frontend track registry — single source of truth for all track metadata.
 *
 * Adding a new track:
 *   1. Add an entry to TRACK_META below.
 *   2. Add a matching entry in backend/tracks.py.
 * Everything else (TRACK_SLUGS, TRACK_LABELS, catalog path) is derived automatically.
 *
 * Question counts are NOT stored here. They are fetched live from /api/catalog/counts
 * via CatalogCountsContext so they never go stale when questions are added.
 * Use useCatalogCounts() to access per-track totals in components.
 */

export const TRACK_META = {
  sql: {
    label: 'SQL',
    description: 'SQL problems against real datasets: joins, aggregations, window functions, and the analytical patterns working data teams reach for on the job.',
    color: '#5B6AF0',
    apiPrefix: '',
    language: 'sql',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    tagline: 'easy · medium · hard',
  },
  python: {
    label: 'Python',
    description: 'Python algorithm problems grounded in real data engineering contexts: sessionization, stream aggregation, DAG ordering, and the algorithmic reasoning data professionals reach for beyond the basics.',
    color: '#2D9E6B',
    apiPrefix: '/python',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    tagline: 'data processing · algorithms · scripting',
  },
  pandas: {
    label: 'Pandas',
    description: 'DataFrame manipulation, groupby aggregation, reshaping, time series, and the data wrangling fluency that analysts and data scientists rely on every day.',
    color: '#C47F17',
    apiPrefix: '/pandas',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    tagline: 'pandas · numpy · data wrangling',
  },
  pyspark: {
    label: 'PySpark',
    description: 'Spark architecture, shuffle optimization, streaming, and Delta Lake: the system-level reasoning behind production Spark decisions.',
    color: '#D94F3D',
    apiPrefix: '/pyspark',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    tagline: 'spark reasoning · predict output · debug',
  },
  'data-engineering': {
    label: 'Data Engineering',
    description: 'ETL vs ELT, idempotency, orchestration, streaming vs batch, CDC, and schema evolution: the system design reasoning behind reliable data pipelines.',
    color: '#B9762B',
    apiPrefix: '/data-engineering',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    tagline: 'systems reasoning · scenario · debug',
  },
  'data-modeling': {
    label: 'Data Modeling',
    description: 'Dimensional modeling, normalization, star vs snowflake, SCDs, and dbt patterns: the design decisions that determine whether downstream analytics scale or break.',
    color: '#3F8E8C',
    apiPrefix: '/data-modeling',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    tagline: 'modeling reasoning · scenario · schema design',
  },
  statistics: {
    label: 'Statistics',
    description: 'Probability, inference, hypothesis testing, A/B test design, and Bayesian reasoning: the quantitative thinking that lets data scientists make defensible claims from data.',
    color: '#7A5AF0',
    apiPrefix: '/statistics',
    language: 'python',
    hasRunCode: true,
    hasMCQ: true,
    mixedSubtype: true,
    tagline: 'conceptual reasoning · numerical',
  },
  'ml-fundamentals': {
    label: 'ML Fundamentals',
    description: 'Model selection, bias-variance, evaluation metrics, regularization, and production ML trade-offs: the judgment that separates practitioners who understand their models from those who just run them.',
    color: '#E0456A',
    apiPrefix: '/ml-fundamentals',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    tagline: 'model reasoning · scenario · debug',
  },
  experimentation: {
    label: 'Experimentation',
    description: 'A/B testing design, statistical power, metric selection, CUPED, novelty effects, multiple testing, and causal inference: the experimentation reasoning that makes product decisions causally defensible.',
    color: '#0EA5E9',
    apiPrefix: '/experimentation',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    tagline: 'experiment reasoning · scenario · predict output',
  },
};

// Active tracks only — safe for routing, catalog, mock, dashboard, etc.
export const TRACK_SLUGS = Object.keys(TRACK_META).filter(k => !TRACK_META[k].comingSoon);
// All tracks including upcoming — used by the landing page index and role selector.
export const ALL_TRACK_SLUGS = Object.keys(TRACK_META);

export const TRACK_LABELS = {
  ...Object.fromEntries(ALL_TRACK_SLUGS.map(s => [s, TRACK_META[s].label])),
  mixed: 'Mixed',
};
