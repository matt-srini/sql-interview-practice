import { describe, it, expect } from 'vitest';
import { extractUtmParams } from './analytics';

describe('extractUtmParams', () => {
  it('returns only present utm_* keys', () => {
    const result = extractUtmParams('?utm_source=twitter&utm_medium=social&utm_campaign=launch');
    expect(result).toEqual({
      utm_source: 'twitter',
      utm_medium: 'social',
      utm_campaign: 'launch',
    });
  });

  it('returns an empty object when no utm params are present', () => {
    expect(extractUtmParams('?foo=bar&baz=1')).toEqual({});
    expect(extractUtmParams('')).toEqual({});
    expect(extractUtmParams('?')).toEqual({});
  });

  it('omits utm keys whose value is empty string', () => {
    const result = extractUtmParams('?utm_source=&utm_medium=email');
    expect(result).toEqual({ utm_medium: 'email' });
  });

  it('handles all five utm keys', () => {
    const search =
      '?utm_source=newsletter&utm_medium=email&utm_campaign=june&utm_content=cta&utm_term=sql';
    const result = extractUtmParams(search);
    expect(result).toEqual({
      utm_source: 'newsletter',
      utm_medium: 'email',
      utm_campaign: 'june',
      utm_content: 'cta',
      utm_term: 'sql',
    });
  });

  it('ignores non-utm query params', () => {
    const result = extractUtmParams('?utm_source=google&role=data-engineer&ref=landing');
    expect(result).toEqual({ utm_source: 'google' });
  });

  it('returns an empty object for null / undefined input without throwing', () => {
    expect(extractUtmParams(null)).toEqual({});
    expect(extractUtmParams(undefined)).toEqual({});
  });
});
