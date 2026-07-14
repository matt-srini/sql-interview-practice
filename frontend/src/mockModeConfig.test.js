import { describe, expect, it } from 'vitest';
import {
  getBenchmarkBlueprint,
  getMockModeCards,
  getMockModeDisplayLabel,
  getMockSetupDescriptor,
  getMockSessionDescriptor,
  getSessionQuestionCount,
  getSessionTimeMinutes,
  isBenchmarkMockMode,
  supportsBenchmarkMode,
  dimensionLabel,
  dimensionBlurb,
} from './mockModeConfig';
import { ROLES, mockRoleToken } from './roleRegistry';

describe('mockModeConfig', () => {
  it('exposes benchmark blueprints for supported tracks', () => {
    expect(getBenchmarkBlueprint('sql')).toMatchObject({ numQuestions: 3, timeMinutes: 60 });
    // mixed track supports role-based benchmark (Phase 3)
    expect(supportsBenchmarkMode('mixed')).toBe(true);
  });

  it('builds mode cards with benchmark enabled for mixed track (Phase 3: role-based)', () => {
    const cards = getMockModeCards('mixed');
    // Phase 3: mixed benchmark is supported via role selection — not disabled at the card level
    expect(cards[0]).toMatchObject({ key: 'benchmark', disabled: false });
    // Phase 3: 30min replaced by custom drill
    expect(cards[1]).toMatchObject({ key: 'custom', label: 'Custom drill' });
  });

  describe('getMockModeCards requiredTier — Free plan', () => {
    it('benchmark card: requiredTier is null and locked is false', () => {
      const [benchmark] = getMockModeCards('sql', 'free');
      expect(benchmark.requiredTier).toBeNull();
      expect(benchmark.locked).toBe(false);
    });

    it('custom card: requiredTier is "pro" and locked is true', () => {
      const [, custom] = getMockModeCards('sql', 'free');
      expect(custom.requiredTier).toBe('pro');
      expect(custom.locked).toBe(true);
    });

    it('loop card: requiredTier is "elite" and locked is true', () => {
      const [,, loop] = getMockModeCards('sql', 'free');
      expect(loop.requiredTier).toBe('elite');
      expect(loop.locked).toBe(true);
    });
  });

  describe('getMockModeCards requiredTier — Pro plan', () => {
    it('custom card: locked is false (Pro unlocks it)', () => {
      const [, custom] = getMockModeCards('sql', 'pro');
      expect(custom.locked).toBe(false);
    });

    it('loop card: locked is true with requiredTier "elite"', () => {
      const [,, loop] = getMockModeCards('sql', 'pro');
      expect(loop.locked).toBe(true);
      expect(loop.requiredTier).toBe('elite');
    });
  });

  describe('getMockModeCards requiredTier — Elite plan', () => {
    it('custom card: locked is false', () => {
      const [, custom] = getMockModeCards('sql', 'elite');
      expect(custom.locked).toBe(false);
    });

    it('loop card: locked is false', () => {
      const [,, loop] = getMockModeCards('sql', 'elite');
      expect(loop.locked).toBe(false);
    });
  });

  it('returns display labels and session shape values for benchmark mode', () => {
    expect(getMockModeDisplayLabel('benchmark')).toBe('Benchmark');
    expect(getMockModeDisplayLabel('60min')).toBe('Full (legacy)');
    expect(getSessionQuestionCount('benchmark', 'statistics', 4)).toBe(3);
    expect(getSessionTimeMinutes('benchmark', 'statistics', 30)).toBe(45);
  });

  it('hides the up-front count + time for Interview Loop (chain length is drawn at start)', () => {
    // Must NOT leak the custom-drill numQuestions/minutes default — both return null
    // so the MockHub brief hides the Questions/Time rows for Interview Loop.
    expect(getSessionQuestionCount('interview_loop', 'ml-fundamentals', 2)).toBeNull();
    expect(getSessionTimeMinutes('interview_loop', 'ml-fundamentals', 30)).toBeNull();
  });

  it('describes benchmark and drill session chrome copy', () => {
    expect(getMockSessionDescriptor('benchmark', 'sql')).toMatchObject({
      phaseLabel: 'Benchmark session',
      title: 'Fixed-shape track benchmark',
      isBenchmark: true,
    });
    expect(getMockSessionDescriptor('custom', 'sql')).toMatchObject({
      phaseLabel: 'Drill session',
      title: 'Custom follow-up drill',
      isBenchmark: false,
    });
  });

  it('getMockSessionDescriptor returns a truthy feedbackLine string for benchmark, custom, and interview_loop', () => {
    expect(typeof getMockSessionDescriptor('benchmark', 'sql').feedbackLine).toBe('string');
    expect(getMockSessionDescriptor('benchmark', 'sql').feedbackLine.length).toBeGreaterThan(0);

    expect(typeof getMockSessionDescriptor('custom', 'sql').feedbackLine).toBe('string');
    expect(getMockSessionDescriptor('custom', 'sql').feedbackLine.length).toBeGreaterThan(0);

    expect(typeof getMockSessionDescriptor('interview_loop', 'sql').feedbackLine).toBe('string');
    expect(getMockSessionDescriptor('interview_loop', 'sql').feedbackLine.length).toBeGreaterThan(0);
  });

  it('builds setup descriptors for drill planning surfaces', () => {
    expect(getMockSetupDescriptor('30min', 'sql', 2, 30)).toMatchObject({
      sectionLabel: 'Drill plan',
      summaryLine: '2 questions · 30 min cap',
    });
    expect(getMockSetupDescriptor('custom', 'sql', 4, 55)).toMatchObject({
      sectionLabel: 'Drill plan',
      summaryLine: '4 questions · 55 min cap',
    });
  });

  it('identifies benchmark mode explicitly', () => {
    expect(isBenchmarkMockMode('benchmark')).toBe(true);
    expect(isBenchmarkMockMode('30min')).toBe(false);
  });
});

describe('dimensionLabel', () => {
  it('returns the human label for a canonical _pivot token', () => {
    expect(dimensionLabel('business_rule_pivot')).toBe('Business rules');
  });

  it('resolves an alias token (without _pivot suffix) to its label', () => {
    expect(dimensionLabel('data_quality')).toBe('Data quality');
  });

  it('returns the label for the abstraction_pivot canonical dimension', () => {
    expect(dimensionLabel('abstraction_pivot')).toBe('Abstraction');
  });

  it('humanizes an unknown token by stripping _pivot and replacing underscores', () => {
    expect(dimensionLabel('made_up_pivot')).toBe('Made up');
  });

  it('returns empty string for null', () => {
    expect(dimensionLabel(null)).toBe('');
  });

  it('returns empty string for undefined', () => {
    expect(dimensionLabel(undefined)).toBe('');
  });

  it('returns empty string for an empty string', () => {
    expect(dimensionLabel('')).toBe('');
  });
});

describe('dimensionBlurb', () => {
  it('returns the correct blurb for a canonical token', () => {
    expect(dimensionBlurb('business_rule_pivot')).toBe('A business rule just changed. Adapt your solution to the new requirement.');
  });

  it('returns a non-empty blurb for an alias token', () => {
    expect(dimensionBlurb('data_quality').length).toBeGreaterThan(0);
  });

  it('returns the specific blurb for the abstraction_pivot canonical dimension', () => {
    expect(dimensionBlurb('abstraction_pivot')).toBe('The interviewer steps up a level — generalise from this specific case, or reframe it under a different lens.');
  });

  it('returns the generic fallback blurb for an unknown token', () => {
    expect(dimensionBlurb('made_up_pivot')).toBe('The interviewer shifts focus to a different dimension of the same problem.');
  });

  it('returns the generic fallback blurb for null', () => {
    expect(dimensionBlurb(null)).toBe('The interviewer shifts focus to a different dimension of the same problem.');
  });
});
import { formatLoopDifficulty } from './mockModeConfig';

describe('formatLoopDifficulty', () => {
  it('shows "x → hard" for escalating loops, single level otherwise', () => {
    expect(formatLoopDifficulty('medium', true)).toBe('medium → hard');
    expect(formatLoopDifficulty('medium', false)).toBe('medium');
    expect(formatLoopDifficulty('hard', false)).toBe('hard');
    expect(formatLoopDifficulty('', false)).toBe('');
    expect(formatLoopDifficulty(null, true)).toBe('');
  });
});

describe('Mixed benchmark count + summary derive from roleRegistry (no hardcode)', () => {
  it('getSessionQuestionCount returns the role track count for every role', () => {
    ROLES.forEach((r) => {
      expect(getSessionQuestionCount('benchmark', 'mixed', null, mockRoleToken(r))).toBe(r.tracks.length);
    });
  });

  it('getBenchmarkBlueprint derives numQuestions + a track-list summary per role', () => {
    ROLES.forEach((r) => {
      const bp = getBenchmarkBlueprint('mixed', mockRoleToken(r));
      expect(bp.numQuestions).toBe(r.tracks.length);
      expect(bp.summary.startsWith(`${r.tracks.length} questions across`)).toBe(true);
    });
  });

  it('Data Scientist Mixed benchmark is 7 questions (product-sense added at 2026-07-14 launch)', () => {
    expect(getSessionQuestionCount('benchmark', 'mixed', null, 'data_scientist')).toBe(7);
    expect(getBenchmarkBlueprint('mixed', 'data_scientist').numQuestions).toBe(7);
  });
});
