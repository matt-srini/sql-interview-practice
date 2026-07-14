# New-track integration surfaces

> **Companion to [`track-onboarding.md`](./track-onboarding.md).** That doc is the *process*
> (phases, curriculum, authoring). This doc is the *exhaustive surface inventory* — every
> place a track's identity, module, counts, or copy appears — so a new track (the 11th and
> beyond) never ships with the class of bugs the 10th hit: `0/0` counts on the landing, a
> 500 on learning-path detail, a missing dashboard row, or stale "9 tracks / 850+" copy.
>
> **The lesson from track 10 (Product Sense):** the track list was hardcoded in ~12 places,
> the launch touched one, and the rest were found only by a user noticing `0/0`. The fix was
> to make the mechanical maps **derive from a single source** and guard the rest with tests.
> Read this before wiring a track; it tells you what is now automatic and what still isn't.

---

## The two single sources of truth

| Layer | SoT | Add a track by… |
|---|---|---|
| **Backend** | `backend/tracks.py` → the `TRACKS` tuple (`TrackConfig`) | Adding one `TrackConfig(slug, db_topic, catalog_module, label, eval_kind, …)` |
| **Frontend** | `frontend/src/trackRegistry.js` → `TRACK_META` | Adding one `TRACK_META` entry (`TRACK_SLUGS` derives from it) |

Everything in **Category A** below reads from one of these two. Get the `TrackConfig` and the
`TRACK_META` entry right and most of the app lights up automatically.

---

## Category A — Auto-derives from the registry (no per-surface edit)

Once the `TrackConfig` exists, these populate themselves. **Do not re-hardcode a track list
in any of these** — that is exactly the drift that caused the track-10 bugs. All derive from
`for t in TRACKS` (or `TRACK_SLUGS`):

| Surface | File | Derives |
|---|---|---|
| Practice counts (`/api/catalog/counts`) — landing "Jump back in", logged-out tracks list, dashboard totals, Sample-Hub total | `backend/routers/system.py` | `{t.slug: counts}` |
| SEO track counts + labels | `backend/routers/spa.py` `_get_track_counts`, `_TRACK_LABELS` | `t.label` |
| Dashboard per-track stats | `backend/routers/dashboard.py` `_TOPIC_MODULES` | `t.catalog_module` |
| Learning-path detail (per-question solved state) | `backend/routers/paths.py` `_TOPIC_MOD`, `_TOPIC_DB` | `t.catalog_module`, `t.db_topic` |
| Sample loading + interaction-mode UI | `backend/sample_questions.py` `_TRACK_SAMPLE_FILES`, `_INTERACTION_MODE_TRACKS` | `"<db_topic>.json"`; `eval_kind in {mcq, mixed}` |
| Mock-debrief language class (reasoning vs executable) | `backend/routers/insights.py` `_REASONING_TRACKS` | `eval_kind == "mcq"` |
| Valid track / mock-role sets, sitemap URLs | `backend/tracks.py`, `backend/routers/spa.py` sitemap | `TRACKS` / spa meta map |
| Frontend track list, catalog counts, "Jump back in", Sample Hub grid | `frontend/src/trackRegistry.js` `TRACK_SLUGS`, `CatalogCountsContext` | `TRACK_META` / `/api/catalog/counts` |
| Total-question copy (landing SEO meta, Sample-Hub footer) | `frontend/src/pages/{LandingPage,SampleHubPage}.js` | `useCatalogCounts()` sum — **never hardcode a total** |

---

## Category B — Manual per-track CONTENT (can't derive — guarded by a test)

These hold hand-authored content that varies per track, so they need an entry. A **completeness
test fails CI** if you forget one — so you cannot silently ship a broken track here.

| Surface | File | If missing… | Guarded by |
|---|---|---|---|
| Single-track mock **benchmark shape** | `backend/routers/mock.py` `BENCHMARK_CONFIGS` | Benchmark mode 404s for the track | `backend/tests/test_track_registry_completeness.py` |
| Practice-page **SEO description** | `backend/routers/spa.py` `_PRACTICE_DESC` | Generic SEO meta on `/practice/<slug>` | `backend/tests/test_track_registry_completeness.py` |
| Mock **focus-concept** chips (Elite) | `frontend/src/pages/MockHub.js` `TRACK_CONCEPT_MAP` | Empty focus-mode chips | `frontend/src/trackRegistryCompleteness.test.js` |
| Benchmark **type distribution** | `backend/routers/mock.py` `_benchmark_type_targets` | Falls back to all-`conceptual` (fine for most; add for accuracy) | — (has a fallback) |
| Hub **description** template | `frontend/src/pages/TrackHubPage.js` `HUB_DESC_TEMPLATES` | Falls back to `trackRegistry` description (acceptable) | — (has a fallback) |

If you add a track and CI goes red on `test_track_registry_completeness` /
`trackRegistryCompleteness`, that is the backstop working — add the missing entry.

---

## Category C — Registration (scaffold, before content)

| Surface | File | Note |
|---|---|---|
| `TrackConfig` | `backend/tracks.py` `TRACKS` | The backend SoT. `eval_kind`, `db_topic`, `catalog_module`, `label`, `concept_blocklist`, hint rules. |
| Catalog loader | `backend/<slug>_questions.py` | Must expose `get_questions_by_difficulty`, `get_all_questions`, `get_public_question`, `get_catalog`. |
| Router include | `backend/main.py` | `app.include_router(<slug>_questions_router.router)` |
| `schemas.json` + empty `easy/medium/hard.json` | `backend/content/<slug>_questions/` | ID ranges; loader validates at boot. |
| Frontend `TRACK_META` | `frontend/src/trackRegistry.js` | The frontend SoT (`comingSoon: true` until launch). No `totalQuestions` field — counts are fetched live. |
| Hero demo frame | `frontend/src/pages/LandingPage.js` `IDE_TRACKS` | Hardcoded (one representative question); not derived. |
| Concept families | `backend/concept_families.py` `CONCEPT_FAMILIES[slug]` | Needed before `_TAXONOMY_VALIDATED_TRACKS`. |
| Path patterns | `backend/path_patterns.py` `PATH_PATTERNS[slug]` | Register pattern slugs before authoring paths. |
| Batch-balance loader | `backend/scripts/check_batch_balance.py` `_LOADERS` | For the authoring balance check. |

---

## Category D — Go-live (flip `comingSoon`; wire role membership together)

Role membership must be wired in **one commit** across FE + BE + tests, or the Mixed-benchmark
count desyncs (see [`DECISIONS.md`](./decisions/DECISIONS.md) 2026-07-13). The parity test
`slots == role pool` (`backend/tests/test_11_mock.py`) enforces the backend half.

| Surface | File | Action |
|---|---|---|
| Remove coming-soon | `frontend/src/trackRegistry.js` | Delete `comingSoon: true` (track becomes enterable; joins `TRACK_SLUGS`). |
| Role → track (FE) | `frontend/src/roleRegistry.js` `ROLES[*].tracks` | Add slug to each role that claims it. |
| Role → track (BE) | `backend/tracks.py` `_ROLE_TRACKS` | Same membership as roleRegistry. |
| Mixed benchmark slots + time | `backend/routers/mock.py` `MIXED_BENCHMARK_CONFIGS` | Add `slug: 1` slot + bump `time_limit_s` (keep slots == role pool). |
| Mixed benchmark blurb/time (FE) | `frontend/src/mockModeConfig.js` `MIXED_BENCHMARK_BLUEPRINTS` + `BENCHMARK_BLUEPRINTS` | Single-track blueprint + Mixed time; count derives from roleRegistry. |
| Role-page SEO copy | `frontend/src/pages/RoleInterviewPrepPage.js` + `backend/routers/spa.py` role meta | Track blurb + count label + description. |
| Strict tag validation | `backend/scripts/validate_content.py` `_TAXONOMY_VALIDATED_TRACKS` **and** `backend/tests/test_paths_quality.py` `_TAXONOMY_VALIDATED_TRACKS` | Add slug (families must be registered first). |
| Sample registration | `backend/scripts/validate_content.py` `SAMPLE_FILES` | Add sample file (the runtime `_TRACK_SAMPLE_FILES` already derives). |
| **Brand assets** | `frontend/public/og-image{,-light}.svg`, `frontend/public/branding/x-banner{,-light}.svg` | Bump the track count + the "N+ curated / N+ mock" floors; **re-render** via `node frontend/scripts/render-brand-assets.mjs`; bump the OG `?v=` in `spa.py` + `index.html`. Then verify the PNG. |
| **Test fixtures** | `frontend/src/pages/ProgressDashboard.test.js`, `LandingPageTiers.test.js` | Bump the mocked track-count fixtures + assertions to the new count. |
| **Docs (same commit)** | `CLAUDE.md`, `docs/content-authoring.md` (bank + tables + ID scheme), `docs/specs/platform-north-star.md`, `docs/frontend.md`, `docs/seo.md`, `docs/growth/{gtm-strategy,editorial-calendar,starter-assets}.md`, `docs/USERGUIDE.md`, `docs/concept-hooks.md` (new track section) | Footprint counts (tracks, practice, mock, samples, paths) + the "N tracks" pillar copy. |

---

## Category E — The backstops (run before you commit)

```bash
# backend — validation, completeness, mock parity, paths, serialization, catalog
cd backend && ../.venv/bin/python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_track_registry_completeness.py \
  tests/test_11_mock.py tests/test_paths_quality.py tests/test_10_paths.py \
  tests/test_public_question_serialization.py tests/test_03_catalog.py -q

# frontend — completeness + full suite + build
cd frontend && npx vitest run && npm run lint && npm run build

# spot-check the live counts end to end (backend running)
curl -s localhost:8000/api/catalog/counts | python3 -m json.tool   # every track, correct total
```

If `test_track_registry_completeness` (backend) or `trackRegistryCompleteness` (frontend) is
red, you missed a Category-B entry. If `test_11_mock`'s `slots == pool` is red, role membership
is half-wired. Green across all of these ⇒ the track is integrated everywhere it needs to be.
