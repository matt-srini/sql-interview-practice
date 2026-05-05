"""TC-001 to TC-005 — API Contract & System Endpoints."""
import pytest
from starlette.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def test_tc001_health_ok():
    """TC-001: GET /health → 200, status ok, postgres ok, at least one table."""
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "healthy"
    assert body.get("postgres") in (True, "ok", "healthy")
    # At least one table name present (DuckDB tables loaded)
    tables = body.get("tables_loaded") or body.get("tables", [])
    assert len(tables) >= 1


def test_tc002_request_id_header():
    """TC-002: X-Request-ID header is non-empty on every response."""
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID", "")
    assert len(rid) > 0


def test_tc003_response_time_header():
    """TC-003: X-Response-Time-Ms is a numeric string >= 0."""
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    rt = r.headers.get("X-Response-Time-Ms", "")
    assert rt != "", "X-Response-Time-Ms header missing"
    assert float(rt) >= 0


def test_tc004_error_shape():
    """TC-004: 4xx error has only {error, request_id} top-level keys."""
    with TestClient(app) as client:
        r = client.get("/api/questions/99999999")
    assert r.status_code >= 400
    body = r.json()
    assert "error" in body and body["error"]
    assert "request_id" in body and body["request_id"]
    # No other top-level error keys
    extra = set(body.keys()) - {"error", "request_id"}
    assert extra == set(), f"Unexpected keys in error body: {extra}"


def test_tc005_config_endpoint():
    """TC-005: GET /api/config → 200 with oauth provider info."""
    with TestClient(app) as client:
        r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    # The config returns oauth_providers list; we derive enabled booleans from it
    assert "oauth_providers" in body
    assert isinstance(body["oauth_providers"], list)
