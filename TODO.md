# TODO — open workstreams

Durable backlog of work that is scoped but not yet done. The **why/what-was-rejected** for
finished decisions lives in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md); this
file is the forward-looking **what's-left**. Detailed, paste-ready Opus session prompts for the
two big items are saved under [`docs/backlog/`](docs/backlog/).

---

## P1 — Load & concurrency readiness  (bites the moment there are 2 concurrent users)
**Prompt:** [`docs/backlog/session-concurrency-load.md`](docs/backlog/session-concurrency-load.md)

The platform has only ever been tested single-user; there are **no load tests and no
multi-user flow simulation**. Two intertwined deliverables:
- **Head-of-line blocking (the known P0 inside this):** every code-exec endpoint is `async def`
  but calls its **blocking** evaluator directly (`return run_python_code(...)`, no
  `await asyncio.to_thread`), so a 5–12 s execution stalls the whole event loop → all requests
  freeze. The concurrency semaphore added this cycle (`main._execution_semaphore`,
  `MAX_CONCURRENT_EXECUTIONS`) is therefore largely cosmetic. Fix = offload to a thread inside
  the semaphore across all 6 code-exec endpoints (questions / python / pandas / statistics
  / sample / mock); subprocess paths are safe concurrently, **SQL/DuckDB is in-process →
  serialize behind a lock**.
- **The load-test capability we don't have:** simulate N concurrent virtual users running real
  flows (anon browse → register → solve-with-code → mock session → dashboard); measure the
  ceiling (throughput, p50/p95/p99 latency, error rate, Postgres pool / subprocess saturation);
  map a tiered scaling roadmap (config → replicas → externalized execution workers).
- Sequence: build the harness + baseline FIRST, then fix, then re-measure.

## P1 — Launch-readiness audit  (the dimensions not yet swept)
**Prompt:** [`docs/backlog/session-launch-readiness.md`](docs/backlog/session-launch-readiness.md)

Security (sandbox + entitlements) and content correctness are done and CI-validated. Still
unaudited: **payments correctness under failure** (webhook idempotency, double-charge,
plan-transition edge cases), **observability/alerting** (is anything paging on error-rate /
failed payments?), **deployment/rollback**, **legal/compliance** (privacy, ToS, GDPR deletion,
email deliverability). Verify against real code, prioritize P0/P1/P2, stop before fixing.

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
**Node.js 20**. GitHub forces Node 24 as the runner default on **2026-06-16** and removes
Node 20 from the runner on **2026-09-16** (per the deprecation notice in the CI logs). Today
it is only a warning — CI passes green. Fix when convenient: bump those actions to versions
that ship Node 24 (newer `checkout`/`setup-python` patch tags already do), or temporarily set
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` on the job. Recorded so the September removal doesn't
silently break CI.

---

### Config notes (operator)
- Railway: `MAX_CONCURRENT_EXECUTIONS=6` is set (8 vCPU − 2). Replica Memory left at the 8 GB
  plan max (billed on actual usage; gives OOM headroom above app + 6×512 MB sandbox peak).
- Sandbox egress filter needs `libseccomp2` (Dockerfile) + `pyseccomp` (requirements) — fails
  open if absent. The one remaining infra item is already done.
