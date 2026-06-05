import { describe, it, expect } from 'vitest';
import { dictRowsToArrays, normalizeRunResult, rowCountLabel } from './normalizeResult';

describe('rowCountLabel', () => {
  it('shows the true total when truncated', () => {
    expect(rowCountLabel({ rows: new Array(200), truncated: true, total_rows: 43152, row_limit: 200 }))
      .toBe('showing first 200 of 43,152 rows');
  });
  it('shows a plain count when not truncated', () => {
    expect(rowCountLabel({ rows: [1, 2, 3], truncated: false, total_rows: 3 })).toBe('3 rows');
    expect(rowCountLabel({ rows: [1] })).toBe('1 row');
    expect(rowCountLabel({ rows: [] })).toBe('0 rows');
    expect(rowCountLabel(null)).toBe('0 rows');
  });
});

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

  it('lifts pandas preview metadata (total_rows/truncated) to the top level', () => {
    const d = normalizeRunResult({
      result: { columns: ['c'], rows: [{ c: 1 }], total_rows: 5000, truncated: true, row_limit: 200 },
    });
    expect(d.total_rows).toBe(5000);
    expect(d.truncated).toBe(true);
    expect(d.row_limit).toBe(200);
    expect(rowCountLabel(d)).toBe('showing first 200 of 5,000 rows');
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
