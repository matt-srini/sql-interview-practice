"""
Dashboard feature tests.

Covers:
  GET /api/dashboard          — track overview, recent activity, concepts_by_track
  GET /api/dashboard/insights — per-track stats, weakest concepts, cross-track insight,
                                streak_days, 60-second in-process cache

Uses the same patterns as the rest of the test suite: synchronous TestClient,
`isolated_state` fixture from conftest.py, and a shared _insert_submission helper
that bypasses the HTTP layer for deterministic test data.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest
from fastapi.testclient import TestClient

import backend.main as main
import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_questions

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_TRACK_MODULES = {
    "sql": sql_questions,
    "python": python_questions,
    "python-data": python_data_questions,
    "pyspark": pyspark_questions,
}

# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------

_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    """Register a new user with the given plan. Returns the user dict."""
    global _counter
    _counter += 1
    email = f"dash-test-{_counter}@internal.test"
    client.get("/api/catalog")  # seed anonymous session
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": f"Dash Test {plan}", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, up.text
        user["plan"] = plan
    return user


def _db_conn() -> "psycopg2.connection":
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test"
    )
    return psycopg2.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))


def _insert_submission(
    user_id: str,
    *,
    track: str,
    question_id: int,
    is_correct: bool,
    submitted_at: datetime,
) -> None:
    """Write a row to the submissions table (read by /api/dashboard/insights)."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO submissions (user_id, track, question_id, is_correct, code, submitted_at)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (user_id, track, question_id, is_correct, "-- test", submitted_at),
            )
        conn.commit()
    finally:
        conn.close()


def _insert_progress(
    user_id: str,
    *,
    track: str,
    question_id: int,
    solved_at: datetime | None = None,
) -> None:
    """Write a row to the user_progress table (read by /api/dashboard)."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_progress (user_id, question_id, topic, solved_at)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (user_id, question_id, topic) DO UPDATE SET solved_at = EXCLUDED.solved_at
                """,
                (user_id, question_id, track, solved_at or datetime.now(timezone.utc)),
            )
        conn.commit()
    finally:
        conn.close()


def _pick_sql_ids() -> tuple[int, int]:
    """Return two distinct SQL easy question IDs; q1 is guaranteed to have concepts."""
    easy = sql_questions.get_questions_by_difficulty()["easy"]
    q1 = next(q for q in easy if q.get("concepts"))
    q2 = next(q for q in easy if int(q["id"]) != int(q1["id"]))
    return int(q1["id"]), int(q2["id"])


def _pick_first_id(track: str) -> int:
    """Return any question ID from the easy tier of the given track."""
    slug = track.replace("-", "_") if track != "python-data" else "python_data"
    module_map = {
        "sql": sql_questions,
        "python": python_questions,
        "python_data": python_data_questions,
        "pyspark": pyspark_questions,
    }
    module = module_map.get(slug) or module_map.get(track)
    easy = module.get_questions_by_difficulty()["easy"]
    return int(easy[0]["id"])


# ===========================================================================
# /api/dashboard — track overview
# ===========================================================================


class TestDashboardEndpoint:
    def test_returns_expected_top_level_keys(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/dashboard")
            assert r.status_code == 200, r.text
            data = r.json()
            assert "tracks" in data
            assert "recent_activity" in data
            assert "concepts_by_track" in data

    def test_all_four_tracks_present(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            data = client.get("/api/dashboard").json()
            assert set(data["tracks"].keys()) == {"sql", "python", "python-data", "pyspark"}

    def test_track_totals_match_catalog(self) -> None:
        """Totals returned for each track must match the actual catalog size."""
        expected = {
            "sql": 95,
            "python": 83,
            "python-data": 82,
            "pyspark": 90,
        }
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            data = client.get("/api/dashboard").json()
            for track, expected_total in expected.items():
                got = data["tracks"][track]["total"]
                assert got == expected_total, f"{track}: expected {expected_total}, got {got}"

    def test_by_difficulty_shape(self) -> None:
        """Each by_difficulty entry must be {solved: int, total: int}."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            data = client.get("/api/dashboard").json()
            for track, track_data in data["tracks"].items():
                for diff, val in track_data["by_difficulty"].items():
                    assert isinstance(val, dict), f"{track}.{diff}: expected dict"
                    assert isinstance(val["solved"], int)
                    assert isinstance(val["total"], int)
                    assert val["solved"] >= 0
                    assert val["total"] > 0

    def test_solved_count_reflects_submissions(self) -> None:
        """Solving a question must increment the track solved counter."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            q_id = _pick_first_id("sql")
            _insert_progress(user["id"], track="sql", question_id=q_id)
            data = client.get("/api/dashboard").json()
            assert data["tracks"]["sql"]["solved"] == 1

    def test_python_data_slug_is_remapped(self) -> None:
        """Backend stores 'python_data'; dashboard must return 'python-data'."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            data = client.get("/api/dashboard").json()
            assert "python-data" in data["tracks"], "python_data must be remapped to python-data"
            assert "python_data" not in data["tracks"], "raw python_data key must not appear"

    def test_recent_activity_empty_for_new_user(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            data = client.get("/api/dashboard").json()
            assert data["recent_activity"] == []

    def test_recent_activity_populated_after_solve(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            q_id = _pick_first_id("sql")
            _insert_progress(user["id"], track="sql", question_id=q_id)
            data = client.get("/api/dashboard").json()
            assert len(data["recent_activity"]) == 1
            row = data["recent_activity"][0]
            assert row["topic"] == "sql"
            assert row["question_id"] == q_id
            assert "title" in row
            assert "difficulty" in row
            assert "solved_at" in row

    def test_recent_activity_topic_remapped(self) -> None:
        """Activity rows for python-data must use the hyphenated slug."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            q_id = _pick_first_id("python-data")
            _insert_progress(user["id"], track="python-data", question_id=q_id)
            data = client.get("/api/dashboard").json()
            topics = [row["topic"] for row in data["recent_activity"]]
            assert "python-data" in topics
            assert "python_data" not in topics

    def test_recent_activity_capped_at_10(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            easy = sql_questions.get_questions_by_difficulty()["easy"]
            ids = [int(q["id"]) for q in easy[:12]]
            now = datetime.now(timezone.utc)
            for i, qid in enumerate(ids):
                _insert_progress(
                    user["id"], track="sql", question_id=qid,
                    solved_at=now - timedelta(minutes=i),
                )
            data = client.get("/api/dashboard").json()
            assert len(data["recent_activity"]) <= 10

    def test_concepts_by_track_empty_for_new_user(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            data = client.get("/api/dashboard").json()
            assert data["concepts_by_track"] == {}

    def test_concepts_by_track_populated_after_solve(self) -> None:
        """Solving a question with concepts must add those concepts to concepts_by_track."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            easy = sql_questions.get_questions_by_difficulty()["easy"]
            q = next(q for q in easy if q.get("concepts"))
            q_id = int(q["id"])
            _insert_progress(user["id"], track="sql", question_id=q_id)
            data = client.get("/api/dashboard").json()
            assert "sql" in data["concepts_by_track"]
            assert len(data["concepts_by_track"]["sql"]) > 0

# ===========================================================================
# /api/dashboard/insights — coaching metrics
# ===========================================================================


class TestInsightsEndpoint:
    def test_returns_expected_shape(self) -> None:
        with TestClient(app) as client:
            _make_user(client)
            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200
            payload = r.json()
            assert set(payload.keys()) == {
                "per_track",
                "weakest_concepts",
                "cross_track_insight",
                "streak_days",
            }

    def test_per_track_has_all_four_tracks(self) -> None:
        with TestClient(app) as client:
            _make_user(client)
            payload = client.get("/api/dashboard/insights").json()
            assert set(payload["per_track"].keys()) == {"sql", "python", "python-data", "pyspark"}

    def test_per_track_fields_shape(self) -> None:
        with TestClient(app) as client:
            _make_user(client)
            payload = client.get("/api/dashboard/insights").json()
            for track, stats in payload["per_track"].items():
                assert "solve_count" in stats, f"{track}: missing solve_count"
                assert "median_solve_seconds" in stats, f"{track}: missing median_solve_seconds"
                assert "accuracy_pct" in stats, f"{track}: missing accuracy_pct"

    def test_empty_user_gets_zero_stats(self) -> None:
        with TestClient(app) as client:
            _make_user(client)
            payload = client.get("/api/dashboard/insights").json()
            for track, stats in payload["per_track"].items():
                assert stats["solve_count"] == 0
                assert stats["median_solve_seconds"] is None
                assert stats["accuracy_pct"] == 0.0
            assert payload["weakest_concepts"] == []
            assert payload["cross_track_insight"] is None
            assert payload["streak_days"] == 0

    def test_metrics_computed_correctly(self) -> None:
        """Full metrics test: solve_count, median_solve_seconds, accuracy_pct."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            assert catalog_resp.status_code == 200
            user_id = catalog_resp.json()["user_id"]

            q1, q2 = _pick_sql_ids()
            now = datetime.now(timezone.utc)

            # SQL q1: 3 attempts, 1 correct (at 12 min) → duration = 12 min = 720s
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=32))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=28))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now - timedelta(minutes=20))

            # SQL q2: 1 attempt correct after 10 min → duration = 10 min = 600s
            # median([720, 600]) = 660s
            _insert_submission(user_id, track="sql", question_id=q2, is_correct=False,
                                submitted_at=now - timedelta(minutes=12))
            _insert_submission(user_id, track="sql", question_id=q2, is_correct=True,
                                submitted_at=now - timedelta(minutes=2))

            # Python: 1 min solve (60s)
            _insert_submission(user_id, track="python", question_id=2001, is_correct=False,
                                submitted_at=now - timedelta(minutes=6))
            _insert_submission(user_id, track="python", question_id=2001, is_correct=True,
                                submitted_at=now - timedelta(minutes=5))

            payload = client.get("/api/dashboard/insights").json()

            sql_stats = payload["per_track"]["sql"]
            assert sql_stats["solve_count"] == 2
            assert sql_stats["median_solve_seconds"] == 660
            # 3 attempts on q1 + 2 on q2 = 5 total; 2 correct → 0.4
            assert sql_stats["accuracy_pct"] == 0.4

            python_stats = payload["per_track"]["python"]
            assert python_stats["solve_count"] == 1
            assert python_stats["median_solve_seconds"] == 60
            assert python_stats["accuracy_pct"] == 0.5

    def test_streak_days_zero_for_new_user(self) -> None:
        with TestClient(app) as client:
            _make_user(client)
            payload = client.get("/api/dashboard/insights").json()
            assert payload["streak_days"] == 0

    def test_streak_days_increments_on_solve_today(self) -> None:
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            payload = client.get("/api/dashboard/insights").json()
            assert payload["streak_days"] == 1

    def test_streak_days_consecutive_days(self) -> None:
        """Streak must span consecutive calendar days ending today."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, q2 = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            # Solves on today, yesterday, and 2 days ago
            for days_ago in [0, 1, 2]:
                _insert_submission(
                    user_id, track="sql", question_id=q1, is_correct=True,
                    submitted_at=now - timedelta(days=days_ago, hours=1),
                )
            payload = client.get("/api/dashboard/insights").json()
            assert payload["streak_days"] == 3

    def test_streak_breaks_on_gap(self) -> None:
        """A gap in daily solves must break the streak."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            # Solves today and 3 days ago (skipping yesterday and 2 days ago)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now - timedelta(days=3))
            payload = client.get("/api/dashboard/insights").json()
            assert payload["streak_days"] == 1

    def test_streak_zero_when_no_solve_today(self) -> None:
        """If the most recent solve was yesterday, streak must be 0 (not 1)."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now - timedelta(days=1))
            payload = client.get("/api/dashboard/insights").json()
            assert payload["streak_days"] == 0

    def test_weakest_concepts_empty_below_3_attempts(self) -> None:
        """Concepts with fewer than 3 attempts must not appear in weakest_concepts."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            # Only 2 attempts — below the 3-attempt threshold
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=5))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            payload = client.get("/api/dashboard/insights").json()
            assert payload["weakest_concepts"] == []

    def test_weakest_concepts_appear_at_3_attempts(self) -> None:
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=10))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=5))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            payload = client.get("/api/dashboard/insights").json()
            assert len(payload["weakest_concepts"]) > 0
            w = payload["weakest_concepts"][0]
            assert w["track"] == "sql"
            assert w["attempts"] >= 3
            assert "accuracy_pct" in w
            assert "concept" in w
            # Phase 4: coaching fields
            assert "summary" in w, "weakest concept must include summary coaching text"
            assert isinstance(w["summary"], str) and len(w["summary"]) > 0

    def test_weakest_concept_summary_reflects_accuracy(self) -> None:
        """Summary text must vary based on accuracy bucket."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            # 4 wrong, 0 correct → accuracy < 0.30
            for i in range(4):
                _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                    submitted_at=now - timedelta(minutes=10 - i))
            payload = client.get("/api/dashboard/insights").json()
            assert len(payload["weakest_concepts"]) > 0
            w = payload["weakest_concepts"][0]
            assert "highest-priority" in w["summary"].lower() or "more often than not" in w["summary"].lower()

    def test_weakest_concept_recommended_question_ids_type(self) -> None:
        """recommended_question_ids, when present, must be a list of ints."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            for i in range(3):
                _insert_submission(user_id, track="sql", question_id=q1, is_correct=(i == 2),
                                    submitted_at=now - timedelta(minutes=5 - i))
            payload = client.get("/api/dashboard/insights").json()
            for w in payload["weakest_concepts"]:
                if "recommended_question_ids" in w:
                    assert isinstance(w["recommended_question_ids"], list)
                    assert all(isinstance(qid, int) for qid in w["recommended_question_ids"])
                    assert len(w["recommended_question_ids"]) <= 2

    def test_weakest_concept_recommended_question_ids_not_already_solved(self) -> None:
        """recommended_question_ids must not include questions the user has already solved."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            for i in range(3):
                _insert_submission(user_id, track="sql", question_id=q1, is_correct=(i == 2),
                                    submitted_at=now - timedelta(minutes=5 - i))
            payload = client.get("/api/dashboard/insights").json()
            for w in payload["weakest_concepts"]:
                reco_ids = w.get("recommended_question_ids", [])
                # q1 was solved (marked correct on 3rd attempt) — must not reappear as recommendation
                assert q1 not in reco_ids, f"solved question {q1} must not appear in recommendations"

    def test_weakest_concepts_capped_at_3(self) -> None:
        """At most 3 entries must be returned in weakest_concepts."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            easy = sql_questions.get_questions_by_difficulty()["easy"]
            # Pick first 5 questions that each have at least one concept
            questions_with_concepts = [q for q in easy if q.get("concepts")][:5]
            now = datetime.now(timezone.utc)
            for i, q in enumerate(questions_with_concepts):
                q_id = int(q["id"])
                for j in range(3):
                    _insert_submission(
                        user_id, track="sql", question_id=q_id, is_correct=(j == 2),
                        submitted_at=now - timedelta(minutes=100 - i * 10 - j),
                    )
            payload = client.get("/api/dashboard/insights").json()
            assert len(payload["weakest_concepts"]) <= 3

    def test_cross_track_insight_none_with_single_track(self) -> None:
        """With only one track having data, cross_track_insight must be None."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            payload = client.get("/api/dashboard/insights").json()
            assert payload["cross_track_insight"] is None

    def test_cross_track_insight_none_when_gap_below_60s(self) -> None:
        """When the gap between fastest and slowest track is < 60s, insight must be None."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            # SQL: 30s solve
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(seconds=30))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            # Python: 20s solve (gap = 10s < 60s)
            _insert_submission(user_id, track="python", question_id=2001, is_correct=False,
                                submitted_at=now - timedelta(seconds=20))
            _insert_submission(user_id, track="python", question_id=2001, is_correct=True,
                                submitted_at=now)
            payload = client.get("/api/dashboard/insights").json()
            assert payload["cross_track_insight"] is None

    def test_cross_track_insight_fires_when_gap_exceeds_60s(self) -> None:
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, q2 = _pick_sql_ids()
            now = datetime.now(timezone.utc)

            # SQL: ~11 min median
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=32))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now - timedelta(minutes=28))
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now - timedelta(minutes=20))
            _insert_submission(user_id, track="sql", question_id=q2, is_correct=False,
                                submitted_at=now - timedelta(minutes=12))
            _insert_submission(user_id, track="sql", question_id=q2, is_correct=True,
                                submitted_at=now - timedelta(minutes=2))

            # Python: 1 min solve
            _insert_submission(user_id, track="python", question_id=2001, is_correct=False,
                                submitted_at=now - timedelta(minutes=6))
            _insert_submission(user_id, track="python", question_id=2001, is_correct=True,
                                submitted_at=now - timedelta(minutes=5))

            payload = client.get("/api/dashboard/insights").json()
            insight = payload["cross_track_insight"]
            assert isinstance(insight, str)
            assert "SQL" in insight and "Python" in insight

    def test_cache_returns_stale_data_within_60s(self) -> None:
        """A second request within 60 s must return the cached payload unchanged."""
        with TestClient(app) as client:
            catalog_resp = client.get("/api/catalog")
            user_id = catalog_resp.json()["user_id"]
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)

            _insert_submission(user_id, track="sql", question_id=q1, is_correct=True,
                                submitted_at=now - timedelta(minutes=1))

            first = client.get("/api/dashboard/insights").json()

            # Insert a new submission immediately — must not affect the cached response
            _insert_submission(user_id, track="sql", question_id=q1, is_correct=False,
                                submitted_at=now)

            second = client.get("/api/dashboard/insights").json()
            assert first == second

    def test_cache_is_per_user(self) -> None:
        """Cache entries must be scoped to individual users."""
        with TestClient(app) as client:
            # User A gets a solve
            user_a = _make_user(client, plan="free")
            q1, _ = _pick_sql_ids()
            now = datetime.now(timezone.utc)
            _insert_submission(user_a["id"], track="sql", question_id=q1, is_correct=True,
                                submitted_at=now)
            payload_a = client.get("/api/dashboard/insights").json()

        # User B in a separate client — must get independent (zero) stats
        with TestClient(app) as client2:
            _make_user(client2, plan="free")
            payload_b = client2.get("/api/dashboard/insights").json()

        assert payload_a["per_track"]["sql"]["solve_count"] == 1
        assert payload_b["per_track"]["sql"]["solve_count"] == 0

    def test_lifetime_plans_can_access_insights(self) -> None:
        """lifetime_pro and lifetime_elite must be able to call /api/dashboard/insights."""
        for plan in ("lifetime_pro", "lifetime_elite"):
            with TestClient(app) as client:
                _make_user(client, plan=plan)
                r = client.get("/api/dashboard/insights")
                assert r.status_code == 200, f"{plan}: expected 200, got {r.status_code}: {r.text}"
