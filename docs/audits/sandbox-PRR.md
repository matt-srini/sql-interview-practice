# Sandbox PRR — code-execution sandbox production-readiness review (2026-06-26)

**What this is.** A single index for the pre-launch hardening pass over the **code-execution sandbox** — the subsystem that runs untrusted user Python / Pandas / Statistics in a subprocess. Referred to interchangeably as the **Sandbox PRR** (*production-readiness review*), the **code-execution sandbox hardening**, or the **sandbox audit**. This doc **links** to where each piece lives; it does not restate them (single-SoT rule). It exists so "everything we did in the sandbox PRR" has one place to point to.

**Scope — four axes, one subsystem.** "Infra/scalability" undersells it: scalability was one axis of four. The through-line is the sandbox, audited across **security · reliability · observability · scalability**, plus the **test methodology** that should have caught it.

---

## Trigger

A production Pandas execution failed with `OpenBLAS error: Memory allocation still failed after 10 retries, giving up` — a launch blocker. Root-causing it surfaced that the failure was **invisible** to both Sentry and the 2026-06-08 load test, which opened a full production-readiness review of the sandbox rather than a one-line patch.

---

## Findings & fixes (by axis)

| # | Finding | Axis | Severity | Status | Where it lives |
|---|---|---|---|---|---|
| 1 | OpenBLAS `RLIMIT_AS` abort on numpy paths (per-core BLAS buffer pool exceeds the 512 MB cap on many-core hosts) | Reliability | Launch-blocker | ✅ Fixed — BLAS thread pins in `_sandbox_env` | [DECISIONS](../decisions/DECISIONS.md) "Pin sandbox BLAS thread pools"; [threat-model](../specs/sandbox-threat-model.md) |
| 2 | Harness infra-failures returned as HTTP 200 `{error}` body → invisible to Sentry (0 hits/90 d) | Observability | High | ✅ Fixed — `capture_sandbox_failure` (error-level, `alert=sandbox_failure`) | `backend/sentry_utils.py`, `backend/python_evaluator.py` |
| 3 | **AST guard bypassable → arbitrary file-read + subprocess, exfiltrable via the response body** (`operator.attrgetter('__globals__')`, `random._os`, `typing.sys.modules`, bytes-literal format) | Security | **Critical (verified)** | ✅ Hardened (defense-in-depth); file-read residual → Landlock | [threat-model](../specs/sandbox-threat-model.md); [DECISIONS](../decisions/DECISIONS.md) "Harden sandbox vs guard-escape" |
| 4 | `.dockerignore` did not exclude `*.env` → a non-git build could bake the prod `DATABASE_URL` into the image | Security | Medium (latent) | ✅ Fixed — `*.env` excluded | `.dockerignore` |
| 5 | `MAX_CONCURRENT_EXECUTIONS` default from `os.cpu_count()` over-reports host cores in a container → semaphore + peak sandbox RAM inflate (≤31 GB on a 64-core host) | Scalability | High (latent) | ✅ Fixed — cgroup-aware `effective_cpu_count()` | [DECISIONS](../decisions/DECISIONS.md) "cgroup-aware concurrency"; [deployment](../deployment.md) § Concurrency & scaling model |
| 6 | The 2026-06-08 load test reported "no blockers" but could not see any of this | Test methodology | High | ✅ Fixed — pandas/stats journeys + **correctness oracle** + deterministic OpenBLAS CI repro | `backend/loadtest/`, `tests/test_sandbox_openblas_pin.py`; [deployment](../deployment.md) scope caveat |
| 7 | No single doc described the sandbox threat model (what each layer contains / doesn't) | Documentation | Medium | ✅ Fixed — canonical threat-model doc + this index | [threat-model](../specs/sandbox-threat-model.md) |
| 8 | Arbitrary file-read via the in-process introspection tail (the hardening narrows it; the guard can't close the class) | Security | **Critical (verified)** | ✅ **Closed by Landlock** (`landlock_sandbox.py`, CI-validated) — prod-active pending the Railway boot-log check | [threat-model](../specs/sandbox-threat-model.md) § Residuals; `tests/test_sandbox_landlock.py` |

---

## The verified escape (security highlight)

The guard is a denylist over AST shapes; runtime-string attribute access (`operator.attrgetter('__globals__')`) and re-exported modules (`random._os`, `typing.sys.modules['os']`) sidestep it. Reproduced live: the escape read `backend/content/**` (the practice/mock **answer keys**) and `/etc/passwd`, **exfiltrated on the run-code response body** — so the network seccomp block does not mitigate it. The hardening (string/bytes escape-gadget scan + re-export attribute blocks + restricted runtime `__import__` + seccomp `execve` block) closes every reproduced vector and robustly closes subprocess; **arbitrary file-read is now closed by Landlock** (#8 — landed + CI-validated; prod-active pending the boot-log check). Full layer-by-layer model: [`docs/specs/sandbox-threat-model.md`](../specs/sandbox-threat-model.md).

---

## Why it was invisible (the methodology lesson)

The same blind spot hid the bug from **both** Sentry and the load test: the failure crossed no capture threshold. It returned a fast HTTP 200 with an `{error}` body — not a 5xx, not an exception, not an ERROR log. The 2026-06-08 load test missed it on three independent axes, all now closed:

1. **Workload** — its one code-exec journey submitted a Python-algorithm `def solve(): return None`, which never imports numpy. The numpy/pandas paths were never exercised. → pandas/stats journeys added.
2. **Oracle** — it scored any non-5xx as "ok", so a 200-with-`{error}` looked healthy. → correctness oracle (assert `body.correct`).
3. **Environment** — it ran on a small-core box where the BLAS buffer pool fit under the cap. → deterministic CI repro forces the many-core condition (`OPENBLAS_NUM_THREADS=32` + tight `RLIMIT_AS`).

Carried forward into the tier roadmap as two standing properties (execution-correctness + sandbox-resource sizing): [`docs/deployment.md`](../deployment.md) § Concurrency & scaling model.

---

## Decisions (the *why* layer)

All in [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) (grep `Area: sandbox`), 2026-06-26:

- **Pin sandbox BLAS thread pools to 1; log harness non-zero exits** — rejected raising `RLIMIT_AS` (it's the load-bearing memory-bomb guard).
- **Harden sandbox vs guard-escape file-read/RCE (defense-in-depth; Landlock deferred)** — rejected an airtight in-process guard (impossible) and listing `os`/`sys` in the runtime import-deny.
- **Sandbox PRR: cgroup-aware concurrency default + load-harness correctness oracle** — rejected `sched_getaffinity` (ignores the CFS quota).

---

## Tests added / extended

`tests/test_guard_redteam.py` (new escape vectors), `tests/test_sandbox_runtime_hardening.py` (restricted `__import__` + exec-block), `tests/test_sandbox_env_isolation.py` (BLAS pins), `tests/test_sandbox_openblas_pin.py` (deterministic OpenBLAS abort repro, Linux-gated), `tests/test_effective_cpu_count.py` (cgroup quota). All Linux-gated sandbox tests are **CI-validated on a branch before landing** — several layers exist only on Linux.

---

## What's left

**Landlock is implemented + CI-validated** (`landlock_sandbox.py`, `tests/test_sandbox_landlock.py`): on a Landlock-capable kernel the sandbox cannot read `content/**` or app source, and pandas/numpy still execute. The **one open item** is a deploy-time check — Landlock is a kernel feature and fails *open*, so confirm it is actually active on **Railway's** host kernel via the boot-log line `Sandbox Landlock FS read-scope: available (ABI vN)` (a `... UNAVAILABLE ...` WARNING means the kernel lacks it; CI proves the code, but GitHub's kernel ≠ Railway's). Tracked in [`docs/specs/sandbox-threat-model.md`](../specs/sandbox-threat-model.md) § Residuals.

## SoT map

| Concern | Source of truth |
|---|---|
| Sandbox threat model (layers, residuals) | [`docs/specs/sandbox-threat-model.md`](../specs/sandbox-threat-model.md) |
| Concurrency, scaling, RAM sizing, tier roadmap | [`docs/deployment.md`](../deployment.md) § Concurrency & scaling model |
| OS-layer hardening table | [`docs/deployment.md`](../deployment.md) § Sandbox security hardening |
| Execution pipeline (runtime data flow) | [`docs/backend.md`](../backend.md) § Python execution pipeline |
| The *why* of every decision | [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) |
| This index | `docs/audits/sandbox-PRR.md` |
