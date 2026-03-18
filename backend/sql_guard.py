from __future__ import annotations

from sqlglot import errors, exp, parse  # type: ignore[reportMissingImports]


_DISALLOWED_NODE_NAMES = [
    "Insert",
    "Update",
    "Delete",
    "Drop",
    "Create",
    "Alter",
    "TruncateTable",
    "Merge",
    "Command",
    "Copy",
    "Transaction",
    "Grant",
    "Revoke",
    "Use",
]

_ALLOWED_ROOT_NAMES = [
    "Select",
    "Union",
    "Intersect",
    "Except",
]


def _node_types_by_name(names: list[str]) -> tuple[type, ...]:
    types: list[type] = []
    for name in names:
        node_type = getattr(exp, name, None)
        if isinstance(node_type, type):
            types.append(node_type)
    return tuple(types)


DISALLOWED_NODE_TYPES = _node_types_by_name(_DISALLOWED_NODE_NAMES)
ALLOWED_ROOT_TYPES = _node_types_by_name(_ALLOWED_ROOT_NAMES)
MAX_JOINS = 4


def _validate_query_cost(statement: exp.Expression) -> None:
    joins = list(statement.find_all(exp.Join))
    if len(joins) > MAX_JOINS:
        raise ValueError(f"Query is too complex. Maximum {MAX_JOINS} joins allowed.")

    for join in joins:
        has_on = join.args.get("on") is not None
        has_using = join.args.get("using") is not None
        if not has_on and not has_using:
            raise ValueError(
                "Potential Cartesian join detected. Add an ON or USING condition."
            )


def validate_read_only_select_query(query: str, max_query_length: int) -> str:
    """
    Validate that a SQL statement is a single read-only SELECT-style query.
    Returns a normalized query string without a trailing semicolon.
    """
    stripped = query.strip()
    if not stripped:
        raise ValueError("Query cannot be empty.")

    if len(stripped) > max_query_length:
        raise ValueError(
            f"Query is too long. Maximum length is {max_query_length} characters."
        )

    try:
        statements = parse(stripped, read="duckdb")
    except errors.ParseError as exc:
        raise ValueError(f"Invalid SQL: {exc}") from exc

    if len(statements) != 1:
        raise ValueError("Only a single SQL statement is allowed.")

    statement = statements[0]

    if ALLOWED_ROOT_TYPES and not isinstance(statement, ALLOWED_ROOT_TYPES):
        raise ValueError("Only SELECT queries are allowed.")

    if DISALLOWED_NODE_TYPES:
        for node in statement.walk():
            if isinstance(node, DISALLOWED_NODE_TYPES):
                raise ValueError("Only read-only SELECT queries are allowed.")

    _validate_query_cost(statement)

    return stripped.rstrip(";")
