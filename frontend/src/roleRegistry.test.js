import { describe, it, expect } from 'vitest';
import { ROLES } from './roleRegistry';
import { MOCK_ROLES } from './pages/MockHub';
import { ROLE_TRACK_FILTERS } from './pages/ProgressDashboard';

// The role→track mapping is duplicated across three frontend surfaces: the
// curriculum SoT (roleRegistry ROLES), the mock role selector (MockHub
// MOCK_ROLES), and the dashboard role filter (ProgressDashboard
// ROLE_TRACK_FILTERS). They MUST encode the same four track-sets. This guard
// would have caught the drift fixed on 2026-06-26 (the Data Scientist mock set
// had silently diverged from the curriculum, and pandas was missing). A cleaner
// future refactor is to derive the latter two from roleRegistry; until then this
// parity test is the guard. See docs/decisions/DECISIONS.md 2026-06-26.

// Order- and id/label-independent: compare the *set of track-sets*.
const trackSets = (rolesArray) =>
  rolesArray.map((r) => [...r.tracks].sort().join(',')).sort();

describe('role→track mapping parity', () => {
  it('MockHub MOCK_ROLES track-sets match roleRegistry ROLES', () => {
    expect(trackSets(MOCK_ROLES)).toEqual(trackSets(ROLES));
  });

  it('Dashboard ROLE_TRACK_FILTERS track-sets match roleRegistry ROLES', () => {
    expect(trackSets(ROLE_TRACK_FILTERS)).toEqual(trackSets(ROLES));
  });

  it('Data Scientist covers six tracks including pandas (2026-06-26 addition)', () => {
    const ds = ROLES.find((r) => r.slug === 'data-scientist');
    expect(ds.tracks).toContain('pandas');
    expect(ds.tracks).toHaveLength(6);
  });
});
