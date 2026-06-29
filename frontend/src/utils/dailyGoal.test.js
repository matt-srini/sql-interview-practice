import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getDailySolves, incrementDailySolves } from './dailyGoal';

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Mock CustomEvent (jsdom may not support it fully)
global.CustomEvent = class CustomEvent extends Event {
  constructor(name, opts) { super(name, opts); }
};

// Helper: format a date as YYYY-MM-DD local time (mirrors the util's localToday)
function localDate(date) {
  return date.toLocaleDateString('en-CA');
}

const TODAY = localDate(new Date());
const YESTERDAY = (() => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return localDate(d);
})();

const STORAGE_KEY = 'dt-daily-solves';

beforeEach(() => {
  localStorageMock.clear();
});

describe('getDailySolves', () => {
  it('returns 0 when nothing is stored', () => {
    expect(getDailySolves()).toBe(0);
  });

  it('returns 0 when the stored date is not today (stale day)', () => {
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({ date: YESTERDAY, count: 7 }));
    expect(getDailySolves()).toBe(0);
  });

  it('returns the stored count when the date matches today', () => {
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({ date: TODAY, count: 3 }));
    expect(getDailySolves()).toBe(3);
  });
});

describe('incrementDailySolves', () => {
  it('sets count to 1 from empty', () => {
    const result = incrementDailySolves();
    expect(result).toBe(1);
    expect(getDailySolves()).toBe(1);
  });

  it('increments to 2 on a second call (same day)', () => {
    incrementDailySolves();
    const result = incrementDailySolves();
    expect(result).toBe(2);
    expect(getDailySolves()).toBe(2);
  });

  it('resets to 1 when the stored date is a previous day', () => {
    localStorageMock.setItem(STORAGE_KEY, JSON.stringify({ date: YESTERDAY, count: 5 }));
    const result = incrementDailySolves();
    expect(result).toBe(1);
    expect(getDailySolves()).toBe(1);
  });
});
