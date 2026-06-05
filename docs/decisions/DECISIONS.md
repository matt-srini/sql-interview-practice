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
