/**
 * Single source of truth for resolving "where to go" within a track catalog.
 *
 * Used by TrackHubPage's Continue/Start button and AppShell's ?resume= redirect
 * so both land the user on the SAME question. Catalog shape:
 *   { groups: [{ difficulty: 'easy'|'medium'|'hard', questions: [{ id, state, is_next }] }] }
 * `is_next` is the backend-computed next-up flag (the SidebarNav "NEXT" badge);
 * `state` is 'solved' | 'unlocked' | 'locked' (locked questions are never a target).
 */

const DIFFICULTY_ORDER = ['easy', 'medium', 'hard'];

/**
 * The user's next-up question id, or null if nothing is reachable.
 *
 * Two passes, both easy→hard:
 *  1. The backend-flagged `is_next` anywhere — a flag in a later difficulty wins
 *     over an earlier difficulty's already-solved questions, so "all easy solved,
 *     next-up in medium" correctly lands on medium (not a solved easy question).
 *  2. Fallback when nothing is flagged anywhere (e.g. the track is fully solved):
 *     the first unlocked question.
 */
export function pickNextQuestionId(catalog) {
  if (!catalog) return null;
  const groupFor = (diff) => catalog.groups?.find((x) => x.difficulty === diff);
  for (const diff of DIFFICULTY_ORDER) {
    const hit = groupFor(diff)?.questions.find((q) => q.is_next);
    if (hit) return hit.id;
  }
  for (const diff of DIFFICULTY_ORDER) {
    const hit = groupFor(diff)?.questions.find((q) => q.state !== 'locked');
    if (hit) return hit.id;
  }
  return null;
}

/**
 * The first unlocked question in the track, ignoring next-up. Fallback target
 * when a track has no next-up (e.g. fully solved).
 */
export function pickFirstQuestionId(catalog) {
  if (!catalog) return null;
  for (const g of (catalog.groups ?? [])) {
    const first = g.questions.find((q) => q.state !== 'locked');
    if (first) return first.id;
  }
  return null;
}

/**
 * Where "Continue" / "Resume" should land: the next-up question if there is
 * one, else the first unlocked question. null if the catalog has nothing
 * reachable.
 */
export function pickContinueQuestionId(catalog) {
  return pickNextQuestionId(catalog) ?? pickFirstQuestionId(catalog);
}
