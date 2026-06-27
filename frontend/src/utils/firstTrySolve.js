/**
 * Whether a correct submission counts as a genuine "first-try solve" — the mastery /
 * honesty signal that the unlock ladder deliberately does not measure (post-reveal
 * solves still advance the gate). ALL three conditions must hold:
 *   - backendPriorAttempts === 0   : no submissions were logged for this question
 *       before this view (from /api/submissions; now populated for anonymous users too).
 *   - isFirstSubmitThisSession      : this is the first submission in the current question
 *       view — a synchronous backstop independent of the async refetch, so a failed first
 *       submit always disqualifies the next one even before pastAttempts refreshes.
 *   - !solutionRevealed             : the user did NOT open the official solution before
 *       solving — copying the answer is the exact answer-peek this signal exists to catch.
 */
export function isFirstTrySolve({ backendPriorAttempts, isFirstSubmitThisSession, solutionRevealed }) {
  return backendPriorAttempts === 0 && isFirstSubmitThisSession === true && !solutionRevealed;
}
