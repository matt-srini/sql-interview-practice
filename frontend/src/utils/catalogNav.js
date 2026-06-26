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
 * The user's NEXT-UP question id — the backend-flagged `is_next`, scanning
 * easy→hard — or null when the track has no actionable next question (every
 * accessible question solved, or nothing unlocked). "No next-up" is a real,
 * representable state (null): callers use it to show a completed/explore state
 * instead of re-opening a solved question.
 */
export function pickNextUpQuestionId(catalog) {
  if (!catalog) return null;
  for (const diff of DIFFICULTY_ORDER) {
    const g = catalog.groups?.find((x) => x.difficulty === diff);
    const hit = g?.questions.find((q) => q.is_next);
    if (hit) return hit.id;
  }
  return null;
}

/**
 * The first unlocked question in the track, ignoring next-up. Fallback target
 * for an explicit "Continue/Start" action when there is no next-up.
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
 * Where an explicit "Continue" / "Start" click should land: the next-up
 * question if there is one, else the first unlocked question. null only if
 * nothing is reachable.
 */
export function pickContinueQuestionId(catalog) {
  return pickNextUpQuestionId(catalog) ?? pickFirstQuestionId(catalog);
}
