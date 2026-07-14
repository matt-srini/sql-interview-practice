# Mock Interview — Feature Reference

> **Canonical source of truth for the mock plan-tier matrix, chain atomicity, and Interview Loop contract.** Other docs (CLAUDE.md, pricing.md, north-star.md) reference this file rather than restating gates. Any change to mock gating must land here first.

## Overview

The mock interview system lets users practise under real interview conditions: a countdown timer, no mid-session solutions, and a post-session debrief. It is accessible to all authenticated users at `/mock` (requires login) and frames the surface explicitly as benchmarks, drills, and Interview Loop — never as "practice with a timer."

datathink's mock layer is a **benchmark, not a faster version of practice**. Every design decision below — atomicity, plan gates, mode separation — exists to defend the readiness signal.

---

## Session Modes (canonical, post-Phase-3)

| Mode | Time limit | Questions | Purpose |
|---|---|---|---|
| `benchmark` | Track-specific fixed shape | Track-specific fixed shape | The serious readiness signal. Fixed blueprint. Compares against historical baseline. |
| `custom` | 10–90 min (user-set) | 1–5 (user-set) | User-tuned to competency. Targeted practice under timed conditions. |
| `interview_loop` | 15 min × chain length | All questions in 1 chain (parent + all follow-ups) | Elite only. Simulates real interview depth: one anchor problem, then the interviewer's escalating pivots. |

**Legacy sessions** with mode `30min` (Sprint drill) and `60min` are read-only in history — they cannot be started new. Mode labels are normalized in the UI: `30min` → "Sprint drill", `60min` → "Full (legacy)", `custom` → "Custom drill", `benchmark` → "Benchmark", `interview_loop` → "Interview Loop".

Benchmark is fixed-shape per track. Mixed track benchmark and custom drill both require role selection (see [Mixed Benchmark Blueprints](#mixed-benchmark-blueprints-role-based) below). Interview Loop is single-track (chains are single-track by definition); selecting it while Mixed is chosen **auto-switches** to a single track rather than blocking (see [Interview Loop § Eligibility](#eligibility)).

Benchmark blueprints:

| Track | Benchmark shape | Time limit |
|---|---|---|
| SQL | 3 executable problems | 60 min |
| Python | 2 executable problems | 50 min |
| Pandas | 2 executable problems | 50 min |
| Statistics | 1 numerical + 2 conceptual | 45 min |
| PySpark | 6 code-adjacent reasoning prompts | 40 min |
| Data Engineering | 6 constructed reasoning prompts | 40 min |
| Data Modeling | 5 constructed reasoning prompts | 40 min |
| ML Fundamentals | 6 constructed reasoning prompts | 40 min |
| Experimentation | 6 constructed reasoning prompts | 40 min |
| Product Sense | 6 constructed reasoning prompts | 40 min |
| **Mixed — Data Analyst** | SQL (1) + Statistics (1) + Product Sense (1) + Pandas (1) + Python (1) | 69 min |
| **Mixed — Data Engineer** | Python (1) + SQL (1) + PySpark (1) + Data Engineering (1) + Data Modeling (1) | 70 min |
| **Mixed — Analytics Engineer** | SQL (1) + Data Modeling (1) + Pandas (1) + Python (1) | 55 min |
| **Mixed — Data Scientist** | ML Fundamentals (1) + Statistics (1) + Experimentation (1) + Product Sense (1) + Python (1) + Pandas (1) + SQL (1) | 93 min |

Benchmark composition follows track-specific type targets where the bank supports them. **The per-track per-difficulty blueprint must match the actual on-disk bank shape at that difficulty** — bank shape governs blueprint, not the other way around (see [`mock-benchmark-spec.md` § Blueprint feasibility](../specs/mock-benchmark-spec.md)). Runtime source of truth is `backend/routers/mock.py` (`_benchmark_type_targets`, `_pyspark_format_targets`, `difficulty_overrides`); the table below is the doc-side canonical render of that source. Any change to either the bank's per-difficulty type distribution or to a blueprint below must update both in the same commit and re-verify feasibility.

| Track | Easy shape | Medium shape | Hard shape |
|---|---|---|---|
| PySpark | `predict_output × 3 + conceptual × 2 + debug × 1` | `predict_output × 2 + debug × 2 + conceptual × 1 + scenario × 1` | `conceptual × 3 + scenario × 2 + predict_output × 1` |
| Data Engineering | `scenario × 3 + conceptual × 2 + debug × 1` | same | same |
| Data Modeling | `scenario × 1 + conceptual × 4` (difficulty override) | `scenario × 3 + conceptual × 2` | `scenario × 3 + conceptual × 2` |
| ML Fundamentals | `scenario × 2 + conceptual × 2 + predict_output × 1 + debug × 1` | same | same |
| Experimentation | `scenario × 2 + conceptual × 2 + predict_output × 1 + debug × 1` | `scenario × 4 + predict_output × 1 + debug × 1` (override) | `scenario × 3 + debug × 2 + predict_output × 1` (override) |
| Product Sense | `scenario × 4 + debug × 1 + predict_output × 1` | same | same |
| Statistics | `numerical × 1 + conceptual × 2` (subtype, not type) | same | same |

DM easy override is the canonical example of "bank shape governs blueprint": at easy difficulty the DM bank holds only 1 `scenario` question by design, so the blueprint declares the intended steady-state shape directly via `difficulty_overrides`. PySpark uses its own difficulty-aware sequencer (`_pyspark_format_targets`); the four other MCQ tracks use `_benchmark_type_targets` with optional `difficulty_overrides`. SQL / Python / Pandas benchmarks are executable and bypass type-targeting entirely.

Mixed benchmark slots draw from the named tracks with fresh-first per-track selection; if one track's easy pool is exhausted for the user, the slot falls back to the deepest-available other track in the role profile (`track_substituted: true` flag set in response). **Important:** Mixed benchmark per-track slots (including the Analytics Engineer Data Modeling slot) are NOT filtered by question type — they draw from the full difficulty-band pool for that track, which may include `debug` questions. The single-track type-targeting sequence (`_benchmark_type_targets`) is applied only when a single track is selected; it is bypassed in the Mixed benchmark path where each track fills its slot count via fresh-first pool sampling.

**Degradation contracts** — when a session cannot be composed to specification, the backend degrades silently and sets a flag in the `/start` response so the frontend can surface a notice if appropriate:

| Flag | Trigger | Behaviour |
|---|---|---|
| `track_substituted: true` | Mixed benchmark: a track's easy pool is exhausted for the user | Slot is filled from the deepest-available other track in the role profile |
| `focus_fallback: true` | Focus mode: fewer matching questions exist than the session needs | Remaining slots filled from the general pool (see Focus Mode section) |
| `pool_exhausted: true` | Interview Loop: no unconsumed chains remain for user × track × difficulty | 409 returned by default. The access map carries `replayable: true` plus top-level `fresh_loop_cells` (the user's still-unexhausted cells); the UI leads with a **redirect-first** "Fresh chains to try" rail and **demotes replay** to a quiet secondary (`POST /start` with `replay: true` → `is_replay: true`). No *silent* fallback — re-showing chains requires the explicit Replay action. See § Follow-up Chain Atomicity rule 6. |
| `type_fallback: true` | Single-track benchmark: a type partition in `_benchmark_type_targets` is exhausted in the available pool | `_sample_by_format` degrades to any remaining question in the difficulty band; declared type sequence is best-effort, not guaranteed |

`type_fallback` is not the steady-state for any track — declared blueprints should match the bank at each difficulty (see [`mock-benchmark-spec.md` § Blueprint feasibility](../specs/mock-benchmark-spec.md)). The flag fires only when an unexpected pool reduction (e.g., a user who has already seen most questions of a requested type in past mocks) leaves a slot unable to be filled by its declared type — `_sample_by_format` then degrades to any remaining question in the difficulty band. It does not indicate an error; it is a first-class composition outcome surfaced for the frontend to optionally annotate.

Custom drill validates server-side: `num_questions` must be 1–5, `time_minutes` must be 10–90.

---

## Mixed Benchmark Blueprints (role-based)

Mixed track always requires the user to select a **role** before starting any mock session (benchmark or custom drill). This scopes the question pool to the tracks that matter for that role.

**Four roles. The role→track pool is the canonical mapping — identical to `frontend/src/roleRegistry.js`, the Landing Page role selector, the dashboard role filter, and `backend/tracks.py` `_ROLE_TRACKS` (the mock pool is no longer a subset; it covers exactly the role's curriculum tracks — see [DECISIONS 2026-06-26](../decisions/DECISIONS.md)):**

| Role | Tracks in pool |
|---|---|
| Data Analyst | SQL, Statistics, Product Sense, Pandas, Python |
| Data Engineer | Python, SQL, PySpark, Data Engineering, Data Modeling |
| Analytics Engineer | SQL, Data Modeling, Pandas, Python |
| Data Scientist | ML Fundamentals, Statistics, Experimentation, Product Sense, Python, Pandas, SQL |

For **benchmark**, the role maps to a fixed blueprint (see table above).

For **custom drill**, the role defines the pool of tracks to draw from. The user sets total question count (1–5) and time (10–90 min). Questions are drawn fresh-first from the combined role-track pool — no per-track slot guarantees (that's the benchmark's job). Role is stored in `mock_sessions.role`.

**API:** `role` is a field on the `POST /api/mock/start` request body. Required when `track="mixed"`. Accepted values: `"data_analyst"`, `"data_engineer"`, `"analytics_engineer"`, `"data_scientist"`. Ignored (must be null) when `track` is a single track.

---

## Tracks and Difficulties

**Tracks:** SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation, Product Sense, Mixed (all tracks, role-gated)

**Mock-only question bank status:**

| Track | Dedicated mock bank? | Notes |
|---|---|---|
| SQL | ✅ | 196 mock-only questions (16 Interview Loop chains: 8 medium, 8 hard) |
| Python | ✅ | 103 mock-only questions |
| Pandas | ✅ | 132 mock-only questions |
| PySpark | ✅ | 150 mock-only questions |
| ML Fundamentals | ✅ | 143 mock-only questions |
| Experimentation | ✅ | 104 mock-only questions |
| Statistics | ✅ | 134 mock-only questions (7 hard Interview Loop chains — 7 parents + 14 follow-ups) |
| Data Modeling | ✅ | 97 mock-only questions |
| Data Engineering | ✅ | 110 mock-only questions |

Sessions for tracks without sufficient mock-only content draw from practice questions. Mixed sessions pool from all role-associated tracks.

**Difficulties:** Easy, Medium, Hard, Mixed (blend across difficulties)

---

## Plan-tier Matrix (canonical SoT)

This is the single source of truth. Any other doc that mentions mock plan gates must link here rather than restating.

### Quick view

| Capability | Free | Pro | Elite / Lifetime Elite |
|---|---|---|---|
| `benchmark` — easy | ✅ **1 per rolling 7 days** | ✅ 3/day | ✅ Unlimited† |
| `benchmark` — medium / hard | ❌ | ✅ 3/day | ✅ Unlimited† |
| `custom` — any difficulty | ❌ | ✅ 3/day | ✅ Unlimited† |
| `interview_loop` | ❌ | ❌ | ✅ Unlimited† |
| Mock-only question pool | ❌ — Free draws from practice pool only | ✅ | ✅ |
| Follow-up chains | ❌ (Interview Loop is Elite only) | ❌ (Interview Loop is Elite only) | ✅ via Interview Loop |
| `focus_concepts` filter | ❌ | ❌ | ✅ (benchmark + custom + Interview Loop) |
| Interview Loop mode | ❌ | ❌ | ✅ |
| Post-session score + per-Q solutions | ✅ | ✅ | ✅ |
| Detailed history + concept breakdown | ❌ | ✅ | ✅ |
| Cross-session trend, dimension analysis, readiness score, study plan, debrief | ❌ | ❌ | ✅ |
| Chain reclaim window (discard without consuming) | n/a | n/a | 2 min |

†Elite soft abuse cap (never displayed in UI unless triggered): minimum 30 s between `POST /api/mock/start` calls · 5 sessions per rolling 60 min · 20 sessions per rolling 24 h.

### Daily and weekly caps, explained

- **Free** — Exactly 1 `benchmark` per rolling 7 days (from `started_at` of the last completed or unconsumed benchmark), easy difficulty only, any single track or Mixed (with role). No `custom` mode at all. The weekly benchmark is the conversion demo: the free user experiences the full benchmark format once a week and feels what they would be upgrading to. No mock-only content.

- **Pro** — 3 benchmarks/day (any difficulty, any track/Mixed). 3 custom drills/day (any difficulty, any track/Mixed). Both counters are independent — spending benchmark quota doesn't affect custom quota and vice versa. Mock-only content pool unlocked. Daily caps reset at midnight UTC.

- **Elite** — All Pro features, plus Interview Loop, Focus, deep analytics, debrief. Counts displayed as "Unlimited" in UI. Backend enforces the soft anti-abuse cap silently.

**Why these shapes:**
- Free's weekly benchmark (not daily) is intentional: once a week creates scarcity that drives upgrade motivation without feeling punitive. A daily free benchmark would blunt the Pro value prop.
- Free getting no custom mode is deliberate. The daily habit hook lives in practice mode (streaks, progress). Mock for Free is the weekly readiness demo, not a daily drill tool.
- Pro's separate counters for benchmark and custom (3 + 3, not 3 combined) preserve user agency. A serious Pro user covering 4–5 tracks can benchmark one track and drill another on the same day without burning a shared counter.
- 6 sessions/day for Pro matches peak interview-week cadence without being obviously gameable.

### Sessions that do NOT count against quota

A session is consumed against the user's quota at `POST /api/mock/start`. Two exceptions:

1. **Discard within the 2-minute window** — `DELETE /api/mock/:id` called within 120 s of `started_at` deletes the session row, which naturally reverts all quota counters (weekly benchmark count, daily benchmark count, daily custom count). Misclicks and "wrong track" recoveries don't penalise the user. **Capped at `MAX_PENALTY_FREE_DISCARDS_PER_DAY` (3) per UTC day** (logged in `mock_discards`): because a discard refunds the rate-limit quota, an uncapped discard would let a user re-roll/preview question sets indefinitely. Once the daily cap is hit, the discard returns **429** and the session is **left active** — the user keeps going or ends it normally (it then counts as used). A blocked discard is **not** itself counted against the user.
2. **Chain reclaim** — when an Interview Loop session is discarded within the 2-minute window, the chain is reclaimed (row deleted from `mock_chain_consumption`) AND the daily quota is reverted. A misclick should never cost a quota slot + a chain simultaneously.

After 120 s the quota slot is locked in regardless of submission state.

### Pre-flight access check

`GET /api/mock/access?track=<track>&mode=<mode>` is called every time the track or mode selector changes. Returns per-difficulty `can_start`, `daily_limit`, `daily_used`, `weekly_limit`, `weekly_used` (Free benchmark), `needs_upgrade`, `block_copy` so the UI can render gate state without a round-trip on Start.

**`mode` param is required.** Access rules are mode-dependent:
- `mode=benchmark`: Free → easy only (`medium`/`hard`/`mixed` → `plan_locked` — `mixed` is gated too, since it draws medium/hard questions); Free weekly limit check; Pro → difficulty unrestricted; daily cap per plan.
- `mode=custom`: Free → `plan_locked` entirely for all difficulties; Pro/Elite → daily cap check.
- `mode=interview_loop`: Free/Pro → `plan_locked`; Elite → **per-difficulty chain-availability check**. Interview Loop requires the user to choose **medium or hard** (easy is never offered — no chains exist at easy difficulty). The access endpoint returns a per-difficulty map `access[medium|hard]`, each entry carrying `{ can_start, block_reason, escalates }`. Difficulties with no chains in the bank return `can_start: false, block_reason: "no_chains"` (the UI greys these per the standard grey+message gating convention — see [DECISIONS 2026-06-16](../decisions/DECISIONS.md)). `escalates: true` is set for Python-medium, SQL-medium, and Data-Modeling-medium (their chains escalate to hard follow-ups); the UI displays these as "medium → hard". Escalation is **uniform per cell** — every chain in a (track, difficulty) cell escalates or none does, enforced by `validate_content.py::_validate_loop_escalation_uniformity` (so the single cell-level badge is always honest; revisit deliberately if a track ever needs mixed escalation). Track-scoped availability rules: **Python → medium only** (hard has no chains); **ML Fundamentals and Experimentation → hard only** (no medium chains); **SQL, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, Product Sense → medium and hard** (SQL-medium and Data-Modeling-medium escalate). Availability is derived from the question files (`backend/routers/mock.py` `_chain_parents_for` / `_interview_loop_access`), never hardcoded in the UI. The Start button is gated on the selected difficulty's `can_start`. When a difficulty entry is `pool_exhausted` (user consumed all chains at that difficulty), the entry returns `can_start: false, block_reason: "pool_exhausted", replayable: true` (and the response carries top-level `fresh_loop_cells`); the session-brief rail shows a positive completion message — *"You've completed every {difficulty} Interview Loop chain for this track — nice work."* — and leads with a **redirect-first** "Fresh chains to try" rail of the user's unexhausted cells, demoting consent-gated **Replay** to a quiet secondary link (see § Follow-up Chain Atomicity rule 6). *(Supersedes the 2026-06-15 "no difficulty selector" decision — see [DECISIONS 2026-06-16](../decisions/DECISIONS.md); replay added [2026-06-19](../decisions/DECISIONS.md), redirect-first [2026-06-22](../decisions/DECISIONS.md).)*

### Surface in the UI

Plan-tier rules must be visible to the user, not buried in account settings. Required surfaces:
- **MockHub** — remaining daily/weekly count under the mode selector ("Free · 1 benchmark available this week" / "Pro · 2 of 3 benchmarks used today").
- **Plan upgrade modal** — triggered when a gated capability is clicked. Lists what unlocks at each tier.
- **Interview Loop mode card** — Elite badge; Free/Pro users see an "Unlock with Elite" overlay.
- **Chain indicator** — when a follow-up question loads in Interview Loop, a pivot card shows the `follow_up_dimension` label so the user understands the interviewer pivot framing is intentional.
- **Role selector** — appears on MockHub when Mixed track is selected (both benchmark and custom drill). Required before Start is active.
- **Focus mode** (Elite) — non-Elite users see a greyed-but-clickable card; clicking reveals "Focus mode is an Elite feature." + an Unlock-with-Elite CTA. The 1–3 concept cap follows the same rule: the extra pills grey but stay clickable, and a click past the cap shows "You can focus on up to 3 concepts at a time."

**Gating convention (one pattern, everywhere).** Every gated control on MockHub is **greyed but stays clickable** and **surfaces its reason on interaction** — never a hard-`disabled`/hidden dead-end. This covers the mode cards (plan locks), the Mixed track pill (role required / single-track for Interview Loop), the difficulty pills (plan locks), and Focus mode (Elite lock + concept cap). Rationale and the rejected alternatives (hard-disable, hide) are in [DECISIONS 2026-06-16](../decisions/DECISIONS.md).

> **Caveat — defaults must not fight the convention.** A default/auto-select effect (e.g. picking a valid difficulty on entry to Interview Loop) must key on *context* — mode, track, access-load — and **never on the selection value itself**. If the value it corrects is one of its own effect dependencies, the effect re-fires on the user's *own click* and bounces them off a gated control before its message can render, silently turning a grey-clickable pill back into a hard block. (This regressed the Interview Loop difficulty selector and was reverted: the auto-select effect is keyed on `[mode, accessState]`, not `difficulty`, so a clicked blocked difficulty stays selected and shows its message.)

---

## Follow-up Chain Atomicity (Interview Loop only)

**Chains appear exclusively in Interview Loop sessions.** Benchmark and custom drill sessions contain only standalone questions — no `follow_up_id` injection, no dynamic follow-up insertion.

Follow-up chains simulate real interviewer pivots — the moment a senior interviewer says "now exclude refunded orders" or "what if the dataset were 10× larger?" Every chain is anchored to a parent question and travels as an atomic unit. Each follow-up escalates exactly one [dimension](../concept-taxonomy.md#the-8-universal-follow-up-dimensions-chain-pivots); they never introduce an unseen concept.

### The atomicity rule (locked decision)

**A parent question and all entries in its `follow_ups[]` form an atomic mock unit. A user sees the entire chain together — never split, never partially. Zero or all.**

This rule applies exclusively to Interview Loop sessions. The atomicity (the chain travels whole) is locked. **Uniqueness is the default, not an absolute:** each chain is drawn once and then excluded from future sessions — until the user has completed *every* chain at that (track, difficulty), at which point they may **explicitly consent to replay** (see Selection rule 6). Replay is never silent: it requires the `replay: true` flag set by a Replay button on the exhausted state. This mirrors what benchmark/custom already do — they recycle questions fresh-first once the fresh pool is spent, and those repeats already count toward readiness — so a *consented* loop replay is strictly more honest than the silent recycling elsewhere. See [DECISIONS 2026-06-19](../decisions/DECISIONS.md).

### Schema

On the **parent** question JSON (always `mock_only: true`):
```json
"follow_ups": [<id1>, <id2>, <id3>]   // ordered chain; max length 3 (parent + up to 3 follow-ups = 4 total)
```

On each **follow-up** question JSON:
```json
"mock_only": true,
"parent_id": <parent_id>,             // back-ref, validated at catalog load
"follow_up_dimension": "scale_pivot"  // one of the 8 universal dimensions below
```

### Selection rules

1. **Within a session:** Interview Loop always draws exactly 1 chain per session. The selector picks a fresh chain (parent not in the user's `mock_chain_consumption`), then loads parent + all follow-ups in `follow_ups[]` order.
2. **Across sessions:** once a chain is selected for any session, the entire chain is marked consumed for that user and does not reappear in future Interview Loop sessions — unless the user, having completed every chain at that (track, difficulty), explicitly opts into replay (rule 6).
3. **Children are never directly selectable.** They enter sessions only via their parent. Orphan selection is forbidden by the validator at catalog load.
4. **Consumption trigger:** chain is marked consumed in `mock_chain_consumption` at **session start** (`POST /api/mock/start`), not at finish. Prevents peek-and-bail abuse.
5. **Reclaim window:** within 2 minutes of session start, `DELETE /api/mock/<id>` reclaims the chain (deletes the `mock_chain_consumption` row). After 2 min, consumption is final regardless of whether the user submitted anything.
6. **Pool exhaustion → consent-gated replay:** when no unconsumed chains remain for a user × track × difficulty, `POST /start` returns **409** with `pool_exhausted: true` and `replayable: true` *by default*. The exhausted state is framed as a completion (not a dead-end) and is **redirect-first** (DECISIONS 2026-06-22): the access response carries `fresh_loop_cells` — the user's still-unexhausted Loop cells (requested track first, capped 4) — which the rail renders as a "Fresh chains to try" set of one-tap cell buttons (each switches the lobby to that cell). **Replay is demoted** to a quiet "Or replay these chains →" secondary link; it re-issues `POST /start` with `replay: true`; `_select_chain` then re-draws a completed chain (fresh-first among the consumed set) and returns `is_replay: true`, which surfaces an in-session "you're revisiting a completed chain" notice. When the user has exhausted *every* cell, `fresh_loop_cells` is empty and replay becomes the only CTA (the sole remaining non-dead-end). **No *silent* fallback** — a repeat only ever happens on the explicit Replay action. (Supersedes the former hard "no soft fallback / dilutes the readiness signal" lockout — the readiness *score* is a separate aggregate that Interview Loop doesn't feed, and the 30-pt mock booster it does feed already counts recycled benchmark/custom repeats; see [DECISIONS 2026-06-19](../decisions/DECISIONS.md).)

### Why session-start, not finish-of-first-question?

- Consume at `POST /start` (chosen) — simple, prevents peek-and-bail, 2-min reclaim is the safety valve.
- Consume at first submission — allows users to read all questions and never submit, enabling infinite re-rolls.
- Consume at finish — same abuse vector as above.

### The 8 universal follow-up dimensions

Every follow-up escalates exactly one dimension. Full taxonomy in `docs/concept-taxonomy.md`. The `_pivot`-less spelling (e.g. `data_quality`) is an accepted alias, normalised by `backend/follow_up_dimensions.py`.

| Dimension | What it tests | Cross-track example |
|---|---|---|
| `scale_pivot` | How does this change at 10× / 100× / petabyte scale? | SQL: "now the orders table has 10B rows"; PySpark: "shuffle strategy must change"; DE: "small-file problem emerges" |
| `business_rule_pivot` | What changes when the business definition shifts? | SQL: "exclude refunded orders"; Stats: "now the metric definition changes"; ML: "label definition shifts" |
| `data_quality_pivot` | How does the answer adapt to dirty data? | SQL: "duplicates in this table"; PySpark: "late-arriving events"; DE: "schema drift upstream" |
| `edge_case_pivot` | What about empty windows, ties, missing days? | SQL: "what if a user has zero orders"; Stats: "small-sample inference"; ML: "rare class" |
| `performance_pivot` | How would you reduce cost/latency? | SQL: "reduce repeated scans"; PySpark: "minimise shuffle"; DE: "cost optimisation" |
| `ambiguity_pivot` | The business question is unclear — what would you ask? | Cross-track: "what counts as 'active'?"; Exp: "is this even testable?" |
| `stakeholder_pivot` | A stakeholder wants a different answer — how do you respond? | "Exec wants weekly not monthly"; "PM wants simpler explanation"; "Finance wants attribution" |
| `abstraction_pivot` | Step up a level — generalise from the instance, or reframe under a different lens | Stats: "frequentist CI → Bayesian credible interval on the same data"; "spot the collider → classify any variable's causal role"; SQL: "make it work for any N tiers, not just 3" |

### Authoring rules for chains (enforced by `validate_content.py`)

- Chain total length: 2 minimum (parent + 1 follow-up), 4 maximum (parent + 3 follow-ups).
- **Each follow-up must use a different `follow_up_dimension` than the previous follow-up.**
- A child cannot have its own `follow_ups[]` (no nested chains).
- A child can only appear in one parent's `follow_ups[]` (no shared children).
- All chain questions must share the same `track` and same-or-escalating `difficulty`.

### Persistence model

```sql
CREATE TABLE mock_chain_consumption (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id   INTEGER NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id  BIGINT REFERENCES mock_sessions(id) ON DELETE SET NULL,
    reclaimed   BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (user_id, parent_id)
);

CREATE INDEX idx_mcc_user_active ON mock_chain_consumption (user_id) WHERE NOT reclaimed;
```

The composite primary key `(user_id, parent_id)` prevents double-consumption at the database level. The partial index on `NOT reclaimed` supports the hot path: "what chains has this user already consumed?"

### `mock_session_questions` additions

```sql
ALTER TABLE mock_session_questions ADD COLUMN follow_up_dimension TEXT;
```

Populated at session creation for Interview Loop sessions (denormalised from the question's `follow_up_dimension` field). Null for benchmark and custom sessions. Enables per-dimension performance analytics without re-joining question JSON at analytics time.

### `mock_sessions` additions

```sql
ALTER TABLE mock_sessions ADD COLUMN role TEXT;
ALTER TABLE mock_sessions ADD COLUMN loop_escalated BOOLEAN;
```

`role` — nullable. Set only for `track="mixed"` sessions. Values: `"data_analyst"`, `"data_engineer"`, `"analytics_engineer"`, `"data_scientist"`.

`loop_escalated` — nullable. Set only for `mode="interview_loop"` sessions at session creation from the drawn chain's actual follow-up difficulties. `true` if the chain escalates to a harder difficulty (e.g. medium→hard); `false` if all questions stay at the same difficulty; `NULL` for legacy sessions predating migration `20260624_000001` (those fall back to the cell-level flag). Read by history and the active-session badge to show what the session actually did; the pre-start badge uses the cell-level `_loop_difficulty_escalates` flag instead (no chain drawn yet).

---

## Interview Loop Mode (Elite only)

### What it is

The user picks a track and optionally a focus area, and the system composes a session of **exactly 1 chain** — parent question plus all its follow-ups in order. Within the chain the user experiences:

1. The parent question (standard mock UX)
2. After submitting the parent, an **interviewer-pivot card** appears inline showing the **human-readable dimension label** (e.g. "Business rules") and a **dimension-specific interviewer framing line** drawn from the [8-dimension taxonomy](../concept-taxonomy.md#the-8-universal-follow-up-dimensions-chain-pivots) (e.g. for `business_rule_pivot`: *"A business rule just changed. Adapt your solution to the new requirement."*). The pivot card always appears, regardless of whether the parent answer was correct — real interviews continue either way. User dismisses the card to advance.
3. The follow-up question, building on the same dataset / problem / context
4. Repeat for each follow-up in the chain

This mode simulates the real interview shape — interviewers don't ask 5 unrelated questions; they ask one question and iterate on it. Loop trains adaptability, not memorisation.

### Eligibility

- **Plan:** Elite only. Free/Pro see "Unlock with Elite" copy on the Interview Loop mode card; cannot start a session.
- **Content:** Only parents with `follow_ups[]` length ≥ 1 are eligible.
- **Track:** Any single track. Mixed is not supported (chains are single-track by definition). The Interview Loop mode card is **not disabled** on Mixed — selecting it **auto-switches** the track to a single track (the selected role's first, else SQL) and shows an indigo note stating the constraint — *"Interview Loop runs on one track — can't choose Mixed."* (it names the constraint rather than the switched-to track, which the Track selector already shows), so there's no unexplained dead-end.
- **Difficulty:** **Per-track, medium or hard.** The user picks medium or hard in the MockHub difficulty step (easy is never offered). Track-scoped availability: **Python → medium only** (escalates to hard follow-ups; displayed as "medium → hard"); **ML Fundamentals and Experimentation → hard only**; **SQL, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, Product Sense → medium and hard** (SQL-medium and Data-Modeling-medium also escalate to hard follow-ups, displayed as "medium → hard"). Difficulties with no chains in the bank are greyed with a reason message per the standard gating convention. The session stores the chosen difficulty (`mock_sessions.difficulty`); for **history and the active session**, the difficulty badge reads `escalates` from the **stored per-session `mock_sessions.loop_escalated`** column (set at session creation from the chain's actual follow-up difficulties; cell-flag fallback if NULL), so a past session reflects what it actually did — escalating difficulties are shown as "medium → hard" via `formatLoopDifficulty(difficulty, escalates)` in `frontend/src/mockModeConfig.js`. The **pre-start** badge remains the cell-level `_loop_difficulty_escalates` flag (no chain drawn yet). *(Supersedes the 2026-06-15 "no difficulty" decision — see [DECISIONS 2026-06-16](../decisions/DECISIONS.md).)*
- **Atomicity:** all chain atomicity rules apply. Each session consumes 1 full chain; once consumed, it's gone from that user's pool.

### Session shape

| Parameter | Value |
|---|---|
| Chains per session | Exactly **1** |
| Total questions | Chain length (parent + all follow-ups) — 2 to 4 questions |
| Time limit | **15 min × chain length** — computed at session start once chain is selected |
| Mid-session reveal | None (benchmark invariants apply) |

Time examples: 2Q chain → 30 min · 3Q chain → 45 min · 4Q chain → 60 min.

The user does **not** see total question count up front (preserves the dialogue-shape simulation). A per-question progress indicator appears as questions are completed.

### Chain selection algorithm

1. Load all `mock_only` parents with non-empty `follow_ups[]` for the track at the **chosen difficulty** (`_chain_parents_for(track, difficulty)`). Only chains matching the user-selected difficulty are eligible — no cross-difficulty mixing.
2. Exclude chains already consumed by this user (present in `mock_chain_consumption` with `reclaimed=false`).
3. If `focus_concepts` is set, filter parents whose concept tags match at least one focus concept. Focus applies to the **parent only** — the full chain travels regardless of whether follow-ups carry the focus concept.
4. Select 1 chain fresh-first (prefer chains not yet seen by this user at all). If all eligible chains have been seen in discarded sessions (reclaimed), pick from reclaimed pool.
5. Mark chain consumed in `mock_chain_consumption` atomically with session creation.
6. Load parent + all follow-up questions in `follow_ups[]` order. Denormalise `follow_up_dimension` into `mock_session_questions` for each follow-up row.
7. If no eligible chains exist, the failure is split by cause:
   - **The track has no chains at all in the content** (permanent — not the case for any current track): `start_session` catches this *before* `_select_chain` and returns **403**.
   - **Chains existed but this user consumed them all at this difficulty** (dynamic): `_select_chain` returns **409** with `pool_exhausted: true` and `replayable: true` *unless* `replay: true` was passed. The access map surfaces this as `access[difficulty].pool_exhausted` + `replayable` plus top-level `fresh_loop_cells`, so the UI disables the primary Start, frames the state as a completion, **leads with a "Fresh chains to try" redirect rail**, and demotes **Replay** to a secondary link (re-issues `/start` with `replay: true` — see Selection rule 6).

### Pivot card UX (frontend specification)

- **Trigger:** displayed after the user submits any non-final question in the chain (i.e. all except the last follow-up).
- **Content:** the human-readable **dimension label** + a **dimension-specific interviewer framing line**, both keyed off `follow_up_dimension` via the shared map in `frontend/src/mockModeConfig.js` (`dimensionLabel()` / `dimensionBlurb()`). **Not** the question's `framing` field — `framing` carries the question *type* token (e.g. `"scenario"`), not interviewer narrative; the label+blurb come from the [8-dimension taxonomy](../concept-taxonomy.md#the-8-universal-follow-up-dimensions-chain-pivots). Unknown/drifted tokens are humanized (never shown raw).
- **Form:** inline card in MockSession, not a modal. Replaces the "Next question →" button. User must explicitly dismiss it to advance. Cannot be skipped.
- **Wrong answer:** pivot card still appears. No answer reveal. The debrief surfaces the miss post-session.
- **Styling:** visually distinct from the question area — use an interviewer-voice tone. The dimension label renders as the card heading.
- **Post-mortem:** the session summary marks each follow-up question with a "↩ Follow-up · {dimension label}" chip (requires `is_follow_up` persisted on `mock_session_questions` — see audit C5). Per-dimension analytics in the lobby use the same human-readable labels (never the raw token).

### Mode interaction with focus

If `focus_concepts` is enabled together with Interview Loop, the focus filter applies to the **parent's** concept tags only. The full chain travels regardless of whether follow-ups carry the focus concept — that's the iterative-pivot point.

### Analytics

After completion, Interview Loop sessions contribute a new analytics dimension in the Elite dashboard: **performance by follow-up dimension**.

`GET /api/mock/analytics` Elite payload gains:

```json
"loop_summary": {
  "sessions": <int>,
  "per_dimension_performance": {
    "scale_pivot":     {"attempted": 12, "correct": 9, "accuracy_pct": 75.0},
    "ambiguity_pivot": {"attempted": 8,  "correct": 3, "accuracy_pct": 37.5}
  }
}
```

`per_dimension_performance` is an **object keyed by the raw `follow_up_dimension` token** (the frontend humanises each key for display via `dimensionLabel()` in `mockModeConfig.js`); each value carries `attempted`, `correct`, `accuracy_pct`. Populated only when Interview Loop sessions exist for the user. Computed from `mock_session_questions.follow_up_dimension` joined against submission results. Only returned to Elite users. (Strongest/weakest dimension is not emitted — a consumer derives it from the map; `chains_completed` is likewise not emitted.)

---

## Interview Loop positioning (the earned capstone)

The Interview Loop is framed across the product as the **culminating "real interview" test** — the deliberate readiness check a user reaches for *after* benchmarking (diagnose) and drilling (fix weak spots), not a daily drill tool. The arc is **Benchmark → Drill → Interview Loop**.

**This is framing + recommendation only — never a hard prerequisite.** A user who knows what they want can always start a Loop directly. Hard-gating a paid Elite feature behind "you must benchmark first" would be artificial friction (the *serving-a-metric-not-the-user* anti-pattern). Every nudge below is suggestive, dismissible, and never disables the Start control. The scarcity stays *honest* (it reflects the genuinely deep, finite, expensive-to-author chain pools and the readiness-test purpose), never *manufactured*. Operator direction 2026-06-19 (TODO P3), refined to framing-not-gate; see [DECISIONS 2026-06-21](../decisions/DECISIONS.md).

### The `loop_ready` signal (canonical)

`GET /api/dashboard/insights` → `readiness_scores[track].loop_ready` (bool). Computed in `_compute_readiness_scores` (`backend/routers/insights.py`). Elite-only by construction (readiness scores are Elite-only). True **iff both** hold:

1. `readiness_scores[track].score >= 65` — the "Getting there" band or better (the holistic coverage + first-time-solve-quality + mock signal), **and**
2. the user has **≥1 completed *direct* benchmark on that track** in mock history. Mixed/role benchmarks are **deliberately excluded** — a role-mix benchmark is not a single track's readiness signal.

`loop_ready` never feeds any score; it is a pure presentation flag.

### Where it surfaces

| Surface | File | Trigger | Copy intent |
|---|---|---|---|
| Dashboard readiness chip → "Ready for a Loop →" CTA | `ProgressDashboard.js` | `readiness_scores[track].loop_ready` (holistic) | Persistent "you're ready" reminder; deep-links `/mock` with an `interview_loop` hard preset + honest note. Takes precedence over the `mock_limited` "Mock to level up" nudge (a Loop *is* a timed mock). |
| Mock post-mortem footer → "Try an Interview Loop →" primary CTA | `MockSession.js` | Strong single-track **benchmark this session** (≥60%) **and** holistic `readiness_scores[track].score >= 65` | Strike-while-hot: the just-completed benchmark is the most contextual readiness evidence. Reads the *score* (not `loop_ready`) so the benchmark-count cache lag can't hide the capstone the moment a practice-ready user aces their first benchmark. Demotes "Plan follow-up drill" to secondary. |
| Hero + "How it works" modal | `MockHub.js` | always | Sequences Benchmark → Drill → Interview Loop; the modal states explicitly "a recommendation, not a gate — start any mode directly." |
| Loop mode card + Loop setup descriptor | `mockModeConfig.js` | always | Shifts from *what it is* to *when to reach for it* ("Your capstone — best after a benchmark and a drill or two"). |
| Loop setup rail → "Suggested first" soft nudge | `MockHub.js` (`loopTrackBenchmarked`) | Elite + Loop selected + **no benchmark on the selected track** + rail not in a blocked/completion state | "Run a quick {track} benchmark first … You can start it now either way." Never blocks Start. |

**Two honest triggers, by design.** The dashboard uses the holistic `loop_ready` (the durable, aggregate readiness signal — right for a persistent surface). The post-mortem uses *this session's strong benchmark + a ≥65 score floor* (the immediate, contextual signal — right for the moment just after a benchmark). Both are honest-by-construction and Elite-scoped; they are complementary signals at two moments, not a single trigger restated in two places.

---

## Focus Mode (Elite only)

Elite users can enable **Focus mode** on MockHub. When active, a concept pill multi-select appears (1–3 concepts max). The session pool is filtered to questions tagged with the selected concepts.

**Fallback:** if fewer matching questions exist than needed, the session fills remaining slots from the general pool and sets `focus_fallback: true` in the `/start` response. The session page shows a subtle notice when this happens.

**Request:** `focus_concepts: ["WINDOW FUNCTIONS", "COHORT RETENTION"]` in the `POST /api/mock/start` body.

Focus is available on all three modes (benchmark, custom, interview_loop).

---

## Mock History Analytics (Elite only)

`GET /api/mock/analytics` returns aggregated stats over the last 50 completed sessions.

- `total_sessions`, `sessions_last_30d`
- `benchmark_summary`: score/time/trend/breakdown for benchmark sessions only
- `drill_summary`: score/time/trend/breakdown for custom drill sessions only
- `loop_summary`: per-dimension performance for interview_loop sessions only (see above)
- `mode_breakdown`: counts for `benchmark`, `custom`, `interview_loop`
- `top_concepts`: top 5 by attempt count (with accuracy)
- `weak_concepts`: worst 3 concepts by accuracy (≥3 attempts, <60%). Concept resolution uses the shared `_CONCEPTS_LOOKUP` (`routers/insights.py`), which spans practice **and mock-only** questions — so the questions a mock actually serves contribute to its own weak-concept readout (the lookup was practice-only before 2026-06-16, which silently dropped every mock-only question from this analysis).

Returns 403 for non-Elite plans.

**Not part of this payload:** `readiness_scores` and `study_plan` are **not** returned by `/api/mock/analytics`. They are computed by `GET /api/dashboard/insights` (Elite-only — see [`docs/features/dashboard.md`](dashboard.md)) and surfaced in the mock **post-mortem** (the session-summary view fetches `/dashboard/insights` directly). The plan-tier matrix row above ("Cross-session trend, dimension analysis, readiness score, study plan, debrief") groups them by *tier entitlement*, not by endpoint: trend + dimension analysis come from this endpoint, the **debrief** comes from the `/finish` payload, and readiness score + study plan come from dashboard insights.

---

## Daily Cap Implementation Notes (backend)

The current difficulty-based counter system (`MOCK_DAILY_LIMITS` keyed by plan × difficulty, `get_daily_mock_usage()` counting by difficulty) must be replaced with **mode-based counters**.

**New DB functions required:**

```python
async def get_daily_benchmark_usage(user_id: str) -> int:
    """Count benchmark sessions started today (UTC). Used for Pro 3/day cap."""

async def get_daily_custom_usage(user_id: str) -> int:
    """Count custom sessions started today (UTC). Used for Pro 3/day cap."""

async def get_weekly_benchmark_usage(user_id: str) -> int:
    """Count benchmark sessions started in the last 7 rolling days. Used for Free 1/7-day cap."""
```

Each function queries `mock_sessions` filtered by `mode` and `started_at` range. Since `discard_mock_session` deletes the session row entirely, discarded sessions are automatically excluded from counts — no special handling needed.

**`compute_mock_access()` signature change:**

Add `mode: str` parameter. Access logic becomes mode-dependent:

```
benchmark + free + difficulty=easy  → weekly cap check (1/7 days)
benchmark + free + difficulty=medium or hard → plan_locked
benchmark + pro                     → daily benchmark cap (3/day)
benchmark + elite                   → soft cap only
custom + free                       → plan_locked entirely
custom + pro                        → daily custom cap (3/day)
custom + elite                      → soft cap only
interview_loop + free               → plan_locked
interview_loop + pro                → plan_locked
interview_loop + elite              → soft cap only
```

**`GET /api/mock/access` endpoint:**

Must accept `mode` query param in addition to `track`. Returns `weekly_benchmark_used` and `weekly_benchmark_limit: 1` for Free plan + benchmark mode.

---

## Active Session (`/mock/:id`)

- **Session framing card** — left panel makes session type explicit: benchmark shows the fixed-shape blueprint framing; custom drill shows flexible follow-up framing; Interview Loop shows "Interview simulation — 1 chain, [N] questions" framing.
- **Countdown timer** — colour-coded: normal → amber (<10 min) → red (<3 min). Browser tab title updates with remaining time.
- **Auto-finish** when timer reaches 0.
- **Question navigation** — numbered dot tabs, each shows solved/unsolved state.
- **Run code** — SQL, Python, Pandas, and Statistics (numerical) support running code mid-session, **as many times as you like** before the one-shot submit. PySpark and MCQ tracks do not. Run goes to the **mock-scoped** `POST /api/mock/:id/run` (not the practice `/{track}/run-code`): it is gated on **session membership**, not the practice unlock state, so mock-only questions (every Interview Loop chain) run instead of returning a spurious "locked" error. It executes against **public** test cases only — no solution, no progress recorded. **Output hierarchy (test-case tracks — Python, Statistics numerical):** each test-case row carries its own `stdout` in the context of that row's input; there is **no separate aggregate output panel**, because the aggregate is exactly the join of those per-case outputs (harness `print_output`) and duplicating it below the results is noise. `print()` remains a first-class debugging channel — it just lands inside the relevant test-case row, not a competing block. Pandas and SQL keep a standalone output/results panel (they render a result table, not per-case rows, so it is the only home for stdout).
- **SQL schema viewer** — Description / Schema toggle in left panel.
- **Hints and concept tags** visible on each question.
- **Submit per question** — each question allows exactly one real submission. A second submit returns 409. Blank code or missing MCQ selection returns 422 without consuming the slot. **The verdict shown is mode-dependent (canonical: [`mock-benchmark-spec.md` §Mid-session submit response](../specs/mock-benchmark-spec.md)):**
  - **Custom drill** — reveals the **verdict only** (right/wrong): the submit button locks to `✓ Solved` or `✗ Submitted`, the dot fills for a correct solve, and the pre-closure modal shows solved/unsolved. It does **not** reveal the correct answer, the MCQ correct index, hidden-test results, or the explanation — those stay for the debrief. Backend returns a **verdict-only** response body: `{"correct": <bool>}` (plus `"error"` if present) — answer-key fields (`public_results`, `hidden_summary`, `expected_result`, `user_result`, `feedback`) are stripped and never sent in the custom-submit HTTP response (`routers/mock.py` `submit_answer`).
  - **Benchmark / Interview Loop** — reveals **nothing but acceptance**: the button locks to `✓ Submitted` regardless of correctness, dots reflect *submitted* state only, and the backend returns a bare `{"submitted": True}`. No verdict, no solution, no answer key mid-session.
- **Interview Loop pivot card** — after submitting any non-final chain question, an interviewer-pivot card appears inline (see [Pivot card UX](#pivot-card-ux-frontend-specification) above). User must dismiss to advance.
- **"Next question →"** button after submit on non-last questions (benchmark/custom). For Interview Loop, this is replaced by the pivot card until dismissed.
- **Exit confirmation** — clicking Exit or End Session shows a confirm dialog.
- **Early-exit discard** — the server honours `DELETE /api/mock/:id` within **120 s** of `started_at` (reverts all quota counters; Interview Loop chains are reclaimed). There is **no always-on countdown chip and no "Discard & re-roll" button** in the topbar. Instead, clicking Exit/End within the **first 60 s and before any run or submit** opens a discard prompt — *"Barely started — want to keep this?"* — with **Keep going / End normally / Discard session** (Interview Loop adds *"This chain will return to your pool."*). After 60 s, or once the user has run or submitted anything, Exit shows the normal pre-submission review modal instead. (The UI's 60 s prompt window is intentionally narrower than the server's 120 s safety margin — the prompt targets genuine misclicks, while the server stays lenient.) **Daily cap:** after 3 penalty-free discards in a UTC day the server returns 429 and the discard prompt shows the limit message with the "Discard session" button hidden — only "Keep going" / "End normally" remain, and the session stays active.
- **Active session guard** — 409 from `POST /api/mock/start` if user has an active session. Response body includes existing `session_id`, `track`, `difficulty`, `mode`.
- **Session reload recovery** — navigating back to `/mock/:id` restores state from server. Remaining time recomputed from `started_at`.
- **Mobile** — collapsible left panel.

---

## Post-session Summary

Shown after `POST /api/mock/:id/finish`:

- **Mode-aware framing** — benchmark vs custom drill vs Interview Loop, session shape restated.
- **Score headline** — `X/Y correct`.
- **(Pro+)** Baseline comparison — `X% above/below your historical accuracy`.
- **Time used** — `MM:SS used of MM:SS limit`.
- **Per-question breakdown** — solved/unsolved badge, time spent, expandable "See solution" toggle (reference solution + explanation, revealed only after finish).
- **(Pro+) Concept breakdown** — every concept in the session with `correct / attempted`, sorted worst-first. Each **weak** concept (accuracy < 100%) carries its own `Drill →` link to `/practice/{track}?drill={concept}` (the [concept drill](dashboard.md)), so the user chooses which weak concept to attack. Concept-only — no learning-path link (paths live on the dashboard). Replaces the former single aggregate "Drill weak concepts →" button, which deep-linked just one arbitrarily-chosen concept. On Elite summaries the debrief's NEXT STEP concept is floated to the **top row** (via the returned `priority_concept`/`priority_track`), so the table's first row always agrees with NEXT STEP.
- **(Elite) Interview Loop: per-dimension breakdown** — for Loop sessions, shows performance by `follow_up_dimension` (e.g. "Strong: scale pivot · Weak: ambiguity pivot").
- **(Elite) Session debrief** — coaching narrative panel (template-based, no external AI). Headline + up to 3 pattern observations + a **priority action** + historical context if concept matches a known weak area. For a weak concept the priority action's next-step CTA is the **concept drill** (`/practice/{track}?drill={concept}`, via the `priority_concept`/`priority_track` fields) — concept-only, with **no learning-path link**. Path recommendations are a dashboard-only affordance (the dashboard keeps the concept-primary / path-secondary pairing — see [dashboard.md](dashboard.md)). The featured concept is the session's weakest, chosen by **most session misses (attempts − correct) → lowest session accuracy → known cross-session weakness (≥3 past attempts, <60%, family-aware) → concept name** — so a better-evidenced gap (e.g. 1/5) outranks a lone careless miss (0/1), a recurring cross-session gap wins an otherwise-even tie, and full ties resolve deterministically by name (not by implicit question order). The known-cross-session-weakness match resolves both the session tag and the user's history to their canonical **family** (`resolve_to_family`), so it fires for lowercase-tagged tracks like Statistics and stays consistent with the dashboard's `weakest_concepts` and the drill endpoint. This is distinct from the dashboard's *relative* weakness signal (bottom-3 by recency-weighted accuracy, [dashboard.md](dashboard.md)); the debrief uses an *absolute* threshold — two intentionally different definitions.
- **(Elite) "Known weakness" badge** — amber highlight when a session concept matches cross-session `weakest_concepts`.
- **Share result** — `navigator.share` with clipboard fallback. Includes track, mode, difficulty, score, baseline delta (Pro/Elite), top 2 weak concepts.
- **Mode-aware footer actions** — benchmark: `Share result` + `Back to Mock` + `Plan follow-up drill`; custom/Loop: `Share result` + `Back to drill lobby` (concept drills are per-row in the breakdown above, so the footer is navigation only).

---

## History (`/mock` page)

- Last 20 sessions split into benchmark, custom drill, and Interview Loop sections.
- Mode labels normalised: `benchmark` → "Benchmark", `custom` → "Custom drill", `interview_loop` → "Interview Loop", `30min` → "Sprint drill (legacy)", `60min` → "Full (legacy)".
- First-run: explicit framing for each mode instead of a generic empty state.
- Partial-history states are explicit (benchmark-only users see "No drill sessions yet", etc.).
- **Review →** for completed sessions, **Resume →** for in-progress ones.

---

## How to Use (the `?` button on /mock)

1. **Choose session type** — Benchmark for the fixed-shape track readiness signal, Custom drill for targeted practice, or Interview Loop (Elite) for chain-driven interview simulation.
2. **Pick track** — single track or Mixed. Mixed always requires selecting a role (Data Analyst, Data Engineer, Analytics Engineer, Data Scientist).
3. **Pick difficulty** — buttons show live access state (remaining daily/weekly sessions or upgrade CTAs). Medium/hard requires Pro or above. **Interview Loop has a track-aware difficulty step** (medium or hard; easy is never offered). Greyed difficulties mean no chains exist at that level for this track. Where shown, a hint *"Follow-ups escalate to Hard."* indicates an escalating loop (Python-medium, SQL-medium, Data-Modeling-medium).
4. **(Benchmark or Custom + Mixed)** Select role.
5. **(Elite)** Optionally enable **Focus mode** (1–3 concept families).
6. **Start** — timer starts immediately. Interview Loop sessions draw a chain and lock it to you; discard within 2 minutes if you want to cancel penalty-free.
7. **During the session** — run code as many times as you like. When ready, submit — **each question is one shot**. Blank code or unselected MCQ is rejected before counting. Interview Loop: read the pivot card after each answer and dismiss to advance.
8. **End session** — click "End session" or let the timer run out.
9. **Review** — score, solutions, concept breakdown, (Elite) Interview Loop dimension analysis and debrief.

---

## Backend Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/mock/access` | Required | Pre-flight: per-difficulty access state for a given track and mode. For `interview_loop`, returns `access[medium|hard]` each with `{ can_start, block_reason, escalates }` — difficulties with no chains return `can_start: false, block_reason: "no_chains"`. Params: `track`, `mode`. Returns `weekly_benchmark_used` + `weekly_benchmark_limit` for Free + benchmark. Returns top-level `fresh_loop_cells` (unexhausted Loop cells) when an interview_loop cell is exhausted. |
| GET | `/api/mock/history` | Required | Last 20 sessions |
| GET | `/api/mock/analytics` | Required (Elite) | Aggregate analytics — benchmark/drill/loop summaries, trends, concept signals, per-dimension Loop performance |
| POST | `/api/mock/start` | Required | Start a session. Body: `mode`, `track`, `difficulty` (required for benchmark/custom/interview_loop; for interview_loop must be `'medium'` or `'hard'`, track-dependent — 400 on a difficulty that has no chains for the track), `role` (required when `track="mixed"`), `num_questions` (custom only), `time_minutes` (custom only), `focus_concepts` (Elite), `replay` (interview_loop only — `true` re-draws a completed chain once the pool is exhausted; returns `is_replay: true`). Returns 409 if active session exists (body: `session_id`, `track`, `difficulty`, `mode`); 409 `pool_exhausted` + `replayable` for an exhausted loop without `replay`. |
| GET | `/api/mock/:id` | Required | Load/reload session state |
| POST | `/api/mock/:id/run` | Required | Run (not grade) a code answer mid-session against **public** test cases. Body: `question_id`, `track`, `code`. Gated on **session membership** (not the practice unlock state), so mock-only questions run. No progress recorded; callable repeatedly. |
| POST | `/api/mock/:id/submit` | Required | Submit one answer mid-session. Returns 409 if question already submitted. Returns 422 for blank input. |
| POST | `/api/mock/:id/finish` | Required | End session — full summary with solutions and (Elite) debrief |
| DELETE | `/api/mock/:id` | Required | Discard active session within 120 s. Returns 204. Returns 403 if too old or already completed. For Interview Loop: reclaims chain. For all modes: reverts quota counter. |

---

## Database Schema Changes (Phase 3)

All three changes below require Alembic migrations before any Phase 3 feature can ship.

```sql
-- 1. Role column on mock_sessions (Mixed benchmark + custom drill)
ALTER TABLE mock_sessions ADD COLUMN role TEXT;

-- 2. Follow-up dimension on mock_session_questions (Interview Loop analytics)
ALTER TABLE mock_session_questions ADD COLUMN follow_up_dimension TEXT;

-- 3. Chain consumption tracking (Interview Loop atomicity)
CREATE TABLE mock_chain_consumption (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id   INTEGER NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id  BIGINT REFERENCES mock_sessions(id) ON DELETE SET NULL,
    reclaimed   BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (user_id, parent_id)
);
CREATE INDEX idx_mcc_user_active ON mock_chain_consumption (user_id) WHERE NOT reclaimed;
```

---

## Test Coverage

See `backend/tests/test_11_mock.py`. Phase 3 requires new/updated test cases covering:

- Weekly rolling benchmark cap (Free): blocks on second benchmark within 7 days; resets correctly after 7 days; discard reverts count
- Benchmark difficulty gate for Free: medium + hard → 403 regardless of practice unlock state
- Custom mode for Free: all difficulties → 403
- Interview Loop: Elite-only gate (Free/Pro → 403); chain atomicity (consumed at start, not finish); reclaim within 2 min; pool exhaustion → 409; time limit = 15 min × chain length; `follow_up_dimension` denormalised into session questions; pivot card flag in response
- Mixed benchmark: requires `role` param; 400 without role; correct blueprint per role; track substitution on pool exhaustion
- Mixed custom drill: requires `role`; pool draws from role tracks only
- Mode-based daily cap (Pro): benchmark counter independent from custom counter; 3/day each
- Legacy `30min` sessions: still readable in history; cannot be started new (400)
- Remove `follow_up_id` dynamic injection: `submit_answer` no longer calls `inject_follow_up_question`
- `loop_summary` in analytics: only populated for Elite + Loop sessions; correct per-dimension accuracy
