"""Regression: unhandled 500s must carry CORS headers.

FastAPI's generic ``@app.exception_handler(Exception)`` is invoked by Starlette's
ServerErrorMiddleware — the outermost middleware, *above* CORSMiddleware — so a
500 would otherwise ship with no ``Access-Control-Allow-Origin`` and the browser
reports the request cross-origin as an opaque "Network Error", hiding the real
failure. (Clean AppError/HTTPException responses flow back through the middleware
and keep their CORS headers, so this only concerns the 500 path.)
"""
import pytest
from starlette.testclient import TestClient
from starlette.routing import Route

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

ORIGIN = "http://localhost:3000"


# Test-only route that raises an unhandled exception, to exercise the 500 handler.
async def _cors_boom(request):  # pragma: no cover - driven via TestClient below
    raise RuntimeError("boom")


# Insert ahead of the SPA catch-all route (which would otherwise 404 this unknown
# /api path) so the request actually reaches the handler and triggers a 500.
app.router.routes.insert(0, Route("/api/__cors_boom__", _cors_boom, methods=["GET"]))


def test_unhandled_500_carries_cors_headers(monkeypatch):
    monkeypatch.setattr(main, "ALLOWED_ORIGINS", [ORIGIN])
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/api/__cors_boom__", headers={"Origin": ORIGIN})
    assert r.status_code == 500
    # Without the fix these assertions fail: the browser would see "Network Error".
    assert r.headers.get("access-control-allow-origin") == ORIGIN
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_unhandled_500_omits_cors_for_disallowed_origin(monkeypatch):
    monkeypatch.setattr(main, "ALLOWED_ORIGINS", [ORIGIN])
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/api/__cors_boom__", headers={"Origin": "https://evil.example"})
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") is None
