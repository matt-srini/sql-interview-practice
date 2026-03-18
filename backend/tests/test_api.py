from fastapi.testclient import TestClient

import main
from main import app
from questions import get_question


def _first_two_easy_ids(client: TestClient, user_id: str) -> tuple[int, int]:
    catalog = client.get("/catalog", headers={"X-User-Id": user_id}).json()
    easy = next(group for group in catalog["groups"] if group["difficulty"] == "easy")
    easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
    return int(easy_questions[0]["id"]), int(easy_questions[1]["id"])


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert "employees" in payload["tables_loaded"]


def test_get_questions() -> None:
    with TestClient(app) as client:
        resp = client.get("/questions")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) >= 75
        assert {"id", "title", "difficulty"}.issubset(payload[0].keys())


def test_get_api_questions() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/questions")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) >= 75


def test_get_catalog_groups_and_initial_unlocks() -> None:
    with TestClient(app) as client:
        resp = client.get("/catalog", headers={"X-User-Id": "u_catalog"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["user_id"] == "u_catalog"
        groups = {g["difficulty"]: g for g in payload["groups"]}
        assert set(groups.keys()) == {"easy", "medium", "hard"}

        for diff in ["easy", "medium", "hard"]:
            assert groups[diff]["counts"]["total"] >= 25
            first = sorted(groups[diff]["questions"], key=lambda q: q["order"])[0]
            assert first["state"] == "unlocked"
            assert first["is_next"] is True

        # Easy question #2 should be locked until #1 is solved.
        easy_questions = sorted(groups["easy"]["questions"], key=lambda q: q["order"])
        assert easy_questions[1]["state"] == "locked"


def test_get_question_detail() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client, "u_detail")
        resp = client.get(f"/api/questions/{first_easy_id}", headers={"X-User-Id": "u_detail"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["id"] == first_easy_id
        assert "schema" in payload
        assert "progress" in payload
        assert {"state", "is_next", "unlocked"}.issubset(payload["progress"].keys())
        assert "solution_query" not in payload
        assert "expected_query" not in payload
        assert "explanation" not in payload


def test_get_question_detail_blocks_locked_question() -> None:
    with TestClient(app) as client:
        _, second_easy_id = _first_two_easy_ids(client, "u_detail_locked")
        resp = client.get(f"/api/questions/{second_easy_id}", headers={"X-User-Id": "u_detail_locked"})
        assert resp.status_code == 403


def test_run_query_success() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client, "u_run_ok")
        resp = client.post(
            "/run-query",
            json={"query": "SELECT id, name FROM employees LIMIT 3", "question_id": first_easy_id},
            headers={"X-User-Id": "u_run_ok"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["columns"] == ["id", "name"]
        assert len(payload["rows"]) == 3


def test_run_query_locked_question_blocked() -> None:
    with TestClient(app) as client:
        _, second_easy_id = _first_two_easy_ids(client, "u_locked")
        resp = client.post(
            "/run-query",
            json={"query": "SELECT email FROM employees LIMIT 1", "question_id": second_easy_id},
            headers={"X-User-Id": "u_locked"},
        )
        assert resp.status_code == 403


def test_run_query_invalid_question() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/run-query",
            json={"query": "SELECT 1", "question_id": 999},
        )
        assert resp.status_code == 404

        payload = resp.json()
        assert "error" in payload
        assert "request_id" in payload


def test_submit_correct_answer() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client, "u_progress")
        first_easy = get_question(first_easy_id)
        assert first_easy is not None

        resp = client.post(
            "/submit",
            json={"query": first_easy["solution_query"], "question_id": first_easy_id},
            headers={"X-User-Id": "u_progress"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["correct"] is True
        assert "solution_query" in payload
        assert "explanation" in payload

        # After solving easy #1, easy #2 should unlock for this user.
        catalog = client.get("/catalog", headers={"X-User-Id": "u_progress"}).json()
        easy = next(g for g in catalog["groups"] if g["difficulty"] == "easy")
        easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
        assert easy_questions[0]["id"] == first_easy_id
        assert easy_questions[0]["state"] == "solved"
        assert easy_questions[1]["state"] == "unlocked"


def test_submit_blocks_disallowed_query() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client, "u_submit_block")
        resp = client.post(
            "/submit",
            json={"query": "DELETE FROM employees", "question_id": first_easy_id},
            headers={"X-User-Id": "u_submit_block"},
        )
        assert resp.status_code == 400

        payload = resp.json()
        assert "error" in payload
        assert "request_id" in payload


def test_rate_limit_headers_present() -> None:
    main._clear_rate_limit_state()
    with TestClient(app) as client:
        resp = client.get("/questions")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers


def test_rate_limit_enforced() -> None:
    main._clear_rate_limit_state()
    limiter = main.rate_limiter
    original_requests = limiter.max_requests
    original_window = limiter.window_seconds
    limiter.max_requests = 2
    limiter.window_seconds = 60

    try:
        with TestClient(app) as client:
            assert client.get("/questions").status_code == 200
            assert client.get("/questions").status_code == 200
            limited = client.get("/questions")
            assert limited.status_code == 429
            payload = limited.json()
            assert "error" in payload
            assert "request_id" in payload
            assert "X-Request-ID" in limited.headers
    finally:
        limiter.max_requests = original_requests
        limiter.window_seconds = original_window
        main._clear_rate_limit_state()


def test_get_sample_question_by_difficulty() -> None:
    with TestClient(app) as client:
        for difficulty in ["easy", "medium", "hard"]:
            user_id = f"u_sample_{difficulty}"
            reset = client.post(f"/api/sample/{difficulty}/reset", headers={"X-User-Id": user_id})
            assert reset.status_code == 200

            resp = client.get(f"/api/sample/{difficulty}", headers={"X-User-Id": user_id})
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["difficulty"] == difficulty
            assert payload["progress"]["mode"] == "sample"
            assert payload["progress"]["unlocked"] is True
            assert "solution_query" not in payload
            assert payload["id"] >= 1000
            assert payload["sample"]["total"] == 3


def test_sample_questions_exhaust_after_three_shown() -> None:
    user_id = "u_sample_exhaust"
    seen_ids: set[int] = set()

    with TestClient(app) as client:
        reset = client.post("/api/sample/easy/reset", headers={"X-User-Id": user_id})
        assert reset.status_code == 200

        for _ in range(3):
            resp = client.get("/api/sample/easy", headers={"X-User-Id": user_id})
            assert resp.status_code == 200
            payload = resp.json()
            seen_ids.add(int(payload["id"]))

        assert len(seen_ids) == 3

        exhausted = client.get("/api/sample/easy", headers={"X-User-Id": user_id})
        assert exhausted.status_code == 409


def test_reset_sample_progress_restarts_difficulty_sequence() -> None:
    user_id = "u_sample_reset"

    with TestClient(app) as client:
        reset_initial = client.post("/api/sample/easy/reset", headers={"X-User-Id": user_id})
        assert reset_initial.status_code == 200

        first = client.get("/api/sample/easy", headers={"X-User-Id": user_id})
        assert first.status_code == 200
        first_id = int(first.json()["id"])

        second = client.get("/api/sample/easy", headers={"X-User-Id": user_id})
        assert second.status_code == 200
        assert int(second.json()["id"]) != first_id

        reset = client.post("/api/sample/easy/reset", headers={"X-User-Id": user_id})
        assert reset.status_code == 200
        assert reset.json()["reset"] is True

        after_reset = client.get("/api/sample/easy", headers={"X-User-Id": user_id})
        assert after_reset.status_code == 200
        assert int(after_reset.json()["id"]) == first_id
        assert after_reset.json()["sample"]["shown_count"] == 1


def test_sample_submit_does_not_advance_catalog_progress() -> None:
    user_id = "u_sample_progress"

    with TestClient(app) as client:
        reset = client.post("/api/sample/easy/reset", headers={"X-User-Id": user_id})
        assert reset.status_code == 200

        before = client.get("/api/catalog", headers={"X-User-Id": user_id}).json()
        before_easy = next(group for group in before["groups"] if group["difficulty"] == "easy")

        sample = client.get("/api/sample/easy", headers={"X-User-Id": user_id}).json()
        assert sample["id"] == 1001

        resp = client.post(
            "/api/sample/submit",
            json={
                "query": "SELECT MAX(salary) AS max_salary FROM employees",
                "question_id": sample["id"],
            },
            headers={"X-User-Id": user_id},
        )
        assert resp.status_code == 200
        assert resp.json()["correct"] is True

        after = client.get("/api/catalog", headers={"X-User-Id": user_id}).json()
        after_easy = next(group for group in after["groups"] if group["difficulty"] == "easy")

        assert before_easy == after_easy
