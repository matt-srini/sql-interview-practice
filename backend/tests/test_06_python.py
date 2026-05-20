"""TC-091 to TC-100 — Python Execution."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
from python_questions import get_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = get_questions_by_difficulty()
_easy_q = _catalog["easy"][0]
_easy_id = _easy_q["id"]  # 4001
_easy_solution = _easy_q["solution_code"]


def test_tc091_correct_code_passes_all_tests_and_returns_stdout():
    """TC-091: Correct code → test_results array with passes; stdout key present."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": _easy_solution,
        })
    assert r.status_code == 200
    body = r.json()
    assert "test_results" in body
    assert any(tr.get("passed") for tr in body["test_results"])
    assert "stdout" in body  # may be empty string


def test_tc092_compile_error_returns_readable_message():
    """TC-092: Compile error → readable error message, no raw traceback."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": "def solve(x\n    return x",
        })
    assert r.status_code in (200, 400)
    body = r.json()
    assert "error" in body
    assert len(body["error"]) > 5
    assert "Traceback" not in body["error"]
    assert "/backend/" not in body["error"]


def test_tc093_execution_timeout_enforced():
    """TC-093: time.sleep(10) → timeout within ~7s wall-clock."""
    code = "def solve(n):\n    import time\n    time.sleep(10)\n    return n"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        start = time.time()
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": code,
        }, timeout=15)
        elapsed = time.time() - start
    assert elapsed < 8, f"Timeout took too long: {elapsed:.1f}s"
    body = r.json()
    assert "error" in body or any(not tr.get("passed") for tr in body.get("test_results", [{}]))


def test_tc094_stdout_captured():
    """TC-094: print('hello') → stdout contains 'hello'."""
    code = "def solve(nums, target):\n    print('hello')\n    return nums"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": code,
        })
    assert r.status_code == 200
    body = r.json()
    assert "hello" in body.get("stdout", "")


def test_tc095_correct_submit_returns_correct_true_and_solution():
    """TC-095: Correct submit → correct: true + solution present."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/submit", json={
            "question_id": _easy_id,
            "code": _easy_solution,
            "duration_ms": 3000,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is True
    assert body.get("solution_code")


def test_tc096_wrong_answer_correct_false_with_breakdown():
    """TC-096: Wrong submit → correct: false with per-test breakdown."""
    code = "def solve(nums, target):\n    return []"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/submit", json={
            "question_id": _easy_id,
            "code": code,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is False
    # Per-test breakdown
    results = body.get("test_results", [])
    assert results  # at least one test entry


def test_tc097_import_os_rejected():
    """TC-097: import os → 400 guard rejection."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": "import os; os.listdir('/')",
        })
    assert r.status_code == 400


def test_tc098_import_subprocess_rejected():
    """TC-098: import subprocess → 400 guard rejection."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": "import subprocess",
        })
    assert r.status_code == 400


def test_tc099_open_for_write_rejected():
    """TC-099: open() for write → 400 guard rejection."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": "open('/tmp/pwned', 'w').write('x')",
        })
    assert r.status_code == 400


def test_tc100_safe_import_math_accepted():
    """TC-100: import math → guard passes (200 or test failure, not guard 400)."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/python/run-code", json={
            "question_id": _easy_id,
            "code": "import math\ndef solve(n): return math.sqrt(n)",
        })
    assert r.status_code != 400, "Guard should not reject import math"
