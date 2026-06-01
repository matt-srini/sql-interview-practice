# Data Engineering Track

> **Authoring rule, no exceptions:** Every DE question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/data_engineering_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working data engineer's job isn't to "write more efficient queries" — it's to **design systems that survive Tuesday morning at 9 AM**: when an upstream service double-fires, when a schema drifts, when the cost dashboard spikes, when at-least-once turns out to mean at-least-three-times. The DE track tests systems reasoning: idempotency, watermarks, delivery semantics, schema evolution, cost trade-offs, incident response. These are not academic; they are what every senior DE interview probes and what every production pipeline owner fights with daily.

> *Datathink philosophy applied:* The DE who can name three Spark configs is everywhere. The DE who reads a pipeline diagram and says "this assumes exactly-once but the source guarantees at-least-once — here's where idempotency must live, here's how I'd test it, here's what breaks if I'm wrong" — that's the one whose pager doesn't go off.

## Modality

**Constructed reasoning.** No execution. Response: MCQ (4 options).

Question types:
- **`conceptual`** — conceptual systems reasoning with concrete scenario context, evaluated via single-best-answer MCQ
- **`scenario`** — `scenario_context` field holds the situation; description asks for a decision
- **`debug`** — broken pipeline design; identify what's wrong and what to fix

The track does **not** have `predict_output` as a category (PySpark owns that for code-adjacent reasoning); DE questions describe pipeline behaviour in prose, not code.

## ID range (TXNNN scheme)

`T=5` for DE.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 51001–51999 | `backend/content/data_engineering_questions/easy.json` |
| Medium | 52001–52999 | `backend/content/data_engineering_questions/medium.json` |
| Hard | 53001–53999 | `backend/content/data_engineering_questions/hard.json` |

Data Engineering has **dedicated sample questions** in `backend/content/sample_questions/data_engineering.json` (IDs 511–513 easy, 521–523 medium, 531–533 hard). Sample questions are completely separate from the practice and mock pools and must never duplicate practice content.

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | Single concept, clear scenario, distractors wrong for simple clear reasons | ETL vs ELT, idempotency basics, DAG-based scheduling, batch vs streaming, partitioning intuition, basic SCDs |
| **Medium** | 2 concept families composed OR a genuine trade-off; distractors are tempting | Schema-evolution trade-offs, watermarks and late-data handling, delivery semantics (at-least-once / at-most-once / exactly-once), backfill idempotency, small-file problem, partitioning strategy |
| **Hard** | Multi-family judgement, ambiguous-by-design; best answer defensible but not obvious; distractors represent common expert-level mistakes | Exactly-once semantics across boundaries, incident response, lineage debugging under silent failures, partition-granularity cost trade-offs, schema-registry compatibility modes, data-contract violations |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses tool-trivia or config-default recall. Even easy questions are anchored in a realistic pipeline situation.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Choose ETL vs ELT for a stated need · why a retried task must be idempotent · batch vs streaming for a given latency requirement · partitioning intuition for a query pattern. Single concept, clear scenario. |
| **Medium** | "Consumer lag is growing — choose the fix" · which delivery semantic a use case needs · handling late data with watermarks · the small-file problem on a given write pattern. A genuine trade-off with tempting distractors. |
| **Hard** | Exactly-once across a source→sink boundary · lineage debugging under a silent failure · partition-granularity cost trade-off under an SLA · schema-registry compatibility under producer/consumer disagreement. Multi-family judgement, ambiguous by design. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | ETL vs ELT → idempotency basics → DAG / orchestration basics → batch vs streaming → partitioning intuition → SCD types |
| Medium | Schema evolution + backward compatibility → watermarking + late data → delivery semantics → backfill idempotency → small-file problem → CDC mechanics |
| Hard | Exactly-once across boundaries → incident response patterns → lineage debugging → partition-granularity cost trade-offs → schema-registry compatibility modes → data contracts under producer/consumer disagreement |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Data Engineering section](../concept-taxonomy.md#data-engineering--concept-families).

21 families. **This track had the cleanest pre-existing tag discipline in the bank** (41 unique tags, top 20 cover 95% of usage) — the registry mostly formalises what authors were already doing.

## Coverage & sizing targets

**Phase 2 complete (2026-05-24).** 96 new mock-only questions authored and committed.

| Difficulty | Practice | Mock-only | Total |
|---|---|---|---|
| Easy | 30 | 0 | 30 |
| Medium | 35 | 34 | 69 |
| Hard | 26 | 76 | 102 |
| **Total** | **91** | **110** | **201** |

**Ratio:** 110 / 91 = **1.21×** (within the 1.20× ± 5pp target band locked at Stage A).

**Mock-only chain inventory (post retro-cleanup 2026-05-25):** 13 chains total — 5 medium (parents at 52045/52047/52050/52052/52054; note: 52052 was dissolved when its child 52053 re-tiered to hard) + 8 hard (parents at 53035/53038/53040/53043/53045/53048/53051/53053) + the chain 53089/53090/53091 (re-tiered from medium to hard together, intact). 7 follow-up dimensions remain covered.

**Type distribution (mock-only, post retro-cleanup):**
- Medium (34 total): 16 INCIDENT RESPONSE questions re-tiered to hard; remaining mix of scenario, debug, conceptual
- Hard (76 total): includes the 16 re-tiered INCIDENT RESPONSE questions (scenario/debug/conceptual)

**Mock-only difficulty split rationale.** Post retro-cleanup, mock m:h = 34:76 ≈ 1:2.24 — heavier hard-skew than other tracks (PySpark 1:1.0, SQL 1:1.22, Pandas 1:1.20, DM 1:1.13). This is **corrected** content, not over-shift: the 16 re-tiered INCIDENT RESPONSE questions exercise multi-family judgement under ambiguous conditions (on-call triage, cascading-failure diagnosis, postmortem framing, containment+recovery sequencing) — intrinsically hard-tier reasoning per `docs/content-authoring.md` § Difficulty model (`Hard` = "2+ dependent reasoning steps, trade-offs, edge-case awareness, production-grade thinking"). The original Stage B mis-tiered these at medium because the mock difficulty target was a soft anchor; the family character is the binding constraint. Audited spot-check on 3 questions (53087, 53092, 53102 — beginning, chain-dissolution case, end of range) confirmed hard-tier reasoning bar on all three.

**DATA CONTRACT family resurrected via pattern fix.** The DE registry had a shadow bug: `"DATA CONTRACT"` appeared as a match pattern under SCHEMA EVOLUTION (preceded DATA CONTRACT family in dict order), making the DATA CONTRACT family unreachable. 23 existing questions tagged literal `"DATA CONTRACT"` all resolved to SCHEMA EVOLUTION. Fix applied 2026-05-25 (remove the pattern from SCHEMA EVOLUTION). Post-fix: DATA CONTRACT family covers 21 mock-only + 2 practice questions; well above rule-2 floor. SCHEMA EVOLUTION remains well above floor as well.

**No mock-only realism families.** All 21 DE concept families are practice-grounded and directly gradeable as MCQ. `MOCK_ONLY_REALISM_FAMILIES["data-engineering"] = set()` enforced in `concept_families.py`. Track is in `_TAXONOMY_VALIDATED_TRACKS` in `validate_content.py`.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | Single concept, clear scenario. Distractors clearly wrong. |
| Practice medium | `medium.json` no `mock_only` | Trade-off question; scenario type encouraged. Tempting distractors. |
| Practice hard | `hard.json` no `mock_only` | Multi-family judgement. Every option a defensible expert-level position. |
| Mock-only medium | `medium.json` with `mock_only: true` | Anchored in real incident framings: "your pipeline fired duplicates last night, diagnose"; "consumer lag is growing, choose"; "the producer changed schema, what breaks?" |
| Mock-only hard | `hard.json` with `mock_only: true` | Multi-system scenarios under cost / SLA / compliance pressure. `EXACTLY-ONCE`, `LINEAGE & OBSERVABILITY`, `INCIDENT RESPONSE`, `COST OPTIMIZATION`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (throughput 100×), business rule (compliance requires GDPR exclusion), data quality (schema drift), performance (cost spike), ambiguity (is this batch or streaming?). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and incident realism, not new concepts. A mock-only question recombines DE reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh incident or production scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Anti-patterns specific to DE

- **Tool-name questions** — "what's Airflow's equivalent of cron?" Reject. Test the *concept* (DAG-based scheduling, dependencies), not the brand.
- **Hard questions where one option is the famous correct answer** — "exactly-once: which option is the right way?" Every distractor must reflect a real expert-level position someone has defended.
- **MCQ that's actually a checklist** — if the right answer is "all of the above," the question is testing memorisation, not reasoning.
- **Questions about a config flag's default value** — same as PySpark; not the test.
- **Scenarios that don't read like real incidents** — "imagine you have a pipeline" is weaker than "your overnight pipeline ran at 3:14 AM, started failing at 4:02 AM, the on-call sees this in logs..."
- **Schema registry compatibility claimed as a generated-code guard** — FULL/BACKWARD compatibility validates field numbers and types at wire-format level only. A Protobuf field rename that keeps the same field number passes FULL wire-compatibility even though it breaks consumers whose generated class now exposes a different attribute name. The correct structural fix for that failure class is consumer contract testing gated in the producer's publishing pipeline — not a schema registry rule. Separately, FULL is non-transitive: a consumer reading all historical schema versions needs FULL_TRANSITIVE, not FULL alone.
- **Wrong Kafka partition numbering** — Partition IDs are sequential integers starting at 0. Expanding a topic from 3 to 5 partitions adds partitions 3 and 4; original partitions stay 0, 1, 2. Any scenario implying a non-sequential original set (e.g., "partitions 0, 1, 3 were consumed before the expansion") is impossible. Verify partition numbers before publishing.

## JSON schema

```json
{
  "id": 53008,
  "order": 6,
  "title": "Idempotent backfill under at-least-once source",
  "difficulty": "hard",
  "type": "scenario",
  "scenario_context": "You own a daily pipeline that reads from a Kafka topic with at-least-once delivery, deduplicates by event_id, and writes to a Snowflake fact table with CLUSTER BY (event_date). The downstream BI team relies on the fact for daily revenue reporting. Yesterday's run failed mid-write; you need to re-run for the missing date range and the next two days have already loaded successfully.",
  "description": "What's the safest backfill strategy?",
  "options": [
    "Replay from the Kafka offset corresponding to the start of yesterday; the dedup step will handle duplicates.",
    "Delete yesterday's date range from the fact table, then re-run the pipeline for just that day; downstream BI can be re-queried.",
    "Append the missing rows by reading from a Kafka tier-2 archive bucket filtered to yesterday's events; merge into the fact.",
    "Re-run yesterday's pipeline in dry-run mode, diff against the partial output, then apply only the missing rows."
  ],
  "correct_option": 1,
  "explanation": "Option 1 is canonical: idempotent date-range overwrite is the cleanest pattern for daily batches. Because Snowflake uses micro-partition clustering on event_date (not user-defined partitions), the safe equivalent is a DELETE WHERE event_date = '<yesterday>' followed by a full reload for that day — this leaves adjacent days' micro-partitions untouched. The dedup-on-event-id property of the pipeline means re-running produces the same result regardless of upstream replays. (Option 0) re-reads from offset but doesn't reset the partial fact-table state — the delete+reload is the discipline. (Option 2) tier-2 archives may not match the original event stream exactly (some sources only retain certain events in archive); introduces drift risk. (Option 3) diffing against partial output is an anti-pattern; you can't trust the partial state if the failure cause is unknown.",
  "hints": [
    "What pipeline property makes 're-run' safe regardless of how many times the source replays?",
    "Date-range-aligned deletes give you a natural atomicity boundary in Snowflake — use it."
  ],
  "concepts": ["IDEMPOTENCY", "BACKFILL DESIGN", "PARTITIONING & PRUNING"]
}
```

Required:
- Exactly 4 options, each ≥ 20 characters.
- `correct_option` 0-indexed integer.
- Explanation refutes every distractor.
- `scenario` type includes `scenario_context`; `debug` type's description describes a broken pipeline.

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k data_engineering
```

Eyeball discipline: walk each distractor and confirm a competent DE could plausibly defend it. If you eliminate any option in <5 seconds, the question is too easy for the tier.
