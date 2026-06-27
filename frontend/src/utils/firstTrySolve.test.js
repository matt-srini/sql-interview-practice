import { describe, it, expect } from 'vitest';
import { isFirstTrySolve } from './firstTrySolve';

describe('isFirstTrySolve', () => {
  const base = { backendPriorAttempts: 0, isFirstSubmitThisSession: true, solutionRevealed: false };

  it('is true only with no prior attempts, first submit this session, and no solution reveal', () => {
    expect(isFirstTrySolve(base)).toBe(true);
  });

  it('is false when the official solution was revealed (answer-peeking)', () => {
    expect(isFirstTrySolve({ ...base, solutionRevealed: true })).toBe(false);
  });

  it('is false when a prior submission was already made this session (e.g. a failed empty submit)', () => {
    expect(isFirstTrySolve({ ...base, isFirstSubmitThisSession: false })).toBe(false);
  });

  it('is false when the backend already has prior logged attempts for this question', () => {
    expect(isFirstTrySolve({ ...base, backendPriorAttempts: 2 })).toBe(false);
  });

  it('is false when several disqualifiers hold at once (the reported bug: failed submit + solution reveal)', () => {
    expect(isFirstTrySolve({ backendPriorAttempts: 0, isFirstSubmitThisSession: false, solutionRevealed: true })).toBe(false);
  });
});
