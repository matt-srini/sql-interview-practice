"""Tests for the /guides server-rendered surface."""
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

import main as _main_module
from main import app
from config import CANONICAL_BASE_URL

# ---------------------------------------------------------------------------
# Draft fixture: create a temp draft guide file for draft-exclusion tests
# ---------------------------------------------------------------------------

DRAFT_SLUG = "_test_draft_guide"
DRAFT_PATH = Path(__file__).parent.parent / "content" / "guides" / f"{DRAFT_SLUG}.md"
DRAFT_CONTENT = textwrap.dedent(f"""\
    ---
    title: "Draft Guide for Testing"
    description: "This is a draft and should not be publicly visible."
    slug: "{DRAFT_SLUG}"
    date: 2026-06-29
    draft: true
    ---

    This guide is a draft and must not appear in the index or sitemap.
""")


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    # Guides router is filesystem-only — no DB or frontend build needed.
    monkeypatch_module.setattr(_main_module, "ensure_schema", AsyncMock(return_value=None))
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest's built-in is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Reset the in-memory per-IP rate limiter before each test.

    These tests use a custom DB-free client (above) that does NOT opt into
    conftest's `isolated_state`, which is what normally clears the limiter. The
    limiter is active for non-localhost test clients (TestClient IP is
    'testclient'), so without this reset the cumulative request count across the
    full suite trips a 429 on the later guides requests -- green in isolation,
    red in CI (the exact failure caught on the first branch CI run).
    """
    from main import _clear_rate_limit_state
    _clear_rate_limit_state()
    yield


@pytest.fixture(autouse=False)
def draft_guide_file():
    DRAFT_PATH.write_text(DRAFT_CONTENT, encoding="utf-8")
    yield
    if DRAFT_PATH.exists():
        DRAFT_PATH.unlink()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_guides_index_200(client):
    r = client.get("/guides")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_guides_index_contains_starter_guide(client):
    r = client.get("/guides")
    assert "Reasoning vs Recall" in r.text
    assert 'href="/guides/reasoning-vs-recall-data-interviews"' in r.text


def test_guide_page_200(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_guide_page_h1_title(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    assert "Reasoning vs Recall" in r.text


def test_guide_page_exact_sentence(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    assert "Recognition is not reasoning." in r.text


def test_guide_page_title_tag(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    expected = "<title>Reasoning vs Recall: How to Actually Prepare for Data Interviews | datathink</title>"
    assert expected in r.text


def test_guide_page_canonical(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    expected_canonical = f"{CANONICAL_BASE_URL}/guides/reasoning-vs-recall-data-interviews"
    assert expected_canonical in r.text


def test_guide_page_json_ld_article(client):
    r = client.get("/guides/reasoning-vs-recall-data-interviews")
    assert "application/ld+json" in r.text
    assert '"Article"' in r.text


def test_guide_page_not_found(client):
    r = client.get("/guides/does-not-exist")
    assert r.status_code == 404


def test_sitemap_contains_guide(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "/guides/reasoning-vs-recall-data-interviews" in r.text


def test_no_em_dash_in_starter_guide_title():
    path = Path(__file__).parent.parent / "content" / "guides" / "reasoning-vs-recall-data-interviews.md"
    import frontmatter
    post = frontmatter.load(str(path))
    assert "—" not in post.metadata.get("title", ""), "em-dash found in title"
    assert "—" not in post.metadata.get("description", ""), "em-dash found in description"


def test_draft_guide_returns_404(client, draft_guide_file):
    r = client.get(f"/guides/{DRAFT_SLUG}")
    assert r.status_code == 404


def test_draft_guide_absent_from_index(client, draft_guide_file):
    r = client.get("/guides")
    assert DRAFT_SLUG not in r.text


def test_draft_guide_absent_from_sitemap(client, draft_guide_file):
    r = client.get("/sitemap.xml")
    assert DRAFT_SLUG not in r.text
