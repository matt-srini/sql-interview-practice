"""
SQL feature extraction for concept-aware evaluation.

Uses simple keyword-based detection (case-insensitive) — no heavy AST parsing.
Designed to be fast and dependency-free.
"""

from __future__ import annotations

import re


# Concept name → question field name mapping (used by evaluate())
CONCEPT_TO_FEATURE: dict[str, str] = {
    "group_by":        "has_group_by",
    "join":            "has_join",
    "left_join":       "has_left_join",
    "subquery":        "has_subquery",
    "window_function": "has_window_function",
    "order_by":        "has_order_by",
    "where":           "has_where",
    "aggregation":     "has_aggregation",
    "distinct":        "has_distinct",
    "having":          "has_having",
}

# Human-readable label for each concept (used in feedback messages)
CONCEPT_LABELS: dict[str, str] = {
    "group_by":        "GROUP BY",
    "join":            "JOIN",
    "left_join":       "LEFT JOIN",
    "subquery":        "a subquery",
    "window_function": "a window function",
    "order_by":        "ORDER BY",
    "where":           "a WHERE clause",
    "aggregation":     "an aggregation function (COUNT, SUM, AVG, MAX, MIN)",
    "distinct":        "DISTINCT",
    "having":          "HAVING",
}


def extract_query_features(query: str) -> dict[str, bool]:
    """
    Extract structural features from a SQL query using keyword detection.

    Returns a dict of boolean flags — True when the feature is present.
    Detection is case-insensitive and token-boundary-aware to avoid false
    positives (e.g. a column named 'order_by_user').
    """
    q = query.lower()

    def kw(pattern: str) -> bool:
        """Match a keyword/phrase surrounded by word boundaries or whitespace."""
        return bool(re.search(pattern, q))

    has_group_by = kw(r"\bgroup\s+by\b")
    has_order_by = kw(r"\border\s+by\b")
    has_where    = kw(r"\bwhere\b")
    has_having   = kw(r"\bhaving\b")
    has_distinct = kw(r"\bdistinct\b")

    # JOIN detection — LEFT JOIN is a subset of JOIN
    has_left_join = kw(r"\bleft\s+(outer\s+)?join\b")
    has_join      = has_left_join or kw(r"\b(inner\s+)?join\b")

    # Subquery: opening paren followed (eventually) by SELECT
    has_subquery = kw(r"\(\s*select\b")

    # Window functions: OVER keyword with optional partition/order clause
    has_window_function = kw(r"\bover\s*\(")

    # Aggregation: any standard aggregate function call
    has_aggregation = kw(r"\b(count|sum|avg|min|max)\s*\(")

    return {
        "has_group_by":        has_group_by,
        "has_join":            has_join,
        "has_left_join":       has_left_join,
        "has_subquery":        has_subquery,
        "has_window_function": has_window_function,
        "has_order_by":        has_order_by,
        "has_where":           has_where,
        "has_aggregation":     has_aggregation,
        "has_distinct":        has_distinct,
        "has_having":          has_having,
    }
