# Dashboard Feature Reference

The dashboard is the cross-track progress hub at `/dashboard` (`ProgressDashboard.js`). It surfaces track overview statistics, coaching insights, streak state, and mock interview history for any authenticated user. The weak-areas coaching panel (the full gap list) is a **Pro+** feature. Elite users see additional exclusive sections: a personalised study plan and per-track interview readiness scores — the *prescription* layer, distinct from the Pro-visible *diagnosis*.

---

## What the page shows

| Section | Description |
|---|---|
| **Track Overview** | One card per active track (all 9 tracks). Each shows solved/total (**practice catalog only**), an animated progress bar, median solve time, accuracy %, and (Elite) a per-track readiness score badge. **Accuracy spans practice + mock submissions** (mock answers are recorded to `submissions`, so a track with 0 practice solves can still have an accuracy) — it renders as `—` when the track has **zero attempts** (never a misleading `0%`), and is annotated `N in mock` when the attempts are **purely mock** (so a `0 solved · 100% acc` row reads true rather than looking broken). On mobile (≤600px) the row reflows to two lines — name + readiness chip on the first, progress bar + count + accuracy (with the `N in mock` qualifier) on the second — dropping the tagline, median solve time, and the "Mock to level up" nudge to stay compact. Data from `/api/dashboard` (practice solved counts) + `/api/dashboard/insights` (accuracy %, `attempts`/`practice_attempts`/`mock_attempts`, median, readiness). |
| **Personalised study plan** | **(Elite)** An ordered list of 3–5 next steps based on weak concepts, practice gaps, and mock frequency. Non-Elite users see a gated upgrade prompt. |
| **Focus card** | A single hero CTA. For Pro/Elite with weak-concept data: *Drill {top weak concept} → Go* — the [concept drill](../frontend.md#concept-drill), a Pro+ focused practice walk. Otherwise a cross-track pace insight or a continue-practice nudge. |
| **Where to focus (weak areas)** | **(Pro/Elite)** Concept rows with accuracy %, a coaching summary, a primary *Drill this concept →* CTA (the concept drill), and an **honest secondary** *Or take the … path →* when a matching learning path exists. Pro and Elite both see the **full gap list** (the diagnosis is not paywalled between paid tiers — 2026-06-13, decision B); Elite's extra is the *prescription* (study plan + readiness scores), not more gaps. |
| **Recent Activity** | Up to 10 most-recently-solved questions across all tracks. Each row shows track, difficulty badge, question title, and relative time. |
| **Concepts by Track** | Tags of concepts covered by solved questions, grouped by track. Only rendered when at least one concept exists. |
| **Mock Interviews** | Last 5 mock sessions in a compact table with date, mode, track, difficulty, score, and a Review/Resume link. Hidden when no mock history exists. |

---

## Plan-gated sections

| Section | Free | Pro | Elite |
|---|---|---|---|
| Track Overview (basic stats) | ✅ | ✅ | ✅ |
| Focus card (hero CTA) | ✅ (pace / continue nudge) | ✅ (drill top weak concept) | ✅ (drill top weak concept) |
| Where to focus (weak areas + concept drill) | ❌ (upgrade teaser) | ✅ (full gap list) | ✅ (full gap list) |
| Per-track readiness score badges | ❌ (upgrade teaser shown) | ❌ (upgrade teaser shown) | ✅ |
| Personalised study plan | ❌ (locked section shown) | ❌ (locked section shown) | ✅ |

---

## Endpoints

### `GET /api/dashboard`

Returns the track overview, recent activity, and concept tags for the current user.

**Response shape:**
```json
{
  "tracks": {
    "sql":         { "solved": 12, "total": 95, "by_difficulty": { "easy": {"solved": 10, "total": 32}, ... } },
    "python":      { ... },
    "pandas": { ... },
    "pyspark":     { ... },
    "data-engineering": { ... },
    "data-modeling": { ... },
    "statistics": { ... },
    "ml-fundamentals": { ... },
    "experimentation": { ... }
  },
  "recent_activity": [
    { "topic": "sql", "question_id": 1, "title": "...", "difficulty": "easy", "solved_at": "2026-04-24T..." }
  ],
  "concepts_by_track": {
    "sql": ["window functions", "CTEs", ...],
    "python": [...]
  }
}
```

**Notes:**
- `pandas` is remapped to `pandas` in all keys before returning.
- `recent_activity` is ordered newest-first, capped at 10.
- `concepts_by_track` only includes tracks where at least one concept exists.
- `by_difficulty` values are objects `{solved, total}`, not plain integers.
- Data source: `user_progress` table (written on correct submission).

---

### `GET /api/dashboard/insights`

Returns per-track coaching metrics, weakest concepts, the cross-track pace insight string, and the current solve streak. Results are **cached in-process for 60 seconds per user**.

**Response shape:**
```json
{
  "per_track": {
    "sql":         { "solve_count": 12, "median_solve_seconds": 420, "accuracy_pct": 0.72 },
    "python":      { "solve_count": 5,  "median_solve_seconds": 180, "accuracy_pct": 0.60 },
    "pandas": { "solve_count": 0,  "median_solve_seconds": null, "accuracy_pct": 0.0 },
    "pyspark":     { "solve_count": 3,  "median_solve_seconds": 30,  "accuracy_pct": 0.90 },
    "data-engineering": { "solve_count": 0, "median_solve_seconds": null, "accuracy_pct": 0.0 },
    "data-modeling": { "solve_count": 0, "median_solve_seconds": null, "accuracy_pct": 0.0 },
    "statistics": { "solve_count": 0, "median_solve_seconds": null, "accuracy_pct": 0.0 },
    "ml-fundamentals": { "solve_count": 0, "median_solve_seconds": null, "accuracy_pct": 0.0 },
    "experimentation": { "solve_count": 0, "median_solve_seconds": null, "accuracy_pct": 0.0 }
  },
  "weakest_concepts": [
    {
      "concept": "window functions", "track": "sql", "attempts": 7, "correct": 2, "accuracy_pct": 0.286,
      "summary": "You're getting this wrong more often than not. This is your highest-priority gap right now.",
      "recommended_path_slug": "window-functions-sql",
      "recommended_path_title": "Window Functions",
      "recommended_question_ids": [42, 55]
    }
  ],
  "cross_track_insight": "You solve SQL ~4 minutes slower than PySpark. Try 3 SQL mediums to close the gap.",
  "streak_days": 3
}
```

**Notes:**
- `median_solve_seconds` is `null` when there are no solved questions on that track.
- `accuracy_pct` is `0.0` when there are zero attempts on that track.
- `weakest_concepts` contains at most 3 entries, sorted by recency-weighted accuracy ascending (worst first), with `attempts` as the tiebreaker. Only concepts with ≥ 3 total attempts appear. Attempts from the last 14 days count 1.5× so recent struggles surface ahead of stale history. **Both practice and mock attempts count** — the concept lookup (`_build_concepts_lookup` in `routers/insights.py`) spans practice + mock-only questions, so a miss on a mock-only question feeds weak-concept detection (a miss under interview pressure is a strong weakness signal). The **drill** a weak concept links to stays practice-only (`/api/practice/drill` reads the practice catalog), so mock-only questions are detected-from but never served back to the user.
- `cross_track_insight` is `null` when fewer than 2 tracks have data, or when the fastest–slowest gap is < 60 seconds.
- `streak_days` is 0 when the user has not solved anything today.
- Data source: `submissions` table (all attempts, not just first-correct).

---

## Coaching insights spec

### Per-track stats

| Field | How it is computed |
|---|---|
| `solve_count` | Distinct question IDs with a correct submission on this track |
| `median_solve_seconds` | For each solved question: time from first attempt to first correct attempt. Median of those durations across all solved questions on the track. |
| `accuracy_pct` | `correct_submissions / total_submissions` for this track. Rounded to 3 decimal places. |

### Weakest concepts

A concept appears in `weakest_concepts` if it is tagged on a question the user has attempted ≥ 3 times (correct or incorrect). Concepts are ranked by recency-weighted accuracy ascending (worst first). At most 3 are returned.

Each entry is enriched with:
- `summary` — a deterministic one-sentence coaching note keyed to accuracy bucket (< 30% → "highest-priority gap"; < 50% → "pattern isn't sticking"; < 70% → "breaks under new angles"; ≥ 70% → "not fully consistent yet").
- `recommended_path_slug` / `recommended_path_title` — the most foundational accessible learning path that covers this concept (foundational paths preferred over intermediate / advanced). Matching is **family-aware** — both the weak concept and the path's `focus_concepts` are resolved to their canonical concept family before comparison (same resolver Mock's `focus_concepts` filter uses). Only present when a matching path exists and its tier is accessible under the user's plan.
- `recommended_question_ids` — up to 2 unsolved question IDs on this concept, easiest-first. Free users only get easy questions; Pro/Elite get any difficulty. **Retained in the payload but no longer the primary nav** — the dashboard and the logged-in landing now surface each weak concept as a **concept drill** (`/practice/{track}?drill={concept}`, a Pro+ focused practice walk — see [frontend.md §Concept drill](../frontend.md#concept-drill)) rather than deep-linking a single question. The `recommended_path_slug` path is offered as an **honest secondary** (*Or take the … path →*) when present, never as the primary "drill" CTA.

### Interview readiness score (Elite only)

`readiness_scores` in `/api/dashboard/insights` returns per-track scores (0–100) for Elite users (`null` for other plans). Each score has three components:

| Component | Points | How it is computed |
|---|---|---|
| Coverage | 45 max | Difficulty-weighted breadth of *distinct* solves. Easy: `min(solved/total, 1) × 12`. Medium: `min(solved/total, 1) × 18`. Hard: `min(solved/(total × 0.5), 1) × 15` — 50% hard coverage earns full hard credit (hard questions weighted highest per question). |
| Solve quality | 25 max | First-time-correct (FTC) mastery: `min(ftc / (0.4 × total_practice), 1) × 25`. A question is FTC if the user's *first* submission on it was correct. Question-level, so re-running or re-submitting never dilutes this term. |
| Mock performance | 30 max | Confidence-weighted accuracy over **engaged** completed sessions (those where `attempted_count ≥ 1`; abandoned/timed-out/seed sessions with 0 attempts are excluded). Per-session accuracy = `solved_count / attempted_count` (not over total — unanswered questions aren't counted as wrong). The most-recent **5** engaged sessions are averaged, then multiplied: `avg_accuracy × 30 × confidence`, where `confidence = min(n_engaged / 4, 1)`. A handful of sessions can't pin the top bands; mock reaches full weight (~4+ engaged sessions), at which point it is the decisive signal for "Interview ready" and above. Returns 0 when no engaged mock history exists for the track. |

**Label thresholds:** < 40 → "Early stage" · 40–64 → "Building" · 65–79 → "Getting there" · 80–89 → "Interview ready" · 90+ → "Strong"

The score badge on each track card is colour-coded along a calm ramp (no red — "Early stage" is a neutral starting point, not a failure state): grey/sage (Early stage), amber (Building → Getting there), green (Interview ready), blue (Strong).

**Key properties:**

- **Monotonic.** Every component only increases as the user practises more or solves more cleanly — engaging with new material or attempting a question a second time can never lower the score.
- **Solve time is intentionally excluded.** The platform's reasoning-over-speed positioning means time pressure surfaces through mock (which is timed), not through the readiness metric. Time remains a displayed per-track insight only.
- **Coverage + quality cap at 70 ("Getting there").** Reaching "Interview ready" (80+) or "Strong" (90+) requires mock performance. This is deliberate: genuine interview readiness should require having performed under timed conditions, not just accumulated practice solves.

Each track object also carries `mock_limited` (bool): `true` when `coverage + quality ≥ 50` and `n_engaged < 4` and `total < 80` — meaning the user is practice-strong but does not yet have enough engaged mock sessions for the confidence factor to reach full weight. A user who has mocked frequently but scores poorly is genuinely mock-weak, not `mock_limited`. The UI uses this flag to nudge practice-strong tracks toward a benchmark mock.

**Note on mock metric vs. analytics score:** The readiness mock metric (accuracy over *attempted*, engaged sessions only, confidence-weighted) is intentionally distinct from the post-session analytics headline `avg_score_pct` (`solved_count / total_count`, which counts unanswered questions as misses). Readiness measures demonstrated skill on questions the user engaged with; `avg_score_pct` measures session outcome including gaps. Both are valid; the divergence is by design, not a bug.

### Personalised study plan (Elite only)

`study_plan` in `/api/dashboard/insights` returns an ordered list of 3–5 action items for Elite users (`null` otherwise). Each item has:
- `type`: `concept_drill` | `learning_path` | `mock_session` | `practice_hard`
- `title`, `description`, `cta_label`, `cta_href`, `track`, `priority`

**Generation algorithm:**
1. Lowest-readiness track → target its worst concept (path if available, else a `concept_drill`)
2. Top 2 weakest concepts across all tracks → path or `concept_drill` action
3. Track with < 30% hard question coverage → `practice_hard` action
4. Fewer than 3 completed mocks in the last 14 days → `mock_session` action

A `concept_drill` step's `cta_href` is `/practice/{track}?drill={concept}` (the focused [concept drill](../frontend.md#concept-drill) walk); a `learning_path` step's is `/learn/{track}/{slug}`. The study plan is a curated mixed planner, so a `learning_path` step (labelled *Start path →*) is legitimate here — unlike the explicit *Drill this concept →* affordances on the focus card / weak-areas panel, which always lead with the concept drill.

Actions are deduplicated (no two of the same type + track), and capped at 5 total.

### Cross-track pace insight

Computed by comparing `median_solve_seconds` across tracks that have at least one solved question. If the gap between the slowest and fastest track is ≥ 60 seconds, a human-readable coaching string is returned naming both tracks and suggesting 3 practice questions on the slow track. Example:

> "You solve SQL ~4 minutes slower than PySpark. Try 3 SQL mediums to close the gap."

If only one track has data, or the gap is < 60 s, `cross_track_insight` is `null`.

---

## Streak logic

`streak_days` in `/api/dashboard/insights` counts consecutive calendar days (UTC) ending **today** on which at least one correct submission was recorded.

- If today has no correct submission: `streak_days = 0`.
- If today has a correct submission but yesterday does not: `streak_days = 1`.
- The count extends back as long as consecutive days all have at least one correct submission.

`streak_at_risk` (from `GET /api/auth/me`) is `true` when `streak_days = 0` **and** yesterday had at least one correct submission — i.e. the user had a streak that will break unless they solve something today. This field is not part of the insights payload; it is read from the `AuthContext` (`user.streak_at_risk`). The streak is surfaced on the **dashboard hero stat** (the day count with a *Streak at risk ⚡* flag, `ProgressDashboard.js`) and on the **workspace topbar pill** (`AppShell.js`, `.shell-pill-streak` / `.shell-pill-streak-risk`); streak **milestone toasts** fire on solves in `QuestionPage.js`.

---

## Cache behaviour

`/api/dashboard/insights` uses an **in-process dictionary cache** keyed by `user_id`.

| Property | Value |
|---|---|
| TTL | 60 seconds |
| Scope | Per user, per process instance |
| Invalidation | TTL expiry only (no explicit invalidation on new submissions) |
| Cold miss | Full recomputation from the `submissions` table |
| Warm hit | Cached payload returned immediately, no DB query |

In a multi-process/multi-replica deployment, each process maintains its own cache independently. Stale data of up to 60 seconds is expected and acceptable.

---

## Test coverage

`backend/tests/test_12_dashboard.py` is the focused backend suite for dashboard and insights behavior.

Current coverage emphasis:

- `/api/dashboard` response shape, difficulty counters, recent activity, concept tags, and slug normalization
- `/api/dashboard/insights` metric computation, streak logic, weakest concept selection, cache behavior, and lifetime-plan access
- Legacy regression coverage for the original executable-track slice is still deepest in tests; the product and API now operate across all 9 active tracks
