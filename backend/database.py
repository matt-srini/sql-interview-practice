import os
import re

import duckdb


DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_golden_conn: duckdb.DuckDBPyConnection | None = None
# Snapshot of the loaded table names, captured once at startup. The set of tables
# never changes after init (datasets are loaded once from committed CSVs), so we
# cache it instead of running `SHOW TABLES` on the shared connection on every call.
# This is load-bearing for concurrency: `_golden_conn.execute(...)` from more than
# one thread at a time SEGFAULTS the process (DuckDB connections are not thread-safe
# for concurrent use). `get_loaded_tables()` is hit by /health and by every SQL
# query (via get_query_cursor); reading the cached tuple touches no shared state, so
# it is safe to call concurrently. Actual query execution still goes through a
# per-call `conn.cursor()` serialized behind the SQL offload lock (see offload.py).
_loaded_table_names: tuple[str, ...] = ()


def _require_query_engine() -> duckdb.DuckDBPyConnection:
    if _golden_conn is None:
        raise RuntimeError("DuckDB query engine is not initialized")
    return _golden_conn


def _table_name_from_dataset_file(dataset_file: str) -> str:
    if not dataset_file.endswith(".csv"):
        raise ValueError(f"Unsupported dataset file: {dataset_file}")
    table_name = dataset_file[:-4]
    if not _TABLE_NAME_RE.match(table_name):
        raise ValueError(f"Invalid dataset/table name: {dataset_file}")
    return table_name


def init_query_engine() -> None:
    global _golden_conn, _loaded_table_names

    if _golden_conn is not None:
        return

    conn = duckdb.connect(database=":memory:")
    # Single-threaded execution makes floating-point aggregation deterministic.
    # DuckDB parallelises aggregates, and float addition is non-associative, so a
    # multi-threaded avg()/sum() can vary in its last bits between runs; a query that
    # then ROUND()s near a boundary flips its displayed value, making grading
    # non-deterministic (a correct answer marked wrong on the unlucky run). Grading
    # datasets are tiny (≤ ~9k rows), so the throughput cost is negligible and the
    # determinism is load-bearing for sound comparison. See evaluator._results_match
    # and tests/test_sql_grading_determinism.py.
    conn.execute("SET threads TO 1")
    loaded = []

    try:
        for filename in sorted(os.listdir(DATASETS_DIR)):
            if not filename.endswith(".csv"):
                continue
            table_name = _table_name_from_dataset_file(filename)
            filepath = os.path.join(DATASETS_DIR, filename)
            conn.execute(
                f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
                [filepath],
            )
            loaded.append(table_name)
    except Exception:
        conn.close()
        raise

    _golden_conn = conn
    _loaded_table_names = tuple(sorted(loaded))
    print(f"[database] Loaded tables: {', '.join(loaded)}")


def get_query_cursor(dataset_files: list[str]) -> duckdb.DuckDBPyConnection:
    conn = _require_query_engine()
    loaded_tables = set(_loaded_table_names)

    for dataset_file in dataset_files:
        table_name = _table_name_from_dataset_file(str(dataset_file))
        if table_name not in loaded_tables:
            raise ValueError(f"Dataset table not loaded: {table_name}")

    return conn.cursor()


def close_query_engine() -> None:
    global _golden_conn, _loaded_table_names

    if _golden_conn is not None:
        _golden_conn.close()
        _golden_conn = None
    _loaded_table_names = ()


def get_loaded_tables() -> list[str]:
    """Return the loaded table names from the startup snapshot.

    Deliberately does NOT query the shared `_golden_conn` — see `_loaded_table_names`.
    Reading the cached tuple is thread-safe; running `SHOW TABLES` on the shared
    connection concurrently (which the previous implementation did on every /health
    and every SQL query) segfaults the process.
    """
    return list(_loaded_table_names)
