from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from config import (
    CANONICAL_BASE_URL,
    FRONTEND_BASE_URL,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GITHUB_REDIRECT_URI,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from database import get_loaded_tables
from db import ping

router = APIRouter()


@router.get("/health")
async def health() -> Any:
    postgres_ok = await ping()
    tables_loaded = get_loaded_tables()
    if not postgres_ok or not tables_loaded:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "postgres": postgres_ok,
                "tables_loaded": tables_loaded,
            },
        )
    return {
        "status": "healthy",
        "postgres": True,
        "tables_loaded": tables_loaded,
    }


@router.get("/api/config")
async def runtime_config() -> dict[str, list[str]]:
    oauth_providers: list[str] = []
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI:
        oauth_providers.append("google")
    if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET and GITHUB_REDIRECT_URI:
        oauth_providers.append("github")
    return {"oauth_providers": oauth_providers}


@router.get("/api/catalog/counts")
async def catalog_counts() -> dict:
    """Per-track practice question counts — computed from loaded catalogs, no auth required."""
    import importlib

    _TRACK_CONFIG = [
        ("sql",              "questions",                  "get_questions_by_difficulty"),
        ("python",           "python_questions",           "get_all_questions"),
        ("pandas",           "pandas_questions",           "get_all_questions"),
        ("pyspark",          "pyspark_questions",          "get_all_questions"),
        ("data-engineering", "data_engineering_questions", "get_all_questions"),
        ("data-modeling",    "data_modeling_questions",    "get_all_questions"),
        ("statistics",       "statistics_questions",       "get_all_questions"),
        ("ml-fundamentals",  "ml_fundamentals_questions",  "get_all_questions"),
        ("experimentation",  "experimentation_questions",  "get_all_questions"),
    ]

    result = {}
    for slug, module_name, fn_name in _TRACK_CONFIG:
        mod = importlib.import_module(module_name)
        fn = getattr(mod, fn_name)
        if fn_name == "get_questions_by_difficulty":
            grouped = fn()
            per_diff = {
                diff: len([q for q in qs if not q.get("mock_only")])
                for diff, qs in grouped.items()
            }
        else:
            practice = [q for q in fn() if not q.get("mock_only")]
            per_diff = {
                "easy":   len([q for q in practice if q.get("difficulty") == "easy"]),
                "medium": len([q for q in practice if q.get("difficulty") == "medium"]),
                "hard":   len([q for q in practice if q.get("difficulty") == "hard"]),
            }
        per_diff["total"] = per_diff["easy"] + per_diff["medium"] + per_diff["hard"]
        result[slug] = per_diff

    return result


_CANONICAL_BASE = CANONICAL_BASE_URL


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /auth\n"
        "Disallow: /dashboard\n"
        "Disallow: /mock\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {_CANONICAL_BASE}/sitemap.xml\n"
    )


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml() -> Response:
    from xml.sax.saxutils import escape as xml_escape

    from routers.spa import _get_seo_meta  # lazy import to avoid circular at module load

    base = _CANONICAL_BASE
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    meta_paths = [p for p, m in _get_seo_meta().items() if not m.get("noindex")]
    extra_static = ["/contact", "/privacy", "/terms", "/refund-policy"]
    ordered = list(dict.fromkeys(["/"] + sorted(p for p in meta_paths if p != "/") + extra_static))

    def _priority_cf(path: str) -> tuple[str, str]:
        segments = [s for s in path.strip("/").split("/") if s]
        n = len(segments)
        if path == "/":
            return ("1.0", "daily")
        if path in extra_static:
            return ("0.3", "monthly")
        if path == "/learn" or (n == 2 and segments[0] in ("practice", "learn")):
            return ("0.8", "weekly")
        if n == 3 and segments[0] == "learn":
            return ("0.7", "weekly")
        if segments[0] == "sample" or path == "/faq":
            return ("0.6", "weekly")
        if n == 4 and segments[0] == "practice" and segments[2] == "questions":
            return ("0.5", "weekly")
        return ("0.5", "weekly")

    def url_entry(path: str) -> str:
        pri, cf = _priority_cf(path)
        loc = xml_escape(f"{base}{path}")
        return (
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{cf}</changefreq>\n"
            f"    <priority>{pri}</priority>\n"
            f"  </url>"
        )

    entries = "\n".join(url_entry(p) for p in ordered)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>"
    )

    return Response(content=xml, media_type="application/xml")
