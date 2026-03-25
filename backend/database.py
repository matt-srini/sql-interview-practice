import os
import re

import duckdb


DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_golden_conn: duckdb.DuckDBPyConnection | None = None


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
    global _golden_conn

    if _golden_conn is not None:
        return

    conn = duckdb.connect(database=":memory:")
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
    print(f"[database] Loaded tables: {', '.join(loaded)}")


def get_query_cursor(dataset_files: list[str]) -> duckdb.DuckDBPyConnection:
    conn = _require_query_engine()
    loaded_tables = set(get_loaded_tables())

    for dataset_file in dataset_files:
        table_name = _table_name_from_dataset_file(str(dataset_file))
        if table_name not in loaded_tables:
            raise ValueError(f"Dataset table not loaded: {table_name}")

    return conn.cursor()


def close_query_engine() -> None:
    global _golden_conn

    if _golden_conn is not None:
        _golden_conn.close()
        _golden_conn = None


def get_loaded_tables() -> list[str]:
    if _golden_conn is None:
        return []

    rows = _golden_conn.execute("SHOW TABLES").fetchall()
    return sorted([row[0] for row in rows])
