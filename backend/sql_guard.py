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
    # DuckDB-specific AST nodes that sqlglot knows about
    "ReadCSV",
]

_ALLOWED_ROOT_NAMES = [
    "Select",
    "Union",
    "Intersect",
    "Except",
]

# DuckDB table-valued functions and scalar functions that can read from the
# filesystem or network.  A user could embed these inside an otherwise valid
# SELECT, e.g.  SELECT * FROM read_csv('/etc/passwd').
_BLOCKED_FUNCTION_NAMES: frozenset[str] = frozenset({
    # filesystem readers
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_parquet",
    "read_text",
    "read_xlsx",
    "parquet_scan",
    "csv_scan",
    "json",
    # glob / directory listing
    "glob",
    # file import / export
    "import_file",
    "export_file",
    # external database connectors
    "sqlite_scan",
    "postgres_scan",
    "mysql_scan",
    "iceberg_scan",
    "delta_scan",
    "scan_arrow",
    "scan_fts",
    # extension / httpfs entry points
    "load",
    "load_spatial",
    "httpfs",
    # DuckDB pragma-style helpers that expose internals
    "duckdb_settings",
    "duckdb_extensions",
    "duckdb_functions",
    "duckdb_tables",
    "duckdb_views",
    "duckdb_columns",
    "duckdb_indexes",
    "duckdb_schemas",
    "duckdb_databases",
    "duckdb_secrets",
})


def _node_types_by_name(names: list[str]) -> tuple[type, ...]:
    types: list[type] = []
    for name in names:
        node_type = getattr(exp, name, None)
        if isinstance(node_type, type):
            types.append(node_type)
    return tuple(types)


DISALLOWED_NODE_TYPES = _node_types_by_name(_DISALLOWED_NODE_NAMES)
ALLOWED_ROOT_TYPES = _node_types_by_name(_ALLOWED_ROOT_NAMES)
MAX_JOINS = 5


def _validate_query_cost(statement: exp.Expression) -> None:
    from exceptions import BadRequestError
    import logging
    joins = list(statement.find_all(exp.Join))
    logging.info(f"[sql_guard] Found {len(joins)} JOINs in query.")
    if len(joins) >= MAX_JOINS:
        logging.info(f"[sql_guard] Raising join limit error: {len(joins)} >= {MAX_JOINS}")
        raise BadRequestError(f"Query is too complex. Maximum {MAX_JOINS} joins allowed.")

    for join in joins:
        has_on = join.args.get("on") is not None
        has_using = join.args.get("using") is not None
        if not has_on and not has_using:
            logging.info("[sql_guard] Raising cartesian join error.")
            raise BadRequestError(
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

    # Block dangerous function calls (filesystem / network I/O) that can
    # appear inside otherwise valid SELECT statements.
    # exp.Anonymous covers functions sqlglot doesn't recognise (e.g. future
    # DuckDB additions); exp.Func covers known ones — use sql_name() to get
    # the original SQL identifier rather than the Python class name.
    for node in statement.walk():
        func_name: str | None = None
        if isinstance(node, exp.Anonymous):
            func_name = node.name
        elif isinstance(node, exp.Func):
            try:
                func_name = node.sql_name()
            except Exception:
                func_name = node.__class__.__name__
        if func_name and func_name.lower() in _BLOCKED_FUNCTION_NAMES:
            raise ValueError(
                f"Function '{func_name}' is not allowed in queries."
            )

    _validate_query_cost(statement)

    return stripped.rstrip(";")
