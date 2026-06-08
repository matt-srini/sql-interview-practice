"""Standing CI guard — every question in every track must survive public serialization.

The public question endpoints serve a question by passing its stored dict through the
track's ``get_public_question()``. For code tracks that function slices ``test_cases``
by the ``public_test_cases`` *count*, so the field must be an **int** — but nothing
checked it: ``validate_content`` and the reference/execution guards never call the
public serializer. A question authored with ``public_test_cases`` as a *list* (the
actual public cases instead of the count) parsed clean, passed every guard, and then
500'd the live endpoint with ``TypeError: slice indices must be integers`` (caught on
22051/23037 only in the browser). This guard exercises the real serialization path for
**every question in every track** so that class — and any other serialization break —
is caught in CI, not in production.
"""
import json
from pathlib import Path

import pytest

import questions as sql_questions
import python_questions
import python_data_questions
import pyspark_questions
import data_engineering_questions
import data_modeling_questions
import statistics_questions
import ml_fundamentals_questions
import experimentation_questions

BACKEND = Path(__file__).resolve().parent.parent
DIFFS = ("easy", "medium", "hard")

# (content dir under backend/content, module exposing get_public_question) — all 9 tracks
TRACKS = [
    ("questions", sql_questions),  # SQL
    ("python_questions", python_questions),
    ("python_data_questions", python_data_questions),
    ("pyspark_questions", pyspark_questions),
    ("data_engineering_questions", data_engineering_questions),
    ("data_modeling_questions", data_modeling_questions),
    ("statistics_questions", statistics_questions),
    ("ml_fundamentals_questions", ml_fundamentals_questions),
    ("experimentation_questions", experimentation_questions),
]


def _load(dirname):
    out = []
    d = BACKEND / "content" / dirname
    for diff in DIFFS:
        fp = d / f"{diff}.json"
        if not fp.exists():
            continue
        for q in json.loads(fp.read_text(encoding="utf-8")):
            if isinstance(q, dict):
                out.append(q)
    return out


def test_every_question_public_serializes():
    failures = []
    total = 0
    for dirname, mod in TRACKS:
        if not hasattr(mod, "get_public_question"):
            failures.append(f"{dirname}: module has no get_public_question (guard assumption broke)")
            continue
        for q in _load(dirname):
            total += 1
            qid = q.get("id")
            try:
                pub = mod.get_public_question(q)
            except Exception as exc:  # noqa: BLE001 — any failure must surface
                failures.append(f"{dirname} {qid}: get_public_question raised {type(exc).__name__}: {exc}")
                continue
            ptc = pub.get("public_test_cases")
            # public_test_cases (when present) is an int count the loader slices by; a
            # list/str/float here is the exact bug class this guard exists to catch.
            if ptc is not None and not isinstance(ptc, int):  # bool is an int subclass; acceptable
                failures.append(
                    f"{dirname} {qid}: public_test_cases serialized as {type(ptc).__name__} "
                    f"(must be an int count — the loader slices test_cases by it)"
                )
    assert total > 0, "no questions were loaded — guard is testing nothing"
    assert not failures, "public serialization failures:\n  " + "\n  ".join(failures)
