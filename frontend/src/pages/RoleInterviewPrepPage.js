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
  h2: 'From overview to practice',
  points: [
    {
      heading: 'Start with a sample',
      body: 'Try role-filtered sample questions first, no account required, to get a feel for the track mix and difficulty.',
    },
    {
      heading: 'Build by track',
      body: 'Practice the important tracks one at a time, with real SQL, Python, and Pandas execution where the role calls for it.',
    },
    {
      heading: 'Register when you want progress',
      body: 'A free account keeps your attempts, unlocked questions, learning paths, and mock history in one place.',
    },
  ],
};

const FREE_PRACTICE_FAQ = {
  q: 'Can I start without paying?',
  a: 'Yes. Samples are open without an account, and every easy question is free across all 10 tracks. Pro and Elite unlock medium and hard questions, mock-only inventory, mocks, and deeper analytics.',
  link: { label: 'More details →', to: '/pricing' },
};

const ROLE_CONTENT = {
  'data-engineer': {
    helmet: {
      title: 'Data Engineer Interview Prep: SQL, Python, Spark & Pipelines | datathink',
      description:
        'Data engineer interview prep covering SQL, Python, PySpark, pipelines, and data modeling, with role-specific samples, practice, and mocks.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Engineer',
      h1: 'Data Engineer Interview Prep',
      sub: 'Data engineer interviews usually focus on building reliable data systems. Expect a mix of SQL, Python, distributed processing, pipeline design, and data modeling. The emphasis is on whether you can move data correctly, reason about scale, and explain the design choices behind a warehouse, lakehouse, or production pipeline.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-engineer' },
      ctaSecondary: { label: 'See the 5 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data engineer interviews actually test',
      body: 'A typical data engineer interview checks whether you can work across the data stack: write SQL, solve data-processing problems in Python, reason about Spark jobs, design ETL or ELT pipelines, and choose data models that support analytics. Some companies go deep on coding, others on system design, but the five tracks below cover the common interview surface for the role.',
    },
    tracks: [
      {
        slug: 'python',
        desc: 'Data-processing logic, algorithms, parsing, deduplication, sessionization, and memory-aware transforms.',
        emphasis: 'Primary. Most DE loops include a coding screen; medium-to-hard depth is useful.',
      },
      {
        slug: 'sql',
        desc: 'Joins, aggregation, windows, CTEs, and queries used to validate or transform warehouse data.',
        emphasis: 'Primary. Almost always tested; strong medium-to-hard SQL is expected.',
      },
      {
        slug: 'pyspark',
        desc: 'Distributed data processing, partitions, shuffles, joins, skew, and Spark performance concepts.',
        emphasis: 'Important. Heavier at big-data and platform teams; medium depth covers many screens.',
      },
      {
        slug: 'data-engineering',
        desc: 'Pipeline design, ETL vs ELT, orchestration, CDC, idempotency, backfills, and schema evolution.',
        emphasis: 'Primary. The higher the level, the more this becomes the main interview surface.',
      },
      {
        slug: 'data-modeling',
        desc: 'Dimensional modeling, fact-table grain, SCDs, normalization, and schemas for analytics use cases.',
        emphasis: 'Important. Usually medium depth; deeper for warehouse-heavy roles.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data engineer study for interviews?',
        a: 'Study SQL, Python data-processing, Spark or distributed systems, pipeline design, and data modeling. The exact mix depends on the company, but these five areas cover most data engineer interview loops.',
      },
      {
        q: 'Do data engineer interviews include SQL?',
        a: 'Almost always. SQL is commonly used to test joins, aggregation, windows, CTEs, and whether you can inspect and transform data correctly.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'Data engineer interviews can include coding, but they also test data-system reasoning: pipelines, Spark, schemas, retries, and data quality. datathink keeps the practice tied to those role-specific topics.',
      },
      FREE_PRACTICE_FAQ,
      {
        q: 'How long does it take to prepare?',
        a: 'It depends on your starting point and the interview loop. Start with a few samples, use the track weights to prioritize, then register if you want saved progress, full practice, and mocks.',
      },
    ],
  },

  'data-analyst': {
    helmet: {
      title: 'Data Analyst Interview Prep: SQL, Statistics & Python | datathink',
      description:
        'Data analyst interview prep covering SQL, statistics, Pandas, and Python, with role-specific samples, practice, and mocks.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Analyst',
      h1: 'Data Analyst Interview Prep',
      sub: 'Data analyst interviews usually test whether you can turn business questions into reliable analysis. SQL carries the most weight, followed by statistics, metrics, and practical data manipulation in Pandas or Python. The role is less about memorizing tools and more about producing numbers that can be explained clearly.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-analyst' },
      ctaSecondary: { label: 'See the 5 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data analyst interviews actually test',
      body: 'A typical data analyst interview includes SQL questions, metric interpretation, basic statistics, and sometimes a Python or Pandas exercise. You may be asked to write a query, explain a result, reason about uncertainty, or manipulate a small dataset. The five tracks below show the usual weighting for analyst roles.',
    },
    tracks: [
      {
        slug: 'sql',
        desc: 'Joins, aggregation, windows, CTEs, cohort queries, and metric-building over relational data.',
        emphasis: 'Primary. This is the core analyst screen; depth through hard matters most.',
      },
      {
        slug: 'statistics',
        desc: 'Descriptive statistics, probability, confidence intervals, hypothesis tests, and interpreting noisy results.',
        emphasis: 'Important. Conceptual-to-medium strength is usually enough for analyst roles.',
      },
      {
        slug: 'product-sense',
        desc: 'Turning a business question into the right metric, diagnosing why a number moved, reading a funnel, and judging whether a result is worth acting on.',
        emphasis: 'Important. Metrics and product-judgment questions increasingly appear in analyst screens.',
      },
      {
        slug: 'pandas',
        desc: 'DataFrame filtering, grouping, reshaping, cleaning, and quick analysis outside SQL.',
        emphasis: 'Supporting. Medium fluency covers most screens that include it.',
      },
      {
        slug: 'python',
        desc: 'Basic scripting, parsing, counting, and automation around analysis workflows.',
        emphasis: 'Supporting. Easy-to-medium is usually enough unless the role is Python-heavy.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data analyst study for interviews?',
        a: 'Prioritize SQL first, then applied statistics, metrics, and practical Pandas or Python. Most analyst interviews are trying to see whether you can compute, explain, and trust a result.',
      },
      {
        q: 'How much SQL do data analyst interviews need?',
        a: 'A lot. SQL is usually the highest-weight track for data analyst interviews because it tests joins, aggregation, windows, and metric construction.',
      },
      {
        q: 'Do analyst interviews include statistics?',
        a: 'Often. Statistics questions are usually applied: interpreting a confidence interval, understanding sampling noise, or deciding whether a result is meaningful.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'Most analyst rounds are not algorithm puzzles. datathink focuses on SQL, metrics, statistics, and data manipulation, which are the areas most analyst interviews actually cover.',
      },
      FREE_PRACTICE_FAQ,
    ],
  },

  'analytics-engineer': {
    helmet: {
      title: 'Analytics Engineer Interview Prep: SQL, dbt & Data Modeling | datathink',
      description:
        'Analytics engineer interview prep covering SQL, data modeling, dbt-style transformations, Pandas, and Python, with samples and mocks.',
    },
    hero: {
      eyebrow: 'Interview prep · Analytics Engineer',
      h1: 'Analytics Engineer Interview Prep',
      sub: 'Analytics engineer interviews sit between analysis and data engineering. They usually emphasize SQL, data modeling, transformation design, and dbt-style thinking. You are expected to understand how raw data becomes trusted tables, metrics, and semantic layers that analysts and stakeholders can use.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=analytics-engineer' },
      ctaSecondary: { label: 'See the 4 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What analytics engineer interviews actually test',
      body: 'A typical analytics engineer interview tests advanced SQL, dimensional modeling, transformation quality, and the ability to reason about data definitions. Some loops include dbt concepts directly; others test the same ideas through modeling and SQL design questions. Python and Pandas are useful supporting skills, but SQL and modeling carry the most weight.',
    },
    tracks: [
      {
        slug: 'sql',
        desc: 'Transformation SQL, windows, CTEs, incremental logic, tests, and metric definitions.',
        emphasis: 'Primary. This is the main technical screen; hard-level depth pays off.',
      },
      {
        slug: 'data-modeling',
        desc: 'Grain, star schemas, SCDs, normalization trade-offs, conformed dimensions, and semantic-layer design.',
        emphasis: 'Primary. Medium-to-hard modeling is central to the role.',
      },
      {
        slug: 'pandas',
        desc: 'DataFrame checks, reshaping, validation, and one-off transformations around the warehouse layer.',
        emphasis: 'Supporting. Easy-to-medium is usually sufficient.',
      },
      {
        slug: 'python',
        desc: 'Scripting, data checks, parsing, lightweight automation, and transformation logic.',
        emphasis: 'Often a coding round. Medium is the realistic bar.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should an analytics engineer study for interviews?',
        a: 'Focus on advanced SQL, data modeling, and transformation design. dbt-specific knowledge helps, but many interviews test the same ideas through SQL, model grain, tests, and metric definitions.',
      },
      {
        q: 'Do analytics engineer interviews include data modeling?',
        a: 'Yes. Data modeling is usually a high-weight area: grain, keys, SCDs, star schemas, denormalization, and semantic-layer decisions.',
      },
      {
        q: 'How is SQL tested for analytics engineers?',
        a: 'SQL is tested as transformation work, not just answer retrieval. Interviewers look for correctness, maintainability, readable CTEs, window functions, and metric logic.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'Analytics engineering interviews are closer to SQL and modeling design than algorithm puzzles. datathink focuses on the transformation and data-modeling skills the role actually uses.',
      },
      FREE_PRACTICE_FAQ,
    ],
  },

  'data-scientist': {
    helmet: {
      title: 'Data Scientist Interview Prep: ML, Statistics & Experimentation | datathink',
      description:
        'Data scientist interview prep covering ML fundamentals, statistics, experimentation, Python, Pandas, and SQL, with samples and mocks.',
    },
    hero: {
      eyebrow: 'Interview prep · Data Scientist',
      h1: 'Data Scientist Interview Prep',
      sub: 'Data scientist interviews usually combine quantitative reasoning, machine learning, experimentation, and hands-on data work. The exact loop varies by company, but most roles expect ML fundamentals, statistics, Python or Pandas, SQL, and the ability to explain how a model or experiment supports a decision.',
      ctaPrimary: { label: 'Try a free sample →', to: '/sample?role=data-scientist' },
      ctaSecondary: { label: 'See the 7 tracks ↓', scrollTo: 'ip-tracks' },
    },
    whatSection: {
      h2: 'What data scientist interviews actually test',
      body: 'A typical data scientist interview can include ML concepts, statistical inference, A/B testing, SQL, Python, and Pandas. Product-focused roles often give more weight to experimentation and metrics; applied ML roles usually go deeper on model evaluation, leakage, and production trade-offs. The seven tracks below cover the common technical surface.',
    },
    tracks: [
      {
        slug: 'ml-fundamentals',
        desc: 'Bias-variance, model selection, evaluation metrics, leakage, class imbalance, calibration, and drift.',
        emphasis: 'Primary. Medium-to-hard conceptual depth matters more than algorithm-name recall.',
      },
      {
        slug: 'statistics',
        desc: 'Probability, inference, confidence intervals, hypothesis testing, regression interpretation, and uncertainty.',
        emphasis: 'Primary. Strong statistics is expected across most DS loops.',
      },
      {
        slug: 'experimentation',
        desc: 'A/B testing, power, sample-ratio mismatch, multiple testing, causal reasoning, and experiment interpretation.',
        emphasis: 'Primary for product DS. Important for many generalist DS roles too.',
      },
      {
        slug: 'product-sense',
        desc: 'Metric selection, diagnosing why a number moved, conflicting-metric trade-offs, gaming-robustness, and ship / no-ship judgment under stakeholder pressure.',
        emphasis: 'Primary for product DS. A near-universal round for product-focused data scientists.',
      },
      {
        slug: 'python',
        desc: 'Coding for data processing, algorithms, parsing, counting, and modeling-adjacent workflows.',
        emphasis: 'Important. Medium mastery is usually enough unless the role is coding-heavy.',
      },
      {
        slug: 'pandas',
        desc: 'EDA, grouping, reshaping, cleaning, datetime operations, and feature-prep style transformations.',
        emphasis: 'Important. Medium fluency covers most hands-on DS screens.',
      },
      {
        slug: 'sql',
        desc: 'Querying, joining, cohort selection, metric definitions, and pulling data for analysis or modeling.',
        emphasis: 'Expected almost everywhere. Easy-to-medium, deeper at SQL-heavy shops.',
      },
    ],
    reasoningSection: SHARED_REASONING,
    faq: [
      {
        q: 'What should a data scientist study for interviews?',
        a: 'Study ML fundamentals, statistics, experimentation, Python, Pandas, and SQL. The weight varies by role type: product DS leans more on experiments and metrics, while applied ML leans more on modeling and evaluation.',
      },
      {
        q: 'Do data scientist interviews include statistics and experimentation?',
        a: 'Often, especially for product and decision-science roles. Expect inference, A/B test design, power, multiple testing, and interpretation of results.',
      },
      {
        q: 'Is machine learning enough on its own?',
        a: 'Usually not. Data scientist interviews also test statistics, SQL, data manipulation, experimentation, and whether you can explain the reasoning behind a model or result.',
      },
      {
        q: 'How is this different from LeetCode-style prep?',
        a: 'Some DS interviews include coding, but the role also requires ML, statistics, experimentation, SQL, and Pandas. datathink weights practice around that broader data-science interview mix.',
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
                The track weights below show what to prioritize first for a {roleData.label.toLowerCase()} interview. Try a free sample, then register when you want saved progress, full practice, and mocks.
              </p>
            </Reveal>
            <div className="ip-track-grid">
              {tracks.map(({ slug, desc, emphasis }, index) => {
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
                      {emphasis && (
                        <p className="ip-track-emphasis">
                          <span className="ip-track-emphasis-label">Interview weight</span>
                          {emphasis}
                        </p>
                      )}
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
            <a href="/guides">Guides</a>
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
