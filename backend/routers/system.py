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
    """Per-track practice question counts — no auth required.

    Derived from the ``TRACKS`` registry (the single source of truth for the track
    list), so a new track appears here automatically with no per-endpoint edit.
    """
    from tracks import TRACKS

    result = {}
    for t in TRACKS:
        grouped = t.catalog_module.get_questions_by_difficulty()
        per_diff = {
            diff: len([q for q in grouped.get(diff, []) if not q.get("mock_only")])
            for diff in ("easy", "medium", "hard")
        }
        per_diff["total"] = per_diff["easy"] + per_diff["medium"] + per_diff["hard"]
        result[t.slug] = per_diff

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

    from routers.guides import get_all_guide_slugs  # lazy import to avoid circular at module load
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
        if segments[0] == "sample" or path in ("/faq", "/pricing"):
            return ("0.6", "weekly")
        if n == 4 and segments[0] == "practice" and segments[2] == "questions":
            return ("0.5", "weekly")
        if segments[0] == "guides":
            return ("0.7", "weekly")
        return ("0.5", "weekly")

    def url_entry(path: str, lastmod: str = today) -> str:
        pri, cf = _priority_cf(path)
        loc = xml_escape(f"{base}{path}")
        return (
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{cf}</changefreq>\n"
            f"    <priority>{pri}</priority>\n"
            f"  </url>"
        )

    # Guides: /guides index + each non-draft guide page with its own lastmod
    guide_entries_str = url_entry("/guides")
    for g in get_all_guide_slugs():
        guide_entries_str += "\n" + url_entry(f"/guides/{g['slug']}", lastmod=g["updated"])

    entries = "\n".join(url_entry(p) for p in ordered) + "\n" + guide_entries_str
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>"
    )

    return Response(content=xml, media_type="application/xml")
