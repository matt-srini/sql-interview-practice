"""
Query execution and answer evaluation.

Security note: user-submitted queries are restricted to SELECT statements only.
Execution uses read-only DuckDB connections with SQL parser validation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import time
from typing import Any

import pandas as pd

from database import create_isolated_connection
from exceptions import BadRequestError
from middleware.request_context import get_request_id
from sql_guard import validate_read_only_select_query


logger = logging.getLogger(__name__)

QUERY_TIMEOUT_SECONDS = 3
MAX_RESULT_ROWS = 200
MAX_QUERY_LENGTH = 5000


def _validate_query(query: str) -> str:
    """Validate and normalize user SQL using parser-based rules."""
    return validate_read_only_select_query(query, max_query_length=MAX_QUERY_LENGTH)


def _execute_limited_query(normalized_query: str, question: dict[str, Any]) -> pd.DataFrame:
    """Execute the query in read-only mode and cap returned rows for payloads."""
    conn = create_isolated_connection(question)
    try:
        # Execute the validated query as-is so ORDER BY semantics are preserved.
        # Wrapping in SELECT * FROM (<query>) can allow the optimizer to drop
        # inner ordering and incorrectly mark reversed-order answers as correct.
        result = conn.execute(normalized_query).fetchdf()
        if len(result) > MAX_RESULT_ROWS:
            return result.head(MAX_RESULT_ROWS)
        return result
    finally:
        conn.close()


def _run_with_timeout(normalized_query: str, question: dict[str, Any]) -> pd.DataFrame:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute_limited_query, normalized_query, question)
        try:
            return future.result(timeout=QUERY_TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise BadRequestError(
                f"Query timed out after {QUERY_TIMEOUT_SECONDS} seconds. "
                "Try a simpler query."
            ) from exc


def run_query(query: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a SELECT query and return results as {columns, rows}.
    Raises ValueError for disallowed queries or on execution error.
    """
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%sRun query: question_id=%s query_len=%s",
        prefix,
        question.get("id"),
        len(query or ""),
    )
    try:
        normalized_query = _validate_query(query)
    except Exception as exc:
        logger.info("%sQuery failed: %s", prefix, str(exc))
        raise BadRequestError(str(exc)) from exc
    try:
        start = time.time()
        result = _run_with_timeout(normalized_query, question)
        duration = time.time() - start
        logger.info("%sQuery executed in %.3fs", prefix, duration)
    except Exception as exc:
        logger.info("%sQuery failed: %s", prefix, str(exc))
        raise BadRequestError(str(exc)) from exc

    payload = {
        "columns": list(result.columns),
        "rows": result.where(pd.notnull(result), None).values.tolist(),
        "row_limit": MAX_RESULT_ROWS,
    }

    logger.info(
        "%sQuery succeeded: columns=%s rows=%s",
        prefix,
        len(payload["columns"]),
        len(payload["rows"]),
    )
    return payload


def _requires_order_sensitive_comparison(expected_query: str) -> bool:
    """
    Decide whether row order should be part of correctness.

    We preserve row order only when the expected query explicitly contains
    ORDER BY.

    This fixes cases where a prompt asks for ascending/descending output but the
    previous evaluator sorted rows during normalization and incorrectly accepted
    reversed results.
    """
    return "order by" in expected_query.lower()


def normalize_dataframe(df: pd.DataFrame, *, sort_rows: bool = True) -> pd.DataFrame:
    """
    Normalize a DataFrame so that two semantically-equal result sets compare equal.

    Steps applied, in order:
      1. Lowercase column names — "Name" and "name" are the same column.
      2. Sort columns alphabetically — column ordering must not affect correctness.
      3. Round float columns to 5 decimal places — avoids false negatives caused by
         floating-point arithmetic differences (e.g. 0.33333 vs 0.33333000001).
      4. Convert every value to a canonical string:
         - Any form of NULL (None, float NaN, pd.NA, pd.NaT) becomes the string "NULL",
           making comparisons consistent regardless of how DuckDB / pandas represents
           missing data for a given column type.
         - Whole-number floats (e.g. 5.0) are normalised to their integer string ("5")
           so that an INTEGER column and a DOUBLE column containing the same logical
           value compare equal.
         - All remaining values are converted with str(), which handles decimals,
           booleans, dates, and other scalar types uniformly.
        5. Optionally sort rows deterministically — by default ordering does not
            affect correctness, but for ORDER BY-sensitive questions we preserve
            row sequence and compare it as-is.
      6. Reset the index — a clean 0-based index is required for DataFrame.equals().

    Duplicate rows are preserved throughout so that COUNT / UNION ALL results
    are compared correctly.
    """
    df = df.copy()

    # Step 1 & 2: normalise column names and reorder
    df.columns = [str(c).lower() for c in df.columns]
    df = df[sorted(df.columns)]

    # Step 3: floating-point tolerance — round before string conversion so that
    # values like 1.000001 and 1.0 collapse to the same representation.
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(5)

    # Step 4: canonical string conversion
    def _to_canonical(v: object) -> str:
        # Catch all NULL-like sentinels before any other check.
        if v is None:
            return "NULL"
        if isinstance(v, float) and pd.isna(v):
            return "NULL"
        # pd.NA (nullable integer / boolean) and pd.NaT both satisfy pd.isna();
        # wrap in try/except because pd.isna raises TypeError for some container types.
        try:
            if pd.isna(v):
                return "NULL"
        except (TypeError, ValueError):
            pass

        # Normalise whole-number floats to integer strings (5.0 → "5") so that an
        # INTEGER column and a FLOAT column with the same logical value are equal.
        if isinstance(v, float) and v == int(v):
            return str(int(v))

        return str(v)

    df = df.apply(lambda col: col.map(_to_canonical))

    # Step 5 & 6: deterministic row order (when allowed), clean index
    if sort_rows:
        df = df.sort_values(by=list(df.columns))
    df = df.reset_index(drop=True)

    return df


def evaluate(user_query: str, expected_query: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run both queries and compare their result sets.
    Returns a dict with keys: correct, user_result, expected_result.
    """
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info("%sEvaluate answer: question_id=%s", prefix, question.get("id"))

    eval_start = time.time()
    user_result = run_query(user_query, question)
    expected_result = run_query(expected_query, question)

    # Build DataFrames from the already-serialised row/column payloads so that
    # the same representation used by the UI is also used for evaluation.
    user_df = pd.DataFrame(user_result["rows"], columns=user_result["columns"])
    expected_df = pd.DataFrame(
        expected_result["rows"], columns=expected_result["columns"]
    )

    try:
        order_sensitive = _requires_order_sensitive_comparison(expected_query)
        correct = normalize_dataframe(user_df, sort_rows=not order_sensitive).equals(
            normalize_dataframe(expected_df, sort_rows=not order_sensitive)
        )
    except Exception:
        correct = False

    logger.info("%sEvaluation complete: correct=%s", prefix, correct)
    logger.info("%sEvaluation completed in %.3fs", prefix, time.time() - eval_start)

    return {
        "correct": correct,
        "user_result": user_result,
        "expected_result": expected_result,
    }
