/**
 * Role registry — single source of truth for role → track mapping.
 *
 * `slug`    — URL segment used in /interview-prep/:role
 * `hasPage` — true when a dedicated /interview-prep/<slug> page is published
 *
 * Used by:
 *   - LandingPage RoleSelectorSection (tabs + track panels)
 *   - RoleInterviewPrepPage (config-driven SEO page per role)
 */
export const ROLES = [
  {
    id: 'engineer',
    slug: 'data-engineer',
    label: 'Data Engineer',
    hasPage: true,
    tagline: 'Python pipelines · distributed systems · DE concepts',
    tracks: ['python', 'sql', 'pyspark', 'data-engineering', 'data-modeling'],
  },
  {
    id: 'analyst',
    slug: 'data-analyst',
    label: 'Data Analyst',
    hasPage: true,
    tagline: 'SQL depth · statistical reasoning · Python for data',
    tracks: ['sql', 'statistics', 'pandas', 'python'],
  },
  {
    id: 'analytics_engineer',
    slug: 'analytics-engineer',
    label: 'Analytics Engineer',
    hasPage: true,
    tagline: 'SQL precision · data modeling · dbt patterns',
    tracks: ['sql', 'data-modeling', 'pandas', 'python'],
  },
  {
    id: 'scientist',
    slug: 'data-scientist',
    label: 'Data Scientist',
    hasPage: true,
    tagline: 'ML · statistical inference · Python & Pandas for modelling',
    tracks: ['ml-fundamentals', 'statistics', 'experimentation', 'python', 'pandas', 'sql'],
  },
];
