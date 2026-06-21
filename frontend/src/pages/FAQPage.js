import { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Topbar from '../components/Topbar';
import { useAuth } from '../contexts/AuthContext';

const PAID_PLANS = ['pro', 'elite', 'lifetime_pro', 'lifetime_elite'];

const FAQ_JSON_LD = [
  {
    "@type": "Question",
    "name": "Is datathink free to use?",
    "acceptedAnswer": { "@type": "Answer", "text": "Yes. All easy questions across all nine tracks are free, including for visitors without an account. Medium and hard questions unlock progressively as you solve more easy questions. No credit card required." }
  },
  {
    "@type": "Question",
    "name": "Can I practice without creating an account?",
    "acceptedAnswer": { "@type": "Answer", "text": "Yes. All easy questions and sample questions are accessible without registering. Your progress is tracked in a browser cookie that lasts 30 days — closing the browser tab won't reset it. You'll lose progress only if you clear browser cookies, switch to a different browser or device, or haven't visited in over 30 days. Create a free account to save progress permanently across all your devices." }
  },
  {
    "@type": "Question",
    "name": "What SQL topics are covered?",
    "acceptedAnswer": { "@type": "Answer", "text": "SQL questions spanning aggregation, window functions, CTEs, joins, subqueries, cohort analysis, period-over-period analysis, query optimization, string and date functions, set operations, recursive CTEs, and more — all executed against real datasets using DuckDB with instant feedback and solution analysis." }
  },
  {
    "@type": "Question",
    "name": "What tracks are available?",
    "acceptedAnswer": { "@type": "Answer", "text": "Nine tracks: SQL, Python algorithms, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation. Each has easy, medium, and hard tiers. Code tracks (SQL, Python, Pandas) use a live execution environment; the remaining tracks use conceptual, scenario, predict-output, and debug formats. Beyond the free practice catalog, every track also has a deep pool of mock-exclusive questions — over 1,000 across the nine tracks, available only on Pro and Elite — reserved for mock interviews and never shown in the practice bank." }
  },
  {
    "@type": "Question",
    "name": "Which companies' interview questions are covered?",
    "acceptedAnswer": { "@type": "Answer", "text": "SQL questions are tagged with companies including Amazon, Meta, Google, Stripe, Netflix, Shopify, LinkedIn, and more. You can filter by company in the SQL practice workspace sidebar." }
  },
  {
    "@type": "Question",
    "name": "How do question unlocks work?",
    "acceptedAnswer": { "@type": "Answer", "text": "Easy questions are available to everyone from the start. Medium and hard questions unlock as you solve more — the more you practice, the more you unlock. Pro and Elite subscribers get immediate access to all questions." }
  },
  {
    "@type": "Question",
    "name": "What are mock sessions?",
    "acceptedAnswer": { "@type": "Answer", "text": "Mocks are timed interview simulations in three modes: benchmark (fixed-shape readiness signal), custom drill (1–5 questions, 10–90 min), and Interview Loop (Elite-only chain-driven follow-up sessions). On Pro and Elite, mocks draw from a dedicated pool of over 1,000 mock-exclusive questions — content reserved for mock interviews that never appears in the practice catalog, so every mock is a genuine unseen test. Free users get one easy benchmark per rolling 7 days, drawn from the practice pool. Pro users get three benchmarks per day plus three custom drills per day across difficulties. Elite users get unlimited sessions plus Interview Loop, focus-mode targeting, readiness analytics, and coaching debriefs." }
  },
  {
    "@type": "Question",
    "name": "What is the difference between Free, Pro, and Elite?",
    "acceptedAnswer": { "@type": "Answer", "text": "Free gives access to all easy questions, progressive medium/hard unlocks as you practice, and one easy benchmark per rolling 7 days. Pro unlocks every question immediately, adds the mock-only question pool, and provides 3 benchmarks plus 3 custom drills per day, detailed history, and weakest-concept drill recommendations. Elite includes everything in Pro plus Interview Loop mode, focus-mode targeting, per-dimension weak-spot detection, readiness scoring, study plans, coaching debriefs, and unlimited sessions. Visit datathink.co for the full pricing comparison." }
  }
];

export default function FAQPage({ isModal = false }) {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const userPlan = user?.plan ?? 'free';
  const isPaid = PAID_PLANS.includes(userPlan);

  // Closing the modal returns to the background page (the landing footer) and
  // keeps scroll position — it does not jump to the top.
  const handleClose = () => {
    const bg = location.state?.backgroundLocation;
    navigate(bg ? `${bg.pathname}${bg.search}` : '/', { replace: true, state: { preserveScroll: true } });
  };

  useEffect(() => {
    if (!isModal) window.scrollTo(0, 0);
  }, [isModal]);

  const pricingLink = isPaid
    ? <Link to="/account" className="faq-link">Manage your plan →</Link>
    : <Link to="/pricing" className="faq-link">Compare plans &amp; pricing →</Link>;

  const content = (
    <div className="auth-card policy-card" role="main">
      {isModal && (
        <button type="button" className="policy-exit" onClick={handleClose} aria-label="Close FAQ">X</button>
      )}
      <h1 className="auth-card-title">Frequently Asked Questions</h1>
      <div className="policy-body">
        <dl className="faq-list">
          <div className="faq-item">
            <dt className="faq-q">Is datathink free to use?</dt>
            <dd className="faq-a">Yes. All easy questions across all nine tracks are free, including for visitors without an account. Medium and hard questions unlock progressively as you solve more easy questions. No credit card required.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">Can I practice without creating an account?</dt>
            <dd className="faq-a">Yes. All easy questions and sample questions are accessible without registering. Your progress is tracked in a browser cookie that lasts 30 days — closing the browser tab won't reset it. You'll lose progress only if you clear browser cookies, switch to a different browser or device, or haven't visited in over 30 days. <Link to="/auth" className="faq-link">Create a free account</Link> to save progress permanently across all your devices.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">What SQL topics are covered?</dt>
            <dd className="faq-a">SQL questions spanning aggregation, window functions, CTEs, joins, subqueries, cohort analysis, period-over-period analysis, query optimization, string and date functions, set operations, recursive CTEs, and more — all executed against real datasets using DuckDB with instant feedback and solution analysis.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">What tracks are available?</dt>
            <dd className="faq-a">Nine tracks: SQL, Python algorithms, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation. Each has easy, medium, and hard tiers. Code tracks (SQL, Python, Pandas) use a live execution environment; the remaining tracks use conceptual, scenario, predict-output, and debug formats. Beyond the free practice catalog, every track also has a deep pool of <strong>mock-exclusive questions — over 1,000 across the nine tracks</strong>, available only on Pro and Elite, reserved for mock interviews and never shown in the practice bank.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">Which companies' interview questions are covered?</dt>
            <dd className="faq-a">SQL questions are tagged with companies including Amazon, Meta, Google, Stripe, Netflix, Shopify, LinkedIn, and more. You can filter by company in the SQL practice workspace sidebar.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">How do question unlocks work?</dt>
            <dd className="faq-a">Easy questions are available to everyone from the start. Medium and hard questions unlock as you solve more — the more you practice, the more you unlock. Pro and Elite subscribers get immediate access to all questions.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">What are mock sessions?</dt>
            <dd className="faq-a">Mocks are timed interview simulations in three modes: <strong>benchmark</strong> (fixed-shape readiness signal), <strong>custom drill</strong> (1–5 questions, 10–90 min), and <strong>Interview Loop</strong> (Elite-only chain-driven follow-up sessions). On Pro and Elite, mocks draw from a <strong>dedicated pool of 1,000+ mock-exclusive questions</strong> — reserved for mock interviews and never shown in the practice catalog, so every mock is a genuine unseen test. Free users get one easy benchmark per rolling 7 days, drawn from the practice pool. Pro users get three benchmarks per day plus three custom drills per day across difficulties. Elite users get unlimited sessions plus Interview Loop, focus-mode targeting, readiness analytics, and coaching debriefs.</dd>
          </div>
          <div className="faq-item">
            <dt className="faq-q">What is the difference between Free, Pro, and Elite?</dt>
            <dd className="faq-a">
              Free gives access to all easy questions, progressive medium/hard unlocks as you practice, and one easy benchmark per rolling 7 days. Pro unlocks every question immediately, adds the mock-only question pool, and provides 3 benchmarks plus 3 custom drills per day, detailed history, and weakest-concept drill recommendations. Elite includes everything in Pro plus Interview Loop mode, focus-mode targeting, per-dimension weak-spot detection, readiness scoring, study plans, coaching debriefs, and unlimited sessions.{' '}
              {pricingLink}
            </dd>
          </div>
        </dl>
      </div>
      <div className="policy-footer-nav">
        {isModal ? (
          <button type="button" className="btn btn-secondary" onClick={handleClose}>Close</button>
        ) : (
          <Link to="/" className="btn btn-secondary">Back to home</Link>
        )}
      </div>
    </div>
  );

  if (isModal) return content;

  return (
    <div className="auth-page">
      <Helmet>
        <title>Frequently Asked Questions — datathink</title>
        <meta name="description" content="Common questions about datathink — free access, no-account practice, SQL and Python topics, company coverage, question unlocks, mock sessions, and plan differences." />
        <meta property="og:title" content="Frequently Asked Questions — datathink" />
        <meta property="og:description" content="Common questions about datathink — free access, no-account practice, SQL and Python topics, company coverage, question unlocks, mock sessions, and plan differences." />
        <meta property="og:url" content="https://datathink.co/faq" />
        <link rel="canonical" href="https://datathink.co/faq" />
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": FAQ_JSON_LD
        })}</script>
      </Helmet>
      <Topbar />
      <main className="auth-main">
        {content}
      </main>
    </div>
  );
}
