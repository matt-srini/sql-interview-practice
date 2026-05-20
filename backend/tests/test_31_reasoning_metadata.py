"""TC-RM-01 to TC-RM-10 — reasoning-track interaction_mode metadata."""

from copy import deepcopy

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
import data_engineering_questions as de_catalog
import data_modeling_questions as dm_catalog
import experimentation_questions as exp_catalog
import ml_fundamentals_questions as ml_catalog
import statistics_questions as st_catalog

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

CONSTRUCTED_TRACK_CASES = [
    (
        "data-engineering",
        de_catalog,
        {"easy": [51001, 51999], "medium": [52001, 52999], "hard": [53001, 53999]},
    ),
    (
        "data-modeling",
        dm_catalog,
        {"easy": [61001, 61999], "medium": [62001, 62999], "hard": [63001, 63999]},
    ),
    (
        "ml-fundamentals",
        ml_catalog,
        {"easy": [81001, 81999], "medium": [82001, 82999], "hard": [83001, 83999]},
    ),
    (
        "experimentation",
        exp_catalog,
        {"easy": [91001, 91999], "medium": [92001, 92999], "hard": [93001, 93999]},
    ),
]


@pytest.mark.parametrize("_track_slug, catalog_module, id_ranges", CONSTRUCTED_TRACK_CASES)
def test_tc_rm01_constructed_reasoning_loaders_reject_mismatched_interaction_mode(
    _track_slug,
    catalog_module,
    id_ranges,
):
    """TC-RM-01: Constructed-reasoning loaders reject mismatched interaction_mode values."""
    candidate = deepcopy(catalog_module.QUESTIONS[0])
    candidate["interaction_mode"] = "code_adjacent_reasoning"
    with pytest.raises(ValueError, match="Invalid interaction_mode"):
        catalog_module._validate_question(candidate, id_ranges=id_ranges)


@pytest.mark.parametrize("track_slug, catalog_module, _id_ranges", CONSTRUCTED_TRACK_CASES)
def test_tc_rm02_constructed_reasoning_catalog_rows_expose_interaction_mode(
    track_slug,
    catalog_module,
    _id_ranges,
):
    """TC-RM-02: Constructed-reasoning catalog rows expose interaction_mode metadata."""
    expected_id = catalog_module.get_questions_by_difficulty()["easy"][0]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/{track_slug}/catalog")
    assert response.status_code == 200
    body = response.json()
    easy_group = next(group for group in body["groups"] if group["difficulty"] == "easy")
    row = next(question for question in easy_group["questions"] if question["id"] == expected_id)
    assert row["interaction_mode"] == "constructed_reasoning"
    assert row["type"] == catalog_module.get_question(expected_id)["type"]


@pytest.mark.parametrize("track_slug, catalog_module, _id_ranges", CONSTRUCTED_TRACK_CASES)
def test_tc_rm03_constructed_reasoning_detail_exposes_interaction_mode(
    track_slug,
    catalog_module,
    _id_ranges,
):
    """TC-RM-03: Constructed-reasoning unlocked details expose interaction_mode metadata."""
    question_id = catalog_module.get_questions_by_difficulty()["easy"][0]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/{track_slug}/questions/{question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["interaction_mode"] == "constructed_reasoning"


@pytest.mark.parametrize("track_slug, catalog_module, _id_ranges", CONSTRUCTED_TRACK_CASES)
def test_tc_rm04_constructed_reasoning_locked_detail_preserves_interaction_mode(
    track_slug,
    catalog_module,
    _id_ranges,
):
    """TC-RM-04: Locked reasoning-track details keep interaction_mode while hiding options."""
    medium_question_id = catalog_module.get_questions_by_difficulty()["medium"][-1]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/{track_slug}/questions/{medium_question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["locked"] is True
    assert body["interaction_mode"] == "constructed_reasoning"
    assert "options" not in body


def test_tc_rm05_statistics_loader_rejects_mismatched_conceptual_interaction_mode():
    """TC-RM-05: Conceptual statistics questions reject executable interaction_mode."""
    candidate = deepcopy(next(question for question in st_catalog.QUESTIONS if question["subtype"] == "conceptual"))
    candidate["interaction_mode"] = "executable_problem_solving"
    with pytest.raises(ValueError, match="Invalid interaction_mode"):
        st_catalog._validate_question(candidate, id_ranges={"easy": [71001, 71999], "medium": [72001, 72999], "hard": [73001, 73999]})


def test_tc_rm06_statistics_loader_rejects_mismatched_numerical_interaction_mode():
    """TC-RM-06: Numerical statistics questions reject constructed interaction_mode."""
    candidate = deepcopy(next(question for question in st_catalog.QUESTIONS if question["subtype"] == "numerical"))
    candidate["interaction_mode"] = "constructed_reasoning"
    with pytest.raises(ValueError, match="Invalid interaction_mode"):
        st_catalog._validate_question(candidate, id_ranges={"easy": [71001, 71999], "medium": [72001, 72999], "hard": [73001, 73999]})


def test_tc_rm07_statistics_catalog_rows_expose_hybrid_interaction_modes():
    """TC-RM-07: Statistics catalog rows expose constructed vs executable interaction_mode."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get("/api/statistics/catalog")
    assert response.status_code == 200
    body = response.json()
    easy_group = next(group for group in body["groups"] if group["difficulty"] == "easy")
    conceptual_row = next(question for question in easy_group["questions"] if question["subtype"] == "conceptual")
    numerical_row = next(question for question in easy_group["questions"] if question["subtype"] == "numerical")
    assert conceptual_row["interaction_mode"] == "constructed_reasoning"
    assert conceptual_row["type"] == "conceptual"
    assert numerical_row["interaction_mode"] == "executable_problem_solving"
    assert numerical_row["type"] == "numerical"


def test_tc_rm08_statistics_conceptual_detail_exposes_constructed_reasoning():
    """TC-RM-08: Conceptual statistics detail exposes constructed_reasoning interaction_mode."""
    conceptual_id = next(question["id"] for question in st_catalog.QUESTIONS if question["subtype"] == "conceptual")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/statistics/questions/{conceptual_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["interaction_mode"] == "constructed_reasoning"


def test_tc_rm09_statistics_numerical_detail_exposes_executable_problem_solving():
    """TC-RM-09: Numerical statistics detail exposes executable_problem_solving interaction_mode."""
    numerical_id = next(question["id"] for question in st_catalog.QUESTIONS if question["subtype"] == "numerical")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/statistics/questions/{numerical_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["interaction_mode"] == "executable_problem_solving"


def test_tc_rm10_statistics_locked_detail_preserves_interaction_mode():
    """TC-RM-10: Locked statistics detail includes interaction_mode while preserving lock behavior."""
    medium_question_id = st_catalog.get_questions_by_difficulty()["medium"][-1]["id"]
    expected_mode = st_catalog.get_question(medium_question_id)["interaction_mode"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        response = client.get(f"/api/statistics/questions/{medium_question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["locked"] is True
    assert body["interaction_mode"] == expected_mode