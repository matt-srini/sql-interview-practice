import json

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse, HTMLResponse

from config import FRONTEND_DIST_DIR, VITE_BACKEND_URL, VITE_POSTHOG_HOST, VITE_POSTHOG_KEY, VITE_SENTRY_DSN

router = APIRouter()


def _frontend_runtime_config() -> dict[str, str]:
    payload = {
        "VITE_BACKEND_URL": VITE_BACKEND_URL or "",
        "VITE_SENTRY_DSN": VITE_SENTRY_DSN or "",
        "VITE_POSTHOG_KEY": VITE_POSTHOG_KEY or "",
        "VITE_POSTHOG_HOST": VITE_POSTHOG_HOST or "",
    }
    return {key: value for key, value in payload.items() if value}


def _serve_frontend_index() -> Response:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index not found")

    index_html = index_path.read_text(encoding="utf-8")
    runtime_script = f"<script>window.__APP_CONFIG__={json.dumps(_frontend_runtime_config())};</script>"
    if "</head>" in index_html:
        index_html = index_html.replace("</head>", f"{runtime_script}</head>", 1)
    else:
        index_html = f"{runtime_script}{index_html}"
    return HTMLResponse(index_html)


def _serve_frontend_path(asset_path: str) -> Response:
    if not FRONTEND_DIST_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend bundle not found")

    requested_path = (FRONTEND_DIST_DIR / asset_path).resolve()
    dist_root = FRONTEND_DIST_DIR.resolve()
    if requested_path.is_file() and requested_path.is_relative_to(dist_root):
        return FileResponse(requested_path)

    return _serve_frontend_index()


@router.get("/")
def serve_frontend_root() -> Response:
    return _serve_frontend_index()


@router.get("/{asset_path:path}")
def serve_frontend(asset_path: str) -> Response:
    if asset_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_frontend_path(asset_path)
