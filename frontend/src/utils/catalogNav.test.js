import { describe, it, expect } from 'vitest';
import { pickNextQuestionId, pickFirstQuestionId, pickContinueQuestionId } from './catalogNav';

const catalog = (groups) => ({ groups });

describe('catalogNav', () => {
  describe('pickNextQuestionId', () => {
    it('returns the flagged is_next question', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [
          { id: 1, state: 'solved' },
          { id: 2, state: 'unlocked', is_next: true },
        ] },
      ]);
      expect(pickNextQuestionId(c)).toBe(2);
    });

    it('prefers a flagged is_next in a later difficulty over an already-solved earlier one', () => {
      // All easy solved (no is_next there); next-up is in medium. The whole point
      // of the Resume fix: do NOT land on a solved easy question.
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'solved' }] },
        { difficulty: 'medium', questions: [{ id: 20, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickNextQuestionId(c)).toBe(20);
    });

    it('scans easy→hard for the flag regardless of group array order', () => {
      const c = catalog([
        { difficulty: 'medium', questions: [{ id: 20, state: 'unlocked', is_next: true }] },
        { difficulty: 'easy', questions: [{ id: 10, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickNextQuestionId(c)).toBe(10);
    });

    it('falls back to the first unlocked question when nothing is flagged (track fully solved)', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'solved' }] },
      ]);
      expect(pickNextQuestionId(c)).toBe(1);
    });

    it('skips locked questions in the fallback', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'locked' }, { id: 2, state: 'unlocked' }] },
      ]);
      expect(pickNextQuestionId(c)).toBe(2);
    });

    it('returns null for empty / missing catalog or an all-locked track', () => {
      expect(pickNextQuestionId(null)).toBeNull();
      expect(pickNextQuestionId(catalog([]))).toBeNull();
      expect(pickNextQuestionId(catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'locked' }] },
      ]))).toBeNull();
    });
  });

  describe('pickFirstQuestionId', () => {
    it('returns the first non-locked question across groups', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'unlocked' }] },
      ]);
      expect(pickFirstQuestionId(c)).toBe(1);
    });

    it('returns null when everything is locked', () => {
      expect(pickFirstQuestionId(catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'locked' }] },
      ]))).toBeNull();
    });
  });

  describe('pickContinueQuestionId', () => {
    it('prefers next-up over the first question', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickContinueQuestionId(c)).toBe(2);
    });

    it('falls back to the first unlocked question', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }] },
      ]);
      expect(pickContinueQuestionId(c)).toBe(1);
    });
  });
});
