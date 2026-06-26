import { describe, it, expect } from 'vitest';
import { pickNextUpQuestionId, pickFirstQuestionId, pickContinueQuestionId } from './catalogNav';

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
});
