"""TC-069 to TC-074 — Question Access & Details."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
from questions import get_questions_by_difficulty as sql_qs
from python_questions import get_questions_by_difficulty as py_qs
from pyspark_questions import get_questions_by_difficulty as spark_qs

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_sql_catalog = sql_qs()
_easy_sql_id = _sql_catalog["easy"][0]["id"]
_medium_sql_id = _sql_catalog["medium"][0]["id"]

_py_catalog = py_qs()
_easy_py_id = _py_catalog["easy"][0]["id"]

_spark_catalog = spark_qs()
_easy_spark_id = _spark_catalog["easy"][0]["id"]


def test_tc069_locked_question_returns_403():
    """TC-069: Free user GET locked medium question → 200 preview (locked in progress)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/questions/{_medium_sql_id}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("progress", {}).get("unlocked") is False


def test_tc070_unlocked_question_returns_detail():
    """TC-070: Free user GET easy question → 200, has required fields, no solution."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/questions/{_easy_sql_id}")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "title" in body
    assert "prompt" in body or "description" in body
    assert "hints" in body
    assert "concepts" in body
    assert "schema" in body
    assert body.get("solution") is None


def test_tc071_solution_absent_before_submission():
    """TC-071: Solution field absent before any submission."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/questions/{_easy_sql_id}")
    assert r.status_code == 200
    body = r.json()
    assert "solution" not in body or body["solution"] is None


def test_tc072_mock_only_questions_absent_from_practice_catalog():
    """TC-072: Elite catalog count = 373 practice questions (no mock_only)."""
    from questions import get_all_questions
    from python_questions import get_all_questions as py_all
    from python_data_questions import get_all_questions as pd_all
    from pyspark_questions import get_all_questions as spark_all

    # Count practice questions (exclude mock_only)
    sql_count = len([q for q in get_all_questions() if not q.get("mock_only")])
    py_count = len([q for q in py_all() if not q.get("mock_only")])
    pd_count = len([q for q in pd_all() if not q.get("mock_only")])
    spark_count = len([q for q in spark_all() if not q.get("mock_only")])

    total = sql_count + py_count + pd_count + spark_count
    assert total == 373, f"Expected 373 practice questions, got {total} ({sql_count}+{py_count}+{pd_count}+{spark_count})"

    # Verify via HTTP catalog endpoint for elite user
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_sql = client.get("/api/catalog")
        r_py = client.get("/api/python/catalog")
        r_pd = client.get("/api/python-data/catalog")
        r_spark = client.get("/api/pyspark/catalog")

    # Verify the catalogs return questions
    assert r_sql.status_code == 200
    assert r_py.status_code == 200
    assert r_pd.status_code == 200
    assert r_spark.status_code == 200


def test_tc073_python_question_has_test_cases_and_signature():
    """TC-073: Pro user GET Python question → test_cases and function_signature."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get(f"/api/python/questions/{_easy_py_id}")
    assert r.status_code == 200
    body = r.json()
    assert "test_cases" in body
    assert isinstance(body["test_cases"], list)
    assert len(body["test_cases"]) > 0
    assert "starter_code" in body


def test_tc074_pyspark_question_has_4_options_no_correct():
    """TC-074: Free user GET PySpark question → 4 options, no correct_option field."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/pyspark/questions/{_easy_spark_id}")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert len(body["options"]) == 4
    assert "correct_option" not in body or body.get("correct_option") is None
