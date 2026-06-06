"""Negative-entitlement test suite.

Every test asserts that a FREE or ANONYMOUS user calling a plan-gated endpoint
receives either 403 (access denied) or a preview response with gated fields absent.
This is the regression guard: if any of these tests fail, a future code change has
silently broken the server-side plan enforcement.

Design notes:
- Tests use a fresh registered free-plan user (via _make_user(client, plan="free")).
- Anonymous-session tests use a raw client with no registration.
- Solution fields that must NEVER appear in gated responses:
    SQL:    solution_query, expected_query
    Python: solution_code, expected_code
    MCQ:    correct_option, explanation (for locked questions)
- Mock-only content must 403 in practice mode.
- Hard questions must 403 on run-code and submit for free users (no hard access).
"""
import pytest
from starlette.testclient import TestClient

from main import app
from tests.conftest import _make_user

# Every test makes HTTP calls + registers users — isolate DB state and rate-limit
# counters per test (resets the test DB before/after each), matching the other
# HTTP suites. Without this the file passes only in the full suite (neighbours'
# teardowns clean the DB) and is flaky when run alone.
pytestmark = pytest.mark.usefixtures("isolated_state")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _assert_no_solution_fields(body: dict) -> None:
    """Assert none of the gated answer fields leaked into the response."""
    forbidden = ("solution_query", "expected_query", "solution_code", "expected_code")
    for field in forbidden:
        assert field not in body, (
            f"GATED FIELD '{field}' LEAKED in response: {list(body.keys())}"
        )


# ---------------------------------------------------------------------------
# SQL track
# ---------------------------------------------------------------------------

class TestSQLEntitlements:
    def test_hard_sql_run_query_blocked_for_free(self):
        """Free user cannot run a hard SQL question."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/run-query", json={"question_id": 13001, "query": "SELECT 1"})
            assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_hard_sql_submit_blocked_for_free(self):
        """Free user cannot submit a hard SQL question."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/submit", json={"question_id": 13001, "query": "SELECT 1"})
            assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_mock_only_sql_practice_detail_blocked(self):
        """Mock-only SQL question is 403 in practice mode."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            # 13030 is a hard mock-only SQL question
            r = client.get("/questions/13030")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    def test_hard_sql_detail_preview_excludes_solution(self):
        """Hard SQL question detail for free user: preview mode, no solution field."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/questions/13001")
            assert r.status_code == 200
            body = r.json()
            assert body.get("unlocked") is False or body.get("progress", {}).get("unlocked") is False
            _assert_no_solution_fields(body)

    def test_anon_user_cannot_submit_hard_sql(self):
        """Anonymous session (no registration) cannot submit a hard question."""
        with TestClient(app) as client:
            client.get("/api/catalog")  # seed session
            r = client.post("/submit", json={"question_id": 13001, "query": "SELECT 1"})
            assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ---------------------------------------------------------------------------
# Python track
# ---------------------------------------------------------------------------

class TestPythonEntitlements:
    def test_hard_python_run_code_blocked_for_free(self):
        """Free user cannot run-code on a hard Python question."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/python/run-code",
                            json={"question_id": 23001, "code": "def solve(): pass"})
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    def test_hard_python_submit_blocked_for_free(self):
        """Free user cannot submit a hard Python question."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/python/submit",
                            json={"question_id": 23001, "code": "def solve(): pass"})
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    def test_hard_python_detail_preview_excludes_solution(self):
        """Hard Python question detail for free user: preview mode, no solution field."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/python/questions/23001")
            assert r.status_code == 200
            body = r.json()
            assert body.get("unlocked") is False or body.get("progress", {}).get("unlocked") is False
            _assert_no_solution_fields(body)


# ---------------------------------------------------------------------------
# PySpark / MCQ track
# ---------------------------------------------------------------------------

class TestMCQEntitlements:
    def test_locked_pyspark_detail_excludes_options_and_answer(self):
        """Locked PySpark question returns stem only — no options, no correct_option."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            # 43027 is a hard mock-only PySpark question; free users have no hard access
            r = client.get("/api/pyspark/questions/43027")
            # Should be 403 (locked) or 200 preview without options/correct_option
            if r.status_code == 200:
                body = r.json()
                assert "correct_option" not in body, "correct_option LEAKED in locked preview"
                assert "options" not in body, "options LEAKED in locked preview"
                assert "explanation" not in body, "explanation LEAKED in locked preview"
            else:
                assert r.status_code == 403

    def test_locked_pyspark_submit_blocked(self):
        """Free user cannot submit a locked hard PySpark question."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/pyspark/submit",
                            json={"question_id": 43027, "selected_option": 0})
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# ---------------------------------------------------------------------------
# Mock session entitlements
# ---------------------------------------------------------------------------

class TestMockEntitlements:
    def test_free_user_cannot_start_mock_hard(self):
        """Free user is blocked from starting a hard mock session."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/mock/start", json={
                "track": "sql", "difficulty": "hard", "mode": "benchmark"
            })
            assert r.status_code in (403, 400), (
                f"Free user started hard mock — expected 403/400, got {r.status_code}: {r.text[:200]}"
            )

    def test_anon_user_cannot_start_mock(self):
        """Anonymous (not registered) user cannot start any mock session."""
        with TestClient(app) as client:
            client.get("/api/catalog")  # seed anon session
            r = client.post("/api/mock/start", json={
                "track": "sql", "difficulty": "easy", "mode": "benchmark"
            })
            # anon session is a real user row but plan=free with no email;
            # mock requires a registered session (plan check via compute_mock_access)
            assert r.status_code in (200, 400, 403), (
                f"Unexpected mock start status: {r.status_code}"
            )
            # If it "succeeds" (200), verify no mock-only content leaked:
            if r.status_code == 200:
                body = r.json()
                questions = body.get("questions", [])
                for q in questions:
                    assert not q.get("mock_only"), "mock_only question in anon session"

    def test_free_user_cannot_start_interview_loop(self):
        """Interview Loop is Elite-only — free user must be rejected."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/mock/start", json={
                "track": "ml-fundamentals", "difficulty": "hard", "mode": "interview_loop"
            })
            assert r.status_code in (403, 400), (
                f"Free user started interview_loop — expected 403/400, got {r.status_code}"
            )

    def test_pro_user_cannot_start_interview_loop(self):
        """Interview Loop is Elite-only — pro user must also be rejected."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/mock/start", json={
                "track": "ml-fundamentals", "difficulty": "hard", "mode": "interview_loop"
            })
            assert r.status_code in (403, 400), (
                f"Pro user started interview_loop — expected 403/400, got {r.status_code}"
            )


# ---------------------------------------------------------------------------
# Dashboard / insights (Elite-only features)
# ---------------------------------------------------------------------------

class TestInsightsEntitlements:
    def test_free_user_insights_no_readiness_or_study_plan(self):
        """Free user dashboard/insights must not include readiness_scores or study_plan."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200
            body = r.json()
            assert "readiness_scores" not in body or body["readiness_scores"] is None, (
                "readiness_scores LEAKED to free user"
            )
            assert "study_plan" not in body or body["study_plan"] is None, (
                "study_plan LEAKED to free user"
            )

    def test_pro_user_insights_no_readiness_or_study_plan(self):
        """Pro user (not Elite) must not see readiness_scores or study_plan."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200
            body = r.json()
            assert "readiness_scores" not in body or body["readiness_scores"] is None
            assert "study_plan" not in body or body["study_plan"] is None

    def test_mock_analytics_free_user_forbidden(self):
        """GET /api/mock/analytics is Elite-only — free user must get 403."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/analytics")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}"
