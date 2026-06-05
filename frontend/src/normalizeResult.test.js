import { describe, it, expect } from 'vitest';
import { dictRowsToArrays, normalizeRunResult } from './normalizeResult';

describe('dictRowsToArrays', () => {
  it('converts pandas dict-rows to column-ordered arrays', () => {
    const cols = ['event_id', 'user_id', 'name'];
    const rows = [
      { user_id: 33, event_id: 1, name: 'view' },
      { event_id: 2, name: 'cart', user_id: 33 },
    ];
    expect(dictRowsToArrays(cols, rows)).toEqual([
      [1, 33, 'view'],
      [2, 33, 'cart'],
    ]);
  });

  it('is a no-op for SQL array-rows', () => {
    const rows = [[1, 'a'], [2, 'b']];
    expect(dictRowsToArrays(['x', 'y'], rows)).toBe(rows);
  });

  it('handles empty rows and missing keys', () => {
    expect(dictRowsToArrays(['a'], [])).toEqual([]);
    expect(dictRowsToArrays(['a', 'b'], [{ a: 1 }])).toEqual([[1, null]]);
  });
});

describe('normalizeRunResult', () => {
  it('converts a pandas run result and flattens to top level', () => {
    const d = normalizeRunResult({
      result: { columns: ['c1', 'c2'], rows: [{ c1: 1, c2: 2 }] },
      print_output: 'hi',
    });
    expect(d.rows).toEqual([[1, 2]]);
    expect(d.columns).toEqual(['c1', 'c2']);
    expect(d.stdout).toBe('hi');
  });

  it('converts submit user_result / expected_result dict-rows', () => {
    const d = normalizeRunResult({
      correct: false,
      user_result: { columns: ['a'], rows: [{ a: 9 }] },
      expected_result: { columns: ['a'], rows: [{ a: 8 }] },
    });
    expect(d.user_result.rows).toEqual([[9]]);
    expect(d.expected_result.rows).toEqual([[8]]);
  });

  it('passes SQL array-rows through unchanged', () => {
    const d = normalizeRunResult({ columns: ['x'], rows: [[1], [2]], results: [] });
    expect(d.rows).toEqual([[1], [2]]);
  });
});
