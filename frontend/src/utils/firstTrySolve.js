/**
 * Whether a correct submission counts as a genuine "first-try solve" — the mastery /
 * honesty signal that the unlock ladder deliberately does not measure (post-reveal
 * solves still advance the gate). Both conditions must hold:
 *   - backendPriorAttempts === 0   : no submissions were logged for this question
 *       before this view (from /api/submissions; now populated for anonymous users too).
 *   - isFirstSubmitThisSession      : this is the first submission in the current question
 *       view — a synchronous backstop independent of the async refetch, so a failed first
 *       submit always disqualifies the next one even before pastAttempts refreshes.
 *
 * Note: there is intentionally NO "solution revealed" condition. The hints + official
 * solution only ever unlock AFTER a submission (the feedback panel is gated on
 * submitResult, and the pre-solve reveal paths additionally require !submitResult.correct
 * — a wrong submit). So any reveal is necessarily preceded by a submit, which already
 * makes isFirstSubmitThisSession false — a separate reveal flag would be redundant.
 */
export function isFirstTrySolve({ backendPriorAttempts, isFirstSubmitThisSession }) {
  return backendPriorAttempts === 0 && isFirstSubmitThisSession === true;
}
