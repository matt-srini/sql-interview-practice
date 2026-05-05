"""TC-229 to TC-239 — Security (SQL Guard, Python Guard, CSRF)."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from python_guard import validate_code
from sql_guard import validate_read_only_select_query
from conftest import _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ---------------------------------------------------------------------------
# TC-229 to TC-231: SQL guard
# ---------------------------------------------------------------------------

def test_tc229_sql_guard_rejects_insert():
    """TC-229: INSERT statement raises ValueError."""
    with pytest.raises(ValueError):
        validate_read_only_select_query("INSERT INTO users VALUES (1)", max_query_length=10000)


def test_tc230_sql_guard_rejects_delete():
    """TC-230: DELETE statement raises ValueError."""
    with pytest.raises(ValueError):
        validate_read_only_select_query("DELETE FROM users", max_query_length=10000)


def test_tc231_sql_guard_rejects_multiple_statements():
    """TC-231: Multiple statements raises ValueError."""
    with pytest.raises(ValueError):
        validate_read_only_select_query(
            "SELECT 1; SELECT 2", max_query_length=10000
        )


# ---------------------------------------------------------------------------
# TC-232 to TC-236: Python AST guard
# ---------------------------------------------------------------------------

def test_tc232_python_guard_rejects_import_os():
    """TC-232: 'import os' in Python (algorithm) → error returned."""
    errors = validate_code("import os\nprint(os.getcwd())", topic="python")
    assert len(errors) > 0
    assert any("os" in e for e in errors)


def test_tc233_python_guard_rejects_import_subprocess():
    """TC-233: 'import subprocess' in Python → error returned."""
    errors = validate_code("import subprocess\nresult = subprocess.run(['ls'])", topic="python")
    assert len(errors) > 0


def test_tc234_python_guard_rejects_dunder_import():
    """TC-234: __import__ call in Python → error returned."""
    errors = validate_code("x = __import__('os')\nx.system('ls')", topic="python")
    assert len(errors) > 0
    assert any("__import__" in e for e in errors)


def test_tc235_python_guard_rejects_open_for_write():
    """TC-235: open() call in Python → error returned."""
    errors = validate_code("f = open('evil.txt', 'w')\nf.write('hack')", topic="python")
    assert len(errors) > 0
    assert any("open" in e for e in errors)


def test_tc236_python_guard_allows_safe_math():
    """TC-236: Safe pure algorithm code → no errors."""
    code = """
def solve(nums):
    total = 0
    for n in nums:
        total += n
    return total
"""
    errors = validate_code(code, topic="python")
    assert errors == []


# ---------------------------------------------------------------------------
# TC-237 to TC-239: CSRF middleware
# ---------------------------------------------------------------------------

def test_tc237_csrf_blocks_request_without_origin_in_prod(monkeypatch):
    """TC-237: IS_PROD=True + session cookie + no Origin → 403."""
    monkeypatch.setattr(main, "IS_PROD", True)
    monkeypatch.setattr(main, "_CSRF_ALLOWED_ORIGINS", {"https://app.example.com"})

    with TestClient(app) as client:
        # Create a user session
        user = _make_user(client, plan="free")
        # Get the session cookie
        session_cookie = client.cookies.get("session_token")
        if not session_cookie:
            pytest.skip("No session cookie found after login")

        # Make a POST request without Origin header (the session_token cookie
        # is already in the client's cookie jar from _make_user above)
        r = client.post(
            "/api/auth/logout",
            headers={},  # no Origin header
        )
    # With IS_PROD=True and session cookie present, no Origin → 403
    assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"


def test_tc238_csrf_allows_request_with_valid_origin_in_prod(monkeypatch):
    """TC-238: IS_PROD=True + session cookie + valid Origin → 200."""
    allowed_origin = "https://app.example.com"
    monkeypatch.setattr(main, "IS_PROD", True)
    monkeypatch.setattr(main, "_CSRF_ALLOWED_ORIGINS", {allowed_origin})

    with TestClient(app) as client:
        user = _make_user(client, plan="free")
        session_cookie = client.cookies.get("session_token")
        if not session_cookie:
            pytest.skip("No session cookie found after login")

        r = client.post(
            "/api/auth/logout",
            headers={"Origin": allowed_origin},
        )
    # With valid Origin, CSRF check passes
    assert r.status_code in (200, 204), f"Expected success, got {r.status_code}: {r.text}"


def test_tc239_csrf_disabled_when_not_prod(monkeypatch):
    """TC-239: IS_PROD=False (default) → POST without Origin → 200 (no CSRF block)."""
    # Ensure IS_PROD is False (default in test env)
    monkeypatch.setattr(main, "IS_PROD", False)

    with TestClient(app) as client:
        _make_user(client, plan="free")
        # Make a POST without Origin header — should not be blocked
        r = client.post(
            "/api/auth/logout",
            headers={},
        )
    assert r.status_code in (200, 204), f"Expected success without CSRF block, got {r.status_code}"
