# `/guides` article style guide

**Single SoT for the voice, rules, and mechanics of every long-form `/guides` article.** Publishing a
guide = dropping a markdown file into `backend/content/guides/`. This doc governs how those files read.
Referenced from [`editorial-calendar.md`](editorial-calendar.md) § SEO pillar waves; the rendering
contract lives in `backend/routers/guides.py`; the broader brand voice lives in
[`starter-assets.md`](starter-assets.md) § Voice and [`gtm-strategy.md`](gtm-strategy.md) (pro-reasoning,
never anti-competitor). Current guide voice reference: the 2026-07-14 guide batch in
`backend/content/guides/`, which keeps the tone natural, friendly, and broadly applicable.

---

## 1. Voice: write as a senior practitioner

**Every article is written in the voice of a senior data professional in the discipline the article is
about** — someone who has done the job for years and understands what interviews usually check, while
still writing for a broad search visitor. Not a content marketer, not a bootcamp instructor, not a
brand. A senior practitioner explaining the role clearly to a smart peer.

Match the persona to the article's primary discipline:

| Article subject | Persona to write as |
|---|---|
| SQL depth, pipelines, idempotency, PySpark, data engineering | **Senior data engineer / data architect** |
| Metric definition, analyst SQL, dashboards, "is this signal" | **Senior data analyst** |
| ML, bias-variance, statistics, experimentation, A/B testing | **Senior data scientist** |
| Dimensional modeling, grain, dbt, the transformation layer | **Senior analytics engineer** |
| Tooling / cross-cutting (e.g. pandas vs SQL) | The persona whose **day-to-day the article most reflects** — pick one, do not hedge between them |

The persona shows up as *judgment*, not as a costume. It means the article knows what actually breaks
in production, what an interview is usually checking, and where candidates predictably go wrong. Keep
the examples general enough that a reader from any company can recognize the pattern.

## 2. The brand bar (non-negotiable)

- **Reasoning-premium.** Teach the reasoning that makes someone effective in the role; interview success
  is the consequence, not the pitch. Every article must be genuinely useful and original on its own.
- **Confident, calm, specific.** The existing datathink voice ([`starter-assets.md`](starter-assets.md)).
- **Pro-reasoning, never anti-competitor.** "LeetCode has X" is not an argument and never appears. We
  make our case on depth, not on someone else's shortcomings.
- **No hype, no volume-as-value.** No superlatives about datathink, no "965 questions" as a flex, no
  growth-hack energy. The product is mentioned once or twice, softly, near the end.
- **Show the why.** Mechanism over assertion. If you claim a query double-counts, show *how* the
  fan-out happens.

## 3. Sound human, not generated (the anti-AI-tells)

This is where most drafts fail. Polished, confident, and frictionless reads as machine-written. Break
the tells deliberately:

- **Vary sentence rhythm.** Do not write a metronome of short declaratives. Mix long, clause-rich
  sentences with genuinely short ones. Read it aloud; if it has a uniform beat, rewrite.
- **Kill the antithesis crutch.** "It's not X, it's Y" and "X is not reasoning" constructions are an AI
  signature when stacked. One or two in a whole article, maximum.
- **Don't land every paragraph on a tidy aphorism.** The mic-drop closer, paragraph after paragraph, is
  a tell. Let most paragraphs end on a working observation instead.
- **Use practical specifics, not interview-room anecdotes.** A concrete pattern beats a clean abstraction:
  a join that changes grain, a sample-ratio mismatch, a tied timestamp, a leaking feature. Do not write
  as if the author watched a particular interview. Keep it generic and reusable.
- **Keep first person rare.** The default guide voice should be direct and friendly, not memoir-like.
  Avoid "I watched candidates..." and "I have interviewed people..." unless there is a specific signed
  reason to use it.
- **Allow texture.** Mild hedges and dry asides ("honestly," "cheerfully falls over," "wearing different
  business clothes") are human. Models sanitize these out; put some back.
- **Stay concrete with domain nouns.** `ROW_NUMBER`, sample ratio mismatch, a learning curve, MERGE.
  Specificity reads as expertise.
- **Define a loaded term once, then use it.** A broad search visitor may not know grain, fan-out,
  shuffle, idempotency, or SCD Type 2. Introduce the term with a short inline gloss on first use ("the
  grain, what one row represents"), then use it plainly. Avoiding the term reads as dumbed-down;
  re-explaining it every time reads as padding. (The weekly-cut social register this mirrors is
  canonical in [`gtm-strategy.md`](gtm-strategy.md) § 4; this doc owns the long-form guide voice.)
- **Banned register.** No throat-clearing openers ("In today's data-driven world"), no listicle
  scaffolding ("Let's dive in"), no LLM-vocabulary tells (delve, leverage, robust, seamless, unlock,
  realm, tapestry, "it's worth noting"), no emoji, no exclamation marks.

**Smell test before publishing:** could a competent model have produced this paragraph from the heading
alone? If yes, it needs a specific, a rhythm break, or a real opinion.

## 4. Structure and SEO mechanics

- **Target one role+intent query.** Lead the title with the query phrasing; a punchier tail is fine
  (e.g. "Data Analyst Interview Questions: What They Are Actually Checking").
- **Length:** ~900–1,400 words. Enough to be the best answer to the query, not padded.
- **Frontmatter contract** (see `guides.py`):
  - `title` — **without** the brand suffix; the template renders `{title} | datathink`.
  - `description` — ≤160 chars, a real summary, **no em-dashes**.
  - `slug` — must equal the filename (minus `.md`).
  - `date` / `updated` — ISO dates; `draft: false` to publish (true keeps it 404 + out of sitemap).
- **No em-dashes (—) anywhere** — title, description, *and* body. SEO strings ban them
  ([`seo.md`](../seo.md)); we extend the ban to body prose for brand consistency. Avoid en-dashes (–)
  too. Use commas, colons, periods, parentheses.
- **Markdown:** `##` section headers, standard markdown links. Available extensions: fenced code,
  tables, toc, sane lists.

## 5. The internal-link mesh

Every article wires into the hub-and-spoke (see [`editorial-calendar.md`](editorial-calendar.md) § SEO
pillar waves):

- Link to the relevant **`/interview-prep/<role>`** page and at least one **`/sample/<track>`**, as
  markdown links woven into a sentence — never a bare "try it now" banner. The CTA is earned and soft.
- Where natural, link a **role pillar ↔ track pillar** and to **`/learn/<topic>`** (the live paths
  surface). Link to `/learn/<topic>`, never enumerate path slugs (they get re-leveled and go stale).
- Role framing to draw on lives in `frontend/src/pages/RoleInterviewPrepPage.js`; concept seeds in
  [`../concept-hooks.md`](../concept-hooks.md) and [`../concept-taxonomy.md`](../concept-taxonomy.md).

## 6. Before you publish

Guides are **public brand copy**. Treat them accordingly:

1. **Draft, then get a voice sign-off** before committing the first article in a new style or batch.
   (Once the voice is signed off, the rest of a batch can follow it.)
2. **Verify mechanically:** `cd backend && ../.venv/bin/python -m pytest tests/test_guides.py -q` (green)
   and `../.venv/bin/python scripts/validate_content.py` (passes). Spot-check each file: word count in
   range, `grep -c "[—–]"` returns 0, description ≤160, slug == filename.
3. **Publishing is outward-facing.** Landing on `origin/main` makes the article live, crawlable, and in
   the sitemap. Get an explicit go-ahead before pushing.

---

## Quick checklist (per article)

- [ ] Written as the right **senior persona** for the subject
- [ ] Reasoning-premium; useful and original; no hype, no anti-competitor, no volume-as-value
- [ ] Passes the **anti-AI smell test** (rhythm varied, specifics present, no banned register)
- [ ] Targets one role+intent query; title leads with it
- [ ] 900–1,400 words
- [ ] Frontmatter: title without brand suffix, description ≤160, slug == filename, `draft: false`
- [ ] **Zero em-dashes / en-dashes** anywhere
- [ ] Internal links to `/interview-prep/<role>` + `/sample/<track>`, woven in softly
- [ ] `test_guides.py` green, `validate_content.py` passes
- [ ] Voice sign-off + explicit go-ahead before publishing
