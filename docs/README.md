# Documentation

This is the documentation hub for the datathink interview practice platform. Start here, then follow the links into the specific area you need.

---

## Docs index

| Doc | What it covers |
|---|---|
| [architecture.md](./architecture.md) | System design, request lifecycles, data model, execution pipelines, scaling considerations |
| [backend.md](./backend.md) | All API routes, routers, query execution pipeline, Python sandbox, identity model |
| [frontend.md](./frontend.md) | Route tree, pages, components, design system, data flows |
| [datasets.md](./datasets.md) | All 11 CSV tables — columns, row counts, intentional edge cases |
| [deployment.md](./deployment.md) | Local dev setup, Docker, production build, environment variables, Railway |
| [railway-razorpay-launch-checklist.md](./railway-razorpay-launch-checklist.md) | End-to-end launch checklist for local Razorpay test mode, Railway deployment, and live-mode cutover |
| [content-authoring.md](./content-authoring.md) | Curriculum philosophy, question counts, concept coverage maps, per-track authoring rules, JSON schemas |
| [content-quality-remediation-plan.md](./content-quality-remediation-plan.md) | Phased implementation plan for improving question quality, hinting, guided progression, weak-spot analysis, and pricing-claim alignment |
| [USERGUIDE.md](./USERGUIDE.md) | End-user guide to the platform |

---

## Quick orientation

**What it is:** A data interview preparation platform with four tracks (SQL, Python, Pandas, PySpark), 350 questions, Monaco editor, instant feedback, and plan-gated progression.

**Tech stack:** React 18 + Vite frontend · FastAPI backend · PostgreSQL (state) · DuckDB (SQL execution) · Python subprocess sandbox · Redis (rate limiting) · Razorpay (billing) · Single Docker container on Railway.

**Two practice modes:**
- **Challenge mode** (`/practice/:topic`) — plan-aware question bank, persistent progress, unlock gates
- **Sample mode** (`/sample/:topic/:difficulty`) — no login required, no progress recorded, 3 questions per track+difficulty

---

## Question bank at a glance

| Track | Easy | Medium | Hard | Total |
|---|---|---|---|---|
| SQL | 32 | 34 | 29 | 95 |
| Python | 30 | 29 | 24 | 83 |
| Pandas | 29 | 30 | 23 | 82 |
| PySpark | 38 | 30 | 22 | 90 |
| **Total** | **129** | **123** | **98** | **350** |

Sample questions (no login, no progress tracking): 3 per track × 3 difficulties = **36 total**.

---

## Adding or editing questions

See [content-authoring.md](./content-authoring.md) for the full authoring guide — philosophy, difficulty standards, JSON schemas, and the pre-commit checklist.

For AI-assisted question generation, use the track-specific agent prompt files in `.github/agents/`:

| Track | Agent file |
|---|---|
| SQL | [`.github/agents/sql-question-authoring.agent.md`](../.github/agents/sql-question-authoring.agent.md) |
| Python | [`.github/agents/python-question-authoring.agent.md`](../.github/agents/python-question-authoring.agent.md) |
| Pandas | [`.github/agents/pandas-question-authoring.agent.md`](../.github/agents/pandas-question-authoring.agent.md) |
| PySpark | [`.github/agents/pyspark-question-authoring.agent.md`](../.github/agents/pyspark-question-authoring.agent.md) |

---

## Where to start reading

| Goal | Start here |
|---|---|
| Understand how the system works end-to-end | [architecture.md](./architecture.md) |
| Add or change a question | [content-authoring.md](./content-authoring.md) |
| Work on the API or execution pipeline | [backend.md](./backend.md) |
| Work on the UI | [frontend.md](./frontend.md) |
| Understand the datasets | [datasets.md](./datasets.md) |
| Set up the dev environment | [deployment.md](./deployment.md) |
