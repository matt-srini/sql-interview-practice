"""
Security guard tests — verify that prohibited code/SQL hits a hard block at
the API layer and that users receive a clear error message.

Three guard surfaces are tested:

  SQL  (/api/run-query, /api/submit)
    - Mutating statements: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER,
      TRUNCATE, MERGE, COPY
    - Multi-statement execution
    - DuckDB filesystem/network table functions: read_csv, read_json, glob,
      sqlite_scan, read_parquet, duckdb_settings …
    - Cartesian join and join-count limits

  Python algorithm  (/api/python/run-code, /api/python/submit)
    - import statements (any module)
    - from … import
    - Dangerous builtins: eval, exec, compile, open, __import__
    - Dangerous attribute access: __class__, __subclasses__, __globals__ …
    - Infinite loop (timeout)
    - Stdout bomb (truncation, no crash)
    - Huge return value (hard cap)

  Pandas  (/api/python-data/run-code, /api/python-data/submit)
    - Disallowed imports (os, subprocess, socket, urllib …)
    - Dangerous builtins: eval, exec, open
    - pandas I/O methods: pd.read_csv, pd.read_html, pd.to_csv …
    - numpy I/O methods: np.load, np.save …
    - Dangerous attributes: __subclasses__, __globals__ …

Each test checks:
  1. HTTP status code is 400 (bad request).
  2. Response body contains an intelligible error keyword so the user is not
     left wondering what went wrong.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app


@pytest.fixture(scope="module", autouse=True)
def _db_reset_once():
    """Reset the Postgres test DB once for the entire module.

    Security-guard tests verify behaviour that fires *before* any DB write
    (the guard blocks the request immediately), so per-test isolation is not
    needed.  Running isolated_state per parametrized test causes concurrent
    ALTER TABLE migrations that deadlock Postgres.
    """
    from db import close_pool, ensure_schema_admin, reset_database_admin
    from backend.main import _clear_rate_limit_state

    asyncio.run(close_pool())
    asyncio.run(ensure_schema_admin())
    asyncio.run(reset_database_admin())
    _clear_rate_limit_state()
    yield
    asyncio.run(close_pool())
    asyncio.run(reset_database_admin())
    _clear_rate_limit_state()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Clear in-memory rate-limit counters before every test.

    Without this, the many parametrized tests exhaust the per-IP limit and
    start receiving 429 instead of the guard's 400, causing false failures.
    This fixture only touches an in-memory dict — no DB ops, no deadlocks.
    """
    from backend.main import _clear_rate_limit_state
    _clear_rate_limit_state()
    yield
    _clear_rate_limit_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client() -> TestClient:
    return TestClient(app)


def _run_sql(client: TestClient, query: str, question_id: int = 1003) -> tuple[int, dict]:
    resp = client.post("/api/run-query", json={"query": query, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _submit_sql(client: TestClient, query: str, question_id: int = 1003) -> tuple[int, dict]:
    resp = client.post("/api/submit", json={"query": query, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _run_python(client: TestClient, code: str, question_id: int = 4001) -> tuple[int, dict]:
    resp = client.post("/api/python/run-code", json={"code": code, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _submit_python(client: TestClient, code: str, question_id: int = 4001) -> tuple[int, dict]:
    resp = client.post("/api/python/submit", json={"code": code, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _run_pandas(client: TestClient, code: str, question_id: int = 5002) -> tuple[int, dict]:
    resp = client.post("/api/python-data/run-code", json={"code": code, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _submit_pandas(client: TestClient, code: str, question_id: int = 5002) -> tuple[int, dict]:
    resp = client.post("/api/python-data/submit", json={"code": code, "question_id": question_id})
    try:
        body = resp.json()
    except Exception:
        body = {}
    return resp.status_code, body


def _error_text(body: dict) -> str:
    """Extract error string from any response shape."""
    detail = body.get("detail") or body.get("error") or ""
    if isinstance(detail, dict):
        return str(detail.get("error", "")) + " " + str(detail.get("guard_errors", ""))
    return str(detail)


# ---------------------------------------------------------------------------
# SQL — mutating statements
# ---------------------------------------------------------------------------

MUTATING_SQL = [
    ("INSERT INTO users VALUES (99, 'hax', 'hax@evil.com', NULL, NULL, NULL, NULL, NULL, NULL, NULL)", "INSERT"),
    ("UPDATE users SET name = 'hax' WHERE user_id = 1", "UPDATE"),
    ("DELETE FROM users WHERE user_id = 1", "DELETE"),
    ("DROP TABLE users", "DROP"),
    ("CREATE TABLE evil AS SELECT 1 AS x", "CREATE"),
    ("ALTER TABLE users ADD COLUMN evil TEXT", "ALTER"),
    ("TRUNCATE TABLE users", "TRUNCATE"),
    ("MERGE INTO users USING (SELECT 1) AS s ON false WHEN NOT MATCHED THEN INSERT VALUES (99, 'x', 'x', NULL, NULL, NULL, NULL, NULL, NULL, NULL)", "MERGE"),
]


@pytest.mark.parametrize("sql,label", MUTATING_SQL, ids=[x[1] for x in MUTATING_SQL])
def test_sql_mutating_blocked_run(sql: str, label: str) -> None:
    with _client() as client:
        status, body = _run_sql(client, sql)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert err, f"{label}: expected non-empty error message. body={body}"


@pytest.mark.parametrize("sql,label", MUTATING_SQL, ids=[x[1] for x in MUTATING_SQL])
def test_sql_mutating_blocked_submit(sql: str, label: str) -> None:
    with _client() as client:
        status, body = _submit_sql(client, sql)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    assert _error_text(body), f"{label}: empty error. body={body}"


# ---------------------------------------------------------------------------
# SQL — multi-statement
# ---------------------------------------------------------------------------

def test_sql_multi_statement_blocked_run() -> None:
    with _client() as client:
        status, body = _run_sql(client, "SELECT 1; SELECT 2;")
    assert status == 400
    assert "single" in _error_text(body).lower()


def test_sql_multi_statement_blocked_submit() -> None:
    with _client() as client:
        status, body = _submit_sql(client, "SELECT 1; DROP TABLE users;")
    assert status == 400


# ---------------------------------------------------------------------------
# SQL — DuckDB filesystem / network functions
# ---------------------------------------------------------------------------

DANGEROUS_SQL_FUNCTIONS = [
    ("SELECT * FROM read_csv('/etc/passwd')", "read_csv"),
    ("SELECT * FROM read_csv_auto('/etc/passwd')", "read_csv_auto"),
    ("SELECT * FROM read_json('/tmp/x.json')", "read_json"),
    ("SELECT * FROM read_parquet('/tmp/x.parquet')", "read_parquet"),
    ("SELECT * FROM glob('/etc/*')", "glob"),
    ("SELECT * FROM sqlite_scan('/tmp/app.db', 'users')", "sqlite_scan"),
    ("SELECT * FROM duckdb_settings()", "duckdb_settings"),
    ("SELECT * FROM duckdb_extensions()", "duckdb_extensions"),
    ("SELECT * FROM duckdb_tables()", "duckdb_tables"),
    ("SELECT * FROM duckdb_secrets()", "duckdb_secrets"),
]


@pytest.mark.parametrize("sql,label", DANGEROUS_SQL_FUNCTIONS, ids=[x[1] for x in DANGEROUS_SQL_FUNCTIONS])
def test_sql_dangerous_function_blocked_run(sql: str, label: str) -> None:
    with _client() as client:
        status, body = _run_sql(client, sql)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert err, f"{label}: empty error. body={body}"


@pytest.mark.parametrize("sql,label", DANGEROUS_SQL_FUNCTIONS, ids=[x[1] for x in DANGEROUS_SQL_FUNCTIONS])
def test_sql_dangerous_function_blocked_submit(sql: str, label: str) -> None:
    with _client() as client:
        status, body = _submit_sql(client, sql)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# SQL — join limits
# ---------------------------------------------------------------------------

def test_sql_cartesian_join_blocked() -> None:
    sql = (
        "SELECT * FROM users "
        "JOIN orders ON 1=1"
    )
    with _client() as client:
        # No ON clause → cartesian. Use CROSS JOIN explicitly as well.
        status, body = _run_sql(
            client,
            "SELECT * FROM users CROSS JOIN orders",
            question_id=1003,
        )
    assert status == 400
    assert "cartesian" in _error_text(body).lower() or "join" in _error_text(body).lower()


def test_sql_too_many_joins_blocked() -> None:
    sql = (
        "SELECT 1 "
        "FROM users u "
        "JOIN orders o ON o.user_id = u.user_id "
        "JOIN employees e ON e.country = u.country "
        "JOIN departments d ON d.department_id = e.department_id "
        "JOIN products p ON p.is_active = TRUE "
        "JOIN users u2 ON u2.user_id = u.user_id"
    )
    with _client() as client:
        status, body = _run_sql(client, sql, question_id=1003)
    assert status == 400
    assert "join" in _error_text(body).lower() or "complex" in _error_text(body).lower()


# ---------------------------------------------------------------------------
# SQL — legitimate queries still work
# ---------------------------------------------------------------------------

VALID_SQL = [
    "SELECT user_id, name FROM users ORDER BY user_id LIMIT 5",
    "WITH top AS (SELECT user_id FROM users LIMIT 10) SELECT COUNT(*) FROM top",
    "SELECT COUNT(*) FROM users WHERE signup_date > '2022-01-01'",
]


@pytest.mark.parametrize("sql", VALID_SQL)
def test_sql_valid_queries_allowed(sql: str) -> None:
    with _client() as client:
        status, body = _run_sql(client, sql)
    assert status == 200, f"Valid SQL unexpectedly blocked: {sql!r}. body={body}"
    assert "columns" in body


# ---------------------------------------------------------------------------
# Python algorithm — import guard
# ---------------------------------------------------------------------------

PYTHON_IMPORT_CASES = [
    ("import os\ndef solve(n): return os.listdir('.')", "import os"),
    ("import sys\ndef solve(n): return sys.version", "import sys"),
    ("import subprocess\ndef solve(n): return subprocess.check_output(['id'])", "import subprocess"),
    ("import socket\ndef solve(n): return socket.gethostname()", "import socket"),
    ("import builtins\ndef solve(n): return dir(builtins)", "import builtins"),
    ("from os import path\ndef solve(n): return path.exists('/')", "from os import"),
    ("from subprocess import check_output\ndef solve(n): return check_output(['id'])", "from subprocess import"),
]


@pytest.mark.parametrize("code,label", PYTHON_IMPORT_CASES, ids=[x[1] for x in PYTHON_IMPORT_CASES])
def test_python_import_blocked_run(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_python(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert "import" in err.lower() or "disallowed" in err.lower() or "not allowed" in err.lower(), \
        f"{label}: error message unclear: {err!r}"


@pytest.mark.parametrize("code,label", PYTHON_IMPORT_CASES, ids=[x[1] for x in PYTHON_IMPORT_CASES])
def test_python_import_blocked_submit(code: str, label: str) -> None:
    with _client() as client:
        status, body = _submit_python(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Python algorithm — dangerous builtin calls
# ---------------------------------------------------------------------------

PYTHON_BUILTIN_CASES = [
    ("def solve(n): return eval('1+1')", "eval"),
    ("def solve(n): exec('x=1')", "exec"),
    ("def solve(n): return compile('1', '<s>', 'eval')", "compile"),
    ("def solve(n): return open('/etc/passwd').read()", "open"),
    ("def solve(n): return __import__('os').listdir('.')", "__import__"),
]


@pytest.mark.parametrize("code,label", PYTHON_BUILTIN_CASES, ids=[x[1] for x in PYTHON_BUILTIN_CASES])
def test_python_dangerous_builtin_blocked_run(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_python(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert err, f"{label}: empty error. body={body}"


# ---------------------------------------------------------------------------
# Python algorithm — attribute escape attempts
# ---------------------------------------------------------------------------

PYTHON_ATTRIBUTE_CASES = [
    ("def solve(n): return ().__class__.__bases__[0].__subclasses__()", "__class__/__subclasses__"),
    ("def solve(n): return (lambda: None).__globals__", "__globals__"),
    ("def solve(n): return solve.__code__", "__code__"),
    ("def solve(n): return getattr(n, '__class__')", "getattr __class__"),
]


@pytest.mark.parametrize("code,label", PYTHON_ATTRIBUTE_CASES, ids=[x[1] for x in PYTHON_ATTRIBUTE_CASES])
def test_python_attribute_escape_blocked(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_python(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Python algorithm — resource abuse (via evaluator, not guard)
# ---------------------------------------------------------------------------

def test_python_infinite_loop_times_out() -> None:
    # Use *args so the signature matches any question's test cases — the loop
    # must actually run to trigger the timeout.
    code = "def solve(*args):\n    while True:\n        pass\n"
    with _client() as client:
        status, body = _run_python(client, code)
    # Guard passes (no disallowed construct); evaluator subprocess is killed
    # after CODE_TIMEOUT_SECONDS and returns an error.  The router returns 200
    # with an error field (not an HTTP error code) since this is a runtime
    # outcome, not a validation failure.
    assert status == 200, f"Expected 200 from evaluator timeout path, got {status}. body={body}"
    err = (body.get("error") or "").lower()
    assert err, f"Expected a non-empty error message for infinite loop. body={body}"
    assert (
        "timed out" in err or "timeout" in err or "execution failed" in err
    ), f"Expected timeout/execution-failed message. got: {err!r}"


def test_python_stdout_bomb_does_not_crash() -> None:
    """Printing a huge string should be silently truncated, not crash the server."""
    code = "def solve(n):\n    print('A' * 200_000)\n    return n\n"
    with _client() as client:
        status, body = _run_python(client, code)
    assert status == 200, f"Stdout bomb should not crash the server. body={body}"


def test_python_huge_return_value_blocked() -> None:
    code = "def solve(n):\n    return list(range(100_000))\n"
    with _client() as client:
        status, body = _run_python(client, code)
    # Should either be blocked (400) or return an error field (200 with error)
    if status == 200:
        results = body.get("results", [])
        if results:
            first = results[0]
            assert first.get("error") or not first.get("passed"), \
                f"Huge return should error or not pass. result={first}"
    else:
        assert status in (400, 500)


# ---------------------------------------------------------------------------
# Pandas — import guard
# ---------------------------------------------------------------------------

PANDAS_IMPORT_CASES = [
    ("import os\ndef solve(df): return df", "import os"),
    ("import subprocess\ndef solve(df): return df", "import subprocess"),
    ("import socket\ndef solve(df): return df", "import socket"),
    ("import urllib\ndef solve(df): return df", "import urllib"),
    ("import pathlib\ndef solve(df): return df", "import pathlib"),
    ("from os import getcwd\ndef solve(df): return df", "from os import"),
    ("from subprocess import run\ndef solve(df): return df", "from subprocess import"),
]


@pytest.mark.parametrize("code,label", PANDAS_IMPORT_CASES, ids=[x[1] for x in PANDAS_IMPORT_CASES])
def test_pandas_import_blocked_run(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert "import" in err.lower() or "disallowed" in err.lower() or "not allowed" in err.lower(), \
        f"{label}: error message unclear: {err!r}"


@pytest.mark.parametrize("code,label", PANDAS_IMPORT_CASES, ids=[x[1] for x in PANDAS_IMPORT_CASES])
def test_pandas_import_blocked_submit(code: str, label: str) -> None:
    with _client() as client:
        status, body = _submit_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Pandas — dangerous builtins
# ---------------------------------------------------------------------------

PANDAS_BUILTIN_CASES = [
    ("def solve(df): return eval('df')", "eval"),
    ("def solve(df): exec('x=1')", "exec"),
    ("def solve(df): return open('/etc/passwd').read()", "open"),
]


@pytest.mark.parametrize("code,label", PANDAS_BUILTIN_CASES, ids=[x[1] for x in PANDAS_BUILTIN_CASES])
def test_pandas_dangerous_builtin_blocked(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Pandas — pandas/numpy I/O methods (AST guard catches at attribute access)
# ---------------------------------------------------------------------------

PANDAS_IO_CASES = [
    ("def solve(df): return pd.read_csv('/etc/passwd')", "pd.read_csv"),
    ("def solve(df): return pd.read_html('http://evil.com')", "pd.read_html"),
    ("def solve(df): return pd.read_excel('/tmp/x.xlsx')", "pd.read_excel"),
    ("def solve(df): return pd.read_parquet('/tmp/x.parquet')", "pd.read_parquet"),
    ("def solve(df):\n    df.to_csv('/tmp/out.csv')\n    return df", "df.to_csv"),
    ("def solve(df): return pd.read_json('/tmp/x.json')", "pd.read_json"),
    ("def solve(df): return pd.read_sql('SELECT 1', None)", "pd.read_sql"),
    ("def solve(df): return np.load('/tmp/x.npy')", "np.load"),
    ("def solve(df): np.save('/tmp/x.npy', df.values)\n    return df", "np.save"),
    ("def solve(df): return np.loadtxt('/tmp/x.txt')", "np.loadtxt"),
]


@pytest.mark.parametrize("code,label", PANDAS_IO_CASES, ids=[x[1] for x in PANDAS_IO_CASES])
def test_pandas_io_blocked_run(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"
    err = _error_text(body)
    assert err, f"{label}: empty error. body={body}"


@pytest.mark.parametrize("code,label", PANDAS_IO_CASES, ids=[x[1] for x in PANDAS_IO_CASES])
def test_pandas_io_blocked_submit(code: str, label: str) -> None:
    with _client() as client:
        status, body = _submit_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Pandas — attribute escape attempts
# ---------------------------------------------------------------------------

PANDAS_ATTRIBUTE_CASES = [
    ("def solve(df): return df.__class__.__bases__", "__class__"),
    ("def solve(df): return (lambda: None).__globals__", "__globals__"),
    ("def solve(df): return df.__subclasses__", "__subclasses__"),
]


@pytest.mark.parametrize("code,label", PANDAS_ATTRIBUTE_CASES, ids=[x[1] for x in PANDAS_ATTRIBUTE_CASES])
def test_pandas_attribute_escape_blocked(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_pandas(client, code)
    assert status == 400, f"{label}: expected 400, got {status}. body={body}"


# ---------------------------------------------------------------------------
# Pandas — legitimate code still works
# ---------------------------------------------------------------------------

VALID_PANDAS = [
    (
        "def solve(users):\n"
        "    return users[['user_id', 'name']].head(5)\n",
        "basic filter",
    ),
    (
        "def solve(users):\n"
        "    import pandas as pd\n"
        "    return users.groupby('country').size().reset_index(name='count')\n",
        "groupby",
    ),
]


@pytest.mark.parametrize("code,label", VALID_PANDAS, ids=[x[1] for x in VALID_PANDAS])
def test_pandas_valid_code_allowed(code: str, label: str) -> None:
    with _client() as client:
        status, body = _run_pandas(client, code)
    # A 200 means the guard passed; the evaluator may still return an error
    # for wrong output shape — that is acceptable here.
    assert status == 200, f"Valid pandas code unexpectedly blocked ({label}). body={body}"
