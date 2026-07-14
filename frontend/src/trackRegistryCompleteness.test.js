import { describe, expect, it } from 'vitest';
import { TRACK_SLUGS } from './trackRegistry';
import { TRACK_CONCEPT_MAP } from './pages/MockHub';

// CI backstop for the single-SoT model. The frontend track list is the trackRegistry
// (TRACK_SLUGS); the per-track mock focus-concept lists are hand-authored in MockHub and
// cannot derive. A new live track must have an entry, or its Elite focus-mode chips are
// empty. See docs/track-onboarding.md § New-track integration surfaces.
describe('track-registry completeness (frontend)', () => {
  it('every live track (TRACK_SLUGS) has a MockHub TRACK_CONCEPT_MAP entry', () => {
    const missing = TRACK_SLUGS.filter((slug) => !TRACK_CONCEPT_MAP[slug]);
    expect(missing).toEqual([]);
  });
});
