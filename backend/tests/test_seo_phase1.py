"""SEO assertions — title rewrite, JSON-LD, robots.txt, sitemap.xml, canonical, role pages."""
import os
import re
import sys

import pytest

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
for path in (REPO_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TESTING", "1")

from starlette.testclient import TestClient
import backend.main as main

app = main.app


@pytest.fixture(scope="module")
def client():
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
    # Must include all 9 tracks — previously-missing pages
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
