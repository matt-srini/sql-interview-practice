"""SEO assertions — title rewrite, JSON-LD, robots.txt, sitemap.xml, canonical, role pages."""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
for path in (REPO_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TESTING", "1")

from starlette.testclient import TestClient
import backend.main as main
from routers import spa  # the SPA router module main.app actually uses (sys.modules["routers.spa"])

app = main.app


@pytest.fixture(scope="module", autouse=True)
def _frontend_index():
    """The backend-tests CI job runs pytest without building the frontend, so
    frontend/dist/index.html is absent and the SPA would 404 every HTML route
    (the cause of the long-standing CI red on these 3 SEO tests). Point the SPA
    at a temp dir holding the real *source* frontend/index.html — the authored
    static SEO layer that _inject_seo rewrites — so these tests validate
    _inject_seo without depending on a Vite build. Build output and source carry
    identical SEO tags; the build only adds asset/script tags _inject_seo ignores."""
    source_index = Path(REPO_ROOT) / "frontend" / "index.html"
    tmp = Path(tempfile.mkdtemp(prefix="seo-dist-"))
    shutil.copy(source_index, tmp / "index.html")
    orig_dir, orig_cache = spa.FRONTEND_DIST_DIR, spa._INDEX_HTML_CACHE
    spa.FRONTEND_DIST_DIR = tmp
    spa._INDEX_HTML_CACHE = None
    try:
        yield
    finally:
        spa.FRONTEND_DIST_DIR = orig_dir
        spa._INDEX_HTML_CACHE = orig_cache
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def client(_frontend_index):
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_homepage_title_and_jsonld(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "<title>Data Engineer, Analyst &amp; Scientist Interview Prep | datathink</title>" in body
    assert "application/ld+json" in body
    assert '"Organization"' in body
    # Organization sameAs lists the verified first-party profiles (entity disambiguation)
    assert '"sameAs"' in body
    assert "https://www.linkedin.com/company/datathink-co" in body
    assert "https://x.com/datathinkHQ" in body
    assert "https://www.youtube.com/@datathinkHQ" in body
    assert "https://www.instagram.com/datathinkhq" in body


def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct
    body = resp.text
    assert "Sitemap:" in body
    assert "Disallow: /dashboard" in body


def test_sitemap_xml_includes_and_excludes(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    body = resp.text
    # Must include homepage and a practice page
    assert "<loc>https://datathink.co/</loc>" in body
    assert "<loc>https://datathink.co/practice/sql</loc>" in body
    # Must include all 10 tracks — previously-missing pages
    assert "/practice/statistics" in body
    assert "/practice/data-engineering" in body
    assert "/sample/statistics/medium" in body
    # Must NOT include noindex paths
    assert "/dashboard" not in body
    assert "/auth" not in body


def test_single_self_canonical_per_page(client):
    # Regression: spa.py must REWRITE the static index.html canonical in place,
    # not append a second one. Two conflicting rel=canonical (homepage + self)
    # would risk Google canonicalizing every non-home page to "/".
    for path in ["/", "/practice/sql", "/interview-prep/data-engineer"]:
        body = client.get(path).text
        canonicals = re.findall(r'<link rel="canonical" href="([^"]*)"', body)
        assert canonicals == [f"https://datathink.co{path}"], (path, canonicals)


def test_role_interview_prep_page(client):
    resp = client.get("/interview-prep/data-engineer")
    assert resp.status_code == 200
    body = resp.text
    assert "<title>Data Engineer Interview Prep: SQL, Python, Spark &amp; Pipelines | datathink</title>" in body
    assert "interview-prep/data-engineer" in client.get("/sitemap.xml").text
