# Data Engineering Question Authoring Agent

Use this agent to generate new Data Engineering Concepts questions for the platform.

## Track overview

**Track:** `data-engineering`  
**Format:** MCQ / scenario / debug / predict_output  
**Eval kind:** MCQ (no code execution — option selection only)  
**ID space:** Easy `51001–51999` · Medium `52001–52999` · Hard `53001–53999`  
**Content directory:** `backend/content/data_engineering_questions/`

## Question schema

```json
{
  "id": 51001,
  "order": 1,
  "title": "Short title (≤60 chars)",
  "difficulty": "easy",
  "type": "mcq",
  "description": "Full question text.",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_option": 0,
  "explanation": "Why correct option is right and why each distractor is wrong.",
  "hints": ["First hint (no mechanism leak — see rules)", "Second hint"],
  "concepts": ["CONCEPT FAMILY 1", "CONCEPT FAMILY 2"]
}
```

For **scenario** type, also include `scenario_context` (string describing the situation):

```json
{
  ...
  "type": "scenario",
  "scenario_context": "A streaming pipeline processes…",
  "description": "Question that asks a decision about the scenario above.",
  ...
}
```

For **debug** type, description describes a broken pipeline design and asks what's wrong.

## Difficulty rules

- **Easy:** Single concept family, single decision. Options are clearly distinct. Distractors are wrong for simple, clear reasons. One-concept tag minimum.
- **Medium:** Compose 2 concept families or present a genuine tradeoff. Scenario type encouraged. Distractors are tempting. 2–3 hints.
- **Hard:** Multi-family judgment, ambiguous-by-design. The best answer is defensible but not obvious. Distractors should represent common expert-level mistakes. All scenario option strings ≥20 chars. 2–3 hints.

## Concept families (use these as concept tags)

```
ETL VS ELT          IDEMPOTENCY         BACKFILL DESIGN     ORCHESTRATION
SCHEDULING & SLAS   SCHEMA EVOLUTION    BATCH VS STREAMING  WATERMARKING
DELIVERY SEMANTICS  PARTITIONING & PRUNING  STORAGE LAYOUT & FILE FORMATS
CDC & INGESTION     DATA QUALITY        LINEAGE & OBSERVABILITY
SCD OPERATIONS      STORAGE ARCHITECTURE  COST OPTIMIZATION  INCIDENT RESPONSE
```

Use 2–4 tags per question drawn from (or rolling up to) these families.

## Concept blocklist — FORBIDDEN as concept tags

`airflow`, `spark`, `kafka`, `flink`, `dbt`, `s3`, `glue`, `task`, `operator`,
`sensor`, `trigger`, `pipeline`, `etl`, `elt`, `cron`

These are too implementation-specific. Use the family names above instead.

## Hint rules

| Difficulty | Min | Max |
|---|---|---|
| easy | 1 | 2 |
| medium | 2 | 3 |
| hard | 2 | 3 |

**First-hint leak patterns — NEVER appear in the first hint:**
- `idempoten` / `idempotency` / `idempotent`
- `watermark`
- `exactly-once` / `exactly once`
- `SCD`
- `change data capture`
- `backfill`
- `at-least-once` / `at least once`
- `at-most-once` / `at most once`

Second/third hints may name mechanisms freely.

## Difficulty arc

**Easy:** ETL/ELT, idempotency, basic orchestration, partitioning, SCD basics, storage architecture.  
**Medium:** Schema evolution, batch/streaming tradeoffs, watermarking, data quality, cost.  
**Hard:** Exactly-once, incident response, observability under failure, multi-system tradeoffs.

## ID assignment rules

- IDs are append-only. Never reuse or renumber existing IDs.
- Check the current highest ID in easy/medium/hard.json before authoring.
- Assign the next sequential ID. Set `order` to the next sequential order number.
- Mock-only questions use `"mock_only": true` and live at the top of each difficulty range (after practice questions).
- Easy questions have no mock-only variants by design.

## Quality checklist per question

- [ ] Description is clear and unambiguous
- [ ] Correct option is definitively right
- [ ] Distractors represent real misconceptions (not strawman answers)
- [ ] Explanation tells you why each distractor is wrong, not just why the correct one is right
- [ ] `concepts` tags are 2–4 items, not in the blocklist, drawn from the family list
- [ ] `hints` count is within the min/max for the difficulty
- [ ] First hint does not contain any leak-pattern words
- [ ] For scenario type: `scenario_context` is present; all 4 options are ≥20 chars

## Workflow

1. Read the existing question files to find the next available ID and order.
2. Author the requested questions following the schema exactly.
3. Append the new questions to the appropriate difficulty JSON file (do not rewrite the whole file if adding to an existing bank).
4. Run `python scripts/validate_content.py` from `backend/` to verify.
5. Report the IDs and titles of questions authored.
