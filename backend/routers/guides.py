"""Server-rendered /guides surface — fully crawlable HTML, separate from the React SPA."""
import json
from datetime import date, datetime
from pathlib import Path

import frontmatter
import markdown
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import CANONICAL_BASE_URL

router = APIRouter()

_GUIDES_DIR = Path(__file__).parent.parent / "content" / "guides"
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_MD = markdown.Markdown(
    extensions=["fenced_code", "tables", "toc", "sane_lists"],
    output_format="html",
)

_OG_IMAGE = f"{CANONICAL_BASE_URL}/og-image.png?v=4"
_ORG_ID = f"{CANONICAL_BASE_URL}/#organization"


def _date_str(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.isoformat()[:10]
    return str(d)


def _load_guide(path: Path) -> dict | None:
    post = frontmatter.load(str(path))
    meta = post.metadata
    if not meta.get("slug"):
        return None
    _MD.reset()
    body_html = _MD.convert(post.content)
    pub = _date_str(meta.get("date", ""))
    upd = _date_str(meta.get("updated", meta.get("date", "")))
    return {
        "title": meta.get("title", ""),
        "description": meta.get("description", ""),
        "slug": meta.get("slug", ""),
        "date": pub,
        "updated": upd,
        "draft": bool(meta.get("draft", False)),
        "body_html": body_html,
    }


def _all_guides(include_drafts: bool = False) -> list[dict]:
    guides = []
    for path in sorted(_GUIDES_DIR.glob("*.md")):
        g = _load_guide(path)
        if g is None:
            continue
        if g["draft"] and not include_drafts:
            continue
        guides.append(g)
    guides.sort(key=lambda g: g["date"], reverse=True)
    return guides


def _article_ld(guide: dict) -> str:
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": guide["title"],
                "description": guide["description"],
                "datePublished": guide["date"],
                "dateModified": guide["updated"],
                "url": f"{CANONICAL_BASE_URL}/guides/{guide['slug']}",
                "author": {
                    "@type": "Organization",
                    "@id": _ORG_ID,
                    "name": "datathink",
                },
                "publisher": {
                    "@type": "Organization",
                    "@id": _ORG_ID,
                    "name": "datathink",
                },
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": CANONICAL_BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": "Guides", "item": f"{CANONICAL_BASE_URL}/guides"},
                    {"@type": "ListItem", "position": 3, "name": guide["title"], "item": f"{CANONICAL_BASE_URL}/guides/{guide['slug']}"},
                ],
            },
        ],
    }
    return json.dumps(ld, ensure_ascii=False)


def _index_ld(guides: list[dict]) -> str:
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": CANONICAL_BASE_URL},
                    {"@type": "ListItem", "position": 2, "name": "Guides", "item": f"{CANONICAL_BASE_URL}/guides"},
                ],
            },
            {
                "@type": "ItemList",
                "name": "datathink Guides",
                "url": f"{CANONICAL_BASE_URL}/guides",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i + 1,
                        "name": g["title"],
                        "url": f"{CANONICAL_BASE_URL}/guides/{g['slug']}",
                    }
                    for i, g in enumerate(guides)
                ],
            },
        ],
    }
    return json.dumps(ld, ensure_ascii=False)


@router.get("/guides", response_class=HTMLResponse, include_in_schema=False)
async def guides_index(request: Request) -> HTMLResponse:
    guides = _all_guides()
    page_title = "Guides | datathink"
    page_description = "Long-form articles on data interview preparation, reasoning depth, and professional data practice."
    canonical_url = f"{CANONICAL_BASE_URL}/guides"
    return _templates.TemplateResponse(
        request,
        "guides_index.html",
        {
            "page_title": page_title,
            "page_description": page_description,
            "canonical_url": canonical_url,
            "og_type": "website",
            "og_image": _OG_IMAGE,
            "guides": guides,
            "index_ld": _index_ld(guides),
        },
    )


@router.get("/guides/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def guide_page(slug: str, request: Request) -> HTMLResponse:
    path = _GUIDES_DIR / f"{slug}.md"
    if not path.exists():
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)
    guide = _load_guide(path)
    if guide is None or guide["draft"]:
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)
    page_title = f"{guide['title']} | datathink"
    canonical_url = f"{CANONICAL_BASE_URL}/guides/{slug}"
    return _templates.TemplateResponse(
        request,
        "guide.html",
        {
            "page_title": page_title,
            "page_description": guide["description"],
            "canonical_url": canonical_url,
            "og_type": "article",
            "og_image": _OG_IMAGE,
            "guide": guide,
            "body_html": guide["body_html"],
            "article_ld": _article_ld(guide),
        },
    )


def get_all_guide_slugs() -> list[dict]:
    """Return list of {slug, updated} for all non-draft guides — used by sitemap."""
    return [{"slug": g["slug"], "updated": g["updated"]} for g in _all_guides()]
