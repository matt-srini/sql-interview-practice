import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useTopic } from '../contexts/TopicContext';
import { useCatalogCounts } from '../contexts/CatalogCountsContext';
import { useAuth } from '../contexts/AuthContext';

import PathProgressCard from '../components/PathProgressCard';
import TierBanner from '../components/TierBanner';
import UpgradeButton from '../components/UpgradeButton';
import Skeleton from '../components/Skeleton';
import { summarizeQuestionForms } from '../questionFormLabel';
import { pickNextUpQuestionId, pickFirstQuestionId } from '../utils/catalogNav';

const HUB_DESC_TEMPLATES = {
  sql:              n => `Your SQL practice workspace. ${n} questions by difficulty — joins, aggregations, window functions, and CTEs with instant DuckDB execution and solution analysis.`,
  python:           n => `Your Python practice workspace. ${n} algorithm and data processing questions with automated test case feedback and step-by-step hints.`,
  'pandas':    n => `Your Pandas practice workspace. ${n} DataFrame manipulation questions with live execution and side-by-side output comparison.`,
  pyspark:          n => `Your PySpark practice workspace. ${n} reasoning prompts across predict-output, debug, and scenario formats covering Spark behavior and performance trade-offs.`,
  'data-engineering': n => `Your Data Engineering practice workspace. ${n} questions covering ETL, orchestration, streaming, and system design.`,
  'data-modeling':  n => `Your Data Modeling practice workspace. ${n} questions covering dimensional modeling, normalization, and dbt design.`,
  statistics:       n => `Your Statistics practice workspace. ${n} conceptual and numerical questions covering probability, inference, and A/B testing.`,
  'ml-fundamentals': n => `Your ML Fundamentals practice workspace. ${n} questions covering bias-variance, evaluation metrics, and production ML.`,
  experimentation:  n => `Your Experimentation practice workspace. ${n} questions covering A/B testing, power analysis, and causal inference.`,
  'product-sense':  n => `Your Product Sense practice workspace. ${n} questions covering metric design, diagnosis, trade-offs, and ship decisions.`,
};

export default function TrackHubPage() {
  const { topic, meta } = useTopic();
  const trackCounts = useCatalogCounts();
  const trackTotal = trackCounts[topic]?.total ?? 0;
  const hubDescription = (HUB_DESC_TEMPLATES[topic]?.(trackTotal) ?? meta.description);
  const { catalog, loading, error } = useCatalog();
  const navigate = useNavigate();
  const { user } = useAuth();

  const nextId = useMemo(() => pickNextUpQuestionId(catalog), [catalog]);
  const firstId = useMemo(() => pickFirstQuestionId(catalog), [catalog]);
  const continueId = nextId ?? firstId;
  const questionFormSummary = useMemo(
    () => summarizeQuestionForms(catalog?.groups ?? []),
    [catalog]
  );

  const totalSolved = useMemo(() => {
    if (!catalog) return 0;
    return (catalog.groups ?? []).reduce((acc, g) => acc + g.questions.filter((q) => q.state === 'solved').length, 0);
  }, [catalog]);

  const totalQuestions = useMemo(() => {
    if (!catalog) return trackTotal;
    return (catalog.groups ?? []).reduce((acc, g) => acc + g.questions.length, 0);
  }, [catalog, meta]);

  const mediumSolved = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'medium');
    return g ? g.questions.filter(q => q.state === 'solved').length : 0;
  }, [catalog]);
  const mediumTotal = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'medium');
    return g ? g.questions.length : 0;
  }, [catalog]);
  const hardTotal = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'hard');
    return g ? g.questions.length : 0;
  }, [catalog]);

  // Milestone detection
  const mediumComplete = mediumTotal > 0 && mediumSolved >= mediumTotal;
  const hasLockedQuestions = useMemo(
    () => catalog?.groups?.some(g => g.questions.some(q => q.state === 'locked')) ?? false,
    [catalog]
  );
  // User has exhausted all accessible questions (nothing left to solve right now)
  const allAccessibleSolved = nextId === null && totalSolved > 0;

  const overallPct = totalQuestions > 0 ? totalSolved / totalQuestions : 0;

  const [topicPaths, setTopicPaths] = useState([]);
  const [duckdbTipOpen, setDuckdbTipOpen] = useState(false);
  useEffect(() => {
    api.get('/paths').then(r => setTopicPaths(r.data.filter(p => p.topic === topic))).catch(() => {});
  }, [topic]);

  // Sort paths: incomplete first, then by (level, display_order) — foundational
  // before intermediate before advanced; within each level, by author-curated
  // display_order (1-based, lower = earlier in the conceptual walk).
  const sortedPaths = useMemo(() => {
    const levelOrder = { foundational: 0, intermediate: 1, advanced: 2 };
    return [...topicPaths].sort((a, b) => {
      const aComplete = a.question_count > 0 && a.solved_count === a.question_count;
      const bComplete = b.question_count > 0 && b.solved_count === b.question_count;
      if (aComplete !== bComplete) return aComplete ? 1 : -1;
      const levelDelta = (levelOrder[a.level] ?? 3) - (levelOrder[b.level] ?? 3);
      if (levelDelta !== 0) return levelDelta;
      return (a.display_order ?? 999) - (b.display_order ?? 999);
    });
  }, [topicPaths]);

  // Pick the top recommendation: first incomplete accessible path in role order.
  const recommendedPath = useMemo(() => sortedPaths.find(
    p => p.accessible && !(p.question_count > 0 && p.solved_count === p.question_count)
  ) ?? null, [sortedPaths]);

  function getPathLabel(path) {
    if (!path) return null;
    if (path.level === 'foundational' && path.solved_count === 0) return 'Start here';
    if (path.level === 'foundational') return 'Continue';
    if (path.solved_count > 0) return 'Continue';
    return 'Recommended next';
  }

  function handleContinue() {
    if (continueId) {
      navigate(`/practice/${topic}/questions/${continueId}`);
    }
  }

  if (loading) {
    return (
      <main className="container track-hub-page" style={{ paddingTop: '2rem' }}>
        <div className="track-hub-loading" aria-label={`Loading ${meta.label} questions`}>
          <Skeleton width="11rem" height="0.95rem" />
          <Skeleton width="20rem" height="2rem" />
          <Skeleton width="90%" height="0.85rem" />
          <Skeleton width="100%" height="10rem" />
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="container track-hub-page" style={{ paddingTop: '2rem' }}>
        <p className="error-box">{error}</p>
      </main>
    );
  }

  return (
    <main className="container track-hub-page">
      <Helmet>
        <title>{meta.label} Interview Practice — datathink</title>
        <meta name="description" content={hubDescription} />
        <meta property="og:title" content={`${meta.label} Interview Practice — datathink`} />
        <meta property="og:description" content={hubDescription} />
        <meta property="og:url" content={`https://datathink.co/practice/${topic}`} />
        <meta property="og:image" content="https://datathink.co/og-image.png?v=4" />
        <link rel="canonical" href={`https://datathink.co/practice/${topic}`} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://datathink.co/og-image.png?v=4" />
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Course",
          "name": `${meta.label} Interview Practice`,
          "description": hubDescription,
          "url": `https://datathink.co/practice/${topic}`,
          "numberOfLessons": trackTotal || undefined,
          "provider": { "@type": "Organization", "name": "datathink", "url": "https://datathink.co" }
        })}</script>
      </Helmet>
      <div className="track-hub-inner">
        <TierBanner plan={user?.plan ?? 'free'} returnTo={{ path: `/practice/${topic}`, label: `${meta.label} Practice` }} />
        <div className="track-hub-header">
          <div className="track-hub-title-row">
            <h2 className="track-hub-title">{meta.label} Practice</h2>
            <span className="track-hub-tagline">{meta.tagline}</span>
          </div>
          <p className="track-hub-desc">{meta.description}</p>
          {topic === 'sql' && (
            <>
              <p className="track-hub-db-note">
                Queries run on DuckDB, so a few functions work differently from Postgres or MySQL.{' '}
                <button className="thub-db-link-btn" onClick={() => setDuckdbTipOpen(true)}>
                  Quick reference
                </button>
              </p>
              {duckdbTipOpen && (
                <div className="duckdb-tip-overlay" role="dialog" aria-modal="true" aria-label="DuckDB syntax reference" onClick={() => setDuckdbTipOpen(false)}>
                  <div className="duckdb-tip-modal" onClick={(e) => e.stopPropagation()}>
                    <div className="duckdb-tip-header">
                      <span className="duckdb-tip-title">DuckDB syntax reference</span>
                      <button className="duckdb-tip-close" onClick={() => setDuckdbTipOpen(false)} aria-label="Close">×</button>
                    </div>
                    <div className="duckdb-tip-table-wrap">
                      <table className="duckdb-tip-table">
                        <thead>
                          <tr><th>Operation</th><th>Use in DuckDB</th><th>Not this</th></tr>
                        </thead>
                        <tbody>
                          <tr><td>Date → string</td><td><code>STRFTIME('%Y-%m', date)</code></td><td><code>TO_CHAR(date, 'YYYY-MM')</code></td></tr>
                          <tr><td>String → date</td><td><code>STRPTIME(str, '%Y-%m-%d')</code></td><td><code>TO_DATE</code></td></tr>
                          <tr><td>Date bucketing</td><td><code>DATE_TRUNC('month', date)</code></td><td>—</td></tr>
                          <tr><td>Date arithmetic</td><td><code>date::DATE + INTERVAL 7 DAY</code></td><td><code>DATE_ADD</code></td></tr>
                          <tr><td>String concat</td><td><code>a || ' ' || b</code></td><td><code>CONCAT</code> (non-portable)</td></tr>
                          <tr><td>NULL-last sort</td><td><code>ORDER BY col ASC NULLS LAST</code></td><td>—</td></tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          {questionFormSummary.length > 1 && (
            <div className="track-hub-form-strip" aria-label="Question forms in this track">
              <span className="track-hub-form-strip-label">What you'll practice</span>
              <div className="track-hub-form-strip-chips">
                {questionFormSummary.map((item) => (
                  <span key={item.label} className="track-hub-form-chip">
                    <span>{item.label}</span>
                    <span className="track-hub-form-chip-count">{item.count}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="thub-stat-card" style={{ '--track-color': meta.color }}>
          <div className="thub-top-row">
            <div className="thub-count-line">
              <span className="thub-count-solved">{totalSolved}</span>
              <span className="thub-count-sep">/</span>
              <span className="thub-count-total">{totalQuestions}</span>
              <span className="thub-count-label">solved</span>
              <span className="thub-count-divider" aria-hidden="true" />
              <span className="thub-count-pct">{Math.round(overallPct * 100)}%</span>
            </div>
            {!allAccessibleSolved ? (
              <button className="thub-cta-btn" onClick={handleContinue}>
                {totalSolved > 0 ? 'Continue →' : 'Start →'}
              </button>
            ) : hasLockedQuestions ? (
              <UpgradeButton tier="pro" label="Unlock more" compact source="hub_allsolved" />
            ) : (
              <Link to="/" className="btn btn-secondary btn-compact">Explore tracks →</Link>
            )}
          </div>

          <div className="thub-bar-track">
            <div className="thub-bar-fill" style={{ width: `${overallPct * 100}%` }} />
          </div>

          {catalog?.groups?.length > 0 && (
            <div className="thub-diff-strip">
              {catalog.groups.map((g) => {
                const solved = g.questions.filter((q) => q.state === 'solved').length;
                const total = g.questions.length;
                const pct = total > 0 ? (solved / total) * 100 : 0;
                return (
                  <div key={g.difficulty} className="thub-diff-item">
                    <span className={`thub-diff-dot thub-diff-dot--${g.difficulty}`} />
                    <span className="thub-diff-label">{g.difficulty}</span>
                    <div className="thub-diff-mini-bar">
                      <div className="thub-diff-mini-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="thub-diff-frac">{solved}/{total}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* All-accessible-solved milestone — celebrates completion before showing the upgrade wall */}
        {allAccessibleSolved && (user?.plan === 'free' || user?.plan === 'pro') && hasLockedQuestions && (
          <div className="track-hub-milestone track-hub-milestone-upgrade">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏁</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                You've solved every accessible {meta.label} question!
              </p>
              <p className="track-hub-milestone-desc">
                {user?.plan === 'free'
                  ? `That's ${totalSolved} questions down. Upgrade to Pro for the full ${hardTotal > 0 ? `hard track (${hardTotal} questions)` : 'question bank'} and keep building.`
                  : `That's real depth. Upgrade to Elite for full access and unlimited mock interviews.`}
              </p>
              <div className="track-hub-milestone-actions">
                {user?.plan === 'free' && (
                  <UpgradeButton tier="pro" label="Unlock Pro — all medium & hard" compact source="hub_milestone_allsolved" />
                )}
                <UpgradeButton tier="elite" label="Unlock Elite" compact source="hub_milestone_allsolved_elite" />
              </div>
            </div>
          </div>
        )}

        {/* Full track completion — for Pro/Elite users who've solved everything */}
        {allAccessibleSolved && !hasLockedQuestions && totalSolved > 0 && (
          <div className="track-hub-milestone track-hub-milestone-complete">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏆</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                Track complete — all {totalSolved} {meta.label} questions solved!
              </p>
              <p className="track-hub-milestone-desc">
                Outstanding. Take a mock interview to put it under pressure, or pick up another track.
              </p>
              <div className="track-hub-milestone-actions">
                <Link to="/mock" className="btn btn-primary btn-compact">Take a mock interview →</Link>
                <Link to="/" className="btn btn-secondary btn-compact">Explore other tracks</Link>
              </div>
            </div>
          </div>
        )}

        {/* Medium-complete milestone — all medium solved, hard still locked on free */}
        {!allAccessibleSolved && mediumComplete && (user?.plan === 'free') && (
          <div className="track-hub-milestone track-hub-milestone-tier">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏆</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                You've mastered all {mediumTotal} medium questions!
              </p>
              <p className="track-hub-milestone-desc">
                Hard questions require a Pro or Elite plan. <Link to="/pricing" state={{ returnTo: { path: `/practice/${topic}`, label: `${meta.label} Practice` } }} className="track-hub-inline-link">See pricing →</Link>
              </p>
              <div className="track-hub-milestone-actions">
                <UpgradeButton tier="pro" label="Unlock all hard questions" compact source="hub_milestone_medium_complete" />
              </div>
            </div>
          </div>
        )}

        {sortedPaths.length > 0 && (
          <div className="trackhub-twoways">
            <h3 className="trackhub-twoways-heading">Two ways to work {meta.label}</h3>
            <div className="trackhub-twoways-grid">
              <div className="trackhub-twoways-item">
                <span className="trackhub-twoways-item-label">Practice — the full catalog</span>
                <span className="trackhub-twoways-item-desc">
                  {totalQuestions} questions, solved in any order from the list on the left.
                </span>
                <span className="trackhub-twoways-point">
                  ↑ Click <strong>{totalSolved > 0 ? 'Continue' : 'Start'}</strong> above to {totalSolved > 0 ? 'resume' : 'begin'}
                </span>
              </div>
              <Link to={`/learn/${topic}`} className="trackhub-twoways-item trackhub-twoways-item--link" style={{ '--tw-color': meta.color }}>
                <span className="trackhub-twoways-item-label">Learning paths — guided routes</span>
                <span className="trackhub-twoways-item-desc">
                  {sortedPaths.length} ordered walk{sortedPaths.length === 1 ? '' : 's'} — every concept, in sequence.
                </span>
                <span className="trackhub-twoways-point">
                  ↓ Choose a <strong>path</strong> below
                </span>
              </Link>
            </div>
            <p className="trackhub-twoways-caption">
              Same questions — solve one in either place and it's marked done in both. You never redo a question.
            </p>
          </div>
        )}

        {sortedPaths.length > 0 && (
          <section className="trackhub-paths">
            <div className="trackhub-paths-header">
              <h3 className="trackhub-paths-title">Learning paths</h3>
              {sortedPaths.length > 2 && (
                <Link to={`/learn/${topic}`} className="trackhub-paths-viewall">
                  View all {sortedPaths.length} →
                </Link>
              )}
            </div>
            <div className="trackhub-paths-grid">
              {sortedPaths.slice(0, 2).map(p => (
                <PathProgressCard
                  key={p.slug}
                  path={p}
                  compact
                  recommendationLabel={p.slug === recommendedPath?.slug ? getPathLabel(p) : null}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
