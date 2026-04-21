from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from config import FRONTEND_BASE_URL
from database import get_loaded_tables
from db import ping
from path_loader import get_all_paths

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, Any]:
    postgres_ok = await ping()
    tables_loaded = get_loaded_tables()
    if not postgres_ok or not tables_loaded:
        return {
            "status": "unhealthy",
            "postgres": postgres_ok,
            "tables_loaded": tables_loaded,
        }
    return {
        "status": "healthy",
        "postgres": True,
        "tables_loaded": tables_loaded,
    }


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt() -> str:
    base = FRONTEND_BASE_URL.rstrip("/")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /dashboard\n"
        "Disallow: /mock\n"
        "Disallow: /auth\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml() -> Response:
    base = FRONTEND_BASE_URL.rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Static public URLs
    static_urls = [
        ("", "1.0", "daily"),       # landing
        ("/learn", "0.9", "weekly"),
        ("/learn/sql", "0.8", "weekly"),
        ("/learn/python", "0.8", "weekly"),
        ("/learn/python-data", "0.8", "weekly"),
        ("/learn/pyspark", "0.8", "weekly"),
        ("/practice/sql", "0.8", "weekly"),
        ("/practice/python", "0.8", "weekly"),
        ("/practice/python-data", "0.8", "weekly"),
        ("/practice/pyspark", "0.8", "weekly"),
        ("/sample/sql/easy", "0.7", "weekly"),
        ("/sample/sql/medium", "0.7", "weekly"),
        ("/sample/sql/hard", "0.7", "weekly"),
        ("/sample/python/easy", "0.7", "weekly"),
        ("/sample/python/medium", "0.7", "weekly"),
        ("/sample/python/hard", "0.7", "weekly"),
        ("/sample/python-data/easy", "0.7", "weekly"),
        ("/sample/python-data/medium", "0.7", "weekly"),
        ("/sample/python-data/hard", "0.7", "weekly"),
        ("/sample/pyspark/easy", "0.7", "weekly"),
        ("/sample/pyspark/medium", "0.7", "weekly"),
        ("/sample/pyspark/hard", "0.7", "weekly"),
    ]

    # Learning path URLs
    try:
        paths = get_all_paths()
        path_urls = [
            (f"/learn/{p['topic']}/{p['slug']}", "0.7", "monthly")
            for p in paths
            if "topic" in p and "slug" in p
        ]
    except Exception:
        path_urls = []

    all_urls = static_urls + path_urls

    def url_entry(loc: str, priority: str, changefreq: str) -> str:
        return (
            f"  <url>\n"
            f"    <loc>{base}{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    entries = "\n".join(url_entry(loc, pri, freq) for loc, pri, freq in all_urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>"
    )

    return Response(content=xml, media_type="application/xml")
