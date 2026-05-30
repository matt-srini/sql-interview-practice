# PySpark Track

> **Authoring rule, no exceptions:** Every PySpark question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/pyspark_questions/*.json` bypass the difficulty arc, the concept-taxonomy contract, and the "no code execution" discipline.

## What this track trains

A working PySpark practitioner does not get rewarded for memorising `spark.sql.shuffle.partitions` defaults. They get rewarded for **reading code and predicting what Spark will actually do** — which line triggers a shuffle, where memory goes, when AQE will rewrite their plan at runtime, why their broadcast join silently fell back to sort-merge. PySpark interviews probe this execution-model understanding precisely because production Spark jobs fail in execution-model ways: skew, OOM, shuffle storms, broadcast threshold misconfigurations.

> *Datathink philosophy applied:* The engineer who memorised the config flag is everywhere. The engineer who reads the snippet and says "this will shuffle three times — here's why, here's how to eliminate two of them" is the one whose pipelines actually run at scale.

This is a **code-adjacent reasoning** track. We don't execute Spark — we test whether the candidate can reason about what Spark will do without running it.

## Modality

**Code-adjacent reasoning.** No execution. Every question is multiple-choice with exactly 4 options. The candidate reads code, predicts output / identifies a bug / picks a strategy — but never runs anything.

Question subtypes:
- **`predict_output`** — given a PySpark snippet, predict what it returns, what schema it produces, what error it raises
- **`debug`** — given broken code or an error message, identify the root cause and the correct fix
- **`conceptual`** — conceptual understanding *anchored in a concrete real-world scenario* (not abstract trivia)
- **`scenario`** — scenario-anchored question requiring multi-concept application in a realistic production setting
- **`optimization`** — given a job description and a bottleneck, choose the best strategy

**Easy tier must mix types.** Pure-recall `conceptual` is rejected at easy — use `predict_output` or `debug` to force mental execution tracing.

## ID range (TXNNN scheme)

`T=4` for PySpark.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 41001–41999 | `backend/content/pyspark_questions/easy.json` |
| Medium | 42001–42999 | `backend/content/pyspark_questions/medium.json` |
| Hard | 43001–43999 | `backend/content/pyspark_questions/hard.json` |

**PySpark has no separate sample file or sample IDs.** Samples are served at runtime by `backend/sample_questions.py::get_topic_sample_pool()`, which slices the first 3 practice questions by `order` from the live catalog (same as Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation). Do not author dedicated sample questions and do not create a `sample/` directory for this track.

## Difficulty vocabulary

| Tier | Reasoning depth | Subtypes | Topics |
|---|---|---|---|
| **Easy** | Single concept, one unambiguous correct answer. Mental execution tracing. | `predict_output` or `debug` preferred; `conceptual` only if scenario-anchored | Transformation-vs-action, narrow-vs-wide, basic schema, `collect()` driver implications, common `AnalysisException` patterns |

> **Sample surface note:** Because the sample pool is the first 3 easy practice questions by `order`, the three lowest-`order` easy questions are the track's shopfront for anonymous users. At least one of those three must be `predict_output` or `debug` — three consecutive definitional `conceptual` questions misrepresent the track as definition-recall and fail to demonstrate the code-adjacent reasoning that differentiates it.
| **Medium** | Trade-off reasoning. Two approaches both plausible but differ in meaningful ways. | All subtypes | Partitioning, shuffle triggers, `repartition` vs `coalesce`, broadcast join conditions, PySpark window-function API and frames (`rowsBetween` / ROWS vs RANGE), `explode` and `collect_list`/`pivot`, Delta Lake MERGE / schema evolution / time travel, Structured Streaming output modes |

> **Sample surface note (medium):** Because the medium sample pool is the first 3 medium practice questions by `order`, the three lowest-`order` medium questions serve as the track's medium shopfront for anonymous users. None should be a bare classification question ("which of these triggers a shuffle?") without code context or job symptom — they must demonstrate the scenario-anchored execution-model reasoning that defines PySpark medium. See anti-patterns (§ "Duplicate narrow/wide or shuffle-trigger classification questions") for the specific menu anti-pattern.
| **Hard** | Multi-factor trade-off under production constraints. **All 4 distractors plausible** to a candidate who partially understands. | All subtypes | AQE (partition coalescing, broadcast conversion, skew-join), dynamic partition pruning, salting, pandas UDF memory model, Z-ordering vs partitioning, watermark behaviour with late data, speculative execution |

If a hard question's distractors are not all plausible — if a competent practitioner immediately eliminates two — the question is medium dressed as hard.

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses default-value or API-signature recall. Even easy questions are anchored in a realistic Spark situation an engineer would actually reason through.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Predict the output of a `filter`/`select`/`withColumn` chain · trace lazy vs eager evaluation · spot the `AnalysisException` cause · narrow-vs-wide classification on a real snippet. Mental execution tracing, scenario-anchored. |
| **Medium** | "This job shuffles three times — why?" · `repartition` vs `coalesce` for a given write · broadcast-join eligibility for a given size · window frame with `rowsBetween` vs `rangeBetween` · `explode` producing unexpected row counts · Delta MERGE / schema-evolution behaviour. Two defensible options, one better. |
| **Hard** | AQE skew-join coalescing under a real DAG · salting a hot key · pandas-UDF memory model vs regular UDF · watermark behaviour with late data · Z-ordering vs partition pruning trade-off. Production-grade multi-factor trade-off, all distractors plausible. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Transformation vs action (lazy evaluation) → narrow vs wide → DataFrame schema basics → `predict_output` on `filter`/`select`/`withColumn` → UDF basics → `collect()`/`show()` driver implications → common `AnalysisException` debug patterns |
| Medium | Partitioning and partition count → shuffle triggers → `repartition` vs `coalesce` → broadcast join conditions → PySpark window function API and frames (`rowsBetween` / ROWS vs RANGE, cumulative aggregation, tie-handling) → `explode` / `collect_list` / `pivot` for collection and array columns → Delta Lake MERGE / schema evolution / time travel → Structured Streaming output modes |
| Hard | AQE partition coalescing and broadcast conversion → dynamic partition pruning → skew join detection and salting → pandas UDF memory model vs regular UDF → Z-ordering vs partition pruning trade-offs → watermark behaviour with late data → speculative execution and straggler tasks → complex `explode`+pivot patterns and array-column gotchas |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → PySpark section](../concept-taxonomy.md#pyspark--concept-families).

23 canonical families. **PySpark had the worst tag fragmentation in the bank** (493 unique tags / 623 occurrences before consolidation) — many existing tags were mechanic names like `shuffle`, `Catalyst optimizer`, `broadcast join` written lowercase. The new registry forces these into reasoning families: `SHUFFLE REASONING`, `CATALYST OPTIMIZER`, `JOIN STRATEGY SELECTION`. The mechanic terms remain as match patterns *within* families, not as tag values.

Three families are shared with the SQL and Pandas tracks under identical names (the executable-track reusability principle):

- **`DATA QUALITY SKEPTICISM`** — late events, duplicate events, NULL keys, dirty input reasoning
- **`DOUBLE-COUNTING DETECTION`** — fan-out joins (with the PySpark twist that fan-out also amplifies shuffle volume and OOM risk)
- **`OUTPUT SANITY VALIDATION`** — `.count()` plausibility, `.printSchema()` shape checks, row-count assertions before writes

Two cross-track families are **intentionally not** added to PySpark: `METRIC INTERPRETATION & DENOMINATOR CHOICE` (PySpark tests Spark execution reasoning, not business-metric interpretation) and `PERFORMANCE-AWARE ANALYTICS` (PySpark already has 6+ performance-focused families covering this space). See the taxonomy doc's PySpark section for the rationale.

All three are now **practice-grounded** in PySpark — `DATA QUALITY SKEPTICISM` (16 practice / 30 mock), `DOUBLE-COUNTING DETECTION` (4 / 10), `OUTPUT SANITY VALIDATION` (13 / 34). PySpark has **no mock-only realism family** by design — because PySpark is MCQ-only, sanity-check / validation reasoning grades cleanly as `predict_output` / `debug`, so these three lenses are taught and graded in practice (not deferred to mock as in SQL). `MOCK_ONLY_REALISM_FAMILIES["pyspark"] = set()` in `backend/concept_families.py` makes this explicit.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | Scenario-anchored single-concept question. Prefer `predict_output` / `debug` over `conceptual`. |
| Practice medium | `medium.json` no `mock_only` | Trade-off question; two of four options are both defensible but one is better. |
| Practice hard | `hard.json` no `mock_only` | Production-grade multi-factor trade-off. Every distractor plausible. |
| Mock-only medium | `medium.json` with `mock_only: true` | Anchored in a real failure mode — "your job ran 4× longer last night, here's the DAG, what changed?" Heavy `DEBUG SPARK ERRORS`, `JOIN STRATEGY SELECTION`, `SHUFFLE REASONING`, `MEMORY MANAGEMENT`. |
| Mock-only hard | `hard.json` with `mock_only: true` | AQE / skew / streaming-watermark scenarios. `DATA SKEW & MITIGATION`, `ADAPTIVE QUERY EXECUTION`, `STRUCTURED STREAMING`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (cluster size cut in half), business rule (now exactly-once required), data quality (late events), performance (eliminate shuffle X). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and realism, not new execution concepts. A mock-only question recombines Spark-execution reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh failure mode or production scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Coverage & sizing targets

These are the durable *targets* (what the bank ought to look like). For live counts (what it *is* right now) see the "Question bank current state" table in [`docs/content-authoring.md`](../content-authoring.md) and the content footprint in `CLAUDE.md`. **Targets are provisional — revisit against real Pro/Elite usage data.**

- **No mock-only realism family.** PySpark is MCQ-only, so sanity-check / output-validation / data-quality reasoning grades cleanly as `predict_output` or `debug` MCQ. All 3 ⚡ families are practice-grounded; the SQL realism-class rationale does not transfer. The empty `MOCK_ONLY_REALISM_FAMILIES["pyspark"]` set (`backend/concept_families.py`) makes this explicit.
- **Practice: lean, scenario-anchored.** Target ~125–135, with **easy scenario-anchored** (no default-value or API-signature recall — track-doc anti-pattern). All 23 families covered in practice. Tier balance roughly ⅓ each is healthy for the execution-reasoning curriculum.
- **Mock-only: ~150, hard-skewed in principle (~60/40), accepted final at ~50/50.** PySpark's all-4-distractors-plausible bar on hard MCQ is the authoring bottleneck — relaxing it to pad the hard ratio would erode quality, so 50/50 is the accepted floor (see deviation row in the tracker decision log). Medium + hard only (easy is practice-only). **~⅓ chain members** feeding Interview Loop. Format mix favors interview-realism formats: ~30% `predict_output`, ~25–30% `debug`, ~15–20% `optimization`, ~13% `scenario`, ~5% scenario-anchored `conceptual` (away from pure-recall conceptual; pre-Phase-2 was 43% conceptual).

**Mock-only chain inventory (as of 2026-05-26):** 15 chains, each parent (medium) + 2 follow-ups — total 45 chain-member slots, ~30% of 150 mock-only. Dimension coverage: `scale_pivot` 7, `business_rule_pivot` 7, `edge_case_pivot` 6, `performance_pivot` 6, `data_quality_pivot` 3, `stakeholder_pivot` 1 (= 6 of 7 universal dimensions; only `ambiguity_pivot` unused, consistent with PySpark's execution-model curriculum where ambiguous interpretation is rare — most production Spark questions admit a single defensible answer). Documentation gap caught 2026-05-26 alongside the Python chain inventory backfill.
- **Mock distribution weighted by interview importance.** High-priority families: `SHUFFLE REASONING`, `JOIN STRATEGY SELECTION` + `DATA SKEW & MITIGATION`, `ADAPTIVE QUERY EXECUTION`, `STRUCTURED STREAMING` (especially late-data / watermarks), `DELTA LAKE OPERATIONS`, `MEMORY MANAGEMENT` + OOM forensics, `PERFORMANCE TUNING & TRADE-OFFS`. Secondary: `WINDOW FUNCTIONS & FRAMES`, `COLLECTION & ARRAY OPERATIONS`, `UDF & PYTHON BOUNDARY`. Natural chain pivots: `performance_pivot` (eliminate shuffle X), `scale_pivot` (cluster size cut in half), `data_quality_pivot` (late/dirty events), `business_rule_pivot` (now exactly-once required).
- **The bar for every mock-only question: recombination, not reskin.** A mock question that's a practice scenario with cosmetic changes is a clone; recombine the same execution concept under a fresh production-incident framing (`scenario_context` is the right vehicle — see Q43031, Q42050, Q43043 for the gold standard).
- **Distractor quality is a first-class axis.** Hard distractors must ALL be plausible expert positions; if a competent practitioner eliminates any option in <5s, the question is medium dressed as hard (track-doc rule).

## Anti-patterns specific to PySpark

- **Default-value memorization questions** — "what's `spark.sql.shuffle.partitions` by default?" Reject. The answer is unfindable without docs and the question tests no real skill.
- **API-signature questions** — "what's the third argument to `DataFrame.withColumn`?" Reject.
- **Pure-`conceptual` recall at easy tier** — "what is a transformation?" Reject. Use `predict_output` or `debug` to make the candidate reason.
- **Hard questions with one obvious right answer** — if a competent practitioner picks it immediately, the question isn't hard.
- **Questions answerable from a single line of the official docs** — googleable; not the test.
- **Duplicate narrow/wide or shuffle-trigger classification questions** — the bank had two near-identical questions (filter/select/groupBy/withColumn options, same correct answer position) at easy. One was retired. Any future question testing "which of these is a wide transformation / triggers a shuffle?" must use a clearly different scenario or a predict_output framing (e.g. predict partition count after operation X) rather than the same four-operation menu.
- **Easy distractors that are immediately eliminable** — all four MCQ options must require thought. If a competent practitioner can rule out any distractor in under 5 seconds (e.g. "The Driver stores all data in memory"), replace it with a plausible wrong position — one that uses real Spark terminology but draws the wrong conclusion about which component is responsible. The hard-question rule (all 4 distractors plausible) does not apply at easy, but "obviously nonsensical" distractors do not belong at any tier.
- **Disjunctive or version-dependent answers in predict_output / debug questions** — "null values appear OR a runtime exception is thrown" is not a predict_output answer; it is a hedge. If behavior genuinely varies by Spark version, either pin the version in the stem or convert the question to `conceptual` / `debug` framing that asks for diagnosis and fix rather than runtime prediction.
- **Internally inconsistent correct options** — A correct option that partially refutes its own premise within the same text ("the hint should override the threshold — however, the hint cannot override the threshold...") is invalid. The correct answer must commit to a single coherent causal chain. Caveats and qualifications belong in the explanation, not inside the correct option text.
- **Streaming debug questions must map symptoms to the correct diagnosis domain** — Spark UI streaming metrics have distinct meanings: `inputRowsPerSecond` is a source-side metric (Kafka / file source delivering data to Spark); `processedRowsPerSecond` and sink row count are post-watermark metrics (rows evaluated and emitted). `0 input rows/sec` is a source-side stall (Kafka consumer group issue, topic partition stall, offset problem) — it is NOT a watermark late-data-discard symptom. Late-data discard produces **non-zero input with zero emitted output**. Mismatching these in a debug question teaches the wrong debugging reflex.
- **Stale format-target config after type-distribution changes** — After any audit pass that materially changes the type distribution of a difficulty band, update `_pyspark_format_targets` in `backend/routers/mock.py` in the same commit. The slot sequence and docstring comment must reflect the current bank composition (`predict_output(N), conceptual(N), debug(N)`). A lagging config biases benchmark selection toward the old dominant type and misrepresents the improved bank in mock sessions.
- **DPP questions must be consistent on the broadcast coupling.** By default (`spark.sql.optimizer.dynamicPartitionPruning.reuseBroadcastOnly=true`), DPP only activates when there is a broadcast hash join on the dimension side — it reuses the already-broadcast key set to inject the runtime partition filter. Without broadcast, no DPP fires by default. The non-default mode (`reuseBroadcastOnly=false`) allows DPP via an independent subquery scan, but this is non-default and adds overhead. Every DPP question must: (a) state whether the broadcast prerequisite is met or missing, and (b) treat the default coupling as the assumed baseline unless `reuseBroadcastOnly=false` is explicitly set in the stem. Explanations across all DPP questions must agree — a question that says "DPP works without broadcast using a subquery" and a question that says "DPP requires broadcast" are only consistent if one of them specifies the non-default config.

## JSON schema

```json
{
  "id": 43012,
  "order": 9,
  "topic": "pyspark",
  "type": "optimization",
  "difficulty": "hard",
  "title": "Skew join with hot key — choose the mitigation",
  "description": "You're joining `events` (2 TB, hot key: 0.1% of user_ids account for 60% of rows) with `users` (5 GB). The join takes 4 hours, with one stage stuck at 99% for the last 3 hours. AQE skew join handling is enabled but not triggering. Pick the best mitigation.",
  "options": [
    "Increase spark.sql.autoBroadcastJoinThreshold so the users table broadcasts.",
    "Salt the hot keys on events with a random prefix and unsalt after the join.",
    "Increase spark.sql.shuffle.partitions to 4000 to spread the skew.",
    "Repartition events by user_id with 1000 partitions before the join."
  ],
  "correct_option": 1,
  "explanation": "AQE skew-join handling triggers based on partition size thresholds and may not catch all skew patterns, especially with extreme hot keys. Salting is the canonical fix: prefix the hot user_ids with a random salt on events, replicate the matching users rows N ways (one per salt), join, then unsalt. (Option 0) — users is 5 GB, far above any reasonable broadcast threshold; broadcasting would OOM the executors. (Option 2) — more partitions doesn't help: the hot key still hashes to a single partition. (Option 3) — repartitioning by user_id doesn't change the hash distribution; the same hot user_ids still collide.",
  "hints": [
    "AQE skew-join doesn't catch every skew pattern; what's the manual fix when extreme hot keys defeat it?",
    "The fix involves making the hot key *not* a hot key by mixing it with something random."
  ],
  "concepts": ["DATA SKEW & MITIGATION", "JOIN STRATEGY SELECTION", "ADAPTIVE QUERY EXECUTION"]
}
```

Required:
- Exactly 4 options.
- `correct_option` is a **0-indexed integer** (0, 1, 2, or 3).
- Each option ≥ 20 characters (no "Yes" / "No" / "True").
- Explanation refutes **every** distractor (why each wrong option is wrong, not just why the right one is right).
- For `debug`: include the realistic error string the broken code produces.
- For `predict_output`: include the snippet and ask what it returns (or schema it produces).
- For `optimization`: include the production scenario (cluster size, data size, observed behavior).

## Hints discipline

- 1–2 hints typical at easy/medium, 2–3 at hard.
- First hint must **not** name the correct option's key concept verbatim.
- Hints should narrow the option space by elimination, not point at the answer.
- **Common leak patterns to avoid at easy:**
  - Naming the relationship category ("sometimes two method names do exactly the same thing" → directly yields the alias answer)
  - Naming the analogy that is the answer ("think about how SQL UNION works — positional or by name?" → immediately resolves union() direction)
  - Saying "X never raises an error" when the question is asking what happens (eliminates all error-based options in one step)
  - Naming the return value of a side-effect method ("returns None") when the question asks what type is returned
- **For MCQ-specific hints:** guide through an *elimination path* ("which of these options requires a shuffle? start by identifying what data movement each would need") rather than through the answer category. A hint that names the reasoning class of the correct answer is still a leak even if it doesn't name the answer word-for-word.
- **Fix-hints do not belong on predict_output questions.** Telling the candidate how to *fix* the code collapses the guessing space about *what happens* — the presence of a fix implies the current code is broken, and the fix direction often reveals which specific failure mode occurs.

## Verification before commit

```bash
# No execution to verify; the discipline is:
# 1. Walk through each distractor and confirm a competent practitioner could plausibly pick it
# 2. Confirm the explanation refutes each wrong option specifically
# 3. Confirm the "right" answer is unambiguously better, not just defensible

python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k pyspark
```
