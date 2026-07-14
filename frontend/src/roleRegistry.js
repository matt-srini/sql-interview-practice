/**
 * Role registry — single source of truth for role → track mapping.
 *
 * `slug`    — URL segment used in /interview-prep/:role
 * `hasPage` — true when a dedicated /interview-prep/<slug> page is published
 *
 * Used by (everything role→track derives from here — no second hardcoded mapping):
 *   - LandingPage RoleSelectorSection (tabs + track panels)
 *   - RoleInterviewPrepPage (config-driven SEO page per role)
 *   - MockHub MOCK_ROLES (mock role selector) — derived
 *   - ProgressDashboard ROLE_TRACK_FILTERS (dashboard role filter) — derived
 *   - mockModeConfig (Mixed benchmark question count + track summary) — derived
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
    tagline: 'SQL depth · product metrics · statistical reasoning',
    tracks: ['sql', 'statistics', 'product-sense', 'pandas', 'python'],
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
    tagline: 'ML · experiments · product metrics · Python & Pandas',
    tracks: ['ml-fundamentals', 'statistics', 'experimentation', 'product-sense', 'python', 'pandas', 'sql'],
  },
];

// ── Derived role accessors ───────────────────────────────────────────────────
// The mock/API role token is the underscored slug ('data-scientist' → 'data_scientist').
// MockHub's MOCK_ROLES, the dashboard's ROLE_TRACK_FILTERS, the Mixed benchmark question
// count, and the backend role token all derive from here. Nothing restates the mapping.
export const mockRoleToken = (role) => role.slug.replace(/-/g, '_');

export const roleByMockToken = (token) =>
  ROLES.find((r) => mockRoleToken(r) === token) ?? null;
