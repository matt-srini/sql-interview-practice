import { describe, expect, it } from 'vitest';
import {
  getBenchmarkBlueprint,
  getMockModeCards,
  getMockModeDisplayLabel,
  getMockSessionDescriptor,
  getSessionQuestionCount,
  getSessionTimeMinutes,
  supportsBenchmarkMode,
} from './mockModeConfig';

describe('mockModeConfig', () => {
  it('exposes benchmark blueprints for supported tracks', () => {
    expect(getBenchmarkBlueprint('sql')).toMatchObject({ numQuestions: 3, timeMinutes: 60 });
    expect(supportsBenchmarkMode('mixed')).toBe(false);
  });

  it('builds mode cards with benchmark disabled for mixed track', () => {
    const cards = getMockModeCards('mixed');
    expect(cards[0]).toMatchObject({ key: 'benchmark', disabled: true });
    expect(cards[1]).toMatchObject({ key: '30min', label: 'Sprint drill' });
  });

  it('returns display labels and session shape values for benchmark mode', () => {
    expect(getMockModeDisplayLabel('benchmark')).toBe('Benchmark');
    expect(getMockModeDisplayLabel('60min')).toBe('Full (legacy)');
    expect(getSessionQuestionCount('benchmark', 'statistics', 4)).toBe(3);
    expect(getSessionTimeMinutes('benchmark', 'statistics', 30)).toBe(45);
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
});