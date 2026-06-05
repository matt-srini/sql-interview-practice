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

## 2026-06-05 — Adopt an append-only decision log (this file)
**Area:** process · **Status:** accepted
**Decision:** Capture the *reasoning* layer in a single append-only, topic-tagged, never-expiring `docs/decisions/DECISIONS.md`, consulted on demand via a `CLAUDE.md` trigger and a one-line memory pointer — not auto-loaded every session.
**Rejected:** (a) A daily `history/` log on a rolling 2-week/1-month window — time is the wrong retrieval index, and expiry deletes exactly the *old* decisions that cause re-litigation. (b) Storing the decision archive in Claude memory — its index loads every session, so a growing log would tax every turn whether relevant or not; memory holds only the pointer. (c) Relying on commit messages alone — change-indexed not decision-indexed, can't be marked superseded, and rejected alternatives rarely survive.
**Affects:** CLAUDE.md (standing instruction + doc-mapping row), docs/README.md, memory (`decision_log.md` + index pointer).
