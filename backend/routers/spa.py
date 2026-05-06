import json
import re
from html import escape as html_escape

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse

from config import FRONTEND_BASE_URL, FRONTEND_DIST_DIR, VITE_BACKEND_URL, VITE_POSTHOG_HOST, VITE_POSTHOG_KEY, VITE_SENTRY_DSN

router = APIRouter()

BASE_URL = "https://datathink.co"

_TRACK_LABELS = {"sql": "SQL", "python": "Python", "python-data": "Pandas", "pyspark": "PySpark"}

# Cached at first use — filesystem reads only, no DB
_INDEX_HTML_CACHE: str | None = None
_SEO_META: dict | None = None


def _get_index_html() -> str:
    global _INDEX_HTML_CACHE
    if _INDEX_HTML_CACHE is None:
        index_path = FRONTEND_DIST_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Frontend index not found")
        _INDEX_HTML_CACHE = index_path.read_text(encoding="utf-8")
    return _INDEX_HTML_CACHE


def _build_seo_meta() -> dict:
    meta: dict = {
        "/": {
            "title": "datathink — SQL, Python & Data Interview Practice",
            "description": "Practice SQL, Python, Pandas, and PySpark interview questions in a real execution environment. 350+ questions, instant feedback, and curated learning paths for data professionals.",
        },
        "/learn": {
            "title": "Learning Paths — datathink",
            "description": "Curated SQL, Python, Pandas, and PySpark learning paths to build interview-ready skills step by step.",
        },
        "/learn/sql": {
            "title": "SQL Learning Paths — datathink",
            "description": "Curated SQL learning paths covering window functions, aggregation, cohort analysis, and more.",
        },
        "/learn/python": {
            "title": "Python Learning Paths — datathink",
            "description": "Curated Python learning paths covering algorithms, data structures, and data processing patterns.",
        },
        "/learn/python-data": {
            "title": "Pandas Learning Paths — datathink",
            "description": "Curated Pandas learning paths covering DataFrame manipulation, groupby, reshaping, and time series.",
        },
        "/learn/pyspark": {
            "title": "PySpark Learning Paths — datathink",
            "description": "Curated PySpark learning paths covering Spark core concepts, performance, streaming, and Delta Lake.",
        },
        "/practice/sql": {
            "title": "SQL Interview Practice — datathink",
            "description": "Practice 95 SQL interview questions against real datasets. Instant DuckDB execution with solution analysis.",
        },
        "/practice/python": {
            "title": "Python Interview Practice — datathink",
            "description": "Practice 83 Python algorithm and data processing interview questions with test case feedback.",
        },
        "/practice/python-data": {
            "title": "Pandas Interview Practice — datathink",
            "description": "Practice 76 Pandas interview questions with live DataFrame execution and output comparison.",
        },
        "/practice/pyspark": {
            "title": "PySpark Interview Practice — datathink",
            "description": "Practice 102 PySpark interview questions covering MCQ, predict-output, debug, and scenario formats.",
        },
    }

    # Sample pages: 4 tracks × 3 difficulties
    for topic, label in _TRACK_LABELS.items():
        for diff, diff_label in [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]:
            meta[f"/sample/{topic}/{diff}"] = {
                "title": f"Free {diff_label} {label} Sample Questions — datathink",
                "description": (
                    f"Try free {diff_label.lower()} {label} interview questions — no account required. "
                    "Real execution environment with instant feedback."
                ),
            }

    # Pages crawlers should not index
    for path in ["/auth", "/dashboard", "/mock"]:
        meta[path] = {"noindex": True}

    # Dynamic: 22 learning paths (filesystem reads)
    try:
        from path_loader import get_all_paths
        for p in get_all_paths():
            slug = p.get("slug", "")
            topic = p.get("topic", "sql")
            raw_desc = f"{p.get('description', '')} {p.get('outcomes', '')}".strip()
            desc = raw_desc[:152] + "..." if len(raw_desc) > 155 else raw_desc
            meta[f"/learn/{topic}/{slug}"] = {
                "title": f"{p['title']} — datathink",
                "description": desc,
            }
    except Exception:
        pass  # graceful degradation if paths can't be loaded

    return meta


def _get_seo_meta() -> dict:
    global _SEO_META
    if _SEO_META is None:
        _SEO_META = _build_seo_meta()
    return _SEO_META


def _inject_seo(html: str, url_path: str) -> str:
    m = _get_seo_meta().get(url_path)
    if not m:
        return html

    if m.get("noindex"):
        return html.replace("</head>", '<meta name="robots" content="noindex, nofollow" /></head>', 1)

    title = html_escape(m["title"])
    desc = html_escape(m["description"])
    canonical = f"{BASE_URL}{url_path}"
    og_image = f"{BASE_URL}/og-image.svg"

    html = re.sub(r"<title>[^<]*</title>", f"<title>{title}</title>", html, count=1)
    html = re.sub(
        r'(<meta\s+name="description"\s+content=")[^"]*(")',
        rf"\g<1>{desc}\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<meta\s+property="og:title"\s+content=")[^"]*(")',
        rf"\g<1>{title}\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<meta\s+property="og:description"\s+content=")[^"]*(")',
        rf"\g<1>{desc}\2",
        html,
        count=1,
    )
    html = re.sub(
        r'(<meta\s+property="og:url"\s+content=")[^"]*(")',
        rf"\g<1>{canonical}\2",
        html,
        count=1,
    )

    # Inject new tags not yet present in index.html
    inject = (
        f'<link rel="canonical" href="{canonical}" />'
        f'<meta property="og:image" content="{og_image}" />'
        f'<meta name="twitter:image" content="{og_image}" />'
    )
    return html.replace("</head>", f"{inject}</head>", 1)


def _frontend_runtime_config() -> dict[str, str]:
    payload = {
        "VITE_BACKEND_URL": VITE_BACKEND_URL or "",
        "VITE_SENTRY_DSN": VITE_SENTRY_DSN or "",
        "VITE_POSTHOG_KEY": VITE_POSTHOG_KEY or "",
        "VITE_POSTHOG_HOST": VITE_POSTHOG_HOST or "",
    }
    return {key: value for key, value in payload.items() if value}


def _serve_frontend_index(request: Request) -> Response:
    index_html = _get_index_html()
    index_html = _inject_seo(index_html, request.url.path)
    runtime_script = f"<script>window.__APP_CONFIG__={json.dumps(_frontend_runtime_config())};</script>"
    index_html = index_html.replace("</head>", f"{runtime_script}</head>", 1)
    return HTMLResponse(index_html)


def _serve_frontend_path(asset_path: str, request: Request) -> Response:
    if not FRONTEND_DIST_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend bundle not found")

    requested_path = (FRONTEND_DIST_DIR / asset_path).resolve()
    dist_root = FRONTEND_DIST_DIR.resolve()
    if requested_path.is_file() and requested_path.is_relative_to(dist_root):
        return FileResponse(requested_path)

    return _serve_frontend_index(request)


@router.get("/")
def serve_frontend_root(request: Request) -> Response:
    return _serve_frontend_index(request)


@router.get("/{asset_path:path}")
def serve_frontend(asset_path: str, request: Request) -> Response:
    if asset_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_frontend_path(asset_path, request)
