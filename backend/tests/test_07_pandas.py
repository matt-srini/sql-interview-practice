"""TC-101 to TC-105 — Pandas Execution."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
from pandas_questions import get_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = get_questions_by_difficulty()
_easy_q = _catalog["easy"][0]
_easy_id = _easy_q["id"]  # 5002
_easy_solution = _easy_q["solution_code"]


def test_tc101_correct_dataframe_returns_correct_true_and_solution():
    """TC-101: Correct pandas code → run-code passes, submit returns correct: true + solution."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_run = client.post("/api/pandas/run-code", json={
            "question_id": _easy_id,
            "code": _easy_solution,
        })
        assert r_run.status_code == 200
        body_run = r_run.json()
        assert "test_results" in body_run
        assert any(tr.get("passed") for tr in body_run["test_results"])

        r_submit = client.post("/api/pandas/submit", json={
            "question_id": _easy_id,
            "code": _easy_solution,
        })
    assert r_submit.status_code == 200
    body_submit = r_submit.json()
    assert body_submit.get("correct") is True
    assert body_submit.get("solution")


def test_tc102_wrong_dataframe_values_returns_correct_false():
    """TC-102: Same shape, wrong values → correct: false."""
    wrong_code = (
        "import pandas as pd\n"
        "def solve(df_users):\n"
        "    return pd.DataFrame({'name': ['Wrong'], 'email': ['wrong@test.com']})\n"
    )
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/pandas/submit", json={
            "question_id": _easy_id,
            "code": wrong_code,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is False
    assert body.get("feedback") or body.get("test_results")


def test_tc103_wrong_dataframe_shape_returns_correct_false():
    """TC-103: Wrong DataFrame shape (extra/missing columns) → correct: false."""
    wrong_code = (
        "import pandas as pd\n"
        "def solve(df_users):\n"
        "    return df_users[['name']]\n"  # missing 'email' column
    )
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/pandas/submit", json={
            "question_id": _easy_id,
            "code": wrong_code,
        })
    assert r.status_code == 200
    assert r.json().get("correct") is False


def test_tc104_timeout_enforced_in_pandas_sandbox():
    """TC-104: a genuine infinite loop in data mode is killed by the wall timeout.

    Uses `while True: pass` — NOT `import time; sleep`, which the pandas allowlist
    rejects before execution (the old version tested guard rejection, not the
    timeout). A bare loop is guard-allowed, so only the wall-clock timeout stops it.
    """
    code = "def solve(df_users):\n    while True:\n        pass"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        start = time.time()
        r = client.post("/api/pandas/run-code", json={
            "question_id": _easy_id,
            "code": code,
        }, timeout=25)
        elapsed = time.time() - start
    assert elapsed < 16, f"Timeout too slow: {elapsed:.1f}s"
    body = r.json()
    assert "error" in body or any(not tr.get("passed") for tr in body.get("test_results", [{}]))


def test_tc105_import_pandas_accepted():
    """TC-105: import pandas accepted by guard (200 or test failure, not guard 400)."""
    code = "import pandas as pd\ndef solve(df): return df.head()"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/pandas/run-code", json={
            "question_id": _easy_id,
            "code": code,
        })
    assert r.status_code != 400, "Guard should not reject import pandas"
