# docs/ — index

This is the navigation hub for all platform documentation. Each doc below owns a specific area; cross-link aggressively, never duplicate.

`CLAUDE.md` (at the repo root) holds Claude-specific standing instructions and pushback lenses — not reference material. For anything that's a fact about the platform, look here first.

---

## Architecture and platform

| File | What it covers |
|---|---|
| [`architecture.md`](architecture.md) | System design, request lifecycles, data model, execution pipelines, scaling |
| [`backend.md`](backend.md) | All API routes, routers, execution pipeline, identity model |
| [`frontend.md`](frontend.md) | Routes, pages, components, design system, data flows |
| [`seo.md`](seo.md) | SEO architecture: per-route meta injection, titles, robots/sitemap, structured data, roadmap |
| [`datasets.md`](datasets.md) | All 11 dataset tables — columns, row counts, intentional edge cases |
| [`deployment.md`](deployment.md) | Local dev, Docker, production image, env vars, Railway |
| [`USERGUIDE.md`](USERGUIDE.md) | End-user guide to the platform |

## Specs (canonical contracts)

| File | What it covers |
|---|---|
| [`specs/platform-north-star.md`](specs/platform-north-star.md) | Canonical product goal, role framing, practice/dashboard/mock relationship, filter policy |
| [`specs/practice-modality-spec.md`](specs/practice-modality-spec.md) | Track modality matrix, practice interaction rules, metadata contract |
| [`specs/mock-benchmark-spec.md`](specs/mock-benchmark-spec.md) | Benchmark-vs-drill split, mock invariants, analytics contract |
| [`specs/sandbox-threat-model.md`](specs/sandbox-threat-model.md) | **Canonical sandbox threat model** — every code-execution defense layer, what each does and does not contain, and the residuals |

## Audits

| File | What it covers |
|---|---|
| [`audits/sandbox-PRR.md`](audits/sandbox-PRR.md) | **Sandbox PRR** (code-execution sandbox production-readiness review, 2026-06-26) — index for the security / reliability / scalability / observability hardening pass: findings, fixes, decisions, and what's deferred (Landlock) |

## Features

| File | What it covers |
|---|---|
| [`features/pricing.md`](features/pricing.md) | Pricing feature reference — plan entitlements, Razorpay flows, CTA states, webhook rules |
| [`features/mock.md`](features/mock.md) | Mock interview feature reference — plan gates, endpoints, coaching insights, test coverage |
| [`features/dashboard.md`](features/dashboard.md) | Dashboard feature reference — plan gates, endpoints, coaching insights, streak logic, caching |

## Content (authoring, taxonomy, tracks)

| File | What it covers |
|---|---|
| [`content-authoring.md`](content-authoring.md) | Platform philosophy, question counts, concept coverage maps, per-track schemas, authoring rules |
| [`concept-taxonomy.md`](concept-taxonomy.md) | Concept-family registry per track + 7 universal follow-up dimensions |
| [`concept-hooks.md`](concept-hooks.md) | Socratic interview-hook inventory (used to seed concept coverage) |
| [`tracks/`](tracks/) | Per-track philosophy, datasets, ID range, difficulty vocabulary, concept arc, authoring allocation — one file per track |

## Growth / go-to-market

| File | What it covers |
|---|---|
| [`growth/gtm-strategy.md`](growth/gtm-strategy.md) | **Canonical GTM SoT** — positioning→messaging, the reasoning-vs-grind wedge, ICP + anti-positioning, market-side launch checklist, channel strategy (LinkedIn / SEO / Reddit primary), the free-sample growth loop on the wired PostHog events, metrics/funnel, solo-founder cadence + the do-NOT list |
| [`growth/editorial-calendar.md`](growth/editorial-calendar.md) | 12-week editorial calendar + the 1-pillar→many-cuts production system + weekly operating rhythm |
| [`growth/starter-assets.md`](growth/starter-assets.md) | Example posts (LinkedIn/X/Reddit/newsletter/Show HN), subreddit target list + each sub's self-promo rule, brand-handle claim list, launch-day checklist, first-2-weeks day-by-day |

## Process / runbooks

| File | What it covers |
|---|---|
| [`track-onboarding.md`](track-onboarding.md) | End-to-end process for adding a new track — spec, backend, frontend, content, paths, docs |
| [`orchestration-runbook.md`](orchestration-runbook.md) | **Phase 2 orchestration handbook** — three-stage process (A planning → B execution → C audit), Stage A/B/C templates, retro-cleanup pattern, current Phase 2 status, pre-identified watch-outs for open tracks. Pickup point for any Opus session running Phase 2 orchestration. |
| [`runbooks/alerting.md`](runbooks/alerting.md) | **Alerting setup** — how an alert reaches you: Sentry payment-failure rules (A–C) + baseline app-error rules (D–E), `payment_stage` taxonomy, uptime monitor, remediation quick-reference. Dashboard setup only, no deploy. |
| [`runbooks/sentry-fix-pipeline.md`](runbooks/sentry-fix-pipeline.md) | **Sentry fix pipeline** — what happens *after* an alert: the human-gated read→fix→ship loop (two approval gates, CI-green-before-`land`, Sentry MCP, migration special-case, close-the-loop via "resolved in next release"). |
| [`decisions/DECISIONS.md`](decisions/DECISIONS.md) | **Decision log** — append-only *why* layer: every direction-changing decision, the alternatives rejected, and why. Consult before reversing anything load-bearing; append after any meaningful decision. Never expires (archive when large). |
| [`design/color-palette.md`](design/color-palette.md) | Canonical Forest & Ink theme — all CSS token definitions, light/dark values, accessibility notes |

## AI question authoring

One universal agent; per-track knowledge in the track docs.

| Purpose | File |
|---|---|
| **Universal authoring agent (mandatory entry point for every question, every track, every edit)** | [`.github/agents/question-authoring.agent.md`](../.github/agents/question-authoring.agent.md) |
| Per-track philosophy, datasets, ID range, difficulty vocabulary, concept arc, authoring allocation | [`tracks/<track>.md`](tracks/) |
| Concept-family registry per track + 7 universal follow-up dimensions | [`concept-taxonomy.md`](concept-taxonomy.md) |
| New track onboarding (end-to-end process) | [`.github/agents/track-onboarding.agent.md`](../.github/agents/track-onboarding.agent.md) |

The per-track question-authoring agent files (`sql-question-authoring.agent.md` etc.) were retired in the 2026-05 refactor — their content migrated to `tracks/<track>.md` and to the universal agent. There is now **one** authoring entry point on the platform. Use it.

## Archive

| File | What it covers |
|---|---|
| [`archive/`](archive/) | Historical phase trackers and migration records (non-authoritative — durable rules live in the docs above) |
| [`phases/`](phases/) | Active and recent phase tracking docs |
