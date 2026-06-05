"""Temporal canonicalization in the shared grading comparator.

Covers the Phase-3 datetime fix: a user is not penalized for a trivial
date-representation difference (Timestamp vs date vs ISO string vs T/space
separator vs a zero time component), while genuine time-of-day and granularity
differences are preserved. The comparator (`normalize_dataframe`) is shared by
the SQL and pandas tracks, so this behaviour is consistent across both.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from evaluator import _canonicalize_temporal, normalize_dataframe
from python_evaluator import evaluate_python_data_code

BACKEND = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Unit: _canonicalize_temporal
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    # zero/absent time → date only
    ("2024-01-05", "2024-01-05"),
    ("2024-01-05T00:00:00", "2024-01-05"),
    ("2024-01-05 00:00:00", "2024-01-05"),
    ("2024-01-05T00:00:00.000000", "2024-01-05"),
    ("2024-01-05 00:00:00.0", "2024-01-05"),
    # real time → kept, separator normalized to 'T'
    ("2024-01-05 23:28:10", "2024-01-05T23:28:10"),
    ("2024-01-05T23:28:10", "2024-01-05T23:28:10"),
    ("2024-01-05T13:30:00.500", "2024-01-05T13:30:00.500"),
    # not a full date / tz-aware / non-temporal → untouched
    ("2024-01", "2024-01"),
    ("2024", "2024"),
    ("2024-01-05T00:00:00+05:30", "2024-01-05T00:00:00+05:30"),
    ("2024-01-05T00:00:00Z", "2024-01-05T00:00:00Z"),
    ("organic", "organic"),
    ("42", "42"),
    ("", ""),
])
def test_canonicalize_temporal(raw, expected):
    assert _canonicalize_temporal(raw) == expected


# ---------------------------------------------------------------------------
# Unit: normalize_dataframe — date representations compare equal / unequal
# ---------------------------------------------------------------------------
def _norm(df):
    return normalize_dataframe(df)


def test_timestamp_date_and_string_midnight_all_equal():
    a = pd.DataFrame({"d": [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-02-09")]})
    b = pd.DataFrame({"d": ["2024-01-05", "2024-02-09"]})
    c = pd.DataFrame({"d": ["2024-01-05T00:00:00", "2024-02-09 00:00:00"]})
    assert _norm(a).equals(_norm(b))
    assert _norm(a).equals(_norm(c))


def test_real_time_is_preserved_and_not_collapsed():
    has_time = pd.DataFrame({"d": ["2024-01-05T23:28:10"]})
    date_only = pd.DataFrame({"d": ["2024-01-05"]})
    assert not _norm(has_time).equals(_norm(date_only))


def test_separator_difference_is_tolerated_for_real_times():
    t_sep = pd.DataFrame({"d": ["2024-01-05T23:28:10"]})
    space_sep = pd.DataFrame({"d": ["2024-01-05 23:28:10"]})
    assert _norm(t_sep).equals(_norm(space_sep))


def test_month_granularity_is_preserved():
    month = pd.DataFrame({"d": ["2024-01"]})
    day = pd.DataFrame({"d": ["2024-01-05"]})
    assert not _norm(month).equals(_norm(day))


def test_null_and_float_canonicalization_unaffected():
    a = pd.DataFrame({"n": [5.0, None], "x": ["2024-01-05T00:00:00", "a"]})
    b = pd.DataFrame({"n": [5, float("nan")], "x": ["2024-01-05", "a"]})
    assert _norm(a).equals(_norm(b))


# ---------------------------------------------------------------------------
# Integration: a date-only question accepts every trivial representation,
# but rejects a submission that keeps the real time it was asked to drop.
# (Q31017 "Extract Order Date (Date Only)" — source order_date carries a time.)
# ---------------------------------------------------------------------------
def _load_q(qid: int):
    for diff in ("easy", "medium", "hard"):
        path = BACKEND / "content" / "python_data_questions" / f"{diff}.json"
        for q in json.loads(path.read_text(encoding="utf-8")):
            if q.get("id") == qid:
                return q
    raise AssertionError(f"question {qid} not found")


def _mk_31017(date_expr: str) -> str:
    return (
        "import pandas as pd\n"
        "def solve(df_orders):\n"
        "    df = df_orders.copy()\n"
        "    df['order_date'] = pd.to_datetime(df['order_date'])\n"
        f"    df['order_day'] = {date_expr}\n"
        "    result = df[['order_id','user_id','order_day','net_amount']]\n"
        "    return result.sort_values('order_day').reset_index(drop=True)\n"
    )


@pytest.mark.parametrize("date_expr", [
    "df['order_date'].dt.date",                    # python date objects (== reference)
    "df['order_date'].dt.strftime('%Y-%m-%d')",    # string
    "df['order_date'].dt.normalize()",             # midnight Timestamp
])
def test_date_question_accepts_trivial_representations(date_expr):
    q = _load_q(31017)
    res = evaluate_python_data_code(_mk_31017(date_expr), q)
    assert res.get("correct") is True, res.get("error")


def test_date_question_rejects_kept_real_time():
    # Returning the full timestamp keeps a time the prompt asked to drop → wrong.
    q = _load_q(31017)
    res = evaluate_python_data_code(_mk_31017("df['order_date']"), q)
    assert res.get("correct") is False


def test_datetime_returning_expected_no_longer_crashes():
    # All 10 previously-ungradeable datetime questions now grade their own
    # reference solution as correct (no serialization crash).
    for qid in (31006, 31010, 31012, 31017, 31018, 31025, 32020, 32072, 32073, 32090):
        q = _load_q(qid)
        res = evaluate_python_data_code(q["expected_code"], q)
        assert res.get("correct") is True, f"{qid}: {res.get('error')}"
