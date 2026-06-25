# SEO

Canonical source of truth for **how datathink's SEO is wired**. The runtime SoT for the actual per-route meta *values* is code — `backend/routers/spa.py` (`_build_seo_meta` + `_inject_seo`); this doc describes the architecture, conventions, and roadmap around it. Keep both in sync (parity guard: `backend/tests/test_seo_phase1.py`).

SoT siblings: [`backend.md`](backend.md) §System / §SPA-static (the endpoints), [`frontend.md`](frontend.md) (Helmet usage per page), [`deployment.md`](deployment.md) (`CANONICAL_BASE_URL` env). Decisions: [`decisions/DECISIONS.md`](decisions/DECISIONS.md) 2026-06-25 SEO Phase 1.

---

## The three meta layers

This is a React SPA. Crawlers and social unfurlers (LinkedIn, Slack, X, Facebook) often do **not** execute JS, so per-route `<meta>` must be present in the **server-rendered HTML**, not only set client-side. We have three layers, in precedence order:

1. **`backend/routers/spa.py` — `_inject_seo()` — the crawler-visible per-route SoT.** For every known route the FastAPI SPA handler server-rewrites `<title>`, `meta description`, `og:title/description/url`, and injects `canonical` + `og:image` + `twitter:image` (+ JSON-LD on the homepage) **before sending the HTML**. This is what Google and unfurlers see with zero JS. The route→meta map is `_build_seo_meta()`. **When the SERP title/description matters, this is the file that controls it.**
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

## robots.txt & sitemap.xml (`backend/routers/system.py`)

- **`GET /robots.txt`** — `Allow: /`; `Disallow:` `/auth`, `/dashboard`, `/mock`, `/api/`; points to `{CANONICAL_BASE_URL}/sitemap.xml`. Registered on the `system` router, which is included **before** the SPA catch-all, so it wins the route match.
- **`GET /sitemap.xml`** — **derived from `_get_seo_meta()`**, not hand-listed: every non-`noindex` route key, plus a small static set of indexable pages not in the meta map (`/contact`, `/privacy`, `/terms`, `/refund-policy`). Self-maintaining — adding a route to the spa.py meta map automatically adds it to the sitemap. Priority/changefreq assigned by path pattern (home 1.0 daily; track/learn roots 0.8; learn-paths 0.7; samples/faq 0.6; per-question 0.5; legal 0.3). Currently ~281 URLs covering all 9 tracks' practice + 27 sample pages + learn paths + easy per-question pages.

## Structured data (JSON-LD)

- **Homepage (`/`)** — `Organization` + `WebSite` graph, injected server-side by `_inject_seo` (crawler-visible). This is the **entity anchor** that helps Google distinguish datathink.co from the other "DataThink" entities. `sameAs` lists the verified first-party profiles (LinkedIn `company/datathink-co` and X `@datathinkHQ`); GitHub is omitted (private). Never point `sameAs` at the imposter "DataThink" profiles.
- **Inner pages** — FAQ, learning paths, track hubs, and sample pages carry their own JSON-LD via Helmet (client-rendered).

## noindex

`/auth`, `/dashboard`, `/mock` are private/utility surfaces — `_build_seo_meta` flags them `noindex` (spa.py injects `<meta name="robots" content="noindex, nofollow">`) and the sitemap excludes them.

## Roadmap

- **Phase 1 (done — this doc).** Homepage + per-route titles/descriptions, robots + derived sitemap, homepage Organization/WebSite JSON-LD, `CANONICAL_BASE_URL` consolidation.
- **Phase 2 — role landing pages.** Indexable `/interview-prep/<role>` pages (`data-engineer` first, then analyst, scientist, analytics-engineer) targeting role-specific intent, built from the existing role→track mapping (`LandingPage.js` `ROLES`; framing per [`specs/platform-north-star.md`](specs/platform-north-star.md)). Each wired into the spa.py meta map + Helmet + sitemap, internally linked from the landing role selector, with `BreadcrumbList`/`Course` JSON-LD.
- **Phase 3 — authority & disambiguation.** `SoftwareApplication`/`FAQPage` schema, per-role OG images, internal-linking pass for sitelinks, and the operational levers: **Google Search Console verification + sitemap submission**, Organization `sameAs`, and a first-party Google Business Profile.

## Brand disambiguation (the real SERP lever)

"datathink" is contested by ≥3 other entities; `datathink.io` holds a verified Google **Business Profile → knowledge panel**, which structurally outranks a plain organic result. **Meta tags alone will not win the bare-brand query.** The levers are entity signals (Organization JSON-LD + `sameAs`, Search Console, a first-party Business Profile) and owning the higher-converting **role + intent** queries (Phase 2). Expect days-to-weeks lag on any change (Google recrawl).

## Tests

`backend/tests/test_seo_phase1.py` — homepage title + JSON-LD presence, robots.txt content, sitemap includes (home, every track incl. reasoning tracks) / excludes (noindex) assertions.
