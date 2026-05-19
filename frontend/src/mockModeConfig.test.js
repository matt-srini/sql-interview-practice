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