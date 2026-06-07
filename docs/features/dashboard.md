# Dashboard Feature Reference

The dashboard is the cross-track progress hub at `/dashboard` (`ProgressDashboard.js`). It surfaces track overview statistics, coaching insights, streak state, and mock interview history for any authenticated user. Elite users see additional exclusive sections: a personalised study plan, per-track interview readiness scores, and the Top-3 weak areas coaching panel.

---

## What the page shows

| Section | Description |
|---|---|
| **Track Overview** | One card per active track (all 9 tracks). Each shows solved/total, an animated progress bar, median solve time, accuracy %, easy/medium/hard breakdown, and (Elite) a per-track readiness score badge. Data from `/api/dashboard` + `/api/dashboard/insights`. |
| **Personalised study plan** | **(Elite)** An ordered list of 3–5 next steps based on weak concepts, practice gaps, and mock frequency. Non-Elite users see a gated upgrade prompt. |
| **Coaching Insights strip** | Three tiles: Cross-track pace coaching, Current streak, Weakest concept. Hidden when `totalSolved === 0` and replaced by an empty-state CTA. |
| **Top-3 Weak Areas** | **(Elite)** Concept rows with accuracy %, coaching summary, and drill/path links. |
| **Recent Activity** | Up to 10 most-recently-solved questions across all tracks. Each row shows track, difficulty badge, question title, and relative time. |
| **Concepts by Track** | Tags of concepts covered by solved questions, grouped by track. Only rendered when at least one concept exists. |
| **Mock Interviews** | Last 5 mock sessions in a compact table with date, mode, track, difficulty, score, and a Review/Resume link. Hidden when no mock history exists. |

---

## Plan-gated sections

| Section | Free | Pro | Elite |
|---|---|---|---|
| Track Overview (basic stats) | ✅ | ✅ | ✅ |
| Coaching Insights strip | ✅ (streak + pace only) | ✅ (all 3 tiles) | ✅ |
| Top-3 Weak Areas panel | ❌ | ❌ | ✅ |
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
    "python-data": { ... },
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
- `python_data` is remapped to `python-data` in all keys before returning.
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
    "python-data": { "solve_count": 0,  "median_solve_seconds": null, "accuracy_pct": 0.0 },
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
- `weakest_concepts` contains at most 3 entries, sorted by recency-weighted accuracy ascending (worst first), with `attempts` as the tiebreaker. Only concepts with ≥ 3 total attempts appear. Attempts from the last 14 days count 1.5× so recent struggles surface ahead of stale history.
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
- `recommended_question_ids` — up to 2 unsolved question IDs on this concept, easiest-first. Free users only get easy questions; Pro/Elite get any difficulty.

### Interview readiness score (Elite only)

`readiness_scores` in `/api/dashboard/insights` returns per-track scores (0–100) for Elite users (`null` for other plans). Each score has three components:

| Component | Points | How it is computed |
|---|---|---|
| Practice coverage | 40 max | Easy (10): `min(solved/total, 1) × 10`. Medium (20): `min(solved/total, 1) × 20`. Hard (10): `min(solved/(total×0.4), 1) × 10` — only 40% hard coverage needed for full 10 pts. |
| Mock accuracy | 35 max | Average score across last 5 completed sessions for this track. 0 pts if no mock history for this track. |
| Concept strength | 25 max | `max(0, strong_count − weak_count×1.5) / 8 × 25` — where strong = concepts ≥ 70% accuracy (≥3 attempts), weak = concepts < 60% (≥3 attempts). Max denominator of 8 represents a well-rounded candidate. |

**Label thresholds:** < 40 → "Early stage" · 40–64 → "Building" · 65–79 → "Getting there" · 80–89 → "Interview ready" · 90+ → "Strong"

The score badge on each track card is colour-coded: green (Strong/Interview ready), amber (Getting there), grey (Building/Early stage).

### Personalised study plan (Elite only)

`study_plan` in `/api/dashboard/insights` returns an ordered list of 3–5 action items for Elite users (`null` otherwise). Each item has:
- `type`: `concept_drill` | `learning_path` | `mock_session` | `practice_hard`
- `title`, `description`, `cta_label`, `cta_href`, `track`, `priority`

**Generation algorithm:**
1. Lowest-readiness track → target its worst concept (path if available, else drill link)
2. Top 2 weakest concepts across all tracks → path or drill action
3. Track with < 30% hard question coverage → `practice_hard` action
4. Fewer than 3 completed mocks in the last 14 days → `mock_session` action

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

`streak_at_risk` (from `GET /api/auth/me`) is `true` when `streak_days = 0` **and** yesterday had at least one correct submission — i.e. the user had a streak that will break unless they solve something today. This field is not part of the insights payload; it is read from the `AuthContext` (`user.streak_at_risk`) by the `InsightStrip` component to determine the streak tile message.

**InsightStrip streak tile messages:**
| State | Message |
|---|---|
| `streak_days = 0` | "Solve one question today to start a streak." |
| `streak_days > 0` and `streak_at_risk = true` | "Solve one today to keep it alive." |
| `streak_days > 0` and `streak_at_risk = false` (already solved today) | "Great work! Come back tomorrow to keep it going." |

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
