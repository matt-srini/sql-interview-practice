# Data Modeling Question Authoring Agent

Use this agent to generate new Data Modeling questions for the platform.

## Track overview

**Track:** `data-modeling`  
**Format:** MCQ / scenario / debug / predict_output  
**Eval kind:** MCQ (no code execution — option selection only)  
**ID space:** Easy `61001–61999` · Medium `62001–62999` · Hard `63001–63999`  
**Content directory:** `backend/content/data_modeling_questions/`

## Question schema

```json
{
  "id": 61001,
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
  "scenario_context": "A data team is designing a warehouse for…",
  "description": "Question that asks a modeling decision about the scenario above.",
  ...
}
```

For **debug** type, description describes a broken schema design and asks what's wrong.

## Difficulty rules

- **Easy:** Single concept family, single decision. Options are clearly distinct. Distractors are wrong for simple, clear reasons. 1–2 hints.
- **Medium:** Compose 2 concept families or present a genuine tradeoff. Scenario type encouraged (~60%). Distractors are tempting. 2–3 hints.
- **Hard:** Multi-family judgment, ambiguous-by-design. The best answer is defensible but not obvious. ALL 4 options ≥20 chars. Distractors represent common expert-level reasoning failures. 2–3 hints. Mostly scenario type.

## Concept families (use these as concept tags)

```
DIMENSIONAL MODELING        NORMALIZATION               DENORMALIZATION TRADEOFF
FACT TABLE DESIGN           GRAIN DEFINITION            DIMENSION DESIGN
SURROGATE VS NATURAL KEYS   SCD STRUCTURE               BRIDGE & MANY-TO-MANY
HIERARCHIES                 PARTITIONING & CLUSTERING   SCHEMA FROM REQUIREMENTS
REFERENTIAL INTEGRITY       DBT MODELING                DATA VAULT
AGGREGATE & SUMMARY DESIGN  WIDE VS NARROW              STORAGE ARCHITECTURE TRADEOFFS
```

Use 2–4 tags per question drawn from (or rolling up to) these families.

## Concept blocklist — FORBIDDEN as concept tags

`star schema`, `snowflake schema`, `fact table`, `dimension table`, `foreign key`,
`primary key`, `scd`, `surrogate key`, `natural key`, `normalization`, `denormalization`,
`grain`, `dbt`, `hub`, `link`, `satellite`

These are too implementation-specific. Use the family names above instead.

## Hint rules

| Difficulty | Min | Max |
|---|---|---|
| easy | 1 | 2 |
| medium | 2 | 3 |
| hard | 2 | 3 |

**First-hint leak patterns — NEVER appear in the first hint:**
- `star schema` / `snowflake schema`
- `slowly changing` / `SCD type`
- `surrogate key`
- `data vault`
- `grain`
- `conformed dimension`

Second/third hints may name mechanisms freely.

## Difficulty arc

**Easy:** Star vs snowflake, normalization intuition (1NF–3NF), fact/dim basics, surrogate keys, SCD Type 1 vs 2 basics, grain definition, denormalization tradeoff intro, dbt staging vs marts, OLAP vs OLTP distinction.

**Medium:** Grain choice in real scenarios, SCD Type 2 vs 3 tradeoffs, bridge tables, dbt materialization, schema-from-requirements scenarios, conformed/role-playing/junk dimensions, referential integrity in analytics, wide-vs-narrow debate.

**Hard:** Data vault design decisions, referential integrity tradeoffs at scale, pre-aggregation strategy, ambiguous schema-from-requirements, complex SCD hybrids (Type 4/6), dbt incremental strategies, OBT vs normalized at scale, lakehouse modeling tradeoffs, accumulating snapshot at wrong grain.

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
