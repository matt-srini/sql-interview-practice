# Sandbox threat model

**Canonical source of truth** for what the user-code execution sandbox defends against, what each defense layer **does and does not** contain, and the known residuals. Anywhere else that describes the sandbox layers (`CLAUDE.md` § Sandbox security layers, `docs/deployment.md` § Sandbox security hardening, `docs/backend.md` § Python execution pipeline) is a **render of this doc** — link here, do not restate. The *why* behind each decision lives in [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) (grep `Area: sandbox`).

Runtime SoT (the code these layers live in): `backend/python_guard.py`, `backend/python_sandbox_harness.py`, `backend/python_evaluator.py`, `Dockerfile`.

---

## What runs untrusted code

Three tracks execute user-submitted Python in a subprocess sandbox: **Python (algorithm)**, **Pandas**, and **Statistics-numerical**. SQL runs in DuckDB (no Python sandbox); the MCQ tracks execute nothing. The entry path for the three is: endpoint → `python_guard.guard_detail()` (reject at 400 if it fails) → `python_evaluator._spawn_harness()` → `python_sandbox_harness.py` in a scrubbed, resource-capped, seccomp-filtered subprocess.

**Core assumption: the in-process AST guard is best-effort, not a boundary.** Safely sandboxing untrusted Python *in-process* is not achievable by denylisting — the object graph is too connected (a single reachable `os`/`__globals__`/`sys.modules` defeats it). So the guard is the *first* layer, and the real boundary is the **OS-level** layers (scrubbed env, seccomp, RLIMITs, non-root read-only FS, and — pending — Landlock). Every claim below is scoped accordingly.

---

## The threat → layer map

| Threat | Contained? | By which layer | Notes |
|---|---|---|---|
| **Network egress** (phone-home, exfil, internal scan) | ✅ yes (Linux) | seccomp network filter (`_install_seccomp_filter`, preexec) denies `socket`/`connect`/`sendto`/… | Fails *open* if `pyseccomp`/`libseccomp2` absent — both are in the image + CI. |
| **Subprocess spawn** (`os.system`, `subprocess`) | ✅ yes | seccomp `execve`/`execveat` block (`_install_exec_block`, harness `main()`) **and** the restricted `__import__` deny of `subprocess`/`_posixsubprocess` | Two independent layers; either suffices. |
| **Secret theft via env** (`DATABASE_URL`, API keys) | ✅ yes | scrubbed subprocess env (`_sandbox_env`) passes only `PATH/HOME/LANG/locale/TMPDIR/TZ` + the BLAS pins | No secret is in the child's environment at all. |
| **Writing app code** (drop a backdoor) | ✅ yes | non-root `appuser` + root-owned `/app` (Dockerfile); only `/tmp` writable | `PYTHONDONTWRITEBYTECODE=1`. |
| **Memory / CPU / fork / disk bombs** | ✅ yes | RLIMITs (`AS` 512 MB, `CPU` 14 s, `NPROC` 256, `FSIZE` 64 MB) + wall timeout + process-group SIGKILL | See `docs/deployment.md` § Sandbox security hardening. |
| **Native-math RLIMIT_AS abort** (OpenBLAS over-reserve) | ✅ yes | BLAS thread pins in `_sandbox_env` (`OPENBLAS/OMP/MKL/NUMEXPR_NUM_THREADS=1`) | Not a security threat but a correctness/availability one; see DECISIONS 2026-06-26. |
| **Reaching `os`/`sys`/`__import__` via the guard** | ⚠️ **known vectors closed; not a proven boundary** | AST guard: blocks non-allowlisted imports, dangerous bare names, dangerous attributes **incl. re-export hops** (`_os`/`_sys`/`sys`/`os`/`modules`), and an explicit set of escape-gadget dunders in **string + bytes** literals (catches `operator.attrgetter('__globals__')`, `b'{0.__globals__}'.decode().format()`). Restricted runtime `__import__` denies native/IPC/deser modules. | The reproduced vectors (attrgetter, `random._os`, `typing.sys.modules`, bytes-format) are all blocked. A determined attacker can still reach `os` via the **introspection tail** (e.g. `attrgetter('sys')`+`attrgetter('modules')` — common-word strings can't be scanned without breaking legit code). |
| **Arbitrary file READ** (answer keys in `content/`, app source) | ❌ **NOT fully contained — top residual** | Only the guard's reach-vectors above; nothing at the OS level restricts file reads today. | **This is the priority residual.** Once `os` is reached, `os.open` reads any `appuser`-readable file, and the value is **exfiltrated via the run-code response body** (`solve()`'s return is echoed to the client), so the network block does not help. Closure = **Landlock** (below). |

---

## The exfiltration nuance (why file-read is the priority)

A run-code response echoes `solve()`'s return value (or the resulting DataFrame) back to the client. So an attacker does **not** need network egress to exfiltrate: returning file contents as the solve output leaks them on the legitimate HTTP response. This is why the *network* seccomp block, while correct, does not mitigate the file-read residual — and why **filesystem read-scoping (Landlock) is the highest-value remaining hardening**, above any further in-process guard patching.

The most product-relevant target is `backend/content/**` (the practice/mock **answer keys**): reading the expected answer for the current question defeats grading integrity directly, with no network needed.

---

## Residuals & roadmap

| Residual | Closure | Status |
|---|---|---|
| Arbitrary file-read via the in-process introspection tail | **Landlock** (Linux ≥5.13) filesystem read-scoping in the harness: allow-read the Python runtime + site-packages + the datasets dir + `/tmp` (rw), deny everything else (incl. `content/**` and app source). | ⏳ **planned (next security iteration)** — needs Railway-kernel verification; fails *open* if the kernel lacks Landlock, so it must log its active/inactive state at startup. |
| In-process guard is best-effort | (Accepted) The guard is defense-in-depth; the boundary is the OS layers + Landlock. New escape vectors are added to `tests/test_guard_redteam.py` as found. | accepted |

---

## Test coverage

| Layer | Test |
|---|---|
| AST guard (incl. the 2026-06-26 escape vectors) | `tests/test_guard_redteam.py` |
| Restricted `__import__` + seccomp exec-block | `tests/test_sandbox_runtime_hardening.py` |
| seccomp network filter | `tests/test_sandbox_seccomp.py` (Linux) |
| RLIMITs (AS/CPU/NPROC/FSIZE) | `tests/test_sandbox_resource_limits.py` (Linux) |
| Scrubbed env + BLAS pins | `tests/test_sandbox_env_isolation.py` |
| OpenBLAS RLIMIT_AS abort (high-thread repro) | `tests/test_sandbox_openblas_pin.py` (Linux) |

The Linux-gated tests are skipped on macOS dev and are the reason a hardening change **must be CI-validated on a branch before landing** — several layers (RLIMITs, seccomp) only exist on Linux, and security tests probe them by importing `os`/`socket`/`resource` inside the sandbox (so those modules are deliberately *not* in the runtime import-deny).

---

## Related

- [`docs/audits/sandbox-PRR.md`](../audits/sandbox-PRR.md) — the **Sandbox PRR** index: the full code-execution-sandbox hardening pass this security layer is one axis of (findings, fixes, and decisions across security / reliability / scalability / observability).
- [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) — the *why* (2026-06-26 entries: BLAS pin; guard-escape hardening + Landlock-deferred; cgroup concurrency + correctness oracle).
- [`docs/deployment.md`](../deployment.md) § Sandbox security hardening — the OS-layer / Railway-equivalents table.
- [`docs/backend.md`](../backend.md) § Python execution pipeline — the runtime data flow.
