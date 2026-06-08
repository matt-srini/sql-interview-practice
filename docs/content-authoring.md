# Content Authoring — cross-track contract

> **Authoring rule, no exceptions:** Every question on this platform is created or modified through [`.github/agents/question-authoring.agent.md`](../.github/agents/question-authoring.agent.md). Direct edits to question JSON files bypass the difficulty arc, the concept-taxonomy registry, the hint guardrails, the verification checklist, and the ID-scheme contract — and have historically been the largest source of content drift on this platform. If you are tempted to edit a question file by hand, stop and invoke the agent instead. This rule has no exceptions.

This doc is the **cross-track contract** for content authoring on datathink. It owns:

- the platform philosophy (verbatim)
- the cross-track quality bar
- the difficulty model
- the authoritative `TXNNN` ID scheme
- the hint discipline
- the concept-tag contract (pointing at the taxonomy registry)
- the mock-only contract reference (pointing at the mock SoT)
- verification commands

**Per-track specifics** — datasets, modality, concept arcs, per-track JSON schemas, anti-patterns — live in each track's dedicated doc under [`docs/tracks/`](./tracks/). This file does not duplicate that content.

---

## Index of authoring sources

| File | Role |
|---|---|
| `.github/agents/question-authoring.agent.md` | The mandatory authoring entry point. Procedure + cross-track quality bar. |
| `docs/content-authoring.md` (this file) | Cross-track contract: philosophy, ID scheme, hint discipline, concept-tag rules, mock-only contract reference. |
| `docs/tracks/<track>.md` × 9 | Per-track knowledge: philosophy applied per track, modality, datasets, ID range, difficulty vocabulary, concept arc, anti-patterns, full JSON schema, verification. |
| `docs/concept-taxonomy.md` | Canonical concept-family registry per track + 7 universal follow-up dimensions. Validator-enforced. |
| `docs/concept-hooks.md` | Socratic interview-hook inventory (seeding tool for concept coverage; informational, not enforced). |
| `docs/features/mock.md` | Canonical plan-tier matrix + chain atomicity contract + Interview Loop spec. |
| `docs/specs/mock-benchmark-spec.md` | Benchmark invariants, blueprint principles, chain schema, Loop selection logic. |
| `docs/datasets.md` | All dataset tables, row counts, intentional edge cases (NULLs, duplicates, orphans). |
| `docs/specs/platform-north-star.md` | Product North Star + role-to-track framing + philosophy verbatim. |
| `docs/specs/practice-modality-spec.md` | Modality matrix (executable / code-adjacent / constructed / hybrid). |

When this doc and a track doc disagree, the **track doc wins** for per-track specifics. When this doc and the concept-taxonomy disagree, the **taxonomy wins** for tag/family rules. When this doc and mock.md disagree, **mock.md wins** for plan gating and chain mechanics.

---

## The datathink philosophy (canonical, verbatim)

> We live in an era defined by data. Every transaction, interaction, and decision leaves a digital trace — and the volume of this data is growing faster than our collective ability to make sense of it.
>
> But data, on its own, means nothing. The real work is generating meaning from it — building systems that store it efficiently, retrieve it reliably, model it thoughtfully, and ultimately transform raw signal into insight that drives better decisions, better products, and better outcomes for people.
>
> This work gave rise to an entire class of technical professions: data engineers who design the pipelines, analysts who surface the patterns, scientists who build the models, and architects who ensure the systems scale. These are not peripheral roles — they are increasingly the backbone of how modern organizations function and grow.
>
> Datathink exists for these professionals — and for those becoming them.
>
> Not as another platform of interview puzzles to crack before a hiring deadline, but as a place to develop the kind of reasoning that makes someone genuinely effective in a data-driven world. The kind of professional who doesn't just write a correct query, but understands why the data is structured the way it is, what question is really worth asking, and how the answer should inform a decision.
>
> If that preparation also makes you exceptional in interviews — and it will — that's a consequence, not the goal.

## The one test every question must pass

**Primary:**
> *Does this question build the kind of reasoning a practicing data professional would still rely on years into the role?*

**Secondary (grounding only):**
> *And would the same reasoning earn the offer in a real interview screen?*

Reasoning depth — not syntax recall, not trivia, not concept-stacking — is the product. If the primary answer is no, reject.

---

## Cross-track quality bar

### What good questions do

- Test *why an approach works* (which join direction, which window frame, which estimator, which schema grain), not whether you remember a keyword.
- Mirror real business / engineering scenarios using the real datasets and real failure modes.
- Teach one durable, transferable concept.
- Slot into a learning arc — each tier builds on the previous tier's mental models.

### Reject on sight

- One-liners whose only challenge is knowing a function / API name.
- Academic toy problems with no connection to real data work.
- Multiple defensible interpretations of the expected output.
- Redundant coverage: 3+ questions testing the same pattern with cosmetic differences.
- Artificial difficulty from stacking 6+ unrelated requirements.
- (MCQ tracks) Distractors no competent practitioner would pick, or questions with multiple correct answers depending on version / assumptions.
- (MCQ tracks) Any two options with identical observable outputs — e.g., two options that produce the same schema string, the same printed value, the same error type, or the same numeric result. All options must be observably distinguishable regardless of how many converge on the same outcome. Distinct options must be wrong (or right) for distinct, independently observable reasons.
- (MCQ tracks) A distractor that contradicts its own stated conclusion within its own text (e.g. a header claiming "2 jobs" while the body explicitly computes 3) is invalid — it is eliminated on sight and provides no reasoning challenge.
- **(MCQ tracks) Option text must not embed a label that collides with the option's own A/B/C/D position.** The canonical failure modes: an option whose text begins "Approach D — …" while it sits in position **C** (the scenario lettered its approaches A–D in a different order than the options are listed), or options prefixed "Option A is best: / Option B is best: …" that re-letter the choices. Both reliably make solvers — and reviewers — answer the *embedded* letter instead of the *position* letter (caught in ml-fundamentals 83011, pyspark 42105, 43081, 83034; data-engineering 52051; pyspark sample 421; even strong models flipped their answer — the Phase-2 external-model audit independently confirmed the flips). Describe each choice on its own terms with **no** "Approach X —" / "Option X is best:" prefix. The discriminator must be the content, never a letter the candidate has to reconcile against the position. **Machine-enforced (since 2026-06-04): `validate_content.py` § `_validate_no_embedded_option_labels` raises ERROR on any *cross-position* embed (option text names a choice-word — Option/Proposal/Approach/Strategy/Design/Method — followed by a letter different from the option's own position) and emits a WARN for the milder *self-matching* prefix ("Option A —" at position A — the whole bank was cleaned of these on 2026-06-04, incl. a 25-question data-modeling option-prefix template; the WARN now guards against reintroduction). Domain-entity labels ("Variant A" for an experiment arm, "Group B" for a cohort) are excluded — only choice-naming words match. Explanations are exempt: they may reference answer positions as "Option A/B/C/D" (the canonical letter convention).
- **(MCQ tracks) Reference options by LETTER (A/B/C/D) in explanations, never by number.** The UI labels options A–D (`MCQPanel.js`), so "Option 0/1/2/3" reads wrong to users and — because the numeric convention drifted between 0-indexed and 1-indexed across the bank — it masked a real key inversion (pyspark 43112: explanation said "Option 2 is the most plausible" while `correct_option` was 1). Always write the answer's identity as its **letter**. Machine-enforced: `validate_content.py` § `_validate_no_numeric_option_references` raises ERROR on any `Option <digit>` in an explanation, and `_validate_correct_option_explanation_consistency` now recognises both letter and 0-indexed numeric refs when checking that an explanation does not refute its own keyed option.
- **(MCQ tracks) The correct answer must not be guessable from its position or its length — run the dumb-baseline check.** Two "dumb-baseline" tells let a candidate pass without reading the question: (1) **position** — the correct option sitting at the same letter too often (always-pick-B passes); (2) **length** — the correct option being the longest (pick-the-wordiest passes). Both were endemic before 2026-06-07 (some tracks were 90–100% one letter; 82–96% "correct is longest"). Before publishing MCQ content, snapshot the affected `(track, difficulty, pool)` group (samples grouped per track): no single correct-answer **position** may exceed 40%, and "correct is the **unique-longest** option" may not exceed 45% (and must not invert into a "shortest" tell). Vary the key position; write distractors at comparable length to the key; never signal the answer by making it the most-elaborated option. **Machine-enforced (since 2026-06-07): `validate_content.py` § `_validate_answer_position_balance` (ERROR: any position >40%, or a ≥5 same-index run by `order`) and `_validate_answer_length_balance` (ERROR: correct-is-unique-longest >55%; authoring target ≤45%).** When fixing length, **trim the over-detailed correct option — never lengthen a distractor into defensibility**: uniqueness beats debiasing. A length edit that risks answer-uniqueness must be reverted and the question left flagged (validate every option-text change still blind-picks uniquely to the key via `audit_blind_answer_openai.py`).
- **A question whose explanation contradicts its own stem is invalid.** If the explanation admits "the described behaviour only occurs when the setup is wrong" or "this suggests the drop was not committed cleanly" or any equivalent self-undermining clause, the scenario in the stem is broken — fix the stem so the described behaviour is real, or fix the explanation so it no longer undermines the stem. This applies to explanations that work through an example and reach a different conclusion than the keyed answer (e.g. the explanation proves X=300 always while the key says "X varies").
- (`predict_output` / `debug`) Disjunctive or version-gated correct answers — "null values appear **or** a runtime exception is thrown" is not a prediction; it is a hedge. If the behavior is version-dependent, either pin the version in the stem or reframe as `conceptual` / `debug` (ask for diagnosis and fix, not runtime prediction). **A question is version-gated even if its explanation states the outcome with confidence.** For every `predict_output` and `debug` question, independently verify the correct answer holds in the **default configuration of the current stable release** — a confident explanation is not evidence of version-independence.
- **Vendor-asserted DDL must be valid on the named platform.** Any DDL clause, function, or storage feature attributed to a named vendor must be verifiable in that vendor's current official documentation. The canonical failure mode: asserting Snowflake `PARTITION BY` in a `CREATE TABLE` statement — Snowflake standard tables do not support user-controlled `PARTITION BY` DDL; the correct Snowflake clustering construct is `CLUSTER BY`. (`PARTITION BY` DDL exists on BigQuery, Iceberg table format, Delta Lake, and Hive-compatible engines — not on Snowflake standard tables.) Before publishing any question that cites vendor-specific syntax, verify the clause exists and behaves as described in that vendor's docs. If verification is impractical, genericize the platform name (e.g. "a cloud data warehouse" instead of "Snowflake") so no false capability is implied. Authoring templates and schema-example snippets used as scaffolding fall under this rule — a template that embeds invalid DDL propagates the error into every question that copies it.
- **Schema registry compatibility modes operate at wire-format level, not generated-code level.** FULL (BACKWARD + FORWARD) and BACKWARD are validated against field numbers, field types, and structural wire compatibility — they do not check generated-code attribute names. A Protobuf field rename that keeps the same field number passes FULL wire-compatibility while breaking consumers whose generated class now exposes a different attribute name. A question that claims "schema registry FULL compatibility blocks this rename" teaches the wrong model; the structural fix for that failure class is consumer contract testing gated in the producer's publishing pipeline. Separately, FULL is non-transitive: it guarantees one schema version in each direction. A consumer that must read all historical schema versions (not just the immediately preceding one) requires FULL_TRANSITIVE or BACKWARD_TRANSITIVE — not FULL alone.
- **Kafka topic partition IDs are sequential and immutable.** Expanding a topic from N to M partitions creates new partitions numbered N through M−1; the original N partitions keep IDs 0 through N−1. A scenario that claims a 3→5 expansion affected "partitions 2 and 4" (implying the original set was {0, 1, 3}) is factually impossible — partition 2 is original in a 3-partition topic. Verify partition numbers match sequential Kafka semantics before publishing.
- Mechanic-name tags as `concepts` values (per-track blocklists in [`docs/concept-taxonomy.md`](./concept-taxonomy.md)).
- **Backward-pass rule.** When a new Reject-on-sight rule is established in response to a found issue, immediately audit every existing question of the same type for the same failure mode — **across all tracks and difficulty bands**, not just the band currently being audited. Do not close the audit until the backward pass is complete. A rule that prevents future violations while leaving existing ones in place is not durable.
- **Independent quality sweep.** When auditing a difficulty band, apply **all** track doc quality rules — difficulty vocabulary (e.g. "pure-recall conceptual is rejected at easy"), the anti-patterns list, and hint discipline — to **every question in that band independently**. Do not rely solely on the incoming finding ID list. A question that was not flagged by the audit source is still a violation if it fails any track doc rule. The sweep is not complete until every question has been checked against every rule, not just those named.
- **Anti-pattern sweep applies to authored and rewritten questions too.** When converting or rewriting a question to fix one issue (format, hint leak, stem mismatch), verify the rewritten question against **all** track anti-patterns before committing — not just the one being fixed. A predict_output conversion that reproduces a default-value recall dependency inside the new format is still a violation. The obligation to sweep is not limited to audit passes; it applies at authoring time.
- **Bank shape governs blueprint, not vice versa.** For MCQ tracks, the runtime benchmark blueprint (`backend/routers/mock.py` § `_benchmark_type_targets` / `_pyspark_format_targets` / `difficulty_overrides`) describes how questions are assembled into a session — it is a derived contract over the bank, never an authoring constraint imposed on the bank. **Never force-fit a question type to satisfy a blueprint slot.** If the genuine, quality-preserving content at a given difficulty doesn't match the declared blueprint, fix the blueprint (and the table in [`docs/features/mock.md`](./features/mock.md) § Benchmark composition) — not the content. The audit dimension that catches blueprint/bank drift is documented in [`docs/orchestration-runbook.md`](./orchestration-runbook.md) § Stage C "Mock-surface blueprint feasibility."

### Framing authority (per-track)

Each `docs/tracks/<track>.md` "What this track trains" section is the **authoritative framing** for that track. Authoring agents, audits, and any analytical session that touches the track must **reinforce** that framing — never substitute their own. Three concrete rules:

- **Do not inject a contradictory lens.** Generic "interview patterns / NeetCode-grind / LeetCode-classic" framings, when they pull against a track doc's professional purpose, are out. The datathink test (durable data-professional reasoning, interview success as consequence) is primary.
- **References must fit the track's professional reality.** Use track-appropriate references for exhaustiveness (e.g. *Designing Data-Intensive Applications* for Data Engineering; data-engineering/data-science Python interview rounds for Python; pandas docs / Wes McKinney for Pandas; Spark: The Definitive Guide for PySpark; StrataScratch / DataLemur for SQL). Generic algorithm-catalogue references may be used **only** to check coverage breadth, never to justify a question's inclusion.
- **Reconcile a track doc's internal contradictions in the doc, not in the audit.** When a track doc's framing prose contradicts its difficulty ladder / concept arc / canonical example (the Python case — prose said "not competitive coders" while the ladder + example were LeetCode), **fix the doc to match its framing**; the framing wins.

### Research grounding (industry sources)

Authoring may use industry sources (StrataScratch, DataLemur, NeetCode, Glassdoor / Levels.fyi interview posts, canonical textbooks like *Designing Data-Intensive Applications*, vendor docs) for two purposes:
1. **Exhaustiveness** — checking that a track's family / pattern / scenario coverage isn't missing something every senior interview probes.
2. **Plausibility of MCQ distractors** — verifying that "an expert could defend this option" is grounded in real practitioner positions.

**Never lift content.** No description, scenario, code, options, or explanation is copied or paraphrased from external sources. Every question is authored from scratch against the datathink datasets, framing, and concept registry. This is a discipline rule with no exceptions.

### Difficulty model (cross-track)

This is the spine of the bank. The same rule applies to every track; only the per-track vocabulary changes (see track docs).

| Tier | Definition | Shape |
|---|---|---|
| **Easy** | One core concept (max two if tightly coupled). Candidate immediately knows what to reach for. Unambiguous output. | Single-step logic |
| **Medium** | 2–3 *related* concepts. Recognising *which tool fits* is the test. | Multi-step reasoning (aggregate→filter, join→aggregate→rank, compare-two-approaches) |
| **Hard** | 2+ *dependent* reasoning steps, trade-offs, edge-case awareness, production-grade thinking. (MCQ) All distractors plausible to someone who half-understands. | Multi-stage dependent logic |

A question is hard because the *reasoning* is layered, never because you bolted on unrelated requirements. **If you can make a question harder by removing a clarification, it was ambiguous, not hard.**

**Every tier maps to realistic business work, never to textbook drills.** Difficulty controls *reasoning depth*; it never licenses toy exercises. Even an easy question should read like a small real-world reporting or KPI task — not a syntax-recall prompt or a function-name quiz. Each track doc lists *allowed business scenarios* per tier (e.g. for SQL: easy = "monthly revenue by country", "users with no orders"; medium = "monthly retention trends", "refund-adjusted revenue"; hard = "cohort retention", "sessionization", "Pareto contribution"). The construct list says *what tools are in bounds*; the scenario list says *what the question should feel like*. Both gate the question.

Per-track difficulty vocabulary tables and allowed business scenarios: see each `docs/tracks/<track>.md`.

---

## Curriculum arc — progressive, with deliberate spiral reinforcement

Questions within a difficulty tier form a learning arc. The `order` field is the pedagogical position; the ID is not.

**Placement principles:**

1. **Prerequisite check** — a question at `order` N assumes mastery of everything at `order` 1..N-1.
2. **Unlocking step** — note what reasoning skill it opens up for later questions.
3. **Spiral reinforcement** — later questions should deliberately re-enter an earlier concept *from a new angle*. Reuse with a new angle is the curriculum. Cosmetic reuse is redundancy.
4. **No cold introductions** — never debut a concept at hard that was never touched at medium.

**Insertion workflow:** find the arc position → find nearest existing `order` values → assign an `order` between them. If inserting mid-sequence, state which existing orders shift up. **Never renumber IDs to match `order`** — that breaks `submissions`, `user_progress`, `follow_up_id`, paths.

Per-track concept arcs: see each `docs/tracks/<track>.md`.

---

## TXNNN ID scheme (authoritative — no deviation)

This is the single authoritative source for the ID scheme. Where any other document conflicts, **this section wins.**

### Scheme: `TXNNN` (5 digits)

```
T   = track digit (1–9)
X   = difficulty digit (1=easy, 2=medium, 3=hard)
NNN = sequence within that difficulty (001–999)
```

Examples: `11005` = SQL easy #5 · `42017` = PySpark medium #17 · `53004` = Data Engineering hard #4.

### Track assignments

| Track | T | Easy range | Medium range | Hard range |
|---|---|---|---|---|
| SQL | 1 | 11001–11999 | 12001–12999 | 13001–13999 |
| Python | 2 | 21001–21999 | 22001–22999 | 23001–23999 |
| Pandas | 3 | 31001–31999 | 32001–32999 | 33001–33999 |
| PySpark | 4 | 41001–41999 | 42001–42999 | 43001–43999 |
| Data Engineering | 5 | 51001–51999 | 52001–52999 | 53001–53999 |
| Data Modeling | 6 | 61001–61999 | 62001–62999 | 63001–63999 |
| Statistics | 7 | 71001–71999 | 72001–72999 | 73001–73999 |
| ML Fundamentals | 8 | 81001–81999 | 82001–82999 | 83001–83999 |
| Experimentation | 9 | 91001–91999 | 92001–92999 | 93001–93999 |

All T digits 1–9 are now allocated. New tracks beyond T9 require a T-assignment decision.

### Practice vs mock-only allocation

Practice and `mock_only: true` questions share the same `TXNNN` space within each difficulty file. IDs are assigned in append order — by when the question was authored — with no guarantee that all practice IDs precede all mock-only IDs. Later-added practice questions may carry IDs that are numerically higher than earlier-added mock-only questions (e.g. Data Modeling medium has practice IDs 62035, 62036, 62077 interspersed with mock-only IDs). **Classification is determined solely by the `mock_only` flag, not by ID sequence or position in the file.** **No mock-only questions exist at easy** for any track (by design: easy is practice-only).

### Sample IDs (3-digit TXS format, all tracks)

All 9 tracks use a compact `TXS` format (`T` = track digit, `X` = difficulty digit, `S` = 1–3): 3 easy + 3 medium + 3 hard per track = 9 samples per track, 81 total. By track:

| Track | T | Easy | Medium | Hard |
|---|---|---|---|---|
| SQL | 1 | 111–113 | 121–123 | 131–133 |
| Python | 2 | 211–213 | 221–223 | 231–233 |
| Pandas | 3 | 311–313 | 321–323 | 331–333 |
| PySpark | 4 | 411–413 | 421–423 | 431–433 |
| Data Engineering | 5 | 511–513 | 521–523 | 531–533 |
| Data Modeling | 6 | 611–613 | 621–623 | 631–633 |
| Statistics | 7 | 711–713 | 721–723 | 731–733 |
| ML Fundamentals | 8 | 811–813 | 821–823 | 831–833 |
| Experimentation | 9 | 911–913 | 921–923 | 931–933 |

3-digit TXS IDs never collide with 5-digit practice / mock-only IDs (`TXNNN`).

**Storage:** Every track — SQL included — has a **dedicated sample file** at `backend/content/sample_questions/<track>.json`, loaded by `sample_questions.py` at startup. Sample questions are completely separate from the practice and mock pools — they must never duplicate practice or mock content. Author samples as independent content.

**Required fields (every sample, every track):** `id`, `title`, `difficulty`, `description`, `hints` (exactly 2 entries), `concepts` (1–4 canonical family tags), plus per-eval-kind fields (SQL: `schema`, `dataset_files`, `expected_query`, `solution_query`, `explanation`, `order`; Python/Pandas: `dataframes`, `starter_code`, `expected_code`, `solution_code`, `test_cases`, `explanation`, `order`; MCQ tracks: `options`, `correct_option`, `explanation`, `order`). Field presence is enforced at module-import time by `_load_track_samples` (since 2026-06-01) — a stray edit removing required fields raises before any user can hit the sample.

**Cross-track validator coverage (since Phase 5a, 2026-06-01):** `validate_content.py` extends to `sample_questions/*.json` (SQL excluded for hint-rule reasons — see source). Samples participate in the canonical-name-strict, concept-blocklist, and near-duplicate checks alongside practice/mock. The strict per-track first-hint-leak regex patterns are exempt for samples — those patterns are calibrated for practice/mock and false-positive on samples that legitimately reference their own question subject. Samples have their own audit cadence via the Phase 2 closeout H8 step (see § Phase 2 closeout doc-hygiene).

**SQL-specific validation:** The SQL file additionally goes through `_validate_sample_questions`, which enforces that `schema` columns match committed CSV headers, `dataset_files` exist, and exactly 3 samples exist per difficulty.

### `schemas.json`-first rule

Each track's `schemas.json` defines valid `id_ranges`; the catalog loader validates every ID at startup and **crashes on violation**. `schemas.json` must be created before any question file is added to a new track. The JSON files are the runtime truth; this doc reflects them. Locations: `backend/content/<track>_questions/schemas.json` for each track.

### Ordering vs ID

The `order` field controls pedagogical sequence (sidebar order; sample slicing) and is **independent of the ID**. **Rule: assign IDs by appending to the end of the difficulty range. Never re-align ID gaps to `order` gaps.** Renumbering is forbidden — it breaks `submissions`, `user_progress`, `follow_up_id`, and learning-path arrays.

### Duplicate ID check

**IDs must be globally unique across all question files.** Before committing any question:

```bash
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    all_ids.extend(q['id'] for q in json.load(open(f)))
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"
```

---

## Hint discipline (cross-track)

Hints guide thinking toward the approach without revealing it.

| Difficulty | Target count | Ladder |
|---|---|---|
| Easy | 2 (MCQ-only tracks may use 1 when the concept is simple enough — PySpark / DE / DM / ML Fundamentals / Experimentation) | H1 = mental model / operation class. H2 = the concrete tool / transformation family. |
| Medium | 2–3 | H1 = core pattern. H2 = subproblem split / intermediate representation. H3 = tool or control-flow shape, only if needed. |
| Hard | 2–3 | H1 = decomposition strategy. H2 = dependency ordering / state representation / the bottleneck to isolate. H3 = final assembly or the constraint that commonly breaks solutions. |

- **Good hint:** "Use a hash map to look up previously seen values in O(1)" — names the class of tool.
- **Bad hint:** "Use a dictionary where the key is the number and value is its index" — that's the implementation.

**First-hint leak ban (MCQ-heavy tracks).** The first hint must not contain the answer's key term:

| Track | Forbidden first-hint patterns |
|---|---|
| PySpark | naming the relationship class directly ("two method names do the same thing"), naming the SQL analogy that is the answer ("SQL UNION is positional"), stating "X never raises an error" when the question asks what happens (eliminates all error options in one step), naming the decisive concept in interrogative form ("which X benefits from Y?" where Y appears verbatim in the correct answer) |
| Data Engineering | `idempoten*`, `watermark*`, `exactly-once` |
| Statistics | `p-value`, `null hypothesis`, `central limit theorem` |
| ML Fundamentals | `bias-variance`, `overfitting`, `data leakage` |
| Experimentation | `cuped`, `sample ratio mismatch`, `switchback` |

Anti-patterns: H1 reading like the first line of the solution; pasting code / method chains / clause text; H2 naming every required op in order; (MCQ) restating the correct option instead of hinting through elimination.

**Interrogative framing does not neutralize a leak.** The test is terminological: **does H1 contain any specific term, concept name, or API name that appears in or directly resolves the correct answer?** A hint phrased as a question ("which X benefits from Y?") is still a leak if Y is the decisive term in the correct answer. Apply this test word-by-word to H1 before committing.

**Premise disclosure is also a leak.** Do not state the decisive premise as a given in H1, even framed as a question. If H1 reads "if X is the case, what follows?" and X is the only fact the candidate needs to answer the question, H1 is a leak regardless of whether X is a verbatim term from the answer. Apply this test structurally: can a candidate read H1 and infer the answer without reading any option? If yes, rewrite.

---

## Concept-tag contract (cross-track)

`concepts` is a learner-facing semantic tag describing the *reasoning pattern* — not a parser keyword or API name.

- **1–4 tags** per question (5 only when a hard question genuinely teaches multiple dependent patterns). The target is 2–4: a question that genuinely tests only one canonical family may use 1 tag. Padding with sub-pattern names or weakly-related families to hit a minimum is forbidden — it produces the same noise as near-duplicates.
- Every tag must map to a registered family for the track via the algorithm in [`docs/concept-taxonomy.md`](./concept-taxonomy.md). The validator rejects unmappable tags AND per-track blocklist matches at catalog load.
- Prefer the *reasoning pattern* over the *tool name*. The tag should still make sense if the same problem were solved in another syntax / library (within reason — track-native patterns are OK).
- **Use the canonical family name.** When tagging a family, use its canonical registry name (e.g. `EXECUTION MODEL REASONING`), not a sub-pattern that happens to match it (e.g. `lazy evaluation`, `DAG`, `transformations vs actions` — all sub-patterns of EXECUTION MODEL REASONING). Sub-patterns exist for resolution and discoverability, not as alternative tag values.
- No near-duplicate tags. Within a single question, no two tags may resolve to the same canonical family. Old forms of this rule (e.g. `JOIN` + `INNER JOIN`) are subsumed: if two tags resolve to one family, that's a near-duplicate, even when both look semantically distinct. Machine-enforced for PySpark in `validate_content.py`; warn-only for other tracks until each track's cleanup pass lands.
- No onboarding / meta tags (`CTE INTRODUCTION`, `WITH CLAUSE SYNTAX`).
- **Tag the *distinguishing* technique, not incidental mechanics.** Foundational families that almost every question touches (result ordering, column projection, basic grouping, simple iteration) are concepts *only when they are the primary reasoning being tested*. Never bolt a foundational family onto an advanced question just because the construct happens to appear — tag what makes the question hard. A "weak on GROUPED AGGREGATION" insight must mean *can't aggregate*, not *failed a window-function question that happened to group*. (Mirrors how StrataScratch / DataLemur / NeetCode categorise by primary technique.)

Per-track family lists, blocklists, and resolution rules: [`docs/concept-taxonomy.md`](./concept-taxonomy.md).

**Quick test:** *"If a user saw this tag in a weak-spot insight, would it teach them what kind of thinking to improve?"* If no, rewrite.

### Tag lookup procedure (mandatory)

The 4-step verbatim lookup procedure lives in [`.github/agents/question-authoring.agent.md`](../.github/agents/question-authoring.agent.md) § Tag lookup procedure. Every authoring run — practice or mock-only, new question or edit — must follow it. Adjacent-track family names do not transfer; same name ≠ same registration.

### Validator coverage state

`backend/scripts/validate_content.py` enforces tag-family resolution (`_validate_concept_taxonomy`) and mock-only realism rules (`_validate_mock_only_realism`) **only** for tracks listed in the in-file constant `_TAXONOMY_VALIDATED_TRACKS`. For tracks outside that set, the validator emits a warning to stderr and skips those checks — it does NOT raise. Historically the skip was silent and gave false-positive PASS reports during authoring.

| Track | In set? | Last orphan-resolver sweep | Notes |
|---|---|---|---|
| SQL | ✅ | clean | Phase 2 closed |
| Python | ✅ | clean | Phase 2 closed; no realism families by design |
| Pandas (`python-data`) | ✅ | clean | Phase 2 closed; 3 realism families |
| PySpark | ✅ | clean (278 q, 0 orphans) | Phase 2 closed; added to set post-closure |
| Data Engineering | ✅ | clean | Phase 2 closed; no realism families by design |
| Data Modeling | ✅ | clean | Phase 2 closed; no realism families by design |
| Statistics | ✅ | clean (216 q, 0 orphans) | Phase 2 closed 2026-05-26; 13 families, no realism families by design; 100 practice + 116 mock-only |
| ML Fundamentals | ✅ | clean (243 q, 0 orphans) | Phase 2 closed 2026-05-26; BIAS/FAIRNESS Phase 2.5 closed 2026-05-26; 30 families, no realism families by design; 100 practice + 143 mock-only (8 chains) |
| Experimentation | ✅ | clean | Phase 2 closed 2026-05-26; 24 families, no realism families by design; 87 practice + 104 mock-only (10 chains) |

**Per-ITEM authoring discipline.** When the target track is NOT in `_TAXONOMY_VALIDATED_TRACKS`, Sonnet (or any executor) must run an explicit orphan-resolver one-liner after every ITEM (chunk of 8–12 questions) — `validate_content.py` is not sufficient. The one-liner appears in the Stage A handoff template; if orphans return, fix in that ITEM before authoring the next. Do not accumulate drift across multiple ITEMs.

**Closure rule.** A track joins `_TAXONOMY_VALIDATED_TRACKS` as the final durable-doc step of its Phase 2 closeout (see § Phase 2 closeout doc-hygiene below). Inclusion gates on: (a) registry fully populated for the Phase 2 scope, (b) zero orphans across all questions, (c) realism designation set in `MOCK_ONLY_REALISM_FAMILIES`.

**solution_code presence guard** (`_validate_solution_code_presence` — NOT gated on `_TAXONOMY_VALIDATED_TRACKS`). Enforced unconditionally for all medium/hard mock-only questions in: `python-data` (all mock-only), `python` (all mock-only), and `statistics` (numerical subtype only — conceptual questions use `explanation` instead). Raises on any mock-only question missing a non-empty `solution_code`. Added 2026-05-29 after a 25-question Pandas backfill revealed the field was unguarded at authoring time.

**Canonical-name-strict tag check (added 2026-06-01).** `_validate_concept_taxonomy` now enforces a second rule on top of resolution: every `concepts[]` entry must be written as the **canonical family name itself**, not a sub-pattern / alias that happens to resolve via `match_patterns`. For example, `'CLASSIFICATION METRICS & EVALUATION'` is rejected — author must write the canonical `'CLASSIFICATION METRICS'`. Resolution ≠ authoring permission. Comparison is case-insensitive (Statistics keeps its lowercase convention; every other track keeps uppercase). This closed the validator-gap that surfaced during the ML Fundamentals easy audit: sub-pattern aliases on samples 812/813 had resolved cleanly while drifting from the canonical naming contract. **Deterministic only — does NOT detect "tag resolves but the question doesn't actually test that family's reasoning."** Semantic-mismatch tags (e.g. tagging `CLUSTERING EVALUATION` on a paradigm-recognition question with no cluster-quality content) remain a manual-audit responsibility for the per-track Stage C audit.

**Execution-based reference guards (pytest CI, added 2026-06-08).** `validate_content.py` re-runs each **Python + Statistics-numerical** reference against its stored literal `test_cases` (`_validate_code_reference_reproduces_tests`). But **SQL and Pandas compute their expected output *live*** at grade time, so the validator has no stored answer to contradict — a newly authored SQL/Pandas question whose reference crashes, returns an empty/degenerate result, references a non-existent column, or whose `solution_*` disagrees with `expected_*` previously shipped green. That class was the single largest content-fix category of the 2026-05/06 refactor; the check existed only in the offline `audit_code_tracks.py` sweep and was never wired into CI. It is now promoted into standing pytest guards (run by `pytest -q` in CI):
- **`tests/test_code_references.py`** — every SQL + Pandas practice/mock reference executes, returns ≥1 row (non-degenerate), `solution_*` reproduces `expected_*` through the real guard+grader, and (Pandas) `schema` column order matches the CSV header. **Authoring rule: an SQL or Pandas question is not done until it passes here.** Run `pytest tests/test_code_references.py -k "<id or track>"` before committing. (Pre-existing degenerate-empty defects are quarantined as non-strict `xfail` with tracking reasons — see the `_SQL_KNOWN_DEFECTS` map — never add to it to silence a *new* failure.)
- **`tests/test_generator_reference_budget.py`** — every `compute:reference` generator hidden test runs its reference on the sized input within the wall-clock budget (closes the gap where `_validate_code_reference_reproduces_tests` deliberately *skips* generator-spec cases). It does **not** assert a naive baseline times out (no naive solution is stored) — that remains an authoring judgement.
- **`tests/test_sql_grading_tie_tolerance.py`** + **`tests/test_sql_grading_determinism.py`** — guard the two grading-soundness fixes (order-sensitive comparison is tie-tolerant; the grading DuckDB connection is single-threaded for float-aggregation determinism). See [`docs/backend.md`](./backend.md) § SQL evaluation path.
- **`tests/test_public_question_serialization.py`** — calls each track's `get_public_question()` on every question and asserts it does not raise and that `public_test_cases` serializes as an **`int` count** (the loader slices `test_cases[:public_test_cases]`). Closes the gap where a question authored with `public_test_cases` as a *list* of cases (instead of the count) parsed clean, passed `validate_content` + the reference guards, and then **500'd the live public endpoint** (`TypeError: slice indices must be integers`) — caught on 22051/23037 only in browser preview. The misleading `docs/tracks/python.md` JSON example (which showed the list form) was corrected at the same time.

### Phase 2 closeout doc-hygiene (durable — the H-series)

Every track's Phase 2 closure must execute this checklist as the final step of execution. Items live in durable docs; the historical tracker is archived at `docs/archive/2026-05-authoring-refactor.md`.

1. **Orphan remap.** Run the per-track orphan-resolver one-liner. Remediate every orphan tag — either remap to a registered family or propose a registry addition for user approval. Zero orphans required.
2. **Validator enable.** Add the track slug to `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py` with a one-line comment matching the existing pattern (e.g. `# <Track> Phase 2: registry complete (N families), 0 realism families, <em/mm/hm> mock-only validated`). Re-run `validate_content.py` to confirm the now-enforcing checks still pass.
3. **Taxonomy strip.** Remove the track's `⚡ *real-world gap*` markers from `docs/concept-taxonomy.md` and update the top-of-file ⚡ callout. Realism designation stays in body prose.
4. **Track-doc coverage section.** Add (or update) a "Coverage & sizing targets" section to `docs/tracks/<track>.md`: practice count, mock-only count, ratio, difficulty split, type mix, chain count, realism path.
5. **Realism designation.** Set `MOCK_ONLY_REALISM_FAMILIES["<track>"]` in `backend/concept_families.py` (populated set OR explicit `set()` with design-rationale comment). Must match the track-doc's stated realism path.
6. **IS-count sync.** Update CLAUDE.md (content footprint table + "Practice totals" + "Mock-only totals"), `docs/content-authoring.md` § Question bank current state, `docs/content-authoring.md` § Power-user runway sizing benchmark precedent table (add the row with locked ratio).
7. **Archive record.** Record the closeout summary in the decision log within the archived tracker at `docs/archive/2026-05-authoring-refactor.md`.
8. **Sample-bank sweep.** Audit `backend/content/sample_questions/<track>.json` against the same cross-track rules already verified for practice/mock: canonical-name tags (no sub-patterns / aliases), no duplicate-family within a question, no first-hint-leak or premise-disclosure violations, dataset/schema references match committed CSV headers (SQL only), no near-duplicates of practice or mock content. The 9 samples per track (3 per difficulty) are the first-impression surface — drift here erodes trust in the entire bank. Added 2026-06-01 after a retroactive audit (see `backend/content/sample_questions/` commits dca06fe → cc1c67d and onward) found systematic drift on the 7 closed tracks; future Phase 2 closeouts must not skip this step.

   **8a — Production-pipeline submit check (load-bearing for SQL).** For every newly authored or rewritten SQL sample, submit the canonical `expected_query` through `/api/sample/submit` (with backend running) and confirm `correct=true` is returned. Running queries directly against DuckDB via the unit-test harness bypasses `backend/sql_guard.py`, which sits in the user-submission path and rejects patterns like bare `CROSS JOIN` even when the result is semantically correct. Without this step a sample can pass DuckDB execution + tag validation + structural checks and still be **unsolvable in production** because the canonical answer hits the guard. Caught by the 2026-06-01 browser-preview verification on sample 132 (date-spine via `CROSS JOIN` rejected; remediated by `JOIN ... ON 1=1` in 53522c5). The same gap applies to any future track that adds server-side gates between user input and the executor (Python guard, PySpark optimiser checks, etc.) — adapt the check to that track's gate. Direct DuckDB execution is necessary but not sufficient.

**P1 — closeout commit naming.** The closeout commit must NOT self-title "audit PASS," "PASS," or any self-graded language. The executor does not audit itself; Stage C declares PASS. Use descriptive titles like `Phase 2 doc-hygiene closeout (orphan remap + validator enable + H-series)`.

**P2 — scope-creep.** Any durable-contract doc change OUTSIDE this H-series (e.g. modifications to `docs/content-authoring.md` outside IS-count/precedent rows; modifications to `docs/specs/*`; modifications to `.github/agents/question-authoring.agent.md`; modifications to `docs/concept-taxonomy.md` outside the current track's section) must be surfaced to the user via the executor's hand-back summary BEFORE self-applying. The executor flags; the user triggers a separate doc-hygiene pass.

### Per-family coverage discipline

Concept families must be distributed across questions with neither starvation nor concentration. The rules are calibrated to empirical evidence across six closed tracks — not absolute targets. Soft, with documented overrides; warnings on breach (not errors), because the override paths are real.

**Strategic anchor:** per-family weighting is by **reasoning surface**, never by interview or business frequency. See [`CLAUDE.md`](../CLAUDE.md) § Platform position. A family with broad reasoning surface (many distinct learnable variants — e.g. SQL `WINDOW FUNCTIONS` spans ranking, running totals, frame semantics, lateral patterns, qualify, deduplication via row_number, gap-fill) legitimately occupies more bank space than a narrow family. A family that dominates StrataScratch tag counts does not.

**The eight rules:**

| # | Rule | Anchor / rationale |
|---|---|---|
| 1 | **Practice floor.** Every applicable family has ≥1 practice question per applicable tier (`easy`/`medium`/`hard` where the family applies). | Codifies the existing "one teaching arc per family per applicable tier" principle (currently stated in `docs/tracks/sql.md` + `docs/tracks/pandas.md`). |
| 2 | **Mock-only floor.** Every practice-grounded family has ≥4 mock-only questions. | PySpark min=8; DE/DM min=4 (boundary). Below 4, benchmark/drill sessions exhaust fresh-first within 2–3 picks. |
| 3 | **Max-share ceiling.** No family is tagged on more than **50%** of questions in either tier (practice and mock-only computed independently). | SQL 39.5% / Pandas 50.0% empirical boundary; DM 93.8% broken. Earlier 2×-fair-share proposal would have failed every closed track except PySpark — empirically wrong. |
| 4 | **Zero dead families.** Every registered family appears in mock-only at least once. | PySpark and SQL achieved zero dead families; Python/Pandas/DE/DM each left 1–2 dead. |
| 5 | **Realism families exempt from rule 2.** Realism families are sampled per question as co-tags, not per target count. They are bounded by rule 3 only. | SQL/Pandas realism class design. |
| 6 | **Quality override.** If the anti-duplication rule binds before a floor is met, stop and document — never pad with near-clones. | Existing "Quality > integer" principle (`docs/content-authoring.md` § Power-user runway sizing benchmark). |
| 7 | **Load-bearing exception.** A family may exceed rule 3's 50% ceiling if it has genuinely broad reasoning surface for the track. Must be named explicitly in the track-doc with a reasoning-depth defence (NOT a frequency defence). The defence is: this family has N distinct learnable variants the curriculum must teach; the question count reflects that surface, not interview-market frequency. | Strategic anchor (Platform position). Defended per-track, not platform-wide. |
| 8 | **Curated-lean exception.** A family may sit below the rule-1, rule-2, or rule-4 floor IF the family is registered for legitimate sub-pattern coverage but its primary patterns are out-of-scope for the track's curation philosophy (e.g. Python anti-puzzle, anti-trivia, anti-vendor-lock-in). Must be named explicitly in the track-doc Coverage section with the curation rationale + which sub-patterns warrant continued registration. The defence is: this family stays registered because [legitimate sub-pattern], primary patterns [list] are banned per [philosophy], authoring more would require exactly the patterns the track rejects. | Symmetric to rule 7 — rule 7 defends ceiling breaches on reasoning-depth grounds, rule 8 defends floor breaches on curation-philosophy grounds. Both reject frequency arguments. Anchor: Python Phase 2 anti-puzzle decision; first-class application in `docs/tracks/python.md` § Per-family coverage exceptions (BACKTRACKING, IN-PLACE, MODULAR ARITHMETIC). |

**What does NOT justify a rule-3 ceiling breach:**
- "This is the most-asked family on StrataScratch."
- "Interviewers ask about this often."
- "Business cases use this everywhere."
- "Competitor banks weight this heavily."

These are frequency arguments. The Platform-position rule rejects them.

**What DOES justify a rule-3 ceiling breach (load-bearing exception):**
- "WINDOW FUNCTIONS has N distinct reasoning variants — ranking, running totals, percentiles, frame semantics, lateral subqueries, qualify, deduplication, gap-fill. The bank must teach all N because each is a separate learnable pattern. The 50% breach is the consequence of teaching all variants, not of repeated treatment of one variant."

The defence is per-variant, on disk in the track-doc's Coverage section.

**What does NOT justify a rule-1/2/4 floor breach:**
- "We don't have time to author more."
- "These question types are unpopular."
- "The validator warning is annoying."

These are convenience arguments. The Platform-position rule rejects them.

**What DOES justify a rule-1/2/4 floor breach (rule-8 curated-lean exception):**
- "BACKTRACKING & COMBINATORIAL SEARCH stays registered because BST operations, SERIALIZATION, VISITED STATE tracking, and recursive tree traversal are genuine data-professional patterns. The family's canonical puzzle implementations — subset enumeration, N-queens, Sudoku — are deprecated per the anti-puzzle philosophy. Authoring 4+ mock-only would require exactly the patterns the curriculum bans."

The defence is curation-rooted, on disk in the track-doc's Coverage section. Frequency in interview banks is irrelevant; what matters is whether the registered family has legitimate sub-patterns AND whether its primary patterns conflict with the track's curation philosophy.

**Machine enforcement.** `validate_content.py` runs `_validate_per_family_coverage()` after the existing checks and emits **stderr warnings** for each breach. Gated on `_TAXONOMY_VALIDATED_TRACKS`. Warnings (not errors) because rules 6, 7, and 8 are real override paths — hard failures would force documentation-after-the-fact rather than at the right moment. Stage C audit verifies each warning is either remediated or documented as a rule-7 or rule-8 exception in the track-doc.

**Stage A integration.** Each Phase 2 Stage A produces a per-family target table as part of Sizing + Structure Lock: family count, fair-share per family, target practice count + target mock-only count per family, load-bearing families (rule 7) called out with reasoning-depth rationale, curated-lean families (rule 8) called out with curation rationale.

**Stage C integration.** Audit dimension verifies (a) zero rule-1 floor breaches not documented as curated-lean, (b) zero rule-2 floor breaches not documented as curated-lean (excluding realism), (c) zero rule-3 ceiling breaches not documented as load-bearing, (d) zero dead families not documented as curated-lean (rule 4 + rule 8 cross-reference).

---

## Mock-only authoring contract

`mock_only: true` makes a question exclusive to mock sessions (Pro/Elite). It never appears in the practice catalog.

**Source of truth for plan gating, chain mechanics, Interview Loop:** [`docs/features/mock.md`](./features/mock.md).

### What separates practice from mock-only

The distinction is **framing, realism, ambiguity, and interview dynamics — not the introduction of new reasoning concepts.**

| | Practice | Mock-only |
|---|---|---|
| Exists to | teach reasoning patterns; build the curriculum progressively | evaluate whether learned reasoning *transfers* under pressure and unfamiliar framing |
| Orientation | learner / progression / curriculum | assessment / realism / adaptability |
| Answers | "Can the learner understand and apply this pattern?" | "Can the learner transfer prior reasoning to an unfamiliar situation?" |
| Framing | clean business framing, minimal ambiguity, pedagogical clarity | production-realistic; mild ambiguity, evolving requirements, edge cases, dirty data |
| Concepts | introduces concepts systematically | **recombines and stress-tests already-taught concepts** |

**The governing rule:** a mock-only question must **never introduce a reasoning concept the practice curriculum hasn't already taught at that difficulty.** It recombines previously-learned concepts in an unseen business scenario. A mock should feel like *a real interviewer extending the discussion naturally* — not an artificial puzzle escalation, and not a brand-new topic the candidate was never taught.

### Mock-only contract

- Allocate IDs at the top of the difficulty range, after the last practice question. **Never at easy** — easy is practice-only; mock-only exists at medium and hard only.
- **No unseen concepts.** Every concept family a mock-only question tests must already appear in the practice bank for that track at that difficulty or lower. Mock-only adds *no* new families.
- **Anti-duplication rule (replaces the old concept-novelty cap).** A mock-only question must not clone the *framing* of an existing practice question — it must recombine the same learned concepts in a **fresh business scenario** (different KPI, time window, multi-table relationship, stakeholder pressure, or dirty-data condition). Same reasoning, unseen surface. If a mock-only question would teach a concept the curriculum skipped, author the practice question first.
- **Mock-only realism families (the one exception to "no new families").** Some families are assessment *lenses* layered over a concept the learner already knows (e.g. choosing a denominator, sanity-checking output, reasoning about cost) rather than new curriculum concepts. Where a track designates such families (listed per track in [`docs/concept-taxonomy.md`](./concept-taxonomy.md); machine-readable in `MOCK_ONLY_REALISM_FAMILIES`, `backend/concept_families.py`), they: **(a)** appear only on `mock_only: true` questions; **(b)** may **never** be a question's *sole* concept tag — they must co-occur with ≥1 practice-grounded family (so the underlying concept is always practice-taught — the no-unseen-concepts guarantee holds); **(c)** are exempt from practice-grounding. The validator `_validate_mock_only_realism()` enforces (a) and (b) at catalog load. *(SQL realism families: `METRIC INTERPRETATION & DENOMINATOR CHOICE`, `OUTPUT SANITY VALIDATION`, `PERFORMANCE-AWARE ANALYTICS`. Other tracks set theirs as their Phase 2 audit concludes.)*
- **Chain authoring rules:**
  - Parent (`follow_ups: [child_id, ...]`) and each child (`mock_only: true`, `parent_id`, `follow_up_dimension`) live in the same difficulty file
  - Chain length 2–4 (parent + 1–3 follow-ups)
  - Each follow-up uses one of the 7 universal dimensions in [`docs/concept-taxonomy.md`](./concept-taxonomy.md#the-7-universal-follow-up-dimensions-chain-pivots)
  - Consecutive follow-ups must use different dimensions
  - No nested chains, no shared children
  - Chain stays within one track and uses same-or-escalating difficulty
- **Atomicity** — selector-enforced, see [`docs/features/mock.md`](./features/mock.md#follow-up-chain-atomicity-proelite--mock-only-content). Authors just write chains that *make sense* as iterative interviewer pivots.
- **Mock-only is not limited to query/function-writing.** `debug` (fix a broken query/function/pipeline), `scenario` (read a production-incident narrative and choose the correct call), `reverse` (infer the query from a result preview), and `predict_output` (read code, predict output/schema) are **first-class mock-only types** wherever a track's evaluator + UI support them — they simulate real interview dynamics that pure write-the-query/function questions can't. A track decides which formats fit (see per-track doc); don't default to "mock = write the query."
- **Special types** (track-specific, see per-track doc):
  - `framing: "scenario"` — narrative business brief in `description` (≤3 sentences, grounded)
  - `type: "reverse"` (SQL only) — user sees `result_preview`, writes the query
  - `type: "debug"` — `debug_error` is a real engine error string; starter has exactly one bug

### Power-user runway sizing benchmark (mock-only inventory)

Mock-only inventory must support a power user who completes most of practice and then does months of heavy mock prep — and because **chains are consumed once per user, ever** (`docs/features/mock.md` → atomicity), inventory must (a) exceed peak multi-month consumption and (b) span every interview-relevant medium/hard family. This rules out "lean mock" interpretations.

**Per-track sizing target:** **mock-only count between 1.0× and 1.5× the practice count**, hard-skewed (~55/45 or 60/40 medium/hard), with **~⅓ of mock-only as chain members** (the Interview-Loop capacity floor — parents + follow-ups).

**Established precedent** (these set the contract — diverging requires explicit, written, track-specific justification):

| Track | Practice | Mock-only | Ratio | Notes |
|---|---|---|---|---|
| SQL | 118 | 165 | **1.40×** | executable analytics |
| Python | 79 | 103 | **1.30×** | executable algorithms |
| Pandas | 92 | 114 | **1.24×** | executable analytics |
| PySpark | 127 | 150 | **1.18×** | code-adjacent reasoning (MCQ) |
| Data Engineering | 91 | 110 | **1.21×** | constructed reasoning (MCQ) |
| Data Modeling | 81 | 97 | **1.20×** | constructed reasoning (MCQ) |
| Statistics | 100 | 116 | **1.16×** | hybrid (conceptual MCQ + numerical Python) |
| ML Fundamentals | 100 | 143† | **1.43×** | constructed reasoning (MCQ); †includes 16 chain children from 8 chains; ALGORITHMIC FAIRNESS family added Phase 2.5 (2026-05-26), registry now 30 families |
| Experimentation | 87 | 104 | **1.20×** | constructed reasoning (MCQ); 10 chains (20 chain children); 24-family registry; path (ii) no realism families |

A track audit proposing **< 1.0×** must record the track-specific reason in the brief and the decision log (e.g. interview-frequency data showing low demand, a finite pattern-space argument that more mock would only produce clones, etc.) — and the reason must survive critical pushback. *"Lean"* in this contract applies to **practice** (don't pad the curriculum with puzzles or low-value variants); **mock** sizes to the runway. A small mock pool is a power-user runway failure, not a virtue.

**Composition discipline (orthogonal to count):** the anti-duplication rule (above) bounds *quality* — every mock-only question must recombine practice-taught reasoning under fresh framing, not clone an existing question. If the anti-duplication ceiling appears to bind below the 1.0× floor for a given track, the right response is **drop/replace the SQL-in-pandas-style clones already in the bank** and then re-author up to ratio — not abandon the runway target.

**Band semantics for execution (locked 2026-05-24, applies to track audits from this date onward).** Each track audit locks **one** target ratio inside the 1.0×–1.5× range at Stage A, defended against modality precedent and track-specific reasoning (recorded in the audit brief). The target is a single approx ratio; the executor (Sonnet) authors to a *band*, not a fixed integer:

- **Acceptable landing band:** `target ± ~5pp` (≈5 percentage points either side of the locked target). The executor may close authoring anywhere inside the band.
- **Operational floor: 1.10×.** Stopping below this requires escalation back to a Stage A pushback — not an executor self-declared "quality victory." (Distinct from the 1.0× contract floor above, which governs the Stage A target lock; the 1.10× operational floor governs where the executor may stop authoring against an already-locked target.)
- **Operational ceiling:** `target + ~5pp`. Exceeding the band also requires escalation (prevents over-authoring into near-clone territory under the anti-duplication rule).
- **Quality > integer.** If the anti-duplication rule binds before the band's lower bound, stop authoring, record the binding reason in the closeout commit, and hand back for re-audit. Do not pad with near-clones to hit a number.

**Closed tracks (SQL, Python, PySpark, Pandas, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation) keep their locked targets** — all active tracks have now closed Phase 2. The precedent table above records LANDED ratios (history), not retro-fitted targets.

---

## Per-track JSON schemas

JSON schemas, datasets, ID ranges, concept arcs, and verification commands are **per-track**. Read the relevant track doc before authoring:

- [`docs/tracks/sql.md`](./tracks/sql.md)
- [`docs/tracks/python.md`](./tracks/python.md)
- [`docs/tracks/pandas.md`](./tracks/pandas.md)
- [`docs/tracks/pyspark.md`](./tracks/pyspark.md)
- [`docs/tracks/data-engineering.md`](./tracks/data-engineering.md)
- [`docs/tracks/data-modeling.md`](./tracks/data-modeling.md)
- [`docs/tracks/statistics.md`](./tracks/statistics.md)
- [`docs/tracks/ml-fundamentals.md`](./tracks/ml-fundamentals.md)
- [`docs/tracks/experimentation.md`](./tracks/experimentation.md)

---

## Verification (cross-track)

You are not done when the JSON looks right — it must load and run.

```bash
# 1. Duplicate ID check (global, shown above)
python3 -c "import json, glob; ..."

# 2. Every JSON file parses
python3 -c "
import json, glob
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    json.load(open(f))
print('All valid')
"

# 3. Catalog loader + content validator (schemas validated at startup)
python scripts/validate_content.py

# 4. Backend tests
cd backend && ../.venv/bin/python -m pytest tests/test_evaluator.py tests/test_api.py -q
```

Track-specific runtime checks (DuckDB query execution, Python test-case execution, etc.) are in each track doc's "Verification before commit" section. Run them.

---

## Question bank current state

Practice questions are the full curriculum. Mock-only questions live in the same per-track files but are excluded from the practice catalog.

| Track | Easy | Medium | Hard | Practice total | Modality |
|---|---|---|---|---|---|
| SQL | 37 | 50 | 31 | **118** | Executable (DuckDB) |
| Python | 33 | 29 | 17 | **79** | Executable (sandbox) |
| Pandas | 28 | 40 | 24 | **92** | Executable (sandbox) |
| PySpark | 40 | 45 | 42 | **127** | Code-adjacent reasoning (MCQ) |
| Data Engineering | 30 | 35 | 26 | **91** | Constructed reasoning (MCQ) |
| Data Modeling | 25 | 31 | 25 | **81** | Constructed reasoning (MCQ) |
| Statistics | 31 | 43 | 26 | **100** | Hybrid (conceptual MCQ + numerical Python) |
| ML Fundamentals | 30 | 40 | 30 | **100** | Constructed reasoning (MCQ) |
| Experimentation | 30 | 33 | 24 | **87** | Constructed reasoning (MCQ) |
| **Total** | | | | **875** | |

Mock-only add-on bank: **1,102 questions** (Pro/Elite only). Samples: **81 total** (9 per track × 9 tracks, dedicated content separate from practice and mock pools).

**These counts evolve.** They reflect the bank at the time of the 2026-05 refactor. CLAUDE.md mirrors them; both files update together.

### Learning paths (curated sequences)

**This subsection is the canonical source of truth for learning-path semantics.** Other docs (`CLAUDE.md`, `docs/track-onboarding.md`, `docs/backend.md`, `docs/architecture.md`, `docs/frontend.md`) link here and must not restate the rules below.

46 paths total across 9 tracks. Path files live in `backend/content/paths/`. Per-track pattern registry lives in `backend/path_patterns.py`.

#### What a learning path is

A learning path is a **curated 5–9 question walk through a pattern**, drawing entirely from the existing practice catalog. Paths sit *on top of* practice; they do not introduce new questions and do not bypass the practice-track unlock thresholds. A user who completes a path's question via the path or directly from practice gets the same `solved` state, and the same unlock-threshold counters advance either way.

Paths are not comprehensive. Most questions in the catalog are never in any path. That is intentional — paths are for guided mastery of a specific pattern, not for cataloguing everything that touches the pattern.

#### Patterns vs concepts — two distinct axes

Datathink uses two registered taxonomies that look similar but answer different questions:

| Axis | What it captures | Where it lives | Used by |
|---|---|---|---|
| **Concept family** | The *reasoning* a question exercises (e.g., `TEMPORAL REASONING`, `CARDINALITY REASONING`, `GROUPED AGGREGATION`) | `backend/concept_families.py` per-track registry | Question tags, dashboard weak-spot detection, mock `focus_concepts` filter |
| **Pattern** | The *practitioner skill* a path masters (e.g., `window-functions`, `scd`, `causal-inference`) | `backend/path_patterns.py` per-track registry | Path metadata, "what you'll learn" UI, future Practice→Path→Mock loop |

A path declares **both**:

- `patterns[]` — what subject matter the practitioner picks up
- `focus_concepts[]` — what reasoning families the path strengthens (used by dashboard insights to recommend this path when a user shows weakness in a matching family)

A path's pattern is usually one slug (a focused mastery walk); some paths legitimately span two patterns (e.g., `groupby-and-joins` declares both). `focus_concepts[]` is usually 2–5 family names — enough to cover the included questions without being a catch-all.

**Pattern slug convention:** kebab-case, lowercase, ASCII-only, ≤40 chars. Multi-word slugs use hyphens (`window-functions`, `cohort-and-retention`, `missing-data-and-preprocessing-hygiene`). Register every slug in `backend/path_patterns.py` for its track before using it on a path.

**Planned evolution to 1:1 mapping:** the current `patterns[]` array is a transitional shape. The committed direction is a **1 pattern → 1 path** model in which each question carries a single `pattern` tag and path `questions[]` is auto-derived from the catalog. Migration tracked in [`docs/phases/learning-paths-tracker.md`](./phases/learning-paths-tracker.md) §B (B1–B7). Until that lands, paths may declare multiple patterns when the content genuinely spans them.

#### Parallel-systems design (locked 2026-XX)

Pattern-paths and concept-families are **two separate taxonomies** that serve two non-overlapping surfaces. They do not bridge:

| Axis | Drives | Surfaces |
|---|---|---|
| **Patterns** | Practitioner subject-matter mastery | Practice (learning paths only) |
| **Concept families** | Reasoning diagnostic | Mock (`focus_concepts` filter) + Dashboard (weak-concept detection + recommended-path lookup) |

There is no Practice→Path→Mock loop. There is no `pattern` filter on mock. There is no concept-family field on patterns. The closest thing to a bridge is the dashboard's "weak concept → recommended path" recommendation, which only works because every path declares `focus_concepts` *in addition to* `patterns` — and that link is concept-family driven, not pattern driven.

#### Question-to-pattern routing (locked 2026-XX)

Every practice question routes to exactly one pattern-path (or `null` if no pattern fits). The routing rule:

1. **Strict 1:1.** A question belongs to *exactly one* pattern-path. Never two. If a question's tags span multiple candidate patterns, apply the tie-breaker below.
2. **Route by objective, not by construct.** Inspect the question's concept-family tags. Map each family to its canonical pattern via the per-track routing table (see `scripts/audit_pattern_coverage.py::ROUTING`). The pattern that matches the question's *primary objective* wins.
3. **Analytical wins.** When a question's tags span both an analytical pattern (e.g., `cohort-and-retention`, `funnel-and-event-analysis`, `feature-engineering`) and a construct pattern (e.g., `window-functions`, `aggregation`, `cross-validation`), the analytical pattern wins. Rationale: "Monthly cohort retention" *uses* window functions but its *objective* is cohort analysis. The construct is the tool; the analytical pattern is the lesson.
4. **Mock-only is excluded.** Pattern-paths contain *only* practice questions. Mock-only questions (`mock_only: true`) are never in any pattern-path. They live in the mock pool, indexed by concept-family.
5. **Realism families never route.** Mock-only realism families (`DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`, `METRIC INTERPRETATION & DENOMINATOR CHOICE`, `OUTPUT SANITY VALIDATION`, `PERFORMANCE-AWARE ANALYTICS`) are co-tags only, never primary. They do not influence routing.
6. **Cross-cutting families may route to `None`.** Some families (`NULL HANDLING & COALESCE`, `RESULT SHAPING & ORDERING`, `GREEDY CHOICE`) are intentionally cross-cutting — they appear on many questions but rarely as the *objective*. Questions tagged only with these stay unrouted (catalog-only).

**Easy → hard ordering.** Within each pattern-path's `questions[]`, the order is deterministic: difficulty (`easy < medium < hard`) then question ID. Authors do not hand-order; the loader sorts.

**Where this is exercised.** `scripts/audit_pattern_coverage.py` is the canonical implementation. It walks the catalog, applies the routing rule end-to-end, and emits [`docs/phases/pattern-coverage-audit.md`](./phases/pattern-coverage-audit.md). Re-run anytime to refresh. The question-authoring agent's final checklist includes this path-applicability step — see [`.github/agents/question-authoring.agent.md`](../.github/agents/question-authoring.agent.md).

#### Path schema

| Field | Required | Notes |
|---|---|---|
| `slug` | ✓ | Unique, hyphenated. URL: `/learn/<topic>/<slug>` |
| `title` | ✓ | ≤50 chars, user-facing |
| `description` | ✓ | 1–2 sentences |
| `topic` | ✓ | Must match a track slug |
| `tier` | ✓ | `free` or `pro` — controls **path-listing visibility only** (the questions inside follow practice unlock thresholds regardless) |
| `level` | ✓ | `foundational` \| `intermediate` \| `advanced` — defined below |
| `display_order` | ✓ | 1-based integer, unique per `(topic, level)`. Lower = earlier in the track's recommended walk within that level. Foundational is always 1 (singleton). TrackHub sorts by `(level, display_order)`. |
| `patterns` | ✓ | Non-empty array; every entry must resolve in `path_patterns.py` for the track |
| `focus_concepts` | ✓ | Non-empty array; every entry must resolve to a registered family in `concept_families.py` for taxonomy-validated tracks (others: presence check only until registries are complete) |
| `questions` | ✓ | Ordered array of catalog question IDs (easy → hard within the pattern). Every ID must exist in the track catalog. Every question must carry at least one concept tag in the same family as one of the path's `focus_concepts[]` (mechanical guarantee that the path drills what it claims). |
| `outcomes` | ✓ | 1–2 sentences starting with "You'll…" describing capability gained |
| `recommended_after` | ✓ | Prerequisite path slugs (same track). Empty array `[]` for foundational paths. The resulting graph must be acyclic. |

#### Level definition

**Level describes where the path sits in the track's pattern arc — not the difficulty mix of its questions.** Difficulty mix is whatever the catalog naturally supports for the patterns the path drills.

- **`foundational`** — Covers the foundational patterns of the track: the building blocks every other path assumes. **Exactly one per track** (validator-enforced). UX promise: every track has one obvious entry point ("Start here").
- **`intermediate`** — Mid-tier patterns sitting on top of the foundational layer. **One or more per track.** When a track has parallel mid-tier clusters (e.g. data-modeling: normalization vs dimensional), each gets its own intermediate path — they are not forced to compete for a singleton slot.
- **`advanced`** — Advanced patterns assuming both foundations and some mid-tier exposure. **Zero or more per track.**

Level has no unlock semantics. Levels are used for sort order on TrackHub, the "Start here" pill on the singleton foundational path, and Schema.org metadata. **Path completion does not unlock any practice questions** — unlocks follow the standard practice thresholds (see `docs/backend.md` for the unlock-state computation).

#### Validator integrity rules

`backend/scripts/validate_content.py::_validate_paths` enforces:

1. **Schema completeness.** All required fields present; slug unique; matches filename.
2. **Singleton foundational.** Exactly one `level=foundational` per track. No upper bound on `intermediate` or `advanced`.
3. **Pattern registry.** Every `patterns[]` entry resolves in `path_patterns.py` for the path's track.
4. **Focus-concept registry.** Every `focus_concepts[]` entry resolves to a registered family in `concept_families.py` (only enforced for tracks listed in `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py` — currently `{sql, python}`; others get a presence-only check). **When a track joins the validated set, the path validator immediately enforces this rule strictly for it** — coordinate the concept-family registry completion + paths re-check in the same PR.
5. **Question-tag alignment.** Every question in `questions[]` carries at least one concept tag that resolves to the same family as at least one of the path's `focus_concepts[]`. This is the mechanical guarantee that the path drills what it claims.
6. **Prerequisite DAG.** Every `recommended_after[]` slug exists in the same track; the resulting graph is acyclic.
7. **Question→path uniqueness (1:1 model).** Every question appears in at most one path across the entire bank. The product mental model is that each question belongs to exactly one pattern walk; a question in two paths means a user solving it advances both paths' progress counters, double-counting coverage and breaking the curriculum spine. Enforced by `_validate_paths` rule 7 and `test_rule7_question_appears_in_at_most_one_path`. **When two paths legitimately want the same question, pick the primary path based on the question's primary pattern, not on secondary technique tags** (e.g., "Sliding Window Maximum" is a sliding-window problem first, a monotonic-deque technique second).
8. **Path-length range.** `questions[]` must contain between 4 and 20 entries (hard floor and ceiling, validator-enforced). Paths below 4 are fragments; paths above 20 indicate an insufficiently split pattern.

#### Path-size policy

Paths should hold **5–9 questions** in the sweet spot, **4 minimum** (hard floor), **15 maximum** (default cap). Paths can grow to 16–20 questions only with **explicit per-path approval** — captured in the commit message that introduces the over-cap size. The validator enforces the hard 4–20 range; cap-15-vs-20 is curation discipline, not machine-enforced.

#### What this section explicitly rejects (historical)

The platform previously had a "path-completion unlock shortcut" mechanic (completing a foundational path unlocked all medium; completing intermediate unlocked the hard cap). **That mechanic was removed.** If you find a doc still describing it, that doc is stale — fix it and link here. The current model is: practice thresholds gate question unlocking; paths are curated walks that respect those gates.

---

## Sample question authoring

Sample questions are governed by the same cross-track quality bar as practice and mock-only questions. This section codifies the additional rules that apply specifically to the sample bank — rules that emerged from the 2026-06 sample audit and were absent from docs prior to that point.

**ID scheme, storage location, required fields, and cross-track validator coverage** for sample questions are documented in § TXNNN ID scheme → Sample IDs (3-digit TXS format, all tracks). Read that subsection first; the rules below build on it.

### Purpose and scope

Sample questions are a **first-impression discovery surface**: shown to anonymous visitors and logged-in users before they commit to any track. Each track has exactly 3 easy + 3 medium + 3 hard sample questions (9 per track, 81 total). Sample questions:

- Must stand alone as an interesting, representative first touch — not as a warm-up for the practice arc.
- Never appear in the practice or mock catalog; they are completely separate content.
- Record no progress toward challenge unlock thresholds.
- Use IDs in the compact TXS format (see § TXNNN ID scheme → Sample IDs for per-track ranges).

Because samples are the first experience a user has with a track, quality failures here erode trust in the entire bank — even if the practice bank is clean.

### Difficulty bar

Sample questions use the **same cross-track difficulty vocabulary as practice questions — no softer interpretation is permitted.** Specifically:

- A medium-tier algorithm or reasoning pattern does not become Hard for a sample by adding realistic scenario framing or extra edge cases. The underlying pattern itself must qualify as Hard by the track's difficulty ladder (see each `docs/tracks/<track>.md`).
- A question that a mid-level data professional can solve confidently on first attempt is Easy or Medium regardless of how it is framed.
- **The three-question set within each difficulty tier must cover distinct concept families.** A tier where all three questions tag the same top-level concept family (e.g. all three Easy Python samples are `HASH-MAP STATE`) fails the sample authoring bar even if each individual question is technically correct.

### Anti-duplication rule (authoring-time, not audit-time)

Sample questions must not duplicate, near-clone, or be a weaker reskin of any existing practice or mock question in the same track. This is an **authoring-time obligation** — not something discovered retrospectively. Three forms of violation:

1. **Exact-title match** — prohibited. The validator (`_validate_sample_cross_bank_titles`) enforces this automatically at catalog load.

2. **Family + shape near-clone** — also prohibited, but requires authoring-time judgment. A question titled differently but covering the same algorithm in the same domain with the same problem shape is a near-clone. Example: a sample titled "Top-K Items by Score" that calls `sorted()[:k]` is a near-clone of any practice question covering top-K selection, even if the business domain differs.

3. **Weaker reskin** — prohibited. A sample must not be a lighter, simpler, or less-correct version of an existing practice question. If a practice question already covers the concept, the sample should cover a **different** concept, not a simplified variant of the same one.

The near-clone and weaker-reskin checks are authoring-time judgment calls — the validator cannot enforce them automatically. Check them before finalizing any sample JSON.

### Prompt/solution contract rule

Any specific behavioral promise in the description must be implemented in the canonical solution. This is a **content defect** if violated and must be caught at authoring time, not at audit time. The rule applies to:

- **Coverage promises.** "Include every X", "for each X", "all rows/dates/entities" → the solution must return a row for every X, using a spine, reindex, or equivalent. If the solution cannot guarantee completeness, use conditional phrasing ("for each X with at least one Y") — not absolute coverage language.

- **Ordered constraints.** "Step A then step B", "in order", "A → B" (with arrow notation) → the solution must enforce the ordering. If the solution checks only event co-presence without enforcing order, remove the ordering framing from the description.

- **Set membership.** "Only", "exactly", "all and only" → the solution's output set must match the description's claimed set exactly.

**Test at authoring time:** read the description's behavioral promises; then read the solution; confirm every promise is implemented. A question whose description promises behavior that the solution does not implement is invalid.

### MCQ label alignment rule

For MCQ questions (`options` array + `correct_option` index):

- Every option label explicitly named in the description (e.g. "Option A", "Option B") must correspond to an entry in the `options` array.
- The `options` array must not contain entries whose labels are not referenced in the description (no phantom options).
- `correct_option` must be a valid 0-based index into the `options` array.
- The validator (`_validate_mcq_consistency`) enforces index validity and label-count consistency automatically. **Authoring-time rule:** count the labels named in your description before finalizing the `options` array. A description that names 4 options and an `options` array with 3 entries is a defect — not just a validator error.

### Validator coverage

The following checks are enforced automatically by `validate_content.py` for sample files:

| Check | Function | What it catches |
|---|---|---|
| Exact-title collision vs practice/mock bank | `_validate_sample_cross_bank_titles` | Per-track; raises if any sample title exactly matches any practice or mock title in the same track |
| MCQ index validity and label-count consistency | `_validate_mcq_consistency` | `correct_option` out of bounds; description label count mismatches `options` array length |
| Required-field presence (non-SQL tracks) | `_validate_non_sql_sample_fields` | Enforces `id`, `title`, `description`, `difficulty`, `hints` (exactly 2), `concepts` (1–4), `order`, plus per-eval-kind fields |
| Within-bank duplicate ID detection (non-SQL) | `_validate_non_sql_sample_ids` | Duplicate IDs within a single track's sample file |
| Canonical-name tags, blocklist, near-duplicate families | `_validate_concept_taxonomy` | Same rules as practice/mock (SQL excluded for hint-rule reasons — see source) |

**Authoring-time judgment calls not covered by the validator:**
- Family + shape near-clone detection (requires semantic comparison against the full practice/mock bank)
- Prompt/solution contract correctness (requires reading description → solution and verifying every promise is implemented)

These two checks are the author's responsibility on every sample question, every time.
