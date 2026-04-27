# Dashboard Feature Reference

The dashboard is the cross-track progress hub at `/dashboard` (`ProgressDashboard.js`). It surfaces track overview statistics, coaching insights, streak state, and mock interview history for any authenticated user. All tiers (Free, Pro, Elite, and lifetime variants) can access the full dashboard — there are no plan-gated sections on this page.

---

## What the page shows

| Section | Description |
|---|---|
| **Track Overview** | Four track cards (SQL, Python, Pandas, PySpark). Each shows solved/total, an animated progress bar, median solve time, accuracy %, and an easy/medium/hard breakdown. Data comes from both `/api/dashboard` (solve counts) and `/api/dashboard/insights` (timing + accuracy). |
| **Coaching Insights strip** | Three tiles: Cross-track pace coaching, Current streak, Weakest concept. Hidden when `totalSolved === 0` and replaced by an empty-state CTA. |
| **Recent Activity** | Up to 10 most-recently-solved questions across all tracks. Each row shows track, difficulty badge, question title, and relative time. |
| **Concepts by Track** | Tags of concepts covered by solved questions, grouped by track. Only rendered when at least one concept exists. |
| **Mock Interviews** | Last 5 mock sessions in a compact table with date, mode, track, difficulty, score, and a Review/Resume link. Hidden when no mock history exists. |

---

## Plan-gated sections

There are **no plan-gated sections** on the dashboard. All tiers see the full page. Differences across plans affect what questions can be solved (and therefore what data populates the page), not the dashboard UI itself.

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
    "pyspark":     { ... }
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
    "pyspark":     { "solve_count": 3,  "median_solve_seconds": 30,  "accuracy_pct": 0.90 }
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
- `recommended_path_slug` / `recommended_path_title` — the most foundational accessible learning path that covers this concept (starter paths preferred over intermediate / advanced). Only present when a matching path exists and its tier is accessible under the user's plan.
- `recommended_question_ids` — up to 2 unsolved question IDs on this concept, easiest-first. Free users only get easy questions; Pro/Elite get any difficulty.

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

`backend/tests/test_dashboard.py` — 31 tests, all passing.

### `/api/dashboard` tests (12)

| Test | What it verifies |
|---|---|
| `test_returns_expected_top_level_keys` | Response contains `tracks`, `recent_activity`, `concepts_by_track` |
| `test_all_four_tracks_present` | All four track keys present in `tracks` |
| `test_track_totals_match_catalog` | Per-track `total` matches CLAUDE.md counts (95/83/82/90) |
| `test_by_difficulty_shape` | Each `by_difficulty` entry is `{solved: int, total: int}` |
| `test_solved_count_reflects_submissions` | Inserting a `user_progress` row increments `solved` |
| `test_python_data_slug_is_remapped` | `python_data` → `python-data`, raw key absent |
| `test_recent_activity_empty_for_new_user` | Empty list before any solves |
| `test_recent_activity_populated_after_solve` | Activity row present with correct shape after solve |
| `test_recent_activity_topic_remapped` | `python-data` slug used in activity rows |
| `test_recent_activity_capped_at_10` | At most 10 rows returned |
| `test_concepts_by_track_empty_for_new_user` | Empty dict before any solves |
| `test_concepts_by_track_populated_after_solve` | Concepts appear after solving a question with concepts |

### `/api/dashboard/insights` tests (19)

| Test | What it verifies |
|---|---|
| `test_returns_expected_shape` | All four top-level keys present |
| `test_per_track_has_all_four_tracks` | All four track keys in `per_track` |
| `test_per_track_fields_shape` | Each track has `solve_count`, `median_solve_seconds`, `accuracy_pct` |
| `test_empty_user_gets_zero_stats` | All zeros/nulls for a new user |
| `test_metrics_computed_correctly` | `solve_count`, `median_solve_seconds`, `accuracy_pct` match expected values |
| `test_streak_days_zero_for_new_user` | 0 streak with no submissions |
| `test_streak_days_increments_on_solve_today` | 1-day streak after solving today |
| `test_streak_days_consecutive_days` | 3-day streak for solves on today, yesterday, 2 days ago |
| `test_streak_breaks_on_gap` | Streak = 1 when there's a gap in consecutive days |
| `test_streak_zero_when_no_solve_today` | Streak = 0 if last solve was yesterday |
| `test_weakest_concepts_empty_below_3_attempts` | No concepts with < 3 attempts |
| `test_weakest_concepts_appear_at_3_attempts` | Concept appears at exactly 3 attempts |
| `test_weakest_concepts_capped_at_3` | At most 3 concepts returned |
| `test_cross_track_insight_none_with_single_track` | `null` with only one track having data |
| `test_cross_track_insight_none_when_gap_below_60s` | `null` when fastest–slowest gap < 60 s |
| `test_cross_track_insight_fires_when_gap_exceeds_60s` | String containing both track names returned |
| `test_cache_returns_stale_data_within_60s` | Second request within TTL returns identical payload |
| `test_cache_is_per_user` | User A's cache does not affect User B |
| `test_lifetime_plans_can_access_insights` | `lifetime_pro` and `lifetime_elite` both get 200 |
