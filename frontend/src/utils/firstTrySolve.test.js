import { describe, it, expect } from 'vitest';
import { isFirstTrySolve } from './firstTrySolve';

describe('isFirstTrySolve', () => {
  const base = { backendPriorAttempts: 0, isFirstSubmitThisSession: true };

  it('is true with no prior attempts and this being the first submit this session', () => {
    expect(isFirstTrySolve(base)).toBe(true);
  });

  it('is false when a prior submission was already made this session (e.g. a failed empty submit)', () => {
    expect(isFirstTrySolve({ ...base, isFirstSubmitThisSession: false })).toBe(false);
  });

  it('is false when the backend already has prior logged attempts for this question', () => {
    expect(isFirstTrySolve({ ...base, backendPriorAttempts: 2 })).toBe(false);
  });

  it('is false when both disqualifiers hold (prior backend attempts AND a prior submit this session)', () => {
    expect(isFirstTrySolve({ backendPriorAttempts: 2, isFirstSubmitThisSession: false })).toBe(false);
  });

  // Why no "solution revealed" case: the reveal UI only unlocks after a submission
  // (a wrong one, pre-solve), so a reveal always implies isFirstSubmitThisSession=false
  // — already covered above. See firstTrySolve.js.
});
