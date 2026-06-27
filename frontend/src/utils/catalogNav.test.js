import { describe, it, expect } from 'vitest';
import { pickNextUpQuestionId, pickFirstQuestionId, pickContinueQuestionId, pickSequentialNextQuestionId } from './catalogNav';

const catalog = (groups) => ({ groups });

describe('catalogNav', () => {
  describe('pickNextUpQuestionId (is_next only — null when nothing actionable)', () => {
    it('returns the flagged is_next question', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [
          { id: 1, state: 'solved' },
          { id: 2, state: 'unlocked', is_next: true },
        ] },
      ]);
      expect(pickNextUpQuestionId(c)).toBe(2);
    });

    it('prefers a flagged is_next in a later difficulty over an already-solved earlier one', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'solved' }] },
        { difficulty: 'medium', questions: [{ id: 20, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickNextUpQuestionId(c)).toBe(20);
    });

    it('scans easy→hard for the flag regardless of group array order', () => {
      const c = catalog([
        { difficulty: 'medium', questions: [{ id: 20, state: 'unlocked', is_next: true }] },
        { difficulty: 'easy', questions: [{ id: 10, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickNextUpQuestionId(c)).toBe(10);
    });

    it('returns null when the track is fully solved (no is_next anywhere)', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'solved' }] },
        { difficulty: 'medium', questions: [{ id: 20, state: 'solved' }] },
      ]);
      expect(pickNextUpQuestionId(c)).toBeNull();
    });

    it('returns null when all accessible are solved and the rest are locked', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }] },
        { difficulty: 'hard', questions: [{ id: 30, state: 'locked' }] },
      ]);
      expect(pickNextUpQuestionId(c)).toBeNull();
    });

    it('returns null for empty / missing catalog', () => {
      expect(pickNextUpQuestionId(null)).toBeNull();
      expect(pickNextUpQuestionId(catalog([]))).toBeNull();
    });
  });

  describe('pickFirstQuestionId', () => {
    it('returns the first non-locked question across groups', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'unlocked' }] },
      ]);
      expect(pickFirstQuestionId(c)).toBe(1);
    });
    it('skips locked questions', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'locked' }, { id: 2, state: 'unlocked' }] },
      ]);
      expect(pickFirstQuestionId(c)).toBe(2);
    });
    it('returns null when everything is locked', () => {
      expect(pickFirstQuestionId(catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'locked' }] },
      ]))).toBeNull();
    });
  });

  describe('pickContinueQuestionId (next-up, else first unlocked)', () => {
    it('prefers next-up', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'unlocked', is_next: true }] },
      ]);
      expect(pickContinueQuestionId(c)).toBe(2);
    });
    it('falls back to the first unlocked question when there is no next-up (fully solved)', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }, { id: 2, state: 'solved' }] },
      ]);
      expect(pickContinueQuestionId(c)).toBe(1);
    });
  });

  describe('pickSequentialNextQuestionId (workspace Next button — sequential, not next-up)', () => {
    it('advances to the question AFTER the current one, not the global is_next (the Q10 → Q1 bug)', () => {
      // Anonymous user has solved only Q10, so is_next points back to Q1 (first unsolved).
      // Clicking Next on Q10 must go to Q11 — never jump back to Q1.
      const questions = Array.from({ length: 12 }, (_, i) => ({
        id: i + 1, order: i + 1, state: i === 9 ? 'solved' : 'unlocked', is_next: i === 0,
      }));
      const c = catalog([{ difficulty: 'easy', questions }]);
      expect(pickNextUpQuestionId(c)).toBe(1);              // global next-up is Q1...
      expect(pickSequentialNextQuestionId(c, 10)).toBe(11); // ...but Next from Q10 is Q11
    });

    it('orders by `order` within a group, not array position', () => {
      const c = catalog([{ difficulty: 'easy', questions: [
        { id: 3, order: 3, state: 'unlocked' },
        { id: 1, order: 1, state: 'unlocked' },
        { id: 2, order: 2, state: 'unlocked' },
      ] }]);
      expect(pickSequentialNextQuestionId(c, 1)).toBe(2);
      expect(pickSequentialNextQuestionId(c, 2)).toBe(3);
    });

    it('spills into the next difficulty group at the end of the current one', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, order: 1, state: 'unlocked' }, { id: 2, order: 2, state: 'unlocked' }] },
        { difficulty: 'medium', questions: [{ id: 20, order: 1, state: 'unlocked' }] },
      ]);
      expect(pickSequentialNextQuestionId(c, 2)).toBe(20);
    });

    it('skips locked questions so Next never dumps into a locked preview', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, order: 1, state: 'unlocked' }, { id: 2, order: 2, state: 'unlocked' }] },
        { difficulty: 'medium', questions: [{ id: 20, order: 1, state: 'locked' }, { id: 21, order: 2, state: 'unlocked' }] },
      ]);
      expect(pickSequentialNextQuestionId(c, 2)).toBe(21);
    });

    it('returns null at the end of the catalog', () => {
      const c = catalog([{ difficulty: 'easy', questions: [{ id: 1, order: 1, state: 'unlocked' }, { id: 2, order: 2, state: 'unlocked' }] }]);
      expect(pickSequentialNextQuestionId(c, 2)).toBeNull();
    });

    it('returns null when only locked questions remain after the current one', () => {
      const c = catalog([
        { difficulty: 'easy', questions: [{ id: 1, order: 1, state: 'unlocked' }] },
        { difficulty: 'medium', questions: [{ id: 20, order: 1, state: 'locked' }] },
      ]);
      expect(pickSequentialNextQuestionId(c, 1)).toBeNull();
    });

    it('returns null for an unknown current id or a missing catalog', () => {
      const c = catalog([{ difficulty: 'easy', questions: [{ id: 1, order: 1, state: 'unlocked' }] }]);
      expect(pickSequentialNextQuestionId(c, 999)).toBeNull();
      expect(pickSequentialNextQuestionId(null, 1)).toBeNull();
      expect(pickSequentialNextQuestionId(c, null)).toBeNull();
    });
  });
});
