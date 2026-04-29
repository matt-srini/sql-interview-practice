from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from fastapi import APIRouter, Depends

import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_questions
from db import get_mock_history, get_submission_events
from deps import get_current_user
from path_loader import get_all_paths
from unlock import normalize_plan

router = APIRouter(prefix="/api/dashboard")

_TRACK_LABELS = {
    "sql": "SQL",
    "python": "Python",
    "python-data": "Pandas",
    "pyspark": "PySpark",
}

_TRACK_ORDER = ["sql", "python", "python-data", "pyspark"]

_TOPIC_MODULES = {
    "sql": sql_questions,
    "python": python_questions,
    "python-data": python_data_questions,
    "pyspark": pyspark_questions,
}

_CACHE_TTL_SECONDS = 60
_insights_cache: dict[str, dict[str, Any]] = {}

# Maps (track, concept) → (slug, title, tier) for the highest-priority matching path.
# Starter paths take precedence over intermediate, which take precedence over advanced,
# so the recommendation points to the most foundational accessible path first.
def _build_concept_path_index() -> dict[tuple[str, str], tuple[str, str, str]]:
    role_order = {"starter": 0, "intermediate": 1, "advanced": 2}
    paths = sorted(
        get_all_paths(),
        key=lambda p: role_order.get(p.get("role", "advanced"), 2),
    )
    index: dict[tuple[str, str], tuple[str, str, str]] = {}
    for path in paths:
        track = path["topic"]
        tier = path.get("tier", "pro")
        for concept in path.get("focus_concepts", []):
            key = (track, concept)
            if key not in index:
                index[key] = (path["slug"], path["title"], tier)
    return index


_CONCEPT_PATH_INDEX = _build_concept_path_index()


def _build_concepts_lookup() -> dict[str, dict[int, list[str]]]:
    lookup: dict[str, dict[int, list[str]]] = {}
    for track, module in _TOPIC_MODULES.items():
        grouped = module.get_questions_by_difficulty()
        questions = [q for difficulty_questions in grouped.values() for q in difficulty_questions]
        lookup[track] = {
            int(q["id"]): list(q.get("concepts", []))
            for q in questions
        }
    return lookup


_CONCEPTS_LOOKUP = _build_concepts_lookup()


def _build_concept_question_index() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Returns {track: {concept: [question_dict, ...]}} sorted easy-first within each concept."""
    diff_order = {"easy": 0, "medium": 1, "hard": 2}
    index: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for track, module in _TOPIC_MODULES.items():
        grouped = module.get_questions_by_difficulty()
        all_qs = [
            {**q, "_diff_order": diff_order.get(q.get("difficulty", "hard"), 2)}
            for qs in grouped.values()
            for q in qs
        ]
        all_qs.sort(key=lambda q: q["_diff_order"])
        track_index: dict[str, list[dict[str, Any]]] = {}
        for q in all_qs:
            for concept in q.get("concepts", []):
                track_index.setdefault(concept, []).append(q)
        index[track] = track_index
    return index


_CONCEPT_QUESTION_INDEX = _build_concept_question_index()


def _concept_summary(accuracy_pct: float) -> str:
    """Return a coaching sentence for a concept based on accuracy bucket."""
    if accuracy_pct < 0.30:
        return "You're getting this wrong more often than not. This is your highest-priority gap right now."
    if accuracy_pct < 0.50:
        return "Under 50% accuracy — the pattern isn't sticking yet. Targeted repetition here will pay off quickly."
    if accuracy_pct < 0.70:
        return "You get this right about half the time, but it breaks under new problem angles. Try articulating the pattern before writing code."
    return "Mostly solid, but not fully consistent yet. One or two more deliberate attempts should lock it in."


def _cache_get(user_id: str) -> dict[str, Any] | None:
    cached = _insights_cache.get(user_id)
    if not cached:
        return None
    if cached["expires_at"] <= datetime.now(UTC):
        _insights_cache.pop(user_id, None)
        return None
    return cached["payload"]


def _cache_set(user_id: str, payload: dict[str, Any]) -> None:
    _insights_cache[user_id] = {
        "expires_at": datetime.now(UTC) + timedelta(seconds=_CACHE_TTL_SECONDS),
        "payload": payload,
    }


def _compute_streak_days(correct_dates: set[datetime.date]) -> int:
    today = datetime.now(UTC).date()
    if today not in correct_dates:
        return 0

    streak = 0
    cursor = today
    while cursor in correct_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _to_median_solve_seconds(events: list[dict[str, Any]]) -> dict[str, int | None]:
    per_track_durations: dict[str, list[int]] = defaultdict(list)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[(event["track"], int(event["question_id"]))].append(event)

    for (track, _question_id), attempt_events in grouped.items():
        first_attempt_at = attempt_events[0]["submitted_at"]
        first_correct_at = next(
            (item["submitted_at"] for item in attempt_events if item["is_correct"]),
            None,
        )
        if first_correct_at is None:
            continue

        duration_s = int((first_correct_at - first_attempt_at).total_seconds())
        per_track_durations[track].append(max(0, duration_s))

    medians: dict[str, int | None] = {}
    for track in _TRACK_ORDER:
        durations = per_track_durations.get(track, [])
        medians[track] = int(median(durations)) if durations else None
    return medians


def _build_cross_track_insight(per_track: dict[str, dict[str, Any]]) -> str | None:
    candidates: list[tuple[str, int]] = []
    for track, stats in per_track.items():
        median_seconds = stats.get("median_solve_seconds")
        if isinstance(median_seconds, int):
            candidates.append((track, median_seconds))

    if len(candidates) < 2:
        return None

    slow_track, slow_seconds = max(candidates, key=lambda item: item[1])
    fast_track, fast_seconds = min(candidates, key=lambda item: item[1])
    gap = slow_seconds - fast_seconds
    if gap < 60:
        return None

    slow_label = _TRACK_LABELS.get(slow_track, slow_track)
    fast_label = _TRACK_LABELS.get(fast_track, fast_track)
    gap_minutes = max(1, round(gap / 60))

    return (
        f"You solve {slow_label} ~{gap_minutes} minute{'s' if gap_minutes != 1 else ''} "
        f"slower than {fast_label}. Try 3 {slow_label} mediums to close the gap."
    )


@router.get("/insights")
async def get_dashboard_insights(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = current_user["id"]
    effective_plan = normalize_plan(current_user.get("plan", "free"))

    cached = _cache_get(user_id)
    if cached is not None:
        return cached

    events = await get_submission_events(user_id)

    per_track_attempts: dict[str, int] = defaultdict(int)
    per_track_correct: dict[str, int] = defaultdict(int)
    per_track_solved_question_ids: dict[str, set[int]] = defaultdict(set)
    concept_attempts: dict[tuple[str, str], int] = defaultdict(int)
    concept_correct: dict[tuple[str, str], int] = defaultdict(int)
    # Recency-weighted tallies: attempts from the last 14 days count 1.5×,
    # older attempts count 1.0× — so a single bad recent session doesn't
    # permanently dominate a concept score built up over months.
    concept_weighted_attempts: dict[tuple[str, str], float] = defaultdict(float)
    concept_weighted_correct: dict[tuple[str, str], float] = defaultdict(float)
    correct_dates: set[datetime.date] = set()

    recency_cutoff = datetime.now(UTC) - timedelta(days=14)

    for event in events:
        track = event["track"]
        if track not in _TRACK_ORDER:
            continue

        question_id = int(event["question_id"])
        is_correct = bool(event["is_correct"])
        submitted_at = event["submitted_at"]
        weight = 1.5 if (submitted_at is not None and submitted_at >= recency_cutoff) else 1.0

        per_track_attempts[track] += 1
        if is_correct:
            per_track_correct[track] += 1
            per_track_solved_question_ids[track].add(question_id)
            if submitted_at is not None:
                correct_dates.add(submitted_at.date())

        concepts = _CONCEPTS_LOOKUP.get(track, {}).get(question_id, [])
        for concept in concepts:
            key = (track, concept)
            concept_attempts[key] += 1
            concept_weighted_attempts[key] += weight
            if is_correct:
                concept_correct[key] += 1
                concept_weighted_correct[key] += weight

    medians = _to_median_solve_seconds(events)

    per_track: dict[str, dict[str, Any]] = {}
    for track in _TRACK_ORDER:
        attempts = per_track_attempts.get(track, 0)
        correct = per_track_correct.get(track, 0)
        accuracy = (correct / attempts) if attempts else 0.0
        per_track[track] = {
            "solve_count": len(per_track_solved_question_ids.get(track, set())),
            "median_solve_seconds": medians.get(track),
            "accuracy_pct": round(accuracy, 3),
        }

    weakest_concepts: list[dict[str, Any]] = []
    for (track, concept), attempts in concept_attempts.items():
        if attempts < 3:
            continue
        correct = concept_correct.get((track, concept), 0)
        w_attempts = concept_weighted_attempts.get((track, concept), float(attempts))
        w_correct = concept_weighted_correct.get((track, concept), float(correct))
        weighted_accuracy = w_correct / w_attempts if w_attempts > 0 else 0.0
        weakest_concepts.append(
            {
                "concept": concept,
                "track": track,
                "attempts": attempts,
                "correct": correct,
                "accuracy_pct": round(correct / attempts, 3),
                "_weighted_accuracy": weighted_accuracy,
            }
        )

    # Sort by recency-weighted accuracy (ascending) so fresh struggles rank highest.
    weakest_concepts.sort(
        key=lambda item: (item["_weighted_accuracy"], -item["attempts"], item["concept"])
    )

    # Enrich each entry and strip the internal sort key.
    for entry in weakest_concepts[:3]:
        entry.pop("_weighted_accuracy", None)
        track = entry["track"]
        concept = entry["concept"]
        accuracy = entry["accuracy_pct"]

        # Coaching summary
        entry["summary"] = _concept_summary(accuracy)

        # Recommended path
        lookup = _CONCEPT_PATH_INDEX.get((track, concept))
        if lookup:
            slug, title, tier = lookup
            if tier == "free" or effective_plan in ("pro", "elite"):
                entry["recommended_path_slug"] = slug
                entry["recommended_path_title"] = title

        # Recommended question IDs (unsolved, accessible, easy-first)
        solved_for_track = per_track_solved_question_ids.get(track, set())
        candidate_qs = _CONCEPT_QUESTION_INDEX.get(track, {}).get(concept, [])
        reco_ids: list[int] = []
        for q in candidate_qs:
            qid = int(q["id"])
            if qid in solved_for_track:
                continue
            if q.get("difficulty") != "easy" and effective_plan not in ("pro", "elite"):
                continue
            reco_ids.append(qid)
            if len(reco_ids) >= 2:
                break
        if reco_ids:
            entry["recommended_question_ids"] = reco_ids

    # Elite-only: readiness scores and study plan (adds one extra DB call for mock history,
    # only on cache misses — result is cached for 60s like the rest of the payload).
    readiness_scores: dict[str, Any] | None = None
    study_plan: list[dict[str, Any]] | None = None
    if effective_plan == "elite":
        mock_sessions_for_elite = await get_mock_history(user_id, limit=20)
        readiness_scores = _compute_readiness_scores(
            per_track_solved_question_ids=per_track_solved_question_ids,
            mock_sessions=mock_sessions_for_elite,
            concept_attempts=concept_attempts,
            concept_correct=concept_correct,
            effective_plan=effective_plan,
        )
        study_plan = build_study_plan(
            weakest_concepts=weakest_concepts[:3],
            per_track_solved_question_ids=per_track_solved_question_ids,
            mock_sessions=mock_sessions_for_elite,
            readiness_scores=readiness_scores,
            effective_plan=effective_plan,
        )

    payload = {
        "per_track": per_track,
        "weakest_concepts": weakest_concepts[:3],
        "cross_track_insight": _build_cross_track_insight(per_track),
        "streak_days": _compute_streak_days(correct_dates),
        "readiness_scores": readiness_scores,
        "study_plan": study_plan,
    }

    _cache_set(user_id, payload)
    return payload


# ---------------------------------------------------------------------------
# Readiness score (Elite-only)
# ---------------------------------------------------------------------------

def _compute_readiness_scores(
    per_track_solved_question_ids: dict[str, set[int]],
    mock_sessions: list[dict[str, Any]],
    concept_attempts: dict[tuple[str, str], int],
    concept_correct: dict[tuple[str, str], int],
    effective_plan: str,
) -> dict[str, dict[str, Any]] | None:
    """
    Compute per-track interview readiness scores (0–100) for Elite users.

    Score components (each track scored independently):
      1. Practice coverage (40 pts):
           Easy:   min(solved_easy / total_easy, 1.0) × 10
           Medium: min(solved_medium / total_medium, 1.0) × 20
           Hard:   min(solved_hard / (total_hard × 0.4), 1.0) × 10
      2. Mock accuracy (35 pts):
           Average score across last 5 completed sessions for this track.
           0 pts when the user has never run a mock for this track.
      3. Concept strength (25 pts):
           Counts concepts with ≥3 attempts. Strong (≥70% accuracy) − weak (<60%)
           gaps scaled to a max of 8 well-rounded concepts.

    Returns None for non-Elite plans.
    Labels: <40 Early stage · 40–64 Building · 65–79 Getting there · 80–89 Interview ready · 90+ Strong
    """
    if effective_plan != "elite":
        return None

    label_thresholds = [
        (90, "Strong"),
        (80, "Interview ready"),
        (65, "Getting there"),
        (40, "Building"),
        (0, "Early stage"),
    ]

    def _label(score: int) -> str:
        for threshold, lbl in label_thresholds:
            if score >= threshold:
                return lbl
        return "Early stage"

    scores: dict[str, dict[str, Any]] = {}

    for track in _TRACK_ORDER:
        solved_ids = per_track_solved_question_ids.get(track, set())
        module = _TOPIC_MODULES[track]
        grouped = module.get_questions_by_difficulty()

        easy_ids   = {int(q["id"]) for q in grouped.get("easy", [])}
        medium_ids = {int(q["id"]) for q in grouped.get("medium", [])}
        hard_ids   = {int(q["id"]) for q in grouped.get("hard", [])}

        total_easy   = len(easy_ids)
        total_medium = len(medium_ids)
        total_hard   = len(hard_ids)

        solved_easy   = len(solved_ids & easy_ids)
        solved_medium = len(solved_ids & medium_ids)
        solved_hard   = len(solved_ids & hard_ids)

        # Component 1: practice coverage (40 pts)
        easy_pts   = (min(solved_easy   / total_easy,   1.0) * 10) if total_easy   else 0.0
        medium_pts = (min(solved_medium / total_medium, 1.0) * 20) if total_medium else 0.0
        hard_threshold = total_hard * 0.4
        hard_pts = (min(solved_hard / hard_threshold, 1.0) * 10) if hard_threshold else 0.0
        practice_pts = easy_pts + medium_pts + hard_pts

        # Component 2: mock accuracy (35 pts)
        track_sessions = [
            s for s in mock_sessions
            if s.get("status") == "completed"
            and (s.get("track") == track or s.get("track") == "mixed")
            and (s.get("total_count") or 0) > 0
        ][-5:]
        if track_sessions:
            avg_mock = sum(s["solved_count"] / s["total_count"] for s in track_sessions) / len(track_sessions)
            mock_pts = avg_mock * 35.0
        else:
            mock_pts = 0.0

        # Component 3: concept strength (25 pts)
        strong = 0
        weak = 0
        for (t, _concept), attempts in concept_attempts.items():
            if t != track or attempts < 3:
                continue
            correct = concept_correct.get((t, _concept), 0)
            accuracy = correct / attempts
            if accuracy >= 0.70:
                strong += 1
            elif accuracy < 0.60:
                weak += 1
        max_expected_strong = 8
        raw_concept = max(0.0, (strong - weak * 1.5)) / max_expected_strong * 25.0
        concept_pts = min(raw_concept, 25.0)

        total = round(min(practice_pts + mock_pts + concept_pts, 100.0))
        scores[track] = {
            "score": total,
            "label": _label(total),
            "components": {
                "practice": round(practice_pts, 1),
                "mock_accuracy": round(mock_pts, 1),
                "concept_strength": round(concept_pts, 1),
            },
        }

    return scores


# ---------------------------------------------------------------------------
# Personalised study plan (Elite-only)
# ---------------------------------------------------------------------------

def build_study_plan(
    weakest_concepts: list[dict[str, Any]],
    per_track_solved_question_ids: dict[str, set[int]],
    mock_sessions: list[dict[str, Any]],
    readiness_scores: dict[str, dict[str, Any]] | None,
    effective_plan: str,
) -> list[dict[str, Any]] | None:
    """
    Generate a personalised study plan for Elite users: an ordered list of
    3–5 actionable steps based on weak areas and practice gaps.

    Action types: concept_drill · learning_path · mock_session · practice_hard
    Each action has: type, title, description, cta_label, cta_href, track, priority.

    Returns None for non-Elite plans.
    """
    if effective_plan != "elite":
        return None

    actions: list[dict[str, Any]] = []
    seen_type_track: set[tuple[str, str | None]] = set()

    def _add(
        type_: str,
        title: str,
        description: str,
        cta_label: str,
        cta_href: str,
        track: str | None = None,
    ) -> None:
        key = (type_, track)
        if key in seen_type_track or len(actions) >= 5:
            return
        seen_type_track.add(key)
        actions.append({
            "type": type_,
            "title": title,
            "description": description,
            "cta_label": cta_label,
            "cta_href": cta_href,
            "track": track,
            "priority": len(actions) + 1,
        })

    # Step 1: Lowest-readiness track → target its worst concept
    if readiness_scores:
        lowest_track = min(
            _TRACK_ORDER,
            key=lambda t: readiness_scores.get(t, {}).get("score", 100),
        )
        track_concepts = [c for c in weakest_concepts if c.get("track") == lowest_track]
        if track_concepts:
            worst = track_concepts[0]
            concept = worst["concept"]
            track_label = _TRACK_LABELS.get(lowest_track, lowest_track)
            path_info = _CONCEPT_PATH_INDEX.get((lowest_track, concept))
            if path_info:
                slug, path_title, _ = path_info
                _add(
                    "learning_path",
                    path_title,
                    f"Your {track_label} readiness is lowest. {concept.title()} is your sharpest gap — this path targets it directly.",
                    "Start path →",
                    f"/learn/{lowest_track}/{slug}",
                    track=lowest_track,
                )
            else:
                concept_slug = concept.lower().replace(" ", "_")
                _add(
                    "concept_drill",
                    f"Drill {concept.title()} — {track_label}",
                    f"Your {track_label} readiness is lowest. More focused practice on {concept.title()} will move the needle fastest.",
                    "Drill now →",
                    f"/practice/{lowest_track}?concepts={concept_slug}",
                    track=lowest_track,
                )

    # Step 2: Top 2 weakest concepts across all tracks
    for item in weakest_concepts[:2]:
        track = item.get("track", "sql")
        concept = item["concept"]
        track_label = _TRACK_LABELS.get(track, track)
        accuracy_pct = round(item["accuracy_pct"] * 100)
        path_info = _CONCEPT_PATH_INDEX.get((track, concept))
        if path_info:
            slug, path_title, _ = path_info
            _add(
                "learning_path",
                path_title,
                f"Covers {concept.title()} — you're at {accuracy_pct}% accuracy in {track_label}.",
                "Start path →",
                f"/learn/{track}/{slug}",
                track=track,
            )
        else:
            concept_slug = concept.lower().replace(" ", "_")
            _add(
                "concept_drill",
                f"Drill {concept.title()} — {track_label}",
                f"You're at {accuracy_pct}% accuracy. Deliberate repetition on {concept.title()} will close this gap.",
                "Drill now →",
                f"/practice/{track}?concepts={concept_slug}",
                track=track,
            )

    # Step 3: Hard practice gap (track with lowest solved-hard ratio, if < 30%)
    worst_hard_track: str | None = None
    worst_hard_ratio = 1.0
    for track in _TRACK_ORDER:
        module = _TOPIC_MODULES[track]
        grouped = module.get_questions_by_difficulty()
        total_hard = len(grouped.get("hard", []))
        if total_hard == 0:
            continue
        hard_ids = {int(q["id"]) for q in grouped.get("hard", [])}
        solved_hard = len(per_track_solved_question_ids.get(track, set()) & hard_ids)
        ratio = solved_hard / total_hard
        if ratio < worst_hard_ratio:
            worst_hard_ratio = ratio
            worst_hard_track = track

    if worst_hard_track and worst_hard_ratio < 0.3:
        track_label = _TRACK_LABELS.get(worst_hard_track, worst_hard_track)
        _add(
            "practice_hard",
            f"Push into {track_label} hard questions",
            f"Only {round(worst_hard_ratio * 100)}% hard coverage — interviewers expect you to handle tough edge cases.",
            "Go to hard →",
            f"/practice/{worst_hard_track}",
            track=worst_hard_track,
        )

    # Step 4: Mock boost — fewer than 3 completed mocks in the last 14 days
    cutoff_14d = datetime.now(UTC) - timedelta(days=14)
    recent_mocks = sum(
        1 for s in mock_sessions
        if s.get("status") == "completed"
        and s.get("ended_at")
        and datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00")) >= cutoff_14d
    )
    if recent_mocks < 3:
        _add(
            "mock_session",
            "Run a timed mock interview",
            "Simulated interviews improve time management and pressure recall under real conditions.",
            "Start mock →",
            "/mock",
            track=None,
        )

    return actions or None


# ---------------------------------------------------------------------------
# Session debrief (Elite-only, called from mock.py finish endpoint)
# ---------------------------------------------------------------------------

def build_session_debrief(
    enriched_questions: list[dict[str, Any]],
    session_meta: dict[str, Any],
    submission_events: list[dict[str, Any]],
    effective_plan: str,
) -> dict[str, Any] | None:
    """
    Generate a template-based coaching debrief for a completed mock session.
    Elite-only — returns None for other plans.

    enriched_questions : list from finish_session (has is_solved, concepts,
                         time_spent_s, is_follow_up, track, title, difficulty)
    session_meta       : dict with solved_count, total_count, time_used_s,
                         time_limit_s, difficulty, track
    submission_events  : from get_submission_events(user_id) for historical context
    effective_plan     : normalized plan string
    """
    if effective_plan != "elite":
        return None

    total_count = len(enriched_questions)
    if total_count == 0:
        return None

    solved_count = sum(1 for q in enriched_questions if q.get("is_solved"))
    time_used_s: int | None = session_meta.get("time_used_s")
    time_limit_s: int = session_meta.get("time_limit_s") or 1800
    session_difficulty: str = session_meta.get("difficulty") or "medium"
    session_track: str = session_meta.get("track") or "sql"

    # ── Build concept accuracy map from historical events ────────────────────
    # (track, concept) → (correct_total, attempt_total)
    hist_concept: dict[tuple[str, str], tuple[int, int]] = {}
    session_q_ids = {int(q.get("id", 0)) for q in enriched_questions}
    for event in submission_events:
        t = event.get("track", "sql")
        qid = int(event.get("question_id", 0))
        if qid in session_q_ids:
            continue  # exclude this session's questions from historical baseline
        for concept in _CONCEPTS_LOOKUP.get(t, {}).get(qid, []):
            key = (t, concept)
            c, a = hist_concept.get(key, (0, 0))
            hist_concept[key] = (c + (1 if event.get("is_correct") else 0), a + 1)

    # ── Session concept accuracy map ─────────────────────────────────────────
    sess_concept: dict[str, dict[str, Any]] = {}
    for q in enriched_questions:
        is_solved = bool(q.get("is_solved"))
        q_track = q.get("track") or session_track
        for concept in q.get("concepts") or []:
            key = f"{q_track}::{concept}"
            if key not in sess_concept:
                sess_concept[key] = {
                    "concept": concept, "track": q_track, "correct": 0, "attempts": 0,
                }
            sess_concept[key]["attempts"] += 1
            if is_solved:
                sess_concept[key]["correct"] += 1

    strong = [v for v in sess_concept.values() if v["correct"] == v["attempts"] and v["attempts"] > 0]
    weak = sorted(
        [v for v in sess_concept.values() if v["correct"] < v["attempts"] and v["attempts"] > 0],
        key=lambda x: (x["correct"] / x["attempts"], -x["attempts"]),
    )

    # ── 1. Headline ──────────────────────────────────────────────────────────
    accuracy = solved_count / total_count

    if accuracy == 1.0:
        score_part = (
            "Perfect session — all questions solved"
            if total_count > 1
            else "Perfect session — question solved"
        )
    elif accuracy >= 0.67:
        score_part = f"Solid session — {solved_count} of {total_count} solved"
    elif accuracy >= 0.34:
        score_part = f"Partial session — {solved_count} of {total_count} solved"
    else:
        score_part = f"Tough session — {solved_count} of {total_count} solved"

    time_part = ""
    if time_used_s is not None and time_limit_s:
        ratio = time_used_s / time_limit_s
        if ratio < 0.5 and accuracy == 1.0:
            time_part = ", finishing well inside the time limit"
        elif ratio < 0.65 and accuracy >= 0.67:
            time_part = " with time to spare"
        elif ratio > 0.92:
            time_part = ", right up to the time limit"

    headline = score_part + time_part + "."

    # ── 2. Patterns ──────────────────────────────────────────────────────────
    patterns: list[str] = []

    # Strong concepts
    if strong and len(strong) <= 2:
        names = " and ".join(c["concept"] for c in strong[:2])
        patterns.append(f"You handled {names} confidently.")
    elif strong and len(strong) > 2:
        patterns.append(f"You were solid across {len(strong)} concepts — the gaps are narrow and specific.")

    # Weak concepts
    if weak:
        top = weak[0]
        name = top["concept"]
        hist_correct, hist_attempts = hist_concept.get((top["track"], name), (0, 0))
        is_known_weak = hist_attempts >= 3 and (hist_correct / hist_attempts) < 0.6

        if top["correct"] == 0:
            if is_known_weak:
                patterns.append(
                    f"{name} remains your toughest area — the same gap showed up again. "
                    "This is your highest-priority concept right now."
                )
            else:
                patterns.append(
                    f"Every question involving {name} went unsolved — "
                    "this is the clearest gap from this session."
                )
        else:
            pct = int(100 * top["correct"] / top["attempts"])
            if is_known_weak:
                patterns.append(
                    f"You got {top['correct']} of {top['attempts']} {name} questions right, "
                    "but your history shows this concept still needs deliberate work."
                )
            else:
                patterns.append(
                    f"{name} was inconsistent ({pct}% this session). "
                    "Try articulating the approach before writing code next time."
                )

    # Follow-up performance
    follow_ups = [q for q in enriched_questions if q.get("is_follow_up")]
    if follow_ups:
        fu_solved = sum(1 for q in follow_ups if q.get("is_solved"))
        if fu_solved == len(follow_ups):
            patterns.append(
                "You handled the follow-up question correctly too — "
                "a good sign you can stay sharp when complexity escalates."
            )
        else:
            patterns.append(
                "The follow-up question caught you out — these harder variants "
                "expose the edges of a concept you're still internalising."
            )

    # Time-sink pattern (only meaningful with 2+ questions)
    if total_count >= 2 and time_used_s:
        timed_qs = [q for q in enriched_questions if q.get("time_spent_s") is not None]
        if timed_qs:
            max_q = max(timed_qs, key=lambda q: q["time_spent_s"])
            max_t = max_q["time_spent_s"]
            if max_t > 0 and (max_t / time_used_s) > 0.55:
                mins, secs = divmod(max_t, 60)
                t_str = f"{mins}m {secs}s" if mins else f"{secs}s"
                label = max_q.get("title") or f"Q{max_q.get('position', '?')}"
                patterns.append(
                    f'"{label}" absorbed most of your time ({t_str}) — '
                    "worth revisiting to see where you slowed down."
                )

    # ── 3. Priority action ───────────────────────────────────────────────────
    priority_action: str | None = None
    priority_path_slug: str | None = None
    priority_path_title: str | None = None
    priority_question_ids: list[int] = []

    if not weak:
        if session_difficulty == "medium":
            priority_action = (
                "You're handling this difficulty well. "
                "Try a hard session to push your ceiling."
            )
        elif session_difficulty == "hard":
            priority_action = (
                "Excellent — consistent hard-session performance is what "
                "separates interview-ready candidates. Keep the cadence up."
            )
        else:
            priority_action = (
                "Good warmup. Move to a medium or hard session for a more realistic challenge."
            )
    else:
        top = weak[0]
        concept_name = top["concept"]
        track = top["track"]
        path_lookup = _CONCEPT_PATH_INDEX.get((track, concept_name))
        if path_lookup:
            slug, title, _tier = path_lookup
            priority_path_slug = slug
            priority_path_title = title
            priority_action = f'Work through the "{title}" path to reinforce {concept_name}.'
        else:
            track_label = {"sql": "SQL", "python": "Python", "python-data": "Pandas", "pyspark": "PySpark"}.get(track, track)
            priority_action = (
                f"Drill {concept_name} in {track_label} practice mode — "
                "filter by that concept tag and aim for 3 consecutive correct answers."
            )

        # Recommend unseen drill questions
        candidate_qs = _CONCEPT_QUESTION_INDEX.get(top["track"], {}).get(concept_name, [])
        priority_question_ids = [
            int(q["id"]) for q in candidate_qs if int(q["id"]) not in session_q_ids
        ][:2]

    return {
        "headline": headline,
        "patterns": [p for p in patterns if p],
        "priority_action": priority_action,
        "priority_path_slug": priority_path_slug,
        "priority_path_title": priority_path_title,
        "priority_question_ids": priority_question_ids,
    }
