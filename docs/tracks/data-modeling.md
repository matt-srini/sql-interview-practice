# Data Modeling Track

> **Authoring rule, no exceptions:** Every Data Modeling question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/data_modeling_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working data architect / analytics engineer / senior analyst gets paid to **answer a stakeholder's question with a schema that won't lie at scale**. Pick the wrong grain → metrics drift. Pick the wrong SCD type → history is unreadable. Denormalize too aggressively → integrity erodes silently. Conform a dimension across two source systems badly → exec dashboards show different numbers depending on who joined what. The Data Modeling track tests these design decisions — which are where the real-world failure modes live.

> *Datathink philosophy applied:* The modeller who recites "star vs snowflake" is everywhere. The modeller who reads a fuzzy stakeholder brief, names the grain ambiguity, defends a fact-table design under cross-system constraints, and shows you exactly where the double-counting risk is — that's the one whose schema survives the company growing 3×.

## Modality

**Constructed reasoning.** No execution. Response: MCQ (4 options).

Question types:
- **`conceptual`** — modeling decision evaluated via single-best-answer MCQ
- **`scenario`** — `scenario_context` carries the business / system situation; description asks for the design call
- **`debug`** — `scenario_context` describes a broken model or query output; description asks for the root cause and fix (mock-only only; never in the practice bank)

## ID range (TXNNN scheme)

`T=6` for Data Modeling.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 61001–61999 | `backend/content/data_modeling_questions/easy.json` |
| Medium | 62001–62999 | `backend/content/data_modeling_questions/medium.json` |
| Hard | 63001–63999 | `backend/content/data_modeling_questions/hard.json` |

DM samples are auto-sliced from the first 3 practice questions per difficulty.

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | Single modeling concept, clear right answer | Star vs snowflake, 1/2/3NF, fact-table types (transaction / periodic / accumulating), surrogate vs natural keys, grain definition |
| **Medium** | Grain decisions under ambiguity, SCD trade-offs | SCD Type 2 vs 3 vs 4, bridge tables, Data Vault basics, schema from requirements, denormalization trade-offs |
| **Hard** | Multi-hop grain alignment, conflicting requirements, governance | Multi-hop grain alignment, SCD under conflicting requirements, Data Vault vs Kimball, conformed-dimension governance, bi-temporal modeling, semantic layer trade-offs |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses vocabulary trivia. Even easy questions are anchored in a realistic modeling decision.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Star vs snowflake for a stated reporting need · pick the fact-table type for an event · surrogate vs natural key for a given source · state the grain of a simple fact. One concept, clear right answer. |
| **Medium** | Choose an SCD type under a change-tracking requirement · resolve a many-to-many with a bridge · infer a schema from a short stakeholder brief · denormalization trade-off for a query pattern. Grain/SCD decisions under ambiguity. |
| **Hard** | Align grain across multiple facts · conformed-dimension governance across two source systems · Data Vault vs Kimball under conflicting requirements · bi-temporal modeling. Multi-hop judgement under conflicting requirements. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Star vs snowflake → 1NF / 2NF / 3NF → fact-table types → surrogate vs natural keys → grain definition basics |
| Medium | Grain under ambiguity → SCD Type 2 vs 3 vs 4 → bridge tables for many-to-many → Data Vault basics → schema from requirements → denormalization trade-offs |
| Hard | Multi-hop grain alignment → SCD under conflicting requirements → Data Vault vs Kimball → conformed-dimension governance → bi-temporal modeling → semantic-layer + metric-governance trade-offs |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Data Modeling section](../concept-taxonomy.md#data-modeling--concept-families).

22 families. **Already well-formed pre-existing registry** (44 unique tags, top 15 cover 90%) — formalisation is mostly endorsement of current practice.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One modeling concept, clean. |
| Practice medium | `medium.json` no `mock_only` | Trade-off under ambiguity. |
| Practice hard | `hard.json` no `mock_only` | Multi-system / conflicting-requirement design. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real stakeholder briefs: "Marketing wants this attribution; Finance wants that. Design the fact." Heavy `GRAIN DEFINITION`, `SCHEMA FROM REQUIREMENTS`, `BRIDGE & MANY-TO-MANY`. |
| Mock-only hard | `hard.json` with `mock_only: true` | M&A scenarios (conformed dimensions across two companies), metric deprecation, zero-downtime migrations. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: business rule (definition shifts), scale (dimension grows 100×), data quality (conflicting source attributes), stakeholder (DS team wants different grain). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and stakeholder realism, not new concepts. A mock-only question recombines modeling reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh stakeholder brief or migration scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Anti-patterns specific to DM

- **"Star schema is always right"** questions — when the answer is "snowflake" or "OBT" or "Data Vault depending on context," frame the trade-off, don't crown a winner.
- **Trivia about Kimball/Inmon vocabulary** — "what did Kimball call X?" Reject. Test the *idea*, not the historical naming.
- **Questions where the grain is given to you** — the test is usually *picking* the grain; if you hand the candidate the grain, you've removed the reasoning.
- **Schema from requirements with the "right" answer prescribed** — real briefs are ambiguous; the candidate's job is to name the ambiguity and defend a reading.

## JSON schema

```json
{
  "id": 62019,
  "order": 12,
  "title": "Choose the SCD type for a customer-attribute that changes monthly with full audit requirement",
  "difficulty": "medium",
  "type": "scenario",
  "scenario_context": "A B2C company tracks customer-tier (Bronze / Silver / Gold / Platinum). Tier is recomputed monthly based on rolling 90-day spend. The CFO wants every historical month's revenue report to use the tier the customer held *at the time of the order*, not their current tier. The compliance team additionally requires a full audit trail of when tier changes happened.",
  "description": "What's the right SCD strategy on the customer dimension?",
  "options": [
    "SCD Type 1: overwrite tier each month — simplest, since most BI uses current state.",
    "SCD Type 2 with effective_from / effective_to dates — preserves history per row.",
    "SCD Type 3: keep current and previous tier columns — quick comparison without table growth.",
    "SCD Type 4: separate history table with all tier changes timestamped; current state in main dim."
  ],
  "correct_option": 1,
  "explanation": "SCD Type 2 is canonical here. Fact rows join to the tier valid at order_date via effective_from / effective_to range condition. (Option 0) violates the CFO requirement — overwriting loses the historical tier. (Option 2) only keeps one previous value; with monthly recompute over a long history, you lose anything older than 2 months ago. (Option 3) is defensible but heavier — Type 2 inline gives the audit trail without a separate join, and the row-count growth (12 tier-change-rows/year/customer in the worst case) is well within fact-table-join cost. Type 4 is a reasonable second choice but Type 2 is simpler when the fact volume isn't enormous.",
  "hints": [
    "Both requirements force you to keep more than one historical value per customer.",
    "Which SCD type lets fact rows join to the version-at-time-of-event naturally?"
  ],
  "concepts": ["SCD STRUCTURE", "DIMENSION DESIGN", "BI-TEMPORAL MODELING"]
}
```

Required:
- Exactly 4 options, each ≥ 20 characters.
- Explanation refutes every distractor.
- Scenario type includes substantive `scenario_context` (real business detail, real constraints).

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k data_modeling
```
