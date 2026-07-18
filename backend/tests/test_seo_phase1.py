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


def test_homepage_og_description_carries_brand_pitch(client):
    """The social card (og/twitter description) carries the M4 brand pitch, while
    the SEO meta description stays the length/keyword-tuned SERP snippet. The two
    are intentionally decoupled — see spa.py og_description."""
    body = client.get("/").text
    pitch = "Interview success follows real mastery. It&#x27;s the consequence, not the goal."
    # og + twitter descriptions carry the pitch
    assert re.search(r'<meta property="og:description" content="[^"]*' + re.escape(pitch), body)
    assert re.search(r'<meta name="twitter:description" content="[^"]*' + re.escape(pitch), body)
    # the SEO meta description stays the keyword snippet, NOT the pitch
    seo_desc = re.search(r'<meta name="description" content="([^"]*)"', body).group(1)
    assert "questions with instant feedback" in seo_desc
    assert "Interview success follows real mastery" not in seo_desc


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


def test_pricing_page_indexed(client):
    resp = client.get("/pricing")
    assert resp.status_code == 200
    body = resp.text
    assert "<title>Plans &amp; Feature Comparison | datathink</title>" in body
    # frontend/index.html's canonical <link> is self-closed with " />" (not bare
    # ">") — _inject_seo rewrites only the href value in place, so that closing
    # syntax carries through unchanged.
    assert '<link rel="canonical" href="https://datathink.co/pricing" />' in body
    assert "/pricing" in client.get("/sitemap.xml").text


def test_unmapped_question_path_is_noindexed(client):
    # Medium/hard question pages aren't in the SEO meta map (only easy questions
    # are) but are real, linkable SPA routes — must be noindexed, not silently
    # served with homepage meta/canonical.
    resp = client.get("/practice/sql/questions/some-medium-question-id")
    assert resp.status_code == 200
    assert '<meta name="robots" content="noindex, nofollow" />' in resp.text

    # Entire MCQ-only tracks have no per-question meta at all (any difficulty).
    resp = client.get("/practice/statistics/questions/any-id")
    assert resp.status_code == 200
    assert '<meta name="robots" content="noindex, nofollow" />' in resp.text


def test_legacy_path_redirects(client):
    cases = [
        ("/questions/abc123", "/practice/sql/questions/abc123"),
        ("/practice/questions/abc123", "/practice/sql/questions/abc123"),
        ("/practice/python-data", "/practice/pandas"),
        ("/practice/python-data/questions/xyz", "/practice/pandas/questions/xyz"),
        ("/learn/python-data", "/learn/pandas"),
        ("/learn/python-data/some-path-slug", "/learn/pandas/some-path-slug"),
        ("/sample/python-data/easy", "/sample/pandas/easy"),
        ("/sample/easy", "/sample/sql/easy"),
        ("/sample/pandas", "/sample/pandas/easy"),
        ("/sample/not-a-real-thing", "/sample"),
    ]
    for src, expected_location in cases:
        resp = client.get(src, follow_redirects=False)
        assert resp.status_code == 301, (src, resp.status_code)
        assert resp.headers["location"] == expected_location, (src, resp.headers["location"])
