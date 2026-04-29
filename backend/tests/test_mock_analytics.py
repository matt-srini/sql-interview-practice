"""
Tests for mock history analytics.

Pure unit tests for _compute_mock_analytics() cover all computation
branches without touching the database. Integration tests verify the
/api/mock/analytics endpoint enforces plan gating and returns the
correct response shape.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dt(days_ago: float = 0, hours_ago: float = 0) -> str:
    """Return an ISO-8601 UTC string offset by the given delta from now."""
    t = datetime.now(UTC) - timedelta(days=days_ago, hours=hours_ago)
    return t.isoformat()


def _session(
    *,
    solved: int,
    total: int,
    track: str = "sql",
    difficulty: str = "medium",
    status: str = "completed",
    days_ago: float = 1.0,
    time_limit_s: int = 1800,
    duration_s: int | None = None,
) -> dict:
    """Build a minimal mock_history session dict."""
    ended = datetime.now(UTC) - timedelta(days=days_ago)
    started = ended - timedelta(seconds=duration_s if duration_s is not None else time_limit_s // 2)
    return {
        "id": id(track),  # arbitrary unique-ish value
        "mode": "30min",
        "track": track,
        "difficulty": difficulty,
        "status": status,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "time_limit_s": time_limit_s,
        "solved_count": solved,
        "total_count": total,
    }


def _event(
    *,
    track: str = "sql",
    question_id: int = 1,
    is_correct: bool = True,
    days_ago: float = 0.5,
) -> dict:
    """Build a minimal submission event dict."""
    return {
        "track": track,
        "question_id": question_id,
        "is_correct": is_correct,
        "submitted_at": datetime.now(UTC) - timedelta(days=days_ago),
    }


# ── Pure unit tests for _compute_mock_analytics ───────────────────────────────

class TestComputeMockAnalyticsEmpty:

    def test_empty_sessions_returns_zero_stats(self) -> None:
        from routers.mock import _compute_mock_analytics
        result = _compute_mock_analytics([], [])
        assert result["total_sessions"] == 0
        assert result["sessions_last_30d"] == 0
        assert result["avg_score_pct"] == 0.0
        assert result["best_score_pct"] == 0.0
        assert result["avg_time_used_pct"] == 0.0
        assert result["score_trend"] == []
        assert result["top_concepts"] == []
        assert result["weak_concepts"] == []

    def test_non_completed_sessions_ignored(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=3, status="in_progress"),
            _session(solved=0, total=0, status="completed"),  # total=0 also ignored
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["total_sessions"] == 0

    def test_empty_events_no_concept_data(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=2, total=3)]
        result = _compute_mock_analytics(sessions, [])
        assert result["top_concepts"] == []
        assert result["weak_concepts"] == []


class TestComputeMockAnalyticsScores:

    def test_avg_score_computed_correctly(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=4),   # 50%
            _session(solved=3, total=4),   # 75%
            _session(solved=4, total=4),   # 100%
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["avg_score_pct"] == pytest.approx(75.0, abs=0.2)

    def test_best_score_is_max(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=1, total=4),   # 25%
            _session(solved=4, total=4),   # 100%
            _session(solved=2, total=4),   # 50%
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["best_score_pct"] == 100.0

    def test_total_sessions_counts_completed_only(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=3, status="completed"),
            _session(solved=1, total=3, status="completed"),
            _session(solved=0, total=3, status="in_progress"),
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["total_sessions"] == 2

    def test_perfect_score_session(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=3, total=3)]
        result = _compute_mock_analytics(sessions, [])
        assert result["avg_score_pct"] == 100.0
        assert result["best_score_pct"] == 100.0

    def test_zero_score_session(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=0, total=3)]
        result = _compute_mock_analytics(sessions, [])
        assert result["avg_score_pct"] == 0.0
        assert result["best_score_pct"] == 0.0


class TestComputeMockAnalyticsRecentFilter:

    def test_sessions_last_30d_filters_correctly(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=3, days_ago=5),    # within 30d
            _session(solved=2, total=3, days_ago=15),   # within 30d
            _session(solved=2, total=3, days_ago=31),   # outside 30d
            _session(solved=2, total=3, days_ago=60),   # outside 30d
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["sessions_last_30d"] == 2
        assert result["total_sessions"] == 4  # all 4 still count for total

    def test_sessions_last_30d_all_recent(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=1, total=2, days_ago=i) for i in range(1, 6)]
        result = _compute_mock_analytics(sessions, [])
        assert result["sessions_last_30d"] == 5

    def test_sessions_last_30d_none_recent(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=1, total=2, days_ago=40 + i) for i in range(3)]
        result = _compute_mock_analytics(sessions, [])
        assert result["sessions_last_30d"] == 0


class TestComputeMockAnalyticsScoreTrend:

    def test_score_trend_chronological_order(self) -> None:
        from routers.mock import _compute_mock_analytics
        # Session 1 is oldest (most days ago), session 5 is most recent
        sessions = [
            _session(solved=1, total=4, days_ago=5),   # 25%
            _session(solved=2, total=4, days_ago=4),   # 50%
            _session(solved=3, total=4, days_ago=3),   # 75%
            _session(solved=4, total=4, days_ago=2),   # 100%
        ]
        result = _compute_mock_analytics(sessions, [])
        trend = result["score_trend"]
        assert trend == sorted(trend), "Score trend should be chronological (ascending time = ascending index)"

    def test_score_trend_capped_at_last_10(self) -> None:
        from routers.mock import _compute_mock_analytics
        # 15 completed sessions
        sessions = [_session(solved=2, total=4, days_ago=15 - i) for i in range(15)]
        result = _compute_mock_analytics(sessions, [])
        assert len(result["score_trend"]) == 10

    def test_score_trend_all_sessions_when_fewer_than_10(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [_session(solved=i + 1, total=4, days_ago=5 - i) for i in range(4)]
        result = _compute_mock_analytics(sessions, [])
        assert len(result["score_trend"]) == 4


class TestComputeMockAnalyticsBreakdowns:

    def test_track_breakdown_groups_by_track(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=4, track="sql"),
            _session(solved=4, total=4, track="sql"),
            _session(solved=3, total=4, track="python"),
        ]
        result = _compute_mock_analytics(sessions, [])
        tb = result["track_breakdown"]
        assert "sql" in tb
        assert "python" in tb
        assert tb["sql"]["sessions"] == 2
        assert tb["python"]["sessions"] == 1
        assert tb["sql"]["avg_score_pct"] == pytest.approx(75.0, abs=0.2)
        assert tb["python"]["avg_score_pct"] == 75.0

    def test_difficulty_breakdown_groups_by_difficulty(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            _session(solved=2, total=4, difficulty="easy"),
            _session(solved=2, total=4, difficulty="easy"),
            _session(solved=4, total=4, difficulty="hard"),
        ]
        result = _compute_mock_analytics(sessions, [])
        db = result["difficulty_breakdown"]
        assert db["easy"]["sessions"] == 2
        assert db["hard"]["sessions"] == 1

    def test_avg_time_used_pct_computed_from_start_end(self) -> None:
        from routers.mock import _compute_mock_analytics
        # Session used exactly half the time_limit
        sessions = [_session(solved=2, total=4, time_limit_s=1800, duration_s=900)]
        result = _compute_mock_analytics(sessions, [])
        # Should be ~50%
        assert 40.0 <= result["avg_time_used_pct"] <= 60.0

    def test_avg_time_used_pct_zero_when_no_timestamps(self) -> None:
        from routers.mock import _compute_mock_analytics
        sessions = [
            {"id": 1, "status": "completed", "total_count": 3, "solved_count": 2,
             "track": "sql", "difficulty": "medium", "started_at": None, "ended_at": None,
             "time_limit_s": 1800}
        ]
        result = _compute_mock_analytics(sessions, [])
        assert result["avg_time_used_pct"] == 0.0


class TestComputeMockAnalyticsConcepts:

    def test_top_concepts_sorted_by_attempt_count(self) -> None:
        from routers.mock import _compute_mock_analytics

        # _compute_mock_analytics returns early when completed sessions list is empty,
        # so we need at least one completed session for event processing to run.
        dummy_session = [_session(solved=2, total=3)]

        synthetic_lookup = {
            "sql": {
                1: ["WINDOW FUNCTIONS"],
                2: ["CTEs"],
                3: ["JOINS"],
                4: ["WINDOW FUNCTIONS"],
                5: ["WINDOW FUNCTIONS"],
            }
        }
        events = [
            _event(track="sql", question_id=1, is_correct=True),
            _event(track="sql", question_id=2, is_correct=True),
            _event(track="sql", question_id=3, is_correct=True),
            _event(track="sql", question_id=4, is_correct=True),
            _event(track="sql", question_id=5, is_correct=False),
        ]
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics(dummy_session, events)

        top = result["top_concepts"]
        assert len(top) > 0
        # WINDOW FUNCTIONS should be first (3 attempts)
        assert top[0]["concept"] == "WINDOW FUNCTIONS"
        assert top[0]["attempted"] == 3

    def test_weak_concepts_require_3_attempts_and_below_60_pct(self) -> None:
        from routers.mock import _compute_mock_analytics

        dummy_session = [_session(solved=2, total=3)]

        synthetic_lookup = {
            "sql": {
                1: ["SUBQUERIES"],
                2: ["SUBQUERIES"],
                3: ["SUBQUERIES"],   # 3 attempts total
                4: ["JOINS"],
                5: ["JOINS"],
                6: ["JOINS"],        # 3 attempts total
            }
        }
        events = [
            # SUBQUERIES: 1 correct / 3 attempts = 33% → weak
            _event(track="sql", question_id=1, is_correct=True),
            _event(track="sql", question_id=2, is_correct=False),
            _event(track="sql", question_id=3, is_correct=False),
            # JOINS: 3 correct / 3 attempts = 100% → not weak
            _event(track="sql", question_id=4, is_correct=True),
            _event(track="sql", question_id=5, is_correct=True),
            _event(track="sql", question_id=6, is_correct=True),
        ]
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics(dummy_session, events)

        weak = result["weak_concepts"]
        weak_names = [w["concept"] for w in weak]
        assert "SUBQUERIES" in weak_names
        assert "JOINS" not in weak_names

    def test_concepts_below_3_attempts_not_included(self) -> None:
        from routers.mock import _compute_mock_analytics

        synthetic_lookup = {"sql": {1: ["RARE_CONCEPT"], 2: ["RARE_CONCEPT"]}}
        events = [
            _event(track="sql", question_id=1, is_correct=False),
            _event(track="sql", question_id=2, is_correct=False),
        ]
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics([], events)

        all_concept_names = [c["concept"] for c in result["top_concepts"] + result["weak_concepts"]]
        assert "RARE_CONCEPT" not in all_concept_names

    def test_weak_concepts_sorted_worst_first(self) -> None:
        from routers.mock import _compute_mock_analytics

        dummy_session = [_session(solved=2, total=3)]

        # Concept A: 0/3 = 0%, Concept B: 1/3 = 33%
        synthetic_lookup = {
            "sql": {
                10: ["A"], 11: ["A"], 12: ["A"],
                20: ["B"], 21: ["B"], 22: ["B"],
            }
        }
        events = (
            [_event(track="sql", question_id=i, is_correct=False) for i in [10, 11, 12]]
            + [_event(track="sql", question_id=20, is_correct=True)]
            + [_event(track="sql", question_id=i, is_correct=False) for i in [21, 22]]
        )
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics(dummy_session, events)

        weak = result["weak_concepts"]
        assert len(weak) >= 2
        assert weak[0]["concept"] == "A", "Worst concept should be first"
        assert weak[0]["accuracy_pct"] < weak[1]["accuracy_pct"]

    def test_weak_concepts_capped_at_3(self) -> None:
        from routers.mock import _compute_mock_analytics

        # Create 5 concepts, each with 3 attempts and 0% accuracy
        concept_lookup: dict[int, list[str]] = {}
        events = []
        for i in range(5):
            concept_name = f"WEAK_CONCEPT_{i}"
            qids = [i * 3 + 1, i * 3 + 2, i * 3 + 3]
            for qid in qids:
                concept_lookup[qid] = [concept_name]
                events.append(_event(track="sql", question_id=qid, is_correct=False))

        synthetic_lookup = {"sql": concept_lookup}
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics([], events)

        assert len(result["weak_concepts"]) <= 3

    def test_top_concepts_capped_at_5(self) -> None:
        from routers.mock import _compute_mock_analytics

        concept_lookup: dict[int, list[str]] = {}
        events = []
        for i in range(8):
            concept_name = f"CONCEPT_{i}"
            qids = [i * 3 + 1, i * 3 + 2, i * 3 + 3]
            for qid in qids:
                concept_lookup[qid] = [concept_name]
                events.append(_event(track="sql", question_id=qid, is_correct=True))

        synthetic_lookup = {"sql": concept_lookup}
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics([], events)

        assert len(result["top_concepts"]) <= 5

    def test_concept_accuracy_pct_is_0_to_100(self) -> None:
        from routers.mock import _compute_mock_analytics

        synthetic_lookup = {"sql": {1: ["TEST"], 2: ["TEST"], 3: ["TEST"]}}
        events = [
            _event(track="sql", question_id=1, is_correct=True),
            _event(track="sql", question_id=2, is_correct=False),
            _event(track="sql", question_id=3, is_correct=False),
        ]
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics([], events)

        for c in result["top_concepts"] + result["weak_concepts"]:
            assert 0 <= c["accuracy_pct"] <= 100


class TestComputeMockAnalyticsResponseShape:

    def test_all_required_keys_present(self) -> None:
        from routers.mock import _compute_mock_analytics
        result = _compute_mock_analytics([_session(solved=2, total=3)], [])
        expected_keys = {
            "total_sessions", "sessions_last_30d", "avg_score_pct", "best_score_pct",
            "avg_time_used_pct", "track_breakdown", "difficulty_breakdown",
            "score_trend", "top_concepts", "weak_concepts",
        }
        assert expected_keys.issubset(result.keys()), (
            f"Missing keys: {expected_keys - result.keys()}"
        )

    def test_concept_entries_have_required_fields(self) -> None:
        from routers.mock import _compute_mock_analytics
        synthetic_lookup = {"sql": {1: ["WIN"], 2: ["WIN"], 3: ["WIN"]}}
        events = [_event(track="sql", question_id=i, is_correct=True) for i in [1, 2, 3]]
        with patch("routers.mock._CONCEPTS_LOOKUP", synthetic_lookup):
            result = _compute_mock_analytics([], events)
        for entry in result["top_concepts"]:
            assert {"concept", "correct", "attempted", "accuracy_pct"}.issubset(entry.keys())


# ── Integration tests for GET /api/mock/analytics ────────────────────────────

_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    global _counter
    _counter += 1
    email = f"analytics-test-{_counter}@internal.test"
    client.get("/api/catalog")  # seed session cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Analytics Test", "password": "Password123"},
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


class TestAnalyticsEndpointPlanGating:

    def test_free_user_returns_403(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 403

    def test_pro_user_returns_403(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 403

    def test_elite_user_returns_200(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 200

    def test_lifetime_elite_returns_200(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 200

    def test_lifetime_pro_returns_403(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 403

    def test_unauthenticated_returns_401_or_403(self) -> None:
        with TestClient(app) as client:
            r = client.get("/api/mock/analytics")
        assert r.status_code in (401, 403)


class TestAnalyticsEndpointResponseShape:

    def test_elite_user_with_no_history_returns_zero_stats(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 200
        body = r.json()
        assert body["total_sessions"] == 0
        assert body["sessions_last_30d"] == 0
        assert body["avg_score_pct"] == 0.0
        assert body["best_score_pct"] == 0.0
        assert body["score_trend"] == []
        assert body["top_concepts"] == []
        assert body["weak_concepts"] == []

    def test_response_has_all_required_keys(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.get("/api/mock/analytics")
        assert r.status_code == 200
        body = r.json()
        required = {
            "total_sessions", "sessions_last_30d", "avg_score_pct", "best_score_pct",
            "avg_time_used_pct", "track_breakdown", "difficulty_breakdown",
            "score_trend", "top_concepts", "weak_concepts",
        }
        assert required.issubset(body.keys()), f"Missing: {required - body.keys()}"
