# Track Phase 2 Orchestration Runbook

**Status:** durable orchestration doc (survives Phase 3 tracker deletion)
**Audience:** any Opus session picking up Phase 3 of the 2026-05 authoring refactor, or any future Phase 2 round for a new track added post-refactor. **All 9 Phase 2 rounds + both Phase 2.5 cycles (DM re-balance, ML BIAS/FAIRNESS new-family addition) closed 2026-05-26.** The transitional tracker (`docs/phases/2026-05-authoring-refactor.md`) will be archived to `docs/archive/` once Phase 3 ships; this runbook is the durable orchestration handbook and stays authoritative.

This is the **orchestration handbook**, not the contract. The contract (rules, philosophy, schemas) lives in the durable docs listed at the bottom. This doc captures the **process patterns** for running a track through Phase 2: how Stage A plans, how Sonnet executes Stage B, how Stage C audits — all the orchestration-level knowledge that doesn't fit in the contract docs and historically lived only in conversation context.

---

## 1. The three-stage process

| Stage | Who runs it | What it produces | Critical rule |
|---|---|---|---|
| **A — Pre-execution analysis** | Opus | Per-track decisions log + Sonnet handoff prompt | Plans, does not author. Locked decisions go into the handoff verbatim. |
| **B — Execution** | Sonnet (fresh session, model-gated) | New questions + remaps + validators clean + H1–H7 closeout commits | Executes the locked plan. Does not re-litigate Stage A decisions. Does not self-audit. |
| **C — Post-execution audit** | Opus (fresh session) | PASS / FAIL verdict against durable contract; remediation prompt if FAIL | Independent. No context from Stage A or Stage B. Verifies disk state, not hand-back claims. |

### Why stages are independent

Stage A and Stage C must be **separate Opus sessions**. If the same session that locked decisions also audits the execution, the audit is self-confirming — it reads against its own assumptions, not against the durable contract. Independence is the safeguard.

Sonnet (Stage B) must not produce its own Stage C verdict. Self-audited commits (e.g. a closeout titled "Phase 2 audit PASS") were a real failure mode in the DE/DM rounds — the `P1` procedural rule (`docs/content-authoring.md` § Phase 2 closeout doc-hygiene) was introduced to prevent recurrence.

---

## 2. Stage A — Pre-execution analysis playbook

### 2.1 Inputs the planner must read in full

In this order:

1. `docs/tracks/<track>.md` — **framing authority** for the track. "What this track trains" is canonical. If the track-doc's prose contradicts its own difficulty ladder, flag for user (do not silently reinterpret).
2. `docs/specs/practice-modality-spec.md` — terminology authority. `mcq` is never a valid question `type`; real type values are `conceptual`, `scenario`, `debug`, `predict_output`, `optimization`, `numerical`.
3. `docs/content-authoring.md` — full cross-track contract:
   - § The one test every question must pass.
   - § Concept-tag contract + § Tag lookup procedure (mandatory) + § Validator coverage state + § Per-family coverage discipline + § Phase 2 closeout doc-hygiene.
   - § Mock-only authoring contract + § Power-user runway sizing benchmark (precedent table — keep current).
4. `docs/concept-taxonomy.md` — track's family registry, blocklist, match patterns, the 7 universal follow-up dimensions.
5. `.github/agents/question-authoring.agent.md` — procedure, tag discipline, final checklist (includes per-family coverage discipline).
6. `docs/features/mock.md` — mock layer SoT.
7. `backend/concept_families.py` — track's registered families + `MOCK_ONLY_REALISM_FAMILIES`.
8. `backend/scripts/validate_content.py` — `_TAXONOMY_VALIDATED_TRACKS` membership; per-family coverage warnings.
9. `CLAUDE.md` — current state counts, § Platform position (the strategic resolver).

### 2.2 Six deliverables

**Deliverable 1 — Track Reality + Watch-Outs block.** Self-contained, formatted for the Sonnet handoff. Must include: on-disk counts (split by subtype if applicable), current practice:mock ratio, closest-precedent analog (with quoted precedent table), framing summary lifted from track-doc, current registry state (family count, orphan count, ⚡-scaffolding count), reject-on-sight anti-patterns specific to the track (≥4 named), adjacent-track tag bleed list (per § 2.5 below).

**Deliverable 2 — Registry expansion proposal (if needed).** Mandatory if the track's registered family count is materially incomplete relative to its on-disk concept space (precedent: Statistics started with 12 families + 84 orphan tag instances; Stage A Deliverable 2 expanded to 13 families with full pattern coverage before Sonnet authoring began). Proposes new families with name + definition + initial `members` list + initial `match_patterns` + practice-grounded-vs-realism designation + reasoning-depth justification. **User approval gates Sonnet authoring** — Sonnet must NOT author against an incomplete registry; the validator's silent-skip (now warning) would mask drift. **Pattern-shadow warning** (lesson from Stats Stage C): when authoring new patterns, walk the registry from top and check whether each new pattern substring-shadows an earlier-defined family. Stats Round 1 audit caught a `"variance"` substring shadow that mis-routed 11 tags; verify on disk during Stage A before locking the registry.

**Deliverable 3 — Practice gap analysis.** Read every practice question. Reconcile concept-tag coverage against the (post-expansion) registry. Identify concept-arc gaps that need practice additions BEFORE mock-only sizing is locked.

**Deliverable 4 — Existing mock-only anti-pattern audit.** Audit every existing mock-only question against: recombination rule, type/subtype-mix differentiation, anti-duplication, framing alignment. Report N keep / N edit / N replace with IDs and rationale per case.

**Deliverable 5 — Sizing + Structure lock.** Per-subtype where applicable:
- D5a. Target practice:mock ratio — defended against the precedent table.
- D5b. Mock-only difficulty split — defended against the precedent table.
- D5c. Type/subtype mix inside mock-only.
- D5d. Per-family target table (NEW): family count → fair-share per family → soft ceiling (50% per tier) → target practice + target mock-only per family → load-bearing families called out with reasoning-depth defence.
- D5e. Realism-family decision — path (i) designated family OR path (ii) no realism by design (defended).
- D5f. Chain policy — count + dimension mix. **Critical (lesson from ML Phase 2 Stage C F4): chain children count IN the locked mock-only total, NOT additive on top.** A target of 120 mock-only with 8 chains × (parent + 2 children) means: 8 parents + 16 children + 96 standalones = 120 total. The chain-member percentage anchor (see § 6.3 Chain-member % precedent — ~30%) drives chain SIZING within the locked total, not above it. Explicit Stage A handoff language should read: "Mock-only target N includes all chain members. Chain children are inside the count, not additive."

**Deliverable 6 — Sonnet handoff prompt.** See § 3 for the required format.

### 2.3 Pre-filled watch-outs framework (W1–WN)

Each track's Stage A pre-fills a watch-out list. These are pre-identified pitfalls the orchestrator has spotted that the planner should confirm/refute on inspection. The W-series typically includes:

- W1: ratio gap from contract band (sub-1.0× starting point if track Phase 2 is large).
- W2: closest-precedent analog by modality (e.g. PySpark for MCQ-response tracks; Python for code-graded tracks).
- W3: registry-completeness state (drives Deliverable 2 inclusion).
- W4: track-character call (e.g. type narrowness — DM only uses `conceptual` + `scenario`; ML decision on whether to introduce a new type).
- W5: adjacent-track tag bleed list (per § 2.5).
- W6: validator enforcement state (in/out of `_TAXONOMY_VALIDATED_TRACKS`; gates per-ITEM check selection).

Pre-identified W-blocks for the remaining open tracks live in § 7.

### 2.4 Pushback checklist (run before producing Deliverable 6)

- Does my sizing sit in the 1.0–1.5× band? Below 1.0× is a contract violation.
- Does my mock m:h split fall within or near the precedent table? If outlier, do I have a track-character reason?
- Did I lock the realism-family decision with track-specific reasoning, not just "follow precedent"?
- Did I lock any track-specific binary calls (W4-type decisions) with explicit defence?
- Did I audit ALL existing mock-only individually, or did I assume a clean keep-rate?
- Is my proposed type mix actually differentiated from practice, or is mock-only "more of the same"?
- Did I name the cleanest abstraction even if Sonnet will execute a less-clean one?
- Did I use real type values consistently — no `mcq` slipping in as a type?
- Did I include W5 reject-on-sight tag bleeds and the per-ITEM orphan-resolver one-liner (if track not in set) verbatim in the handoff?
- Did I include P1 and P2 procedural rules verbatim?
- Did I gate Sonnet on user approval where it should be gated (registry expansion per Deliverable 2)?

If any answer comes back soft, redo that deliverable before handing off.

### 2.5 Adjacent-track tag bleed list (Deliverable 1 sub-component)

Same family name across tracks does NOT mean shared registration. Adjacent tracks have natural-sounding family names that a Sonnet under cognitive load will reach for. Stage A enumerates 3–5 most likely bleeds for the target track by reading the registries of related tracks, and the list goes verbatim into the Sonnet handoff as reject-on-sight.

Pre-identified candidates for the open tracks live in § 7.

---

## 3. Stage B — Sonnet handoff format

### 3.1 Mandatory opening (verbatim from CLAUDE.md)

```
★ STOP — MODEL CHECK: this is a bulk question-AUTHORING + remap task and must run on Sonnet, not Opus (cost). Before doing ANYTHING, confirm the active model is Sonnet. If it is not, do not proceed — tell the user to switch the model to Sonnet, then resume. Do not author, edit, or commit anything until the model is Sonnet.
```

### 3.2 Required reads (track doc FIRST)

Sonnet must read in this order before any authoring:

1. `docs/tracks/<track>.md` — internalise the track's framing authority before writing. (Python-lesson rule from the 2026-05 refactor: when the track-doc framing wasn't internalised first, the executor drifted toward generic interview-bank shape.)
2. `docs/specs/practice-modality-spec.md` § Response mechanism is not a question type.
3. `docs/content-authoring.md` § Tag lookup procedure + § Per-family coverage discipline + § Phase 2 closeout doc-hygiene.

### 3.3 Per-ITEM checks (run after every chunk of 8–12 questions)

| Check | When mandatory | Tool |
|---|---|---|
| Orphan-resolver one-liner | Track NOT in `_TAXONOMY_VALIDATED_TRACKS` | Inline Python (pasted in handoff) |
| `validate_content.py` | All tracks | Standard validator |
| Per-family coverage warning scan | All closed-Phase-2 tracks; informational for in-progress tracks | Same validator (emits warnings) |

The orphan-resolver one-liner template (substitute `<TRACK>` and `<DIR>`):

```
python3 -c "
import json, sys; sys.path.insert(0, 'backend')
from concept_families import CONCEPT_FAMILIES, resolve_to_family
families = set(CONCEPT_FAMILIES['<TRACK>'].keys())
orphans = []
for diff in ['easy','medium','hard']:
    for q in json.load(open(f'backend/content/<DIR>/{diff}.json')):
        for t in q.get('concepts', []):
            if resolve_to_family(t, '<TRACK>') not in families:
                orphans.append((q['id'], t))
if orphans:
    print('ORPHANS:', orphans); sys.exit(1)
print('No orphans')
"
```

Rule: if orphans returned in an ITEM, fix in that ITEM before authoring the next. Do not accumulate drift.

### 3.4 Closeout (H-series H1–H7)

Sonnet executes the H-series as the CLOSING step of Stage B. The H-series is durable and lives in `docs/content-authoring.md` § Phase 2 closeout doc-hygiene. Summary (full text in the durable doc):

| H | Step |
|---|---|
| H1 | Orphan remap — final orphan-resolver returns 0. |
| H2 | Validator enable — add track slug to `_TAXONOMY_VALIDATED_TRACKS` with comment. Re-run validator. |
| H3 | Taxonomy strip — remove ⚡ markers from track section of `docs/concept-taxonomy.md`. |
| H4 | Track-doc Coverage section — add/update with practice + mock + ratio + splits + type mix + chain count + realism path. |
| H5 | Realism designation — set `MOCK_ONLY_REALISM_FAMILIES["<track>"]` in `backend/concept_families.py`. |
| H6 | IS-count sync — CLAUDE.md footprint + totals, `docs/content-authoring.md` § Question bank current state, precedent table row. |
| H7 | Tracker tick — `docs/phases/2026-05-authoring-refactor.md` row + decision log. |

### 3.5 Procedural rules (always include in handoff)

- **P1** — closeout commits must NOT self-title "audit PASS" or "PASS." Sonnet does not audit itself. Use descriptive titles like `Phase 2 closeout (H1–H7)`.
- **P2** — any durable-contract doc change outside the H-series scope MUST be surfaced in the hand-back summary BEFORE self-applying. Sonnet flags; user triggers separate doc-hygiene pass.

Full text in `docs/content-authoring.md` § Phase 2 closeout doc-hygiene.

### 3.6 Hand-back format

Sonnet must produce on completion:

1. Per-item / per-deliverable decision log with question IDs touched.
2. Files changed (with insertion/deletion counts).
3. Validator state after — full output of `validate_content.py` (especially per-family coverage warnings).
4. Test suite state after — pass/fail counts vs prior baseline.
5. P2 flags — any proposed registry additions, pattern additions, or out-of-scope changes needing user approval.
6. Explicit "STOP — do not self-audit. Hand back to user for Stage C."

---

## 4. Stage C — Post-execution audit playbook

### 4.1 Independence rule

Fresh Opus session. NO context from Stage A or Stage B. Reads disk state against durable contract.

### 4.2 Audit dimensions (A–J)

| Dim | What it checks | Pass criterion |
|---|---|---|
| **A. Structural integrity** | JSON parses; IDs in range; no collisions; validator + tests pass; counts reconcile across CLAUDE.md / content-authoring.md / track-doc / disk | All sources of truth agree exactly |
| **B. Terminology** | `"type": "mcq"` grep returns zero; every `type` value is one declared in the track-doc | Zero `mcq` type hits |
| **C. Framing alignment** | Sample 12 new questions; confirm each is a legitimate exercise of the track's "What this track trains"; reject-on-sight anti-patterns absent | Sample passes; distractors plausible (≥4 not strawman) |
| **D. Difficulty arc** | Sampled questions match per-track difficulty vocabulary; hint count + ladder match contract | No mis-tiering in sample |
| **E. Concept tags** | Every tag resolves to a registered family; no blocklist hits; tags identify distinguishing technique (not incidental); cross-track family names semantically aligned if reused | Zero orphans; spot-check passes |
| **F. Mock-only contract** | Recombination rule, anti-duplication, realism family path verified, type-mix differentiation, chain atomicity, W4-type decisions actually implemented (not theoretical) | All sampled rules satisfied |
| **G. Sizing benchmark** | Practice:mock ratio inside 1.0–1.5× band; mock m:h split defensible against precedent table | Ratio in band; split documented if outlier |
| **H. Doc hygiene (H1–H7)** | Each step independently verified on disk — DONE / MISSING / PARTIAL per item | All 7 DONE |
| **I. Procedural (P1, P2)** | No self-titled "PASS" commits; out-of-scope doc changes flagged (not self-applied) | Both verified |
| **J. Commit hygiene** | Main branch, no `--no-verify`, co-author line present, descriptive commit messages | All four verified |

### 4.3 Per-family coverage audit (subset of E + F)

New audit dimension since the per-family coverage discipline landed:

- Verify zero rule-1 floor breaches (every applicable family has practice at appropriate tier).
- Verify zero rule-2 floor breaches (≥4 mock-only per practice-grounded family).
- Verify zero rule-3 ceiling breaches NOT documented as load-bearing in the track-doc.
- Verify zero rule-4 dead families.
- Cross-reference any warnings emitted by `_validate_per_family_coverage()` against the track-doc's load-bearing-exception section.

### 4.4 Verdict format (PASS / FAIL)

Verdict block must include: track name, result, counts on disk (practice + mock split), ratio, difficulty split, type mix, realism path, chain count, findings (one line per dimension A–J marked OK/FAIL/N/A/FLAG), H1–H7 closeout status (DONE/MISSING/PARTIAL per item), procedural verdict (P1/P2 VERIFIED or VIOLATED), scope-creep verdict (any commits outside H-series scope judged ACCEPTED / ACCEPTED-WITH-NOTE / REJECTED), required remediations if FAIL, Sonnet remediation prompt if FAIL (opens with model-gate verbatim).

If PASS: state "<Track> Phase 2 closed. Tracker may tick <track>." Stop. Do NOT propose next-track work.

If FAIL: do not attempt to fix. Hand back to user with remediation prompt.

---

## 5. Retro-cleanup pattern (post-closure remediation)

Used when the validator surfaces per-family coverage breaches (or other rule violations) on **already-closed** tracks — typically when a new rule is introduced that retro-applies, or when latent drift surfaces post-closure.

### 5.1 When to use

- New durable rule introduced → existing tracks fail it → focused cleanup pass per track.
- Latent drift surfaces (e.g. a path's `focus_concepts` orphans surface when a track is added to `_TAXONOMY_VALIDATED_TRACKS`).
- Stage C audit FAIL with remediation scope smaller than a full Phase 2 round.

### 5.2 Scope

Focused on the flagged findings ONLY. NOT a full Phase 2 round. No new Stage A deliverables; no registry expansion (unless flagged and approved separately); no sizing-band re-litigation.

**What IS in scope (always, when content changes):**
- New questions, edits to existing questions, tag remaps for the flagged families.
- Numerical count-syncing in CLAUDE.md (content footprint table + "Practice totals" + "Mock-only totals") AND `docs/content-authoring.md` § Question bank current state. Required by the no-stale-docs rule whenever question counts shift — this overrides any blanket "do not modify CLAUDE.md" language in the brief.
- Re-running validators after each ITEM and at end.
- The applicable subset of the H-series H1–H7 closeout (typically H1 orphan remap if any new orphans were introduced; H6 count sync; H7 tracker tick if scope is large enough to warrant a decision-log entry).

**What is OUT of scope (P2 applies — surface as flag, do not self-apply):**
- Adding new families to `CONCEPT_FAMILIES`.
- Modifying `MOCK_ONLY_REALISM_FAMILIES`.
- Adding match patterns to existing families (lower-risk; flag in hand-back).
- Modifying philosophy/rules sections of CLAUDE.md, `docs/content-authoring.md`, `docs/specs/*`, `.github/agents/question-authoring.agent.md`.
- Modifying `docs/concept-taxonomy.md` outside the track's section.
- Re-litigating sizing-band targets or precedent table ratios.

**The P2 boundary in one line:** numerical/mechanical updates (count syncs, tag remaps to registered families, content additions per the remedy menu) are in scope; philosophy/rule/registry/contract edits are not.

### 5.3 Remedy menu per finding

For each flagged finding, Sonnet picks one of three remedies and documents the rationale:

- **R1.** Add the missing content (1 practice at lower tier, or N mock-only to hit floor). Use when the family has a genuine teaching arc at the missing tier.
- **R2.** Re-tier the existing question (e.g. mock-only medium → mock-only hard). Use when the family is intrinsically advanced and was mis-tiered.
- **R3.** Document as load-bearing exception or other defensible quality-override in the track-doc. Use when authoring would violate the "Quality > integer" principle or push toward grind-market shape.

### 5.4 Retro-cleanup brief structure

Smaller than a Stage A handoff. Includes:
- Model-gate opening (always — bulk authoring task).
- Required reads (durable contract pointers — same as Stage B but track-doc focus on the breached families only).
- Verbatim validator output for the flagged findings.
- Per-family investigation + remedy procedure (Step 1 investigate, Step 2 propose, Step 3 execute, Step 4 verify).
- Hypothesis-level guidance per family (if available) — investigate-against-content; do not pre-commit.
- **Explicit count-sync expectation:** state that CLAUDE.md content footprint + totals AND `docs/content-authoring.md` § Question bank current state must be updated as the closing step of the pass if question counts shifted. Do NOT write blanket "DO NOT modify CLAUDE.md" language — that conflicts with the no-stale-docs rule.
- P1 + P2 verbatim, with the § 5.2 boundary statement included so Sonnet knows numerical sync is in scope and philosophy edits aren't.
- Hand-back format with explicit instruction: "describe what was actually done, not what was intended. If a chain was dissolved rather than updated, say dissolved. Hand-back accuracy is part of the contract."
- Out-of-scope list (other tracks, separate work streams).

**Chain-handling rule for retro-cleanup that re-tiers questions.** If a re-tier moves a child to a different difficulty file than its parent, that's allowed by the chain-integrity validator (children may be at >= parent difficulty, same track). Two valid responses:
- **(a) Keep chain intact** — update parent's `follow_ups[]` and children's `parent_id` references; chain now spans difficulty files. Preferred when the pedagogical link is valuable.
- **(b) Dissolve chain** — strip `follow_ups[]` from parent, strip `parent_id` + `follow_up_dimension` from children. All become standalone mock-only. Valid when the original chain depended on same-tier pedagogical framing that re-tiering broke.
Sonnet picks per chain with documented rationale in the hand-back. NEVER describe a dissolution as an "update" — these are different operations with different pedagogical consequences.

No Stage A pre-planning needed; Sonnet uses judgment per family with documented rationale. User reviews hand-back; if any per-family decision is wrong, request remediation.

---

## 6. Current Phase 2 status

Update this section after each track closes / each retro-cleanup completes.

### 6.1 Track status (as of 2026-05-26)

| Track | Phase 2 status | Per-family coverage state | Notes |
|---|---|---|---|
| SQL | ✅ Closed | ✅ Retro-cleanup closed 2026-05-25 — zero warnings; 3 mock-only added (13132/33/34), 3 practice added (12121/22/23), 11 mock-only re-tiered medium → hard, 2 chains dissolved on re-tier (12042/12043) — accepted per § 5.4 chain-handling rule | Practice 115→118, mock 162→165, ratio 1.40× |
| Python | ✅ Closed | ✅ Retro-cleanup closed 2026-05-25 — DP(2D): R1, 1 mock-only added (23086 LCS pipeline diff). UNION-FIND: R1, 2 mock-only added (23087 entity resolution, 23088 fraud ring). BACKTRACKING: R2 re-tag 22100 (dropped BACKTRACKING; kept LIST & COLLECTION TRANSFORMATION + INDEXED SEQUENCE REASONING) + R4 dead-family documented in docs/tracks/python.md. MODULAR ARITHMETIC: R4 dead-family documented. IN-PLACE TRANSFORMATION: R4 sub-floor documented. 3 remaining validator warnings are documented R4 exceptions in python.md Coverage section. | Practice 79, mock 100→103, ratio 1.27×→1.30× |
| Pandas | ✅ Closed | ✅ Retro-cleanup closed 2026-05-25 — TRANSFORM VS AGGREGATE: shadow bug (GROUPED AGGREGATION's " AGG" pattern) caused dead-family false alarm; 12 questions re-tagged "GROUPBY TRANSFORM" to resolve without concept_families.py edit. 3 sub-floor families remediated (4 mock-only added: 32091, 33085, 33086, 33087). GROUPED AGGREGATION 59.8% ceiling breach defended as load-bearing in docs/tracks/pandas.md; standing soft warning. | Practice 92, mock 110→114, ratio 1.20×→1.24× |
| PySpark | ✅ Closed | ✅ Zero coverage warnings | Cleanest track on platform under per-family discipline |
| Data Engineering | ✅ Closed | ✅ Retro-cleanup closed 2026-05-25 — zero warnings. INCIDENT RESPONSE: 16 medium mock-only re-tiered to hard (R2). DATA CONTRACT: registry pattern shadow fixed (1-line removal from SCHEMA EVOLUTION patterns) resurrected family with 21 mock-only + 2 practice already on disk. Spot-check on 3 re-tiered questions (53087/53092/53102) confirmed hard-tier reasoning bar. 2 chains touched per § 5.4 (1 intact, 1 dissolved). | Practice 91, mock 110, ratio 1.21×, mock m:h = 1:2.24 (corrected — rationale in data-engineering.md) |
| Data Modeling | ✅ Closed (Phase 2.5 closed 2026-05-26) | Phase 2.5 re-balance complete: Op1 — 2 registry shadows fixed (CONFORMED bare pattern removed from DIMENSION DESIGN; DENORMALIZATION TRADEOFF reordered before NORMALIZATION); Op2 — DIMENSIONAL MODELING stripped from 85 mock-only (93.8% → ~2%, 2 retained on 2-tag constraint flagged for Stage C); Op3 — Q62077 DATA VAULT practice authored (medium); Op4 — Q62078 NORMALIZATION mock-only authored (medium). | Practice 81, mock 97, ratio 1.20×; validator-enabled |
| Statistics | ✅ Closed | ✅ Phase 2 closed 2026-05-26 (Stage C PASS after 2 remediation rounds — see tracker decision log). 13-family registry locked (expanded from 12 via Stage A Deliverable 2). 100 practice + 116 mock-only authored; 12 chains all 7 follow-up dimensions exercised. Dual-subtype (conceptual + numerical); per-subtype ratios conceptual 1.42× / numerical 0.78× (numerical below 1.0× — provisional, first-remediation candidate if exhaustion observed). Path (ii) no realism by design (union-of-modalities defence in `statistics.md`). | Practice 100, mock 116, ratio 1.16× (band low end); validator-enabled |
| ML Fundamentals | ✅ Closed (Phase 2.5 closed 2026-05-26) | ✅ Phase 2 closed 2026-05-26 (Stage C PASS after remediation). BIAS/FAIRNESS Phase 2.5 closed 2026-05-26: ALGORITHMIC FAIRNESS family added (registry 29→30); Q83031 retagged; 3 practice authored (P1 medium, P2/P3 hard); 4 mock-only authored (M2/M3/M4/M5 all hard — M4/M5 escalated from Stage A's planned medium per rule 1 and difficulty vocabulary; DEPLOYMENT CONSTRAINTS and MODEL MONITORING are hard-tier families). All 30 families pass ≥4 mock-only floor. | Practice 100, mock 143, ratio 1.43×; validator-enabled |
| Experimentation | ✅ Closed | ✅ Phase 2 closed 2026-05-26. 24-family registry locked (22→24 via SEQUENTIAL TESTING + METRIC SENSITIVITY). 87 practice + 104 mock-only (0e/45m/59h; 39 hard standalone + 20 chain children from 10 chains); ratio 1.20×. Realism path (ii): no realism families by design (MCQ-only, all reasoning lenses directly gradeable). Q83029 resurrected from ML as 93038. Validator-enabled. | Practice 87, mock 104, ratio 1.20×; validator-enabled |

### 6.2 Validator coverage state (`_TAXONOMY_VALIDATED_TRACKS`)

In set: SQL, Python, Pandas (`python-data`), PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation.
Out of set: none (all 9 active tracks enrolled).

### 6.3 Precedent table (sizing-benchmark anchor for next Stage A)

| Track | Practice | Mock-only | Ratio | Chains | Chain-members | Chain-member % |
|---|---|---|---|---|---|---|
| SQL | 118 | 165 | 1.40 | 6 | 12 (6p + 6c) | 7% |
| Python | 79 | 103 | 1.30 | 18 | 36 (18p + 18c) | 35% |
| Pandas | 92 | 114 | 1.24 | 13 | 35 (13p + 22c) | 31% |
| PySpark | 128 | 150 | 1.17 | 15 | 45 (15p + 30c) | 30% |
| DE | 91 | 110 | 1.21 | 13 | 33 (13p + 20c) | 30% |
| DM | 80 | 96 | 1.20 | 10 | 31 (10p + 21c) | 32% |
| Statistics | 100 | 116 | 1.16 | 12 | 35 (12p + 23c) | 30% |
| ML Fundamentals | 100 | 143† | 1.43 | 8 | 24 (8p + 16c) | 17%† |
| Experimentation | 87 | 104 | 1.20 | 10 | 30 (10p + 20c) | 29% |

†Total mock-only 143 includes 16 chain children; standalone mock-only = 127. Chain-member % is 17% against total mock (24/143) — below the 30–35% cluster but chains were sized at ~20% of the planned 120 mock-only under a prior estimate that undercounted chain-member math (parent-only vs parent+children). Phase 2.5 added 4 hard standalone mock-only (no new chains). See chain-member % note below.

**Chain-member % precedent**: most closed tracks cluster at **30–35%** chain-members per mock-only. SQL is the chain-light outlier at 7% (Phase 2 authored chains conservatively as 1-child pairs; no retroactive chain expansion). Future Stage A planners should target **~30%** as the precedent anchor, NOT ~10-20%. (Backfilled 2026-05-26 — chain counts were never previously surfaced at the orchestration layer; an earlier orchestrator estimate of "DM 10%, DE 15%, Stats 10%" was based on miscounted parent-only figures rather than full chain-member math. ML Fundamentals Phase 2 was sized at 8 chains (~20%) under the wrong figure; this is below precedent but in operational range — not a blocker, candidate for post-Stage-C consideration if Elite-tier Interview Loop coverage feels thin.)

Band: 1.0–1.5×. Always quote this in Stage A Deliverable 1.

**Subtype caveat for Statistics:** the 1.16× track-level ratio masks asymmetric per-subtype ratios — conceptual subtype landed at 1.42× (60/85), numerical subtype at 0.78× (40/31). The numerical 0.78× is below the 1.0× contract floor and is flagged as provisional in `docs/tracks/statistics.md` Coverage section; first remediation candidate if benchmark fresh-first exhausts. Future hybrid-subtype tracks should plan per-subtype ratios that BOTH sit inside the band.

---

## 7. Pre-identified watch-outs for the remaining open tracks

These are starting hypotheses. Each track's Stage A planner refines on inspection.

### 7.1 Statistics — ✅ CLOSED 2026-05-26

Outcome (historical reference for future hybrid-subtype tracks):
- Final state: 100 practice (31e/43m/26h, 60c/40n subtype) + 116 mock-only (0e/66m/50h, 85c/31n subtype) = 1.16× ratio (band low end).
- Registry: 12 → 13 families via Stage A Deliverable 2 (added `survival analysis & time-to-event`; expanded patterns on `errors & power` + `variance decomposition & ANOVA`). Bayesian-frequentist non-inversion enforced (D2-A). Experimental-design boundary narrowed to statistical-foundation only (D2-B option a) — platform-mechanic patterns deferred to Experimentation track.
- Path (ii) no realism family — defended on union-of-modalities + chain-pivot coverage in `docs/tracks/statistics.md`.
- Stage C took 2 remediation rounds + a doc-only Round 3 closeout. Real catches: Bayesian-frequentist co-tag violations on 2 questions, `"variance"` substring shadow mis-routing 11 tags, 3 factual answer-key errors in pre-existing conceptual questions, Coverage-section subtype counts fabricated rather than computed from disk. **Lesson for future Stage Bs**: when validator enforcement is first enabled for a track (H2), pre-existing questions surfaced as failures must be remediated as part of closeout — but those edits should still be surfaced to user BEFORE self-applying, not in hand-back-only. Codification candidate: extend P2 guidance with "validator-blocked = closeout-blocking but still surface-first."
- **Provisional flag carried forward to runbook § 6.3:** numerical subtype 0.78× ratio is below 1.0× contract floor; first remediation candidate if benchmark fresh-first exhausts.
- **Experimentation Phase 2 handoff carry**: the 3 platform-mechanic concepts stripped from Stats path focus_concepts (`SEQUENTIAL TESTING`, `METRIC SENSITIVITY`, `GUARDRAIL METRICS`) must map to Experimentation families when its Phase 2 runs.

### 7.2 ML Fundamentals

- **W1**: Current ratio 25/96 ≈ 0.26× — sub-band, needs ~96–144 mock-only target.
- **W2**: Closest precedents: DE 1.21 / DM 1.20 / PySpark 1.17 (MCQ-response analogues).
- **W3**: Registry already at 29 families / 0 orphans — registry is clean enough to enforce immediately. Stage A may skip Deliverable 2; H2 closeout will add ML to `_TAXONOMY_VALIDATED_TRACKS`.
- **W4**: Realism-family decision — open. ML has candidate clusters around model-evaluation pathology (overfitting traps, leakage detection, baseline-comparison sanity, metric-choice tradeoffs). Defend path (i) or (ii) — DE/DM/PySpark precedent leans (ii) but ML has more legitimate judgment-lens territory than DE/DM did.
- **W5**: Adjacent-track tag bleeds — Stats's `BIAS-VARIANCE TRADEOFF`, `HYPOTHESIS TESTING`; Exp's `A/B TESTING DESIGN`, `CAUSAL INFERENCE`; DE's `FEATURE STORE / SERVING` patterns. Verify on inspection.
- **W6**: Validator NOT enforcing ML yet. Per-ITEM orphan-resolver mandatory in handoff.
- **DE Phase 2 finding still open**: "pre-existing ml-fundamentals validator failures — 10 single-concept questions — surfaced after B1 fix; out of PySpark scope, filed as ml-fundamentals Phase 2 prerequisite" (from the tracker decision log). Stage A must address this.

### 7.3 Experimentation — ✅ CLOSED 2026-05-26

Outcome (historical reference for future tracks):
- Final state: 87 practice (30e/33m/24h, +3 practice additions) + 104 mock-only (0e/45m/59h) = 1.20× ratio (precedent-aligned).
- Registry: 22 → 24 families via Stage A Deliverable 2 (added SEQUENTIAL TESTING + METRIC SENSITIVITY as standalone families per Option-2 decision — both substantively distinct from EXPERIMENT DURATION and METRIC SELECTION; pattern-absorption would have conflated reasoning surfaces).
- Stats carry resolved: all three platform-mechanic concepts (`SEQUENTIAL TESTING`, `METRIC SENSITIVITY`, `GUARDRAIL METRICS`) now resolve to Experimentation families.
- 83029 ML carry resurrected as 93038 with `CAUSAL INFERENCE` + `EXPERIMENT DESIGN` tags.
- Realism path (ii) no realism by design — MCQ-only format, all reasoning lenses directly gradeable.
- 10 chains / 20 children = 30 chain members (29% chain-member share, precedent-aligned). All 7 follow-up dimensions covered.
- **Lesson confirmed**: chain-children-IN-locked-total (runbook § 2.2 D5f, codified post-ML Stage C) worked as expected — no overage.
- **Lesson confirmed**: new-family pattern-shadow check (runbook § 2.2 D2 warning, codified post-Stats Stage C) caught no surprises.

### 7.4 DM Phase 2.5 re-balance — ✅ CLOSED 2026-05-26

Outcome (historical reference):
- DIMENSIONAL MODELING share: 93.8% → 5.2% mock-only (rule-3 cleared on both tiers).
- Dead families resurrected via registry-pattern-shadow fix (not via tag-shuffling — the cleaner-possible-signal path): DENORMALIZATION TRADEOFF reordered before NORMALIZATION; bare `"CONFORMED"` pattern removed from DIMENSION DESIGN. Tags were already on questions; routing was broken.
- DATA VAULT rule-1 floor cleared via R1 (Q62077 medium practice authored).
- Bonus: Q62078 NORMALIZATION mock-only added at medium (family-pair coverage).
- Final state: 81 practice + 97 mock-only = 1.20× (band-aligned, +1 practice / +1 mock from baseline).
- **Lesson confirmed**: tag-honesty (E5 audit dimension) caught zero tagging lies — Stage B's discipline of pre-surfacing 2-tag-constraint cases (62032, 63029) in the commit message rather than silently keeping them set a cleaner precedent for future Phase 2.5 work.

### 7.5 BIAS/FAIRNESS Phase 2.5 — ✅ CLOSED 2026-05-26

Outcome (historical reference for future new-family additions):
- Family name locked: **`ALGORITHMIC FAIRNESS`** (chosen over `BIAS & FAIRNESS LENS` / `FAIRNESS & DISPARATE IMPACT` — concrete reasoning surface, avoids "lens" framing which would have signalled realism).
- Final state: ML registry 29 → 30 families. ML practice 97 → 100 (+3: 1 medium + 2 hard). ML mock-only 139 → 143 (+4 new mock-only; Q83031 retagged in-place to `[ALGORITHMIC FAIRNESS, CLASSIFICATION METRICS]`, `DEPLOYMENT CONSTRAINTS` stripped as tag-honesty correction).
- Ratio 1.43× (essentially unchanged from pre-2.5 baseline).
- Practice tier distribution for the new family: 0e/1m/2h. Mock-only: 5 hard (5 ≥ 4 rule-2 floor); zero medium mock-only because at Stage B the M4/M5 questions were escalated to hard per rule 1 (DEPLOYMENT CONSTRAINTS and MODEL MONITORING co-tag families are hard-tier; medium-tier mock would have created a rule-1 floor violation). Tracker row 828 documents the escalation rationale.
- **Pattern-shadow design**: new family's 7 patterns (`FAIRNESS`, `DISPARATE IMPACT`, `DEMOGRAPHIC PARITY`, `EQUALIZED ODDS`, `GROUP FAIRNESS`, `FAIRNESS METRIC`, `FAIRNESS CONSTRAINT`) intentionally exclude bare `"BIAS"` to preserve BIAS-VARIANCE TRADEOFF resolution. Two expected shadows documented in `docs/concept-taxonomy.md` author-guidance table (`ALGORITHMIC BIAS` → BIAS-VARIANCE TRADEOFF with author direction to use `ALGORITHMIC FAIRNESS`; `CALIBRATION BY GROUP` → MODEL CALIBRATION with co-tag direction).
- W4 designation: path (ii) preserved (`MOCK_ONLY_REALISM_FAMILIES["ml-fundamentals"] = set()` unchanged). Family is practice-grounded.
- **Lesson confirmed**: new-family pattern-shadow check (runbook § 2.2 D2) caught the BIAS-VARIANCE TRADEOFF collision risk upfront; Stage A's `"BIAS"`-exclusion design prevented mis-routing.
- **Lesson confirmed**: P1 disclosure pattern — Sonnet surfaced the M4/M5 medium→hard escalation in commit message + tracker row + track-doc rationale (transparent deviation from Stage A plan, not silent drift).

---

**🎉 ALL 2026-05 AUTHORING REFACTOR WORK COMPLETE.** Phase 2 + DM Phase 2.5 + BIAS/FAIRNESS Phase 2.5 closed. Phase 3 is the next pickup; once Phase 3 ships, the transitional tracker (`docs/phases/2026-05-authoring-refactor.md`) will be **moved to `docs/archive/`** and will become **non-authoritative historical record**. This runbook stays as the durable orchestration handbook.

---

## 8. Durable-contract map (pointers)

Where every rule lives. The runbook references; the contract enforces.

| What | Where |
|---|---|
| Strategic frame (premium reasoning-based, weighting by reasoning surface) | `CLAUDE.md` § Platform position |
| The five-perspective pushback | `CLAUDE.md` § Standing instructions |
| The one test every question must pass | `docs/content-authoring.md` § The one test every question must pass |
| Datathink philosophy | `docs/content-authoring.md` § The datathink philosophy |
| Reject-on-sight + framing authority + research grounding | `docs/content-authoring.md` § Cross-track quality bar |
| Difficulty model | `docs/content-authoring.md` § Difficulty model (cross-track) |
| TXNNN ID scheme | `docs/content-authoring.md` § TXNNN ID scheme |
| Hint discipline | `docs/content-authoring.md` § Hint discipline (cross-track) |
| Concept-tag contract + 50% ceiling + load-bearing + per-family discipline | `docs/content-authoring.md` § Concept-tag contract + § Per-family coverage discipline |
| Tag lookup procedure (verbatim) | `.github/agents/question-authoring.agent.md` § Tag lookup procedure |
| Question type values | `docs/content-authoring.md` § Question type values + `docs/specs/practice-modality-spec.md` |
| Mock-only contract (recombination, realism, formats, sizing benchmark) | `docs/content-authoring.md` § Mock-only authoring contract + § Power-user runway sizing benchmark |
| Mock plan-tier matrix + chain atomicity + Interview Loop | `docs/features/mock.md` |
| Per-track framing authority | `docs/tracks/<track>.md` § What this track trains |
| Per-track datasets, ID range, difficulty vocabulary, concept arc, authoring allocation | `docs/tracks/<track>.md` |
| Concept-family registry (per track) + 7 universal follow-up dimensions | `docs/concept-taxonomy.md` |
| Machine-readable family registry + realism families | `backend/concept_families.py` |
| Validator coverage state + per-family coverage warnings | `backend/scripts/validate_content.py` + `docs/content-authoring.md` § Validator coverage state |
| Phase 2 closeout doc-hygiene (H1–H7) | `docs/content-authoring.md` § Phase 2 closeout doc-hygiene |
| Procedural rules (P1, P2) | `docs/content-authoring.md` § Phase 2 closeout doc-hygiene |
| Transitional execution log (deletes Phase 3) | `docs/phases/2026-05-authoring-refactor.md` |

---

## 9. Notes for the next orchestrator

- Each Stage A you produce will be **shorter** than the ones in the conversation history, because you can reference this runbook + the durable contract instead of re-explaining patterns inline. Aim for ~1500–2500 words per Stage A handoff (the DE/DM/Stats drafts were 4000–6000 because they were inlining patterns now codified here).
- Each Stage C audit playbook similarly compresses — reference § 4.2 audit dimensions instead of restating.
- The retro-cleanup brief (§ 5.4) is the smallest artefact — ~800–1500 words typical.
- Always re-read § 6.1 status table before starting work; update it after each close.
- Always quote § 6.3 precedent table in Stage A Deliverable 1.
- The W-series structure (§ 2.3) is the planner's safeguard against under-specified Stage A handoffs. Use it.
- When in doubt about scope (full Phase 2 vs Phase 2.5 vs retro-cleanup), the differentiator is: does the work require new sizing-band locked decisions (→ Phase 2 / 2.5) or only remediation of flagged findings (→ retro-cleanup)?
