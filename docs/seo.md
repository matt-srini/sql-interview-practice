# SEO

Canonical source of truth for **how datathink's SEO is wired**. The runtime SoT for the actual per-route meta *values* is code — `backend/routers/spa.py` (`_build_seo_meta` + `_inject_seo`); this doc describes the architecture, conventions, and roadmap around it. Keep both in sync (parity guard: `backend/tests/test_seo_phase1.py`).

SoT siblings: [`backend.md`](backend.md) §System / §SPA-static (the endpoints), [`frontend.md`](frontend.md) (Helmet usage per page), [`deployment.md`](deployment.md) (`CANONICAL_BASE_URL` env). Decisions: [`decisions/DECISIONS.md`](decisions/DECISIONS.md) 2026-06-25 SEO Phase 1.

---

## The three meta layers

This is a React SPA. Crawlers and social unfurlers (LinkedIn, Slack, X, Facebook) often do **not** execute JS, so per-route `<meta>` must be present in the **server-rendered HTML**, not only set client-side. We have three layers, in precedence order:

1. **`backend/routers/spa.py` — `_inject_seo()` — the crawler-visible per-route SoT.** For every known route the FastAPI SPA handler server-rewrites `<title>`, `meta description`, `og:title/description/url`, and the `canonical` href (rewritten **in place** so every page has exactly one self-referencing canonical — `index.html` ships a static homepage canonical that would otherwise conflict; regression-guarded in `test_seo_phase1.py`), and injects `og:image` + `twitter:image` (+ JSON-LD on the homepage) **before sending the HTML**. This is what Google and unfurlers see with zero JS. The route→meta map is `_build_seo_meta()`. **When the SERP title/description matters, this is the file that controls it.**
2. **`frontend/index.html` — the static default.** Ships in the build as the fallback `<title>`/meta for any route `_inject_seo` does *not* map (it returns the HTML unchanged for unmapped routes — those are **not** auto-`noindex`'d). Keep its homepage values in sync with the spa.py `/` entry.
3. **React Helmet (per page, `frontend/src/pages/*`) — client-nav meta.** Updates the tab title/meta on in-app SPA navigations (after JS loads). For shared routes (especially `/`) it must **mirror** layer 1, or the title flashes/drifts on client load.

> **Drift hazard.** The homepage title/description lives in all three layers. They are kept identical by hand; spa.py is the declared SoT, the other two are renders of it. Change one → change all three in the same commit. This is the exact multi-source failure mode `CLAUDE.md` §Linked-docs warns about.

## Canonical base URL — single SoT

`backend/config.py` → `CANONICAL_BASE_URL = _getenv("CANONICAL_BASE_URL", "https://datathink.co")`. The literal domain appears **once**. Both `spa.py` (canonical link, `og:url`, `og:image`, JSON-LD `@id`/`url`/`logo`) and `system.py` (robots `Sitemap:` line, every sitemap `<loc>`) import it. Override per-environment with the `CANONICAL_BASE_URL` env var.

## Title & description conventions

- Separator is a **pipe** ` | `, brand **last**: `<Page descriptor> | datathink`. The brand is contested (see §Brand disambiguation), so titles front-load intent keywords rather than the brand.
- **No em-dashes (—)** in any SEO string (title, description, JSON-LD). Use colon / comma / period / pipe.
- Aim ≤ 60 chars for titles (SERP truncation), ≤ ~160 for descriptions.
- High-intent phrasing: track practice pages target the literal query "**`<Track>` Interview Questions**"; the homepage targets role intent.

| Route | Title |
|---|---|
| `/` | `Data Engineer, Analyst & Scientist Interview Prep \| datathink` |
| `/practice/<track>` | `<Track> Interview Questions \| datathink` |
| `/learn` · `/learn/<track>` | `Data Interview Learning Paths \| datathink` · `<Track> Learning Paths \| datathink` |
| `/sample/<track>/<diff>` | `Free <Track> Interview Questions (<Diff>) \| datathink` |
| `/faq` | `Frequently Asked Questions \| datathink` |

Homepage description (premium positioning lives here, not in the title): *"Premium data interview practice on real execution engines: SQL, Python, ML, statistics and more. {N}+ questions with instant feedback and curated learning paths."* (`{N}` is the live non-mock question total in spa.py; the static layers use a safe `870+`.)

## /guides — server-rendered content surface (`backend/routers/guides.py`)

Unlike every other URL on datathink, `/guides` and `/guides/{slug}` are **fully server-rendered HTML** — real `<h1>/<p>` in the response body, zero JS required. The React SPA is **not** involved; the guides router sits in `backend/routers/guides.py` and is registered in `main.py` **before** the SPA catch-all so the routes are never swallowed by it.

- **Content store:** `backend/content/guides/*.md` — Markdown files with YAML frontmatter (`title`, `description`, `slug`, `date`, `updated`, `draft`). `draft: true` files return 404 and are excluded from the index and sitemap.
- **Rendering:** `python-frontmatter` parses frontmatter; `markdown` (extensions: `fenced_code`, `tables`, `toc`, `sane_lists`) renders the body. Templates: `backend/templates/guide.html` and `backend/templates/guides_index.html` (share `base.html`). Rendered via Jinja2 (`fastapi.templating.Jinja2Templates`).
- **Per-page `<head>`:** Each guide page owns its own `<title>`, meta description, canonical link, OG tags, and JSON-LD — **`_build_seo_meta` in `routers/spa.py` does NOT cover `/guides/*`**. The guides router generates all SEO metadata itself.
- **Structured data:**
  - Guide pages: `Article` (headline, datePublished, dateModified, author/publisher = datathink Organization) + `BreadcrumbList` (Home › Guides › title).
  - Index page: `BreadcrumbList` (Home › Guides) + `ItemList` of all non-draft guides.
- **Sitemap:** `backend/routers/system.py` calls `get_all_guide_slugs()` from the guides router and appends `/guides` + each `/guides/{slug}` to the sitemap with the guide's own `updated` date as `lastmod` (priority 0.7, weekly). robots.txt does not disallow `/guides`.

## robots.txt & sitemap.xml (`backend/routers/system.py`)

- **`GET /robots.txt`** — `Allow: /`; `Disallow:` `/auth`, `/dashboard`, `/mock`, `/api/`; points to `{CANONICAL_BASE_URL}/sitemap.xml`. Registered on the `system` router, which is included **before** the SPA catch-all, so it wins the route match.
- **`GET /sitemap.xml`** — **derived from `_get_seo_meta()`**, not hand-listed: every non-`noindex` route key, plus a small static set of indexable pages not in the meta map (`/contact`, `/privacy`, `/terms`, `/refund-policy`), **plus `/guides` and every non-draft `/guides/{slug}` entry** (appended via `get_all_guide_slugs()` from `routers/guides.py`, each with its own `lastmod` from the guide's `updated` field). Self-maintaining — adding a route to the spa.py meta map automatically adds it to the sitemap; adding a non-draft `.md` file to `backend/content/guides/` automatically includes it. Priority/changefreq assigned by path pattern (home 1.0 daily; track/learn roots 0.8; learn-paths + guides 0.7; samples/faq 0.6; per-question 0.5; legal 0.3). Currently ~281 SPA URLs covering all 9 tracks' practice + 27 sample pages + learn paths + easy per-question pages, plus the guides surface.

## Structured data (JSON-LD)

- **Homepage (`/`)** — `Organization` + `WebSite` graph, injected server-side by `_inject_seo` (crawler-visible). This is the **entity anchor** that helps Google distinguish datathink.co from the other "DataThink" entities. `sameAs` lists the verified first-party profiles (LinkedIn `company/datathink-co`, X `@datathinkHQ`, and YouTube `@datathinkHQ`); GitHub is omitted (private). Never point `sameAs` at the imposter "DataThink" profiles.
- **Inner pages** — role interview-prep pages (`BreadcrumbList` 3-level + `FAQPage`), the `/interview-prep` index (`BreadcrumbList` + `ItemList`), FAQ, learning paths, track hubs, and sample pages carry their own JSON-LD via Helmet (client-rendered).

## noindex

`/auth`, `/dashboard`, `/mock` are private/utility surfaces — `_build_seo_meta` flags them `noindex` (spa.py injects `<meta name="robots" content="noindex, nofollow">`) and the sitemap excludes them.

## Roadmap

- **Phase 1 (done — this doc).** Homepage + per-route titles/descriptions, robots + derived sitemap, homepage Organization/WebSite JSON-LD, `CANONICAL_BASE_URL` consolidation.
- **Phase 2 — role landing pages (done).** Four indexable role pages at `/interview-prep/<role>` (data-engineer, data-analyst, analytics-engineer, data-scientist) + a `/interview-prep` roles index, targeting role-specific intent. Built from the shared role→track mapping in `frontend/src/roleRegistry.js` (the SoT, framing per [`specs/platform-north-star.md`](specs/platform-north-star.md) §Role-to-track). Each page has spa.py meta + a Helmet mirror, sits in the sitemap, carries a 3-level `BreadcrumbList` + `FAQPage` JSON-LD, is internally linked from the landing role selector (a per-role prep link), the index, and a **topbar "By Role" dropdown on every page**, and points its primary CTA at a **role-filtered Sample Hub** (`/sample?role=<slug>`, a toggle bar of `All` + the four roles). Component `RoleInterviewPrepPage` is config-driven (`ROLE_CONTENT`); the index is `InterviewPrepIndexPage`. Scroll-reveal animations come from the shared `components/Reveal.js`.
- **Phase 3 — authority & disambiguation.** `SoftwareApplication`/`FAQPage` schema, per-role OG images, internal-linking pass for sitelinks, and the operational levers: **Google Search Console verification + sitemap submission**, Organization `sameAs`, and a first-party Google Business Profile.

## Brand disambiguation (the real SERP lever)

"datathink" is contested by ≥3 other entities; `datathink.io` holds a verified Google **Business Profile → knowledge panel**, which structurally outranks a plain organic result. **Meta tags alone will not win the bare-brand query.** The levers are entity signals (Organization JSON-LD + `sameAs`, Search Console, a first-party Business Profile) and owning the higher-converting **role + intent** queries (Phase 2). Expect days-to-weeks lag on any change (Google recrawl).

## Tests

- `backend/tests/test_seo_phase1.py` — homepage title + JSON-LD presence, robots.txt content, sitemap includes (home, every track incl. reasoning tracks) / excludes (noindex) assertions.
- `backend/tests/test_guides.py` — `/guides` index (200, contains starter guide link), `/guides/{slug}` (200, exact sentence, `<title>` tag, canonical URL, `Article` JSON-LD), 404 on missing slug, sitemap contains `/guides/{slug}`, no em-dash in frontmatter, draft guide is excluded (404 on direct hit, absent from index and sitemap).
