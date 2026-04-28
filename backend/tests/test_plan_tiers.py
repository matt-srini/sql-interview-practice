"""
Plan-tier integration tests.

Verifies that the API correctly enforces access gates for free / pro / elite
users across catalog unlock state, mock session limits, and dashboard shape.

These are complementary to test_unlock.py (which tests the pure policy function
in isolation) — here we exercise the full HTTP stack with a real DB.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _make_user(client: TestClient, plan: str = "free", suffix: str = "") -> dict:
    """Register a user and optionally upgrade their plan. Returns the user dict."""
    global _counter
    _counter += 1
    email = f"tier-test-{_counter}{suffix}@internal.test"
    client.get("/api/catalog")  # seed anonymous session cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": f"Tier Test {plan}", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    assert user["plan"] == "free"

    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, up.text
        user["plan"] = plan

    return user


def _catalog_states(client: TestClient, endpoint: str = "/api/catalog") -> dict[str, list[str]]:
    """Return {difficulty: [state, ...]} for all questions in a catalog endpoint."""
    resp = client.get(endpoint)
    assert resp.status_code == 200, resp.text
    result: dict[str, list[str]] = {}
    for group in resp.json()["groups"]:
        result[group["difficulty"]] = [q["state"] for q in group["questions"]]
    return result


def _start_mock(client: TestClient, difficulty: str = "hard", track: str = "sql") -> tuple[int, dict]:
    resp = client.post(
        "/api/mock/start",
        json={"mode": "30min", "track": track, "difficulty": difficulty},
    )
    return resp.status_code, resp.json()


# ---------------------------------------------------------------------------
# Catalog: free tier
# ---------------------------------------------------------------------------

class TestFreeCatalog:
    def test_sql_easy_all_unlocked_medium_hard_all_locked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            states = _catalog_states(client, "/api/catalog")

            assert all(s == "unlocked" for s in states["easy"]), "free: all easy should be unlocked"
            assert all(s == "locked" for s in states["medium"]), "free: all medium should be locked with 0 solves"
            assert all(s == "locked" for s in states["hard"]), "free: all hard should be locked with 0 solves"

    def test_python_easy_unlocked_medium_hard_locked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            states = _catalog_states(client, "/api/python/catalog")
            assert all(s == "unlocked" for s in states["easy"])
            assert all(s == "locked" for s in states["medium"])
            assert all(s == "locked" for s in states["hard"])

    def test_pyspark_easy_unlocked_medium_hard_locked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            states = _catalog_states(client, "/api/pyspark/catalog")
            assert all(s == "unlocked" for s in states["easy"])
            assert all(s == "locked" for s in states["medium"])
            assert all(s == "locked" for s in states["hard"])

    def test_pandas_easy_unlocked_medium_hard_locked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            states = _catalog_states(client, "/api/python-data/catalog")
            assert all(s == "unlocked" for s in states["easy"])
            assert all(s == "locked" for s in states["medium"])
            assert all(s == "locked" for s in states["hard"])


# ---------------------------------------------------------------------------
# Catalog: pro tier
# ---------------------------------------------------------------------------

class TestProCatalog:
    def test_sql_all_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            states = _catalog_states(client, "/api/catalog")
            for diff, qs in states.items():
                assert all(s == "unlocked" for s in qs), f"pro: SQL {diff} should all be unlocked"

    def test_python_all_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            states = _catalog_states(client, "/api/python/catalog")
            for diff, qs in states.items():
                assert all(s == "unlocked" for s in qs), f"pro: Python {diff} should all be unlocked"

    def test_pyspark_all_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            states = _catalog_states(client, "/api/pyspark/catalog")
            for diff, qs in states.items():
                assert all(s == "unlocked" for s in qs), f"pro: PySpark {diff} should all be unlocked"

    def test_pandas_all_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            states = _catalog_states(client, "/api/python-data/catalog")
            for diff, qs in states.items():
                assert all(s == "unlocked" for s in qs), f"pro: Pandas {diff} should all be unlocked"


# ---------------------------------------------------------------------------
# Catalog: elite tier
# ---------------------------------------------------------------------------

class TestEliteCatalog:
    def test_all_tracks_fully_unlocked(self) -> None:
        endpoints = [
            "/api/catalog",
            "/api/python/catalog",
            "/api/python-data/catalog",
            "/api/pyspark/catalog",
        ]
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            for endpoint in endpoints:
                states = _catalog_states(client, endpoint)
                for diff, qs in states.items():
                    locked = [s for s in qs if s == "locked"]
                    assert locked == [], f"elite: {endpoint} {diff} has {len(locked)} locked questions"

    def test_total_question_counts(self) -> None:
        """Sanity-check total question counts match CLAUDE.md spec."""
        expected = {
            "/api/catalog": {"easy": 32, "medium": 34, "hard": 29},
            "/api/python/catalog": {"easy": 30, "medium": 29, "hard": 24},
            "/api/python-data/catalog": {"easy": 22, "medium": 31, "hard": 23},
            "/api/pyspark/catalog": {"easy": 38, "medium": 30, "hard": 22},
        }
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            for endpoint, counts in expected.items():
                resp = client.get(endpoint)
                assert resp.status_code == 200
                for group in resp.json()["groups"]:
                    diff = group["difficulty"]
                    got = len(group["questions"])
                    assert got == counts[diff], (
                        f"{endpoint} {diff}: expected {counts[diff]} questions, got {got}"
                    )


# ---------------------------------------------------------------------------
# Mock access: plan gates
# ---------------------------------------------------------------------------

class TestMockPlanGates:
    def test_free_user_blocked_from_hard_mock(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            status, body = _start_mock(client, difficulty="hard")
            assert status == 403, f"expected 403, got {status}: {body}"
            assert "Pro" in body["error"], f"expected upgrade message, got: {body}"

    def test_free_user_can_start_easy_mock(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            status, body = _start_mock(client, difficulty="easy")
            assert status == 200, f"expected 200, got {status}: {body}"
            assert "session_id" in body

    def test_pro_user_can_start_hard_mock(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            status, body = _start_mock(client, difficulty="hard")
            assert status == 200, f"expected 200, got {status}: {body}"
            assert "session_id" in body

    def test_elite_user_can_start_hard_mock(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, difficulty="hard")
            assert status == 200, f"expected 200, got {status}: {body}"
            assert "session_id" in body


# ---------------------------------------------------------------------------
# Mock access: daily limits enforced at the API level
# ---------------------------------------------------------------------------

class TestMockDailyLimits:
    def test_pro_hard_limit_is_3_per_day(self) -> None:
        """Pro users get exactly 3 hard mocks per day; the 4th must be rejected."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")

            for i in range(1, 4):
                status, body = _start_mock(client, difficulty="hard")
                assert status == 200, f"hard mock #{i} should succeed for pro, got {status}: {body}"

            status, body = _start_mock(client, difficulty="hard")
            assert status == 403, f"4th hard mock should be blocked for pro, got {status}: {body}"
            assert "daily" in body["error"].lower() or "limit" in body["error"].lower(), (
                f"unexpected error message: {body['error']}"
            )

    def test_pro_hard_limit_does_not_affect_easy_or_medium(self) -> None:
        """Exhausting the hard quota must not block easy or medium mocks."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")

            # Exhaust hard daily limit
            for _ in range(3):
                status, _ = _start_mock(client, difficulty="hard")
                assert status == 200

            # Easy and medium should still work
            status, body = _start_mock(client, difficulty="easy")
            assert status == 200, f"easy mock should still work after hard limit: {body}"

            status, body = _start_mock(client, difficulty="medium")
            assert status == 200, f"medium mock should still work after hard limit: {body}"

    def test_elite_hard_mock_is_unlimited(self) -> None:
        """Elite users must not be blocked regardless of how many hard sessions they start."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")

            # Start more than the pro daily limit — should all succeed
            for i in range(1, 6):
                status, body = _start_mock(client, difficulty="hard")
                assert status == 200, f"elite hard mock #{i} was blocked unexpectedly: {body}"

    def test_free_user_medium_mock_requires_medium_unlocked(self) -> None:
        """Free users need medium questions unlocked in practice before they can start a medium mock."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            # No questions solved → medium mock should be blocked
            status, body = _start_mock(client, difficulty="medium")
            assert status == 403, f"expected 403 for free user with no medium unlocked, got {status}: {body}"


# ---------------------------------------------------------------------------
# Dashboard: response shape
# ---------------------------------------------------------------------------

class TestDashboardShape:
    def test_by_difficulty_returns_solved_and_total(self) -> None:
        """Each entry in by_difficulty must be {solved: int, total: int}, not a plain int."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            resp = client.get("/api/dashboard")
            assert resp.status_code == 200, resp.text
            data = resp.json()

            for track, track_data in data["tracks"].items():
                by_diff = track_data["by_difficulty"]
                for diff, val in by_diff.items():
                    assert isinstance(val, dict), (
                        f"dashboard tracks.{track}.by_difficulty.{diff} should be a dict, got {type(val).__name__}"
                    )
                    assert "solved" in val, f"missing 'solved' key in {track}.{diff}"
                    assert "total" in val, f"missing 'total' key in {track}.{diff}"
                    assert isinstance(val["solved"], int)
                    assert isinstance(val["total"], int)
                    assert val["total"] > 0, f"{track}.{diff}.total should be > 0"
                    assert val["solved"] <= val["total"]

    def test_dashboard_totals_match_catalog_counts(self) -> None:
        """Dashboard totals should match the number of questions in each catalog."""
        expected_totals = {
            "sql": 95,
            "python": 83,
            "python-data": 76,
            "pyspark": 90,
        }
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            resp = client.get("/api/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            for track, expected_total in expected_totals.items():
                got = data["tracks"][track]["total"]
                assert got == expected_total, (
                    f"dashboard {track}.total: expected {expected_total}, got {got}"
                )


# ---------------------------------------------------------------------------
# Lifetime Pro — catalog and mock access (must mirror base Pro)
# ---------------------------------------------------------------------------

class TestLifetimeProCatalog:
    """lifetime_pro users must have identical catalog access to pro users.

    The plan value stored in the DB is 'lifetime_pro' verbatim; normalize_plan()
    maps it to 'pro' for all access-control decisions.
    """

    def test_sql_catalog_fully_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            states = _catalog_states(client, "/api/catalog")
            assert all(s in ("unlocked", "solved") for s in states["easy"])
            assert all(s in ("unlocked", "solved") for s in states["medium"])
            # Pro caps hard — all should be unlocked (not locked)
            assert all(s in ("unlocked", "solved") for s in states["hard"]), (
                "lifetime_pro must unlock all hard SQL questions, same as pro"
            )

    def test_python_catalog_fully_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            states = _catalog_states(client, "/api/python/catalog")
            assert all(s in ("unlocked", "solved") for s in states["hard"]), (
                "lifetime_pro must unlock all hard Python questions"
            )

    def test_profile_stores_lifetime_pro_verbatim(self) -> None:
        """The profile endpoint must return 'lifetime_pro', not 'pro'.

        Verbatim storage is what prevents subscription.deleted from downgrading
        the user — do not normalise this value in the DB or API layer.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="lifetime_pro")
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.status_code == 200
            assert profile.json()["plan"] == "lifetime_pro", (
                "plan must be stored and returned as 'lifetime_pro', not collapsed to 'pro'"
            )

    def test_mock_hard_allowed_within_daily_limit(self) -> None:
        """lifetime_pro users may start hard mocks (same 3/day budget as pro)."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            r = client.post(
                "/api/mock/start",
                json={"mode": "30min", "track": "sql", "difficulty": "hard"},
            )
            assert r.status_code == 200, (
                f"lifetime_pro must be allowed to start hard mocks, got {r.status_code}: {r.json()}"
            )

    def test_company_filter_mock_blocked(self) -> None:
        """Company-filtered mocks require elite tier — lifetime_pro must be blocked."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            r = client.post(
                "/api/mock/start",
                json={"mode": "30min", "track": "sql", "difficulty": "hard",
                      "company_filter": "Meta"},
            )
            assert r.status_code in (400, 403), (
                f"lifetime_pro must not access company-filtered mocks, got {r.status_code}"
            )


# ---------------------------------------------------------------------------
# Lifetime Elite — catalog and mock access (must mirror base Elite)
# ---------------------------------------------------------------------------

class TestLifetimeEliteCatalog:
    """lifetime_elite users must have full catalog access identical to elite users."""

    def test_sql_catalog_fully_unlocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            states = _catalog_states(client, "/api/catalog")
            assert all(s in ("unlocked", "solved") for s in states["hard"]), (
                "lifetime_elite must unlock all hard SQL questions"
            )

    def test_profile_stores_lifetime_elite_verbatim(self) -> None:
        """The profile endpoint must return 'lifetime_elite', not 'elite'."""
        with TestClient(app) as client:
            user = _make_user(client, plan="lifetime_elite")
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.status_code == 200
            assert profile.json()["plan"] == "lifetime_elite", (
                "plan must be stored and returned as 'lifetime_elite', not collapsed to 'elite'"
            )

    def test_mock_hard_unlimited(self) -> None:
        """lifetime_elite users have no daily cap on hard mocks."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            # Start 4 hard mocks — beyond the pro daily cap of 3
            for i in range(4):
                r = client.post(
                    "/api/mock/start",
                    json={"mode": "30min", "track": "sql", "difficulty": "hard"},
                )
                assert r.status_code == 200, (
                    f"lifetime_elite mock #{i + 1} must be allowed (no daily cap), "
                    f"got {r.status_code}: {r.json()}"
                )

    def test_company_filter_mock_allowed(self) -> None:
        """Company-filtered mocks must be accessible to lifetime_elite users."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            r = client.post(
                "/api/mock/start",
                json={"mode": "30min", "track": "sql", "difficulty": "hard",
                      "company_filter": "Meta"},
            )
            assert r.status_code == 200, (
                f"lifetime_elite must access company-filtered mocks, got {r.status_code}: {r.json()}"
            )
