# 06 · Mock-only & interview loops — Product Sense

> Research/proposal. Follows [`content-authoring.md` §Mock-only authoring contract](../../content-authoring.md#mock-only-authoring-contract),
> [`docs/features/mock.md`](../../features/mock.md) (chain atomicity, Interview Loop), and the 8 universal
> follow-up dimensions in [`docs/concept-taxonomy.md`](../../concept-taxonomy.md). Mock content is
> *supplemental benchmark inventory*, never the curriculum (north-star: "Mock is a benchmark").

## §The subset rule — the governing constraint

**Mock must never introduce a concept the practice track hasn't already taught.** This is the load-bearing
rule for the whole package (and the user's explicit requirement). Concretely, for every mock-only question:

1. Its concept family/families must already be **taught in the practice bank at that difficulty or lower**
   ([`03`](03-concept-taxonomy.md) is the registry; [`04`](04-difficulty-split.md) is the per-tier
   placement). A mock-only `hard` question may recombine any family taught at practice hard *or* medium
   *or* easy — never a family the practice bank never covers.
2. It must **recombine**, not clone — a fresh, named-product scenario under stakeholder/time pressure that
   exercises *already-taught* reasoning. If a mock idea would need an untaught family, **author the
   practice question first** (or drop the idea).
3. Authoring order therefore is **practice-first, always**: the practice bank for a family must exist
   before any mock-only question leans on it. (This is why [`04`](04-difficulty-split.md) sizes practice
   to cover every family at the difficulty its mock questions will assume.)

This rule has teeth here because product-sense scenarios are *seductive* — it's easy to write a great
mock case that quietly relies on a reasoning move (say, synthetic-control intuition, or a specific
prioritisation framework) the practice bank never taught. The discipline: if the user could face a
concept in mock that practice never showed them, the question is invalid, however good it reads.

## §What separates practice from mock-only

Per the cross-track contract, the difference is **framing and stakeholder realism, not new concepts**:

| | Practice | Mock-only |
|---|---|---|
| Job | *teach* the reasoning durably | *stress-test transfer* under pressure |
| Scenario | clean, instructional, one concept foregrounded | a fresh real-product situation, mid-decision, with a human pushing |
| Anchor | the concept | the moment ("the PM wants to ship in 3 days and the read conflicts") |
| New concepts? | yes — this is where they're introduced | **never** |

A strong product-sense mock-only question reads like a slice of a real Analytical-Execution round:
*"Reels watch-time is +4%, original-post creation is −2%, ads-revenue-per-session is flat after 9 days,
and leadership wants a Friday decision — what's your call?"* — every reasoning move in it
(conflicting-metric judgment, guardrail logic, novelty suspicion, ship decision) was taught separately in
practice; mock recombines them under time pressure.

## §Mock-only composition — the two draw surfaces (`mock-standalone` vs `mock-chain`)

Sized in [`04`](04-difficulty-split.md): **~100 mock-only (0 easy / ~45 medium / ~55 hard)**, ratio ≈1.15×.
The mock-only pool is **not one pool** — it splits into two *draw surfaces* that different session modes
consume, and which the balance validators group **separately**:

| Sub-pool | ~Count (E / M / H) | Drawn by | Shape |
|---|--:|---|---|
| **`mock-standalone`** | **~70** (0 / ~33 / ~37) | **Benchmark** + **Custom** (Pro+) | self-contained single questions |
| **`mock-chain`** | **~30 members** from **~10 chains** (parent + ~2 follow-ups) | **Interview Loop** (Elite) only | atomic parent→follow-up chains |
| **Total mock-only** | **~100** | | |

This split is **load-bearing for balance, not bookkeeping.** A session draws from exactly one surface (a
Benchmark never serves a chain; a Loop serves only chains), so a biased chain pool is invisible if you
average it into the combined `mock` group — the **dilution trap** that once hid a 15/15
"correct-is-longest" chain batch behind a clean combined number. Therefore:

- Author and balance-check **each surface on its own**: run `check_batch_balance.py` on the standalone
  batch *and* on the chain batch separately (position ≤40%, unique-longest ≤45%).
- Per the cross-track validator state, the `mock-chain` group starts **WARN-level** and is promoted to
  ERROR only after the chain pool is debiased — so plan the chain batch to clear that bar from the start.

**Anchoring families** (where stakeholder pressure adds the most signal), each ≤ the cross-track ~50%
ceiling *per surface*:

- `SHIP / NO-SHIP DECISION` — the canonical "decide under pressure" mock surface.
- `CONFLICTING-METRIC & TRADE-OFF JUDGMENT` — two-sided / competing-goal tension.
- `METRIC MOVEMENT DIAGNOSIS` + `SEGMENTATION & DECOMPOSITION` — "investigate this drop, now."
- `METRIC GAMING & ROBUSTNESS` + `PRODUCT HEALTH & STRATEGIC TRADE-OFFS` — hard-tier strategic recombination.

**Type mix** (both surfaces, the `type` values from [`02`](02-track-design.md)): `scenario`-heavy (~70%,
the Experimentation precedent) + `debug` (a flawed product/metric argument to fix) + a little
`predict_output` (forward outcome prediction). No `conceptual` skew at medium/hard (the round is
situational). Chains are **scenario-led** (the interviewer-dialogue shape).

## §Benchmark shape per difficulty (proposed)

Derived from the on-disk bank (bank shape governs blueprint), scenario-led. A plausible starting target —
to be set against the real bank once authored:

| Difficulty | Blueprint (6 slots) |
|---|---|
| Easy | `scenario × 3 + conceptual × 2 + predict_output × 1` (no `debug` if the easy bank has too few) |
| Medium | `scenario × 4 + debug × 1 + predict_output × 1` |
| Hard | `scenario × 4 + debug × 2` |

Final shape follows the bank — never author a type just to fill a slot
([mock-benchmark-spec](../../specs/mock-benchmark-spec.md) §Blueprint feasibility).

## §Interview-loop chains

**Chains appear only in Interview Loop sessions** (Elite). A chain is a parent + 1–3 follow-ups that travel
as one **atomic** unit (consumed at session start, single-track, per-user lifetime at-most-once; the
contract is owned by [`mock.md`](../../features/mock.md), don't restate the gates). Product sense is an
*excellent* fit for chains — the real Analytical-Reasoning round literally *is* an interviewer adding
constraints mid-conversation ("…now suppose creator satisfaction also dropped…"), which is exactly the
chain shape.

**Dimensions used:** the existing **8 universal pivots** unchanged (the audit confirmed they cover
product-sense escalations — no new dimension needed). Consecutive follow-ups must differ; `performance_pivot`
is the least natural here (the round isn't compute-bound) and should be rare. The richest pivots for this
track are `business_rule_pivot` (the goal/definition changes), `stakeholder_pivot` (a human with an agenda
pushes), `data_quality_pivot` (a logging gap surfaces), `ambiguity_pivot` (a term is left undefined), and
`scale_pivot` (now across many markets).

### Proposed chain designs (8 shown · target ~10)

The 8 below are illustrative; the **`mock-chain` sizing target is ~10 chains (~30 members)** — the
Experimentation precedent (10 chains / 30 members / 29% of mock-only). Each is a parent (no
`follow_up_dimension`) + an ordered pivot sequence. Every member's concept family is already taught in
practice (subset rule).

| # | Parent (anchor) | Pivot sequence | Families exercised |
|---|---|---|---|
| 1 | "Pick the success metric for a new 'Save for later' feature." | → `business_rule_pivot` (goal changes from adoption to retention) → `stakeholder_pivot` (exec wants to ship on the adoption number anyway) | METRIC SELECTION → GUARDRAIL & COUNTER-METRIC → SHIP/NO-SHIP |
| 2 | "Daily orders dropped 6% on Tuesday — first move?" | → `segmentation` via `edge_case_pivot` (the drop is 0.5% of users in one region) → `data_quality_pivot` (a logging gap overlaps the window) | METRIC MOVEMENT DIAGNOSIS → SEGMENTATION & DECOMPOSITION → REAL-CHANGE VS ARTIFACT |
| 3 | "+5% bookings, −2% repeat-rate, flat NPS after 10 days — ship?" | → `business_rule_pivot` (the guardrail threshold just changed) → `scale_pivot` (now decide for 30 markets at once) | SHIP/NO-SHIP → CONFLICTING-METRIC → PRODUCT HEALTH & STRATEGIC TRADE-OFFS |
| 4 | "Design a 'creator health' metric for a content platform." | → `abstraction_pivot` (generalise the *class* of metric that's always gameable this way) → `stakeholder_pivot` (growth team objects it slows their number) | METRIC GAMING & ROBUSTNESS → PRODUCT HEALTH → CONFLICTING-METRIC |
| 5 | "Engagement +8%, creator satisfaction −2% on a feed change — launch?" | → `ambiguity_pivot` ("define 'creator satisfaction' — I won't") → `scale_pivot` (the effect differs by creator tier at scale) | CONFLICTING-METRIC → METRIC DEFINITION INTEGRITY → SEGMENTATION & DECOMPOSITION |
| 6 | "Marketplace sellers who list on weekends sell 30% more — bonus them?" | → `business_rule_pivot` (now they want it as a permanent policy) → `data_quality_pivot` (weekend listings are mostly one high-GMV category) | CAUSAL VS CORRELATIONAL → SHIP/NO-SHIP → SEGMENTATION & DECOMPOSITION |
| 7 | "DAU/MAU is 0.18 for this app — good?" | → `business_rule_pivot` (compare it now to a *daily-utility* product) → `edge_case_pivot` (the ratio is propped up by notification re-engagement) | ENGAGEMENT & STICKINESS → BUSINESS-MODEL METRIC FLUENCY → METRIC GAMING & ROBUSTNESS |
| 8 | "Define success for a feature whose goal is to *reduce* time spent." | → `ambiguity_pivot` (what's 'good' engagement here?) → `stakeholder_pivot` (ads team's revenue metric falls — defend the trade-off) | PRODUCT HEALTH & STRATEGIC TRADE-OFFS → METRIC SELECTION → CONFLICTING-METRIC |

**Authoring discipline for chains:** the parent earns the chain (it must be a genuinely strong standalone
hard/medium question); each follow-up escalates exactly one dimension; no two consecutive pivots share a
dimension; chain length 2–4 (parent + 1–3). Per the spec, chains are mock-only and never enter a
pattern-path. Difficulty is same-or-escalating along the chain.

### Time + availability

Loop time = **15 min × chain length** (standard). For a track this scenario-heavy, a 3-question chain
(45 min) is the sweet spot — enough room for the interviewer-dialogue feel without becoming a take-home.
Chain availability per difficulty is derived from the authored bank (medium and/or hard), never hardcoded
— same as every track.
