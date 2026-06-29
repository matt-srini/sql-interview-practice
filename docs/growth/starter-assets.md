# Starter Assets (appendix)

Appendix to [`gtm-strategy.md`](gtm-strategy.md) (the canonical GTM SoT). The actionable kit: example
posts in the datathink voice, the subreddit target list + each sub's self-promo rule, the launch-day
checklist, the brand-handle claim list, and a day-by-day first-two-weeks plan. Edit freely.

> **Voice reminder.** datathink is pro-reasoning, never anti-competitor. Confident, calm, specific.
> We show the *why* behind an answer; we never hype, never engagement-bait, never claim volume as
> value. All example posts below are **original drafts** — adapt, don't paste blind.
>
> **Hook source.** For more "can you solve this?" / reasoning-teardown seeds, mine
> [`../concept-hooks.md`](../concept-hooks.md) — a per-track Socratic-hook inventory whose Mock-Only
> section was authored explicitly for "social media posts, ad copy, and email sequences." Each hook is
> a concept framed as a reasoning tension: a drop-in post seed. (Never lift a gated mock-only
> question's content into a public post — the hook is the *tension*, not the answer.)

---

## A. Example posts (10, in the datathink voice)

### LinkedIn — carousel anchor (caption + slide skeleton)

**Caption:**
> Most candidates can write a window function. Far fewer can explain why the `PARTITION BY` is what
> it is — and that gap is exactly where interviews are won or lost.
>
> Here's the same question two ways: the answer that *passes the test case*, and the answer that
> *survives the follow-up question*. 👇
>
> (The full track runs on a real engine — you can try a sample, no login: [link to /sample/sql])

**Slides:** 1) The question (a realistic running-total ask). 2) The naive answer + "this passes."
3) The follow-up the interviewer actually asks. 4) Why the naive partition breaks. 5–9) The reasoned
build, one decision per slide. 10) The principle + soft CTA ("Train the reasoning, not the template").

### LinkedIn — "recognition ≠ reasoning" story post (text)

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

### LinkedIn — role-prep post (text)

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
> streaks. 9 tracks (SQL, Python, pandas, PySpark, stats, ML, and more), with a free no-login sample
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
| LinkedIn (founder personal) | (founder profile) | — | the primary channel; keep bio → datathink.co |
| X / Twitter | `@datathinkHQ` | live | ✓ in `sameAs` |
| Reddit | `u/datathink` (or founder handle, disclosed) | claim | n/a (profile, not sameAs) |
| YouTube | `@datathink` | claim | add to sameAs when active |
| Product Hunt | `datathink` (maker + product) | claim pre-launch | n/a |
| Hacker News | founder account (age + karma) | seed early | n/a |
| Newsletter (LinkedIn + email) | "datathink weekly" | set up | n/a |
| GitHub | (private — intentionally omitted from sameAs) | — | ✗ (per seo.md) |
| Instagram (optional) | `@datathink` | defensive claim | optional |
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
