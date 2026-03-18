from __future__ import annotations

from typing import Any


EMPLOYEES_SCHEMA: dict[str, list[str]] = {
    "employees": ["id", "name", "email", "salary", "department_id"],
}

DEPARTMENTS_SCHEMA: dict[str, list[str]] = {
    "departments": ["id", "name"],
}

CUSTOMERS_SCHEMA: dict[str, list[str]] = {
    "customers": ["id", "name"],
}

ORDERS_SCHEMA: dict[str, list[str]] = {
    "orders": ["order_id", "user_id", "order_date", "amount", "status"],
}

USERS_SCHEMA: dict[str, list[str]] = {
    "users": ["user_id", "name", "signup_date", "country"],
}


def merge_schema(*schemas: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for schema in schemas:
        for table, cols in schema.items():
            merged[table] = list(cols)
    return merged


def q(
    *,
    id: int,
    order: int,
    title: str,
    description: str,
    difficulty: str,
    schema: dict[str, list[str]],
    dataset_files: list[str],
    expected_query: str,
    solution_query: str,
    explanation: str,
    hints: list[str] | None = None,
    concepts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "order": order,
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "schema": schema,
        "dataset_files": dataset_files,
        "expected_query": expected_query.strip().rstrip(";"),
        "solution_query": solution_query.strip(),
        "explanation": explanation.strip(),
        "hints": hints if hints is not None else [],
        "concepts": concepts if concepts is not None else [],
    }
