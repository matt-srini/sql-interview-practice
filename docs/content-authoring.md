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
- Mechanic-name tags as `concepts` values (per-track blocklists in [`docs/concept-taxonomy.md`](./concept-taxonomy.md)).

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

Practice and `mock_only: true` questions share the same `TXNNN` space within each difficulty file. Mock-only questions allocate at the **top of each difficulty range**, immediately after the last practice question — never separately numbered. **No mock-only questions exist at easy** for any track (by design: easy is practice-only).

### SQL sample IDs (3-digit, SQL only)

SQL samples use a compact `TXS` format (S = 1–3): `111–113` easy · `121–123` medium · `131–133` hard. Defined in `backend/sample_questions.py`. Never collides with 5-digit practice IDs.

**Non-SQL tracks have no separate sample files or sample IDs.** `get_topic_sample_pool()` serves samples by slicing the first 3 practice questions by `order` from the live catalog. For Pandas, Python, PySpark, DE, DM, Statistics, ML, Experimentation: do not author dedicated sample questions.

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
| Easy | 2 (PySpark / DE / DM may use 1) | H1 = mental model / operation class. H2 = the concrete tool / transformation family. |
| Medium | 2–3 | H1 = core pattern. H2 = subproblem split / intermediate representation. H3 = tool or control-flow shape, only if needed. |
| Hard | 2–3 | H1 = decomposition strategy. H2 = dependency ordering / state representation / the bottleneck to isolate. H3 = final assembly or the constraint that commonly breaks solutions. |

- **Good hint:** "Use a hash map to look up previously seen values in O(1)" — names the class of tool.
- **Bad hint:** "Use a dictionary where the key is the number and value is its index" — that's the implementation.

**First-hint leak ban (MCQ-heavy tracks).** The first hint must not contain the answer's key term:

| Track | Forbidden first-hint patterns |
|---|---|
| Data Engineering | `idempoten*`, `watermark*`, `exactly-once` |
| Statistics | `p-value`, `null hypothesis`, `central limit theorem` |
| ML Fundamentals | `bias-variance`, `overfitting`, `data leakage` |
| Experimentation | `cuped`, `sample ratio mismatch`, `switchback` |

Anti-patterns: H1 reading like the first line of the solution; pasting code / method chains / clause text; H2 naming every required op in order; (MCQ) restating the correct option instead of hinting through elimination.

---

## Concept-tag contract (cross-track)

`concepts` is a learner-facing semantic tag describing the *reasoning pattern* — not a parser keyword or API name.

- **2–4 tags** per question (5 only when a hard question genuinely teaches multiple dependent patterns).
- Every tag must map to a registered family for the track via the algorithm in [`docs/concept-taxonomy.md`](./concept-taxonomy.md). The validator rejects unmappable tags AND per-track blocklist matches at catalog load.
- Prefer the *reasoning pattern* over the *tool name*. The tag should still make sense if the same problem were solved in another syntax / library (within reason — track-native patterns are OK).
- No near-duplicate tags (`JOIN` + `INNER JOIN` both blocked).
- No onboarding / meta tags (`CTE INTRODUCTION`, `WITH CLAUSE SYNTAX`).
- **Tag the *distinguishing* technique, not incidental mechanics.** Foundational families that almost every question touches (result ordering, column projection, basic grouping, simple iteration) are concepts *only when they are the primary reasoning being tested*. Never bolt a foundational family onto an advanced question just because the construct happens to appear — tag what makes the question hard. A "weak on GROUPED AGGREGATION" insight must mean *can't aggregate*, not *failed a window-function question that happened to group*. (Mirrors how StrataScratch / DataLemur / NeetCode categorise by primary technique.)

Per-track family lists, blocklists, and resolution rules: [`docs/concept-taxonomy.md`](./concept-taxonomy.md).

**Quick test:** *"If a user saw this tag in a weak-spot insight, would it teach them what kind of thinking to improve?"* If no, rewrite.

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
- **Special types** (track-specific, see per-track doc):
  - `framing: "scenario"` — narrative business brief in `description` (≤3 sentences, grounded)
  - `type: "reverse"` (SQL only) — user sees `result_preview`, writes the query
  - `type: "debug"` — `debug_error` is a real engine error string; starter has exactly one bug

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
| SQL | 37 | 47 | 31 | **115** | Executable (DuckDB) |
| Python | 33 | 29 | 17 | **79** | Executable (sandbox) |
| Pandas | 27 | 36 | 23 | **86** | Executable (sandbox) |
| PySpark | 41 | 39 | 36 | **116** | Code-adjacent reasoning (MCQ) |
| Data Engineering | 30 | 35 | 26 | **91** | Constructed reasoning (MCQ) |
| Data Modeling | 25 | 28 | 23 | **76** | Constructed reasoning (MCQ) |
| Statistics | 31 | 41 | 25 | **97** | Hybrid (conceptual MCQ + numerical Python) |
| ML Fundamentals | 30 | 38 | 28 | **96** | Constructed reasoning (MCQ) |
| Experimentation | 30 | 32 | 22 | **84** | Constructed reasoning (MCQ) |
| **Total** | | | | **840** | |

Mock-only add-on bank: **394 questions** (Pro/Elite only). Samples: **36 total** SQL/Python/Pandas/PySpark + auto-sliced from practice for the other 5 tracks.

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

#### Path schema

| Field | Required | Notes |
|---|---|---|
| `slug` | ✓ | Unique, hyphenated. URL: `/learn/<topic>/<slug>` |
| `title` | ✓ | ≤50 chars, user-facing |
| `description` | ✓ | 1–2 sentences |
| `topic` | ✓ | Must match a track slug |
| `tier` | ✓ | `free` or `pro` — controls **path-listing visibility only** (the questions inside follow practice unlock thresholds regardless) |
| `role` | ✓ | `starter` \| `intermediate` \| `advanced` — defined below |
| `patterns` | ✓ | Non-empty array; every entry must resolve in `path_patterns.py` for the track |
| `focus_concepts` | ✓ | Non-empty array; every entry must resolve to a registered family in `concept_families.py` for taxonomy-validated tracks (others: presence check only until registries are complete) |
| `questions` | ✓ | Ordered array of catalog question IDs (easy → hard within the pattern). Every ID must exist in the track catalog. Every question must carry at least one concept tag in the same family as one of the path's `focus_concepts[]` (mechanical guarantee that the path drills what it claims). |
| `outcomes` | ✓ | 1–2 sentences starting with "You'll…" describing capability gained |
| `recommended_after` | ✓ | Prerequisite path slugs (same track). Empty array `[]` for starter paths. The resulting graph must be acyclic. |

#### Role definition

**Role describes where the path sits in the track's pattern arc — not the difficulty mix of its questions.** Difficulty mix is whatever the catalog naturally supports for the patterns the path drills.

- **`starter`** — Covers the foundational patterns of the track: the building blocks every other path assumes. **Exactly one per track** (validator-enforced). UX promise: every track has one obvious entry point ("Start here").
- **`intermediate`** — Mid-tier patterns sitting on top of the foundational layer. **One or more per track.** When a track has parallel mid-tier clusters (e.g. data-modeling: normalization vs dimensional), each gets its own intermediate path — they are not forced to compete for a singleton slot.
- **`advanced`** — Advanced patterns assuming both foundations and some mid-tier exposure. **Zero or more per track.**

Role has no unlock semantics. Roles are used for sort order on TrackHub, the "Start here" pill on the singleton starter, and Schema.org metadata. **Path completion does not unlock any practice questions** — unlocks follow the standard practice thresholds (see `docs/backend.md` for the unlock-state computation).

#### Validator integrity rules

`backend/scripts/validate_content.py::_validate_paths` enforces:

1. **Schema completeness.** All required fields present; slug unique; matches filename.
2. **Singleton starter.** Exactly one `role=starter` per track. No upper bound on `intermediate` or `advanced`.
3. **Pattern registry.** Every `patterns[]` entry resolves in `path_patterns.py` for the path's track.
4. **Focus-concept registry.** Every `focus_concepts[]` entry resolves to a registered family in `concept_families.py` (only enforced for tracks listed in `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py` — currently `{sql, python}`; others get a presence-only check). **When a track joins the validated set, the path validator immediately enforces this rule strictly for it** — coordinate the concept-family registry completion + paths re-check in the same PR.
5. **Question-tag alignment.** Every question in `questions[]` carries at least one concept tag that resolves to the same family as at least one of the path's `focus_concepts[]`. This is the mechanical guarantee that the path drills what it claims.
6. **Prerequisite DAG.** Every `recommended_after[]` slug exists in the same track; the resulting graph is acyclic.

#### What this section explicitly rejects (historical)

The platform previously had a "path-completion unlock shortcut" mechanic (completing a starter path unlocked all medium; completing intermediate unlocked the hard cap). **That mechanic was removed.** If you find a doc still describing it, that doc is stale — fix it and link here. The current model is: practice thresholds gate question unlocking; paths are curated walks that respect those gates.
