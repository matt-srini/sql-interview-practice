import { describe, it, expect } from 'vitest';
import { ROLES } from './roleRegistry';
import { MOCK_ROLES } from './pages/MockHub';
import { ROLE_TRACK_FILTERS } from './pages/ProgressDashboard';

// MockHub MOCK_ROLES and the dashboard ROLE_TRACK_FILTERS are now DERIVED from
// roleRegistry ROLES (the SoT) — there is no second hardcoded role→track mapping.
// This test verifies the derivation stays correct and fails loudly if anyone
// re-hardcodes either list and lets it drift (the 2026-06-26 bug). See
// docs/decisions/DECISIONS.md 2026-06-26.

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
