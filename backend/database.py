def init_user_profile_storage() -> None:
    conn = get_connection(read_only=False)
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id VARCHAR PRIMARY KEY,
                plan VARCHAR NOT NULL,
                metadata JSON
            );
            '''
        )
    finally:
        conn.close()

def get_user_profile(user_id: str):
    conn = get_connection(read_only=True)
    try:
        row = conn.execute(
            'SELECT user_id, plan, metadata FROM user_profiles WHERE user_id = ?', [user_id]
        ).fetchone()
        if not row:
            return None
        return {
            'user_id': row[0],
            'plan': row[1],
            'metadata': row[2] if row[2] is not None else None
        }
    finally:
        conn.close()

def set_user_profile(user_id: str, plan: str, metadata=None):
    import logging
    conn = get_connection(read_only=False)
    try:
        logging.info(f"[set_user_profile] Writing user_id={user_id}, plan={plan}, metadata={metadata}")
        conn.execute(
            'INSERT INTO user_profiles(user_id, plan, metadata) VALUES (?, ?, ?)' 
            'ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, metadata=excluded.metadata',
            [user_id, plan, metadata]
        )
        conn.commit()
        logging.info(f"[set_user_profile] Commit complete for user_id={user_id}")
    finally:
        conn.close()
import os
import re

import duckdb

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")
DB_PATH = os.path.join(os.path.dirname(__file__), "sql_practice.duckdb")
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection to the project database file."""
    import os
    if os.environ.get("TESTING") == "1":
        # Always use read_only=False in test mode to ensure visibility across connections
        return duckdb.connect(database=DB_PATH, read_only=False)
    return duckdb.connect(database=DB_PATH, read_only=read_only)


def _table_name_from_dataset_file(dataset_file: str) -> str:
    if not dataset_file.endswith(".csv"):
        raise ValueError(f"Unsupported dataset file: {dataset_file}")
    table_name = dataset_file[:-4]
    if not _TABLE_NAME_RE.match(table_name):
        raise ValueError(f"Invalid dataset/table name: {dataset_file}")
    return table_name


def create_isolated_connection(question: dict) -> duckdb.DuckDBPyConnection:
    """
    Creates a fresh DuckDB in-memory connection and loads only the question's datasets.
    """
    dataset_files = question.get("dataset_files") if isinstance(question, dict) else None
    if not dataset_files or not isinstance(dataset_files, list):
        raise ValueError("Question must provide dataset_files for isolated execution")

    conn = duckdb.connect(database=":memory:")
    try:
        for dataset_file in dataset_files:
            table_name = _table_name_from_dataset_file(str(dataset_file))
            dataset_path = os.path.abspath(os.path.join(DATASETS_DIR, str(dataset_file)))
            datasets_root = os.path.abspath(DATASETS_DIR)
            if not dataset_path.startswith(f"{datasets_root}{os.sep}"):
                raise ValueError(f"Invalid dataset path: {dataset_file}")
            if not os.path.exists(dataset_path):
                raise ValueError(f"Dataset file not found: {dataset_file}")

            conn.execute(
                f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
                [dataset_path],
            )

        return conn
    except Exception:
        conn.close()
        raise


def load_datasets() -> None:
    """
    Read every CSV file in the datasets/ directory and register it as a
    persistent DuckDB table named after the file (without the .csv extension).
    """
    conn = get_connection(read_only=False)
    loaded = []

    try:
        for filename in sorted(os.listdir(DATASETS_DIR)):
            if not filename.endswith(".csv"):
                continue
            table_name = filename[:-4]  # strip .csv
            filepath = os.path.join(DATASETS_DIR, filename)
            # CREATE OR REPLACE so re-loading is safe
            conn.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{filepath}')"
            )
            loaded.append(table_name)
    finally:
        conn.close()

    print(f"[database] Loaded tables: {', '.join(loaded)}")


def get_loaded_tables() -> list[str]:
    """Return currently available table names in the DuckDB database."""
    conn = get_connection(read_only=True)
    try:
        rows = conn.execute("SHOW TABLES").fetchall()
        return sorted([r[0] for r in rows])
    finally:
        conn.close()
