import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Topbar from '../components/Topbar';
import { Reveal } from '../components/Reveal';
import { ROLES } from '../roleRegistry';
import { TRACK_META } from '../contexts/TopicContext';
import NotFoundPage from './NotFoundPage';

// ── Per-role content map ─────────────────────────────────────────────────────
// Only roles with `hasPage: true` in roleRegistry.js need an entry here.
// Keys must match the `slug` field in roleRegistry.js.

const BREADCRUMB_LD = (label, slug) => ({
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    {
      '@type': 'ListItem',
      position: 1,
      name: 'Home',
      item: 'https://datathink.co/',
    },
    {
      '@type': 'ListItem',
      position: 2,
      name: 'Interview prep',
      item: 'https://datathink.co/interview-prep',
    },
    {
      '@type': 'ListItem',
      position: 3,
      name: label,
      item: `https://datathink.co/interview-prep/${slug}`,
    },
  ],
});

// ── Shared reasoning section (platform-level, identical for every role) ──────
const SHARED_REASONING = {
  h2: 'Built for reasoning, not recall',
  points: [
    {
      heading: 'Real engines where it counts',
      body: 'SQL runs on DuckDB and Python in a sandbox with instant feedback. The reasoning tracks test judgment with realistic scenarios, not rote recall.',
    },
    {
      heading: 'Mock interviews',
      body: 'Timed sessions that pressure-test the whole stack, with a post-mortem that names your weakest concepts.',
    },
    {
      heading: 'A graded path',
      body: 'Curated learning paths take you from foundational to advanced, concept by concept.',
    },
  ],
};

const FREE_PRACTICE_FAQ = {
  q: 'Can I practice for free?',
  a: 'More than you might expect. Every easy question is free, and medium and hard unlock as you solve, so a free account goes a long way. Samples need no account at all. Paid plans lift the unlock caps and add the mock-only question bank, mock interviews, and deep analytics.',
  link: { label: 'More details →', to: '/pricing' },
};

const ROLE_CONTENT = {
  'data-engineer': {
    helmet: {
      title: 'Data Engineer Interview Prep: SQL, Python, Spark & Pipelines | datathink',
      description:
        'Data engineer interview prep on real execution engines: SQL, Python, PySpark and data pipeline design, plus mock interviews and reasoning-first questions.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Engineer',
      h1: 'Data Engineer Interview Prep',
      sub: 'A pipeline that is correct on Monday can quietly double-count after a Tuesday retry. Data engineer interviews push on exactly that kind of judgment: idempotent loads, the Python that sessionizes an event stream without holding it all in memory, when a broadcast join beats a shuffle, and the fact-table grain that keeps analytics honest as volume grows. datathink builds it on the real engines, the way the job does.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-engineer' },
      ctaSecondary: { label: 'See the 5 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data engineer interviews actually test',
      body: 'Syntax recall is not the job. A data engineer is judged on whether the pipeline survives production: picking a fact-table grain that will not silently lie, making a backfill idempotent so an at-least-once source cannot double-fire, salting a hot key when a skew join stalls, and writing SQL that stays correct as tables outgrow memory. That judgment is what the five tracks build, each on the engine where the mistake actually shows up.',
    },
    tracks: [
      {
        slug: 'python',
        desc: 'Data-processing algorithms: sessionization, dedup, streaming aggregation, and the logic behind pipeline transforms.',
      },
      {
        slug: 'sql',
        desc: 'Window functions, aggregation, and the query depth that holds up as tables grow.',
      },
      {
        slug: 'pyspark',
        desc: 'Distributed processing: shuffles, joins, partitioning, and the trade-offs behind a tuned Spark job.',
      },
      {
        slug: 'data-engineering',
        desc: 'Pipeline design: ETL vs ELT, idempotency, orchestration, CDC, and schema evolution.',
      },
      {
        slug: 'data-modeling',
        desc: 'Dimensional modeling, grain, normalization, and SCDs, so downstream analytics scale instead of breaking.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data engineer study for interviews?',
        a: 'Focus on SQL depth, a data-processing language like Python, distributed processing with Spark, and pipeline and data-modeling reasoning such as idempotency, grain, and orchestration. datathink groups these into five tracks built around the data engineer interview.',
      },
      {
        q: 'Do data engineer interviews include SQL?',
        a: 'Almost always. SQL is the most common screen for data engineers: joins, window functions, and queries that stay correct and efficient as data scales. It is one of the five datathink tracks for the role.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'datathink trains the reasoning a data engineer uses on the job, not pattern memorization. Code runs on real engines, and the reasoning tracks test judgment with realistic scenarios rather than multiple-choice trivia. Two-step hints build the mental model before the technique, and learning paths take you from foundational to advanced, concept by concept. Elite plans add per-track readiness scores and Interview Loops: chain-driven mock sessions where each follow-up pivots like a real interviewer, the way a real screen escalates.',
      },
      FREE_PRACTICE_FAQ,
      {
        q: 'How long does it take to prepare?',
        a: 'It depends on your starting point. Most candidates work in focused sessions across the five tracks, and the dashboard surfaces your weakest concepts so you spend time where it moves the needle.',
      },
    ],
  },

  'data-analyst': {
    helmet: {
      title: 'Data Analyst Interview Prep: SQL, Statistics & Python | datathink',
      description:
        'Data analyst interview prep on real engines: SQL depth, statistical reasoning, Pandas and Python for data, plus mock interviews and reasoning-first questions.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Analyst',
      h1: 'Data Analyst Interview Prep',
      sub: 'Anyone can pull a number; a data analyst is hired to pull the right one and know whether it means anything. Interviews test that whole arc: SQL that joins and aggregates to the grain the question actually asked, the statistics to separate a real lift from sampling noise, and the Pandas to answer what a dashboard cannot. Every track runs on a real engine, so you are judged on the answer, not your recall of the syntax.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-analyst' },
      ctaSecondary: { label: 'See the 4 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data analyst interviews actually test',
      body: 'The hard part of the analyst screen is not remembering a window function; it is defending the answer. You will be asked to choose the denominator that makes a metric honest, to say whether an 8% lift is signal or sampling noise, to catch the join fan-out that quietly double-counts revenue, and to reshape data in Pandas when the warehouse cannot. datathink drills each of those calls with reasoning questions and live execution, across the four tracks the role leans on.',
    },
    tracks: [
      {
        slug: 'sql',
        desc: 'Joins, window functions, and the query patterns that turn raw tables into the metric a stakeholder asked for.',
      },
      {
        slug: 'statistics',
        desc: 'Hypothesis testing, confidence intervals, and the judgment to tell a real effect from noise.',
      },
      {
        slug: 'pandas',
        desc: 'Reshaping, grouping, and cleaning data in DataFrames when the question outgrows SQL.',
      },
      {
        slug: 'python',
        desc: 'The scripting and logic to automate analysis and handle data a query cannot.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data analyst study for interviews?',
        a: 'Prioritize SQL fluency, applied statistics, and a working command of Python or Pandas for analysis. datathink groups these into four tracks built around the data analyst interview, with reasoning questions, not trivia.',
      },
      {
        q: 'How much SQL do data analyst interviews need?',
        a: 'A lot. SQL is the core analyst screen: joins, aggregation, window functions, and getting the metric right as data scales. It is one of the four datathink tracks for the role.',
      },
      {
        q: 'Do analyst interviews include statistics?',
        a: 'Often. Many ask you to judge whether a result is meaningful, design a simple test, or interpret a confidence interval. The Statistics track covers this with conceptual and numerical questions.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'datathink trains the reasoning an analyst uses on the job, not pattern memorization. Code runs on real engines, two-step hints build the mental model before the technique, and learning paths take you from foundational to advanced. Elite plans add per-track readiness scores and Interview Loops, chain-driven mock sessions that pivot like a real interviewer.',
      },
      FREE_PRACTICE_FAQ,
    ],
  },

  'analytics-engineer': {
    helmet: {
      title: 'Analytics Engineer Interview Prep: SQL, dbt & Data Modeling | datathink',
      description:
        'Analytics engineer interview prep on real engines: SQL precision, dimensional data modeling, dbt patterns, Pandas and Python, plus mock interviews and reasoning-first questions.',
    },
    hero: {
      eyebrow: 'Interview prep · Analytics Engineer',
      h1: 'Analytics Engineer Interview Prep',
      sub: 'The analytics engineer owns the layer every dashboard inherits, so a wrong grain here becomes a hundred wrong numbers downstream. Interviews probe that responsibility: the fact-table grain and keys that stay correct under slowly-changing dimensions, when to normalize versus denormalize, and SQL clean enough to trust in production and still read six months later. datathink trains it on the engines and schema problems the job is actually made of.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=analytics-engineer' },
      ctaSecondary: { label: 'See the 4 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What analytics engineer interviews actually test',
      body: 'Design is the whole game, and the interview rewards it over recall. The decisions compound: choosing a grain that will not need re-platforming later, picking an SCD Type 2 strategy when audit and reporting requirements disagree, conforming a dimension across two independently sourced systems, and writing transformation SQL a teammate can read and a model can depend on. Pandas and Python cover the steps that do not belong in a query. The four tracks rehearse each of those, the way a real design review would.',
    },
    tracks: [
      {
        slug: 'sql',
        desc: 'Window functions, CTEs, and the precise, maintainable SQL the transformation layer depends on.',
      },
      {
        slug: 'data-modeling',
        desc: 'Dimensional modeling, grain, normalization, and the dbt-style design that decides whether analytics scale.',
      },
      {
        slug: 'pandas',
        desc: 'DataFrame transformation and reshaping for the steps that do not belong in SQL.',
      },
      {
        slug: 'python',
        desc: 'The scripting and logic behind reliable, testable transformation code.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should an analytics engineer study for interviews?',
        a: 'Focus on advanced SQL, dimensional data modeling, and dbt-style transformation patterns, with Python or Pandas for the rest. datathink groups these into four tracks built around the analytics engineer interview.',
      },
      {
        q: 'Do analytics engineer interviews include data modeling?',
        a: 'Yes, heavily. Grain, keys, normalization, slowly changing dimensions, and star schemas are core. The Data Modeling track covers them with scenario and design questions.',
      },
      {
        q: 'How is SQL tested for analytics engineers?',
        a: 'Beyond getting the answer, you are judged on SQL that is correct, efficient, and maintainable as a model grows. The SQL track drills exactly that.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'datathink trains the reasoning an analytics engineer uses on the job, not pattern memorization. Code runs on real engines, two-step hints build the mental model first, and learning paths take you from foundational to advanced. Elite plans add per-track readiness scores and Interview Loops, chain-driven mock sessions that pivot like a real interviewer.',
      },
      FREE_PRACTICE_FAQ,
    ],
  },

  'data-scientist': {
    helmet: {
      title: 'Data Scientist Interview Prep: ML, Statistics & Experimentation | datathink',
      description:
        'Data scientist interview prep on real engines: ML fundamentals, statistical inference, experimentation, plus Python and SQL, with mock interviews and reasoning-first questions.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Scientist',
      h1: 'Data Scientist Interview Prep',
      sub: 'A data scientist has to get from raw data to a claim that survives scrutiny, and interviews test every step of that path. Expect to diagnose why a model that scored 0.95 offline drops to 0.70 in production, to say when a result is statistically real instead of underpowered noise, to design an experiment that isolates cause, and to do the Pandas, Python, and SQL the work actually runs on. datathink drills that reasoning on engines that execute, not flashcards.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-scientist' },
      ctaSecondary: { label: 'See the 6 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data scientist interviews actually test',
      body: 'Memorized formulas do not get you through a data science loop; judgment does. You will be asked to read a learning curve and name bias versus variance, to spot the leakage hiding behind a too-good AUC, to choose a correction when a PM ran eight tests and one came back significant, to defend an experiment against sample-ratio mismatch, and to wrangle the data in Pandas and SQL before any of it. These are the calls the six tracks drill, with a timed mock and a post-mortem that names the ones you missed.',
    },
    tracks: [
      {
        slug: 'ml-fundamentals',
        desc: 'Model selection, bias-variance, evaluation metrics, and the production trade-offs interviewers probe.',
      },
      {
        slug: 'statistics',
        desc: 'Probability, inference, and hypothesis testing, the quantitative backbone of a defensible claim.',
      },
      {
        slug: 'experimentation',
        desc: 'A/B design, power, and causal inference, so your conclusions hold up.',
      },
      {
        slug: 'python',
        desc: 'The data-processing and modeling code a data scientist writes every day.',
      },
      {
        slug: 'pandas',
        desc: 'DataFrame wrangling for exploratory analysis and feature prep, the hands-on step before a model.',
      },
      {
        slug: 'sql',
        desc: 'Pulling and shaping the data a model needs, correctly and at scale.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data scientist study for interviews?',
        a: 'Prioritize ML fundamentals, applied statistics, and experimentation, with Python, Pandas, and SQL underneath. datathink groups these into six tracks built around the data scientist interview, with reasoning questions, not trivia.',
      },
      {
        q: 'Do data scientist interviews include statistics and experimentation?',
        a: 'Almost always. Expect questions on inference, A/B test design, power, and reading a result honestly. The Statistics and Experimentation tracks cover both.',
      },
      {
        q: 'Is machine learning enough on its own?',
        a: 'No. Interviews probe whether you understand why a model behaves as it does, plus the statistics and experiment design around it. datathink covers the full reasoning surface, not just model recall.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'datathink trains the reasoning a data scientist uses on the job, not pattern memorization. Code runs on real engines, two-step hints build the mental model first, and learning paths take you from foundational to advanced. Elite plans add per-track readiness scores and Interview Loops, chain-driven mock sessions that pivot like a real interviewer.',
      },
      FREE_PRACTICE_FAQ,
    ],
  },
};

// ── FAQ item component ───────────────────────────────────────────────────────
function FaqItem({ q, a, link }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`ip-faq-item${open ? ' is-open' : ''}`}>
      <button
        type="button"
        className="ip-faq-q"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {q}
        <span className="ip-faq-arrow" aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="ip-faq-a">
          {a}
          {link && (
            <Link className="ip-faq-link" to={link.to}>{link.label}</Link>
          )}
        </div>
      )}
    </div>
  );
}

// ── Track count heading helper ───────────────────────────────────────────────
function tracksHeading(roleLabel, count) {
  const words = { 4: 'four', 5: 'five', 6: 'six', 7: 'seven' };
  return `The ${words[count] || count} tracks for ${roleLabel.toLowerCase()}`;
}

// ── Main page component ──────────────────────────────────────────────────────
export default function RoleInterviewPrepPage() {
  const { role: roleSlug } = useParams();

  const roleData = ROLES.find((r) => r.slug === roleSlug);
  const content = ROLE_CONTENT[roleSlug];

  // Guard: role not found, not published, or no content entry
  if (!roleData || !roleData.hasPage || !content) {
    return <NotFoundPage />;
  }

  const { helmet, hero, whatSection, tracks, reasoningSection, faq } = content;

  const breadcrumbLd = BREADCRUMB_LD(roleData.label, roleSlug);
  const faqLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faq.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  };

  return (
    <div className="ip-page">
      <Helmet>
        <title>{helmet.title}</title>
        <meta name="description" content={helmet.description} />
        <meta property="og:title" content={helmet.title} />
        <meta property="og:description" content={helmet.description} />
        <meta property="og:url" content={`https://datathink.co/interview-prep/${roleSlug}`} />
        <link rel="canonical" href={`https://datathink.co/interview-prep/${roleSlug}`} />
        <script type="application/ld+json">{JSON.stringify(breadcrumbLd)}</script>
        <script type="application/ld+json">{JSON.stringify(faqLd)}</script>
      </Helmet>

      <Topbar />

      <main className="ip-main">

        <div className="lp-inner ip-breadcrumb-wrap">
          <nav className="ip-breadcrumb" aria-label="Breadcrumb">
            <Link to="/">datathink</Link>
            <span className="ip-breadcrumb-sep" aria-hidden="true">/</span>
            <Link to="/interview-prep">Interview prep</Link>
            <span className="ip-breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">{hero.h1}</span>
          </nav>
        </div>

        {/* ── HERO ─────────────────────────────────────────────── */}
        <section className="lp-section ip-hero">
          <div className="lp-inner ip-hero-inner">
            <p className="lp-eyebrow">{hero.eyebrow}</p>
            <h1 className="ip-h1">{hero.h1}</h1>
            <p className="ip-hero-sub">{hero.sub}</p>
            <div className="ip-hero-actions">
              <Link className="btn btn-primary" to={hero.ctaPrimary.to}>
                {hero.ctaPrimary.label}
              </Link>
              {hero.ctaSecondary.scrollTo ? (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => document.getElementById(hero.ctaSecondary.scrollTo)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                >
                  {hero.ctaSecondary.label}
                </button>
              ) : (
                <Link className="btn btn-secondary" to={hero.ctaSecondary.to}>
                  {hero.ctaSecondary.label}
                </Link>
              )}
            </div>
          </div>
          <button
            type="button"
            className="ip-scroll-cue"
            aria-label="Scroll to content"
            onClick={(e) => e.currentTarget.closest('section')?.nextElementSibling?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
          </button>
        </section>

        {/* ── WHAT INTERVIEWS TEST ─────────────────────────────── */}
        <section className="lp-section lp-section-rule ip-what">
          <div className="lp-inner">
            <Reveal>
              <h2 className="lp-section-h2">{whatSection.h2}</h2>
              <p className="ip-body">{whatSection.body}</p>
            </Reveal>
          </div>
        </section>

        {/* ── TRACKS ───────────────────────────────────────────── */}
        <section id="ip-tracks" className="lp-section lp-section-rule ip-tracks">
          <div className="lp-inner">
            <Reveal>
              <h2 className="lp-section-h2">{tracksHeading(roleData.label, tracks.length)}</h2>
              <p className="ip-body ip-tracks-intro">
                Each maps to a real slice of the {roleData.label.toLowerCase()} interview. Practice on real engines, or pull any one into a timed mock.
              </p>
            </Reveal>
            <div className="ip-track-grid">
              {tracks.map(({ slug, desc }, index) => {
                const meta = TRACK_META[slug];
                if (!meta) return null;
                return (
                  <Reveal key={slug} delay={index * 60}>
                    <div
                      className="ip-track-card"
                      style={{ '--ip-track-color': meta.color }}
                    >
                      <div className="ip-track-card-header">
                        <span
                          className="ip-track-dot"
                          style={{ background: meta.color }}
                          aria-hidden="true"
                        />
                        <span className="ip-track-label">{meta.label}</span>
                      </div>
                      <p className="ip-track-desc">{desc}</p>
                      <div className="ip-track-links">
                        <Link
                          to={`/practice/${slug}`}
                          className="ip-track-link ip-track-link--primary"
                          style={{ color: meta.color }}
                        >
                          Practice →
                        </Link>
                        <Link
                          to={`/sample/${slug}/easy`}
                          className="ip-track-link ip-track-link--secondary"
                        >
                          Free sample
                        </Link>
                      </div>
                    </div>
                  </Reveal>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── REASONING SECTION ────────────────────────────────── */}
        <section className="lp-section lp-section-rule ip-reasoning">
          <div className="lp-inner">
            <Reveal>
              <h2 className="lp-section-h2">{reasoningSection.h2}</h2>
              <div className="ip-reasoning-grid">
                {reasoningSection.points.map((pt) => (
                  <div key={pt.heading} className="ip-reasoning-point">
                    <h3 className="ip-reasoning-heading">{pt.heading}</h3>
                    <p className="ip-reasoning-body">{pt.body}</p>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* ── FAQ ──────────────────────────────────────────────── */}
        <section className="lp-section lp-section-rule ip-faq">
          <div className="lp-inner">
            <Reveal>
              <h2 className="lp-section-h2">{roleData.label} interview questions</h2>
              <div className="ip-faq-list">
                {faq.map((item) => (
                  <FaqItem key={item.q} q={item.q} a={item.a} link={item.link} />
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        {/* ── CLOSING STRIP ────────────────────────────────────── */}
        <section className="lp-section lp-section-rule ip-closing">
          <div className="lp-inner">
            <Reveal className="ip-closing-inner">
              <span className="ip-closing-text">Preparing for a different role?</span>
              <Link to="/interview-prep" className="ip-closing-link">See all roles →</Link>
            </Reveal>
          </div>
        </section>

      </main>

      {/* ── FOOTER ───────────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <span className="landing-footer-copy">&copy; 2026 datathink</span>
          <nav className="landing-footer-links" aria-label="Legal">
            <Link to="/faq">FAQ</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/refund-policy">Refund Policy</Link>
            <Link to="/contact">Contact Us</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
