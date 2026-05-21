# Data Engineering Track

> **Authoring rule, no exceptions:** Every DE question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/data_engineering_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working data engineer's job isn't to "write more efficient queries" — it's to **design systems that survive Tuesday morning at 9 AM**: when an upstream service double-fires, when a schema drifts, when the cost dashboard spikes, when at-least-once turns out to mean at-least-three-times. The DE track tests systems reasoning: idempotency, watermarks, delivery semantics, schema evolution, cost trade-offs, incident response. These are not academic; they are what every senior DE interview probes and what every production pipeline owner fights with daily.

> *Datathink philosophy applied:* The DE who can name three Spark configs is everywhere. The DE who reads a pipeline diagram and says "this assumes exactly-once but the source guarantees at-least-once — here's where idempotency must live, here's how I'd test it, here's what breaks if I'm wrong" — that's the one whose pager doesn't go off.

## Modality

**Constructed reasoning.** No execution. MCQ / scenario / debug / predict_output. Every question is multiple-choice with exactly 4 options.

Subtypes:
- **`mcq`** — conceptual with concrete scenario context
- **`scenario`** — `scenario_context` field holds the situation; description asks for a decision
- **`debug`** — broken pipeline design; identify what's wrong and what to fix

The track does **not** have `predict_output` as a category currently (PySpark owns that for code-adjacent reasoning); DE questions describe pipeline behaviour in prose, not code.

## ID range (TXNNN scheme)

`T=5` for DE.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 51001–51999 | `backend/content/data_engineering_questions/easy.json` |
| Medium | 52001–52999 | `backend/content/data_engineering_questions/medium.json` |
| Hard | 53001–53999 | `backend/content/data_engineering_questions/hard.json` |

DE samples are auto-sliced from the first 3 practice questions per difficulty (no dedicated sample IDs).

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | Single concept, clear scenario, distractors wrong for simple clear reasons | ETL vs ELT, idempotency basics, DAG-based scheduling, batch vs streaming, partitioning intuition, basic SCDs |
| **Medium** | 2 concept families composed OR a genuine trade-off; distractors are tempting | Schema-evolution trade-offs, watermarks and late-data handling, delivery semantics (at-least-once / at-most-once / exactly-once), backfill idempotency, small-file problem, partitioning strategy |
| **Hard** | Multi-family judgement, ambiguous-by-design; best answer defensible but not obvious; distractors represent common expert-level mistakes | Exactly-once semantics across boundaries, incident response, lineage debugging under silent failures, partition-granularity cost trade-offs, schema-registry compatibility modes, data-contract violations |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | ETL vs ELT → idempotency basics → DAG / orchestration basics → batch vs streaming → partitioning intuition → SCD types |
| Medium | Schema evolution + backward compatibility → watermarking + late data → delivery semantics → backfill idempotency → small-file problem → CDC mechanics |
| Hard | Exactly-once across boundaries → incident response patterns → lineage debugging → partition-granularity cost trade-offs → schema-registry compatibility modes → data contracts under producer/consumer disagreement |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Data Engineering section](../concept-taxonomy.md#data-engineering--concept-families).

21 families. **This track had the cleanest pre-existing tag discipline in the bank** (41 unique tags, top 20 cover 95% of usage) — the registry mostly formalises what authors were already doing.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | Single concept, clear scenario. Distractors clearly wrong. |
| Practice medium | `medium.json` no `mock_only` | Trade-off question; scenario type encouraged. Tempting distractors. |
| Practice hard | `hard.json` no `mock_only` | Multi-family judgement. Every option a defensible expert-level position. |
| Mock-only medium | `medium.json` with `mock_only: true` | Anchored in real incident framings: "your pipeline fired duplicates last night, diagnose"; "consumer lag is growing, choose"; "the producer changed schema, what breaks?" |
| Mock-only hard | `hard.json` with `mock_only: true` | Multi-system scenarios under cost / SLA / compliance pressure. `EXACTLY-ONCE`, `LINEAGE & OBSERVABILITY`, `INCIDENT RESPONSE`, `COST OPTIMIZATION`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (throughput 100×), business rule (compliance requires GDPR exclusion), data quality (schema drift), performance (cost spike), ambiguity (is this batch or streaming?). |

**Easy mock-only: never.**

## Anti-patterns specific to DE

- **Tool-name questions** — "what's Airflow's equivalent of cron?" Reject. Test the *concept* (DAG-based scheduling, dependencies), not the brand.
- **Hard questions where one option is the famous correct answer** — "exactly-once: which option is the right way?" Every distractor must reflect a real expert-level position someone has defended.
- **MCQ that's actually a checklist** — if the right answer is "all of the above," the question is testing memorisation, not reasoning.
- **Questions about a config flag's default value** — same as PySpark; not the test.
- **Scenarios that don't read like real incidents** — "imagine you have a pipeline" is weaker than "your overnight pipeline ran at 3:14 AM, started failing at 4:02 AM, the on-call sees this in logs..."

## JSON schema

```json
{
  "id": 53008,
  "order": 6,
  "title": "Idempotent backfill under at-least-once source",
  "difficulty": "hard",
  "type": "scenario",
  "scenario_context": "You own a daily pipeline that reads from a Kafka topic with at-least-once delivery, deduplicates by event_id, and writes to a Snowflake fact table partitioned by event_date. The downstream BI team relies on the fact for daily revenue reporting. Yesterday's run failed mid-write; you need to re-run for the missing partition and the next two days have already loaded successfully.",
  "description": "What's the safest backfill strategy?",
  "options": [
    "Replay from the Kafka offset corresponding to the start of yesterday; the dedup step will handle duplicates.",
    "Truncate the failed partition, then re-run the pipeline for just that partition; downstream BI can be re-queried.",
    "Append the missing rows by reading from a Kafka tier-2 archive bucket filtered to yesterday's events; merge into the fact.",
    "Re-run yesterday's pipeline in dry-run mode, diff against the partial output, then apply only the missing rows."
  ],
  "correct_option": 1,
  "explanation": "Option 1 is canonical: idempotent partition overwrite is the cleanest pattern for daily batches. The fact's partitioning by event_date means yesterday's partition can be safely truncated and rebuilt without affecting the next two days' partitions. The dedup-on-event-id property of the pipeline means re-running produces the same result regardless of upstream replays. (Option 0) re-reads from offset but doesn't reset the partial fact-table state — the truncate is the discipline. (Option 2) tier-2 archives may not match the original event stream exactly (some sources only retain certain events in archive); introduces drift risk. (Option 3) diffing against partial output is an anti-pattern; you can't trust the partial state if the failure cause is unknown.",
  "hints": [
    "What pipeline property makes 're-run' safe regardless of how many times the source replays?",
    "Partition-aligned writes give you a natural atomicity boundary — use it."
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
