# Go-to-Market & Social / Distribution Strategy

**Canonical source of truth for datathink's go-to-market, social, and distribution strategy.**
This doc owns the *market* side of launch. It is the sibling of the *technical* launch-readiness
work (closed — see [`../../TODO.md`](../../TODO.md) P1 and [`../backlog/session-launch-readiness.md`](../backlog/session-launch-readiness.md))
and it does not re-audit it.

Status: canonical planning spec · Owner: founder / growth · Last updated: 2026-06-29
Appendices: [`editorial-calendar.md`](editorial-calendar.md) (the 3-month calendar + production system)
· [`starter-assets.md`](starter-assets.md) (example posts, subreddit rules, launch-day + first-2-weeks plan).

**SoT siblings — link, never restate their numbers:**
- Positioning & philosophy → [`../specs/platform-north-star.md`](../specs/platform-north-star.md) + `CLAUDE.md` § Platform position
- Pricing, tiers, dual payment rails → [`../features/pricing.md`](../features/pricing.md)
- Organic discovery, role pages, brand disambiguation → [`../seo.md`](../seo.md)
- Role → track mapping → `frontend/src/roleRegistry.js` (the runtime SoT)
- Channel-priority *why* + rejected alternatives → [`../decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-28; brand-led model 2026-06-29)
- Unlock-ladder removal + flat free model → [`../decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-29)

> **This strategy serves the reasoning-premium brand, not vanity growth.** Every tactic below was
> run through the five CLAUDE.md lenses and the nine pushback questions. Where a common "growth"
> tactic conflicts with the positioning, it is named and rejected in § 7 (the do-NOT list), not
> quietly omitted. If a tactic here would embarrass us in a year, it should not be here — flag it.

---

## 0. Why social is strategically load-bearing (not optional)

Two facts from [`../seo.md`](../seo.md) make distribution — especially community and social — a
*primary* growth lever rather than a nice-to-have:

1. **"datathink" is a contested bare-brand query.** `datathink.io` holds a verified Google
   Business Profile → knowledge panel, which structurally outranks a plain organic result. **Meta
   tags alone will not win the brand query.** The levers that *can* win are entity signals
   (Organization JSON-LD + `sameAs`, Search Console, a first-party Business Profile), owning the
   higher-intent **role + intent** queries, and **community/social presence** that Google reads as
   entity corroboration.
2. **Consistent social-handle claiming feeds SEO Phase 3 directly.** Every profile we claim and
   keep active becomes a `sameAs` corroboration signal in the homepage Organization graph (today:
   LinkedIn `company/datathink-co`, X `@datathinkHQ`). Social and SEO are **one program**, not two.

So the social plan in § 3 is also the SEO-Phase-3 disambiguation plan. We treat them as joined
throughout, and we **do not over-index on the bare-brand query** — we win on role + intent +
community + entity signals.

---

## 1. Positioning → Messaging

### The one-line value prop

> **Train the reasoning behind the right answer — not the answer.**

Supporting one-liner (for bios, OG, the 30-second pitch):
> *datathink is data-interview practice on real engines — SQL, Python, pandas, stats, ML and more —
> that trains the judgment a data professional actually uses on the job. Acing the interview is the
> consequence, not the goal.*

This is a distillation of the canonical philosophy in [`../specs/platform-north-star.md`](../specs/platform-north-star.md)
§ The datathink philosophy — **do not rewrite the philosophy here; that doc owns it.**

### The wedge: reasoning vs. grind

The competitive landscape (verified competitor scan, 2026) has a wide-open positioning gap: **every
incumbent talks about "acing the interview."** DataLemur is FAANG-grind-flavored ("Ace the SQL &
Data Science Interview"); StrataScratch is "LeetCode for Data Scientists"; Interview Query is
company-process curation; LeetCode is volume + streaks. **None positions around developing durable
professional judgment.** The reasoning-depth frame is *unclaimed territory in the distribution
language* — which is exactly where a smaller, newer brand should plant its flag, because we win the
argument rather than the volume contest.

One caveat on the wedge: the reasoning-vs-grind *language* is copyable. Any competitor can swap in "judgment" for "patterns" in their tagline. The durable defensibility lives in the **product**: the real DuckDB execution engine, the Python sandbox, the Interview Loop chain mechanics, and curriculum depth that took months to build. The messaging points at that moat; the moat itself is not the messaging.

The wedge is a head-to-head we **welcome and name explicitly**:

| The grind market trains… | datathink trains… |
|---|---|
| Pattern recognition ("I've seen this one") | Reasoning ("I understand *why* this is the answer") |
| Breadth — 1,000s of near-duplicate questions | Depth — fewer questions, each exercising real judgment |
| Synthetic toy data | Real execution engines (DuckDB, real Python sandbox) and realistic datasets |
| Generic "interview questions" | Role-true prep (the 4 roles, the tracks that actually compose each) |
| A streak/leaderboard dopamine loop | Progress that reflects mastery (first-try accuracy, readiness) |

We are **not** anti-competitor in tone — we're pro-reasoning. The narrative is "here's the deeper
skill the grind misses," never "competitor X is bad."

### Messaging pillars (4)

Every piece of content should ladder up to exactly one of these:

1. **Recognition ≠ reasoning.** The candidate who memorized the window-function template freezes when
   the question is phrased sideways. The one who understands *why* the partition is what it is, adapts.
2. **Depth over breadth.** You don't need 2,000 questions. You need the ~30 patterns that recur for
   years in the role, each understood cold.
3. **Real engines, real judgment.** We run your SQL on DuckDB and your Python in a real sandbox —
   because "looks right" and "is right" are different, and the job is the second one.
4. **Role-true prep.** A Data Engineer and a Data Analyst are not preparing for the same interview.
   We map prep to the role you're actually targeting (the 4 roles → their real track stack).

### ICP (who we're for)

Primary: **data professionals and those becoming them**, across the four roles datathink surfaces —
**Data Analyst, Data Engineer, Analytics Engineer, Data Scientist** (mapping: `frontend/src/roleRegistry.js`).
Two states, both in-ICP:

- **Job-seekers** under time pressure (interview-week, layoff, first job, switching roles). High
  intent, high urgency, price-sensitive. The free-sample wedge (§ 5) is for them.
- **Practicing professionals** leveling up (the philosophy's true north: reasoning that compounds in
  the role). Lower urgency, higher willingness to pay for depth, the Pro/Elite buyer.

Two geographies, both first-class (the dual payment rail in [`../features/pricing.md`](../features/pricing.md)
§ Global payments exists precisely because both matter):

- **India** — large, dense, highly engaged data-career audience; INR pricing held deliberately lower
  for home-market price-sensitivity. Channel nuance: LinkedIn (India is the fastest-growing major
  LinkedIn market), `r/developersIndia`, bootcamp partnerships.
- **Global** (US/EU-led) — USD via Paddle (Merchant of Record). Channel nuance: X / Hacker News /
  Product Hunt skew here; the global indie/dev layer lives on X.

### Anti-positioning (what we refuse to be)

Naming the anti-positioning is a brand-protection device — these are the things that, if we drift
into them, quietly convert us into the grind market we're differentiating against:

- **Not** a flashcard / rote-recall bank. (We reject "1,000 SQL questions" as a value claim.)
- **Not** a leaderboard / streak-dopamine product. (Retention via mastery, not via daily-cap tricks.)
- **Not** a "cram the night before" cheat sheet. (Depth takes sessions, and we say so.)
- **Not** a company-question-dump ("the 50 questions Meta asks"). The SQL company filter is a
  practice convenience only, never a tier/marketing lever — see [`../specs/platform-north-star.md`](../specs/platform-north-star.md) § Filter policy.
- **Not** an AI-answer-generator. We train *your* reasoning; we don't do it for you.

---

## 2. Launch readiness — market side (go / no-go checklist)

This is the *market* counterpart to the closed technical checklist. The technical side is **done**
(sandbox, entitlements, payments-under-failure, observability/alerting, deployment/rollback,
legal/compliance, load — all CLOSED, see [`../../TODO.md`](../../TODO.md) P1). Do not re-audit it.

| # | Item | Why it gates launch | Status owner |
|---|---|---|---|
| M1 | **Brand handles claimed on every channel**, consistent name + bio + avatar (`BrandMark`) + link | Feeds SEO `sameAs` / disambiguation ([`../seo.md`](../seo.md) Phase 3); prevents impostor capture | founder |
| M2 | **`sameAs` updated** in the homepage Organization JSON-LD as each handle goes live | The entity-corroboration lever — claiming without wiring it to `sameAs` wastes it | founder + spa.py |
| M3 | **OG / share images** render correctly when a sample/role/track URL is unfurled on LinkedIn, X, Slack. **Infra already exists** — a versioned canonical OG card (`og-image.png?v=N`, server-injected by `spa.py` + Helmet per page) and a light-ground `og-image-light.svg` for email/doc placements (see [`../frontend.md`](../frontend.md) § OG image). This item = *verify* the unfurls + add the per-role OG cards already on the SEO roadmap ([`../seo.md`](../seo.md) Phase 3), not build from zero | founder |
| M4 | **One-liner + 30-second pitch** finalized (§ 1) and used verbatim everywhere | Consistency is an entity signal and a memory aid | founder |
| M5 | **Free-sample Hub (`/sample`) is the single primary CTA** in every bio and most posts | The no-login wedge (§ 5) is the whole top-of-funnel; one CTA, repeated | founder |
| M6 | **Legal / refund pages linkable** (`/privacy`, `/terms`, `/refund-policy`, `/contact`) | Trust + required for Product Hunt / paid traffic; already shipped (sitemap) | done |
| M7 | **Launch asset kit** assembled: logo lockups (reuse `BrandMark` + `og-image-light.svg`), 3–5 product screenshots, a 30–60s screen-capture of solving a sample question, the pitch copy | PH/Show HN/press all need these on day 0 | founder |
| M8 | **Google Search Console verified + sitemap submitted; Google Business Profile created** | The actual SERP-disambiguation levers ([`../seo.md`](../seo.md) Phase 3) — start the recrawl clock early | founder |
| M9 | **PostHog funnel dashboard built** on the wired events (§ 6) before first traffic. `sample_landed` (UTM capture on `/sample` entry) and `account_created` are now wired — the full impression→sample→signup→activation chain is instrumented (see § 6) | You cannot improve a funnel you cannot see; the events already fire | done (wired) |
| M10 | **At least one pillar article published to `/guides`** (the server-rendered content surface, live in sitemap + footer) | The SEO content engine is unblocked — publishing one piece starts the indexing clock; waiting costs weeks of compounding | founder |

**Go/no-go rule:** M1–M5 + M9 are hard gates (don't drive traffic you can't capture, convert, or
measure). M6 is already done; M9 is done (funnel wired). M7–M8 should be done by the Product Hunt /
Show HN moment, not necessarily the soft launch. M10 is a soft launch gate — start the indexing
clock early.

---

## 3. Channel strategy

Ranked by expected ROI **for this product** (reasoning-premium, solo founder part-time, dual
India + global, contested bare brand). The priority call and its rejected alternatives are logged in
[`../decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-28; revised 2026-06-29 — LinkedIn
moved from Tier 1 to Tier 2 on the brand-led model decision; paid-search experiment added).

| Tier | Channels | Role |
|---|---|---|
| **1 — primary, weekly** | SEO / content engine · Product-led free-sample loop · Reddit (community-first, disclosed human) | The durable compounding levers. SEO is now unblocked (the `/guides` surface exists — publish into it). The no-login sample loop is the top-of-funnel wedge. Reddit is wide open to competitors but ban-risk, so strictly value-first. |
| **2 — secondary, weekly-lighter** | LinkedIn (company-published + founder-amplified) · X / Twitter · Newsletter | Brand reach + dev credibility + the owned-audience anchor. LinkedIn company-page reach is structurally lower than a personal-brand channel — honest expectation: steady contributor, not a rocket. |
| **3 — time-boxed / opportunistic** | Launch moment (Product Hunt + Show HN) · India partnerships (bootcamps) · data Discord/Slack communities | One-time spikes + backlinks + relationships, not sustained channels. Discord/Slack require a disclosed human, same as Reddit. |
| **Experiment** | Small time-boxed paid-search validation (§ 3.9) | One-time thermometer: learn the free→paid conversion rate fast. Hard budget cap + kill criterion. Not a sustained channel. |

The **free-sample growth loop (§ 5)** is the connective tissue across all four tiers — every channel's
job is to put a free sample question in front of the right person.

### 3.1 LinkedIn — Tier 2 (company-published + founder-amplified)

**Why it fits (and honest expectations).** The data-career audience for all four roles lives on
LinkedIn, in both India and globally. India is the fastest-growing major LinkedIn market, and the
practical-skill-plus-career-outcome content that performs there is exactly the reasoning-vs-grind
narrative we own. The channel is right; the model is brand-led — not founder-personal-brand-led.

**The model.** The **company page (`company/datathink-co`) is the primary publisher.** The founder's
personal profile is an **amplification layer**: reshare each company post within the first ~60
minutes to seed distribution (the first-hour engagement signal matters for reach), and occasionally
add a first-person note on a post. No cultivated founder personality, no daily personal cadence.

**Honest reach expectation.** The proven competitor playbook in this space is founder-personal-brand-
led: DataLemur's Nick Singh built a 160K+ follower "Top Voice" moat and used it as the primary
acquisition engine. StrataScratch, which leaned on a company page instead, has far less reach.
Company-page reach is *structurally lower* than a personal-brand channel — the feed allocation
differs. We are not going to replicate the DataLemur rocket on this model. The realistic comparable
is StrataScratch: a steady, growing contributor-presence that builds brand recognition and entity
signals, not a flywheel of personal viral posts. That is the honest expectation, and it is enough —
the brand advantage is that it compounds without being a single person's identity.

**Content angle / format.** The 2026 algorithm rewards *dwell time* ("Depth Score"), and the formats
that win are **native document/PDF carousels** (highest engagement of any format) and **multi-image
carousels** — both mechanically reward swiping/reading. Our reasoning content is a natural fit: an
8–12 slide carousel that poses a problem, walks the *reasoning* (not just the syntax), and lands on
the insight + a soft CTA to the matching free sample track.

Post archetypes (rotate; all ladder to a § 1 pillar):
- **"Reasoning teardown" carousel** — a real question, then *why* the naive answer fails and the
  reasoned answer holds. (Pillar 1.)
- **"Recognition ≠ reasoning" story post** — a short narrative: the candidate who memorized vs. the
  one who understood. Text-only, designed to provoke comments. (Pillar 1.)
- **"Can you solve this?" hook** — post a sample question, ask for answers in comments, reply to
  every comment within the first hour (comments drive dwell-time distribution). Link the full sample
  track. (Pillar 2/4.)
- **Role-prep post** — "What a Data Engineer interview *actually* tests vs. what people study,"
  pointing at the `/interview-prep/data-engineer` role page. (Pillar 4.)
- **Build-in-public milestone** — honest numbers, what shipped, what we learned. (Brand/trust.)

**Cadence (solo, part-time).** One deep carousel per week is the anchor (one deep post reliably
beats five thin ones under the new algorithm). Add 1–2 lighter text/image posts (a puzzle, a hook).
Post Tue–Thu mornings; reply to comments hard in the first 60 minutes (decisive for distribution).
The founder reshares each company post promptly after it goes live.

**Risk / rules.** No engagement-bait ("comment 'SQL' and I'll DM you the link" mechanics are a
DataLemur staple we **reject** — see § 7; they juice a vanity comment count and train the audience to
transact, not think). No follower-buying.

### 3.2 SEO / content engine — Tier 1, the durable compounding lever

**Why it fits.** It's the only honest path to winning search on a contested brand: we can't take the
bare-brand knowledge panel with meta tags, but we *can* own **role + intent** queries (per
[`../seo.md`](../seo.md) § Brand disambiguation). The role pages already exist as **campaign landing
targets** (`/interview-prep/<role>`), the per-track pages target "`<Track>` Interview Questions," and
the sitemap is self-maintaining. Content compounds — a good role-prep article keeps acquiring for
years, unlike a post that decays in 48 hours.

**The content home now exists — ship into it.** The server-rendered `/guides` surface is live:
crawlable HTML, in the sitemap, linked from the site footer. Publishing a pillar article = dropping a
markdown file into `backend/content/guides/`. The content engine is unblocked — this item moves from
"we must build a home" to "we have a home, publish." (Role/FAQ page-body prerendering was
deliberately deferred — Google renders their JS and the role pages already ship server-side meta +
JSON-LD.)

**Content angle.** Every content-engine pillar piece (§ 4) gets a long-form home at `/guides` that
targets a role+intent query and **internally links to the matching role page and free sample track**.
The competitor SEO playbook to beat is the "company-specific question page" (DataLemur/StrataScratch
rank well on "<Company> SQL interview questions") — we **don't** copy the company-dump angle (it's the
grind frame we reject); we win the **role + reasoning** angle they've left open ("how to *think
through* a Data Engineer SQL round," not "the 8 questions Company X asks").

**Cadence.** One long-form pillar piece every 1–2 weeks, repurposed into the social cuts (§ 4). This
is the same content as the social engine, given a permanent, indexable home — not separate work.

**Risk / rules.** No thin/AI-spun pages (they erode the entity quality we're trying to build). No
keyword-stuffing. Honor the SEO conventions in [`../seo.md`](../seo.md) (no em-dashes in SEO strings,
pipe separator, role pages as the landing targets). Pair with M8 (Search Console + Business Profile)
— content without the entity signals won't outrank an established knowledge panel.

### 3.3 Reddit — Tier 1, highest reach, highest self-promo risk

**Why it fits.** The exact ICP debates *which platform to use* in `r/dataengineering`,
`r/datascience`, `r/SQL`, `r/learnSQL`, `r/analytics`, `r/cscareerquestions`, and
`r/developersIndia` — and **no competitor runs a real community presence there** (DataLemur merely
*monitors* mentions and screenshots them to LinkedIn). It's wide-open, and Reddit posts rank in
Google (entity signal bonus). But it is the **single highest-ban-risk channel** — the wrong move
gets the account and the brand blacklisted.

**The non-negotiable operating rule: value before promotion, ~20:1.** Every community studied
enforces a value-first gate (the sitewide guideline is the "10% rule" — no more than ~1 in 10 of
your posts/comments may be your own content; the practiced norm in these subs is stricter, ~20
genuinely helpful contributions per 1 self-mention). Concretely, for the first 4–6 weeks we **do not
link datathink at all** — we become the person who writes the clearest answer to "how do I prepare
for a DE SQL round" and posts genuinely useful reasoning breakdowns. The product surfaces *naturally*
and only where rules permit (a weekly careers/resources megathread, a direct "what tool should I
use" question, an author flair/profile rather than a link drop).

**Content angle.** Answer real questions with real reasoning (this *is* the brand). Where a sub
permits it, share a **free, no-login sample** as a resource, not a pitch — the no-login Sample Hub is
purpose-built for this (no signup wall to resent). Post the reasoning-teardown content as a genuine
discussion ("here's how I think about X — how do you?"), not an ad.

**Cadence.** Daily-ish lightweight participation (comments/answers); a substantive original post only
when it genuinely adds value (≈ weekly), and a resource mention only where the sub's rules explicitly
allow it. Per-subreddit rules are catalogued in [`starter-assets.md`](starter-assets.md) § Subreddit
targets — **read each sub's rules before posting; they differ sharply.**

**Disclosed human, not a faceless brand.** Brand-as-face works for broadcast surfaces (company
LinkedIn, X, the site, newsletter), but Reddit requires a **real, disclosed human** — never a
faceless brand account, and never an undisclosed "fellow user" who happens to recommend the product.
The founder's account (or another named human) is the Reddit presence, with affiliation disclosed
every time a resource mention is made. The same applies to data Discord/Slack (§ 3.8).

**Risk / rules.** Read the rules of every sub before first post. Never astroturf (no fake "has anyone
tried datathink?" threads — that's the exact tactic § 7 rejects and the fastest way to get banned).
One account, real history, real participation. Assume mods can see your full post history.

### 3.4 X / Twitter — Tier 2 (dev credibility + global layer)

**Why it fits.** Best channel for the **global indie/dev/build-in-public layer** and for engaging
influencers in the data community; feeds the `@datathinkHQ` `sameAs` signal. The "can you solve
this?" sample-question format is native here. Caveat: X's *India data job-seeker* audience is thinner
than LinkedIn's, so X is for dev credibility + reach + relationships more than direct India
acquisition.

**Content angle / format.** (a) **"Can you solve this?" sample-question threads** — problem in the
hook tweet, the *reasoning* in the thread, the free sample link at the end (X now boosts external
links again, and threads drive 60% more profile visits than single tweets). (b) **Build-in-public**
weekly thread — real numbers, what shipped, what failed; authenticity converts. (c) **Substantive
replies** to 10–15 data/SQL/Python accounts (the "reply-guy" reach strategy: add value in others'
threads before posting your own). First 30 minutes of engagement decide reach.

**Cadence (solo, part-time).** 1 original thread + 3–4 substantive replies per day is the realistic
high-performer floor; if that's too much, 3 threads/week + daily replies. Expect slow follower growth
(hundreds, not thousands, in the first quarter) — that's normal and fine; X is a credibility/relationship
channel for us, not a volume channel.

**Risk / rules.** No follower-buying, no pod/ring engagement-gaming, no rage-bait. Build-in-public
honesty norms apply — share real numbers or don't post the metric.

### 3.5 Newsletter — Tier 2, the owned-audience anchor

**Why it fits.** It's the one asset we own outright (no algorithm between us and the reader), and it
compounds. Every other channel should feed it. DataLemur's 44K-subscriber list is a core moat;
StrataScratch's content list drove sustained acquisition. **Start capturing from day one** even
though it scales last.

**Content angle / cadence.** One useful email per week, same day/time. Mix ≈ 60% educational (a
reasoning breakdown / "common mistake"), 30% product (new questions, features), 10% behind-the-scenes.
The **welcome sequence matters more than cadence** — the first 3 emails after signup set retention;
make them educational, not onboarding. Capture point: the in-product solved-question / unlock flow
("Get the weekly reasoning breakdown") and every social bio. Consider a parallel **LinkedIn
newsletter** (it gets surfaced + notified in-feed) as an amplifier, not a replacement.

**Risk / rules.** Respect the cookie-consent / PII posture already shipped (opt-in; PostHog gated
until Accept — see [`../../TODO.md`](../../TODO.md) launch-readiness). No buying lists. Every footer:
"Forward this to one person prepping for a data interview" (referral beats mechanics at small scale).

### 3.6 Launch moment — Product Hunt + Show HN — Tier 3, time-boxed

**Why it fits.** A one-time spike of qualified traffic + durable backlinks/entity signals (helps M8
disambiguation), not a sustained channel. Realistic outcomes: a strong **Product Hunt** finish ≈
500–2,000 visitors / 50–300 signups in a day; a front-page **Show HN** ≈ 20k–80k visits in 24h
(highly technical, global, early-adopter — excellent for a dev tool). Both compound across repeat
launches.

**Content angle.** PH: gallery images showing the *actual* product workflow (devs scan images first),
a concrete maker comment, full funnel tested under spike load. Show HN: honest, specific, no hype —
title like `Show HN: datathink – data interview practice on real engines (DuckDB + Python sandbox)`,
lead with what's genuinely novel (real execution + reasoning depth, not synthetic toy data), and be
transparent about what it is and isn't (HN punishes hype reflexively).

**Cadence.** Once at launch (after soft launch + a few weeks of community value-building so there's
real signal), then opportunistically re-launch on feature milestones. **Prep, don't wing it** —
checklist in [`starter-assets.md`](starter-assets.md) § Launch-day.

**Risk / rules.** No vote rings, no public "upvote me" asks (both PH and HN penalize/flag them).
Seed HN karma with genuine technical comments for weeks beforehand. These are honesty-gated
communities; the reasoning-premium brand should *want* the scrutiny.

### 3.7 India partnerships (bootcamps / colleges / creators) — Tier 3

**Why it fits.** India's data-bootcamp + early-career TAM is large, the INR price points are tuned for
it, and a bootcamp cohort is a captive, high-intent audience (StrataScratch's first users were
literally a professor's students). Higher effort + sales cycle, so Tier 3 — but outsized if it lands.

**Content angle.** Offer cohorts free Pro access for a term (the admin operator-grant tooling already
exists — `POST /api/admin/grant-plan`, see [`../features/pricing.md`](../features/pricing.md) § Admin
operator grants — so this is operationally trivial, no coupon system needed). Co-branded role-prep
content with creators in the India data-career niche.

**Risk / rules.** Real partnerships only (genuine cohort fit), not logo-collecting. Don't discount the
core product into the grind-market floor; partner on *access*, not on price erosion.

### 3.8 Data Discord / Slack communities — Tier 3

**Why it fits.** Relationship-building with practitioners (DataTalks.Club ≈ 80K Slack members;
MLOps Community ≈ 28K). Same 20:1 value-first norm as Reddit. Same disclosed-human rule (§ 3.3): a
real, named participant who discloses affiliation when the product comes up — never a brand account.
Slow, supporting role — a place to be genuinely helpful and let the brand surface, not a volume channel.

### 3.9 Paid-search validation experiment — one-time thermometer

**What it is.** A single, time-boxed validation experiment — not a sustained channel. ~$300–500 over
~2 weeks, on high-intent queries (e.g. "data engineer interview prep," "SQL interview practice") that
point at `/sample`. Measured through the already-wired funnel: `sample_landed` (UTM) →
`account_created` → `plan_upgraded`.

**Purpose: learn the free→paid conversion rate fast.** The all-organic plan won't yield a
trustworthy free→paid number for months. A small paid experiment gives a directional read within
weeks — is the conversion rate 0.5% or 3%? That number determines whether organic-only is viable
or whether paid deserves a real budget. This is a thermometer, not a faucet.

**Hard constraints.** Budget cap: $500, non-negotiable. Kill criterion: if cost-per-`account_created`
exceeds a 3× target CAC after 7 days, pause immediately. Interpret cautiously — paid-traffic intent
and organic intent differ; this is a signal, not a plan.

**When.** Run after the funnel is verified (M9 + `sample_landed` confirmed firing) and after the
soft-launch SEO/community phase gives a baseline organic conversion rate to compare against.

### 3.10 Short-form video (YouTube Shorts) — defer / repurpose only

**Why deferred.** Highest production cost per output for a solo founder; ROI is acquisition-only (no
meaningful revenue). **Do not build a video-first strategy at launch.** The *only* sustainable version:
spend 1–2 hrs/week clipping existing content (a question's reasoning walkthrough → a 60–90s "the
mistake 80% of candidates make" Short on **YouTube** for its compounding SEO value). 1 Short/week from
repurposed material, never 5/day from scratch.

---

## 4. Content engine

### Content pillars (derived from the product, not invented)

Each pillar is a renewable well that maps to a § 1 messaging pillar and to a real product surface:

| Pillar | Source surface | Messaging tie | Example angle |
|---|---|---|---|
| **Reasoning vs. recall** | The whole thesis | Pillar 1 | "Why the memorized window-function template fails when the question is rephrased" |
| **The 9 tracks, one reasoning skill each** | The track catalog | Pillar 2/3 | "What pandas actually tests that SQL doesn't — and why both matter" |
| **Role-true prep** | `/interview-prep/<role>` pages | Pillar 4 | "The 5 tracks a Data Engineer interview really spans" |
| **Sample questions as bite-size hooks** | `/sample` (no login) | Pillar 2 | "Can you solve this in 3 lines? (no login needed)" |
| **Mock-interview narratives** | Mock / Interview Loop | Pillar 3 | "What a readiness benchmark told me I was actually weak at" |
| **Dashboard / readiness insights** | Dashboard, first-try accuracy | Pillar 1 | "Your solve count is lying to you; first-try accuracy isn't" |

> **Ready-made hook bank — don't write prompts from scratch.** [`../concept-hooks.md`](../concept-hooks.md)
> is a per-track inventory of Socratic interview hooks, and its "Mock-Only Advanced Topics" section was
> **authored explicitly for reuse as "social media posts, ad copy, and email sequences"** (its own
> words). Each hook is a concept framed as the tension a candidate must reason through — i.e. a
> drop-in seed for a "can you solve this?" / reasoning-teardown post. Mine it for the weekly pillar and
> the X/LinkedIn hooks rather than inventing questions; it already maps to the concept families the
> curriculum is built on. (Authoring caveat: hooks are *prompts about* questions — never lift a gated
> mock-only question's content into a public post; the hook is the reasoning tension, not the answer.)

### The 1-pillar → many-cuts production system

The discipline that makes a solo, part-time cadence survivable: **produce one substantial pillar
artifact per week, then cut it into every channel's native format.** One unit of thinking, many
surfaces.

```
WEEKLY PILLAR ARTIFACT  (one reasoning teardown — the week's single creative act)
  │
  ├─ Long-form article → /guides .............. SEO landing target (internal-links role + sample)
  ├─ LinkedIn carousel (company page, 8–12 slides) the week's anchor post; founder reshares ~60 min later
  ├─ LinkedIn text "story" cut (company page) .. the recognition≠reasoning angle, comment-bait-free
  ├─ X thread ("can you solve this?" + reasoning) the hook format, sample link at the end
  ├─ Reddit value comment / discussion ......... disclosed human; reasoning as discussion, link only if allowed
  ├─ Newsletter section ........................ the educational 60% of the week's email
  └─ YouTube Short (optional, repurposed) ...... 60–90s screen-capture of the teardown
```

This is **one piece of work per week**, not seven. The calendar in
[`editorial-calendar.md`](editorial-calendar.md) assigns the weekly pillar and the cut-schedule for
12 weeks.

### Launch sequence

1. **Soft launch (weeks 1–2).** Quietly live. Start LinkedIn company + X posting, begin Reddit
   *value-only* participation (no links yet), stand up the newsletter capture, verify Search Console
   (M8), publish the first pillar piece to `/guides` (M10 — start the indexing clock). PostHog
   funnel dashboard is already built on wired events (M9 done). Goal: real signal + a few honest
   testimonials, no big splash.
2. **Community value phase (weeks 3–6).** Establish the brand voice on LinkedIn/X; cross the
   value-first threshold on Reddit so a resource mention is *earned*; publish 2–3 more SEO pillar
   pieces to `/guides`; grow the newsletter from in-product capture. Run the paid-search
   thermometer (§ 3.9) once the organic baseline is established.
3. **Launch moment (≈ week 6–8).** Product Hunt + Show HN, once there's genuine product signal and a
   small base to activate honestly. Time-boxed.
4. **Sustained cadence (week 8+).** The weekly 1-pillar→many-cuts rhythm becomes steady-state;
   layer in India partnerships as relationships mature.

---

## 5. The free-sample growth loop

The **Sample Hub (`/sample`, no login, 81 sample questions)** is the shareable wedge — the entire
top-of-funnel is built to put a free sample in front of the right person and let the product earn the
next step. No signup wall to resent, nothing to lose by clicking.

### The loop, mapped to the wired PostHog events

The measurement substrate is fully wired — these events fire today (see `CLAUDE.md` § Observability):

```
   SOCIAL HOOK                         (LinkedIn/X "can you solve this?", Reddit resource share)
        │  [leading indicator: link clicks / referral traffic — channel-level, pre-product]
        ▼
   SAMPLE LANDING  (/sample, no login)
        │  ── page entered ──▶  PostHog: sample_landed  +  UTM attribution  ◀── channel attribution
        ▼
   SAMPLE QUESTION  (/sample/<track>/<diff>)
        │  ── user submits ──▶  PostHog: sample_submitted     ◀── the wedge activation event
        ▼
   "TRY THE FULL TRACK"  (sample → practice CTA)
        │
        ▼
   FREE ACCOUNT  (anonymous-first identity; registration upgrades the session in place)
        │  ── account created ──▶  PostHog: account_created   ◀── "made an account" signal
        │  ── first real solve ──▶  PostHog: question_submitted → question_solved
        ▼
   FREE TIER  (all easy questions, all 9 tracks — no ladder, no thresholds)
        │  [the medium / hard wall prompts an upgrade — the clean, honest conversion moment]
        │  ── tries a benchmark ──▶  PostHog: mock_started → mock_completed
        ▼
   PRO / ELITE
           ── upgrade CTA clicked ──▶  PostHog: plan_upgrade_started
           ── payment verified ─────▶  PostHog: plan_upgraded
```

**On the free-tier model:** Free = all easy across 9 tracks, ungated. The unlock ladder (batch
thresholds, per-track caps) was removed (2026-06-29). Medium and hard questions require Pro/Elite —
a clear, honest wall. The conversion moment is "you've worked through the easy questions, now go
deeper" — not a gamified drip. No founding-member pricing, no grandfathering cohorts, no scarcity
hooks. (The grandfathering idea was considered and rejected; see
[`../decisions/DECISIONS.md`](../decisions/DECISIONS.md) 2026-06-29.)

### Measurement gaps — now closed

The funnel's pre-product steps are instrumented (shipped):

- **`sample_landed` + UTM capture** — fired on `/sample` entry, attributes which channel/post drove
  the sample. The impression→sample handoff is now measurable.
- **`account_created`** — distinct from the first `question_*` event; separates "made an account"
  from "activated."

Remaining open item:
- **`sample_shared`** — to be fired when a user uses a share affordance on a solved sample (see
  artifacts below). Powers the viral coefficient. Not yet wired — flag for engineering when the
  share UI ships.

### Shareable artifacts (the loop's fuel)

- **Sample-question cards** — a clean OG image per sample question ("Can you solve this? — datathink,
  no login") so any shared `/sample/<track>/<diff>` URL unfurls as a hook (M3).
- **Role-readiness shares** — "I'm interview-ready for Data Engineer on datathink" style card from the
  readiness score (Elite), opt-in. Honest signal, not a vanity badge.
- **"I solved X"** — a tasteful share on a solved sample/streak. **Guardrail:** this must reflect real
  accomplishment (mastery), never a manufactured streak-flex — or it becomes the dopamine-loop
  anti-positioning we reject (§ 1, § 7).

---

## 6. Metrics + funnel

### North-star metric

> **Weekly Activated Learners (WAL)** — distinct users who, in a 7-day window, signed up *and* solved
> ≥ 1 real (non-sample) question.

Why this and not signups or visits: it captures the moment the product delivered its core value (a
reasoned solve), it's honest (a vanity signup that never solves doesn't count), and it sits directly
upstream of revenue (activated learners are who convert to Pro/Elite). It's derivable from the wired
`question_solved` + identity events.

### The funnel (on existing events)

| Stage | Definition | Event(s) | Wired? |
|---|---|---|---|
| Impression | Saw a post / SERP / unfurl | channel-native analytics | ✗ (channel dashboards only) |
| Sample landed | Hit `/sample` from a channel link | `sample_landed` + UTM | ✓ (wired) |
| Sample tried | Submitted a sample answer | `sample_submitted` | ✓ |
| **Signup** | Created an account | `account_created` | ✓ (wired) |
| **Activation** | Solved ≥1 real question (**north-star**) | `question_solved` | ✓ |
| Engaged | Ran a mock benchmark | `mock_started` → `mock_completed` | ✓ |
| Paid | Upgraded | `plan_upgrade_started` → `plan_upgraded` | ✓ |

The full chain from social hook to paid conversion is now measurable on wired events. The only
remaining gap is the impression row — which always lives in channel dashboards, not the product.

### Per-channel leading indicators (what to watch *before* conversions show up)

- **LinkedIn:** dwell-time / post impressions, comment count on "can you solve this?" posts, profile
  visits, follower quality (data-role titles).
- **SEO:** Search Console impressions + clicks on role/track queries, page-1 keyword count, sample
  page entrances from organic.
- **Reddit:** comment karma in target subs, upvotes on value posts, *referral clicks only where a link
  was rule-permitted* (not a primary metric — community trust is).
- **X:** thread profile-visit lift, reply engagement from data accounts, sample-link CTR.
- **Newsletter:** subscriber growth rate, *click* and *reply* rate (not open rate — unreliable post-iOS).

### Weekly review dashboard (PostHog + channel dashboards)

A single weekly check, ~30 minutes: WAL trend · sample→activation rate · activation→paid rate ·
top-performing post (by sample clicks) · newsletter growth · one qualitative note (best comment/DM/
Reddit thread). Build it in PostHog on the wired events (M9) before first traffic.

### What "working" looks like

- **1 month:** Funnel + dashboard live; founder voice established on LinkedIn + X; Reddit value-first
  threshold crossed; first SEO pieces indexed; newsletter capturing. WAL is small but *measured and
  trending up week-over-week*. (At this stage, leading indicators matter more than absolute numbers.)
- **3 months:** A repeatable weekly pillar→cuts rhythm; LinkedIn posts reliably driving sample clicks;
  ≥1 role+intent query on page 1; a launch-moment spike captured (PH/HN); newsletter in the hundreds;
  first organic Pro conversions attributable to a channel.
- **6 months:** Compounding SEO (multiple role/track queries ranking, `/guides` articles indexed);
  LinkedIn company page a reliable secondary reach driver with founder amplification; Reddit a
  trusted-contributor presence (not a promoter); newsletter low-thousands; a predictable WAL→paid
  rate good enough to forecast; ≥1 live India partnership. The brand's *role+intent* + community +
  entity signals are visibly improving disambiguation (per [`../seo.md`](../seo.md) Phase 3), even
  if the bare-brand panel is still contested.

---

## 7. Resourcing + cadence (honest, solo / part-time)

The cadence is designed for **a solo founder, part-time**. The system in § 4 (one pillar → many cuts)
is what makes that survivable: the only real creative act each week is the pillar teardown.

### Minimum-viable weekly cadence (the floor — protect this)

| Cadence | Time |
|---|---|
| 1 pillar artifact (the week's reasoning teardown) | ~3–4 hrs |
| → LinkedIn carousel (company page, anchor) + 1 text cut + founder reshare | ~1 hr (cut, not create) |
| → X: 1 thread + daily replies | ~20 min/day |
| → Reddit: daily light value participation (disclosed human) | ~15 min/day |
| → Newsletter: assemble the weekly email from the pillar | ~1 hr |
| Weekly metrics review | ~30 min |

≈ **6–8 focused hours/week.** Everything else (video, second LinkedIn post, partnerships outreach) is
*above* the floor — do it only when the floor is comfortably met.

### Ambitious cadence (when there's more capacity / a second person)

Add: a second weekly LinkedIn post, daily X originals, a YouTube Short/week, active bootcamp-partnership
outreach, a second SEO piece. This is the *aspiration*, not the commitment — committing to it and missing
is worse than hitting the floor consistently (consistency is the algorithmic and trust currency).

### Batch / automate

- **Batch** a month of LinkedIn carousels in one design session (template once, fill weekly).
- **Schedule** posts (any scheduler) so posting-day is mechanical, not creative.
- **Template** the X thread + newsletter structure so only the content changes.
- **Reuse** the pillar: never create per-channel from scratch.

### Explicitly do NOT do (the pushback-lens reject list)

These are the "growth" tactics that the lens *"is this serving the user or a metric?"* and *"would I
be embarrassed defending this in a year?"* reject. Naming them is the point — they're tempting because
they *work* short-term in the grind market, and adopting them would quietly convert us into it:

1. **Comment-to-unlock engagement bait** ("comment 'SQL' for the link"). Juices a vanity metric, trains
   the audience to transact rather than reason, and clutters the feed. (A known competitor staple — we
   pass.)
2. **Astroturfing** (fake "has anyone tried datathink?" threads, sockpuppet praise). Dishonest, brand-
   lethal on Reddit/HN, and the antithesis of a reasoning brand.
3. **Follower / upvote buying, engagement pods, vote rings.** Vanity, detectable, penalized.
4. **Daily-streak / leaderboard dopamine mechanics** as a *marketing* hook. This is the anti-positioning
   (§ 1) — retention must come from mastery, not manufactured FOMO. (Distinct from honest progress
   surfacing like first-try accuracy.)
5. **Company-question-dump content** ("the 50 questions Meta asks"). It's the grind frame; it contradicts
   the filter policy and the positioning.
6. **Spray-and-pray cross-posting** the same link to 20 subreddits. Bans the account, signals nothing,
   wastes the wedge.
7. **Manufactured scarcity** (fake "24 hours left" timers, fake cohort caps). Erodes the trust a premium
   reasoning brand runs on.
8. **AI-spun thin SEO pages** at volume. Degrades the entity quality SEO Phase 3 depends on.

If a future tactic isn't on this list but fails the same two lenses, it belongs here — append it.

---

## 8. Concrete starter assets

The actionable kit — example posts in the datathink voice, the subreddit target list with each sub's
self-promo rule, the launch-day checklist, the brand-handle claim list, and a day-by-day first-two-
weeks plan — lives in [`starter-assets.md`](starter-assets.md) so this strategy doc stays the durable
*why* and the assets stay the editable *what*.

The 12-week editorial calendar and the pillar→cuts production schedule live in
[`editorial-calendar.md`](editorial-calendar.md).
