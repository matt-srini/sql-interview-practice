import pytest
from fastapi.testclient import TestClient

import backend.main as main
from questions import get_all_questions, get_question, get_questions_by_difficulty


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _first_two_easy_ids(client: TestClient) -> tuple[int, int]:
    catalog = client.get("/catalog").json()
    easy = next(group for group in catalog["groups"] if group["difficulty"] == "easy")
    easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
    return int(easy_questions[0]["id"]), int(easy_questions[1]["id"])


def _first_medium_id() -> int:
    return int(get_questions_by_difficulty()["medium"][0]["id"])


def test_health() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] in {"ok", "healthy"}
        assert "users" in payload["tables_loaded"]
        assert "orders" in payload["tables_loaded"]


def test_get_questions() -> None:
    with TestClient(app) as client:
        resp = client.get("/questions")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) == len(get_all_questions())
        assert {"id", "title", "difficulty"}.issubset(payload[0].keys())


def test_get_api_questions() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/questions")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload) == len(get_all_questions())


def test_catalog_creates_anonymous_session_and_initial_unlocks() -> None:
    with TestClient(app) as client:
        resp = client.get("/catalog")
        assert resp.status_code == 200
        assert "session_token" in client.cookies

        payload = resp.json()
        assert payload["user_id"]
        groups = {g["difficulty"]: g for g in payload["groups"]}
        assert set(groups.keys()) == {"easy", "medium", "hard"}
        grouped = get_questions_by_difficulty()

        assert groups["easy"]["counts"]["total"] == len(grouped["easy"])
        assert groups["medium"]["counts"]["total"] == len(grouped["medium"])
        assert groups["hard"]["counts"]["total"] == len(grouped["hard"])

        easy_questions = sorted(groups["easy"]["questions"], key=lambda q: q["order"])
        assert all(question["state"] == "unlocked" for question in easy_questions)
        assert easy_questions[0]["is_next"] is True
        assert all(question["is_next"] is False for question in easy_questions[1:])

        medium_questions = sorted(groups["medium"]["questions"], key=lambda q: q["order"])
        hard_questions = sorted(groups["hard"]["questions"], key=lambda q: q["order"])
        assert all(question["state"] == "locked" for question in medium_questions)
        assert all(question["state"] == "locked" for question in hard_questions)
        assert all(question["is_next"] is False for question in medium_questions)
        assert all(question["is_next"] is False for question in hard_questions)


def test_get_question_detail() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client)
        resp = client.get(f"/api/questions/{first_easy_id}")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["id"] == first_easy_id
        assert "schema" in payload
        assert "progress" in payload
        assert {"state", "is_next", "unlocked"}.issubset(payload["progress"].keys())
        assert "solution_query" not in payload
        assert "expected_query" not in payload
        assert "explanation" not in payload


def test_get_question_detail_preview_mode_for_locked_question() -> None:
    """Locked questions now return 200 with content but progress.unlocked=False (preview mode)."""
    with TestClient(app) as client:
        medium_id = _first_medium_id()
        resp = client.get(f"/api/questions/{medium_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["progress"]["unlocked"] is False
        assert "title" in data
        assert "description" in data  # question text is visible in preview


def test_run_query_success() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client)
        resp = client.post(
            "/run-query",
            json={"query": "SELECT user_id, name FROM users ORDER BY user_id LIMIT 3", "question_id": first_easy_id},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["columns"] == ["user_id", "name"]
        assert len(payload["rows"]) == 3


def test_run_query_locked_question_blocked() -> None:
    with TestClient(app) as client:
        medium_id = _first_medium_id()
        resp = client.post(
            "/run-query",
            json={"query": "SELECT country FROM users LIMIT 1", "question_id": medium_id},
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
        first_easy_id, _ = _first_two_easy_ids(client)
        first_easy = get_question(first_easy_id)
        assert first_easy is not None

        resp = client.post(
            "/submit",
            json={"query": first_easy["solution_query"], "question_id": first_easy_id},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["correct"] is True
        assert payload["is_result_correct"] is True
        assert "solution_query" in payload
        assert "explanation" in payload

        catalog = client.get("/catalog").json()
        easy = next(g for g in catalog["groups"] if g["difficulty"] == "easy")
        easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
        assert easy_questions[0]["id"] == first_easy_id
        assert easy_questions[0]["state"] == "solved"
        assert easy_questions[1]["state"] == "unlocked"


def test_submit_requires_enforced_order_by_for_acceptance() -> None:
    with TestClient(app) as client:
        first_easy_id, second_easy_id = _first_two_easy_ids(client)
        first_easy = get_question(first_easy_id)
        assert first_easy is not None

        resp = client.post(
            "/submit",
            json={
                "query": "SELECT user_id, name, email, country FROM users",
                "question_id": first_easy_id,
            },
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["correct"] is False
        assert payload["is_result_correct"] is True
        assert payload["structure_correct"] is False
        assert len(payload["feedback"]) > 0
        assert any("ORDER BY" in message for message in payload["feedback"])

        catalog = client.get("/catalog").json()
        easy = next(g for g in catalog["groups"] if g["difficulty"] == "easy")
        easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
        assert easy_questions[0]["id"] == first_easy_id
        assert easy_questions[0]["state"] == "unlocked"
        assert easy_questions[1]["id"] == second_easy_id
        assert easy_questions[1]["state"] == "unlocked"


def test_easy_questions_with_required_concepts_have_covering_hints() -> None:
    grouped = get_questions_by_difficulty()
    concept_keywords = {
        "order_by": ["order by", "order"],
        "distinct": ["distinct"],
        "where": ["where", "filter"],
        "group_by": ["group by", "group"],
        "having": ["having"],
        "join": ["join"],
        "left_join": ["left join"],
        "aggregation": ["count", "sum", "avg", "min", "max", "aggregate"],
        "subquery": ["subquery"],
        "window_function": ["window", "over"],
    }

    for question in grouped["easy"]:
        required_concepts = question.get("required_concepts") or []
        hints = question.get("hints") or []

        if not required_concepts:
            continue

        normalized_hints = [str(hint).strip().lower() for hint in hints]
        assert len(normalized_hints) == len(set(normalized_hints)), (
            f"Question {question['id']} has duplicate hints"
        )

        combined_hints = " ".join(normalized_hints)
        for concept in required_concepts:
            keywords = concept_keywords.get(concept, [concept.replace("_", " ")])
            assert any(keyword in combined_hints for keyword in keywords), (
                f"Question {question['id']} is missing a hint for required concept '{concept}'"
            )


def test_submit_blocks_disallowed_query() -> None:
    with TestClient(app) as client:
        first_easy_id, _ = _first_two_easy_ids(client)
        resp = client.post(
            "/submit",
            json={"query": "DELETE FROM users", "question_id": first_easy_id},
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
            reset = client.post(f"/api/sample/{difficulty}/reset")
            assert reset.status_code == 200

            resp = client.get(f"/api/sample/{difficulty}")
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["difficulty"] == difficulty
            assert payload["progress"]["mode"] == "sample"
            assert payload["progress"]["unlocked"] is True
            assert "solution_query" not in payload
            assert payload["sample"]["topic"] == "sql"
            if difficulty == "easy":
                assert 101 <= payload["id"] <= 103
            elif difficulty == "medium":
                assert 201 <= payload["id"] <= 203
            elif difficulty == "hard":
                assert 301 <= payload["id"] <= 303
            assert payload["sample"]["total"] == 3


def test_get_topic_sample_question_by_difficulty() -> None:
    with TestClient(app) as client:
        for topic in ["python", "python-data", "pyspark"]:
            reset = client.post(f"/api/sample/{topic}/easy/reset")
            assert reset.status_code == 200

            resp = client.get(f"/api/sample/{topic}/easy")
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["difficulty"] == "easy"
            assert payload["progress"]["mode"] == "sample"
            assert payload["sample"]["topic"] == topic
            assert payload["sample"]["total"] == 3


def test_sample_questions_exhaust_after_three_shown() -> None:
    seen_ids: set[int] = set()

    with TestClient(app) as client:
        reset = client.post("/api/sample/sql/easy/reset")
        assert reset.status_code == 200

        for _ in range(3):
            resp = client.get("/api/sample/sql/easy")
            assert resp.status_code == 200
            payload = resp.json()
            seen_ids.add(int(payload["id"]))

        assert len(seen_ids) == 3

        exhausted = client.get("/api/sample/sql/easy")
        assert exhausted.status_code == 409


def test_reset_sample_progress_restarts_difficulty_sequence() -> None:
    with TestClient(app) as client:
        reset_initial = client.post("/api/sample/sql/easy/reset")
        assert reset_initial.status_code == 200

        first = client.get("/api/sample/sql/easy")
        assert first.status_code == 200
        first_id = int(first.json()["id"])

        second = client.get("/api/sample/sql/easy")
        assert second.status_code == 200
        assert int(second.json()["id"]) != first_id

        reset = client.post("/api/sample/sql/easy/reset")
        assert reset.status_code == 200
        assert reset.json()["reset"] is True

        after_reset = client.get("/api/sample/sql/easy")
        assert after_reset.status_code == 200
        assert int(after_reset.json()["id"]) == first_id
        assert after_reset.json()["sample"]["shown_count"] == 1


def test_sample_submit_does_not_advance_catalog_progress() -> None:
    with TestClient(app) as client:
        reset = client.post("/api/sample/sql/easy/reset")
        assert reset.status_code == 200

        before = client.get("/api/catalog").json()
        before_easy = next(group for group in before["groups"] if group["difficulty"] == "easy")

        sample = client.get("/api/sample/sql/easy").json()
        assert sample["id"] == 101

        resp = client.post(
            "/api/sample/sql/submit",
            json={
                "query": "SELECT COUNT(*) AS user_count FROM users",
                "question_id": sample["id"],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["correct"] is True

        after = client.get("/api/catalog").json()
        after_easy = next(group for group in after["groups"] if group["difficulty"] == "easy")

        assert before_easy == after_easy


def test_topic_sample_question_by_difficulty_for_all_tracks() -> None:
    main._clear_rate_limit_state()
    with TestClient(app) as client:
        for topic in ["sql", "python", "python-data", "pyspark"]:
            for difficulty in ["easy", "medium", "hard"]:
                reset = client.post(f"/api/sample/{topic}/{difficulty}/reset")
                assert reset.status_code == 200
                payload = reset.json()
                assert payload["topic"] == topic
                assert payload["difficulty"] == difficulty
                assert payload["reset"] is True

                resp = client.get(f"/api/sample/{topic}/{difficulty}")
                assert resp.status_code == 200
                body = resp.json()
                assert body["progress"]["mode"] == "sample"
                assert body["sample"]["topic"] == topic
                assert body["sample"]["difficulty"] == difficulty
                assert body["sample"]["total"] == 3

                if topic == "sql":
                    assert body["sample"]["served_difficulty"] == difficulty
                    assert body["id"] in {101, 102, 103, 201, 202, 203, 301, 302, 303}
                else:
                    assert body["sample"]["served_difficulty"] == difficulty
                    if topic == "python":
                        if difficulty == "easy":
                            assert 4001 <= int(body["id"]) <= 4003
                        elif difficulty == "medium":
                            assert 4004 <= int(body["id"]) <= 4006
                        else:
                            assert 4007 <= int(body["id"]) <= 4009
                    elif topic == "python-data":
                        if difficulty == "easy":
                            assert 5001 <= int(body["id"]) <= 5003
                        elif difficulty == "medium":
                            assert 5004 <= int(body["id"]) <= 5006
                        else:
                            assert 5007 <= int(body["id"]) <= 5009
                    else:
                        if difficulty == "easy":
                            assert 11001 <= int(body["id"]) <= 11003
                        elif difficulty == "medium":
                            assert 11004 <= int(body["id"]) <= 11006
                        else:
                            assert 11007 <= int(body["id"]) <= 11009


def test_topic_sample_submit_and_run_preserve_challenge_progress() -> None:
    main._clear_rate_limit_state()
    with TestClient(app) as client:
        before_python = client.get("/api/python/catalog").json()
        before_python_easy = next(group for group in before_python["groups"] if group["difficulty"] == "easy")

        sample_python = client.get("/api/sample/python/easy").json()
        run_python = client.post(
            "/api/sample/python/run-code",
            json={
                "code": sample_python["starter_code"],
                "question_id": sample_python["id"],
            },
        )
        assert run_python.status_code == 200
        assert "results" in run_python.json()

        submit_python = client.post(
            "/api/sample/python/submit",
            json={
                "code": sample_python["starter_code"],
                "question_id": sample_python["id"],
            },
        )
        assert submit_python.status_code == 200
        assert "correct" in submit_python.json()

        sample_python_data = client.get("/api/sample/python-data/easy").json()
        run_python_data = client.post(
            "/api/sample/python-data/run-code",
            json={
                "code": sample_python_data["starter_code"],
                "question_id": sample_python_data["id"],
            },
        )
        assert run_python_data.status_code == 200
        assert "error" in run_python_data.json()

        submit_python_data = client.post(
            "/api/sample/python-data/submit",
            json={
                "code": sample_python_data["starter_code"],
                "question_id": sample_python_data["id"],
            },
        )
        assert submit_python_data.status_code == 200
        assert "correct" in submit_python_data.json()

        after_python = client.get("/api/python/catalog").json()
        after_python_easy = next(group for group in after_python["groups"] if group["difficulty"] == "easy")
        assert before_python_easy == after_python_easy


def test_topic_sample_pyspark_submit_flow() -> None:
    main._clear_rate_limit_state()
    with TestClient(app) as client:
        sample = client.get("/api/sample/pyspark/easy")
        assert sample.status_code == 200
        payload = sample.json()
        assert "options" in payload
        assert len(payload["options"]) >= 2

        submit = client.post(
            "/api/sample/pyspark/submit",
            json={
                "question_id": payload["id"],
                "selected_option": 0,
            },
        )
        assert submit.status_code == 200
        assert "correct" in submit.json()
        assert "explanation" in submit.json()


def test_register_preserves_anonymous_progress_and_user_id() -> None:
    with TestClient(app) as client:
        catalog_before = client.get("/api/catalog").json()
        first_easy_id, _ = _first_two_easy_ids(client)
        first_easy = get_question(first_easy_id)
        assert first_easy is not None

        submit = client.post(
            "/api/submit",
            json={"query": first_easy["solution_query"], "question_id": first_easy_id},
        )
        assert submit.status_code == 200
        anon_user_id = catalog_before["user_id"]

        register = client.post(
            "/api/auth/register",
            json={"email": "anon@example.com", "name": "Anon User", "password": "password123"},
        )
        assert register.status_code == 201
        payload = register.json()["user"]
        assert payload["id"] == anon_user_id
        assert payload["email"] == "anon@example.com"

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["id"] == anon_user_id

        catalog_after = client.get("/api/catalog").json()
        easy = next(group for group in catalog_after["groups"] if group["difficulty"] == "easy")
        easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
        assert easy_questions[0]["state"] == "solved"
        assert easy_questions[1]["state"] == "unlocked"


def test_login_merges_existing_anonymous_progress() -> None:
    first_easy_id = int(get_questions_by_difficulty()["easy"][0]["id"])
    first_easy = get_question(first_easy_id)
    assert first_easy is not None

    with TestClient(app) as registered_client:
        registered_client.get("/api/catalog")
        register = registered_client.post(
            "/api/auth/register",
            json={"email": "merge@example.com", "name": "Merge User", "password": "password123"},
        )
        assert register.status_code == 201
        registered_user_id = register.json()["user"]["id"]

    with TestClient(app) as anonymous_client:
        anonymous_catalog = anonymous_client.get("/api/catalog").json()
        anonymous_user_id = anonymous_catalog["user_id"]
        assert anonymous_user_id != registered_user_id

        submit = anonymous_client.post(
            "/api/submit",
            json={"query": first_easy["solution_query"], "question_id": first_easy_id},
        )
        assert submit.status_code == 200

        login = anonymous_client.post(
            "/api/auth/login",
            json={"email": "merge@example.com", "password": "password123"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["id"] == registered_user_id

        catalog_after = anonymous_client.get("/api/catalog").json()
        assert catalog_after["user_id"] == registered_user_id
        easy = next(group for group in catalog_after["groups"] if group["difficulty"] == "easy")
        easy_questions = sorted(easy["questions"], key=lambda q: q["order"])
        assert easy_questions[0]["state"] == "solved"
        assert easy_questions[1]["state"] == "unlocked"
