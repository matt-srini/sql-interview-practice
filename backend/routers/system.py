from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from config import (
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
from path_loader import get_all_paths

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
        ("/faq", "0.5", "monthly"),
        ("/contact", "0.4", "monthly"),
        ("/privacy", "0.3", "monthly"),
        ("/terms", "0.3", "monthly"),
        ("/refund-policy", "0.3", "monthly"),
        ("/learn/sql", "0.8", "weekly"),
        ("/learn/python", "0.8", "weekly"),
        ("/learn/pandas", "0.8", "weekly"),
        ("/learn/pyspark", "0.8", "weekly"),
        ("/practice/sql", "0.7", "weekly"),
        ("/practice/python", "0.7", "weekly"),
        ("/practice/pandas", "0.7", "weekly"),
        ("/practice/pyspark", "0.7", "weekly"),
        ("/sample/sql/easy", "0.7", "weekly"),
        ("/sample/sql/medium", "0.7", "weekly"),
        ("/sample/sql/hard", "0.7", "weekly"),
        ("/sample/python/easy", "0.7", "weekly"),
        ("/sample/python/medium", "0.7", "weekly"),
        ("/sample/python/hard", "0.7", "weekly"),
        ("/sample/pandas/easy", "0.7", "weekly"),
        ("/sample/pandas/medium", "0.7", "weekly"),
        ("/sample/pandas/hard", "0.7", "weekly"),
        ("/sample/pyspark/easy", "0.7", "weekly"),
        ("/sample/pyspark/medium", "0.7", "weekly"),
        ("/sample/pyspark/hard", "0.7", "weekly"),
    ]

    # Learning path URLs
    try:
        paths = get_all_paths()
        path_urls = [
            (f"/learn/{p['topic']}/{p['slug']}", "0.8", "weekly")
            for p in paths
            if "topic" in p and "slug" in p
        ]
    except Exception:
        path_urls = []

    # Easy question URLs — all 4 tracks
    _EASY_Q_CFG = [
        ("sql",         "/practice/sql/questions/",         "questions",             "get_questions_by_difficulty"),
        ("python",      "/practice/python/questions/",      "python_questions",      "get_all_questions"),
        ("pandas", "/practice/pandas/questions/", "pandas_questions", "get_all_questions"),
        ("pyspark",     "/practice/pyspark/questions/",     "pyspark_questions",     "get_all_questions"),
    ]
    easy_question_urls = []
    try:
        import importlib
        for _topic, _prefix, _module, _fn in _EASY_Q_CFG:
            mod = importlib.import_module(_module)
            fn = getattr(mod, _fn)
            if _fn == "get_questions_by_difficulty":
                qs = fn().get("easy", [])
            else:
                qs = [q for q in fn() if q.get("difficulty") == "easy" and not q.get("mock_only")]
            easy_question_urls += [(f"{_prefix}{q['id']}", "0.6", "monthly") for q in qs]
    except Exception:
        pass

    all_urls = static_urls + path_urls + easy_question_urls

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
