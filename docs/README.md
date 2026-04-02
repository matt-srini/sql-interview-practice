# Documentation

This is the documentation hub for the datanest interview practice platform. Start here, then follow links into the specific area you need.

---

## Docs index

| Doc | What it covers |
|---|---|
| [architecture.md](./architecture.md) | System design, request lifecycles, data model, execution pipelines, scaling |
| [backend.md](./backend.md) | All API routes, routers, query execution, Python sandbox, identity model |
| [frontend.md](./frontend.md) | Route tree, pages, components, design system, data flows |
| [datasets.md](./datasets.md) | All 11 CSV tables — columns, row counts, edge cases |
| [deployment.md](./deployment.md) | Local dev, Docker, production build, environment variables, Railway |
| [content-authoring.md](./content-authoring.md) | Curriculum specs and authoring rules for all four tracks (SQL, Python, Pandas, PySpark) |
| [USERGUIDE.md](./USERGUIDE.md) | End-user guide to the platform |

---

## Quick orientation

**What it is:** A data interview practice platform with four tracks (SQL, Python, Pandas, PySpark), 311 questions, Monaco editor, instant feedback, and plan-gated progression.

**Tech stack:** React 18 + Vite frontend · FastAPI backend · PostgreSQL (state) · DuckDB (SQL execution) · Python subprocess sandbox · Redis (rate limiting) · Stripe (billing) · Single Docker container on Railway.

**Two practice modes:**
- **Challenge mode** (`/practice/:topic`) — plan-aware question bank, persistent progress, unlock gates
- **Sample mode** (`/sample/:topic/:difficulty`) — no login required, no progress recorded, 3 questions per track+difficulty

**For architectural decisions and system design:** see [architecture.md](./architecture.md)

**For adding or editing questions:** see [content-authoring.md](./content-authoring.md)
