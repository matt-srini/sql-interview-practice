"""
Query execution and answer evaluation.

Security note: user-submitted queries are restricted to SELECT statements only.
Execution uses a shared in-memory DuckDB query engine with SQL parser validation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import re
import time
from typing import Any

import pandas as pd

from database import get_query_cursor
from exceptions import BadRequestError
from middleware.request_context import get_request_id
from sql_analyzer import CONCEPT_LABELS, CONCEPT_TO_FEATURE, extract_query_features
from sql_guard import validate_read_only_select_query


logger = logging.getLogger(__name__)

QUERY_TIMEOUT_SECONDS = 3
MAX_RESULT_ROWS = 200
MAX_QUERY_LENGTH = 5000


def _get_explain_total_ec(query: str, question: dict[str, Any]) -> int | None:
    """Run EXPLAIN and sum all estimated cardinality (EC) values from the plan."""
    cursor = get_query_cursor(question["dataset_files"])
    try:
        rows = cursor.execute(f"EXPLAIN {query}").fetchall()
        plan_text = "\n".join(str(row[1]) for row in rows if len(row) > 1)
        ec_values = re.findall(r'\bEC:\s*(\d+)', plan_text)
        return sum(int(v) for v in ec_values) if ec_values else None
    except Exception:
        return None
    finally:
        cursor.close()


def _analyze_query_style(query: str) -> list[str]:
    """Generate style observations about a SQL query."""
    notes = []
    q = query.lower()

    if re.search(r'\bselect\s+\*', q):
        notes.append(
            "Avoid SELECT * in production — list only the columns you need for clarity and performance."
        )

    nested_count = len(re.findall(r'\(\s*select\b', q))
    has_cte = bool(re.search(r'^\s*with\b', q.lstrip()))
    if nested_count >= 2 and not has_cte:
        notes.append(
            "Consider using CTEs (WITH clauses) instead of deeply nested subqueries — they make the query easier to read and debug."
        )

    if has_cte:
        notes.append(
            "Good use of CTEs — breaking the query into named steps improves readability."
        )

    return notes


def _compute_quality(
    user_query: str,
    expected_query: str,
    question: dict[str, Any],
) -> dict[str, Any]:
    """Build the quality scorecard for a correct SQL submission."""
    efficiency_note = None
    try:
        user_ec = _get_explain_total_ec(user_query, question)
        expected_ec = _get_explain_total_ec(expected_query, question)
        if user_ec is not None and expected_ec is not None and expected_ec > 0:
            if user_ec <= expected_ec * 1.5:
                efficiency_note = (
                    f"Efficient — your query estimates ~{user_ec:,} total rows processed, "
                    f"comparable to the reference solution (~{expected_ec:,})."
                )
            else:
                ratio = user_ec / expected_ec
                efficiency_note = (
                    f"Your query estimates ~{user_ec:,} total rows processed vs "
                    f"~{expected_ec:,} for the reference solution ({ratio:.1f}× more work). "
                    "Look for opportunities to filter earlier or reduce join inputs."
                )
    except Exception:
        pass

    style_notes = _analyze_query_style(user_query)
    complexity_hint = question.get("complexity_hint")
    alternative = question.get("alternative_solution")

    return {
        "efficiency_note": efficiency_note,
        "style_notes": style_notes,
        "complexity_hint": complexity_hint,
        "alternative_solution": alternative,
    }


def _validate_query(query: str) -> str:
    """Validate and normalize user SQL using parser-based rules."""
    return validate_read_only_select_query(query, max_query_length=MAX_QUERY_LENGTH)


def _execute_limited_query(normalized_query: str, question: dict[str, Any]) -> pd.DataFrame:
    """Execute the query in read-only mode and cap returned rows for payloads."""
    cursor = get_query_cursor(question["dataset_files"])
    try:
        # Execute the validated query as-is so ORDER BY semantics are preserved.
        # Wrapping in SELECT * FROM (<query>) can allow the optimizer to drop
        # inner ordering and incorrectly mark reversed-order answers as correct.
        result = cursor.execute(normalized_query).fetchdf()
        if len(result) > MAX_RESULT_ROWS:
            return result.head(MAX_RESULT_ROWS)
        return result
    finally:
        cursor.close()


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

    def _to_json_native(v: object) -> object:
        """Convert non-JSON-serializable types (e.g. pandas.Timestamp) to safe Python types."""
        if v is None:
            return None
        if hasattr(v, "isoformat"):  # datetime, date, pandas.Timestamp
            return v.isoformat()
        return v

    clean = result.where(pd.notnull(result), None)
    payload = {
        "columns": list(result.columns),
        "rows": [[_to_json_native(v) for v in row] for row in clean.values.tolist()],
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


def _evaluate_concepts(
    user_query: str,
    question: dict[str, Any],
    result_correct: bool,
) -> tuple[bool, list[str]]:
    """
    Compare user query structure against required_concepts from the question.

    Returns:
        structure_correct: bool — False only when enforce_concepts=True and a
                           required concept is missing.
        feedback: list[str] — human-readable messages about concept usage.
    """
    required_concepts: list[str] = question.get("required_concepts") or []
    enforce: bool = bool(question.get("enforce_concepts", False))
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "

    if not required_concepts:
        return True, []

    features = extract_query_features(user_query)
    feedback: list[str] = []
    structure_correct = True

    for concept in required_concepts:
        feature_key = CONCEPT_TO_FEATURE.get(concept)
        label = CONCEPT_LABELS.get(concept, concept)

        if feature_key is None:
            logger.warning("%sUnknown concept: %s", prefix, concept)
            continue

        present = features.get(feature_key, False)

        if not present:
            if enforce:
                structure_correct = False
                feedback.append(
                    f"Result correct — this question is designed to build {label}. "
                    "The approach matters here."
                )
            else:
                feedback.append(
                    f"Your result is correct, but consider using {label} — "
                    "that's the intended approach for this question."
                )

    return structure_correct, feedback


def evaluate(user_query: str, expected_query: str, question: dict[str, Any]) -> dict[str, Any]:
    """
    Run both queries and compare their result sets, then apply concept-aware
    feedback (hybrid evaluation).

    Returns:
        correct          — result sets match
        structure_correct — required concepts present (or no concepts defined)
        feedback         — list of concept-related feedback messages
        user_result      — {columns, rows, row_limit}
        expected_result  — {columns, rows, row_limit}
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

    # Concept-aware layer — does not override result correctness
    structure_correct, feedback = _evaluate_concepts(user_query, question, correct)
    if correct and not structure_correct:
        feedback.insert(
            0,
            "Your result is correct, but the required approach was not followed."
        )
    if correct and structure_correct and not feedback:
        feedback.append("Your solution is correct and follows the intended approach.")
    elif correct and not feedback:
        feedback.append("Your solution is correct.")

    logger.info(
        "%sEvaluation complete: correct=%s structure_correct=%s feedback_count=%d",
        prefix, correct, structure_correct, len(feedback),
    )
    logger.info("%sEvaluation completed in %.3fs", prefix, time.time() - eval_start)

    quality = None
    if correct and structure_correct:
        try:
            quality = _compute_quality(user_query, expected_query, question)
        except Exception:
            logger.exception("%sQuality analysis failed", prefix)
    elif not correct and user_df.shape == expected_df.shape and user_df.shape[0] > 0:
        # Close miss: same row+column count but wrong values — surface style notes only
        try:
            style_notes = _analyze_query_style(user_query)
            if style_notes:
                quality = {
                    "efficiency_note": None,
                    "style_notes": style_notes,
                    "complexity_hint": None,
                    "alternative_solution": None,
                }
        except Exception:
            pass

    return {
        "correct": correct,
        "structure_correct": structure_correct,
        "feedback": feedback,
        "user_result": user_result,
        "expected_result": expected_result,
        "quality": quality,
    }
