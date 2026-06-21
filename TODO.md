# TODO — open workstreams

Durable backlog of work that is scoped but not yet done. The **why/what-was-rejected** for
finished decisions lives in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md); this
file is the forward-looking **what's-left**. Detailed, paste-ready Opus session prompts for the
two big items are saved under [`docs/backlog/`](docs/backlog/).

---

## P1 — Load & concurrency readiness  (head-of-line P0 fixed; the full ceiling RUN remains)
**Prompt:** [`docs/backlog/session-concurrency-load.md`](docs/backlog/session-concurrency-load.md)

✅ **DONE (2026-06-08) — head-of-line blocking + the load harness.** All blocking evaluators now
run **off** the event loop via `backend/offload.py` (`run_blocking_exec` under the
`MAX_CONCURRENT_EXECUTIONS` semaphore; `run_blocking_sql` offloaded **and** serialized behind a
process-wide lock), across every code-exec router (questions / python / pandas / statistics /
sample / mock). Measured before→after: `/health` head-of-line p95 **9.4× → 1.2×**; a 5 s
execution blocking a concurrent `/health` **4.7 s → ~0**; single-replica knee **~16 → ~32** active
users (now CPU-bound, not loop-bound); Postgres pool 5+10→10+20. The load-simulation harness was
built alongside (`backend/loadtest/` — zero-dep asyncio+httpx driver, weighted journeys in
`scenarios.py`, head-of-line + rate-limit probes; CI smoke test `test_concurrency_smoke.py`).
Off-loop password hashing (separate `MAX_CONCURRENT_HASHES` cap) + rate-limiter graceful
degradation landed too. Full why → `docs/decisions/DECISIONS.md` (2026-06-08 offload / hashing /
rate-limiter entries) + `docs/deployment.md` § Concurrency & scaling model.

**Remaining (still P1):**
- **Run + record the full realistic-load ceiling.** The harness exists and a head-of-line +
  auth-burst baseline is recorded, but the comprehensive `loadtest/driver.py` VU ramp (the
  weighted journeys against a prod-like deploy) has **not** been run end-to-end and recorded.
  Ramp to the knee and capture, per level: throughput (req/s), p50/p95/p99, error rate, Postgres
  pool-in-use vs size, live subprocess count, event-loop lag. State the honest concurrent-user
  ceiling and what saturates first.
- **Validate + finalize the tiered scaling roadmap.** Tiers 1–3 are already drafted in
  `docs/deployment.md` § Concurrency & scaling model (config+offload → horizontal replicas →
  externalized execution fleet). Confirm the Tier-1 "low-thousands read-heavy" figure against the
  measured ceiling, and set the concrete Tier-2 trigger (the VU level / resource-saturation signal
  that means "add a replica now").

## P1 — Launch-readiness audit  (the dimensions not yet swept)
**Prompt:** [`docs/backlog/session-launch-readiness.md`](docs/backlog/session-launch-readiness.md)

Security (sandbox + entitlements) and content correctness are done and CI-validated. Dimensions
swept this cycle: **payments correctness under failure** (webhook idempotency, double-charge,
plan-transition edge cases), **observability/alerting** (is anything paging on error-rate /
failed payments?), **deployment/rollback**, **legal/compliance** (privacy, ToS, GDPR deletion,
email deliverability). Verify against real code, prioritize P0/P1/P2, stop before fixing.

**Status (2026-06-21):** CLOSED for P0/P1. P0s fixed earlier this session (Pro→Elite plan-switch
now persists from the webhook `plan_id`; Paddle dual-rail billing parity). P1s landed this cycle:
**prod config guard** (boot-requires Razorpay plan IDs + `RESEND_API_KEY` + `ADMIN_SECRET`≥32),
**payment alerting** (`capture_payment_failure` → Sentry, one `alert=payment_failure` tag across
razorpay/paddle/account), **rollback runbook** (`docs/deployment.md`), and an opt-in **cookie
consent** banner (PostHog gated until Accept). Why → `docs/decisions/DECISIONS.md` 2026-06-21.
**Operator's one remaining step:** create the Sentry alert rules + uptime monitor per
[`docs/runbooks/alerting.md`](docs/runbooks/alerting.md).

## P2 — Revisit Interview Loop replay once the mock chain-pools are expanded
The consent-gated **replay** (DECISIONS 2026-06-19) was shipped while several loop cells were
thin (Statistics-hard = 1 chain, Pandas-medium = 2, SQL = 3/3) — replay turned those near-instant
dead-ends into a "completed → Replay" state. We are now expanding those pools by authoring fresh
chains (Statistics-hard first, then SQL; Pandas-medium deferred). **Open decision, deliberately
deferred:** once the pools are deep enough that exhaustion is rare, decide whether to **(a) keep
replay** as the permanent end-state UX, or **(b) rewrite/scope it down** (e.g. only surface Replay
after N completed sessions, or revert it entirely if depth makes exhaustion effectively
unreachable). Do **not** decide until the authoring expansion lands and we can see real per-cell
depth. Trigger: after the Stats-hard + SQL chain expansions are merged. Cross-ref:
`docs/decisions/DECISIONS.md` 2026-06-19; `docs/features/mock.md` § Follow-up Chain Atomicity rule 6.

## P3 — Position Interview Loop as the earned capstone (benchmark → drill → Loop)
Frame Interview Loop in the UX as the culminating "real interview" experience — the deliberate
readiness test you reach for *after* benchmarking (diagnose) and drilling (fix weak spots), not a
daily drill tool. Surfaces to touch: the Loop mode card / Loop-setup copy on MockHub (a "best after
a benchmark + a drill or two" line; a soft nudge when the user has no benchmark history), the
dashboard + mock post-mortem recommendation engine (add "you're ready for an Interview Loop" as the
capstone next-step after benchmark+drills, extending the existing benchmark→drill→concept-drill
funnel), and the "How it works" modal (reinforce: Loop = the real-interview readiness check, used
deliberately). **Guardrails — do NOT cross:** this is *framing + recommendation only*, NEVER a hard
prerequisite lock — a user who knows what they want must still be able to start a Loop directly
(hard-gating a paid Elite feature is artificial friction / the "serving a metric, not the user"
anti-pattern). Keep the scarcity *honest* (it reflects the genuinely deep, finite, expensive-to-author
chain pools + the readiness-test purpose), never *manufactured* (no cooldown throttle or daily-cap
retention trick). Bonus: deliberate, occasional Loop use exhausts the thin chain pools far more
slowly — this framing directly relieves the replay-revisit pressure above. Operator direction
(2026-06-19); agreed with one refinement (framing-not-gate, honest-not-manufactured scarcity).

## P2 — SQL reference float-robustness  (the duckdb pin is a band-aid masking this)
`duckdb==1.5.0` is pinned because q13011's reference compared **raw float aggregates** in
`HAVING` (`AVG(after) < AVG(before)`) on a knife-edge — DuckDB 1.5.3 evaluated it differently
and the reference returned 0 rows on CI. **Other SQL references share the pattern**
(`content/questions/hard.json`, `medium.json`). Active guard today = the pin + `SET threads TO
1` + `tests/test_code_references.py` (fails any degenerate reference) + the documented
"re-run that test before any engine bump" rule (`docs/backend.md` §). The durable fix (so
references survive an engine bump): **round float-aggregate comparisons to the displayed
precision** (`ROUND(AVG(...),2) < ROUND(AVG(...),2)`) wherever they appear — via the
question-authoring agent, with the x86 reproduction per question. Not urgent (the pin holds),
but record it so a future `duckdb` bump doesn't silently re-break grading.

## P3 — ml-fundamentals answer length sits below uniform  (minor)
After the MCQ debiasing, ml-fundamentals' "pick-the-longest" rate landed at ~17% (below the
25% uniform) — a mild *reverse* lean ("the correct answer is rarely the longest here"). Not a
gameability hole and not validator-flagged; evening it out carries content-regression risk.
Optional re-center if ever revisited.

## P3 — CI runner Node 20 deprecation  (warning only today)
The CI workflow uses `actions/checkout@v4` + `actions/setup-python@v5`, which run on
**Node.js 20**. GitHub flipped the runner default to Node 24 on **2026-06-16 (now past)** and
removes Node 20 from the runner on **2026-09-16** — that removal is the hard deadline. It remains
warning-only — CI passes green — until then. Fix when convenient: bump those actions to versions
that ship Node 24 (newer `checkout`/`setup-python` patch tags already do), or temporarily set
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` on the job. Recorded so the September removal doesn't
silently break CI.

---

### Config notes (operator)
- Railway: `MAX_CONCURRENT_EXECUTIONS=6` is set (8 vCPU − 2). Replica Memory left at the 8 GB
  plan max (billed on actual usage; gives OOM headroom above app + 6×512 MB sandbox peak).
- Sandbox egress filter needs `libseccomp2` (Dockerfile) + `pyseccomp` (requirements) — fails
  open if absent. The one remaining infra item is already done.
