# Opus session prompt — Launch-readiness audit (the un-swept dimensions)

Paste the block below into a fresh Opus session. Security (sandbox + entitlements) and content
correctness are already done and CI-validated; this covers what's left. See
[`../../TODO.md`](../../TODO.md) for the one-line summary.

> Note: the concurrency/load dimension has its own dedicated prompt
> ([`session-concurrency-load.md`](session-concurrency-load.md)) — run that one for load/scaling;
> this prompt's load section is a pointer to it.

---

```
# datathink — Launch-readiness production review (the dimensions not yet audited)

You are an Opus session. Hold all five CLAUDE.md lenses. Read CLAUDE.md first (standing
instructions: commit to main, keep CI green, verify-then-report-then-fix before changing
anything, route content edits through the authoring agent, never weaken the existing
sandbox/entitlement/grading-determinism hardening).

## Already done — do NOT re-audit (committed, CI-green)
- CONTENT correctness: Phases 1–4 audit (3 external model families + blind adjudication) +
  MCQ answer-key debiasing (position + length). Records: backend/scripts/audit_findings_log.md,
  docs/decisions/DECISIONS.md.
- SECURITY: code-execution sandbox (env scrub, hardened AST guard, seccomp egress, non-root +
  read-only /app, killpg-on-timeout, RLIMIT_AS/NPROC/FSIZE/CPU, output caps, concurrency
  semaphore) + server-side entitlement enforcement with a negative-entitlement test suite.
  See docs/deployment.md § Sandbox security hardening, CLAUDE.md § Sandbox security layers.
- GRADING DETERMINISM: duckdb pinned to 1.5.0, SET threads TO 1, tests/test_code_references.py.

## This session — audit the dimensions never swept. For each: verify against the REAL code,
## report findings with file:line, prioritize P0 (launch-blocker) / P1 (fix-before-launch) /
## P2 (post-launch), and STOP for approval before fixing.

1. PAYMENTS CORRECTNESS UNDER FAILURE (routers/razorpay.py, routers/account.py, db.py billing):
   - Webhook signature verification + IDEMPOTENCY (a replayed/duplicated webhook must not
     double-apply a plan change or double-count).
   - Double-charge protection; order/subscription state machine under partial failure.
   - Plan transitions: upgrade / downgrade / cancel / reactivate / expiry — edge cases, and
     that entitlements update atomically with billing state.
   - No plan grant without a verified payment; no entitlement leak on a failed/partial payment.

2. OBSERVABILITY & ALERTING:
   - Sentry (backend + frontend), PostHog funnel events, request_id tracing, X-Response-Time-Ms
     all wired and firing. Confirm, don't assume.
   - The likely real GAP: is anything actually PAGING on error-rate spikes, failed payments, or
     latency? Name what's missing and what a minimal alerting setup looks like.

3. DEPLOYMENT & ROLLBACK (Dockerfile, railway.json, docs/deployment.md):
   - Health check, single-service image, env-var completeness, the prod-migration runbook
     (ENV=production disables auto-migrate). What is the rollback procedure if a deploy is bad?
   - Confirm prod Postgres is at alembic head; flag any local-only migration.

4. LEGAL / COMPLIANCE (a paid product taking real PII + payments):
   - Privacy policy, ToS, cookie/consent, GDPR data-deletion path (account delete actually
     erases PII?), email deliverability (Resend domain/SPF/DKIM). Flag anything missing.

5. LOAD / SCALING — do NOT do it here. It has a dedicated prompt
   (docs/backlog/session-concurrency-load.md). Just confirm it remains open.

## METHOD
Spawn parallel read-only sub-agents per dimension if it speeds breadth; you integrate. Produce
ONE prioritized readiness report (evidence + risk + fix per finding). Verify before reporting.
STOP after the report; then fix P0/P1 one by one on approval. Keep CI green; work on main;
follow the prod-migration runbook for any schema change.

## START BY
Read CLAUDE.md + docs/architecture.md + docs/backend.md + docs/deployment.md +
docs/features/pricing.md + docs/features/mock.md, then give the dimension-by-dimension plan
before diving in.
```
