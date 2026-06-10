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

### Mid-session submit response contract

The `POST /{session_id}/submit` endpoint must return a **lean result** during benchmark and Interview Loop sessions. Lean means:

| What | Mid-session | At finish (`/finish`) |
|---|---|---|
| `correct` (boolean) | **Omitted** for MCQ tracks | Present on every question |
| `explanation` | Always omitted | Present on every question |
| `correct_option` | Always omitted | Present on MCQ questions |
| `solution_code` | Always omitted | Present on code-execution questions |
| `error` / `feedback` | Present (execution diagnostics only) | Present |

For MCQ tracks (`eval_kind == "mcq"`), the `correct` field must be stripped from the mid-session response for any session with `mode` in `{"benchmark", "interview_loop"}`. The frontend must not use the presence or absence of `correct` to indicate correctness to the user until the session finishes. Buttons and dots should reflect **submitted** state only, not solved/unsolved state, for these session modes.

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

### Blueprint feasibility — difficulty-aware shapes

**Bank shape governs blueprint, not vice versa.** A blueprint declared in code or docs must be achievable given the actual bank composition at the targeted difficulty. Authors **never** force-fit content to a fixed-shape blueprint — if the genuine, quality-preserving question set at a difficulty doesn't match the blueprint, the **blueprint is wrong**, not the content. Good questions are the product; blueprints are a derived contract that describes how those questions are assembled into a session. When the two conflict, fix the blueprint (and this doc).

Bank type-distributions are not uniform across difficulties within a track. For example, a track's easy bank may be almost entirely `conceptual` (e.g., Data Modeling easy: 24 conceptual + 1 scenario), while its medium and hard banks support a richer variety of types. A single, difficulty-agnostic blueprint that targets multiple types will silently fail to honor its declared shape when applied to the easy tier of such a track — the runtime will either skip questions it cannot fill or pull the wrong type proportions.

**Required practice:**

1. **Declare difficulty-specific blueprint shapes.** Where a track's type distribution differs materially across difficulties, each difficulty tier must declare its own type targets in the benchmark selector — not inherit a shared shape that was calibrated for medium/hard.

2. **Match declared targets to actual bank composition.** Before shipping a blueprint change, verify the target counts against the live bank. A blueprint that requests 3 `scenario` questions at easy difficulty is invalid if the easy bank contains only 1 `scenario` question.

3. **Graceful degradation is a fallback, not a design substitute.** When a bank partition is genuinely exhausted at runtime (e.g., due to a pool reduction mid-session), the runtime may apply `type_fallback` degradation as defined in [`docs/features/mock.md`](../features/mock.md) — substituting the nearest compatible type rather than hard-failing the session. However, using `type_fallback` to paper over a blueprint that was never feasible is not acceptable; fix the blueprint instead.

4. **Feasibility check at catalog load (goal state).** The validator should confirm that each declared type target per difficulty is satisfiable by the available bank at that difficulty. Until the validator enforces this, blueprint authors are responsible for manual verification.

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

- Company filtering exists **only in the practice catalog** (free, all tiers, SQL — the `companies` tag in `SidebarNav`). **Mock has no company filter** — the once-stubbed Elite mock company filter was deliberately removed (see `docs/decisions/DECISIONS.md` 2026-06-09): it is a grind-market lever at odds with the reasoning-premium positioning, the per-company pool is too thin to survive mock's no-repeat freshness model, and it's SQL-only so it doesn't generalise.
- For any future targeting in mock, context / concept / interview-situation targeting is more defensible than company filters across tracks.

## Anti-patterns

- A 2-question timer dressed up as a benchmark
- Immediate right/wrong reveal that collapses the interview simulation
- Treating every track as if it should have the same mock shape
- Strong practice analytics with weak mock follow-through
- Feature gating that feels arbitrary rather than aligned to benchmark value

## Migration implications

The current Quick / Full / Custom system is an implementation starting point, not the final product contract. The modality rollout should separate benchmark mocks from drill-style sessions and make the benchmark rules explicit in backend responses, UI copy, and analytics.

---

## Chain atomicity contract (Phase 3)

Cross-reference: full chain mechanics live in [`docs/features/mock.md`](../features/mock.md#follow-up-chain-atomicity-interview-loop-only). The 8 universal `follow_up_dimension` values are defined in [`docs/concept-taxonomy.md`](../concept-taxonomy.md#the-8-universal-follow-up-dimensions-chain-pivots).

This section establishes the spec-level invariants the mock subsystem must enforce; the feature doc owns the user-facing contract.

**Chains appear exclusively in Interview Loop sessions.** Benchmark and custom drill sessions contain only standalone questions.

### Invariants

1. **A parent question + every entry in its `follow_ups[]` array forms one atomic mock unit.** Selection picks the chain as a unit or skips it. Splitting a chain across sessions is forbidden.
2. **Per-user, lifetime, at-most-once exposure.** Once a chain is selected for any Interview Loop session for a user, every member of the chain is consumed for that user and never reappears.
3. **Orphan child selection is forbidden.** Catalog load fails if any follow-up question is reachable by the selector without going through its parent.
4. **Consumption trigger:** `POST /api/mock/start`. Not first submit. Not finish.
5. **Reclaim window:** 120 seconds from `started_at`. `DELETE /api/mock/:id` within the window returns 204 AND reverts the quota counter AND reclaims the chain. After 120 s the chain is locked in.
6. **Pool exhaustion:** when no unconsumed chains remain for the requested track × difficulty for a user, Interview Loop returns **409 with `pool_exhausted: true`**. No soft fallback.

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
  "follow_up_dimension": "scale_pivot",          // one of the 8 universal dimensions
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
- Any `follow_up_dimension` value not in the 8-dimension registry (canonical set or accepted alias)

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
    session_id    INTEGER REFERENCES mock_sessions(id),  -- the session that consumed this chain
    reclaimed     BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, parent_id)
);

CREATE INDEX idx_mcc_user_active ON mock_chain_consumption (user_id) WHERE NOT reclaimed;
```

The `idx_mcc_user_active` partial index supports the hot path: "what parent_ids has this user already consumed?"

**Reclaim is a hard delete, not a flag-flip.** When a chain is reclaimed (discard within the 120 s window), the implementation **deletes the `mock_chain_consumption` row** (`discard_mock_session` in `backend/db.py`) — it does *not* set `reclaimed = TRUE` or null `session_id`. A reclaimed chain is therefore simply absent from the table and becomes selectable again. The `reclaimed` column + the `NOT reclaimed` filter in `get_consumed_chain_parent_ids` are a vestigial soft-delete affordance that the current delete-based path never exercises (a deleted row trivially satisfies `NOT reclaimed` by not existing). Matches `docs/features/mock.md` ("row deleted").

---

## Interview Loop mode

A new Elite-only mock mode that ships in Phase 3. Spec-level contract:

### Purpose

Mock today (benchmark + drills) measures readiness at a single point. Interview Loop simulates the iterative *shape* of a real interview — one anchor question followed by the interviewer's pivots, in sequence. The mode trains adaptability and pivot-handling rather than question-recognition.

### Composition rules

- **Eligibility:** Elite only. Free / Pro see "Unlock with Elite" copy on the mode card; cannot start a session.
- **Content:** Loop is **chain-only**. Eligible parents have `follow_ups[]` of length ≥ 1 (chain total length ≥ 2). Single-question parents belong to benchmark/drill modes.
- **Session shape:** exactly **1 chain** per session (parent + all follow-ups, 2–4 questions total).
- **Time:** 15 min × chain length. 2Q → 30 min · 3Q → 45 min · 4Q → 60 min. Computed at session start once the chain is selected.
- **Track:** any single track. Mixed is not available (chains are single-track by definition).
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
  "per_dimension_performance": {
    "scale_pivot":     {"attempted": 12, "correct": 9, "accuracy_pct": 75.0},
    "ambiguity_pivot": {"attempted": 8,  "correct": 3, "accuracy_pct": 37.5}
  }
}
```

`per_dimension_performance` is an **object keyed by the raw `follow_up_dimension` token**, each value `{attempted, correct, accuracy_pct}` (`accuracy_pct` is a percentage, **not** a 0–1 fraction). `chains_completed`, `weakest_dimension`, and `strongest_dimension` are **not** emitted — a consumer derives strongest/weakest from the map. This is the canonical shape; [`docs/features/mock.md`](../features/mock.md) matches it.

The dimension-level signal feeds the Elite dashboard's "What kinds of interviewer pivots break you?" card.

---

## Plan-gated pool sourcing reference

Spec-level summary. Full plan-tier matrix and rationale live in [`docs/features/mock.md`](../features/mock.md#plan-tier-matrix-canonical-sot).

- **Free** — Mock pool restricted to practice-pool questions (`mock_only != true`). Chains never eligible (Interview Loop is Elite only). Mode access: 1 `benchmark` per rolling 7 days, easy only. No `custom` mode. No `interview_loop`.
- **Pro** — Mock pool includes practice questions AND mock-only questions. No chains (Interview Loop is Elite only). Mode access: 3 `benchmark`/day + 3 `custom`/day, any difficulty.
- **Elite** — Same content access as Pro. Plus Interview Loop (chains), `focus_concepts` filter, deep analytics, debrief. Soft anti-abuse cap only (invisible in UI): 30 s burst / 5/hr / 20/day.

Pool-sourcing is enforced in the backend selector. UI must reflect plan state visibly (remaining-count chips on MockHub; upgrade modals when gated capability clicked).
