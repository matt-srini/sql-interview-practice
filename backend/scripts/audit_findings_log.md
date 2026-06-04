# Blind-Answer Audit — Running Findings Log

Working artifact (gitignored). Every flagged question is **verified by Opus against source JSON** before landing here. Nothing is authored/edited until the user verifies and approves at the end of the sweep.

Legend:
- **KEY-FLIP** — `correct_option` is genuinely wrong; mechanical JSON fix (still content-verified, never auto-applied blindly).
- **CONTENT** — key is correct but question/explanation is defective; must go through the authoring agent.
- **FALSE-POSITIVE** — audit flagged it, verification cleared it; no action.
- Severity: 🔴 high / 🟡 medium / 🟢 low.

---

## ml-fundamentals · hard  (114 Q · pass2-all · run 2026-06-03)
Raw report verdicts: 111 consistent, 2 broken_mechanism, 1 inconsistent. After Opus verification + harness fix:

| ID | mock_only | type | Verdict (verified) | Action | Sev | Note |
|---|---|---|---|---|---|---|
| 83075 | True | predict_output | FALSE-POSITIVE | none | — | Pass-1 token truncation (UNPARSED); key A correct (BS_A=0.025, BS_B≈0.0013, B lower). Resolved by 768-token harness fix. |
| 83011 | False | scenario | **CONTENT** | authoring agent | 🔴 | Option texts re-letter scenario approaches → "Option C) **Approach D** — XGBoost…". Solvers (incl. Claude) answer the approach-letter, not the option-position. Key **C** (XGBoost native handler + missingness indicator) is correct. Fix: strip "Approach X —" prefixes OR reorder options to scenario order + update correct_option. |
| 83081 | True | conceptual | **CONTENT** | authoring agent | 🟢 | Explanation says "SHAP values are the current best practice," superficially endorsing distractor D ("SHAP should *always* replace built-in"). Key **A** correct; explanation does refute D as "too strong." Fix: subordinate the SHAP mention so it doesn't read as a D endorsement. |

**Batch tally:** 0 key-flips · 2 content · 1 false-positive cleared.

### Doc-gap candidate (needs sign-off)
- `docs/content-authoring.md` § Reject-on-sight: add anti-pattern — *option text must not embed labels (scenario approach-letters, etc.) that collide with the option's own A/B/C/D position.* Source: 83011.

### External-LLM (Phase 2) candidates
- 83011 (label-collision instability — a second model's independent read would confirm the confusion is inherent, not Claude-specific).

---

## ml-fundamentals · medium  (99 Q · pass2-all · run 2026-06-03)
Raw report verdicts: 98 consistent, 1 inconsistent. After Opus verification:

| ID | mock_only | type | Verdict (verified) | Action | Sev | Note |
|---|---|---|---|---|---|---|
| 82002 | False | scenario | **CONTENT (borderline ambiguity)** | authoring agent | 🟡 | "Choosing the Right Intervention from a Learning Curve." Key **A** (collect 50k more images) is the textbook high-variance fix; explanation supports it (Pass 2 consistent). But stem is internally tensioned: "root cause" → A, "most directly" → C (dropout+L2). Pass 1 picked C — a defensible distractor. Key A can stay if stem is sharpened to remove A/C tension. |

**Batch tally:** 0 key-flips · 1 content (borderline) · 0 false-positives.

### External-LLM (Phase 2) candidates
- 82002 (A-vs-C split; a second model's independent pick tells us whether the ambiguity is robust).

---

## experimentation · hard  (83 Q · pass2-all · run 2026-06-03)
Raw report verdicts: 74 consistent, 1 inverted_key, 8 inconsistent. After Opus verification (all 8 "inconsistent" had p2_leads == keyed → key defended; disagreement = blind candidate picking a defensible alternative on a hard methodology Q):

| ID | mock_only | type | Verdict (verified) | Action | Sev | Note |
|---|---|---|---|---|---|---|
| 93045 | True | predict_output | **CONTENT — multiple correct answers** | authoring agent | 🔴 | "Sample size ratio." Options **B** (direct (σ/δ)²≈9.6) and **C** (CV-ratio²≈9.7) are BOTH numerically correct via valid methods; **D** says "either B or C correctly calculates the ratio" — also true. Keyed C is not uniquely correct. Audit's "flip C→D" is INVALID (B stays correct). Fix: make B and C each individually incomplete so D is uniquely right, or genuinely differentiate. Reject-on-sight: multiple correct answers / identical observable outputs. |
| 93024 | True | scenario | **CONTENT — stem/key tension** | authoring agent | 🟡 | Stem stipulates competitor withdrawal "unrelated to the CPG brand's experiment," which undercuts keyed **D**'s conditional ("only if unrelated… if the campaign caused it…"). Given the stipulation, Pass 1's **A** (remove the markets) is defensible. Fix: remove the "unrelated" stipulation so exogeneity is genuinely in question, or accept A. |
| 93026 | True | scenario | **CONTENT — non-unique key** | authoring agent | 🟡 | Ranking Q (key D = "2,3,1"). Explanation itself says Pass 1's pick **B** ("2,1,3") is "debatable but defensible" → key not uniquely correct. Fix: make the 2nd/3rd ranking unambiguous or acknowledge the tie. |
| 93066 | True | debug | **CONTENT — indexing leak + A/B tension** | authoring agent | 🟡 | Explanation written as "Option 0/1/2/3" (0-indexed scaffolding leaked to user-facing text — must be A/B/C/D). Key **A** ("symmetric gap → continue"); Pass 1's **B** ("symmetric session loss ≠ unbiased rate; check timing") is arguably the stronger interview answer. Fix indexing at minimum; review A/B framing. |
| 93018 | False | scenario | borderline ambiguity | review (optional) | 🟡 | Bayesian PBE vs threshold. Key **D** (expected-loss framing) defensible under "right analytical framing"; Pass 1's **B** (threshold integrity) is a strong operational position. Hard but defensible. |
| 93019 | False | scenario | borderline ambiguity | review (optional) | 🟡 | "Most fundamental problem." Key **B** (interaction test) textbook-correct; Pass 1's **A** (multiple comparisons, 46% FWER) also strong. Contestable superlative. |
| 93059 | True | scenario | borderline ambiguity | review (optional) | 🟡 | National launch, no holdout. Key **D** ("both DiD & ITS valid") defensible; Pass 1's **B** (commit to DiD given competitors as clean control) reasonable. "It-depends key vs committal pick" pattern. |
| 93022 | True | scenario | acceptable hard | none | 🟢 | Synthetic control donor pool. Key **A** (contaminated donors > demographic diff, since low MSPE mitigates B) well-reasoned. Just hard. |
| 93028 | True | scenario | acceptable hard | none | 🟢 | SUTVA multi-group. Key **C** (multi-group membership reintroduces interference) is clearly the strongest objection vs Pass 1's **B** (variance = efficiency, not validity). Good Q. |

**Batch tally:** 0 clean key-flips · 1 🔴 + 3 🟡 content · 3 🟡 borderline · 2 🟢 fine.

### Track-level observation (experimentation)
Recurring style: "synthesis / it-depends" answer (Option D = "both valid", "neither superior") as the key vs a committal specific Pass-1 pick. Not wrong per se, but drives blind-candidate disagreement and occasionally tips into non-unique keys (93045, 93026, 93059). Worth a track-doc note on when the synthesis answer is genuinely uniquely-correct vs when a committal answer is equally defensible.

### ⚠️ Meta-finding: `inverted_key`/`mechanical` is unreliable
2/2 `inverted_key` verdicts so far (83011, 93045) were actually CONTENT defects, NOT clean key-flips. Auto-applying either would have damaged a correct/defensible question. **Mechanical fixes will be content-verified, never auto-applied.**

### External-LLM (Phase 2) candidates
- 93045 (multiple-correct-answers — a math-strong external model will independently land on B/C/D ambiguity).
- 93024, 93018, 93019, 93059 (A-vs-B / B-vs-D splits — independent second opinion valuable).

---

## experimentation · medium  (78 Q · pass2-all · run 2026-06-03)
Raw report verdicts: 77 consistent, 1 inconsistent. After Opus verification:

| ID | mock_only | type | Verdict (verified) | Action | Sev | Note |
|---|---|---|---|---|---|---|
| 92060 | True | scenario | acceptable hard | none | 🟢 | "SRM from differential bot filtering." Key **B** (conversion salvageable; page-views need scrutiny — asymmetric treatment inflation) well-reasoned; explanation refutes all distractors incl. D's inverted symmetry. Pass 1 picked **C** ("neither salvageable, restart") — over-conservative but weaker. Good Q. |

**Batch tally:** 0 key-flips · 0 content defects · 1 acceptable-hard (no action).

---

## ✅ PRIORITY BATCHES COMPLETE (ml-fundamentals + experimentation, medium+hard) — 374 Q audited

**Headline: 0 wrong answer-keys requiring a mechanical flip across 374 questions.**

Consolidated action list (nothing applied — awaiting user verify+approve):

| ID | Track/Diff | Sev | Action | One-line |
|---|---|---|---|---|
| 83011 | mlf hard | 🔴 | authoring | Option text re-letters scenario approaches → solvers answer approach-letter not option-position. Key C correct. |
| 93045 | exp hard | 🔴 | authoring | Multiple correct answers (B/C/D all valid). Keyed C not unique. |
| 83081 | mlf hard | 🟢 | authoring | Explanation over-concedes "SHAP is current best practice" → reads as endorsing distractor D. Key A correct. |
| 82002 | mlf med | 🟡 | authoring | Stem tension: "root cause"→A vs "most directly"→C. Key A defensible; sharpen stem. |
| 93024 | exp hard | 🟡 | authoring | Stem says withdrawal "unrelated to experiment," undercutting keyed D's doubt-exogeneity logic. |
| 93026 | exp hard | 🟡 | authoring | Ranking Q; explanation admits Pass-1 alt "debatable but defensible" → key D not unique. |
| 93066 | exp hard | 🟡 | authoring | "Option 0/1/2/3" indexing leak in explanation (fix to A/B/C/D) + A/B framing tension. |
| 93018,93019,93059 | exp hard | 🟡 | review (optional) | Borderline "synthesis key vs committal pick" hard Qs; keys defensible. |
| 83075,93022,93028,92060 | various | 🟢 | none | Verified clean (1 was a harness false-positive, 3 acceptable-hard). |

Doc-gap candidate (needs sign-off): add "option text must not embed labels colliding with option positions" to `docs/content-authoring.md` § Reject-on-sight (source: 83011).

**Survivor-class note:** `--pass2-all` caught **83081** (key right, explanation argues toward distractor) which default disagreement-gated Pass-2 would have MISSED. The survivor class is real but rare + low-severity in these two tracks (1 of 374).

---

## pyspark · all difficulties  (277 Q · pass2-all · run 2026-06-03)
Raw report verdicts: 261 consistent, 2 inverted_key, 14 inconsistent, 0 broken. **0 flags at easy.** After Opus verification:

| ID | diff | type | Verdict (verified) | Action | Sev | Note |
|---|---|---|---|---|---|---|
| **43112** | hard | scenario | **KEY-FLIP (confirmed)** | **mechanical 1→2** + authoring | 🔴 | `correct_option` should be **2 (C)**, currently 1 (B). 0-indexed explanation says "Option 2 [=C] is most plausible" and "Option 1 [=B] … wrong direction." Ground truth: B's premise false (`maxOffsetsPerTrigger` is a total, not per-partition limit; more partitions → more capacity not less). FIRST genuine key error in the audit. Also fix the "Option N" indexing. |
| 42088 | medium | conceptual | **CONTENT — explanation contradicts key** | authoring | 🔴 | Keyed **B** asserts partial Delta writes leave duplicates; explanation says Delta's atomic commits PREVENT that and concludes "Delta DOES provide end-to-end exactly-once" → refutes B, points to D. Defect: illustrates a non-idempotent-sink principle using Delta (idempotent). Rewrite (not a clean flip). |
| 43066 | hard | predict_output | **CONTENT — 3 options identical output** | authoring | 🔴 | Options A, B, C ALL predict c1=80/c2=100 (explanation admits "Options 0,1,2 all give the same numeric answer"); only D differs. predict_output with 3 indistinguishable-output options violates reject-on-sight. Make A/B predict wrong numbers so C is unique. |
| 42098 | medium | optimization | CONTENT — index leak + awkward stem | authoring | 🟡 | "Option 0" 0-index leak; stem asks "what placement is wrong" but key A = "nothing's wrong, cache is lazy." Key A defensible. |
| 43081 | hard | optimization | CONTENT — label collision + synthesis key | authoring | 🟡 | Same 83011-class collision: option texts re-letter stem proposals ("Option A) Option C —…"). Key D ("it-depends") defensible. |
| 42115 | medium | predict_output | CONTENT — index leak + debatable | review | 🟡 | 0-index leak; B (CSE) vs C (predicate pushdown) is genuinely version/plan-dependent Catalyst internals. Verify the CSE claim. |
| 42103,42107,43096,43110,43059,43104,43105 | — | — | index-leak (key OK) | authoring (cleanup) | 🟡 | Keys verified CORRECT. 0-indexed "Option N" references; **42107 & 43096 have internally-inconsistent numbering** (mix 0/1-index) — genuinely confusing, not just cosmetic. |
| 42040,42067,42069,42094,42069 etc. | — | — | acceptable hard | none | 🟢 | Keys verified correct; blind-candidate disagreement on hard questions. |

**Batch tally:** **1 confirmed KEY-FLIP (43112)** · 2 🔴 other content defects · several 🟡 content/index-leak · rest acceptable.

### 🚨 SYSTEMIC FINDING: 0-indexed "Option N" in explanations — 243 questions, 5 tracks
Deterministic scan (`Option [0-9]` in explanation text):

| Track | Affected | 
|---|---|
| pyspark | 129 |
| data-modeling | 49 |
| statistics | 33 |
| experimentation | 22 |
| ml-fundamentals | 10 |
| data-engineering | **0 (clean)** |
| **TOTAL** | **243** |

Risk: (a) reads unprofessionally to users ("Option 0 is correct"); (b) **caused the 43112 mis-key**; (c) sometimes internally inconsistent (42107, 43096). Deterministic key-mismatch cross-check (`Option N is correct/wrong` vs `correct_option`) over all 243 surfaced only 43112 as a real mismatch — the other 5 hits (42103, 42107, 43096, 43110×2) were qualified-partial false-positives with correct keys.

**CONFIRMED FRONTEND INCONSISTENCY (user priority).** Frontend labels options **A/B/C/D** (`MCQPanel.js` L50 `String.fromCharCode(65+i)`) and renders the explanation **raw** (`MCQPanel.js` L66, `QuestionPage.js` L1771) — no remap. So users literally see "Option 0/1/2/3" beneath A–D options. **Established convention is letters**: data-engineering 198 letters / **0 numbers** (clean template); every other track is majority-letters with a numbered residual (git log confirms a prior partial normalization — e.g. `90719f1 ml-hard 51 correct_option inversions`). "Already handled previously" = that prior pass, which left these 243.

**DECISION LOCKED (user, 2026-06-03):** standardize on **A/B/C/D across all tracks** in explanation option-references — removes index ambiguity entirely; matches frontend A–D labels + DE's clean convention.

**PLAN:** Finish the normalization (numbers→letters A/B/C/D) as a dedicated bulk pass (Sonnet + model-gate), AFTER the blind-answer sweep reaches each track (so any 43112-style key mismatch is flagged first, making the text remap safe). Per-question: match each "Option N" to the option content, verify endorsed option == `correct_option`, then remap to its letter. DE needs zero work. ⚠ NOT a blind global regex — 42107/43096 have inconsistent internal numbering and 43112 has a key mismatch; these need per-question verification, not find-replace.

Letter-vs-number convention snapshot (explanations): pyspark 106/129 · DE 198/0 · DM 100/49 · stats 68/33 · mlf 178/10 · exp 155/22.

### External-LLM (Phase 2) candidates
- 43112 (key-flip — external model independently picks C), 42088 (Delta exactly-once — strong-systems model), 43066 (identical-output predict), 42115 (Catalyst CSE vs pushdown).

---

## data-engineering · all difficulties  (201 Q · DEFAULT pass-2 · run 2026-06-03)
Raw verdicts: 195 consistent, 0 inverted, 0 broken, 6 inconsistent. After Opus verification — **0 key errors, 0 defects** (cleanest track; 100% letter convention, prior audit work):

| ID | diff | type | Verdict | Action | Sev | Note |
|---|---|---|---|---|---|---|
| 52030 | med | conceptual (practice) | acceptable | none | 🟢 | Key A "trace backward from symptom (mart→staging→raw)" — textbook efficient debug; Pass-1 bottom-up B weaker. |
| 52046 | med | conceptual | acceptable | none | 🟢 | Key A IS the crypto-shredding answer (option text contains it); explanation supports A. Pass-1 C (repartition) ignores existing data. |
| 52047 | med | debug | acceptable | none | 🟢 | Key A (dbt exit-0 with empty source); "0 models modified" log supports A over Pass-1 C. |
| 53043 | hard | debug | acceptable | none | 🟢 | Key A (replication lag) explains BOTH 8% revenue drop AND row-count drop; Pass-1 B (schema change) doesn't. |
| 53039 | hard | scenario | borderline | review (optional) | 🟡 | Key D (stream-transform) vs Pass-1 B (dual topics) — both defensible; D structurally cleaner. |
| 53049 | hard | debug | borderline | review (optional) | 🟡 | Key C (crypto-shredding for append-only) vs Pass-1 A (PII table) — both legit; C canonical for immutable store. |

**Batch tally:** 0 key-flips · 0 defects · 4 acceptable · 2 borderline (keys defensible). No 0-index issues (DE is letter-clean).

---

## data-modeling · all difficulties  (178 Q · DEFAULT pass-2 · run 2026-06-03)
Raw verdicts: 169 consistent, 0 inverted, 0 broken, 9 inconsistent. After Opus verification — **0 key errors, 0 defects.** Deterministic 0-index key-mismatch check on flagged + all 49 numbered residuals: **no mismatches** (DM numbered explanations are all key-consistent — cosmetic remap only).

Flagged (all `inconsistent`, p2_leads==key): 62032, 62043, 62058, 62072, 63002, 63008, 63018, 63030, 63037 — every one a dimensional-modeling **design-choice** question (SCD type selection, fact grain, multi-hierarchy dim, wide-vs-narrow fact, M2M bridge, dbt materialization, intra-day snapshot). Keys are the standard Kimball/dbt textbook answers; Pass-1 picked defensible alternative designs. Explicit constraint lists in each stem disambiguate toward the key. 3 are practice (63002, 63008, 63018) — keys are canonical (bridge table for M2M, Type-6 for current+history, incremental-merge for backfill).

**Batch tally:** 0 key-flips · 0 defects · 9 defensible-design reviews. 49 numbered residuals → A/B/C/D normalization (no key risk).

---

## statistics · all difficulties (conceptual only)  (145 Q audited · DEFAULT pass-2 · run 2026-06-03 — PARTIAL: API CREDIT EXHAUSTED mid-run)
Raw verdicts: 106 consistent, 0 inverted, 0 broken, 39 inconsistent. BUT credit ran out during the Pass-1 tail → all 39 Pass-2 calls errored + 11 Pass-1 calls errored. Reclassified after Opus manual (no-API) verification against explanations:

### 🔴🔴 SYSTEMATIC +1 KEY SHIFT — 27 stats MEDIUM **practice** questions (LIVE, mock_only=false)
`correct_option` = real_answer + 1 on every one (stored 1-indexed, read 0-indexed). Verified TWO ways: blind-answer disagreement + manual explanation read. Frontend shows the wrong option as ✓.

**FIX (mechanical, `correct_option -= 1`, HOLD for user approval):**
```
72001:2→1  72004:2→1  72006:2→1  72007:2→1  72008:1→0  72010:2→1  72012:2→1
72013:2→1  72015:2→1  72019:2→1  72020:2→1  72023:2→1  72024:2→1  72027:2→1
72029:2→1  72030:2→1  72031:2→1  72032:2→1  72033:2→1  72034:2→1  72035:3→2
72036:2→1  72037:2→1  72038:2→1  72039:2→1  72040:2→1  72041:2→1
```
Smoking-gun examples: 72020 keyed C="Poisson mean=√7" (false; real B mean=var=7); 72008 keyed B="reject true H₀ 80% of time" (absurd; real A=power definition); 72006 keyed C (real B). `correct_option` dist on these 30 practice Q was 25×C — the tell.

**Boundary confirmed exact:** the 3 non-flagged practice medium (72005, 72017, 72043) are correctly keyed (key=B, haiku agreed) → NO false-positives, NO over-reach. 72054 (mock, key=D) correctly keyed (letter-convention; explanation says "Option D").

### Stats HARD — CLEAN (the 11 "flags" were API-credit errors, not bugs)
Manually verified 73060–73075: every explanation matches `correct_option` (73060–73070 "Option B"=B✓; 73071 "Option 2"=C✓; 73073/73075 "Option 1"=B✓). No +1 bug in hard. Stats easy: 0 flags.

### Validator-gap (doc note)
`_validate_correct_option_explanation_consistency` did NOT catch these because the stats explanations *describe the concept* (e.g. "mean and variance both equal λ") without writing "Option C is wrong" — so the position-reference pattern the validator keys on is absent. A +1 shift is invisible to it. Worth a validator enhancement (compare explanation's described-answer to keyed option text).

**Batch tally:** **27 confirmed live KEY-SHIFT bugs (medium practice)** · 0 in hard/easy · stats run must be RE-RUN after credit restored (the 39 corrupted Pass-2 + 11 Pass-1 errors) to formally re-confirm via the harness.

---

## ✅ statistics CLEAN RE-RUN (after 27 fixes + credit restored) — 145 Q
141 consistent, 0 inverted, 0 broken, 4 inconsistent. **All 27 fixed IDs now `consistent`** (fix verified end-to-end). Remaining 4: 72054 (correctly keyed, verified earlier), 73024/73041/73045 (intermittent API rate-limit errors — manually verified all 3 correctly keyed: B/B/B, explanations support B). **Statistics: 0 remaining key errors.**

## ✅ ml-fundamentals easy — 30/30 consistent, 0 flags (clean)
## ✅ experimentation easy — 29/30 consistent; 91019 verified clean (key A "raise α increases power" correct; haiku picked D). 0 key errors.

---

# ═══ FINAL: ALL 18 MCQ CELLS AUDITED ═══

| Track | easy | medium | hard | Key errors found |
|---|---|---|---|---|
| ml-fundamentals | ✅ | ✅ | ✅ | 0 |
| experimentation | ✅ | ✅ | ✅ | 0 |
| pyspark | ✅ | ✅ | ✅ | **1 (43112)** |
| data-engineering | ✅ | ✅ | ✅ | 0 |
| data-modeling | ✅ | ✅ | ✅ | 0 |
| statistics | ✅ | ✅ | ✅ | **27 (FIXED ✅)** |

**Total confirmed live `correct_option` bugs: 28** — 27 stats medium (FIXED, committed a85fdca + re-run verified) + 1 pyspark 43112 (pending).

## "Fix everything clean" — consolidated work list (pending user go-ahead)
1. **pyspark 43112** — mechanical `correct_option` 1→2 (key should be C; verified). Same class as the stats 27.
2. **Content defects → authoring agent:** 🔴 42088 (Delta explanation contradicts key), 43066 (predict_output 3 identical outputs), 93045 (multiple correct answers), 83011 (label collision). 🟡 83081, 82002, 93024, 93026, 93066, 42098, 43081, 42115.
3. **A/B/C/D normalization (243 Q):** pyspark 129, DM 49, stats 33, exp 22, mlf 10. Bulk Sonnet + model-gate; per-question verify endorsed option == correct_option before remap (no blind regex).
4. **Code refactor:** single shared `is_mcq_correct()` + `correct_letter()` helper; route all 10 duplicated call-sites through it.
5. **Durable validator guard:** detect +1/index drift (e.g. letter-based cross-check) so this can't recur silently — the existing `_validate_correct_option_explanation_consistency` missed it because stats explanations describe the concept without "Option X is wrong" phrasing.
6. **Doc updates:** add the label-collision + identical-output anti-patterns to `docs/content-authoring.md` § Reject-on-sight; note the validator-gap.

## Phase 2 (external-LLM) candidates
43112, 42088, 43066, 93045 (pyspark/exp); 82002, 93018/93019/93024/93059 (borderline splits); the stats 27 (now fixed — an external model would independently confirm).

---

## ⛔ [RESOLVED] Anthropic API credit exhausted (2026-06-03, mid-statistics run) — credit restored, runs completed
1-token probe returns "Your credit balance is too low to access the Anthropic API." **Cannot run the last 2 cells** (ml-fundamentals easy, experimentation easy) or re-run statistics until credit is restored or a new key is provided. 16 of 18 MCQ cells audited; statistics needs a clean re-run.

---

---

# ═══ PHASE 2 — EXTERNAL-MODEL (Nvidia NIM) BLIND AUDIT ═══
_Run 2026-06-04. Pass 1 (blind): `meta/llama-3.3-70b-instruct`. Pass 2 (explanation-consistency, --pass2-all): `openai/gpt-oss-20b`. Both independent of Claude and of each other. Harness: `audit_blind_answer_nim.py` (resumable, error-results not checkpointed). Reports: `audit_nim_<track>_<diff>.json` (gitignored)._

## Headline
**1157 consistent · 0 inverted_key · 0 broken_mechanism · 78 inconsistent (all review)** across **1,235 MCQs**.
**0 wrong keys. 0 questions where BOTH external models disagree with the key.** Every one of the 78 review flags is a Pass-1 blind-disagreement where Pass-2 (reading the explanation) returns to the keyed option.
Pass-1 UNPARSED/ERROR: 0. Pass-2 UNPARSED: 2 (42071, 52051 — both retried; see Finding B).

## Per-cell verdicts (consistent / inverted / broken / inconsistent)
| Cell | cons | inv | brk | inc |
|---|---|---|---|---|
| pyspark_easy | 34 | 0 | 0 | 6 |
| pyspark_medium | 107 | 0 | 0 | 13 |
| pyspark_hard | 103 | 0 | 0 | 14 |
| data-engineering_easy | 29 | 0 | 0 | 1 |
| data-engineering_medium | 68 | 0 | 0 | 1 |
| data-engineering_hard | 96 | 0 | 0 | 6 |
| data-modeling_easy | 25 | 0 | 0 | 0 |
| data-modeling_medium | 74 | 0 | 0 | 3 |
| data-modeling_hard | 67 | 0 | 0 | 9 |
| statistics_easy | 16 | 0 | 0 | 0 |
| statistics_medium | 82 | 0 | 0 | 1 |
| statistics_hard | 45 | 0 | 0 | 1 |
| ml-fundamentals_easy | 29 | 0 | 0 | 1 |
| ml-fundamentals_medium | 96 | 0 | 0 | 3 |
| ml-fundamentals_hard | 110 | 0 | 0 | 4 |
| experimentation_easy | 30 | 0 | 0 | 0 |
| experimentation_medium | 74 | 0 | 0 | 4 |
| experimentation_hard | 72 | 0 | 0 | 11 |
| **TOTAL** | **1157** | **0** | **0** | **78** |

## Regression confirmation of Phase 1 (PRIMARY GOAL — all ✅)
- **STATS-27** (+1 key-shift fixes, a85fdca): all 27 now `consistent`. Independently confirmed end-to-end.
- **pyspark 43112** (key-flip 1→2/C, 2474cfc): NIM reads key=C, Pass-2 → C. Confirmed.
- Phase-1 content fixes **42088** (Delta EOS), **43066** (3-identical-output), **93045** (multi-correct labels): all `consistent`.
- No new key errors anywhere. Phase 1's 28 mechanical key fixes are independently validated.

## Finding A — Tiebreaker set adjudication (the 7 OPEN Phase-2 candidates)
NIM Pass-1 independently disagreed (escalation trigger) on **5 of 7**. In all, Pass-2 still defends the key (no key error); the escalation is to CONTENT/stem ambiguity. Verdicts:
- **82002** (mlf med) — ESCALATE 🟡: stem 'root cause' vs 'most directly' tension; Llama+Haiku both pick C (regularisation). Key A defensible. Fix = sharpen stem.
- **93066** (exp hard) — ESCALATE 🟡: stem does not foreclose B's peak-hour timing concern; both families pick B (arguably the stronger senior answer). Fix = add stem stipulation (outage uniform across day).
- **42098** (pyspark med) — ESCALATE 🟡: stem presupposes 'what placement is wrong' but key A = 'nothing is wrong'; stem/key framing contradiction. Fix = reframe stem as a diagnosis.
- **93019** (exp hard) — BORDERLINE-ESCALATE 🟡: 'most fundamental' superlative pits A (multiple-comparisons, 46% FWER) vs B (interaction test), both true. Fix = soften superlative / make B uniquely correct.
- **93018** (exp hard) — BORDERLINE-KEEP 🟢: stem's 'right analytical framing' cue does select D (expected-loss); hard but fair.
- **42115, 93059** — KEEP: NIM Pass-1 AGREED with the keys.

## Finding B — NEW SYSTEMIC: label-collision option text (~21 questions) — § Reject-on-sight class
Phase 2 surfaced the 83011/43081 anti-pattern (option text embeds a Proposal/Approach/Strategy/Design/Method/Option letter that collides with the option's own A/B/C/D position) in **21 currently-live questions** Phase 1 missed. Surfaced via `--pass2-all` on the independent model: 52051 was a Pass-2 UNPARSED that, on retry, mapped the explanation to the embedded letter ('B') not the position ('A') — exposing the confusion. Several directly caused NIM review-flags (42075, 42119, 83021, 83022). **All keys appear correct → CONTENT fix (rewrite options to drop embedded labels), via the authoring agent.**

Deterministic scan hits (embedded letter ≠ option position):
- High-severity full re-letter: **52051, 52081, 82022, 82056, 83021, 83022, 83124, 42075, 42119**
- Comparison-format (in-stem 'Option A/B' code variants): **42078, 42090, 43052, 43076, 43092, 43108, 43109, 53078, 63030, 72073, 73049, 73064**
- Full list (21): [42075, 42078, 42090, 42119, 43052, 43076, 43092, 43108, 43109, 52051, 52081, 53078, 63030, 72073, 73049, 73064, 82022, 82056, 83021, 83022, 83124]

## Finding C — harness/methodology note
2 Pass-2 UNPARSED (gpt-oss hit token cap before the LEADS_TO line) were treated as `consistent` (Pass-1 agreed). Retried: 42071 clean (key C); **52051 surfaced Finding B**. Lesson: auto-retry UNPARSED Pass-2 (or raise max_tokens) — silent UNPARSED can mask a survivor-class/collision defect.

## Doc-gap analysis
- The § Reject-on-sight label-collision rule EXISTS (added post-83011) but its **backward-pass** (audit ALL existing questions of the same type when a new reject-on-sight rule lands) was never completed → 21 instances survived. Recommend: (1) remediate the 21 via authoring agent; (2) add a DETERMINISTIC validator guard `_validate_no_embedded_option_labels` (regex-detectable, analogous to the numeric-option-ref check) so it cannot recur.
- Harness lesson (Finding C) → fold UNPARSED-retry into the audit harness for any Phase 3.

## Phase 3 candidate list (paid external model)
- The 5 escalated/borderline tiebreakers (82002, 93066, 42098, 93019, 93018) — a 3rd independent family settles the genuine-ambiguity calls.
- The 21 label-collision questions, AFTER remediation — confirm the rewrites removed the confusion.
- The full review-flag set (below) as a regression baseline.

## All 78 review flags (id | cell | p1→key | p2 | mock | type)
- 41006 | pyspark_easy | D→B | p2=B | mock=False | predict_output
- 41015 | pyspark_easy | B→A | p2=A | mock=False | conceptual
- 41023 | pyspark_easy | B→C | p2=C | mock=False | predict_output
- 41025 | pyspark_easy | C→B | p2=B | mock=False | predict_output
- 41028 | pyspark_easy | B→A | p2=A | mock=False | conceptual
- 41031 | pyspark_easy | D→B | p2=B | mock=False | predict_output
- 42007 | pyspark_medium | C→B | p2=B | mock=False | conceptual
- 42069 | pyspark_medium | D→A | p2=A | mock=True | optimization
- 42075 | pyspark_medium | B→A | p2=A | mock=True | predict_output
- 42078 | pyspark_medium | B→D | p2=D | mock=True | optimization
- 42080 | pyspark_medium | B→A | p2=A | mock=True | debug
- 42083 | pyspark_medium | A→C | p2=C | mock=True | scenario
- 42091 | pyspark_medium | D→B | p2=B | mock=True | predict_output
- 42098 | pyspark_medium | B→A | p2=A | mock=True | optimization
- 42100 | pyspark_medium | A→B | p2=B | mock=True | predict_output
- 42105 | pyspark_medium | A→C | p2=C | mock=True | scenario
- 42113 | pyspark_medium | B→A | p2=A | mock=True | predict_output
- 42117 | pyspark_medium | C→B | p2=B | mock=True | predict_output
- 42119 | pyspark_medium | A→B | p2=B | mock=True | predict_output
- 43032 | pyspark_hard | A→D | p2=D | mock=True | scenario
- 43040 | pyspark_hard | B→C | p2=C | mock=False | predict_output
- 43054 | pyspark_hard | A→C | p2=C | mock=True | optimization
- 43063 | pyspark_hard | A→C | p2=C | mock=True | debug
- 43074 | pyspark_hard | B→C | p2=C | mock=True | debug
- 43081 | pyspark_hard | B→D | p2=D | mock=True | optimization
- 43083 | pyspark_hard | A→B | p2=B | mock=True | debug
- 43084 | pyspark_hard | D→B | p2=B | mock=True | predict_output
- 43088 | pyspark_hard | D→B | p2=B | mock=True | debug
- 43089 | pyspark_hard | A→C | p2=C | mock=True | predict_output
- 43097 | pyspark_hard | C→B | p2=B | mock=True | predict_output
- 43105 | pyspark_hard | B→A | p2=A | mock=True | scenario
- 43111 | pyspark_hard | A→B | p2=B | mock=True | predict_output
- 43112 | pyspark_hard | B→C | p2=C | mock=True | scenario
- 51005 | data-engineering_easy | D→A | p2=A | mock=False | debug
- 52030 | data-engineering_medium | B→A | p2=A | mock=False | conceptual
- 53035 | data-engineering_hard | D→A | p2=A | mock=True | scenario
- 53039 | data-engineering_hard | A→D | p2=D | mock=True | scenario
- 53049 | data-engineering_hard | A→C | p2=C | mock=True | debug
- 53064 | data-engineering_hard | A→B | p2=B | mock=True | debug
- 53078 | data-engineering_hard | A→D | p2=D | mock=True | scenario
- 53080 | data-engineering_hard | D→C | p2=C | mock=True | scenario
- 62002 | data-modeling_medium | D→B | p2=B | mock=False | scenario
- 62004 | data-modeling_medium | C→B | p2=B | mock=False | scenario
- 62043 | data-modeling_medium | B→A | p2=A | mock=True | scenario
- 63005 | data-modeling_hard | D→A | p2=A | mock=False | scenario
- 63008 | data-modeling_hard | D→A | p2=A | mock=False | scenario
- 63009 | data-modeling_hard | A→D | p2=D | mock=False | scenario
- 63016 | data-modeling_hard | B→A | p2=A | mock=False | scenario
- 63018 | data-modeling_hard | A→B | p2=B | mock=False | scenario
- 63023 | data-modeling_hard | D→A | p2=A | mock=False | scenario
- 63043 | data-modeling_hard | D→C | p2=C | mock=True | conceptual
- 63051 | data-modeling_hard | D→B | p2=B | mock=True | scenario
- 63070 | data-modeling_hard | B→A | p2=A | mock=True | scenario
- 72054 | statistics_medium | B→D | p2=D | mock=True | conceptual
- 73057 | statistics_hard | C→B | p2=B | mock=True | conceptual
- 81025 | ml-fundamentals_easy | C→B | p2=B | mock=False | debug
- 82002 | ml-fundamentals_medium | C→A | p2=A | mock=False | scenario
- 82074 | ml-fundamentals_medium | C→B | p2=B | mock=True | predict_output
- 82075 | ml-fundamentals_medium | C→B | p2=B | mock=True | conceptual
- 83019 | ml-fundamentals_hard | D→B | p2=B | mock=False | conceptual
- 83021 | ml-fundamentals_hard | D→C | p2=C | mock=False | scenario
- 83022 | ml-fundamentals_hard | A→B | p2=B | mock=False | conceptual
- 83052 | ml-fundamentals_hard | B→A | p2=A | mock=True | conceptual
- 92036 | experimentation_medium | C→B | p2=B | mock=True | scenario
- 92061 | experimentation_medium | A→B | p2=B | mock=True | scenario
- 92070 | experimentation_medium | D→B | p2=B | mock=True | scenario
- 92074 | experimentation_medium | C→B | p2=B | mock=True | predict_output
- 93013 | experimentation_hard | A→D | p2=D | mock=False | scenario
- 93018 | experimentation_hard | B→D | p2=D | mock=False | scenario
- 93019 | experimentation_hard | A→B | p2=B | mock=False | scenario
- 93022 | experimentation_hard | B→A | p2=A | mock=True | scenario
- 93024 | experimentation_hard | A→D | p2=D | mock=True | scenario
- 93026 | experimentation_hard | A→D | p2=D | mock=True | scenario
- 93030 | experimentation_hard | B→C | p2=C | mock=True | scenario
- 93045 | experimentation_hard | B→D | p2=D | mock=True | predict_output
- 93048 | experimentation_hard | A→B | p2=B | mock=True | debug
- 93063 | experimentation_hard | A→B | p2=B | mock=True | scenario
- 93066 | experimentation_hard | B→A | p2=A | mock=True | debug
