import { useEffect, useState, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { TRACK_SLUGS, TRACK_LABELS } from '../trackRegistry';
import { useCatalogCounts } from '../contexts/CatalogCountsContext';
import Topbar from '../components/Topbar';
import Skeleton from '../components/Skeleton';
import UpgradeButton from '../components/UpgradeButton';

// Role → tracks filter for Track overview section
const ROLE_TRACK_FILTERS = [
  { id: 'analyst',   label: 'Data Analyst',       tracks: ['sql', 'statistics', 'pandas', 'python'] },
  { id: 'engineer',  label: 'Data Engineer',      tracks: ['python', 'sql', 'pyspark', 'data-engineering', 'data-modeling'] },
  { id: 'ae',        label: 'Analytics Eng',      tracks: ['sql', 'data-modeling', 'pandas', 'python'] },
  { id: 'scientist', label: 'Data Scientist',     tracks: ['ml-fundamentals', 'statistics', 'experimentation', 'python', 'sql'] },
];

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatDateLabel(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const itemDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((today - itemDate) / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function groupActivityByDate(items) {
  const groups = [];
  let currentLabel = null;
  for (const item of items) {
    const label = formatDateLabel(item.solved_at);
    if (label !== currentLabel) {
      groups.push({ label, items: [item] });
      currentLabel = label;
    } else {
      groups[groups.length - 1].items.push(item);
    }
  }
  return groups;
}

function AccuracyBar({ pct, color }) {
  const clampedPct = Math.max(0, Math.min(100, Math.round(pct * 100)));
  const barColor = clampedPct < 40 ? 'var(--danger)' : clampedPct < 65 ? 'var(--warning)' : 'var(--success)';
  return (
    <div className="db-accuracy-bar-wrap">
      <div className="db-accuracy-bar-track">
        <div className="db-accuracy-bar-fill" style={{ width: `${clampedPct}%`, background: barColor }} />
      </div>
      <span className="db-accuracy-bar-label" style={{ color: barColor }}>{clampedPct}%</span>
    </div>
  );
}

function ReadinessModal({ onClose }) {
  const handleKey = useCallback((e) => { if (e.key === 'Escape') onClose(); }, [onClose]);
  useEffect(() => {
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [handleKey]);

  return (
    <div className="readiness-modal-backdrop" onClick={onClose} role="presentation">
      <div className="readiness-modal" role="dialog" aria-modal="true" aria-label="Interview Readiness Score" onClick={e => e.stopPropagation()}>
        <div className="readiness-modal-header">
          <div>
            <span className="readiness-modal-kicker">Elite feature</span>
            <h3 className="readiness-modal-title">Interview Readiness Score</h3>
          </div>
          <button className="readiness-modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <p className="readiness-modal-desc">
          A <strong>0–100 score per track</strong> that tells you how interview-ready you are right now — updated after every practice session and mock. Practice alone caps at "Getting there"; reaching the top bands requires timed mock performance.
        </p>
        <div className="readiness-modal-signals">
          {[
            { label: 'Practice coverage', desc: "How broadly you've solved across easy, medium, and hard difficulties in this track." },
            { label: 'Solve quality', desc: 'Whether you solve cleanly on the first attempt — first-time-correct mastery, not just eventual solves.' },
            { label: 'Mock performance', desc: 'Your accuracy under timed mock-interview conditions — practice alone tops out at "Getting there"; mocks unlock the top bands.' },
          ].map(s => (
            <div key={s.label} className="readiness-modal-signal">
              <span className="readiness-signal-dot" />
              <div>
                <span className="readiness-signal-label">{s.label}</span>
                <p className="readiness-signal-desc">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="readiness-modal-labels">
          {['Early stage', 'Building', 'Getting there', 'Interview ready', 'Strong'].map(label => (
            <span key={label} className="readiness-label-chip">{label}</span>
          ))}
        </div>
        <div className="readiness-modal-footer">
          <p className="readiness-modal-upgrade-copy">
            Upgrade to Elite to unlock readiness scores across all tracks, plus your personalised study plan and top weak-area coaching.
          </p>
          <UpgradeButton tier="elite" source="dashboard_readiness_modal" successPath="/?upgraded=true" />
        </div>
      </div>
    </div>
  );
}

export default function ProgressDashboard() {
  const { user, loading: authLoading } = useAuth();
  const location = useLocation();
  const rawPlan = user?.plan ?? 'free';
  const normalisedPlan = rawPlan.startsWith('lifetime_') ? rawPlan.replace('lifetime_', '') : rawPlan;
  const isPaying = normalisedPlan === 'pro' || normalisedPlan === 'elite';
  const isElite = normalisedPlan === 'elite';
  const planLabel =
    rawPlan === 'lifetime_elite' ? 'Lifetime Elite' :
    rawPlan === 'lifetime_pro'   ? 'Lifetime Pro'   :
    normalisedPlan === 'elite'   ? 'Elite'           :
    normalisedPlan === 'pro'     ? 'Pro'             : null;
  const planPillNode = user && isPaying && planLabel
    ? <span className={`shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`}>{planLabel}</span>
    : null;

  const catalogCounts = useCatalogCounts();
  const [data, setData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mockHistory, setMockHistory] = useState([]);
  const [readinessModalOpen, setReadinessModalOpen] = useState(false);
  const [activeRoleId, setActiveRoleId] = useState(null);

  useEffect(() => {
    if (location.state?.upgradeTier === 'elite') {
      setReadinessModalOpen(true);
      window.history.replaceState({}, '', location.pathname);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (authLoading) return;
    if (!user) { setLoading(false); return; }

    setLoading(true);
    setError(null);
    api.get('/dashboard')
      .then(res => setData(res.data))
      .catch(() => setError('Failed to load dashboard data.'))
      .finally(() => setLoading(false));

    api.get('/dashboard/insights').then(res => setInsights(res.data)).catch(() => {});
    api.get('/mock/history').then(r => setMockHistory(r.data.slice(0, 5))).catch(() => {});
  }, [authLoading, user]);

  const totalSolved = TRACK_SLUGS.reduce((sum, topic) => sum + (data?.tracks?.[topic]?.solved ?? 0), 0);
  const totalAccuracy = (() => {
    const values = TRACK_SLUGS
      .map(t => insights?.per_track?.[t]?.accuracy_pct)
      .filter(v => typeof v === 'number');
    if (!values.length) return null;
    return values.reduce((a, b) => a + b, 0) / values.length;
  })();
  const streakDays = insights?.streak_days ?? 0;

  const activeRoleFilter = ROLE_TRACK_FILTERS.find(r => r.id === activeRoleId) ?? null;
  const visibleTracks = activeRoleFilter
    ? activeRoleFilter.tracks.filter(t => TRACK_SLUGS.includes(t))
    : TRACK_SLUGS;

  const showDashboardEmpty = !loading && !error && totalSolved === 0;

  const greeting = (() => {
    const name = user?.name?.split(' ')?.[0] || null;
    const hr = new Date().getHours();
    const tod = hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening';
    return name ? `${tod}, ${name}` : tod;
  })();

  return (
    <>
      <Helmet>
        <title>My Progress — datathink</title>
        <meta name="description" content="Track your interview practice progress, streaks, and coaching insights." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <Topbar active="dashboard" userExtras={planPillNode} />

      <main className="container db-page">

        {loading && (
          <div className="db-loading" aria-label="Loading dashboard">
            <Skeleton width="14rem" height="1.8rem" style={{ marginBottom: '0.5rem' }} />
            <Skeleton width="22rem" height="1rem" />
            <div className="db-hero-stats-skeleton">
              <Skeleton height="5.5rem" />
              <Skeleton height="5.5rem" />
              <Skeleton height="5.5rem" />
            </div>
            <Skeleton height="12rem" />
            <Skeleton height="28rem" />
          </div>
        )}

        {!authLoading && !user && (
          <div className="db-empty-state">
            <p className="db-empty-copy">Sign in to track your progress, streaks, and coaching insights across all tracks.</p>
            <div className="db-empty-actions">
              <Link to="/auth" className="btn btn-primary">Sign in</Link>
              <Link to="/practice/sql" className="btn btn-secondary">Start practising</Link>
            </div>
          </div>
        )}

        {error && <p className="error-box">{error}</p>}

        {!loading && !error && user && (
          <>
            {/* PAGE HEADER */}
            <header className="db-header">
              <div className="db-header-text">
                <h1 className="db-greeting">{greeting}</h1>
                {totalSolved > 0 && (
                  <p className="db-subline">
                    {totalSolved} question{totalSolved !== 1 ? 's' : ''} solved across {TRACK_SLUGS.filter(t => (data?.tracks?.[t]?.solved ?? 0) > 0).length} tracks
                  </p>
                )}
              </div>
            </header>

            {showDashboardEmpty ? (
              <section className="db-empty-state">
                <div className="db-empty-icon">📊</div>
                <h3 className="db-empty-title">No progress yet</h3>
                <p className="db-empty-copy">Start solving questions — your personalised study plan, readiness scores, and coaching will appear here.</p>
                <div className="db-empty-actions">
                  <Link to="/practice/sql" className="btn btn-primary">Start SQL practice</Link>
                  <Link to="/learn" className="btn btn-secondary">Browse learning paths</Link>
                </div>
              </section>
            ) : (
              <>
                {/* HERO STATS */}
                <div className="db-hero-stats">
                  <div className="db-hero-stat">
                    <span className="db-hero-stat-value">{totalSolved}</span>
                    <span className="db-hero-stat-label">Questions solved</span>
                  </div>
                  <div className="db-hero-stat">
                    <span className="db-hero-stat-value">{streakDays}<span className="db-hero-stat-unit">d</span></span>
                    <span className="db-hero-stat-label">
                      {user?.streak_at_risk ? <span className="db-streak-at-risk">Streak at risk ⚡</span> : 'Current streak'}
                    </span>
                  </div>
                  <div className="db-hero-stat">
                    <span className="db-hero-stat-value">
                      {totalAccuracy !== null ? `${Math.round(totalAccuracy * 100)}%` : '—'}
                    </span>
                    <span className="db-hero-stat-label">Avg. accuracy</span>
                  </div>
                </div>

                {/* FOCUS CARD */}
                {(() => {
                  let focusTitle = null;
                  let focusHref = null;
                  let focusCtaLabel = 'Go →';
                  let focusSubline = null;

                  if (isPaying && insights?.weakest_concepts?.length > 0) {
                    const w = insights.weakest_concepts[0];
                    const trackLabel = TRACK_LABELS[w.track] || w.track;
                    focusTitle = `Drill ${w.concept}`;
                    focusHref = `/practice/${w.track}?drill=${encodeURIComponent(w.concept)}`;
                    focusCtaLabel = 'Go →';
                    focusSubline = `Your weakest concept in ${trackLabel} — ${Math.round(w.accuracy_pct * 100)}% accuracy across ${w.attempts} attempts`;
                  } else if (insights?.cross_track_insight) {
                    focusTitle = 'Coaching insight';
                    focusSubline = insights.cross_track_insight;
                    const trackWithActivity = TRACK_SLUGS.find(t => (data?.tracks?.[t]?.solved ?? 0) > 0);
                    focusHref = trackWithActivity ? `/practice/${trackWithActivity}` : '/practice/sql';
                    focusCtaLabel = 'Continue practice →';
                  }

                  if (!focusTitle && !focusSubline) return null;

                  return (
                    <div className="db-focus-card">
                      <div className="db-focus-content">
                        {focusTitle && <p className="db-focus-title">{focusTitle}</p>}
                        {focusSubline && <p className="db-focus-subline">{focusSubline}</p>}
                      </div>
                      {focusHref && (
                        <Link to={focusHref} className="db-focus-cta">{focusCtaLabel}</Link>
                      )}
                    </div>
                  );
                })()}

                {/* TRACK OVERVIEW */}
                <section className="db-section">
                  <div className="db-track-overview-head">
                    <h2 className="db-section-title">Track overview</h2>
                    <div className="db-role-filter" role="group" aria-label="Filter tracks by role">
                      <button
                        className={`db-role-btn${!activeRoleId ? ' db-role-btn--active' : ''}`}
                        onClick={() => setActiveRoleId(null)}
                        aria-pressed={!activeRoleId}
                      >
                        All tracks
                      </button>
                      {ROLE_TRACK_FILTERS.map(role => (
                        <button
                          key={role.id}
                          className={`db-role-btn${activeRoleId === role.id ? ' db-role-btn--active' : ''}`}
                          onClick={() => setActiveRoleId(activeRoleId === role.id ? null : role.id)}
                          aria-pressed={activeRoleId === role.id}
                          title={`${role.label}: ${role.tracks.length} tracks`}
                        >
                          {role.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  {isElite && (
                    <p className="db-readiness-note">Readiness blends coverage, first-time solve quality, and mock performance. Practice tops out at &#8220;Getting there&#8221; — log a few timed mocks to reach &#8220;Interview ready&#8221;.</p>
                  )}
                  <div className="db-track-table" key={activeRoleId ?? 'all'}>
                    {visibleTracks.map(topic => {
                      const meta = TRACK_META[topic];
                      const trackData = data?.tracks?.[topic];
                      const solved = trackData?.solved ?? 0;
                      const total = trackData?.total ?? catalogCounts[topic]?.total ?? 0;
                      const pct = total > 0 ? solved / total : 0;
                      const accuracy = insights?.per_track?.[topic]?.accuracy_pct;
                      const medianSecs = insights?.per_track?.[topic]?.median_solve_seconds;
                      const readiness = isElite ? insights?.readiness_scores?.[topic] : null;

                      return (
                        <Link key={topic} to={`/practice/${topic}`} className="db-track-row">
                          <span className="db-track-dot" style={{ background: meta.color }} />
                          <div className="db-track-name-col">
                            <span className="db-track-name">{meta.label}</span>
                            <span className="db-track-tagline">{meta.tagline}</span>
                          </div>
                          <div className="db-track-bar-col">
                            <div className="db-track-progress-bar">
                              <div className="db-track-progress-fill" style={{ width: `${pct * 100}%`, background: meta.color }} />
                            </div>
                            <span className="db-track-count">{solved}/{total}</span>
                          </div>
                          <div className="db-track-stats-col">
                            {typeof accuracy === 'number' ? (
                              <span className="db-track-accuracy" style={{ color: accuracy < 0.4 ? 'var(--danger)' : accuracy < 0.65 ? 'var(--warning)' : 'var(--success)' }}>
                                {Math.round(accuracy * 100)}% acc
                              </span>
                            ) : <span className="db-track-accuracy db-track-accuracy--muted">—</span>}
                            {typeof medianSecs === 'number' && medianSecs > 0 && (
                              <span className="db-track-time">{Math.round(medianSecs / 60)} min</span>
                            )}
                          </div>
                          <div className="db-track-right-col">
                            {readiness ? (
                              <div
                                className={`db-readiness-chip db-readiness-chip--${readiness.label.toLowerCase().replace(/\s+/g, '-')}`}
                                title={readiness.mock_limited ? 'Practice-strong — log a few timed mocks to raise this score' : undefined}
                              >
                                <span className="db-readiness-score">{readiness.score}</span>
                                <span className="db-readiness-label">{readiness.label}</span>
                              </div>
                            ) : !isElite ? (
                              <button
                                className="db-readiness-gate"
                                onClick={e => { e.preventDefault(); e.stopPropagation(); setReadinessModalOpen(true); }}
                              >
                                Readiness <span className="db-elite-badge">Elite</span>
                              </button>
                            ) : null}
                            {readiness?.mock_limited && (
                              <span className="db-readiness-mocknudge">Mock to level up</span>
                            )}
                            <span className="db-track-arrow">→</span>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </section>

                <div className="db-lower-grid">
                  <div className="db-lower-main">

                    {/* WHERE TO FOCUS */}
                    {(() => {
                      const weakConcepts = insights?.weakest_concepts ?? [];
                      const hasWeakConcepts = weakConcepts.length > 0;
                      const canSeeWeakConcepts = isPaying;

                      if (!canSeeWeakConcepts) {
                        return (
                          <section className="db-section">
                            <h2 className="db-section-title">Where to focus</h2>
                            <div className="db-focus-gate">
                              <p className="db-focus-gate-copy">Upgrade to Pro to see your weakest concepts and get targeted drill recommendations.</p>
                              <UpgradeButton tier="pro" source="dashboard_weak_concepts" successPath="/dashboard" compact />
                            </div>
                          </section>
                        );
                      }

                      if (!hasWeakConcepts) {
                        return (
                          <section className="db-section">
                            <h2 className="db-section-title">Where to focus</h2>
                            <p className="db-empty-copy db-empty-copy--muted">Attempt at least 3 questions on a concept to see gap analysis here.</p>
                          </section>
                        );
                      }

                      // Weak-areas list is a Pro+ feature: any paying user sees the full
                      // gap list (the *diagnosis*). Elite differentiates on the *prescription*
                      // — study plan + per-track readiness — and Interview Loop, not on hiding
                      // the user's own weak spots. (2026-06-13, decision B; matches the landing.)
                      const visibleConcepts = weakConcepts.slice(0, 4);

                      return (
                        <section className="db-section">
                          <h2 className="db-section-title">Where to focus</h2>
                          <div className="db-weak-list">
                            {visibleConcepts.map((item, i) => {
                              const trackLabel = TRACK_LABELS[item.track] || item.track;
                              const drillHref = `/practice/${item.track}?drill=${encodeURIComponent(item.concept)}`;
                              return (
                                <div key={i} className="db-weak-row">
                                  <div className="db-weak-header">
                                    <span className="db-weak-concept">{item.concept}</span>
                                    <span className="db-weak-track">{trackLabel}</span>
                                    <span className="db-weak-attempts">{item.attempts} attempt{item.attempts !== 1 ? 's' : ''}</span>
                                  </div>
                                  <AccuracyBar pct={item.accuracy_pct} />
                                  <Link to={drillHref} className="db-weak-drill">
                                    Drill this concept →
                                  </Link>
                                  {item.recommended_path_slug && (
                                    <Link to={`/learn/${item.track}/${item.recommended_path_slug}`} className="db-weak-drill-secondary">
                                      Or take the {item.recommended_path_title ?? 'path'} path →
                                    </Link>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      );
                    })()}

                    {/* STUDY PLAN — Elite */}
                    {isElite && insights?.study_plan?.length > 0 && (
                      <section className="db-section">
                        <div className="db-section-header">
                          <h2 className="db-section-title">Study plan</h2>
                          <span className="db-elite-badge">Elite</span>
                        </div>
                        <ol className="db-study-plan">
                          {insights.study_plan.map((step, i) => {
                            const typeLabel = {
                              concept_drill: 'Concept drill',
                              learning_path: 'Learning path',
                              mock_session: 'Mock interview',
                              practice_hard: 'Hard practice',
                            }[step.type] ?? step.type;
                            return (
                              <li key={i} className="db-plan-step">
                                <span className="db-plan-num">{i + 1}</span>
                                <div className="db-plan-body">
                                  <div className="db-plan-meta">
                                    <span className="db-plan-type">{typeLabel}</span>
                                  </div>
                                  <p className="db-plan-title">{step.title}</p>
                                  {step.description && <p className="db-plan-desc">{step.description}</p>}
                                </div>
                                <Link to={step.cta_href} className="db-plan-cta">{step.cta_label ?? 'Go →'}</Link>
                              </li>
                            );
                          })}
                        </ol>
                      </section>
                    )}

                    {!isElite && (
                      <section className="db-section db-study-plan-gate">
                        <div className="db-gate-row">
                          <div className="db-gate-text">
                            <p className="db-section-title">Study plan</p>
                            <p className="db-focus-gate-copy">Personalised daily plan based on your weak areas and mock performance.</p>
                          </div>
                          <UpgradeButton tier="elite" source="dashboard_study_plan" successPath="/dashboard" compact />
                        </div>
                      </section>
                    )}

                  </div>

                  <div className="db-lower-aside">

                    {/* RECENT ACTIVITY */}
                    <section className="db-section">
                      <h2 className="db-section-title">Recent activity</h2>
                      {data?.recent_activity?.length > 0 ? (
                        <div className="db-activity-feed">
                          {groupActivityByDate(data.recent_activity.slice(0, 10)).map(group => (
                            <div key={group.label} className="db-activity-group">
                              <p className="db-activity-date-label">{group.label}</p>
                              {group.items.map((item, i) => {
                                const meta = TRACK_META[item.topic];
                                return (
                                  <Link
                                    key={i}
                                    to={`/practice/${item.topic}/questions/${item.question_id}`}
                                    className="db-activity-row"
                                  >
                                    <span className="db-activity-dot" style={{ background: meta?.color }} />
                                    <div className="db-activity-body">
                                      <span className="db-activity-title">{item.title || `#${item.question_id}`}</span>
                                      <div className="db-activity-meta">
                                        <span className="db-activity-track">{meta?.label ?? item.topic}</span>
                                        <span className={`badge badge-${item.difficulty}`}>{item.difficulty}</span>
                                      </div>
                                    </div>
                                    <span className="db-activity-time">{formatRelativeTime(item.solved_at)}</span>
                                  </Link>
                                );
                              })}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="db-activity-empty">
                          <p className="db-empty-copy db-empty-copy--muted">No solved questions yet.</p>
                          <Link to="/learn/sql" className="db-weak-drill">Start the SQL paths →</Link>
                        </div>
                      )}
                    </section>

                    {/* MOCK HISTORY */}
                    {mockHistory.length > 0 && (
                      <section className="db-section">
                        <div className="db-section-header">
                          <h2 className="db-section-title">Mock interviews</h2>
                          <Link to="/mock" className="db-section-link">New mock →</Link>
                        </div>
                        <div className="db-mock-list">
                          {mockHistory.map(s => {
                            const pct = s.total_count > 0 ? s.solved_count / s.total_count : 0;
                            const trackLabel = TRACK_LABELS[s.track] || s.track;
                            return (
                              <Link key={s.session_id} to={`/mock/${s.session_id}`} className="db-mock-card">
                                <div className="db-mock-card-left">
                                  <span className="db-mock-track">{trackLabel}</span>
                                  <div className="db-mock-meta">
                                    {s.difficulty && <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>}
                                    <span className="db-mock-date">{formatRelativeTime(s.started_at)}</span>
                                  </div>
                                </div>
                                <div className="db-mock-card-right">
                                  <span className="db-mock-score">{s.solved_count}/{s.total_count}</span>
                                  <div className="db-mock-score-bar">
                                    <div className="db-mock-score-fill" style={{ width: `${pct * 100}%`, background: pct >= 0.7 ? 'var(--success)' : pct >= 0.5 ? 'var(--warning)' : 'var(--danger)' }} />
                                  </div>
                                  <span className="db-mock-action">{s.status === 'completed' ? 'Review →' : 'Resume →'}</span>
                                </div>
                              </Link>
                            );
                          })}
                        </div>
                      </section>
                    )}

                  </div>
                </div>
              </>
            )}
          </>
        )}
      </main>
      {readinessModalOpen && <ReadinessModal onClose={() => setReadinessModalOpen(false)} />}
    </>
  );
}
