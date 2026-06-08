"""Standing CI guard — generator-spec hidden tests must have a reference that
terminates within the user's wall-clock budget on the sized input (closes gap G4).

Hard / complexity-sensitive Python (and Statistics-numerical) questions ship hidden
test cases whose input is a *generator spec* (e.g. ``{"gen":"random_ints","n":100000}``)
paired with ``expected={"compute":"reference"}`` — the expected value is produced by
running ``expected_code`` against the generated input. ``validate_content.py``'s
reference-reproduces-tests check (gap G1 for Python) deliberately *skips* generator-spec
cases, so nothing in CI executed them: a question whose generated input is oversized
(the n=3,000,000 blow-up class) or whose reference is accidentally non-optimal could
ship with a reference that can't even finish in the time the candidate is given.

At grade time the reference is run **in-process** (in ``evaluate_python_code`` via
``_expand_test_cases``) to compute the expected value before the candidate runs in the
sandbox — so a slow reference is both an ungradeable question *and* backend latency.
This guard times exactly that path.

Limitation: it asserts the *reference* finishes within budget. It does NOT assert that
a naive baseline would time out (no naive solution is stored per question), so it cannot
confirm the hidden test actually discriminates on complexity — that remains an authoring
judgement. It does catch the concrete, recurrent failure mode: a reference/input that is
too slow to grade.
"""
import json
import time
from pathlib import Path

import pytest

from python_evaluator import _expand_test_case

BACKEND = Path(__file__).resolve().parent.parent
TRACK_DIRS = ("python_questions", "statistics_questions")
DIFFS = ("easy", "medium", "hard")

# The algorithm wall-clock budget a candidate gets. A reference that cannot compute the
# expected value within this on the sized input makes the question ungradeable. References
# are normally milliseconds, so this is generous headroom, not a tight (flaky) bound.
BUDGET_S = 5.0


def _collect_generator_cases():
    cases = []
    for d in TRACK_DIRS:
        for diff in DIFFS:
            fp = BACKEND / "content" / d / f"{diff}.json"
            if not fp.exists():
                continue
            for q in json.loads(fp.read_text(encoding="utf-8")):
                if not isinstance(q, dict):
                    continue
                expected_code = q.get("expected_code")
                if not expected_code:
                    continue
                for i, tc in enumerate(q.get("test_cases", []) or []):
                    if not isinstance(tc, dict):
                        continue
                    exp = tc.get("expected", tc.get("expected_output"))
                    if isinstance(exp, dict) and exp.get("compute") == "reference":
                        cases.append((q["id"], i, tc, expected_code))
    return cases


_GENERATOR_CASES = _collect_generator_cases()


@pytest.mark.parametrize(
    "qid,idx,tc,expected_code",
    _GENERATOR_CASES,
    ids=[f"{c[0]}-tc{c[1]}" for c in _GENERATOR_CASES],
)
def test_generator_reference_within_budget(qid, idx, tc, expected_code):
    start = time.monotonic()
    out = _expand_test_case(tc, expected_code)  # generates sized input + runs reference
    elapsed = time.monotonic() - start
    assert out.get("expected") is not None, f"Q{qid} tc{idx}: reference produced no expected value"
    assert elapsed < BUDGET_S, (
        f"Q{qid} tc{idx}: reference took {elapsed:.2f}s on the sized generator input "
        f"(budget {BUDGET_S}s) — oversized input or non-optimal reference."
    )


def test_generator_cases_exist():
    # Sanity: if this drops to zero, the collector or the bank changed — fail loudly
    # rather than silently guarding nothing.
    assert len(_GENERATOR_CASES) >= 15, (
        f"expected the generator-spec corpus (~21 questions); found {len(_GENERATOR_CASES)} cases"
    )
