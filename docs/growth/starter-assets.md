# Starter Assets (appendix)

Appendix to [`gtm-strategy.md`](gtm-strategy.md) (the canonical GTM SoT). The actionable kit: example
posts in the datathink voice, the subreddit target list + each sub's self-promo rule, the launch-day
checklist, the brand-handle claim list, and a day-by-day first-two-weeks plan. Edit freely.

> **Voice reminder.** Write like a thoughtful senior data practitioner: calm, precise, curious,
> generous, and quietly opinionated. Demonstrate the reasoning thesis through concrete problems more
> often than naming it. We show the *why* behind an answer; we never hype, engagement-bait, invent
> candidate statistics, or claim volume as value. Vary the ending rather than attaching a slogan and
> product link to every cut. Aim for warm at the edges and calm in the middle: meet the reader in the
> difficulty in the opener and close, keep the teaching precise, stay empathetic without tipping into
> saccharine coaching, and use the real terms (grain, fan-out, shuffle, idempotency), defining each
> once. The canonical voice rules are in [`gtm-strategy.md`](gtm-strategy.md)
> § 4. All example posts below are **original drafts** — adapt, don't paste blind.
>
> **Channel model reminder.** LinkedIn example posts below are written as **company-page posts** — the
> brand speaks, not the founder's personal voice. The founder reshares each company post within ~60
> minutes. Reddit posts are written as a **disclosed human** (the founder, by name, with affiliation
> stated) — never as a brand account or undisclosed fellow user.
>
> **Hook source.** For more "can you solve this?" / reasoning-teardown seeds, mine
> [`../concept-hooks.md`](../concept-hooks.md) — a per-track Socratic-hook inventory whose Mock-Only
> section was authored explicitly for "social media posts, ad copy, and email sequences." Each hook is
> a concept framed as a reasoning tension: a drop-in post seed. (Never lift a gated mock-only
> question's content into a public post — the hook is the *tension*, not the answer.)

---

## Infographic asset kit

The generated working assets live under the gitignored
`docs/growth/assets/infographics/` directory. Keep LinkedIn single-image masters and PDF documents
in `linkedin/`; keep each topic's ordered square PNGs in `instagram/<slug>/`. The exact dimensions,
naming, three-page story shape, PDF reuse rule, and canonical logo requirement live in
[`gtm-strategy.md`](gtm-strategy.md) § 3.1 and are not duplicated here.

### Visual design system (canonical — pixel-sampled from shipped assets, 2026-08)

Nothing below was written down before week 3; it was reverse-engineered from the week-01/02 PNGs
under time pressure and got the theme wrong on the first pass (built dark, should be light — see
[`DECISIONS.md`](../decisions/DECISIONS.md)). This is now the single source — don't re-derive it from
adjacent brand assets like `x-banner.svg` or `linkedin-banner.svg`; those are a **different, dark**
system (profile banners), not this one.

**Palette** — light "Forest & Ink" cream ground, not the dark banner theme:

| Role | Hex | Use |
|---|---|---|
| Background | `#FDFCF8` | canvas |
| Navy | `#001028` | headlines, strong text |
| Body text | `#23293A` / `#3A4152` | primary / secondary copy |
| Muted | `#7A8296` | captions, kickers, page counter |
| Neutral border | `#D8D4C8` | plain card borders |
| Green (good/correct/CTA) | `#4E9F58` border/title · `#337A3B` CTA icon fill | "this works" framing |
| Red (bad/problem) | `#C93A22` | "this breaks" framing — deepened from a brighter sample for legibility on cream |
| Blue (tip/nav/kicker) | `#0050E0` | tip-bar icon, nav-cue links, top-right kicker |
| Purple (explanation) | `#6B21A8` | "why it happens" panel |
| Editor dark bg | `#0B1220` | code-block mockup |
| Editor text | `#E8EDF5` fg · `#A8B3C7` identifiers · `#7CA6FF` keywords · `#6EE7A0` highlighted token |
| Traffic lights | `#F0564A` / `#F5C147` / `#62C370` | code-window dots |

**Fonts** (Google Fonts; all but Anton/Kalam already match product tokens): **Anton** (condensed
poster headlines, two-tone per page — navy + one accent), **Inter** 400–800 (body, matches
`--font-sans`), **JetBrains Mono** 400–700 (code/stats, matches `--font-mono`), **Kalam** 700
(hand-drawn annotation captions only).

**Component library** (reuse these; don't invent new ones per week):
- **Header** — inline lockup SVG top-left, literal markup from
  `frontend/public/branding/lockup-bar-no-bg.svg` (never redraw/approximate). Page 1 only: blue
  uppercase kicker + 5×2 dot-grid top-right. Pages 2–3: plain `N / 3` page-counter top-right instead.
- **Code editor mockup** — rounded dark card, title bar with 3 traffic-light dots + mono filename,
  syntax-tinted body (keywords blue, the pivotal method/token green, rest near-white).
- **Comparison cards** (paired, color-bordered green/red) — **always preceded by an explicit
  shared-axis kicker label stating what's being compared** (e.g. "Rows in the data this code runs
  against:"). Two numbers with different-sounding captions and no shared label reads as two unrelated
  facts, not a comparison — this shipped wrong on the week-3 first draft and was corrected. When one
  side is the recommended choice, tag it "Preferred" (green tick) opposite "Avoid here" on the other —
  don't rely on border color alone to carry the verdict.
- **"Why it happens" panel** — purple-bordered card, purple circle icon, bold title, body with one
  bold purple key term, optional 2-row mini pill-comparison underneath.
- **Tip bar** — thin blue-bordered pill card, blue circle icon (lightbulb), one line with a bold blue
  emphasis phrase.
- **CTA bar** (final page only) — green-bordered card, green circle icon (arrow), text + solid green
  pill containing the bare URL.
- **Checklist box** — neutral-bordered card, dark circle icon, bold title, row of color-rotating pill
  tags (green/blue/purple/orange).
- **Hand-drawn annotation** — Kalam caption + a custom curved SVG arrow. The curve must **scoop
  toward** what it's pointing at (concave relative to the target), not bow away from it (convex) — got
  this backwards on the week-3 first draft; the fix mirrors the control points to the opposite side of
  the chord.
- **Footer nav cue** (pages 1–2 only, bottom-center) — bold colored "See X →" pointing to the next page.

### Render & export pipeline

No repo tooling renders these (deliberately — they're gitignored drafts, not app assets); rebuild this
each time with Playwright, the same engine `frontend/scripts/render-brand-assets.mjs` uses for brand
PNGs:
1. Author each page as a standalone HTML file at its logical CSS size: square pages `1080×1080`, the
   LinkedIn 4:5 master `1080×1350`.
2. Render square/carousel pages with Playwright Chromium at `deviceScaleFactor: 2` (→ `2160×2160`
   physical px). Render the 4:5 master at `deviceScaleFactor: 1` (→ native `1080×1350` — LinkedIn's own
   accepted max photo width per § 3.1; there's no PDF-softening pipeline on a direct image upload, so
   2x buys nothing there).
3. Assemble the 3 square PNGs into `<slug>-carousel.pdf` with Pillow: JPEG-encode each page at
   `quality=92`, save with `resolution=192.0`. That yields clean `11.25in × 11.25in` PDF pages
   (`2160px ÷ 192dpi`) — this is the fix for the "looks soft in LinkedIn's document editor" issue;
   don't re-render at a different resolution chasing softness, the recipe is correct.
4. Place files per the § 3.1 contract, `sips -g pixelWidth -g pixelHeight` to confirm dimensions, then
   delete the scratch render script/HTML — nothing in this pipeline is meant to persist in the repo.

### Current starter topics

- `sql-execution-order`: the written-vs-logical SQL order, why the order matters, and the
  FROM/JOIN → WHERE → GROUP BY → HAVING → WINDOW → SELECT → DISTINCT → ORDER BY → LIMIT/OFFSET flow.
  When the nine steps are split over three rows, the arrows must remain a continuous serpentine:
  1→2→3, down to 4, 4→5→6 right-to-left, down to 7, then 7→8→9 left-to-right.
- `week-01-running-total`: the hidden default window frame, the tied-date failure mode, and the
  deterministic two-part fix.
- `week-02-data-engineer-interview-map`: the interview-loop map, its first three reasoning surfaces,
  and the cost/rerun judgment surface.
- `week-03-pandas-vectorization`: the correct-on-a-sample row-wise answer, the one-Python-callback-
  per-row mechanism, and the vectorized rewrite. Use callback counts to make scale concrete; do not
  publish universal wall-time benchmarks because hardware, data, and environment change them.

For every topic, keep only the production master, the production PDF, and the ordered Instagram
pages. Do not retain incorrect-logo renders or alternate drafts beside the final exports.

---

## A. Example posts (10, in the datathink voice)

### LinkedIn — carousel anchor (company page; caption + slide skeleton)

**Caption:**
> Most candidates can write a window function. Far fewer can explain why the `PARTITION BY` is what
> it is — and that gap is exactly where interviews are won or lost.
>
> Here's the same question two ways: the answer that *passes the test case*, and the answer that
> *survives the follow-up question*. 👇
>
> (The full track runs on a real engine — you can try a sample, no login: [link to /sample/sql])

**Deep-carousel slides:** 1) The question (a realistic running-total ask). 2) The naive answer +
"this passes." 3) The follow-up the interviewer actually asks. 4) Why the naive partition breaks.
5–9) The reasoned build, one decision per slide. 10) The principle + soft CTA ("Train the reasoning,
not the template"). For the compact infographic variant, compress this to three earned pages using
the contract above; do not squeeze ten pages of copy into three.

### LinkedIn — "recognition ≠ reasoning" story post (company page; text)

> Two candidates, same question.
>
> The first had seen it before. He typed the template from memory — correct, fast. Then the
> interviewer changed one word in the prompt, and he froze. The template didn't fit anymore, and he
> never understood *why* it worked in the first place.
>
> The second was slower. But she'd practiced the *reasoning*: why you partition where you do, what the
> frame clause is actually doing. When the prompt changed, she adjusted in ten seconds.
>
> Guess who got the offer.
>
> Memorizing answers gets you through the easy questions and abandons you at the hard ones. That's the
> whole reason we built datathink around reasoning instead of recall.
>
> What's a question that *looked* familiar in an interview and then wasn't? 👇

### LinkedIn — role-prep post (company page; text)

> If you're prepping for a Data Engineer interview the way you'd prep for a Data Analyst one, you're
> studying the wrong things.
>
> A DE loop actually spans five distinct reasoning surfaces: SQL, Python, PySpark, data engineering
> systems, and data modeling. Each tests a different kind of judgment. Studying "SQL questions"
> alone leaves four of them cold.
>
> We mapped each of the four data roles to the tracks the interview really covers. The Data Engineer
> breakdown: [link to /interview-prep/data-engineer]

### X — "can you solve this?" thread

> 1/ Quick one for the SQL folks. You have a `sessions` table. Find each user's *second* session by
> start time. Sounds trivial. It's where ~half of candidates write a subtly wrong query. Can you?
>
> 2/ The trap: `LIMIT`/`OFFSET` after an `ORDER BY` gives you the global second row, not the second
> *per user*. You need a per-user ranking. Why? Because "second" is defined *within* each user.
>
> 3/ The reasoning that holds up: `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY started_at)`,
> then filter `= 2`. The partition is the whole answer — it's what makes "second" mean per-user.
>
> 4/ If you want to actually run this on a real engine (DuckDB, no login, no signup wall): [/sample/sql]
> Reasoning > recall. That's the whole idea.

### X — build-in-public thread

> 1/ Building datathink in public. The thesis: the data-interview-prep market is a grind — thousands
> of near-duplicate questions, synthetic data, streaks. We're betting on the opposite: depth, real
> execution engines, and training the reasoning that actually compounds in the job.
>
> 2/ This week: shipped the readiness benchmark, fixed the funnel instrumentation, wrote 3 reasoning
> teardowns. Hardest part isn't the code — it's resisting the urge to add a streak counter. (We won't.)
>
> 3/ Numbers, honestly: [real metric]. Small. Growing. If you're prepping for a data role, try a free
> sample and tell me where the reasoning is unclear — that's the most useful thing you can do: [/sample]

### X — single hook tweet

> "Looks right" and "is right" are different queries.
>
> That's why datathink runs your SQL on a real engine instead of checking it against a string. The job
> is the second one.

### Reddit — value comment (NO link; the default mode for weeks 1–6)

> (In reply to "how do I actually get better at SQL interviews, not just memorize?")
>
> The thing that moved the needle for me was stopping at "it passed" and asking "*why* does this
> work, and where would it break?" Concretely, for window-function questions: don't memorize the
> template — be able to say out loud what the `PARTITION BY` is doing and what changes if you remove
> it. Interviewers almost always follow up by tweaking the prompt, and if you only pattern-matched the
> template you'll freeze. Practice rephrasing your own questions and re-solving. Boring, but it's the
> difference between recognition and reasoning.

### Reddit — earned resource post (only where rules allow, after value threshold)

> (In r/developersIndia Monthly Showcase Sunday — affiliation disclosed)
>
> I built datathink — data-interview practice that runs on real engines (DuckDB for SQL, a real Python
> sandbox) and focuses on the *reasoning* behind answers rather than volume. Full disclosure: I'm the
> maker. There's a free sample set with no login if you want to judge it without signing up: [/sample].
> Genuinely keen on feedback from folks here on whether the reasoning explanations are clear — that's
> the part I most want to get right.

### Newsletter — weekly issue skeleton

> **Subject:** The "second per user" trap (and the reasoning that beats it)
>
> **This week's reasoning breakdown** (60%): [the pillar teardown, plain-language].
> **New on datathink** (30%): [new questions / feature].
> **Behind the scenes** (10%): [one honest build note].
> **Footer:** Forward this to one person prepping for a data interview.

### Show HN — submission

> **Title:** Show HN: datathink – data interview practice on real engines (DuckDB + Python sandbox)
>
> **Body:** I got tired of interview-prep sites that check your SQL against a string and call it
> "correct." datathink runs your query on a real DuckDB engine and your Python in a real sandbox, and
> the questions are built around the *reasoning* a data professional actually uses — not volume or
> streaks. 10 tracks (SQL, Python, pandas, PySpark, stats, ML, and more), with a free no-login sample
> set so you can judge it without an account: [/sample]. It's a bootstrapped solo project; happy to go
> deep on the sandbox hardening, the grading determinism, or the curriculum design in the comments.

---

## B. Subreddit targets + self-promo rules

> **Hard rule (all subs): value before promotion.** Reddit retired the formal "90/10 rule," but the
> surviving spam policy is blunt: *if your only activity is sharing your own links, it's spam
> regardless of quality.* The practiced norm in these communities is ~20 genuine contributions per
> self-mention. **Weeks 1–6: participate, do not link.** Establish ~4–6 weeks of real karma in a sub
> before any resource mention, disclose affiliation, and prefer megathreads.
>
> **Research caveat:** exact sidebar rule text is not publicly scrapable for most of these subs;
> entries marked *(inferred)* are from behavioral/culture analysis, not quoted rules. Re-read each
> sub's actual rules in-app before your first post.

| Subreddit | ~Size | Self-promo posture | Cleanest entry point |
|---|---|---|---|
| **r/dataengineering** | ~463k | Brand-skeptical; cold promo removed *(inferred)* | Career/Help flair answers; become a known participant first |
| **r/datascience** | ~2.8M | Large, bot-heavy moderation; on-topic from real participants survives *(inferred)* | Substantive career/technical answers; no cold promo |
| **r/analytics** | ~273k | Practitioner-oriented; "no spam" operative *(inferred)* | Question/Discussion-framed value posts |
| **r/SQL** | ~283k | Technical, help-oriented; resource posts survive if framed as free community resource *(inferred)* | Answer DB-specific Qs; "I built this free practice set" framing later |
| **r/learnSQL** | <50k (est.) | Learning sub — more tolerant of free resources *(inferred)* | Free, no-paywall resource framed pedagogically |
| **r/learnpython** | ~1.0M | **Most promo-tolerant data point found** — a free guide post was indexed and survived | Genuinely pedagogical free resource; wiki/FAQ culture |
| **r/dataanalysis** | ~220k | **Verified rules:** "do not spam," "no social media links," "no URL shorteners"; redirects careers to r/DataAnalysisCareers | "Rate my dashboard"-style project posts (confirmed to land) |
| **r/cscareerquestions** | ~2.4M | High cynicism toward tools; promo culturally risky *(inferred)*; has a weekly/simple-questions thread | Help job-seekers with zero commercial angle |
| **r/DataScienceJobs** | ~15k | Small, career-focused, less bot enforcement; career-relevant resources may be welcome *(inferred)* | Career-relevant help; resource if directly useful |
| **r/BusinessIntelligence** | ~74k | **Verified weekly thread:** "Entering & Transitioning into a BI career" (Mondays) — cleanest low-risk resource slot found | The Monday transitioning thread |
| **r/developersIndia** | ~1.6M | **Verified recurring:** "Monthly Showcase Sundays" — explicitly for sharing projects/tools | Monthly Showcase Sunday (the India entry point) |

**Low / no fit (confirmed):** r/dataisbeautiful (visualization-only; product promo removed),
r/india (political, no fit), r/IndianStreetBets (finance/meme, no fit). No meaningful dedicated India
data-science sub exists; r/developersIndia is the India channel.

**The founder participation pathway that works (cross-source):**
1. Build karma via genuine helpful answers (4–6 weeks, 20+ comments) in the target sub.
2. Use megathreads where they exist (r/BusinessIntelligence Mon; r/developersIndia Monthly Showcase).
3. Frame as a community contribution ("I built this free thing, here's the first problem"), not a launch.
4. Disclose affiliation explicitly.
5. Lean on the no-login Sample Hub so there's no signup wall to resent.

---

## C. Brand-handle claim list (feeds SEO `sameAs` / disambiguation)

Claim consistently (same name, bio, `BrandMark` avatar, link to datathink.co). Each live, active
profile becomes a `sameAs` entry in the homepage Organization JSON-LD — wire it in `spa.py` as it goes
live (see [`gtm-strategy.md`](gtm-strategy.md) M1/M2 and [`../seo.md`](../seo.md) § Structured data).

| Channel | Handle | Status | sameAs? |
|---|---|---|---|
| LinkedIn (company) | `company/datathink-co` | live | ✓ in `sameAs` |
| LinkedIn (founder personal) | (founder profile) | — | amplification layer — reshares company posts; keep bio → datathink.co |
| X / Twitter | `@datathinkHQ` | live | ✓ in `sameAs` |
| Reddit | `u/datathinkHQ` (founder account, disclosed) | live | n/a (profile, not sameAs) |
| YouTube | `@datathinkHQ` | live | ✓ in `sameAs` |
| Product Hunt | `datathink` (maker + product) | claim pre-launch | n/a |
| Hacker News | founder account (age + karma) | seed early | n/a |
| Newsletter (LinkedIn + email) | "datathink weekly" | set up | n/a |
| GitHub | (private — intentionally omitted from sameAs) | — | ✗ (per seo.md) |
| Instagram | `@datathinkhq` | live | ✓ in `sameAs` |
| TikTok (optional) | `@datathink` | defensive claim | optional |

**Defensive claiming matters:** on a contested brand, claiming a handle you won't actively use still
prevents impostor capture (recall seo.md's warning never to point `sameAs` at impostor "DataThink"
profiles).

---

## D. Launch-day checklist (Product Hunt + Show HN)

**T-30 days:** Maker profiles complete with real activity history; seed HN karma (250+) via genuine
technical comments; PH followers warmed.
**T-14 days:** Gallery images showing the *actual* product workflow finalized (M7); maker comment
drafted (<800 chars, concrete, no hype); Show HN title locked.
**T-7 days:** Full funnel tested under spike load (PH/HN → landing → first sample solve); legal pages
linkable (M6); OG unfurls verified (M3).
**Launch day (PH):** Go live 12:01 AM PT; activate genuine supporters (no coordinated public upvote
asks — penalized); respond to every comment within 10 min for the first 4 hours.
**Launch day (Show HN):** Submit Tue–Thu 8–10 AM PT (or Sun 6–9 PM PT); need ~8–10 genuine upvotes +
2–3 substantive comments in the first 30 min; be honest and specific, expect scrutiny (welcome it).
**Do NOT:** vote rings, public "upvote me" posts, hype superlatives. Both platforms flag/penalize them.
**Measure:** activation rate from launch traffic (sample→solve), not leaderboard rank alone.

---

## E. First-two-weeks day-by-day plan

The concrete on-ramp. Maps to Phase 1 of [`editorial-calendar.md`](editorial-calendar.md). Hold the
Tier-1 floor; everything else is bonus.

**Week 1 — set the foundation + first voice**
- **Mon:** Claim all handles (§ C); set bios + avatar; wire live ones into `sameAs`. Verify Google
  Search Console + submit sitemap (M8). Pick week-1 pillar (reasoning vs. recall).
- **Tue:** Build the PostHog funnel dashboard on the wired events (M9). Write + design the week-1
  carousel; post it AM; reply hard the first hour.
- **Wed:** X build-in-public launch thread ("here's the thesis"). Start daily Reddit value answers in
  r/SQL + r/dataengineering (NO links). Verify sample-link OG unfurls (M3).
- **Thu:** LinkedIn story cut ("recognition ≠ reasoning"). Stand up newsletter capture + 3-email
  welcome sequence. UTM-tag every link you post.
- **Fri:** First SEO pillar drafted (role+intent home of the teardown). 30-min: confirm every funnel
  event fires (sample_submitted → question_solved → plan_upgrade_started).
- **Sat/Sun:** Light Reddit participation; finalize the 30-second pitch (M4) and use it everywhere.

**Week 2 — first hooks + measure**
- **Mon:** Pick week-2 pillar (role-true prep). Reddit value answers in r/learnpython + r/developersIndia.
- **Tue:** Week-2 carousel ("What a DE interview actually spans") → link the role page; post AM, reply 1st hr.
- **Wed:** X "can you solve this?" thread #1 (free sample, no login). Publish SEO pillar #1.
- **Thu:** LinkedIn role-prep text post → /interview-prep/data-engineer.
- **Fri:** First newsletter send (if you have subscribers). Weekly metrics review: WAL, sample→activation.
- **Sat/Sun:** Note which post drove the most sample clicks; double down on that format next week.

After week 2 you're in the steady weekly rhythm (editorial-calendar § Weekly operating rhythm).
Crossing the Reddit value-first threshold (~week 4–6) unlocks the first *earned* resource mention.
