import json
import re
from html import escape as html_escape

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse

from config import CANONICAL_BASE_URL, FRONTEND_BASE_URL, FRONTEND_DIST_DIR, VITE_BACKEND_URL, VITE_POSTHOG_HOST, VITE_POSTHOG_KEY, VITE_SENTRY_DSN

router = APIRouter()

BASE_URL = CANONICAL_BASE_URL

_TRACK_LABELS = {
    "sql": "SQL", "python": "Python", "pandas": "Pandas", "pyspark": "PySpark",
    "data-engineering": "Data Engineering", "data-modeling": "Data Modeling",
    "statistics": "Statistics", "ml-fundamentals": "ML Fundamentals", "experimentation": "Experimentation",
}

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


def _get_track_counts() -> dict:
    """Returns {slug: total_practice_count} computed from loaded catalogs."""
    import importlib
    _CFG = [
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
    counts: dict = {}
    for slug, mod_name, fn_name in _CFG:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name)
            if fn_name == "get_questions_by_difficulty":
                grouped = fn()
                counts[slug] = sum(
                    len([q for q in qs if not q.get("mock_only")])
                    for qs in grouped.values()
                )
            else:
                counts[slug] = len([q for q in fn() if not q.get("mock_only")])
        except Exception:
            counts[slug] = 0
    return counts


def _build_seo_meta() -> dict:
    tc = _get_track_counts()
    total = sum(tc.values())

    _PRACTICE_DESC = {
        "sql":              f"Your SQL practice workspace. {tc.get('sql', 0)} questions by difficulty: joins, aggregations, window functions, and CTEs with instant DuckDB execution and solution analysis.",
        "python":           f"Your Python practice workspace. {tc.get('python', 0)} algorithm and data processing questions with automated test case feedback and step-by-step hints.",
        "pandas":           f"Your Pandas practice workspace. {tc.get('pandas', 0)} DataFrame manipulation questions with live execution and side-by-side output comparison.",
        "pyspark":          f"Your PySpark practice workspace. {tc.get('pyspark', 0)} MCQ, predict-output, debug, and scenario questions covering core Spark concepts and performance.",
        "data-engineering": f"Your Data Engineering practice workspace. {tc.get('data-engineering', 0)} MCQ, scenario, and debug questions covering ETL, orchestration, and system design.",
        "data-modeling":    f"Your Data Modeling practice workspace. {tc.get('data-modeling', 0)} MCQ and scenario questions covering dimensional modeling, normalization, and dbt design.",
        "statistics":       f"Your Statistics practice workspace. {tc.get('statistics', 0)} conceptual and numerical questions covering probability, inference, and A/B testing.",
        "ml-fundamentals":  f"Your ML Fundamentals practice workspace. {tc.get('ml-fundamentals', 0)} MCQ and scenario questions covering bias-variance, evaluation, and production ML.",
        "experimentation":  f"Your Experimentation practice workspace. {tc.get('experimentation', 0)} MCQ and scenario questions covering A/B testing, power analysis, and causal inference.",
    }

    meta: dict = {
        "/": {
            "title": "Data Engineer, Analyst & Scientist Interview Prep | datathink",
            "description": f"Premium data interview practice on real execution engines: SQL, Python, ML, statistics and more. {total}+ questions with instant feedback and curated learning paths.",
        },
        "/learn": {
            "title": "Data Interview Learning Paths | datathink",
            "description": "Curated learning paths across SQL, Python, Pandas, PySpark, Statistics, ML, and Experimentation to build interview-ready skills step by step.",
        },
        "/learn/sql": {
            "title": "SQL Learning Paths | datathink",
            "description": "Curated SQL learning paths covering window functions, aggregation, cohort analysis, and more.",
        },
        "/learn/python": {
            "title": "Python Learning Paths | datathink",
            "description": "Curated Python learning paths covering algorithms, data structures, and data processing patterns.",
        },
        "/learn/pandas": {
            "title": "Pandas Learning Paths | datathink",
            "description": "Curated Pandas learning paths covering DataFrame manipulation, groupby, reshaping, and time series.",
        },
        "/learn/pyspark": {
            "title": "PySpark Learning Paths | datathink",
            "description": "Curated PySpark learning paths covering Spark core concepts, performance, streaming, and Delta Lake.",
        },
    }
    for slug, desc in _PRACTICE_DESC.items():
        track_label = _TRACK_LABELS.get(slug, slug.replace("-", " ").title())
        meta[f"/practice/{slug}"] = {
            "title": f"{track_label} Interview Questions | datathink",
            "description": desc,
        }

    # Sample pages: 9 tracks × 3 difficulties
    for topic, label in _TRACK_LABELS.items():
        for diff, diff_label in [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]:
            meta[f"/sample/{topic}/{diff}"] = {
                "title": f"Free {label} Interview Questions ({diff_label}) | datathink",
                "description": (
                    f"Try free {diff_label.lower()} {label} interview questions, no account required. "
                    "Real execution environment with instant feedback."
                ),
            }

    meta["/faq"] = {
        "title": "Frequently Asked Questions | datathink",
        "description": "Common questions about datathink: free access, no-account practice, SQL and Python topics, company coverage, question unlocks, mock interviews, and plan differences.",
    }

    meta["/interview-prep"] = {
        "title": "Data Interview Prep by Role: Analyst, Engineer & Scientist | datathink",
        "description": "Role-specific data interview prep. Pick your path: Data Analyst, Data Engineer, Analytics Engineer, or Data Scientist, each with the tracks, mock interviews, and reasoning that role demands.",
    }

    meta["/interview-prep/data-engineer"] = {
        "title": "Data Engineer Interview Prep: SQL, Python, Spark & Pipelines | datathink",
        "description": "Data engineer interview prep on real execution engines: SQL, Python, PySpark and data pipeline design, plus mock interviews and reasoning-first questions.",
    }

    meta["/interview-prep/data-analyst"] = {
        "title": "Data Analyst Interview Prep: SQL, Statistics & Python | datathink",
        "description": "Data analyst interview prep on real engines: SQL depth, statistical reasoning, Pandas and Python for data, plus mock interviews and reasoning-first questions.",
    }

    meta["/interview-prep/analytics-engineer"] = {
        "title": "Analytics Engineer Interview Prep: SQL, dbt & Data Modeling | datathink",
        "description": "Analytics engineer interview prep on real engines: SQL precision, dimensional data modeling, dbt patterns, Pandas and Python, plus mock interviews and reasoning-first questions.",
    }

    meta["/interview-prep/data-scientist"] = {
        "title": "Data Scientist Interview Prep: ML, Statistics & Experimentation | datathink",
        "description": "Data scientist interview prep on real engines: ML fundamentals, statistical inference, experimentation, plus Python and SQL, with mock interviews and reasoning-first questions.",
    }

    # Pages crawlers should not index
    for path in ["/auth", "/dashboard", "/mock"]:
        meta[path] = {"noindex": True}

    # Dynamic: per-path SEO pages (filesystem reads)
    try:
        from path_loader import get_all_paths
        for p in get_all_paths():
            slug = p.get("slug", "")
            topic = p.get("topic", "sql")
            raw_desc = f"{p.get('description', '')} {p.get('outcomes', '')}".strip()
            desc = raw_desc[:152] + "..." if len(raw_desc) > 155 else raw_desc
            meta[f"/learn/{topic}/{slug}"] = {
                "title": f"{p['title']} | datathink",
                "description": desc,
            }
    except Exception:
        pass  # graceful degradation if paths can't be loaded

    # Easy question pages — all 4 tracks
    _EASY_TRACK_CFG = [
        ("sql",         "SQL",     "questions",             "get_questions_by_difficulty"),
        ("python",      "Python",  "python_questions",      "get_all_questions"),
        ("pandas",      "Pandas",  "pandas_questions",      "get_all_questions"),
        ("pyspark",     "PySpark", "pyspark_questions",     "get_all_questions"),
    ]
    try:
        import importlib
        for url_topic, label, module_name, fn_name in _EASY_TRACK_CFG:
            mod = importlib.import_module(module_name)
            fn = getattr(mod, fn_name)
            if fn_name == "get_questions_by_difficulty":
                questions = fn().get("easy", [])
            else:
                questions = [q for q in fn() if q.get("difficulty") == "easy" and not q.get("mock_only")]
            for q in questions:
                concepts_preview = ", ".join(q.get("concepts", [])[:3])
                raw_desc = q.get("description", "")
                desc = (raw_desc[:120].rstrip() + "...") if len(raw_desc) > 120 else raw_desc
                full_desc = f"Practice: {desc}"
                if concepts_preview:
                    full_desc += f" Covers {concepts_preview}."
                meta[f"/practice/{url_topic}/questions/{q['id']}"] = {
                    "title": f"{q['title']} | {label} Interview Question | datathink",
                    "description": full_desc,
                }
    except Exception:
        pass

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
    og_image = f"{BASE_URL}/og-image.png?v=4"

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
    # Rewrite the canonical href IN PLACE. index.html ships a static homepage
    # canonical; appending a second one (the old behaviour) left two conflicting
    # rel=canonical on every non-home page, risking Google canonicalizing them
    # all to "/". Rewrite (not append) so each page has exactly one.
    html = re.sub(
        r'(<link\s+rel="canonical"\s+href=")[^"]*(")',
        rf"\g<1>{canonical}\2",
        html,
        count=1,
    )

    # og:image / twitter:image are not per-route; index.html already ships them
    # with this same value, so injecting is value-identical (harmless).
    inject = (
        f'<meta property="og:image" content="{og_image}" />'
        f'<meta name="twitter:image" content="{og_image}" />'
    )

    # Homepage-only: inject Organization + WebSite JSON-LD
    if url_path == "/":
        ld = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": f"{BASE_URL}/#organization",
                    "name": "datathink",
                    "url": f"{BASE_URL}/",
                    "logo": f"{BASE_URL}/icon-512.png",
                    "description": "Premium data interview practice platform for data engineers, analysts, analytics engineers and data scientists.",
                    "sameAs": [
                        "https://www.linkedin.com/company/datathink-co",
                        "https://x.com/datathinkHQ",
                    ],
                },
                {
                    "@type": "WebSite",
                    "@id": f"{BASE_URL}/#website",
                    "name": "datathink",
                    "url": f"{BASE_URL}/",
                    "publisher": {"@id": f"{BASE_URL}/#organization"},
                },
            ],
        }
        ld_script = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>'
        inject = inject + ld_script

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
