import os
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest
from fastapi.testclient import TestClient

import backend.main as main
import questions


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _db_conn():
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test")
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(sync_url)


def _insert_submission(
    user_id: str,
    *,
    track: str,
    question_id: int,
    is_correct: bool,
    submitted_at: datetime,
) -> None:
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


def _pick_sql_question_ids() -> tuple[int, int]:
    grouped = questions.get_questions_by_difficulty()
    easy = grouped["easy"]

    # Ensure Q1 has at least one concept so weakest_concepts can be produced.
    q1 = next(q for q in easy if q.get("concepts"))
    q2 = next(q for q in easy if int(q["id"]) != int(q1["id"]))
    return int(q1["id"]), int(q2["id"])


def test_dashboard_insights_returns_expected_shape_and_metrics() -> None:
    with TestClient(app) as client:
        # create session + anonymous user
        catalog_resp = client.get("/api/catalog")
        assert catalog_resp.status_code == 200
        user_id = catalog_resp.json()["user_id"]

        q1, q2 = _pick_sql_question_ids()

        now = datetime.now(timezone.utc)

        # SQL question 1: 3 attempts, 1 correct -> concept attempts >=3, accuracy 1/3
        _insert_submission(user_id, track="sql", question_id=q1, is_correct=False, submitted_at=now - timedelta(minutes=32))
        _insert_submission(user_id, track="sql", question_id=q1, is_correct=False, submitted_at=now - timedelta(minutes=28))
        _insert_submission(user_id, track="sql", question_id=q1, is_correct=True, submitted_at=now - timedelta(minutes=20))

        # SQL question 2: correct after 10 minutes -> median between 12m and 10m = 11m
        _insert_submission(user_id, track="sql", question_id=q2, is_correct=False, submitted_at=now - timedelta(minutes=12))
        _insert_submission(user_id, track="sql", question_id=q2, is_correct=True, submitted_at=now - timedelta(minutes=2))

        # Python: quick solve to force cross-track gap against SQL
        _insert_submission(user_id, track="python", question_id=2001, is_correct=False, submitted_at=now - timedelta(minutes=6))
        _insert_submission(user_id, track="python", question_id=2001, is_correct=True, submitted_at=now - timedelta(minutes=5))

        insights_resp = client.get("/api/dashboard/insights")
        assert insights_resp.status_code == 200
        payload = insights_resp.json()

        assert set(payload.keys()) == {
            "per_track",
            "weakest_concepts",
            "cross_track_insight",
            "streak_days",
        }

        sql_stats = payload["per_track"]["sql"]
        assert sql_stats["solve_count"] == 2
        assert sql_stats["median_solve_seconds"] == 660
        assert sql_stats["accuracy_pct"] == 0.4

        python_stats = payload["per_track"]["python"]
        assert python_stats["solve_count"] == 1
        assert python_stats["median_solve_seconds"] == 60
        assert python_stats["accuracy_pct"] == 0.5

        assert payload["streak_days"] == 1

        assert isinstance(payload["weakest_concepts"], list)
        assert payload["weakest_concepts"]
        weakest = payload["weakest_concepts"][0]
        assert weakest["track"] == "sql"
        assert weakest["attempts"] >= 3
        assert weakest["accuracy_pct"] <= 0.5

        insight = payload["cross_track_insight"]
        assert isinstance(insight, str)
        assert "Python" in insight and "SQL" in insight


def test_dashboard_insights_cache_is_used_for_60s() -> None:
    with TestClient(app) as client:
        catalog_resp = client.get("/api/catalog")
        user_id = catalog_resp.json()["user_id"]
        q1, _ = _pick_sql_question_ids()

        now = datetime.now(timezone.utc)
        _insert_submission(user_id, track="sql", question_id=q1, is_correct=True, submitted_at=now - timedelta(minutes=1))

        first = client.get("/api/dashboard/insights")
        assert first.status_code == 200
        first_payload = first.json()

        # Add a new event immediately; response should stay cached.
        _insert_submission(user_id, track="sql", question_id=q1, is_correct=False, submitted_at=now)
        second = client.get("/api/dashboard/insights")
        assert second.status_code == 200
        second_payload = second.json()

        assert first_payload == second_payload
