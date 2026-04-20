import { describe, expect, it } from 'vitest';
import { parseSqlError } from './sqlErrorParser';

describe('parseSqlError', () => {
  it('returns tailored message for missing table errors', () => {
    const message = parseSqlError('Catalog Error: Table with name orderss does not exist!');
    expect(message).toContain('table was not found');
  });

  it('preserves line number when present', () => {
    const message = parseSqlError('Parser Error: syntax error at or near "FROM"\nLINE 3: FROM users');
    expect(message).toContain('line 3');
  });

  it('falls back to raw text for unknown errors', () => {
    const raw = 'Unexpected engine failure';
    expect(parseSqlError(raw)).toBe(raw);
  });
});
