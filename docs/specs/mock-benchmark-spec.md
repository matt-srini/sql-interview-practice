# Mock Benchmark Spec

Status: canonical planning spec
Owner: product + orchestration
Last updated: 2026-05-19

## Purpose

This spec defines what the mock product should optimize for during the modality migration.

## Core position

Mock is a benchmark layer, not a faster version of practice.

That means the mock experience must prioritize:

- credibility as a readiness signal
- consistent rules across a session
- delayed answer revelation
- strong post-session diagnosis
- track-aware composition instead of one-size-fits-all session templates

## Benchmark invariants

- No correctness reveal mid-session
- No solution reveal mid-session
- `Submit` is final for every track during a benchmark mock
- `Run` is allowed only on executable tracks
- Session composition should follow track blueprints, not one universal question count
- Custom configurable sessions belong to drill mode, not the benchmark contract

## Benchmark vs drill

| Mode | Purpose | Mid-session feedback | Composition |
|---|---|---|---|
| Benchmark mock | Measure readiness | Minimal, no verdict reveal beyond acceptance of submission | Track blueprint |
| Drill / custom session | Target practice under constraints | Flexible | User-configured |

The product may keep both, but they should not be framed as the same thing.

## Blueprint principle

Mock composition must respect modality.

| Modality family | Mock implication |
|---|---|
| Executable problem-solving | Longer per-question time, `Run` allowed, no result verdict until finish |
| Code-adjacent reasoning | Prompts should emphasize debugging, prediction, or execution reasoning |
| Constructed reasoning | Prompts should emphasize case analysis, prioritization, tradeoffs, and interpretation |
| Hybrid | Session blueprint must mix subtypes intentionally rather than randomly |

## Summary contract

Every finished benchmark session should produce:

- score headline
- time usage context
- per-question review with official solution or explanation
- concept breakdown for the session
- comparison against relevant historical baseline
- strongest pattern observed
- weakest pattern observed
- one clear next action

## Analytics contract

Mock analytics should answer four questions:

- How is the user's score trending?
- Which concepts repeatedly break under timed conditions?
- Which tracks or modalities are lagging behind the user's practice confidence?
- What should the user do next in practice or paths?

## Plan philosophy

Plan gating can change over time, but the premium split should follow this logic:

- Free: taste the benchmark loop without replacing the practice product
- Pro: serious mock usage and useful post-session review
- Elite: deep analytics, targeted focus controls, and the most coach-like debrief layer

## Filter philosophy

- Company filtering is a narrow SQL-specific capability today, not a universal mock paradigm.
- For the broader mock redesign, context or concept targeting is more defensible than forcing company filters across every track.

## Anti-patterns

- A 2-question timer dressed up as a benchmark
- Immediate right/wrong reveal that collapses the interview simulation
- Treating every track as if it should have the same mock shape
- Strong practice analytics with weak mock follow-through
- Feature gating that feels arbitrary rather than aligned to benchmark value

## Migration implications

The current Quick / Full / Custom system is an implementation starting point, not the final product contract. The modality rollout should separate benchmark mocks from drill-style sessions and make the benchmark rules explicit in backend responses, UI copy, and analytics.

---

## Chain atomicity contract (2026-05 refactor)

Cross-reference: full chain mechanics live in [`docs/features/mock.md`](../features/mock.md#follow-up-chain-atomicity-proelite--mock-only-content). The 7 universal `follow_up_dimension` values are defined in [`docs/concept-taxonomy.md`](../concept-taxonomy.md#the-7-universal-follow-up-dimensions-chain-pivots).

This section establishes the spec-level invariants the mock subsystem must enforce; the feature doc owns the user-facing contract.

### Invariants

1. **A parent question + every entry in its `follow_ups[]` array forms one atomic mock unit.** Selection picks the chain as a unit or skips it. Reservation in a session blueprint must be contiguous and adjacent. Splitting a chain across sessions is forbidden.
2. **Per-user, lifetime, at-most-once exposure.** Once a chain is selected for any session for a user, every member of the chain is consumed for that user across every future mock session — benchmark, short_drill, custom_drill, focus, Interview Loop.
3. **Orphan child selection is forbidden.** Catalog load fails if any follow-up question is reachable by the selector without going through its parent.
4. **Consumption trigger:** `POST /api/mock/start`. Not first submit. Not finish.
5. **Reclaim window:** 120 seconds from `started_at`. `DELETE /api/mock/:id` within the window returns 204 AND reverts the daily-quota counter AND reclaims every chain marked in that session. After 120 s the chain is locked in regardless of submission state.
6. **Pool exhaustion:** when no fresh chains / questions remain for the requested track × difficulty × mode for a user, mock returns **409 with `pool_exhausted: true`**. No soft fallback to consumed chains — soft fallback would dilute the readiness signal.

### Required schema

Parent (mock-only) question JSON:
```json
{
  "id": <int>,
  "mock_only": true,
  "follow_ups": [<child_id>, <child_id>, ...],   // ordered; length 1–3
  ...
}
```

Follow-up (mock-only) question JSON:
```json
{
  "id": <int>,
  "mock_only": true,
  "parent_id": <int>,                            // must back-reference the parent
  "follow_up_dimension": "scale_pivot",          // one of the 7 universal dimensions
  ...
}
```

### Catalog-load validations (Phase 2 work item)

`validate_content.py` must crash catalog load on:

- `follow_ups[]` referencing a non-existent ID
- Referenced child missing `mock_only: true`, `parent_id`, or `follow_up_dimension`
- Child whose `parent_id` doesn't match the parent that references it
- Child with its own non-empty `follow_ups[]` (nested chain forbidden)
- Two parents referencing the same child (shared child forbidden)
- Chain total length > 4 (parent + 3 follow-ups maximum)
- Two consecutive entries in a chain sharing the same `follow_up_dimension`
- Chain members spanning multiple tracks
- Follow-up easier difficulty than parent (chain difficulty must be same-or-escalating)
- Any `follow_up_dimension` value not in the 7-dimension registry

### Selection algorithm extension

The Phase 3 selector must additionally:

1. Look up the user's consumed-not-reclaimed `parent_id` set from `mock_chain_consumption`.
2. Exclude every question whose `id` is in that set OR whose `parent_id` is in that set (children of consumed parents).
3. When picking a parent with non-empty `follow_ups[]`, allocate (chain length) contiguous slots in the session.
4. If insufficient remaining slots in the session blueprint, **skip the chain** and look for the next eligible question. Do not split.
5. Mark the entire chain consumed in `mock_chain_consumption` (one row per chain, keyed by `parent_id`) atomically with session creation.

### Persistence schema (Phase 3)

```sql
CREATE TABLE mock_chain_consumption (
    user_id       UUID NOT NULL REFERENCES users(id),
    parent_id     INTEGER NOT NULL,
    consumed_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id    INTEGER REFERENCES mock_sessions(id),  -- NULL after reclaim
    reclaimed     BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, parent_id)
);

CREATE INDEX idx_mcc_user_active ON mock_chain_consumption (user_id) WHERE NOT reclaimed;
```

The `idx_mcc_user_active` partial index supports the hot path: "what parent_ids has this user already consumed?"

---

## Interview Loop mode

A new Elite-only mock mode that ships in Phase 3. Spec-level contract:

### Purpose

Mock today (benchmark + drills) measures readiness at a single point. Interview Loop simulates the iterative *shape* of a real interview — one anchor question followed by the interviewer's pivots, in sequence. The mode trains adaptability and pivot-handling rather than question-recognition.

### Composition rules

- **Eligibility:** Elite only. Free / Pro see "Unlock with Elite" copy on the mode card; cannot start a session.
- **Content:** Loop is **chain-only**. Eligible parents have `follow_ups[]` of length ≥ 1 (i.e. chain total length ≥ 2). Single-question parents belong to benchmark/drill modes; Loop is for chain content.
- **Session shape:** 1–3 chains per session. Default 2.
- **Time:** 15 min × number of chains. Default 30 min for 2 chains.
- **All benchmark invariants apply:** no correctness reveal mid-session, no solution reveal until finish, submit is final, run is allowed only on executable tracks.

### Selection logic

1. Filter pool to mock-only parents with `follow_ups[]` length ≥ 1, in the user-selected track.
2. Filter out chains already consumed by the user (`mock_chain_consumption`).
3. If `focus_concepts` is enabled, filter parents whose concept families match. **The filter applies to the parent only** — follow-up children may carry different concepts, since the chain's job is to pivot the topic, not stay on it.
4. Sample N chains where N = session chain count. Each chain enters the session as one atomic group; questions present in parent-then-follow-ups order.

### Within-session UX

- Each chain is visually grouped — a session-card boundary marks "Chain 1," "Chain 2," etc.
- Between parent and first follow-up, an **interviewer-pivot framing card** appears: *"Good. Now…"* + the follow-up's setup (no answer reveal). The pivot card briefly displays the `follow_up_dimension` icon (scale / business rule / data quality / etc.) so the user can pattern-match the kind of pivot they're seeing.
- The user does not see chain length up front (keeps the dialogue-shape simulation honest); a per-chain progress dot row appears as questions complete.

### Post-session analytics

- All standard Pro+ post-session analytics apply (concept breakdown, weak spots).
- **New Elite-only signal: per-dimension performance.** "Strong on `scale_pivot`, weak on `ambiguity_pivot`" — surfaced both in the session debrief and aggregated across Loop sessions in the dashboard.
- This dimension-level signal is unique to Loop and cannot be derived from benchmark/drill sessions.

### Failure modes the spec excludes

- **No Loop without chains.** If the user's available chain pool is empty (all consumed, or none authored for the chosen track), Loop returns 409 with copy nudging the user to a different track or to wait for new chain content. **Do not** silently degrade to a benchmark.
- **No mid-session chain re-roll.** A user who hits a chain they'd rather skip must complete it or discard the session within the 2-min window (which reclaims the chain).
- **No chain peek.** Chain length is hidden until reached; total session question count is implied by the session timer but not shown explicitly.

### Analytics contract additions

`/api/mock/analytics` Elite payload gains:

```json
"loop_summary": {
  "sessions": <int>,
  "chains_completed": <int>,
  "per_dimension_performance": [
    {"dimension": "scale_pivot", "attempted": 12, "correct": 9, "accuracy": 0.75},
    {"dimension": "ambiguity_pivot", "attempted": 8, "correct": 3, "accuracy": 0.375},
    ...
  ],
  "weakest_dimension": "ambiguity_pivot",
  "strongest_dimension": "scale_pivot"
}
```

The dimension-level signal feeds the Elite dashboard's "What kinds of interviewer pivots break you?" card.

---

## Plan-gated pool sourcing reference

Spec-level summary. Full plan-tier matrix and rationale live in [`docs/features/mock.md`](../features/mock.md#plan-tier-matrix-canonical-sot).

- **Free** — Mock pool restricted to practice-pool questions (filter: `mock_only != true`). Chains never included (chains all require mock-only access). Mode access: unlimited easy `short_drill` + 1 `benchmark` per rolling 7 days.
- **Pro** — Mock pool includes practice-pool questions AND mock-only questions including chains. Mode access: easy `short_drill` unlimited; combined 3 drills/day across medium/hard `short_drill` and any `custom_drill`; 3 `benchmark`/day.
- **Elite** — Same content access as Pro. Mode access soft-capped at 30s burst / 5 hourly / 20 daily (abuse defense, invisible). Adds `focus_concepts` filter and Interview Loop mode.

Pool-sourcing is enforced in the selector. UI must reflect plan state visibly (remaining-count chips on MockHub; upgrade modals when gated capability clicked).
