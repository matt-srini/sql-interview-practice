# TODO — open workstreams

Durable backlog of work that is scoped but not yet done. The **why/what-was-rejected** for
finished decisions lives in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md); this
file is the forward-looking **what's-left**. Detailed, paste-ready Opus session prompts for the
two big items are saved under [`docs/backlog/`](docs/backlog/).

---

## P1 — Load & concurrency readiness  ✅ CLOSED (launch-ready Tier 1; 2 non-blocking operator config residuals)
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

✅ **DONE (2026-06-08) — ceiling measured + tier roadmap finalized.** The comprehensive VU ramp was
run on a prod-like box (8 vCPU, single worker, `MAX_CONCURRENT_EXECUTIONS=6`). **Verdict: LAUNCH-READY
at Tier 1, no blockers** — serves low-thousands concurrent active learners (1 VU ≈ 50–100 real users),
degrades by latency and never crashes (**0 5xx at every level**), knee ~16–32 VUs then CPU-bound, peak
~300 rps. Tier 1/2/3 scaling roadmap confirmed against the measured ceiling with concrete move-up
triggers (`docs/deployment.md` § Concurrency & scaling model). Handoff report retained by the operator.

**Residual — non-blocking, operator config (NOT engineering):**
- **Verify proxy-IP rate-limit keying before driving real traffic.** The per-IP limiter keys on
  `request.client.host` (`routers/auth.py:233`); uvicorn derives that from `X-Forwarded-For` *only*
  when the immediate peer is in `--forwarded-allow-ips` (default `127.0.0.1`; the app never reads XFF
  itself). If Railway's hop isn't `127.0.0.1`, every client collapses into one 60/min bucket → mass
  429s under launch load. **Check:** Railway logs for `client_ip=` (request-context middleware logs it)
  — diverse public IPs = fine; one repeated internal/proxy IP = collapsed → set `FORWARDED_ALLOW_IPS=
  <verified Railway hop>` (NEVER `*` — IP-spoofing hole). Dockerfile wiring already in place.
- **`MAX_CONCURRENT_HASHES` default** = cores−1 (favors auth-burst throughput); `cores/2` is a safer
  default if bystander latency during simultaneous-auth bursts matters. Kept as-is; operator's call.

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

## P2 — Revisit Interview Loop replay once the mock chain-pools are expanded ✅ DONE (2026-06-22)
Closed. All three thin cells were expanded (Statistics-hard ✅, SQL ✅, Pandas-medium ✅ 2→8 on
2026-06-22), then the keep-vs-scope-down decision was resolved: **redirect-first, replay demoted.**
The exhausted state now leads with a "Fresh chains to try" rail (`/access` → `fresh_loop_cells`,
requested track first) and demotes replay to a quiet secondary link; replay remains as the
no-dead-end fallback when every cell is exhausted. Rejected N-gates/cooldowns (manufactured
friction) and a hard dead-end (punitive). See `docs/decisions/DECISIONS.md` 2026-06-22 (redirect)
+ 2026-06-19 (original replay); `docs/features/mock.md` § Follow-up Chain Atomicity rule 6.

## P3 — Position Interview Loop as the earned capstone (benchmark → drill → Loop) ✅ DONE (2026-06-21)
Closed. The Loop is now framed as the **Benchmark → Drill → Loop** capstone across five surfaces:
MockHub hero + "How it works" modal (sequenced arc; explicit "a recommendation, not a gate"), the
Loop mode card / setup copy ("Your capstone — best after a benchmark and a drill or two"), a
`Suggested first` soft-nudge in the Loop setup rail when an Elite user picks a Loop on a track they
have not benchmarked, a dashboard readiness-chip **"Ready for a Loop →"** CTA, and a mock post-mortem
**"Try an Interview Loop →"** primary CTA. Backed by a new Elite-only `readiness_scores[track].loop_ready`
signal (`score ≥ 65` + ≥1 direct benchmark on the track). **Guardrails honored:** framing only — no
nudge ever disables Start; scarcity stays honest (finite chain pools), never manufactured (no cooldown
/ daily cap). Full why + rejected alternatives → `docs/decisions/DECISIONS.md` 2026-06-21; canonical
positioning spec → `docs/features/mock.md` § Interview Loop positioning.

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
