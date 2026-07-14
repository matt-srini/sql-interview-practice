# Track Onboarding Guide

> **Navigation:** [Docs index](../README.md) · [Content Authoring](./content-authoring.md) · [Architecture](./architecture.md) · [Backend](./backend.md) · [Frontend](./frontend.md)

This is the authoritative checklist for launching a new question track on datathink. Every aspect of a track — curriculum design, ID allocation, backend scaffolding, frontend registration, content authoring, learning paths, and documentation — must be completed and verified before the track goes live. No phase is optional.

**AI onboarding agent:** [`.github/agents/track-onboarding.agent.md`](../.github/agents/track-onboarding.agent.md) — use this prompt when driving the implementation with Claude.

**Exhaustive surface inventory:** [`track-integration-surfaces.md`](./track-integration-surfaces.md) — **read this too.** It lists *every* place a track's identity/counts/copy appears, split into what now auto-derives from the `TRACKS` registry vs. what still needs a manual per-track entry (and which completeness test guards it). Written after track 10 shipped with `0/0` counts and a 500ing path detail because the track list was hardcoded in ~12 places; it exists so track 11 doesn't repeat that.

---

## Overview of phases

| Phase | What happens | Gate |
|---|---|---|
| 0 · Specification | Define scope, audience, format, color, slug, T digit | Written spec approved before any code |
| 1 · Curriculum design | Concept map, question counts, formats, mock themes, tags, paths | Full spec complete before authoring starts |
| 2 · Backend scaffolding | catalog loader, tracks.py entry, content dir, schemas.json | Backend starts cleanly with empty catalog |
| 3 · Frontend registration | trackRegistry.js, ROLES in LandingPage, route smoke-test | Landing page shows track before content exists |
| 4 · Content authoring | Questions authored in curriculum order, validated in batches | validate_content.py + pytest pass clean |
| 5 · Learning paths | Path JSON files authored, path endpoints verified | All paths load and resolve question states |
| 6 · Docs update | content-authoring.md, CLAUDE.md, backend.md, frontend.md | All docs accurate before launch commit |
| 7 · Pre-launch verification | Full checklist — IDs, counts, endpoints, UI | Every item checked before announcing |

---

## Phase 0 — Specification

Before writing any code or content, answer every question below in a short spec (a GitHub discussion, a doc comment, or a conversation). Do not proceed to Phase 1 until the spec is agreed.

| Question | Notes |
|---|---|
| **What does this track cover?** | Which DS/DE/analytics interview scenarios? What is explicitly out of scope? |
| **Who is the audience?** | Which roles (from the landing page role selector) benefit? At what career level? |
| **Eval kind** | `sql` · `python` · `pandas` · `mcq` · `mixed` — drives submission dispatch |
| **Unlock profile** | `code` or `mcq` — metadata field in `TrackConfig`; retained for schema compatibility. Not consumed by unlock logic (the flat access model uses plan only). |
| **In mixed mock?** | Should this track appear in the `"mixed"` mock pool? |
| **Track color** | Unique hex, consistent with the existing palette. Current palette: SQL `#5B6AF0` · Python `#2D9E6B` · Pandas `#C47F17` · PySpark `#D94F3D` · DE `#B9762B` · Data Modeling `#3F8E8C` · Statistics `#7A5AF0` · ML Fundamentals `#E0456A` · Experimentation `#0EA5E9` |
| **Track slug** | URL-safe, hyphenated, unique. Becomes the `:topic` route param. |
| **T digit** | Next free from `backend/tracks.py` reserved list (currently 8–9). |

---

## Phase 1 — Curriculum Design

This is the most important phase. A track with a weak curriculum design cannot be fixed by adding more questions later. Complete every section before authoring begins.

### 1.1 Concept coverage map

List **all** concepts the track covers, organized by difficulty tier. For each tier verify:
- Are the concepts genuinely at that difficulty level? Do they build on the previous tier?
- Is there meaningful pedagogical progression (easy → medium → hard)?
- Does every concept have at least one question that teaches it?

The concept coverage map becomes the canonical reference during authoring — if a concept is in the map, it must appear in at least 2 questions. If a concept is not in the map, do not add questions for it without first updating the map.

### 1.2 Question counts

Decide counts before authoring. Once set, do not increase counts arbitrarily — mock pool sizing depends on stable totals.

**Guideline ranges by eval_kind:**

| Eval kind | Easy (practice) | Medium (practice) | Hard (practice) | Mock-M | Mock-H | Practice total | Grand total |
|---|---|---|---|---|---|---|---|
| `code` (SQL/Python/Pandas) | 25–35 | 28–36 | 22–30 | 0 | 8–14 | 75–101 | 83–115 |
| `mcq` (PySpark/DE/DM) | 28–40 | 28–40 | 20–28 | 0 | 8–20 | 76–108 | 84–128 |
| `mixed` (Statistics) | 24–30 | 24–30 | 20–28 | 0 | 0–10 | 68–88 | 68–98 |

**Rules:**
- No easy mock-only questions for any track — easy is practice-only by design.
- Mock-only questions are allocated at the **top of the medium/hard difficulty range**, immediately after the last practice question.
- Set these counts in the spec and commit to them. Changing counts after content is authored can break learning path references and mock pool sizing.

### 1.3 Question formats

**For MCQ tracks** (`mcq` eval_kind — PySpark, DE, DM, ML Fundamentals, Experimentation):

Define the format mix and target percentages. Reference PySpark/DE as examples. Recommended format types:

| Type | Use for |
|---|---|
| `conceptual` | Conceptual understanding anchored in a concrete real-world scenario — evaluated via single-best-answer MCQ |
| `scenario` | Multi-clue production/design diagnosis with realistic context |
| `predict_output` | Given a snippet or configuration, predict what happens |
| `debug` | Given broken code or a flawed design, identify the root cause |
| `optimization` | Given a real constraint, choose the best approach and justify |

Easy tier must **not** be pure-recall conceptual. Prefer scenario, predict_output, or debug at easy to force reasoning rather than memorisation.

**For code tracks** (`sql`, `python`, `pandas`): define test case counts per difficulty (see `docs/content-authoring.md` per-track sections).

**For mixed tracks** (`mixed` eval_kind — Statistics): define the conceptual/numerical subtype split per difficulty tier.

### 1.4 Mock-only question themes

List 3–5 scenario themes for medium mock questions and 5–8 for hard mock questions. Mock themes must:
- Be multi-concept (integrate 2+ related concepts in one scenario)
- Not duplicate practice bank question angles
- Feel like real FAANG interview scenarios, not academic exercises

Mock themes should be written as 1-sentence descriptions: *"Integrated model evaluation scenario: candidate must select the correct metric for a class-imbalanced fraud dataset, justify it against alternatives, and diagnose why accuracy is misleading."*

### 1.5 Concept tags (semantic, not API-level)

Define all semantic concept tags for the track. These are used for:
- Concept pills shown on question cards
- Dashboard weak-spot insights
- Learning path `focus_concepts` routing

Rules (same as the global rules in `docs/content-authoring.md`):
- Tags describe the **pattern or reasoning skill**, not the API or function name
- Target 30–60 tags per track
- Tags must still make sense if the same problem were solved in a different syntax or library
- Ask: *"If a user saw this tag in a weak-spot insight, would it teach them what kind of thinking to improve?"*

In parallel, define the **concept blocklist** — lowercase strings that are too API-specific for the validator to allow (e.g. `"p-value"`, `"groupby"`, `"filter()"`, `"scipy"`). The validator in `backend/scripts/validate_content.py` rejects these.

### 1.6 Hint rules

Specify per difficulty:

| Difficulty | Min hints | Max hints | Hint ladder description |
|---|---|---|---|
| Easy | 1–2 | 2 | Hint 1 identifies the mental model or concept class. Hint 2 points to the reasoning direction without naming the answer. |
| Medium | 2 | 3 | Hint 1 identifies the core pattern. Hint 2 identifies the sub-problem split or intermediate step. Hint 3 names the tool/approach family only if genuinely needed. |
| Hard | 2 | 3 | Hint 1 identifies the decomposition strategy. Hint 2 identifies the dependency ordering or key constraint. Hint 3 points to the final assembly or the most common failure mode. |

Also define **first-hint leak patterns** — regex patterns for answer-revealing terms that the validator flags when they appear in the first hint. Examples: `r"\bconfidence\s+interval\b"`, `r"\bdata\s+leakage\b"`, `r"\bSRM\b"`. These protect the integrity of the hint ladder.

### 1.7 Learning paths

**Canonical reference: [`docs/content-authoring.md`](./content-authoring.md) §Paths.** That section defines the path model (patterns vs concepts), the level enum, the schema, and the validator integrity rules. This subsection only summarises the per-track minimums for onboarding.

Every track requires:

- **At least one `foundational` path** (validator floor: ≥ 1 — most tracks run **2–3**, content-driven; the UX entry point that gets the "Start here" pill on TrackHub).
- At least **one `intermediate` path** (covers a mid-tier pattern cluster). Multiple intermediates allowed when a track has parallel mid-tier clusters.
- At least **one `advanced` path** for tracks with 80+ practice questions. Tracks below that may launch with foundational + intermediate only and add advanced paths as the catalog grows.

Each path:

- Declares one or more `patterns[]` slugs from `backend/path_patterns.py` (register new pattern slugs there if no existing pattern fits).
- Declares `focus_concepts[]` resolving to the track's concept-family registry (so dashboard insights can recommend the path from a weak concept).
- Lists 5–9 catalog question IDs in `questions[]`, ordered easy → hard within the pattern.

Paths do not unlock anything — question access follows the plan policy (free = easy only; Pro/Elite = all difficulties; see [`docs/backend.md`](../docs/backend.md) § Unlock model). Path completion just marks every question solved, same as practice.

---

## Phase 2 — Backend Scaffolding

### 2.1 Assign track digit T

Pick the next free T from `backend/tracks.py` (currently 8–9 are reserved). Update the ID allocation table in `docs/content-authoring.md`.

### 2.2 Create `schemas.json`

```json
{
  "difficulty_files": {
    "easy": "easy.json",
    "medium": "medium.json",
    "hard": "hard.json"
  },
  "id_ranges": {
    "easy":   [T1001, T1999],
    "medium": [T2001, T2999],
    "hard":   [T3001, T3999]
  }
}
```

`schemas.json` must exist **before** any question file is committed. The catalog loader validates every ID at startup and crashes on violation.

### 2.3 Create the catalog loader module

Copy the nearest equivalent loader (e.g. `data_engineering_questions.py` for MCQ tracks, `statistics_questions.py` for mixed tracks) and adapt:
- Rename to `<track_slug_underscored>_questions.py`
- Update the content directory path
- Update the `schemas.json` path reference
- Verify it exposes: `get_questions_by_difficulty()`, `get_mock_questions_by_difficulty()`, `get_public_question()`, `get_catalog()`

### 2.4 Register in `backend/tracks.py`

Import the new catalog module at the top of `tracks.py`, then add a `TrackConfig` entry to the `TRACKS` tuple. Every field is required:

```python
TrackConfig(
    slug="<slug>",
    db_topic="<slug>",               # match slug for all new tracks (no legacy alias)
    catalog_module=<module>,
    label="<Display Name>",
    eval_kind="mcq",                 # or "sql" | "python" | "pandas" | "mixed"
    unlock_profile="mcq",            # or "code"
    content_dir=BACKEND_ROOT / "content" / "<content_dir>",
    concept_blocklist={
        "<api-term-1>",
        "<api-term-2>",
    },
    hint_rules={"easy": (1, 2), "medium": (2, 3), "hard": (2, 3)},
    first_hint_leak_patterns=(
        re.compile(r"\b<term>\b", re.IGNORECASE),
    ),
    in_mixed_mock=False,             # True only if the track joins the mixed mock pool
    mixed_subtype=False,             # True only for dual-subtype tracks like Statistics
),
```

### 2.5 Create the content directory structure

```
backend/content/<track>_questions/
├── schemas.json       ← from step 2.2
├── easy.json          ← [] initially (empty array)
├── medium.json        ← [] initially
└── hard.json          ← [] initially
```

### 2.6 Verify backend starts cleanly

```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
# Check /health — new track tables should appear
# Check /api/<slug>/catalog — should return {"easy": [], "medium": [], "hard": []} without errors
```

---

## Phase 3 — Frontend Registration

### 3.1 Add to `frontend/src/trackRegistry.js`

Add an entry to `TRACK_META`:

```javascript
'<slug>': {
  label: '<Display Name>',
  description: '<1–2 sentence description for the landing page tracks index>',
  color: '<#hex>',
  apiPrefix: '/<slug>',   // empty string '' for SQL only
  language: 'text',       // 'sql' | 'python' | 'text'
  hasRunCode: false,       // true for SQL/Python/Pandas
  hasMCQ: true,            // true for MCQ tracks
  mixedSubtype: false,     // true only for Statistics
  totalQuestions: 0,       // update to final count when content is complete
  easyQuestions: 0,        // update when easy content is authored
  tagline: '<short format hint, e.g. "conceptual · scenario · debug">',
  comingSoon: true,        // remove on launch
},
```

Everything else — routing, catalog path, sidebar, TrackHub — derives from this single entry. No other frontend file needs editing for registration.

### 3.2 Add to the role selector in `frontend/src/roleRegistry.js`

The canonical role→track mapping is `frontend/src/roleRegistry.js` (the `ROLES` SoT that LandingPage role tabs, MockHub `MOCK_ROLES`, the dashboard `ROLE_TRACK_FILTERS`, and the `mockModeConfig` Mixed-benchmark question count all derive from). For a **live** track, add its slug to the relevant role `tracks: []` arrays. Consider:
- Which roles genuinely benefit from this track?
- What order (most relevant to that role first)?
- Does it replace or supplement an existing track in that role's list?
- If you change a role's track count, bump the length assertion in `frontend/src/roleRegistry.test.js`.

**Coming-soon tracks do NOT join the role registry until launch.** A `comingSoon` track is left out of `roleRegistry.js` (and the backend `_ROLE_TRACKS`, the `RoleInterviewPrepPage` editorial lists, and the `spa.py` `/interview-prep` copy) until launch. It still surfaces as a "Coming soon" card on the landing **Tracks Index** (section 06) via `trackRegistry.js`, so discovery is preserved without role membership. Reason: `roleRegistry` is not display-only — `mockModeConfig` derives each role's Mixed-benchmark question count from the raw `role.tracks` (one slot per track, no `comingSoon`/`TRACK_SLUGS` filter), so a zero-question track inflates the count and desyncs from the backend's hardcoded per-role benchmark slots; `_ROLE_TRACKS` would likewise leak it into Mixed-custom draws and fail the pooled-track-validity guard (`tests/test_11_mock.py`). Wire all role→track membership (frontend + backend + SEO + the `roleRegistry.test.js` assertion) together in the launch commit, when `comingSoon` is removed. Rationale: [`DECISIONS.md`](./decisions/DECISIONS.md) 2026-07-13.

### 3.3 Add a demo frame to `IDE_TRACKS` in `frontend/src/pages/LandingPage.js`

The HeroIDE animation (section 01) cycles through a **hardcoded** `IDE_TRACKS` array — one entry per track. You must add a new entry for the new track; it is not derived from `trackRegistry.js`.

For MCQ tracks (no code execution), the entry shape is:

```js
{
  slug: 'new-track-slug',
  label: 'Short Label',          // shown on the nav dot tooltip — keep ≤10 chars
  color: '#HEXHEX',              // track color, must match trackRegistry.js
  fname: 'demo_filename.md',     // realistic filename shown in the IDE chrome
  badge: 'Track Name · MCQ',    // shown in the chrome badge next to filename
  code: null,
  type: 'mcq',
  question: 'A representative question stem (keep it to one sentence)',
  options: ['Option A', 'Option B', 'Option C', 'Option D'],
  correct: 0,                    // 0-indexed correct answer
},
```

For tracks with code execution (`type: 'table'` or `type: 'tests'`), copy the shape from an existing entry (e.g. `sql` → `table`, `python` → `tests`).

**Pick a question that makes the track's value obvious at a glance.** A first-time visitor should be able to read the question and immediately understand what the track covers and why it's hard. Avoid trivial definitions; prefer questions that reveal a surprising trade-off or behavior.

### 3.4 Smoke-test the landing page

- HeroIDE cycles to the new track frame (section 01) — correct question, color, badge
- Track appears in the Tracks Index (section 06) with correct question count (0 during development, updated on launch)
- Track appears in the correct role tabs (section 04)
- If `comingSoon: true`: "Coming soon" badge shows, no "Enter →" link
- Track color appears correctly in the dot and (for live tracks) the CTA

---

## Phase 4 — Content Authoring

All per-format rules are in `docs/content-authoring.md`. The additional track-level requirements:

### 4.1 Author in curriculum order

Author easy questions first, then medium, then hard. Within each difficulty, follow the concept coverage map from Phase 1 — author to the progression, not randomly. The `order` field in each question JSON controls sidebar and sample ordering; assign it sequentially starting at 1.

### 4.2 Maintain format balance

For MCQ tracks: track the format counts as you author. Do not let the track become 80%+ pure conceptual. Use the target distribution from Phase 1.3 and check it every 15–20 questions.

### 4.3 Ensure concept tag coverage

Every concept in the Phase 1 coverage map must appear on at least 2 questions. Every tag in the taxonomy must be used on at least 1 question. After authoring each difficulty tier, do a coverage pass: list every concept tag and count how many questions use it.

### 4.4 Maintain distractor quality (MCQ tracks)

Each wrong option must represent a **genuine misconception** — a conclusion a partially-informed candidate could reach. Wrong options must not be obviously wrong, trivially implausible, or distinguishable by length/tone. The explanation must address **all 4 options**, not just the correct one.

### 4.5 Author mock-only questions last

Practice questions come first. Once the practice bank is complete, author mock-only questions using concept angles NOT already covered in the practice bank. Mock-only questions are identified by `"mock_only": true` and must be multi-concept (integrate 2+ related concepts). Allocate their IDs at the top of the medium/hard range, immediately after the last practice question.

### 4.6 Commit cadence

Commit in exactly this sequence — one commit per phase, not one giant commit at the end:

| Commit | Contents |
|---|---|
| Phase 2+3 scaffolding | `schemas.json`, empty JSON files, loader, `tracks.py` entry, `trackRegistry.js`, `ROLES`, `IDE_TRACKS`, `main.py` router wiring |
| Easy questions | `easy.json` complete, validated |
| Medium + hard practice | `medium.json` (practice only) + `hard.json` (practice only), validated |
| Mock-only | Medium + hard mock questions appended to their respective files |
| Phase 5+6 | Path JSON files + full docs update (`CLAUDE.md`, `content-authoring.md`) + `trackRegistry.js` `totalQuestions` + remove `comingSoon` |

This cadence makes git history readable, keeps each commit reviewable, and ensures the docs update is never an afterthought.

### 4.7 Validate in batches

After every 10–15 questions:

```bash
# 1. Duplicate ID check
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    all_ids.extend(q['id'] for q in json.load(open(f)))
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"

# 2. JSON validity
python3 -c "
import json, glob
for f in glob.glob('backend/content/*/*.json'):
    json.load(open(f))
print('All valid')
"

# 3. Content validator
cd backend && ../.venv/bin/python scripts/validate_content.py

# 4. Backend tests
cd backend && ../.venv/bin/python -m pytest tests/ -q
```

---

## Phase 5 — Learning Paths

### 5.1 Author path JSON files

Create one JSON file per path in `backend/content/paths/`. Naming convention: `<slug>.json`.

```json
{
  "slug": "<track-slug>-<path-name>",
  "title": "<Path Title>",
  "description": "<1–2 sentence description shown in PathProgressCard>",
  "topic": "<track-slug>",
  "tier": "free",
  "level": "foundational",
  "questions": [<id1>, <id2>, ...],
  "focus_concepts": ["CONCEPT ONE", "CONCEPT TWO"],
  "outcomes": "You'll be able to...",
  "recommended_after": []
}
```

### 5.2 Verify paths load and resolve

```bash
# All paths including new ones
curl http://localhost:8000/api/paths | python3 -m json.tool | grep '"slug"'

# Specific path detail (includes per-question state)
curl http://localhost:8000/api/paths/<slug> | python3 -m json.tool
```

Confirm:
- All question IDs in `questions[]` resolve to real catalog entries
- `tier` and `role` are set correctly
- `focus_concepts` tags match the track's concept family style

---

## Phase 6 — Docs Update (mandatory — same commit as launch)

Every track launch must update all of the following files in the same commit. Do not skip any.

| File | What to update |
|---|---|
| `docs/content-authoring.md` | Question bank table (add row + update total), learning paths table (add paths), concept coverage section (new `###` section for the track), ID allocation table (add the new T digit row) |
| `CLAUDE.md` | Content footprint table (add row), practice totals line, mock-only totals line, Tracks list in "What this is", docs index if a new doc was created |
| `docs/backend.md` | Track table if any new `eval_kind`, `unlock_profile`, or API endpoint was introduced |
| `docs/frontend.md` | `TRACK_SLUGS` / `TRACK_META` count, role selector section if roles changed |
| `frontend/src/trackRegistry.js` | `totalQuestions` and `easyQuestions` updated to final counts; `comingSoon` removed |

---

## Phase 7 — Pre-launch Verification Checklist

Run every item before pushing the launch commit.

### Content integrity
- [ ] All question IDs are in the correct TXNNN range for their difficulty
- [ ] All question IDs are globally unique (run the duplicate check from Phase 4.6)
- [ ] `schemas.json` `id_ranges` match the actual ID ranges in the question files
- [ ] All `order` values are sequential starting at 1, no gaps within a difficulty file
- [ ] Practice questions do **not** have `"mock_only": true`
- [ ] Mock-only questions **do** have `"mock_only": true`
- [ ] No easy-difficulty mock-only questions exist
- [ ] Every concept in the Phase 1 coverage map appears on ≥2 questions
- [ ] Every concept tag in the taxonomy is used on ≥1 question
- [ ] Format distribution matches the target percentages from Phase 1.3 (MCQ tracks)
- [ ] `python scripts/validate_content.py` passes clean with no warnings
- [ ] `pytest tests/` passes

### Backend
- [ ] Backend starts without errors; `/health` shows the new track
- [ ] `/api/<slug>/catalog` returns questions grouped by difficulty
- [ ] `/api/<slug>/questions/{id}` returns a question (locked fields hidden for locked questions)
- [ ] `/api/sample/<slug>/easy` returns a sample question
- [ ] `/api/sample/<slug>/medium` returns a sample question
- [ ] `/api/sample/<slug>/hard` returns a sample question
- [ ] `/api/mock/access` returns correct `can_start` / `block_reason` for the new track
- [ ] Unlock logic works: Free user sees easy unlocked, medium/hard locked at start
- [ ] At least one `foundational` path exists for the new track (validator-enforced)
- [ ] Every path declares `patterns[]` from `backend/path_patterns.py` and `focus_concepts[]` that resolve to a track concept family

### Frontend
- [ ] Track appears in the Tracks Index (section 06) with correct question count
- [ ] Track appears in the correct role selector tabs (section 04)
- [ ] `comingSoon` flag is removed from `trackRegistry.js`
- [ ] `totalQuestions` and `easyQuestions` in `trackRegistry.js` match actual counts
- [ ] Sample mode works end-to-end in browser (`/sample/<slug>/easy`)
- [ ] Practice mode works end-to-end in browser (`/practice/<slug>/questions/<id>`)
- [ ] Mock session works for the new track (Pro/Elite account required)
- [ ] Track color appears consistently: dot, CTA, concept pills, progress bar

### Docs
- [ ] `docs/content-authoring.md` question bank table is accurate
- [ ] `docs/content-authoring.md` learning paths table is accurate
- [ ] `docs/content-authoring.md` concept coverage section exists for the track
- [ ] `docs/content-authoring.md` ID allocation table has the new T digit row
- [ ] `CLAUDE.md` content footprint table, totals, and track list are accurate

---

## Quick reference: track digit assignments

| T | Track | Slug | Status |
|---|---|---|---|
| 1 | SQL | `sql` | Live |
| 2 | Python | `python` | Live |
| 3 | Pandas | `pandas` | Live |
| 4 | PySpark | `pyspark` | Live |
| 5 | Data Engineering | `data-engineering` | Live |
| 6 | Data Modeling | `data-modeling` | Live |
| 7 | Statistics | `statistics` | Live |
| 8 | ML Fundamentals | `ml-fundamentals` | Live |
| 9 | Experimentation | `experimentation` | Live |
| 10\* | Product Sense | `product-sense` | In development (worktree branch `product-sense-track`) |

\* Track 10 has no free single leading digit (1–9 are exhausted), so it uses a two-digit ID prefix: `10XNNN` practice/mock, `10XS` samples. See [`content-authoring.md`](./content-authoring.md) § TXNNN ID scheme.

---

## Common mistakes to avoid

**Skipping Phase 1.** The concept coverage map feels like overhead but it's the only thing that guarantees curriculum coherence. Tracks authored without one develop blind spots (50% of questions on one concept, zero on another) that can't be easily fixed without renumbering.

**Authoring mock questions before practice is complete.** Mock-only questions recombine concepts the practice curriculum already taught, under fresh framing — they never debut a concept. You can't know which concepts are "already taught" (or which framings would just clone a practice question) until the practice bank is fully authored.

**Setting `totalQuestions` in `trackRegistry.js` before content is complete.** The landing page shows this number. Keep `comingSoon: true` until content is fully authored, validated, and committed — then set `totalQuestions` to the final practice count and remove `comingSoon`.

**Updating `CLAUDE.md` and `docs/` as a follow-up commit.** The rule is: docs update in the same commit as the code change they describe. Docs that lag behind accumulate rot.

**Forgetting the `schemas.json`-first rule.** The catalog loader crashes at startup if `schemas.json` is missing or its `id_ranges` don't cover the actual IDs in the question files. Create it before authoring any questions.

**Adding a concept tag to a question that isn't in the concept blocklist check.** The blocklist only rejects terms that are explicitly listed. It's easy to add low-level tags like `"p-value"` or `"groupby"` that sound like patterns but are actually API names. Always apply the "would this teach a user what kind of thinking to improve?" test before committing a tag.
