# Decision Log

The **why** layer for this platform. The `docs/` files record *what is true now* (the "is"); this file records *why it's true and what we rejected* (the reasoning). They are complementary — never duplicate a doc's content here; link to it instead.

This log exists to kill three recurring failures: decisions evaporating when a session closes, nuances never reaching the docs, and **A→B→A oscillation** — re-deciding something weeks later because the original rationale (and the alternatives already rejected) was never written down.

---

## How to use this file

**Read it** — before *reversing or re-deciding* anything in a load-bearing area: architecture, content gating / unlock rules, the mock contract, pricing, the concept taxonomy, or any per-track curriculum framing. Grep by `**Area:**` tag or keyword first. If a prior entry already settled the question, honor it or supersede it deliberately — don't silently re-litigate.

**Write it** — after any *meaningful or direction-changing* decision, append an entry. The entry rides in the **same commit** as the change it describes (tie it to the existing "commit after meaningful changes" habit). Not every commit needs one — only those that carry a real decision, a rejected alternative, or a reversal.

**Never edit a past entry.** Append-only. To change a decision, add a *new* entry at the top whose `Status:` is `accepted` and that names the entry it **Supersedes**; flip the old entry's `Status:` to `superseded` (the one allowed edit — a single status word) and nothing else. The full chain stays visible: that's what prevents oscillation.

**Never expire.** Old decisions are the dangerous ones — they cause the most re-litigation. We archive, we do not delete. When this file passes ~1500 lines, move the oldest entries to `docs/decisions/archive-<year>.md` (same pattern as `docs/archive/`).

**Index, don't expand.** This is the index of *why*. The durable *rule* still lives in its source-of-truth doc (`docs/...`, the authoring agent, a track doc). Every entry links to where the rule landed via `**Affects:**`.

### Entry template

```markdown
## YYYY-MM-DD — <short imperative title>
**Area:** <architecture|content|gating|mock|pricing|taxonomy|frontend|ops|process|...> · **Status:** accepted
**Decision:** <the call, in one or two sentences>
**Rejected:** <the alternative(s) considered and why they lost — the most important line>
**Affects:** <docs/path.md, file, or "none — reasoning only">
**Supersedes:** <YYYY-MM-DD entry title, only if this reverses a prior decision>
```

Keep entries to 4–6 lines. Friction kills logs; if it's longer than the change deserves, it won't get written. Newest entry on top.

---

## Entries

## 2026-06-08 — Make SQL grading sound under ORDER BY ties and float aggregation
**Area:** architecture · **Status:** accepted
**Decision:** Order-sensitive SQL comparison is now **tie-tolerant**: a result is correct iff it has the same row multiset AND the same sequence of `ORDER BY` *key* values as the reference (rows tied on the key may permute) — `_results_match` / `_parse_order_by_columns` in `evaluator.py`. Separately, the grading DuckDB connection runs **single-threaded** (`SET threads TO 1`) so float aggregation is deterministic. Together these remove a live false-negative: 18 questions whose `ORDER BY` was not a total order, and 2 whose `ROUND`ed aggregate jittered across runs, marked correct answers (incl. the reference graded against itself) wrong a large fraction of the time. Surfaced by the new `test_code_references.py` guard.
**Rejected:** (a) **Full-row positional comparison** (the prior behaviour) — assumed every `ORDER BY` is a total order, nondeterministic on ties. (b) **Sort all rows before comparing** (pre-refactor behaviour) — would re-accept genuinely misordered answers. (c) **Per-question `ORDER BY` tiebreakers** for the 18 — content whack-a-mole that leaves the grader fragile for future questions. (d) **Float comparison tolerance** for the jitter — too loose (would accept near-but-wrong values); single-thread determinism fixes the root cause at negligible cost (≤9k-row datasets).
**Affects:** backend/evaluator.py, backend/database.py, backend/tests/test_sql_grading_tie_tolerance.py, backend/tests/test_sql_grading_determinism.py, docs/backend.md, CLAUDE.md.

## 2026-06-08 — Promote execution-based reference checks into standing CI guards
**Area:** process · **Status:** accepted
**Decision:** Wired the deterministic layer of the offline `audit_code_tracks.py` sweep into CI as pytest guards: `test_code_references.py` (every SQL + Pandas reference executes, is non-degenerate, `solution_*` reproduces `expected_*`, Pandas `schema` matches CSV header order) and `test_generator_reference_budget.py` (every `compute:reference` generator reference finishes within budget). Closes the gap where SQL/Pandas references — which grade *live*, so the content validator has no stored answer to check — could ship crashing/empty/wrong (the largest content-fix class of the 2026-05/06 refactor). Two pre-existing degenerate-empty SQL questions (12030, 13025) are quarantined as non-strict xfail pending an authoring-agent fix.
**Rejected:** (a) **Leaving the checks offline** in `audit_code_tracks.py` (run only during audits) — a new question could silently reintroduce the class. (b) **A Pandas-only guard** — the same hole existed for SQL (its references were never CI-executed either), so the guard spans both code tracks. (c) **An MCQ explanation-vs-key numeric heuristic** (the dropped H6) — false-positive-prone; the Reject-on-sight doc rule carries it instead.
**Affects:** backend/tests/test_code_references.py, backend/tests/test_generator_reference_budget.py, docs/content-authoring.md § Validator coverage state.

## 2026-06-07 — Debias MCQ answer keys on two axes (position + length), in content, gated by a blind re-audit
**Area:** content · **Status:** accepted
**Decision:** Removed two answer-key tells across every MCQ group (practice/mock/sample): correct-option **position** (was up to 100% one letter — fixed to ≤40% via a deterministic permutation + explanation "Option X" letter-remap) and correct-option **length** (was 82–96% "pick the longest" — fixed to ≤45% by trimming over-detailed correct options to mid-pack). Two new ERROR validators (`_validate_answer_position_balance`, `_validate_answer_length_balance`) enforce both forever.
**Rejected:** (a) **Serve-time option shuffle** — 79–97% of explanations reference "Option X" by letter, so runtime shuffling needs fragile prose surgery across 3 submit paths and desyncs on non-canonical phrasing; chose stored re-key. (b) **Wholesale de-letter of explanations** — would blind the `_validate_correct_option_explanation_consistency` key-inversion guard bank-wide; chose mechanical letter-remap that keeps it working. (c) **Forcing length to uniform 25% / lengthening distractors first** — risks answer-uniqueness. Governing rule: **uniqueness beats debiasing** — trim the correct option first (can't create a 2nd correct answer), re-pass every changed question through a GPT-5 blind re-audit, revert any trim-induced flip to audited text, leave-and-flag anything not debiasable safely.
**Affects:** backend/scripts/validate_content.py (2 validators + main()), backend/scripts/rebalance_phase1_positions.py, backend/scripts/audit_blind_answer_openai.py (sample support), docs/content-authoring.md, .github/agents/question-authoring.agent.md, CLAUDE.md.

## 2026-06-05 — Raise SQL guard MAX_JOINS 5 → 9
**Area:** architecture · **Status:** accepted
**Decision:** Raise `sql_guard.MAX_JOINS` from 5 to 9 (allow up to 8 joins anywhere in a query). The join *count* is not the cost driver on the small committed datasets (≤45k rows) — cost is already bounded by the 3s query timeout, the cartesian-join check, and the result caps. A cap of 5 wrongly rejected legitimately-hard analytics questions *and the platform's own reference solutions* (13018/13021/13024), and blocked the natural EXISTS-cohort approach entirely.
**Rejected:** (a) Rewrite the 3 references to ≤4 joins only — leaves users guard-blocked on the natural multi-join solution and distorts 13021's EXISTS lesson. (b) Keep the cap — keeps hard SQL un-authorable above 4 joins. Over-joining is coached via the EXPLAIN-based efficiency note, not blocked.
**Affects:** backend/sql_guard.py; 13018/13024 references also CTE-cleaned (4/3 joins) as quality polish.

## 2026-06-05 — Grade code answers on the full result; display only a preview
**Area:** architecture · **Status:** accepted
**Decision:** Pandas and SQL grading compare the **full** result (capped only by a high safety bound: pandas `_MAX_DATA_RESULT_ROWS=100k`, SQL `MAX_GRADING_ROWS=100k`) and return only a ~200-row preview (`total_rows`/`truncated`) to the client. This decouples grading soundness from payload/render cost, so legitimately large per-row outputs (e.g. dropna over 45k rows) grade correctly and a query/answer that diverges only beyond row 200 is no longer mis-graded.
**Rejected:** (a) Keep capping the *graded* result (pandas 10k hard-error / SQL `head(200)`) — unsound (mis-grades) or unauthorable. (b) Re-scope large-output questions to aggregates — distorts per-row lessons (esp. transform-vs-aggregate). Datetimes are ISO-serialized + date-normalized (not re-scoped) for the same "fix the platform, not the curriculum" reason.
**Affects:** docs/backend.md, docs/tracks/pandas.md, docs/tracks/sql.md; backend evaluator.py / python_evaluator.py / python_sandbox_harness.py.

## 2026-06-05 — Adopt an append-only decision log (this file)
**Area:** process · **Status:** accepted
**Decision:** Capture the *reasoning* layer in a single append-only, topic-tagged, never-expiring `docs/decisions/DECISIONS.md`, consulted on demand via a `CLAUDE.md` trigger and a one-line memory pointer — not auto-loaded every session.
**Rejected:** (a) A daily `history/` log on a rolling 2-week/1-month window — time is the wrong retrieval index, and expiry deletes exactly the *old* decisions that cause re-litigation. (b) Storing the decision archive in Claude memory — its index loads every session, so a growing log would tax every turn whether relevant or not; memory holds only the pointer. (c) Relying on commit messages alone — change-indexed not decision-indexed, can't be marked superseded, and rejected alternatives rarely survive.
**Affects:** CLAUDE.md (standing instruction + doc-mapping row), docs/README.md, memory (`decision_log.md` + index pointer).

## 2026-06-06 — Sandbox security hardening: scrubbed env, AST guard expansion, concurrency cap
**Area:** security · architecture · **Status:** accepted
**Decision:** Three layered hardening decisions shipped together:
1. **Scrubbed subprocess env** (`_sandbox_env`): the user-code subprocess receives a minimal default-deny env (PATH/HOME/locale/TMPDIR/TZ + Python flags). All production secrets are absent by default-deny, not by explicitly excluding named secrets. Rejected: explicit per-secret blocklist — too brittle, new secrets would require code changes.
2. **AST guard: `_BLOCKED_NAMES` via `visit_Name`**: blocking dangerous names at the Name-load AST node closes dynamic-string constructions (`globals()['__builtins__']`) that the prior call-site-only check missed. Also closes the `getattr` dynamic-key bypass (old guard only caught `getattr(x, literal_constant)`, not `getattr(x, dynamic_key)`). The guard is tested by 34 red-team escape attempts (all blocked) + 13 legit snippets (no false positives). Rejected: a runtime allow-only namespace (e.g. `RestrictedPython`) — adds a dependency, harder to understand and audit; our AST check is readable and the env scrub is the real backstop.
3. **Global asyncio concurrency semaphore** (default 10, `MAX_CONCURRENT_EXECUTIONS`): caps concurrent code-execution calls across SQL/Python/Pandas. Cap sits after plan/lock checks and around the DuckDB/subprocess call only. Rejected: per-user semaphore — more complex, and the real bottleneck is system-level (DuckDB process + subprocesses), not per-user fairness.
**What remains (infra-only):** egress block (P0), read-only filesystem (P1), seccomp (P1) — documented in `docs/deployment.md` § Sandbox security hardening.
**Affects:** backend/python_evaluator.py, backend/python_guard.py, backend/main.py, backend/deps.py, backend/routers/questions.py, backend/routers/python_questions.py, backend/routers/python_data_questions.py, Dockerfile, docs/backend.md, docs/deployment.md, CLAUDE.md.

## 2026-06-06 — Sandbox egress/seccomp/read-only done in CODE, not Railway infra
**Area:** security · deployment · **Status:** accepted (supersedes the "infra-only TODO" note in the prior entry)
**Context:** The prior entry deferred egress block / seccomp / read-only-fs as "infra-only" pending Railway config. Research found Railway uses eBPF networking and grants **no NET_ADMIN, no `--security-opt`, no `--read-only`/`--tmpfs`** — the container-level forms are simply unavailable on the platform.
**Decision:** Implement the equivalents in code/image instead:
1. **Egress block + seccomp profile** → a per-process `pyseccomp` filter installed in the sandbox `preexec_fn` (`_install_seccomp_filter`), denylisting the network-syscall family. Unprivileged seccomp works (libseccomp sets NO_NEW_PRIVS on load). Denylist (not allowlist) so pandas/numpy file+compute syscalls are untouched — validated on real Linux (socket BLOCKED, file-read + numpy OK) and in CI. Does NOT block `execve` (subprocess must exec python after preexec).
2. **Read-only app dir** → Dockerfile leaves `/app` root-owned (drop the `chown` to appuser), run as non-root appuser → app readable/executable but not writable; only `/tmp` writable. The in-image equivalent of `--read-only`.
3. **Memory cap** → the ONLY remaining Railway-dashboard item (RLIMIT_AS already caps per-subprocess; container cap is belt-and-suspenders).
**Rejected:** (a) Wait for/contact Railway for egress+seccomp support — slower, uncertain, and the in-process filter is strictly better (per-sandbox, not whole-container). (b) Allowlist seccomp (default-deny) — breaks pandas/numpy (hundreds of syscalls); a network denylist is the right scope. (c) Move code execution to a separate no-egress worker service — larger architecture change, deferred unless the in-process filter proves insufficient.
**Affects:** backend/python_evaluator.py, backend/requirements.txt, Dockerfile, .github/workflows/ci.yml, backend/tests/test_sandbox_seccomp.py, docs/deployment.md, CLAUDE.md.

## 2026-06-06 — Category-3 (resource-exhaustion) hardening: killpg, NPROC/FSIZE, semaphore=cores-2
**Area:** security · architecture · **Status:** accepted
**Context:** Review of the "legit-but-abusive code" vector (infinite loops, memory/fork bombs, output floods) found the AST guard correctly *allows* these (they're resource abuse, not escapes) — so only runtime caps stop them — and two real gaps: (1) the `setsid()` "kills the whole tree" claim was false because `subprocess.run`'s timeout does `proc.kill()` on the single child, orphaning forked grandchildren past the timeout; (2) no `RLIMIT_NPROC`, so a fork bomb (under the assume-guard-bypassed model) was unbounded. Also surfaced: two "timeout" tests (tc093/tc104) used `import time` which the guard blocks first, so they tested guard-rejection, not the timeout.
**Decision:**
1. **Process-GROUP kill on timeout** — `_spawn_harness` switched from `subprocess.run` to `Popen` + `communicate(timeout)`; on timeout `_kill_process_group` does `os.killpg(SIGKILL)`. Makes `setsid()` effective; forked children die with the parent.
2. **`RLIMIT_NPROC` 256 + `RLIMIT_FSIZE` 64 MB** added; **`RLIMIT_CPU` 15→14 s** (just above the 12 s data wall).
3. **Concurrency semaphore default → cores − 2** (was fixed 10) — CPU headroom + bounds peak sandbox memory (concurrency × `RLIMIT_AS`), which the Railway RAM cap is sized above.
4. Fixed tc093/tc104 to real `while True: pass` loops; added `test_sandbox_resource_limits.py` (infinite loop, memory bomb, fork-bomb killpg, output flood, recursion — Linux-gated ones validated in CI + a throwaway production-image run).
**Rejected:** (a) seccomp-block `clone`/`fork` for the fork bomb — breaks numpy/BLAS threads (clone-based); `RLIMIT_NPROC` is the clean per-UID bound. (b) Separate sandbox UID for cleaner `RLIMIT_NPROC` semantics — needs the app to start as root / setuid, which the non-root Railway image avoids; a generous NPROC value with headroom is sufficient. (c) Lower the wall timeouts — risks failing legit slow-but-correct solutions; the group-kill + caps are the right lever, not a tighter clock.
**Railway note:** the container RAM cap is set under Settings → Scale → **Replica Limits** (Memory slider), sized above app baseline + semaphore × 512 MB; do not set it low (DuckDB loads datasets in-memory).
**Affects:** backend/python_sandbox_harness.py, backend/python_evaluator.py, backend/main.py, backend/tests/test_06_python.py, test_07_pandas.py, test_sandbox_resource_limits.py, docs/backend.md, docs/deployment.md, CLAUDE.md.
