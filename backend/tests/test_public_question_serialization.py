"""Standing CI guard — every question must survive public serialization.

The public question endpoints serve a question by passing its stored dict through
the track's ``get_public_question()``. That function slices ``test_cases`` by the
``public_test_cases`` *count*, so the field must be an **int** — but nothing checked
it: ``validate_content`` and the reference/execution guards never call the public
serializer. A question authored with ``public_test_cases`` as a *list* (the actual
public cases instead of the count) parsed clean, passed every guard, and then 500'd
the live endpoint with ``TypeError: slice indices must be integers`` (caught on
22051/23037 only in the browser). This guard exercises the real serialization path
for every question in every track so that class is caught in CI, not in production.
"""
import json
from pathlib import Path

import pytest

import python_questions
import python_data_questions
import pyspark_questions
import statistics_questions

BACKEND = Path(__file__).resolve().parent.parent
DIFFS = ("easy", "medium", "hard")

# (content dir, module exposing get_public_question)
TRACKS = [
    ("python_questions", python_questions),
    ("python_data_questions", python_data_questions),
    ("pyspark_questions", pyspark_questions),
    ("statistics_questions", statistics_questions),
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
    for dirname, mod in TRACKS:
        for q in _load(dirname):
            qid = q.get("id")
            try:
                pub = mod.get_public_question(q)
            except Exception as exc:  # noqa: BLE001 — we want any failure surfaced
                failures.append(f"{dirname} {qid}: get_public_question raised {type(exc).__name__}: {exc}")
                continue
            ptc = pub.get("public_test_cases")
            if ptc is not None and not isinstance(ptc, bool) and not isinstance(ptc, int):
                failures.append(
                    f"{dirname} {qid}: public_test_cases serialized as {type(ptc).__name__} "
                    f"(must be an int count — the loader slices test_cases by it)"
                )
    assert not failures, "public serialization failures:\n  " + "\n  ".join(failures)
