# SEO Implementation Plan — datathink

> Written: 2026-05-15. Do not execute multiple phases in parallel — each phase builds on the previous.
> Constraint: no changes to question content, evaluation logic, unlock rules, or payment flows.

---

## Current state

The platform has a solid foundation:

- **robots.txt** — correct, disallows `/api/`, `/dashboard`, `/mock`, `/auth`, references sitemap
- **sitemap.xml** — 46 URLs dynamically generated: homepage, 4 track hubs, 4 practice hubs, 12 sample pages, 22 learning path pages
- **Server-side meta injection** — `spa.py → _build_seo_meta()` injects title, description, canonical, og:* for all known routes before the HTML reaches a crawler
- **react-helmet-async** — per-route client-side meta management on top of the server injection
- **noindex** — correctly applied to `/auth`, `/dashboard`, `/mock`, and all individual `QuestionPage` instances
- **JSON-LD schemas** — WebSite + Organization + SearchAction on landing; Course on TrackHubPage; LearningResource on individual learning path pages

---

## What was underweighted (and why it matters)

### Free public content is broader than the 36 sample questions

Anonymous visitors have access to **all 122 easy questions** (32 SQL + 30 Python + 22 Pandas + 38 PySpark) under the same free-tier unlock model as registered free users. Session cookies track progress within a session; closing the browser resets it. Medium and hard questions that unlock within a session are also technically accessible to anonymous users, but a crawler with no session history will hit 403 on those API calls (locked), so they cannot be reliably indexed.

Currently `QuestionPage.js` sets `noindex` on every question page regardless of difficulty, and `spa.py` has no entries for any individual question URLs. This means 122 pages of unique, crawlable content are actively hidden from Google.

---

## Gap analysis

| # | Gap | Severity |
|---|---|---|
| 1 | 122 easy question pages are `noindex` + no server-side meta — unique titles, problem descriptions, concepts, companies never indexed | Critical |
| 4 | `SearchAction` target is broken — points to `/practice/sql` which doesn't accept a query param; disqualifies the sitelinks search box in SERPs | High |
| 5 | Policy pages (Privacy, Terms, Contact, Refund) have no `<Helmet>` — fall back to landing page title/description when crawled or shared | High |
| 6 | `LearningPath` uses `LearningResource` schema instead of `Course` — misses rich result eligibility (enrollment CTA, hasCourseInstance SERP chip) | High |
| 7 | No `BreadcrumbList` JSON-LD on learning path pages — HTML breadcrumbs exist but no schema; SERP breadcrumb display blocked | High |
| 8 | No `ItemList` JSON-LD on `LearningPathsIndex` — 22 paths listed but no structured data for the collection | Medium |
| 9 | No `FAQPage` JSON-LD on landing — pricing/feature questions could appear as SERP answer boxes | Medium |
| 10 | `SampleQuestionPage` JSON-LD missing — 36 public pages have no structured data | Medium |
| 11 | Policy pages missing from sitemap | Medium |
| 12 | `/practice/:topic` vs `/learn/:topic` canonical competition — both rank for similar queries at priority 0.8 | Medium |
| 13 | Generic OG image (`og-image.png`) for all pages — every social share looks identical | Low |
| 14 | `teaches` in LearningResource uses freeform outcome text instead of the `focus_concepts` array | Low |
| 15 | No `SoftwareApplication` JSON-LD — missed knowledge panel / app eligibility | Low |

---

## Keyword opportunity map

These are the queries the platform should own but currently doesn't surface:

| Query type | Examples | Where they'd land |
|---|---|---|
| Concept-specific | "sql window functions interview questions", "sql cte practice", "pandas groupby interview" | Concept pages (Phase 3) |
| Company-specific | "amazon sql interview questions", "meta python interview", "google data engineer sql" | Company pages (Phase 3) |
| Question-level long-tail | "sql completed orders query interview", "python two pointer interview problem" | Easy question pages (Phase 2) |
| Platform-level | "sql interview practice online", "pyspark mcq questions", "pandas dataframe interview" | Landing + track hubs (Phase 1) |
| Learning intent | "sql window functions tutorial interview", "how to practice sql for amazon" | Learning path pages (already indexed) |

---

## Implementation plan

### Phase 1 — Technical hygiene (1–2 days, zero functional risk)

All changes are meta tags, JSON-LD, and sitemap entries only.

---

#### 1a. Fix SearchAction target
**File:** `frontend/src/pages/LandingPage.js:401-403`

Current (broken):
```json
"potentialAction": {
  "@type": "SearchAction",
  "target": "https://datathink.co/practice/sql",
  "query-input": "required name=search_term_string"
}
```

Replace with:
```json
"potentialAction": {
  "@type": "SearchAction",
  "target": {
    "@type": "EntryPoint",
    "urlTemplate": "https://datathink.co/learn?q={search_term_string}"
  },
  "query-input": "required name=search_term_string"
}
```

Then handle `?q=` in `LearningPathsIndex.js` to filter paths client-side by keyword. **Impact: unlocks the sitelinks search box in Google SERPs.**

---

#### 1b. Add Helmet to all 4 policy pages
**Files:** `PrivacyPolicyPage.js`, `TermsPage.js`, `ContactPage.js`, `RefundPolicyPage.js`

Each needs: `<title>`, `<meta name="description">`, `<link rel="canonical">`, `og:title`, `og:description`, `og:url`. These pages should be indexed (they build E-E-A-T trust signals with Google). Do NOT add `noindex`.

| Page | Title | Description |
|---|---|---|
| Privacy | "Privacy Policy — datathink" | "How datathink collects, uses, and protects your personal data." |
| Terms | "Terms of Service — datathink" | "Terms governing your use of the datathink interview practice platform." |
| Contact | "Contact datathink" | "Get in touch with the datathink team for support or questions." |
| Refund | "Refund Policy — datathink" | "datathink's refund and cancellation policy for Pro and Elite plans." |

---

#### 1c. Add policy pages to sitemap
**File:** `backend/routers/system.py:73-96`

Add to `static_urls`:
```python
("/privacy", "0.3", "monthly"),
("/terms", "0.3", "monthly"),
("/contact", "0.4", "monthly"),
("/refund-policy", "0.3", "monthly"),
```

---

#### 1d. Sharpen `/practice/:topic` vs `/learn/:topic` meta differentiation
**Files:** `TrackHubPage.js:153-156`, `backend/routers/spa.py:57-72`

The practice hub and learning path index compete for the same queries at the same sitemap priority. Differentiate the framing clearly:

- `/practice/sql` → workspace framing: "Your SQL practice workspace. Track your progress across 95 questions organized by difficulty, pick up where you left off, and solve real interview problems with instant DuckDB feedback."
- `/learn/sql` → curriculum framing: "SQL learning paths for data interviews — curated sequences covering window functions, aggregation, cohort analysis, joins, and more."

Update both the `spa.py` descriptions and the `<meta name="description">` in `TrackHubPage.js`. Keep both in sitemap but at 0.7 for practice hubs and 0.8 for learn hubs to signal the hierarchy.

---

### Phase 2 — Schema enrichment (2–3 days, no functional change)

JSON-LD upgrades across existing pages. No new routes or backend changes needed.

---

#### 2a. Upgrade LearningPath: LearningResource → Course + add BreadcrumbList
**File:** `frontend/src/pages/LearningPath.js:106-116`

Replace the current schema block with two schemas in sequence:

**Course schema** (replaces LearningResource):
```json
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "{path.title}",
  "description": "{path.description}",
  "url": "https://datathink.co/learn/{topic}/{slug}",
  "inLanguage": "en",
  "teaches": "{path.focus_concepts}",
  "numberOfItems": "{path.questions.length}",
  "educationalLevel": "{path.role}",
  "hasCourseInstance": {
    "@type": "CourseInstance",
    "courseMode": "online"
  },
  "provider": {
    "@type": "Organization",
    "name": "datathink",
    "url": "https://datathink.co"
  },
  "isPartOf": {
    "@type": "Course",
    "name": "{trackLabel} Interview Practice",
    "url": "https://datathink.co/learn/{topic}"
  }
}
```

**BreadcrumbList schema** (new, alongside Course):
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Practice", "item": "https://datathink.co" },
    { "@type": "ListItem", "position": 2, "name": "Learning Paths", "item": "https://datathink.co/learn" },
    { "@type": "ListItem", "position": 3, "name": "{trackLabel}", "item": "https://datathink.co/learn/{topic}" },
    { "@type": "ListItem", "position": 4, "name": "{path.title}" }
  ]
}
```

The HTML breadcrumbs already exist at `LearningPath.js:126-133` — this schema is a direct mirror of what's already rendered. **Impact: SERP breadcrumb display replaces the raw URL, substantially improving CTR.**

---

#### 2b. Add ItemList JSON-LD to LearningPathsIndex
**File:** `frontend/src/pages/LearningPathsIndex.js`

When the `paths` data loads (from `/api/paths`, which is already called), emit an `ItemList`:

```json
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "{topic ? trackLabel + ' Learning Paths' : 'Data Interview Learning Paths'}",
  "description": "...",
  "numberOfItems": "{paths.length}",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "item": {
        "@type": "Course",
        "name": "Aggregation Patterns",
        "url": "https://datathink.co/learn/sql/aggregation-patterns",
        "description": "..."
      }
    }
  ]
}
```

Inject this as a `<script type="application/ld+json">` via Helmet once paths are loaded. **Impact: individual learning paths become eligible for rich results directly from the index page.**

---

#### 2c. Add FAQPage JSON-LD to landing
**File:** `frontend/src/pages/LandingPage.js:393-413`

Add alongside the existing WebSite and Organization schemas:

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is datathink free to use?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. All easy questions across all four tracks — SQL, Python, Pandas, and PySpark — are free, including for visitors without an account. Medium and hard questions unlock progressively as you solve more. No credit card required."
      }
    },
    {
      "@type": "Question",
      "name": "What SQL topics are covered?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "datathink covers 95 SQL questions across aggregation, window functions, CTEs, joins, subqueries, cohort analysis, period-over-period analysis, and more — all executed against real datasets using DuckDB."
      }
    },
    {
      "@type": "Question",
      "name": "Can I practice without creating an account?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. All easy questions across all four tracks are accessible without registration. You can also try 3 free sample questions per track and difficulty with no account required. Progress is saved across sessions once you create a free account."
      }
    },
    {
      "@type": "Question",
      "name": "Which companies' interview questions are covered?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Questions are tagged with companies including Amazon, Meta, Google, Stripe, Netflix, Shopify, LinkedIn, and more across all four tracks."
      }
    },
    {
      "@type": "Question",
      "name": "What is the difference between Free, Pro, and Elite?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Free gives access to all easy questions and progressive medium/hard unlocks. Pro unlocks all questions across all tracks plus mock interviews up to hard difficulty. Elite adds unlimited mocks, focus-mode mock sessions, and readiness scoring."
      }
    }
  ]
}
```

**Impact: FAQ rich snippets in SERPs for informational queries about the platform, including competitive queries like "best sql interview practice free".**

---

#### 2d. Add SoftwareApplication JSON-LD to landing
**File:** `frontend/src/pages/LandingPage.js`

Add as a third schema block alongside WebSite and Organization:

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "datathink",
  "applicationCategory": "EducationalApplication",
  "operatingSystem": "Web",
  "inLanguage": "en",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
    "description": "Free tier available with all easy questions"
  },
  "url": "https://datathink.co",
  "provider": {
    "@type": "Organization",
    "name": "datathink",
    "url": "https://datathink.co"
  }
}
```

---

#### 2e. Add Quiz JSON-LD to SampleQuestionPage
**File:** `frontend/src/pages/SampleQuestionPage.js`

These 36 pages are fully public. Add after the existing Helmet meta (line 380):

```json
{
  "@context": "https://schema.org",
  "@type": "Quiz",
  "name": "Free {Difficulty} {Track} Interview Questions",
  "description": "...",
  "educationalLevel": "{difficulty}",
  "inLanguage": "en",
  "about": { "@type": "Thing", "name": "{track} interview preparation" },
  "learningResourceType": "Practice problems",
  "isAccessibleForFree": true,
  "provider": { "@type": "Organization", "name": "datathink", "url": "https://datathink.co" }
}
```

---

### Phase 3 — Index the 122 easy question pages (3–4 days)

This is the most technically involved hygiene fix. All 122 easy questions are publicly accessible to unauthenticated visitors and crawlers, but are actively hidden from Google by a blanket `noindex` and no server-side meta.

---

#### 3a. Server-side meta injection for easy question URLs
**File:** `backend/routers/spa.py — _build_seo_meta()`

At startup, the question JSON files are already loaded in memory by the catalog loaders. Extend `_build_seo_meta()` to also load easy question metadata and add entries for each question URL:

```python
# In _build_seo_meta(), after learning path injection:
try:
    from questions import get_questions  # or however easy.json is accessed
    for q in easy_sql_questions:
        concepts_preview = ", ".join(q.get("concepts", [])[:3])
        companies_preview = ", ".join(q.get("companies", [])[:2])
        desc = q.get("description", "")[:120].rstrip() + "..."
        meta[f"/practice/sql/questions/{q['id']}"] = {
            "title": f"{q['title']} — SQL Practice — datathink",
            "description": f"Practice: {desc} Covers {concepts_preview}.",
        }
    # Repeat for python, python-data, pyspark easy questions
except Exception:
    pass
```

The title format `"{Question Title} — SQL Practice — datathink"` surfaces the question name (which contains the actual keyword), the track, and the brand.

Do the same for Python, Pandas, and PySpark easy questions at their respective URL paths:
- `/practice/python/questions/{id}`
- `/practice/python-data/questions/{id}`
- `/practice/pyspark/questions/{id}`

---

#### 3b. Remove `noindex` from easy questions in QuestionPage
**File:** `frontend/src/pages/QuestionPage.js — around line 849-851`

Currently every question gets `noindex`. Change this to conditional logic based on difficulty:

```jsx
<Helmet>
  <title>{question.title} — {trackLabel} Practice — datathink</title>
  <meta name="description" content={`Practice: ${question.description.slice(0, 120)}...`} />
  {question.difficulty !== 'easy' && (
    <meta name="robots" content="noindex, nofollow" />
  )}
  {question.difficulty === 'easy' && (
    <link rel="canonical" href={`https://datathink.co/practice/${topic}/questions/${question.id}`} />
  )}
</Helmet>
```

Medium and hard questions keep `noindex` because they're conditionally accessible (a crawler without a session history hits 403).

---

#### 3c. Add easy question URLs to sitemap
**File:** `backend/routers/system.py:67-129`

Load easy questions from the in-memory catalog loaders and emit their URLs with priority 0.6:

```python
# In sitemap_xml(), after path_urls:
try:
    from questions import get_questions
    easy_sql = [(f"/practice/sql/questions/{q['id']}", "0.6", "monthly")
                for q in get_questions() if q.get("difficulty") == "easy"]
    # Repeat for other tracks
except Exception:
    easy_sql = []
```

This adds ~122 URLs to the sitemap. The sitemap will grow from 46 to ~168 URLs — still a single sitemap file (50k URL limit).

---

### Phase 4 — Technical performance (optional, do last)

These are high-effort and lower immediate-impact than Phases 1-3.

---

#### 4a. Dynamic OG images per learning path

All pages currently share `/og-image.png`. Every social share looks identical. Use `satori` (or a simple canvas script in the build) to generate per-path images:

```
/og-image/learn/sql/window-functions-mastery.png
```

With the path title, track accent color, and datathink wordmark. Update `_inject_seo()` in `spa.py:126` to use the per-path OG image URL for learning path routes.

---

#### 4b. Make `/api/paths/:slug` metadata publicly readable

Currently path detail requires authentication. The metadata (title, description, question count, focus_concepts) has no reason to be gated — it's shown publicly on the landing page. Making the read-only metadata public would:
1. Allow prerendering learning path pages with real content
2. Allow concept/company pages to link to related paths without auth

Change: strip the `current_user` dependency from the path metadata portion of `routers/paths.py`. Solve state per question still requires auth.

---

#### 4c. Sitemap index as URLs scale

After Phase 3, the sitemap will grow from ~46 to ~168 URLs. If it ever approaches 50k, split into a sitemap index:

- `/sitemap.xml` — index pointing to:
  - `/sitemap-core.xml` — static pages, practice hubs, sample pages
  - `/sitemap-paths.xml` — 22 learning path pages
  - `/sitemap-questions.xml` — ~122 easy question pages

---

## Prioritized execution order

| # | Item | Phase | Files | Est. effort | Impact |
|---|---|---|---|---|---|
| 1 | Fix SearchAction target | 1a | `LandingPage.js:401`, `LearningPathsIndex.js` | 45 min | Sitelinks search box |
| 2 | Helmet on 4 policy pages | 1b | 4 page files | 1 hr | Trust + correct sharing |
| 3 | Policy pages in sitemap | 1c | `system.py:73` | 15 min | Faster discovery |
| 4 | Sharpen practice vs learn meta | 1d | `TrackHubPage.js`, `spa.py` | 1 hr | Reduce cannibalization |
| 5 | LearningPath → Course + BreadcrumbList | 2a | `LearningPath.js:106` | 2 hrs | Rich results + SERP breadcrumbs |
| 6 | ItemList on LearningPathsIndex | 2b | `LearningPathsIndex.js` | 1.5 hrs | Collection rich results |
| 7 | FAQPage JSON-LD on landing | 2c | `LandingPage.js` | 1 hr | SERP answer boxes |
| 8 | SoftwareApplication JSON-LD | 2d | `LandingPage.js` | 30 min | App knowledge panel |
| 9 | Quiz JSON-LD on SampleQuestionPage | 2e | `SampleQuestionPage.js` | 45 min | Sample page rich results |
| 10 | Server-side meta for easy questions | 3a | `spa.py` | 2 hrs | Crawlable meta for 122 pages |
| 11 | Remove noindex from easy questions | 3b | `QuestionPage.js:849` | 30 min | Indexes 122 pages |
| 12 | Easy questions in sitemap | 3c | `system.py` | 1 hr | Sitemap coverage |
| 13 | Dynamic OG images | 4a | Build script + `spa.py` | 3 days | Social CTR |
| 14 | Public path metadata API | 4b | `routers/paths.py` | 1 day | Enables prerendering |
| 15 | Sitemap index | 4c | `system.py` | 1 day | Scalability |

---

## Expected indexable URL count

| State | URLs | Primary queries targeted |
|---|---|---|
| Today | ~46 | Brand, generic track-level |
| After Phase 1+2 | ~50 | + Better CTR on existing pages via rich results |
| After Phase 3 | ~172 | + 122 easy question long-tail keywords |

---

## What this plan does NOT touch

- Question content (descriptions, expected queries, solutions, explanations, hints)
- Evaluation logic (DuckDB execution, Python sandbox, PySpark MCQ comparison)
- Unlock rules (free tier thresholds, path shortcut gates)
- Payment flows (Razorpay orders, subscriptions, webhook handling)
- Auth model (sessions, OAuth, magic links, anonymous identity)
- Any existing API endpoint behavior
