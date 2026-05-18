/**
 * Frontend track registry — single source of truth for all track metadata.
 *
 * Adding a new track:
 *   1. Add an entry to TRACK_META below.
 *   2. Add a matching entry in backend/tracks.py.
 * Everything else (TRACK_SLUGS, TRACK_LABELS, catalog path) is derived automatically.
 */

export const TRACK_META = {
  sql: {
    label: 'SQL',
    description: 'SQL problems against real datasets — joins, aggregations, window functions, and analytical patterns drawn from actual data engineering interviews.',
    color: '#5B6AF0',
    apiPrefix: '',
    language: 'sql',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    totalQuestions: 95,
    easyQuestions: 32,
    tagline: 'easy · medium · hard',
  },
  python: {
    label: 'Python',
    description: 'Python coding problems set in real data contexts — processing pipelines, cleaning routines, and analysis logic typical of data engineering and data science interviews.',
    color: '#2D9E6B',
    apiPrefix: '/python',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    totalQuestions: 83,
    easyQuestions: 30,
    tagline: 'data processing · algorithms · scripting',
  },
  'python-data': {
    label: 'Pandas',
    description: 'Practice Pandas and NumPy interview questions: DataFrame manipulation, groupby, reshaping, and time series analysis.',
    color: '#C47F17',
    apiPrefix: '/python-data',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    mixedSubtype: false,
    totalQuestions: 76,
    easyQuestions: 22,
    tagline: 'pandas · numpy · data wrangling',
  },
  pyspark: {
    label: 'PySpark',
    description: 'Practice PySpark interview questions: Spark architecture, streaming, performance optimization, and Delta Lake patterns.',
    color: '#D94F3D',
    apiPrefix: '/pyspark',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    totalQuestions: 102,
    easyQuestions: 38,
    tagline: 'conceptual · MCQ · predict output',
  },
  'data-engineering': {
    label: 'Data Engineering',
    description: 'Master data engineering concepts: ETL vs ELT, idempotency, orchestration, streaming vs batch, schema evolution, CDC, and system design trade-offs drawn from real DE interviews.',
    color: '#B9762B',
    apiPrefix: '/data-engineering',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    totalQuestions: 80,
    easyQuestions: 30,
    tagline: 'conceptual · MCQ · scenario',
  },
  'data-modeling': {
    label: 'Data Modeling',
    description: 'Dimensional modeling, normalization, star vs snowflake schemas, slowly changing dimensions, data vault patterns, and dbt design for analytics engineering interviews.',
    color: '#3F8E8C',
    apiPrefix: '/data-modeling',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    totalQuestions: 70,
    easyQuestions: 25,
    tagline: 'MCQ · scenario · schema design',
  },
  statistics: {
    label: 'Statistics',
    description: 'Probability, inference, hypothesis testing, A/B test design, and Bayesian reasoning — the quantitative foundation for data science and analytics engineering interviews.',
    color: '#7A5AF0',
    apiPrefix: '/statistics',
    language: 'python',
    hasRunCode: true,
    hasMCQ: true,
    mixedSubtype: true,
    totalQuestions: 80,
    easyQuestions: 28,
    tagline: 'conceptual · numerical · MCQ',
  },
  'ml-fundamentals': {
    label: 'ML Fundamentals',
    description: 'Machine learning concepts for data science interviews: model selection, bias-variance tradeoff, evaluation metrics, ensemble methods, regularization, and production ML trade-offs.',
    color: '#E0456A',
    apiPrefix: '/ml-fundamentals',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    totalQuestions: 90,
    easyQuestions: 30,
    tagline: 'conceptual · MCQ · scenario',
  },
  experimentation: {
    label: 'Experimentation',
    description: 'A/B testing design, statistical power, metric selection, variance reduction (CUPED), novelty and network effects, multiple testing corrections, and causal inference methods — the applied experimentation skills tested in product data science and growth interviews.',
    color: '#0EA5E9',
    apiPrefix: '/experimentation',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    mixedSubtype: false,
    totalQuestions: 80,
    easyQuestions: 30,
    tagline: 'MCQ · scenario · experiment design',
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
