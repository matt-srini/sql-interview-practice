import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_SLUGS, TRACK_LABELS } from '../trackRegistry';
import Topbar from '../components/Topbar';
import UpgradeButton from '../components/UpgradeButton';
import { track as trackEvent } from '../analytics';
import {
  getBenchmarkBlueprint,
  getMockModeCards,
  getMockModeDisplayLabel,
  getSessionQuestionCount,
  getSessionTimeMinutes,
} from '../mockModeConfig';

// Tracks that pool into a single mixed-track session (in_mixed_mock=True in backend).
const MIXED_MOCK_TRACKS = ['sql', 'python', 'python-data', 'pyspark'];

// All tracks now have at least one dedicated mock-only question.
// data-modeling: 63021 (2026-05-19). data-engineering: 53021 (2026-05-19). statistics: 73025–73029.
const NO_MOCK_BANK_TRACKS = new Set();

const MOCK_ROLES = [
  { id: 'analyst',            label: 'Data Analyst',       tracks: ['sql', 'statistics', 'python-data', 'python'] },
  { id: 'engineer',           label: 'Data Engineer',      tracks: ['python', 'sql', 'pyspark', 'data-engineering'] },
  { id: 'analytics_engineer', label: 'Analytics Engineer', tracks: ['sql', 'data-modeling', 'python-data', 'python'] },
  { id: 'scientist',          label: 'Data Scientist',     tracks: ['ml-fundamentals', 'statistics', 'experimentation', 'python', 'sql'] },
];

const DIFFICULTIES = ['easy', 'medium', 'hard', 'mixed'];

const DIFFICULTY_LABELS = { easy: 'Easy', medium: 'Medium', hard: 'Hard', mixed: 'Mixed' };

const PYSPARK_FORMAT_LABELS = {
  mcq: 'MCQ', predict_output: 'Predict Output', debug: 'Debug',
  scenario: 'Scenario', optimization: 'Optimization',
};

const PYSPARK_FORMAT_TARGETS = {
  easy:   ['mcq', 'predict_output', 'mcq', 'predict_output', 'debug', 'mcq'],
  medium: ['mcq', 'scenario', 'debug', 'predict_output', 'mcq', 'optimization'],
  hard:   ['mcq', 'scenario', 'predict_output', 'mcq', 'scenario', 'mcq'],
  mixed:  ['mcq', 'scenario', 'predict_output', 'debug', 'mcq', 'scenario'],
};

const MIXED_DIFF_TARGETS = ['easy', 'medium', 'hard', 'medium', 'hard'];

const TRACK_CONCEPT_MAP = {
  sql: ['AGGREGATION','WINDOW FUNCTIONS','JOINS','SUBQUERY PATTERNS','CTEs','DATE FUNCTIONS','GROUP BY','FILTERING','COHORT RETENTION','FUNNEL ANALYSIS','RANKING','SELF JOIN','SET OPERATIONS','CASE WHEN','STRING FUNCTIONS'],
  python: ['SORTING','BINARY SEARCH','HASH MAPS','TWO POINTERS','SLIDING WINDOW','RECURSION','DYNAMIC PROGRAMMING','GRAPHS','TREES','LINKED LISTS','HEAPS','STACK / QUEUE','BIT MANIPULATION'],
  'python-data': ['GROUPBY','MERGING','PIVOTING','FILTERING','AGGREGATION','WINDOW FUNCTIONS','RESHAPING','TIME SERIES','STRING METHODS','APPLY/MAP','COHORT ANALYSIS','MULTI-INDEX'],
  pyspark: ['DATAFRAME API','GROUPBY','JOINS','WINDOW FUNCTIONS','UDFs','PARTITIONING','AGGREGATION','STREAMING','CACHING','BROADCAST JOIN'],
  'ml-fundamentals': ['CLASSIFICATION METRICS','BIAS-VARIANCE TRADEOFF','DATA LEAKAGE DETECTION','OVERFITTING DIAGNOSIS','CROSS-VALIDATION DESIGN','ENSEMBLE STRATEGY','CLASS IMBALANCE HANDLING','REGULARIZATION EFFECT','HYPERPARAMETER SENSITIVITY','DIMENSIONALITY REDUCTION','TRAINING-SERVING SKEW','FEATURE SELECTION STRATEGY','MODEL MONITORING'],
  experimentation: ['EXPERIMENT DESIGN','CAUSAL INFERENCE','STATISTICAL POWER','METRIC SELECTION','MULTIPLE TESTING','NETWORK EFFECTS','VARIANCE REDUCTION','A/B TEST MECHANICS','TYPE I AND TYPE II ERRORS','EXPERIMENT DURATION','SEGMENTATION ANALYSIS','BAYESIAN EXPERIMENTATION','QUASI-EXPERIMENTAL METHODS'],
  'data-engineering': ['DATA QUALITY','STORAGE ARCHITECTURE','DELIVERY SEMANTICS','LINEAGE & OBSERVABILITY','SCHEDULING & SLAS','IDEMPOTENCY','BATCH VS STREAMING','SCHEMA EVOLUTION','PARTITIONING & PRUNING','ORCHESTRATION','WATERMARKING','BACKFILL DESIGN','DATA CONTRACT'],
  'data-modeling': ['FACT TABLE DESIGN','DIMENSIONAL MODELING','DIMENSION DESIGN','SCHEMA FROM REQUIREMENTS','DENORMALIZATION TRADEOFF','NORMALIZATION','GRAIN DEFINITION','SCD STRUCTURE','DBT MODELING','REFERENTIAL INTEGRITY','SURROGATE VS NATURAL KEYS','BI-TEMPORAL MODELING'],
  statistics: ['PROBABILITY','HYPOTHESIS TESTING','DESCRIPTIVE STATISTICS','DISTRIBUTIONS','CONFIDENCE INTERVALS','STATISTICAL POWER','BAYESIAN INFERENCE','EXPECTED VALUE','MULTIPLE COMPARISONS','REGRESSION','SAMPLING DISTRIBUTIONS','INDEPENDENCE','NON-PARAMETRIC TESTS','LOGISTIC REGRESSION','CAUSAL INFERENCE','RESIDUAL DIAGNOSTICS'],
};

function getSessionExpectations(track, difficulty, n) {
  const lines = [];
  if (track === 'pyspark') {
    const slots = (PYSPARK_FORMAT_TARGETS[difficulty] || []).slice(0, n);
    const counts = {};
    slots.forEach(t => { counts[t] = (counts[t] || 0) + 1; });
    lines.push(Object.entries(counts).map(([t, c]) => `${c} × ${PYSPARK_FORMAT_LABELS[t]}`).join(' · '));
  }
  if (difficulty === 'mixed') {
    const slots = MIXED_DIFF_TARGETS.slice(0, n);
    const counts = {};
    slots.forEach(d => { counts[d] = (counts[d] || 0) + 1; });
    lines.push(Object.entries(counts).map(([d, c]) => `${c} × ${DIFFICULTY_LABELS[d]}`).join(' · '));
  }
  return lines;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatDuration(timeLimitS, timeUsedS) {
  const used = timeUsedS != null ? timeUsedS : null;
  const limit = timeLimitS ? Math.floor(timeLimitS / 60) : null;
  if (used != null) {
    const m = Math.floor(used / 60);
    const s = used % 60;
    return `${m}:${String(s).padStart(2, '0')} used`;
  }
  return limit ? `${limit} min` : '—';
}

export default function MockHub() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const rawPlan = user?.plan ?? 'free';
  const normalisedPlan = rawPlan.startsWith('lifetime_') ? rawPlan.replace('lifetime_', '') : rawPlan;
  const isElite = normalisedPlan === 'elite';
  const isPro = normalisedPlan === 'pro';
  const isPaying = isPro || isElite;
  const planLabel =
    rawPlan === 'lifetime_elite' ? 'Lifetime Elite' :
    rawPlan === 'lifetime_pro'   ? 'Lifetime Pro'   :
    normalisedPlan === 'elite'   ? 'Elite'           :
    normalisedPlan === 'pro'     ? 'Pro'             : null;
  const planPillNode = user && isPaying && planLabel
    ? <span className={`shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`}>{planLabel}</span>
    : null;

  // Role filter — persisted in localStorage
  const [selectedRole, setSelectedRole] = useState(() => localStorage.getItem('mock_role') || null);

  // Derive filtered track list from selected role (always append 'mixed')
  const filteredSlugs = selectedRole
    ? (MOCK_ROLES.find(r => r.id === selectedRole)?.tracks ?? TRACK_SLUGS).filter(t => TRACK_SLUGS.includes(t))
    : TRACK_SLUGS;
  const filteredTracks = [...filteredSlugs, 'mixed'];

  const [mode, setMode] = useState('benchmark');
  const [track, setTrack] = useState('sql');
  const [difficulty, setDifficulty] = useState('easy');
  const [numQuestions, setNumQuestions] = useState(2);
  const [timeMinutes, setTimeMinutes] = useState(30);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState(null);
  const [activeSessionConflict, setActiveSessionConflict] = useState(null);
  const [endingSession, setEndingSession] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Focus mode — Elite feature, but UI is shown to all (locked for non-Elite)
  const [focusMode, setFocusMode] = useState(false);
  const [focusConcepts, setFocusConcepts] = useState([]);

  // Elite intelligence panel expand/collapse (non-Elite users only)
  const [elitePanelOpen, setElitePanelOpen] = useState(() => {
    const stored = localStorage.getItem('mock_elite_panel_open');
    return stored === null ? true : stored === 'true';
  });

  // Analytics — Elite only
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Pre-flight access state
  const [accessState, setAccessState] = useState(null);
  const [accessLoading, setAccessLoading] = useState(false);

  const benchmarkBlueprint = getBenchmarkBlueprint(track);
  const modeCards = getMockModeCards(track);
  const effectiveQuestionCount = getSessionQuestionCount(mode, track, numQuestions);
  const effectiveTimeMinutes = getSessionTimeMinutes(mode, track, timeMinutes);

  useEffect(() => {
    if (track === 'mixed' && mode === 'benchmark') {
      setMode('30min');
    }
  }, [track, mode]);

  function handleRoleSelect(roleId) {
    // Passing null = "All"; clicking the active role also returns to "All"
    const newRole = (roleId === null || roleId === selectedRole) ? null : roleId;
    setSelectedRole(newRole);
    if (newRole) {
      localStorage.setItem('mock_role', newRole);
      const roleTracks = MOCK_ROLES.find(r => r.id === newRole)?.tracks.filter(t => TRACK_SLUGS.includes(t)) ?? [];
      if (!roleTracks.includes(track) && track !== 'mixed') {
        setTrack(roleTracks[0] || 'sql');
        setFocusMode(false);
        setFocusConcepts([]);
      }
    } else {
      localStorage.removeItem('mock_role');
    }
  }

  useEffect(() => {
    api.get('/mock/history')
      .then(r => setHistory(r.data))
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, []);

  useEffect(() => {
    if (!isElite) return;
    setAnalyticsLoading(true);
    api.get('/mock/analytics')
      .then(r => setAnalytics(r.data))
      .catch(() => setAnalytics(null))
      .finally(() => setAnalyticsLoading(false));
  }, [isElite]);

  useEffect(() => {
    setAccessState(null);
    setAccessLoading(true);
    api.get('/mock/access', { params: { track } })
      .then(r => setAccessState(r.data))
      .catch(() => setAccessState(null))
      .finally(() => setAccessLoading(false));
  }, [track]);

  async function handleStart() {
    const diffAccess = accessState?.access?.[difficulty];
    if (diffAccess && !diffAccess.can_start) {
      setStartError(diffAccess.block_copy || 'Cannot start session with this configuration.');
      return;
    }
    setStarting(true);
    setStartError(null);
    try {
      const payload = {
        mode,
        track,
        difficulty,
        ...(mode === 'custom' ? { num_questions: numQuestions, time_minutes: timeMinutes } : {}),
        ...(isElite && focusMode && focusConcepts.length > 0 ? { focus_concepts: focusConcepts } : {}),
      };
      const r = await api.post('/mock/start', payload);
      trackEvent('mock_started', { mode, track, difficulty, session_id: r.data.session_id });
      navigate(`/mock/${r.data.session_id}`, { state: { sessionData: r.data } });
    } catch (err) {
      if (err?.response?.status === 409 && err?.response?.data?.error === 'active_session_exists') {
        const data = err.response.data;
        setActiveSessionConflict({
          session_id: data.session_id,
          track: data.track,
          difficulty: data.difficulty,
          mode: data.mode,
        });
        setStarting(false);
        return;
      }
      const msg = err?.response?.data?.error || err?.response?.data?.detail || 'Failed to start session. Please try again.';
      setStartError(msg);
      setStarting(false);
    }
  }

  async function handleEndAndStart() {
    if (!activeSessionConflict) return;
    setEndingSession(true);
    try {
      await api.post(`/mock/${activeSessionConflict.session_id}/finish`);
    } catch {
      // proceed even if finish fails
    }
    setActiveSessionConflict(null);
    setEndingSession(false);
    handleStart();
  }

  function getDifficultyButtonState(diff) {
    if (!accessState) return { blocked: false, chip: null };
    const a = accessState.access?.[diff];
    if (!a) return { blocked: false, chip: null };
    if (a.can_start) {
      if (a.daily_limit != null && a.daily_used != null) {
        const remaining = a.daily_limit - a.daily_used;
        if (remaining <= 0) return {
          blocked: true,
          chip: `Used today · resets tomorrow`,
          chipAction: a.needs_upgrade
            ? <UpgradeButton tier={a.needs_upgrade} label={`Unlimited with ${a.needs_upgrade === 'elite' ? 'Elite' : 'Pro'}`} compact source={`mock_${diff}_daily`} />
            : null,
        };
        return { blocked: false, chip: `${remaining} remaining today` };
      }
      return { blocked: false, chip: diff === 'easy' ? 'Unlimited' : null };
    }
    const upgradeLabel = a.needs_upgrade ? `${a.needs_upgrade === 'elite' ? 'Elite' : 'Pro'} unlocks this` : null;
    return {
      blocked: true,
      chip: a.block_copy,
      chipAction: a.needs_upgrade
        ? <UpgradeButton tier={a.needs_upgrade} label={upgradeLabel} compact source={`mock_${diff}_blocked`} />
        : a.block_reason === 'not_unlocked'
        ? <Link to={`/practice/${track}`} className="btn btn-secondary btn-compact">Practice to unlock →</Link>
        : null,
    };
  }

  const isMixedTrack = track === 'mixed';
  const hasMockBank  = !NO_MOCK_BANK_TRACKS.has(track);

  return (
    <div className="mock-hub-page">
      <Helmet>
        <title>Mock Interview — datathink</title>
        <meta name="description" content="Simulate real data interview conditions with timed SQL, Python, Pandas, and PySpark mock sessions." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <Topbar active="mock" userExtras={planPillNode} />

      {activeSessionConflict && (
        <div className="mock-modal-overlay" onClick={() => setActiveSessionConflict(null)}>
          <div className="mock-modal" onClick={e => e.stopPropagation()}>
            <h2 className="mock-modal-title">Active session in progress</h2>
            <p className="mock-modal-body">
              You already have an active{' '}
              <strong>{TRACK_LABELS[activeSessionConflict.track] || activeSessionConflict.track}</strong>{' '}
              <strong>{activeSessionConflict.difficulty}</strong>{' '}
              <strong>{getMockModeDisplayLabel(activeSessionConflict.mode)}</strong> session. Resume it or end it before starting a new one.
            </p>
            <div className="mock-modal-actions">
              <button className="btn btn-secondary" onClick={() => setActiveSessionConflict(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={handleEndAndStart} disabled={endingSession}>
                {endingSession ? 'Ending…' : 'End & start new'}
              </button>
              <button className="btn btn-primary" onClick={() => navigate(`/mock/${activeSessionConflict.session_id}`)}>
                Resume session →
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="mock-hub-main">
        {/* Hero */}
        <section className="mock-hub-hero">
          <h1 className="mock-hub-title">Mock Interview</h1>
          <p className="mock-hub-subtitle">
            Simulate real interview conditions with a countdown timer.
            <button className="mock-help-btn" onClick={() => setShowHelp(true)} aria-label="How it works">?</button>
          </p>
        </section>

        {/* Mode selector */}
        <section className="mock-hub-section">
          <div className="mock-mode-cards">
            {modeCards.map(card => (
              <button
                key={card.key}
                type="button"
                className={`mock-mode-card ${mode === card.key ? 'selected' : ''}${card.disabled ? ' mock-mode-card-disabled' : ''}`}
                onClick={() => {
                  if (card.disabled) return;
                  setMode(card.key);
                  setStartError(null);
                }}
                disabled={card.disabled}
              >
                <div className="mock-mode-card-label">{card.label}</div>
                <div className="mock-mode-card-sublabel">{card.sublabel}</div>
                <div className="mock-mode-card-desc">{card.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {mode === 'benchmark' && benchmarkBlueprint && (
          <section className="mock-hub-section mock-benchmark-blueprint">
            <div className="mock-benchmark-blueprint-kicker">Benchmark blueprint</div>
            <div className="mock-benchmark-blueprint-main">
              <span className="mock-benchmark-blueprint-shape">{benchmarkBlueprint.summary}</span>
              <span className="mock-benchmark-blueprint-time">{benchmarkBlueprint.timeMinutes} min fixed session</span>
            </div>
            <p className="mock-benchmark-blueprint-copy">{benchmarkBlueprint.description}</p>
          </section>
        )}

        {/* Custom controls */}
        {mode === 'custom' && (
          <section className="mock-hub-section mock-custom-controls">
            <div className="mock-custom-row">
              <label className="mock-custom-label">Questions</label>
              <input
                className="mock-custom-input"
                type="number" min="1" max="5" value={numQuestions}
                onChange={e => setNumQuestions(Math.max(1, Math.min(5, Number(e.target.value))))}
              />
              <span className="mock-custom-hint">(1–5)</span>
            </div>
            <div className="mock-custom-row">
              <label className="mock-custom-label">Time (minutes)</label>
              <input
                className="mock-custom-input"
                type="number" min="10" max="90" value={timeMinutes}
                onChange={e => setTimeMinutes(Math.max(10, Math.min(90, Number(e.target.value))))}
              />
              <span className="mock-custom-hint">(10–90)</span>
            </div>
          </section>
        )}

        {/* Configuration */}
        <section className="mock-hub-section">
          <div className="mock-hub-config">

            {/* Role filter */}
            <div className="mock-hub-config-row">
              <span className="mock-hub-config-label">Role</span>
              <div className="mock-role-pills">
                <button
                  type="button"
                  className={`mock-role-pill ${!selectedRole ? 'active' : ''}`}
                  onClick={() => handleRoleSelect(null)}
                >
                  All
                </button>
                {MOCK_ROLES.map(r => (
                  <button
                    key={r.id}
                    type="button"
                    className={`mock-role-pill ${selectedRole === r.id ? 'active' : ''}`}
                    onClick={() => handleRoleSelect(r.id)}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Track */}
            <div className="mock-hub-config-row">
              <span className="mock-hub-config-label">Track</span>
              <div className="mock-config-pills">
                {filteredTracks.map(t => (
                  <button
                    key={t}
                    type="button"
                    className={`mock-config-pill ${track === t ? 'active' : ''}`}
                    onClick={() => { setTrack(t); setFocusMode(false); setFocusConcepts([]); setStartError(null); }}
                  >
                    {TRACK_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div className="mock-hub-config-row">
              <span className="mock-hub-config-label">Difficulty</span>
              <div className="mock-config-pills">
                {DIFFICULTIES.map(d => {
                  const btnState = getDifficultyButtonState(d);
                  const isSelected = difficulty === d;
                  return (
                    <button
                      key={d}
                      type="button"
                      className={`mock-config-pill ${isSelected ? 'active' : ''} ${btnState.blocked ? 'mock-config-pill--blocked' : ''}`}
                      onClick={() => { setDifficulty(d); setStartError(null); }}
                      aria-disabled={btnState.blocked}
                    >
                      {DIFFICULTY_LABELS[d]}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Mixed track note */}
        {isMixedTrack && (
          <div className="mock-track-note">
            Draws questions from {MIXED_MOCK_TRACKS.map(s => TRACK_LABELS[s]).join(' · ')} — the four code-execution tracks. Mixed stays drill-only while benchmark mode becomes track-specific.
          </div>
        )}

        {/* No dedicated mock bank note */}
        {!isMixedTrack && !hasMockBank && (
          <div className="mock-track-note mock-track-note--info">
            No dedicated mock question bank yet for this track — this session draws from practice questions.
          </div>
        )}

        {/* Focus mode — shown to all, locked for non-Elite */}
        {!isMixedTrack && (
          <section className="mock-hub-section mock-focus-section">
            {isElite ? (
              <>
                <label className="mock-focus-label">
                  <input
                    type="checkbox"
                    checked={focusMode}
                    onChange={e => { setFocusMode(e.target.checked); setFocusConcepts([]); }}
                  />
                  <span>Focus mode</span>
                  <span className="mock-focus-label-sub">— target specific concepts in this session</span>
                </label>
                {focusMode && (
                  <div className="mock-focus-concepts">
                    {(TRACK_CONCEPT_MAP[track] || []).map(c => {
                      const selected = focusConcepts.includes(c);
                      const disabled = !selected && focusConcepts.length >= 3;
                      return (
                        <button
                          key={c}
                          type="button"
                          className={`mock-focus-concept-pill${selected ? ' selected' : ''}`}
                          onClick={() => {
                            if (selected) setFocusConcepts(prev => prev.filter(x => x !== c));
                            else if (!disabled) setFocusConcepts(prev => [...prev, c]);
                          }}
                          disabled={disabled}
                        >
                          {c}
                        </button>
                      );
                    })}
                    <p className="mock-focus-hint">Select 1–3 concepts. Session draws from questions tagged with them.</p>
                  </div>
                )}
              </>
            ) : (
              <div className="mock-focus-locked">
                <div className="mock-focus-locked-header">
                  <input type="checkbox" disabled className="mock-focus-locked-check" />
                  <span className="mock-focus-locked-label">Focus mode</span>
                  <span className="mock-elite-badge-inline">Elite</span>
                </div>
                <p className="mock-focus-locked-desc">
                  Target specific concepts — your session draws only from questions tagged with them.
                </p>
              </div>
            )}
          </section>
        )}

        {/* Difficulty notice */}
        {(() => {
          if (difficulty === 'medium' || difficulty === 'hard') {
            const notice = getDifficultyButtonState(difficulty);
            if (!notice.chip) return null;
            return (
              <div className={`mock-diff-notice${notice.blocked ? ' mock-diff-notice--blocked' : ''}`}>
                <span>{notice.chip}</span>
                {notice.chipAction && notice.chipAction}
              </div>
            );
          }
          if (difficulty === 'mixed' && accessState) {
            const medBlocked = accessState.access?.medium?.can_start === false;
            const hardBlocked = accessState.access?.hard?.can_start === false;
            if (medBlocked && hardBlocked) {
              return (
                <div className="mock-diff-notice mock-diff-notice--info">
                  <span>With your current access, this mix will only include easy questions.</span>
                  {accessState.access?.medium?.needs_upgrade && (
                    <UpgradeButton tier={accessState.access.medium.needs_upgrade} label="Unlock more with Pro" compact source="mock_mixed_notice" />
                  )}
                </div>
              );
            }
            if (hardBlocked) {
              return (
                <div className="mock-diff-notice mock-diff-notice--info">
                  <span>Hard questions aren't included yet — this mix will draw from easy and medium.</span>
                  {accessState.access?.hard?.needs_upgrade && (
                    <UpgradeButton tier={accessState.access.hard.needs_upgrade} label="Unlock hard with Pro" compact source="mock_mixed_hard_notice" />
                  )}
                </div>
              );
            }
          }
          return null;
        })()}

        {/* What to expect */}
        {(() => {
          const expectations = getSessionExpectations(track, difficulty, effectiveQuestionCount);
          if (mode !== 'benchmark' && !expectations.length) return null;
          return (
            <div className="mock-session-expect">
              <span className="mock-session-expect-label">Expect</span>
              <span className="mock-session-expect-line">{effectiveQuestionCount} questions · {effectiveTimeMinutes} min</span>
              {expectations.map((line, i) => (
                <span key={i} className="mock-session-expect-line">{line}</span>
              ))}
            </div>
          );
        })()}

        {startError && <p className="mock-hub-error">{startError}</p>}

        <section className="mock-hub-section mock-hub-start-row">
          <button
            className="btn btn-primary mock-start-btn"
            onClick={handleStart}
            disabled={starting || accessLoading || (accessState && !accessState.access?.[difficulty]?.can_start)}
          >
            {starting ? 'Starting…' : mode === 'benchmark' ? 'Start benchmark' : 'Start drill session'}
          </button>
        </section>

        {/* Elite analytics panel — visible to Elite users */}
        {isElite && (
          <section className="mock-hub-section mock-analytics-panel">
            <div className="mock-analytics-header">
              <span className="mock-analytics-elite-badge">Elite</span>
              <h2 className="mock-analytics-title">Mock Analytics</h2>
            </div>
            {analyticsLoading && <p className="mock-analytics-loading">Loading analytics…</p>}
            {!analyticsLoading && analytics && analytics.total_sessions > 0 && (
              <>
                <p className="mock-analytics-summary">
                  {analytics.total_sessions} session{analytics.total_sessions !== 1 ? 's' : ''} total
                  {analytics.sessions_last_30d > 0 && ` · ${analytics.sessions_last_30d} this month`}
                </p>
                <div className="mock-analytics-stat-row">
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{analytics.avg_score_pct}%</span>
                    <span className="mock-analytics-stat-label">Avg score</span>
                  </div>
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{analytics.best_score_pct}%</span>
                    <span className="mock-analytics-stat-label">Best score</span>
                  </div>
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{analytics.avg_time_used_pct}%</span>
                    <span className="mock-analytics-stat-label">Avg time used</span>
                  </div>
                </div>
                {analytics.score_trend.length > 1 && (
                  <div className="mock-analytics-sparkline-wrap">
                    <span className="mock-analytics-sparkline-label">Score trend (last {analytics.score_trend.length})</span>
                    <div className="mock-analytics-sparkline">
                      {analytics.score_trend.map((score, i) => {
                        const heightPct = Math.max(10, score);
                        const colorClass = score >= 75 ? 'good' : score >= 50 ? 'mid' : 'low';
                        return (
                          <div
                            key={i}
                            className={`mock-analytics-sparkline-bar ${colorClass}`}
                            style={{ height: `${heightPct}%` }}
                            title={`${score}%`}
                          />
                        );
                      })}
                    </div>
                  </div>
                )}
                <div className="mock-analytics-concepts">
                  {analytics.top_concepts[0] && (
                    <div className="mock-analytics-concept-row">
                      <span className="mock-analytics-concept-label strongest">Strongest:</span>
                      <span className="mock-analytics-concept-name">{analytics.top_concepts[0].concept}</span>
                      <span className="mock-analytics-concept-acc">{analytics.top_concepts[0].accuracy_pct}%</span>
                    </div>
                  )}
                  {analytics.weak_concepts[0] && (
                    <div className="mock-analytics-concept-row">
                      <span className="mock-analytics-concept-label needswork">Needs work:</span>
                      <span className="mock-analytics-concept-name">{analytics.weak_concepts[0].concept}</span>
                      <span className="mock-analytics-concept-acc">{analytics.weak_concepts[0].accuracy_pct}%</span>
                    </div>
                  )}
                </div>
              </>
            )}
            {!analyticsLoading && (!analytics || analytics.total_sessions === 0) && (
              <p className="mock-analytics-empty">Complete your first mock session to see analytics here.</p>
            )}
          </section>
        )}

        {/* Elite intelligence panel — teaser for Free and Pro users */}
        {!isElite && (
          <section className="mock-hub-section mock-elite-panel">
            <div className="mock-elite-panel-header">
              <span className="mock-elite-wordmark">Elite</span>
              <h2 className="mock-elite-panel-title">
                {isPro ? 'One step from Elite' : 'What Elite adds to every session'}
              </h2>
              <button
                type="button"
                className="mock-elite-panel-toggle"
                onClick={() => {
                  const next = !elitePanelOpen;
                  setElitePanelOpen(next);
                  localStorage.setItem('mock_elite_panel_open', String(next));
                }}
                aria-expanded={elitePanelOpen}
                aria-label={elitePanelOpen ? 'Collapse' : 'Expand'}
              >
                {elitePanelOpen ? '▴' : '▾'}
              </button>
            </div>

            {elitePanelOpen && (
              <div className="mock-elite-panel-body">
                <ul className="mock-elite-features">
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Focus mode</span>
                    <span className="mock-elite-feature-desc">Target specific concepts — your session draws only from questions tagged with them.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Score trends</span>
                    <span className="mock-elite-feature-desc">Track whether you're improving session over session, across every track.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Concept breakdown</span>
                    <span className="mock-elite-feature-desc">Know which topics are costing you before the real interview.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Coaching debrief</span>
                    <span className="mock-elite-feature-desc">One priority fix after every session — so you always know what to work on next.</span>
                  </li>
                  {!isPro && (
                    <li className="mock-elite-feature">
                      <span className="mock-elite-feature-name">Unlimited sessions</span>
                      <span className="mock-elite-feature-desc">No daily caps on any difficulty.</span>
                    </li>
                  )}
                </ul>
                <div className="mock-elite-panel-cta">
                  <UpgradeButton tier="elite" label="Upgrade to Elite →" source="mock_elite_panel" />
                  {isPro && (
                    <span className="mock-elite-panel-cta-note">You're on Pro — one tier away.</span>
                  )}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Recent sessions */}
        {!historyLoading && history.length > 0 && (
          <section className="mock-hub-section mock-hub-history">
            <h2 className="mock-hub-history-title">Recent sessions</h2>
            <table className="mock-history-table">
              <thead>
                <tr>
                  <th>Date</th><th>Mode</th><th>Track</th><th>Difficulty</th><th>Score</th><th>Time</th><th></th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 5).map(s => (
                  <tr key={s.session_id}>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{getMockModeDisplayLabel(s.mode)}</td>
                    <td>{TRACK_LABELS[s.track] || s.track}</td>
                    <td>{s.difficulty && <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>}</td>
                    <td>{s.solved_count}/{s.total_count}</td>
                    <td>{formatDuration(s.time_limit_s, null)}</td>
                    <td>
                      <Link to={`/mock/${s.session_id}`} className="mock-review-link">
                        {s.status === 'completed' ? 'Review →' : 'Resume →'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {!historyLoading && history.length === 0 && (
          <section className="mock-hub-section mock-hub-empty-state">
            <p className="mock-hub-empty">No mock sessions yet. Start your first interview simulation now.</p>
            <div className="mock-hub-empty-actions">
              <Link to="/practice/sql" className="btn btn-secondary btn-compact">Warm up in SQL</Link>
              <Link to="/dashboard" className="btn btn-secondary btn-compact">View progress dashboard</Link>
            </div>
          </section>
        )}

        {/* How it works modal */}
        {showHelp && (
          <div className="mock-help-overlay" role="dialog" aria-modal="true" aria-labelledby="mock-help-title">
            <div className="mock-help-modal">
              <div className="mock-help-modal-header">
                <h2 id="mock-help-title">How mock interviews work</h2>
                <button className="mock-help-close" onClick={() => setShowHelp(false)} aria-label="Close">✕</button>
              </div>
              <ol className="mock-help-steps">
                <li>Choose a session type — Benchmark for the fixed-shape track benchmark, Sprint drill for a short calibration round, or Custom drill for targeted follow-up practice.</li>
                <li>Filter by role to see the tracks most relevant to your interview target, then pick a track and difficulty. Mixed draws from {MIXED_MOCK_TRACKS.map(s => TRACK_LABELS[s]).join(', ')} only.</li>
                <li>Benchmark mode is track-specific and fixed-shape. Mixed remains drill-only.</li>
                <li><strong>(Elite)</strong> Enable <strong>Focus mode</strong> to target specific concepts — your session draws from questions tagged with them.</li>
                <li>During the session — a countdown timer runs. Write your answer and submit each question independently.</li>
                <li>No solutions are revealed mid-session.</li>
                <li>After finishing — you'll see your score, time used, and <strong>(Elite)</strong> a coaching debrief with concept weak-spots and a priority action.</li>
                <li><strong>(Elite)</strong> Check your <strong>Mock analytics</strong> panel to track score trends and concept performance across all sessions.</li>
              </ol>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
