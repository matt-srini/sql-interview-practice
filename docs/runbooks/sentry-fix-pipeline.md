# Sentry fix pipeline — read → fix → ship

How a production error in Sentry becomes a deployed, verified fix. The loop is
**human-gated by design**: two explicit approvals, and CI must be green before
`main` moves. This is the companion to [`alerting.md`](alerting.md) (which tells
you *how the alert reaches you*) and the [rollback runbook](../deployment.md#rollback-runbook)
(which tells you *what to do when a fix is bad*).

> **The governing fact:** on Railway, **push to `main` = deploy to production.**
> There is no separate "deploy" button in the happy path — `scripts/land.sh`
> pushing `main` is the deploy. Every gate below exists because of this.

---

## The loop at a glance

```
 [1] DETECT     Sentry alert → Slack/email (rules live in alerting.md §2)
       │
 [2] READ       Claude pulls the issue via the Sentry MCP: stack trace, tags
       │         (request_id · user.plan · payment_stage), breadcrumbs, suspect commit
       ▼
 [3] DIAGNOSE  ◄── APPROVAL GATE 1 — you review the plan/diff before anything commits
       │         worktree per issue · reproduce · fix + regression test + doc update
       ▼
 [4] VERIFY     local tests green · push the BRANCH → CI green (a check, not a deploy)
       │         ⚠ migration? → the migration discipline applies (see below)
       ▼
 [5] SHIP      ◄── APPROVAL GATE 2 — you say "land"
       │         scripts/land.sh <branch> → ff main → push → Railway deploys
       ▼
 [6] CLOSE      mark issue "Resolved in next release" → Sentry auto-reopens on regression
```

---

## Stage 1 — DETECT

An alert fires from a Sentry rule (see [`alerting.md`](alerting.md) §2). Payment
failures (Rules A/B/C) page loudest; the baseline rules (D/E) catch the long tail
of non-payment errors. Every alert links straight to the Sentry **issue**.

You do not start this pipeline from a hunch — you start it from an issue URL.

## Stage 2 — READ (Claude pulls the context)

Connect the **Sentry MCP** once (declared in the project [`.mcp.json`](../../.mcp.json);
first use prompts an OAuth flow in the browser):

```
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

Then hand Claude the issue:

> Pull Sentry issue `<URL or SHORT-ID>` and root-cause it. Use the `request_id`
> tag to correlate with the Railway logs. Don't propose a fix yet — first tell me
> the failing code path and your hypothesis.

What Claude reads off the issue, and why each matters here:

| Signal | Where it points |
|---|---|
| `http.path` tag | the router in `backend/routers/` |
| `user.plan` tag | an entitlement/gate bug (`unlock.py`, mock plan-tier) if it's plan-specific |
| `payment_stage` tag | the exact billing failure point — see [`alerting.md`](alerting.md) §1 |
| `request_id` tag | `grep` it in Railway logs for the full server-side trail of that one request |
| suspect commit | the commit Sentry blames (requires the GitHub integration + release commits) |

## Stage 3 — DIAGNOSE & PROPOSE — **APPROVAL GATE 1**

Claude works in an **issue-scoped worktree** (never on `main`):

```
git worktree add ../sql-interview-practice-fix-<issue> -b fix-<issue>
```

It reproduces the failure against the real code path, then proposes: the **fix**,
a **regression test** that fails before and passes after, and the **doc update**
(per the no-stale-docs rule). For anything non-trivial, use **Plan mode** — Claude
presents the plan and you approve *before* it writes code.

**Nothing commits without your review of the diff.** This is the gate.

## Stage 4 — VERIFY (the pre-deploy gate)

Because `main` = prod, verification happens **before** `main` moves, in two layers:

1. **Local** — run the relevant suite in the worktree:
   - backend: `cd backend && ../.venv/bin/python -m pytest -q` (+ `scripts/validate_content.py` if questions changed — see the CLAUDE.md post-fix checklist)
   - frontend: `cd frontend && npm test`
   - UI change → browser-preview it (note: a worktree frontend can't auth against the prod CORS list; verify on the main checkout after land, or set `VITE_BACKEND_URL`).
2. **CI** — `git push -u origin fix-<issue>`. CI (`ci.yml`) runs on **every branch**,
   so this gets you a full green check (migrations, tests, audits, build) **without
   deploying** — Railway only deploys `main`. **Wait for green before Stage 5.**
   This is the whole reason to push the branch: CI becomes a true pre-deploy gate
   instead of running concurrently with the deploy.

### ⚠ If the fix ships a migration

Schema is the one thing a code rollback (Railway redeploy) cannot undo. Follow the
CLAUDE.md migration discipline **in this same session**: write the migration, sync
`_SCHEMA_SQL` in `db.py`, apply it to prod with the `DATABASE_URL` from `backend/.env`,
confirm `alembic current` shows the new head, and log it in `deployment.md`. Raise
the review bar accordingly.

## Stage 5 — SHIP — **APPROVAL GATE 2**

On your "land":

```
scripts/land.sh fix-<issue>
```

This fast-forwards `main` to the verified branch commits, pushes `origin/main`,
and removes the worktree + branch. Railway picks up the `main` push and deploys.

Then **watch**:
- `GET /health` returns 200 (Railway marks the deploy live only on a 200).
- The Sentry issue — new events should stop arriving on the new release.

If `/health` fails or events keep coming, go to the [rollback runbook](../deployment.md#rollback-runbook):
code-only rollback is a one-click Railway redeploy of the previous image and carries
zero DB risk (`ENV=production` disables auto-migrate).

## Stage 6 — CLOSE THE LOOP

In Sentry, mark the issue **Resolved in next release**. If the same error recurs in
a *later* release, Sentry **auto-reopens** it as a regression — this is your tripwire
for a bad fix. It only works if releases are tracked correctly: backend and frontend
must share one release id per deploy (set `SENTRY_RELEASE` to the git SHA — see
[`deployment.md`](../deployment.md) Sentry env vars).

---

## Guardrails (why the loop is not autonomous)

- **Keep both approval gates.** A bot that auto-pushes fixes to a payment product
  where `main` = prod is exactly the thing not to build. You review the diff (Gate 1)
  and you say "land" (Gate 2).
- **CI green before `land`, never after.** Push the branch, wait for the check.
- **Migrations get the full discipline** — they are the asymmetric, hard-to-revert risk.
- **Model usage:** diagnosis (Stages 2–3) on the capable model; once the fix is a
  known mechanical edit, delegate the edit to Sonnet. You remain the approver either way.

---

## See also

- [`alerting.md`](alerting.md) — alert rules, payment-failure stages, uptime monitor, remediation
- [`../deployment.md#rollback-runbook`](../deployment.md) — code vs schema rollback, smoke checklist
- `CLAUDE.md` — worktree + `land.sh` workflow, migration discipline, post-fix verification checklist
