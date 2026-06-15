import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
  getMockSetupDescriptor,
  isBenchmarkMockMode,
  getSessionQuestionCount,
  getSessionTimeMinutes,
  dimensionLabel,
} from '../mockModeConfig';

// Tracks that pool into a single mixed-track session (in_mixed_mock=True in backend).
const MIXED_MOCK_TRACKS = ['sql', 'python', 'pandas', 'pyspark'];

const MOCK_ROLES = [
  { id: 'data_analyst',       label: 'Data Analyst',       tracks: ['sql', 'pandas', 'statistics'] },
  { id: 'data_engineer',      label: 'Data Engineer',      tracks: ['sql', 'python', 'pyspark', 'data-engineering'] },
  { id: 'analytics_engineer', label: 'Analytics Engineer', tracks: ['sql', 'data-modeling', 'pandas'] },
  { id: 'data_scientist',     label: 'Data Scientist',     tracks: ['python', 'pandas', 'statistics', 'ml-fundamentals'] },
];

const DIFFICULTIES = ['easy', 'medium', 'hard', 'mixed'];

const DIFFICULTY_LABELS = { easy: 'Easy', medium: 'Medium', hard: 'Hard', mixed: 'Mixed' };

const PYSPARK_FORMAT_LABELS = {
  conceptual: 'Conceptual', predict_output: 'Predict Output', debug: 'Debug',
  scenario: 'Scenario', optimization: 'Optimization',
};

const PYSPARK_FORMAT_TARGETS = {
  easy:   ['predict_output', 'conceptual', 'predict_output', 'debug', 'predict_output', 'conceptual'],
  medium: ['predict_output', 'debug', 'predict_output', 'debug', 'conceptual', 'scenario'],
  hard:   ['conceptual', 'scenario', 'predict_output', 'conceptual', 'scenario', 'conceptual'],
  mixed:  ['conceptual', 'scenario', 'predict_output', 'debug', 'conceptual', 'scenario'],
};

const MIXED_DIFF_TARGETS = ['easy', 'medium', 'hard', 'medium', 'hard'];

const TRACK_CONCEPT_MAP = {
  sql: ['AGGREGATION','WINDOW FUNCTIONS','JOINS','SUBQUERY PATTERNS','CTEs','DATE FUNCTIONS','GROUP BY','FILTERING','COHORT RETENTION','FUNNEL ANALYSIS','RANKING','SELF JOIN','SET OPERATIONS','CASE WHEN','STRING FUNCTIONS'],
  python: ['SORTING','BINARY SEARCH','HASH MAPS','TWO POINTERS','SLIDING WINDOW','RECURSION','DYNAMIC PROGRAMMING','GRAPHS','TREES','LINKED LISTS','HEAPS','STACK / QUEUE','BIT MANIPULATION'],
  'pandas': ['GROUPBY','MERGING','PIVOTING','FILTERING','AGGREGATION','WINDOW FUNCTIONS','RESHAPING','TIME SERIES','STRING METHODS','APPLY/MAP','COHORT ANALYSIS','MULTI-INDEX'],
  pyspark: ['DATAFRAME API','GROUPBY','JOINS','WINDOW FUNCTIONS','UDFs','PARTITIONING','AGGREGATION','STREAMING','CACHING','BROADCAST JOIN','SHUFFLE & PERFORMANCE','CATALYST & QUERY PLANNING','MEMORY MANAGEMENT','DATA SKEW','DELTA LAKE','AQE'],
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

// Renders the history "Time" cell as "used / limit" (e.g. "14:56 / 60:00") — the time
// limit varies by track/difficulty/mode, so the ratio gives pacing context the bare
// time-used can't, and it mirrors the table's "Score 2/3" (solved/total) idiom. Falls
// back to "— / limit" for sessions with no recorded time-used (active/abandoned).
function formatDuration(timeLimitS, timeUsedS) {
  const clock = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${String(sec).padStart(2, '0')}`;
  };
  const limit = timeLimitS != null ? clock(timeLimitS) : null;
  const used = timeUsedS != null ? clock(timeUsedS) : null;
  if (used != null && limit != null) return `${used} / ${limit}`;
  if (limit != null) return `— / ${limit}`;
  if (used != null) return used;
  return '—';
}

export default function MockHub() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const appliedPresetKeyRef = useRef(null);

  const rawPlan = user?.plan ?? 'free';
  const normalisedPlan = rawPlan.startsWith('lifetime_') ? rawPlan.replace('lifetime_', '') : rawPlan;
  const isElite = normalisedPlan === 'elite';
  const isPro = normalisedPlan === 'pro';
  const isPaying = isPro || isElite;

  // Role filter — persisted in localStorage. Map legacy IDs to current ones.
  const [selectedRole, setSelectedRole] = useState(() => {
    const stored = localStorage.getItem('mock_role');
    const LEGACY_MAP = { analyst: 'data_analyst', engineer: 'data_engineer', scientist: 'data_scientist' };
    return LEGACY_MAP[stored] || stored || null;
  });

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

  // Transient note shown when selecting Interview Loop auto-switches off the Mixed
  // track (Interview Loop is single-track). Cleared on the next mode/track change.
  const [loopTrackSwitchNote, setLoopTrackSwitchNote] = useState(null);

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
  const [analyticsError, setAnalyticsError] = useState(false);

  // Pre-flight access state
  const [accessState, setAccessState] = useState(null);
  const [accessLoading, setAccessLoading] = useState(false);
  const [presetNotice, setPresetNotice] = useState(null);

  const benchmarkBlueprint = getBenchmarkBlueprint(track, track === 'mixed' ? selectedRole : undefined);
  const modeCards = getMockModeCards(track, rawPlan);
  const setupDescriptor = getMockSetupDescriptor(mode, track, numQuestions, timeMinutes, selectedRole);
  const effectiveQuestionCount = getSessionQuestionCount(mode, track, numQuestions, selectedRole);
  const effectiveTimeMinutes = getSessionTimeMinutes(mode, track, timeMinutes, selectedRole);
  const benchmarkHistory = history.filter((session) => isBenchmarkMockMode(session.mode));
  const loopHistory = history.filter((session) => session.mode === 'interview_loop');
  const drillHistory = history.filter((session) => !isBenchmarkMockMode(session.mode) && session.mode !== 'interview_loop');
  const benchmarkAnalytics = analytics?.benchmark_summary ?? null;
  const drillAnalytics = analytics?.drill_summary ?? null;
  const loopAnalytics = analytics?.loop_summary ?? null;
  const expectationLines = getSessionExpectations(track, difficulty, effectiveQuestionCount);
  const showFirstRunFraming = !historyLoading && history.length === 0;
  const showBenchmarkEmptyFraming = !historyLoading && history.length > 0 && benchmarkHistory.length === 0;
  const showDrillEmptyFraming = !historyLoading && history.length > 0 && drillHistory.length === 0;

  useEffect(() => {
    // interview_loop does not support mixed track — fall back to custom
    if (track === 'mixed' && mode === 'interview_loop') {
      setMode('custom');
    }
  }, [track, mode]);

  useEffect(() => {
    const preset = location.state?.mockPreset;
    if (!preset || appliedPresetKeyRef.current === location.key) return;

    appliedPresetKeyRef.current = location.key;

    const nextTrack = [...TRACK_SLUGS, 'mixed'].includes(preset.track) ? preset.track : 'sql';
    const VALID_MODES = new Set(['benchmark', 'custom', 'interview_loop']);
    const nextMode = VALID_MODES.has(preset.mode) ? preset.mode : 'benchmark';
    const nextDifficulty = DIFFICULTIES.includes(preset.difficulty) ? preset.difficulty : 'easy';

    setMode(nextMode);
    setTrack(nextTrack);
    setDifficulty(nextDifficulty);
    setNumQuestions(typeof preset.numQuestions === 'number' ? Math.max(1, Math.min(5, preset.numQuestions)) : 2);
    setTimeMinutes(typeof preset.timeMinutes === 'number' ? Math.max(10, Math.min(90, preset.timeMinutes)) : 30);
    setFocusMode(false);
    setFocusConcepts([]);
    setStartError(null);
    setPresetNotice(preset.note || null);

    const roleTracks = selectedRole
      ? (MOCK_ROLES.find(r => r.id === selectedRole)?.tracks ?? []).filter(t => TRACK_SLUGS.includes(t))
      : [];
    if (selectedRole && nextTrack !== 'mixed' && !roleTracks.includes(nextTrack)) {
      setSelectedRole(null);
      localStorage.removeItem('mock_role');
    }
  }, [location.key, location.state, selectedRole]);

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

  const fetchAnalytics = useCallback(() => {
    setAnalyticsLoading(true);
    setAnalyticsError(false);
    api.get('/mock/analytics')
      .then(r => { setAnalytics(r.data); setAnalyticsError(false); })
      .catch(() => { setAnalytics(null); setAnalyticsError(true); })
      .finally(() => setAnalyticsLoading(false));
  }, []);

  useEffect(() => { if (isElite) fetchAnalytics(); }, [isElite, fetchAnalytics]);

  const fetchAccess = useCallback(() => {
    setAccessState(null);
    setAccessLoading(true);
    api.get('/mock/access', { params: { track, mode } })
      .then(r => setAccessState(r.data))
      .catch(() => setAccessState(null))
      .finally(() => setAccessLoading(false));
  }, [track, mode]);

  useEffect(() => { fetchAccess(); }, [fetchAccess]);

  function handleSelectMode(key) {
    setStartError(null);
    setLoopTrackSwitchNote(null);
    // Interview Loop is single-track. If Mixed is selected, move off it to a sensible
    // single track (the role's first, else SQL) and explain the switch — no dead-end.
    if (key === 'interview_loop' && track === 'mixed') {
      const roleTracks = selectedRole
        ? (MOCK_ROLES.find(r => r.id === selectedRole)?.tracks ?? []).filter(t => TRACK_SLUGS.includes(t))
        : [];
      const nextTrack = roleTracks[0] || 'sql';
      setTrack(nextTrack);
      setFocusMode(false);
      setFocusConcepts([]);
      // State the constraint, not the switched-to track — the Track selector already
      // shows the new single track, and naming it here just adds noise/confusion.
      setLoopTrackSwitchNote("Interview Loop runs on one track — can't choose Mixed.");
    }
    setMode(key);
  }

  async function handleStart() {
    // Interview Loop gates on full-pool ("mixed") chain availability; other modes
    // gate on the selected difficulty.
    const gate = mode === 'interview_loop' ? 'mixed' : difficulty;
    const diffAccess = accessState?.access?.[gate];
    if (diffAccess && !diffAccess.can_start) {
      setStartError(diffAccess.block_copy || 'Cannot start session with this configuration.');
      return;
    }
    if (track === 'mixed' && !selectedRole) {
      setStartError('Please select a role for a mixed-track session.');
      return;
    }
    setStarting(true);
    setStartError(null);
    try {
      const payload = {
        mode,
        track,
        // Interview Loop carries no user-chosen difficulty (emergent from the chain).
        ...(mode === 'interview_loop' ? {} : { difficulty }),
        ...(track === 'mixed' ? { role: selectedRole } : {}),
        ...(mode === 'custom' ? { num_questions: numQuestions, time_minutes: timeMinutes } : {}),
        ...(isElite && focusMode && focusConcepts.length > 0 ? { focus_concepts: focusConcepts } : {}),
      };
      const r = await api.post('/mock/start', payload);
      trackEvent('mock_started', { mode, track, difficulty: mode === 'interview_loop' ? null : difficulty, session_id: r.data.session_id });
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
      // Error shapes: 403 → { error }; dict-detail 409 (pool_exhausted) is spread
      // to the top level by the API error handler, so block_copy sits at data.block_copy.
      const data = err?.response?.data || {};
      const detail = data.detail;
      const msg =
        data.error ||
        data.block_copy ||
        (typeof detail === 'string' ? detail : detail?.block_copy) ||
        'Failed to start session. Please try again.';
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
      if (a.weekly_benchmark_limit != null && a.weekly_benchmark_used != null) {
        const remaining = a.weekly_benchmark_limit - a.weekly_benchmark_used;
        return { blocked: false, chip: remaining > 0 ? `${remaining} free benchmark this week` : null };
      }
      return { blocked: false, chip: null };
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
  const isLoop = mode === 'interview_loop';

  // Interview Loop has no user-chosen difficulty — the chain difficulty is emergent
  // (parent → escalating follow-ups). Gate it on the full-pool ("mixed") chain
  // availability for the track; every other mode gates on the selected difficulty.
  const gateKey = isLoop ? 'mixed' : difficulty;
  const railDiffState = getDifficultyButtonState(gateKey);

  return (
    <div className="mock-hub-page">
      <Helmet>
        <title>Benchmarks & Drills — datathink</title>
        <meta name="description" content="Set your baseline with benchmarks, then use drills to improve weak areas across SQL, Python, Pandas, PySpark, and reasoning tracks." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <Topbar active="mock" />

      {activeSessionConflict && (
        <div className="mock-modal-overlay" onClick={() => setActiveSessionConflict(null)}>
          <div className="mock-modal" onClick={e => e.stopPropagation()}>
            <h2 className="mock-modal-title">Active session in progress</h2>
            <p className="mock-modal-body">
              You already have an active{' '}
              <strong>{TRACK_LABELS[activeSessionConflict.track] || activeSessionConflict.track}</strong>{' '}
              {activeSessionConflict.difficulty && <><strong>{activeSessionConflict.difficulty}</strong>{' '}</>}
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

        {/* ── Two-column lobby ── */}
        <div className="mock-hub-lobby">

          {/* Left: primary setup lane */}
          <div className="mock-hub-left-col">

            {/* Hero */}
            <section className="mock-hub-hero">
              <div className="mock-hub-kicker">Benchmarks, drills, and Interview Loop</div>
              <h1 className="mock-hub-title">Interview Practice</h1>
              <div className="mock-hub-subtitle-row">
                <p className="mock-hub-subtitle">
                  Use benchmarks for a consistent interview-style check, then use custom drills or Interview Loop to work on the gaps you find.
                </p>
                <button className="mock-help-btn" onClick={() => setShowHelp(true)} aria-label="How it works">?</button>
              </div>
            </section>

            {/* Recommendation banner */}
            {presetNotice && (
              <section className="mock-hub-section mock-setup-recommendation">
                <div className="mock-setup-recommendation-kicker">Recommended next step</div>
                <p className="mock-setup-recommendation-copy">{presetNotice}</p>
              </section>
            )}

            {/* Mode selector */}
            <section className="mock-hub-section">
              <div className="mock-mode-cards">
                {modeCards.map(card => (
                  <button
                    key={card.key}
                    type="button"
                    className={[
                      'mock-mode-card',
                      mode === card.key ? 'selected' : '',
                      card.disabled ? 'mock-mode-card-disabled' : '',
                      card.locked ? 'mock-mode-card-locked' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => { if (!card.disabled) handleSelectMode(card.key); }}
                    disabled={card.disabled}
                    title={card.locked ? card.lockedReason : undefined}
                  >
                    <div className="mock-mode-card-label-row">
                      <span className="mock-mode-card-label">{card.label}</span>
                      {card.locked && card.requiredTier && (
                        <span className={`mock-mode-card-badge ${card.requiredTier === 'elite' ? 'mock-elite-badge-inline' : 'mock-mode-card-badge--pro'}`}>
                          {card.requiredTier === 'elite' ? 'Elite' : 'Pro'}
                        </span>
                      )}
                    </div>
                    <div className="mock-mode-card-sublabel">{card.sublabel}</div>
                    <div className="mock-mode-card-desc">{card.desc}</div>
                    {card.locked && (
                      <div className="mock-mode-card-lock-notice">{card.lockedReason}</div>
                    )}
                  </button>
                ))}
              </div>
            </section>

            {/* Benchmark blueprint — single-track AND Mixed. For Mixed it renders the
                role-based mix once a role is picked (benchmarkBlueprint is null until then). */}
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

            {/* Drill / Loop planner */}
            {mode !== 'benchmark' && setupDescriptor && (
              <section className="mock-hub-section mock-drill-plan">
                <div className="mock-drill-plan-main">
                  <div className="mock-drill-plan-title-row">
                    <span className="mock-drill-plan-kicker">{setupDescriptor.sectionLabel}</span>
                    <span className="mock-drill-plan-mode">{setupDescriptor.modeLabel}</span>
                  </div>
                  {mode !== 'interview_loop' && (
                    <div className="mock-drill-plan-chips">
                      {effectiveQuestionCount > 0 && <span className="mock-drill-plan-chip">{effectiveQuestionCount} q</span>}
                      {effectiveTimeMinutes != null && effectiveTimeMinutes > 0 && (
                        <span className="mock-drill-plan-chip">{effectiveTimeMinutes} min</span>
                      )}
                      <span className="mock-drill-plan-chip mock-drill-plan-chip-track">{TRACK_LABELS[track]}</span>
                      {expectationLines.map((line, index) => (
                        <span key={index} className="mock-drill-plan-chip mock-drill-plan-chip-shape">{line}</span>
                      ))}
                    </div>
                  )}
                  {mode === 'interview_loop' && (
                    <div className="mock-drill-plan-chips">
                      <span className="mock-drill-plan-chip">1 chain</span>
                      <span className="mock-drill-plan-chip">15 min / question</span>
                      <span className="mock-drill-plan-chip mock-drill-plan-chip-track">{TRACK_LABELS[track]}</span>
                    </div>
                  )}
                  {mode === 'interview_loop' && loopTrackSwitchNote && (
                    <p className="mock-loop-switch-note">{loopTrackSwitchNote}</p>
                  )}
                  <p className="mock-drill-plan-copy">{setupDescriptor.description}</p>
                  {setupDescriptor.detailLines?.length > 0 && (
                    <p className="mock-drill-plan-note">{setupDescriptor.detailLines[0]}</p>
                  )}

                  {mode === 'custom' && (
                    <div className="mock-custom-controls mock-custom-controls-inline">
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
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Configuration: role, track, difficulty */}
            <section className="mock-hub-section">
              <div className="mock-hub-config">

                {/* Role — ALWAYS in this fixed position (never relocated by track/mode).
                    Single-track uses it as a track filter ("All" = no filter); Mixed
                    requires a specific role, nudged by a helper note below the config. */}
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
                        onClick={() => { setTrack(t); setFocusMode(false); setFocusConcepts([]); setStartError(null); setLoopTrackSwitchNote(null); }}
                      >
                        {TRACK_LABELS[t]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Difficulty — not shown for Interview Loop: its difficulty is
                    emergent (the chain escalates), not a user-chosen knob. */}
                {!isLoop && (
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
                          className={`mock-config-pill ${isSelected && !btnState.blocked ? 'active' : ''} ${btnState.blocked ? 'mock-config-pill--blocked' : ''}`}
                          onClick={() => { setDifficulty(d); setStartError(null); }}
                          aria-disabled={btnState.blocked}
                          title={btnState.blocked && typeof btnState.chip === 'string' ? btnState.chip : undefined}
                        >
                          {DIFFICULTY_LABELS[d]}
                        </button>
                      );
                    })}
                  </div>
                </div>
                )}
                {/* Mixed track needs a role — surfaced as a helper note here, NOT by
                    relocating the Role selector (which stays fixed above). The blueprint
                    for the chosen mix renders in the Benchmark blueprint panel above. */}
                {isMixedTrack && mode !== 'interview_loop' && !selectedRole && (
                  <p className="mock-config-hint">
                    Mixed track needs a role — pick one above to set your track mix{mode === 'benchmark' ? ' and benchmark blueprint' : ''}.
                  </p>
                )}
              </div>
            </section>

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

          </div>{/* end mock-hub-left-col */}

          {/* Right: sticky session brief rail */}
          <aside className="mock-hub-rail">
            <div className="mock-rail-card">
              <span className="mock-rail-kicker">Session brief</span>

              {/* Mode badge */}
              <span className={`mock-rail-mode-badge mock-rail-mode-badge--${mode === 'benchmark' ? 'benchmark' : mode === 'interview_loop' ? 'loop' : 'drill'}`}>
                {getMockModeDisplayLabel(mode)}
              </span>

              {/* Detail rows */}
              <div className="mock-rail-details">
                <div className="mock-rail-row">
                  <span className="mock-rail-key">Track</span>
                  <span className="mock-rail-val">{TRACK_LABELS[track]}</span>
                </div>
                {!isLoop && (
                  <div className="mock-rail-row">
                    <span className="mock-rail-key">Difficulty</span>
                    <span className={`badge badge-${difficulty}`}>{DIFFICULTY_LABELS[difficulty]}</span>
                  </div>
                )}
                {effectiveQuestionCount > 0 && (
                  <div className="mock-rail-row">
                    <span className="mock-rail-key">Questions</span>
                    <span className="mock-rail-val">{effectiveQuestionCount}</span>
                  </div>
                )}
                {effectiveTimeMinutes > 0 && (
                  <div className="mock-rail-row">
                    <span className="mock-rail-key">Time limit</span>
                    <span className="mock-rail-val">{effectiveTimeMinutes} min</span>
                  </div>
                )}
              </div>

              {/* Focus concepts if any selected */}
              {isElite && focusMode && focusConcepts.length > 0 && (
                <div className="mock-rail-focus-pills">
                  {focusConcepts.map(c => (
                    <span key={c} className="mock-rail-focus-pill">{c}</span>
                  ))}
                </div>
              )}

              {!accessLoading && !accessState && (
                <div className="mock-rail-access mock-rail-access--blocked">
                  <span>Couldn't check your access.</span>
                  <button type="button" className="btn btn-secondary btn-compact" onClick={fetchAccess}>Retry</button>
                </div>
              )}

              {/* Access state notice — per-difficulty for benchmark/custom; track-level
                  ("mixed") chain availability for Interview Loop (shows "all chains
                  completed for this track" when the pool is exhausted). */}
              {railDiffState.blocked ? (
                <div className="mock-rail-access mock-rail-access--blocked">
                  <span>{railDiffState.chip}</span>
                  {railDiffState.chipAction}
                </div>
              ) : railDiffState.chip && railDiffState.chip !== 'Unlimited' ? (
                <div className="mock-rail-access mock-rail-access--remaining">
                  {railDiffState.chip}
                </div>
              ) : null}

              {/* Error */}
              {startError && <p className="mock-rail-error">{startError}</p>}

              {/* Start CTA */}
              <button
                className="btn btn-primary mock-start-btn"
                onClick={handleStart}
                disabled={
                  starting ||
                  accessLoading ||
                  (!accessState || !accessState.access?.[gateKey]?.can_start) ||
                  (isMixedTrack && mode !== 'interview_loop' && !selectedRole)
                }
              >
                {starting
                  ? 'Starting…'
                  : mode === 'benchmark'
                  ? 'Start benchmark'
                  : mode === 'interview_loop'
                  ? 'Start Interview Loop'
                  : 'Start drill session'}
              </button>
            </div>
          </aside>

        </div>{/* end mock-hub-lobby */}

        {/* ── Below lobby: analytics and history ── */}

        {/* Elite analytics panel */}
        {isElite && (
          <section className="mock-hub-section mock-analytics-panel">
            <div className="mock-analytics-header">
              <span className="mock-analytics-elite-badge">Elite</span>
              <h2 className="mock-analytics-title">Benchmark Analytics</h2>
            </div>
            {analyticsLoading && <p className="mock-analytics-loading">Loading analytics…</p>}
            {!analyticsLoading && analytics && benchmarkAnalytics && benchmarkAnalytics.total_sessions > 0 && (
              <>
                <p className="mock-analytics-summary">
                  {benchmarkAnalytics.total_sessions} benchmark session{benchmarkAnalytics.total_sessions !== 1 ? 's' : ''}
                  {benchmarkAnalytics.sessions_last_30d > 0 && ` · ${benchmarkAnalytics.sessions_last_30d} this month`}
                  {analytics.mode_breakdown?.drill > 0 && ` · ${analytics.mode_breakdown.drill} drill session${analytics.mode_breakdown.drill !== 1 ? 's' : ''} tracked separately`}
                </p>
                <div className="mock-analytics-stat-row">
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{benchmarkAnalytics.avg_score_pct}%</span>
                    <span className="mock-analytics-stat-label">Avg benchmark score (all tracks)</span>
                  </div>
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{benchmarkAnalytics.best_score_pct}%</span>
                    <span className="mock-analytics-stat-label">Best benchmark score</span>
                  </div>
                  <div className="mock-analytics-stat">
                    <span className="mock-analytics-stat-value">{benchmarkAnalytics.avg_time_used_pct}%</span>
                    <span className="mock-analytics-stat-label">Avg benchmark time used</span>
                  </div>
                </div>
                {benchmarkAnalytics.track_breakdown && Object.keys(benchmarkAnalytics.track_breakdown).length > 1 && (
                  <div className="mock-analytics-track-breakdown">
                    <span className="mock-analytics-track-breakdown-label">Per-track breakdown</span>
                    <div className="mock-analytics-track-rows">
                      {Object.entries(benchmarkAnalytics.track_breakdown)
                        .sort((a, b) => b[1].sessions - a[1].sessions)
                        .map(([t, stats]) => (
                          <div key={t} className="mock-analytics-track-row">
                            <span className="mock-analytics-track-name">{TRACK_LABELS[t] || t}</span>
                            <span className="mock-analytics-track-sessions">{stats.sessions} session{stats.sessions !== 1 ? 's' : ''}</span>
                            <span className="mock-analytics-track-score">{stats.avg_score_pct}% avg</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
                {benchmarkAnalytics.score_trend.length > 1 && (
                  <div className="mock-analytics-sparkline-wrap">
                    <span className="mock-analytics-sparkline-label">Benchmark score trend (last {benchmarkAnalytics.score_trend.length})</span>
                    <div className="mock-analytics-sparkline">
                      {benchmarkAnalytics.score_trend.map((score, i) => {
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
                {drillAnalytics && drillAnalytics.total_sessions > 0 && (
                  <div className="mock-analytics-secondary-row">
                    <div className="mock-analytics-secondary-card">
                      <span className="mock-analytics-secondary-label">Custom drills</span>
                      <span className="mock-analytics-secondary-value">{drillAnalytics.total_sessions} sessions</span>
                      <span className="mock-analytics-secondary-copy">{drillAnalytics.avg_score_pct}% avg score · {drillAnalytics.avg_time_used_pct}% avg time used</span>
                    </div>
                  </div>
                )}
                {loopAnalytics && loopAnalytics.sessions > 0 && (
                  <div className="mock-analytics-secondary-row">
                    <div className="mock-analytics-secondary-card">
                      <span className="mock-analytics-secondary-label">Interview Loops</span>
                      <span className="mock-analytics-secondary-value">{loopAnalytics.sessions} completed</span>
                      {loopAnalytics.per_dimension_performance && Object.keys(loopAnalytics.per_dimension_performance).length > 0 && (
                        <div className="mock-loop-dimension-breakdown">
                          {Object.entries(loopAnalytics.per_dimension_performance)
                            .sort((a, b) => a[1].accuracy_pct - b[1].accuracy_pct)
                            .map(([dim, stats]) => (
                              <span key={dim} className="mock-loop-dimension-row">
                                <span className="mock-loop-dimension-name">{dimensionLabel(dim)}</span>
                                <span className="mock-loop-dimension-acc">{stats.accuracy_pct}%</span>
                              </span>
                            ))}
                        </div>
                      )}
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
            {!analyticsLoading && analytics && benchmarkAnalytics && benchmarkAnalytics.total_sessions === 0 && (
              <p className="mock-analytics-empty">
                Complete your first benchmark session to unlock comparable benchmark analytics.
                {analytics.mode_breakdown?.drill > 0 ? ` You already have ${analytics.mode_breakdown.drill} drill session${analytics.mode_breakdown.drill !== 1 ? 's' : ''} tracked separately.` : ''}
              </p>
            )}
            {!analyticsLoading && analyticsError && (
              <p className="mock-analytics-empty">
                Couldn't load analytics. <button type="button" className="mock-link-button" onClick={fetchAnalytics}>Retry</button>
              </p>
            )}
          </section>
        )}

        {/* Pro benchmark history card — stripped view, no concept panel or sparkline */}
        {isPro && !isElite && (() => {
          const scoredSessions = benchmarkHistory.filter(s => s.total_count > 0);
          const proAvgScore = scoredSessions.length > 0
            ? Math.round(scoredSessions.reduce((sum, s) => sum + (s.solved_count / s.total_count) * 100, 0) / scoredSessions.length)
            : null;
          const lastBenchmark = benchmarkHistory[0] || null;
          return (
            <section className="mock-hub-section mock-pro-history-panel">
              <div className="mock-pro-history-header">
                <h2 className="mock-pro-history-title">Benchmark history</h2>
                {benchmarkHistory.length > 0 && (
                  <span className="mock-pro-history-count">{benchmarkHistory.length} session{benchmarkHistory.length !== 1 ? 's' : ''}</span>
                )}
              </div>
              {benchmarkHistory.length === 0 ? (
                <p className="mock-pro-history-empty">
                  Complete your first benchmark to see your history here.
                </p>
              ) : (
                <div className="mock-pro-history-body">
                  {proAvgScore !== null && (
                    <div className="mock-pro-history-stat-row">
                      <div className="mock-pro-history-stat">
                        <span className="mock-pro-history-stat-value">{proAvgScore}%</span>
                        <span className="mock-pro-history-stat-label">Avg score (all tracks)</span>
                      </div>
                    </div>
                  )}
                  {lastBenchmark && (
                    <div className="mock-pro-history-last">
                      <span className="mock-pro-history-last-label">Last benchmark</span>
                      <span className="mock-pro-history-last-detail">
                        {TRACK_LABELS[lastBenchmark.track] || lastBenchmark.track}
                        {' · '}
                        <span className={`badge badge-${lastBenchmark.difficulty}`}>{lastBenchmark.difficulty}</span>
                        {' · '}
                        {lastBenchmark.total_count > 0
                          ? `${lastBenchmark.solved_count}/${lastBenchmark.total_count} solved`
                          : '—'}
                        {' · '}
                        {formatDate(lastBenchmark.started_at)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </section>
          );
        })()}

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
                aria-label={elitePanelOpen ? 'Hide panel' : 'Show panel'}
              >
                <span>{elitePanelOpen ? 'Hide' : 'Show'}</span>
                <span className="mock-elite-panel-toggle-arrow" aria-hidden="true">{elitePanelOpen ? '▴' : '▾'}</span>
              </button>
            </div>

            {elitePanelOpen && (
              <div className="mock-elite-panel-body">
                <ul className="mock-elite-features">
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Interview Loop</span>
                    <span className="mock-elite-feature-desc">Chain-driven sessions where each follow-up pivots like a real interviewer — scale, business rule, dirty data, ambiguity.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Focus mode</span>
                    <span className="mock-elite-feature-desc">Target specific concepts — your session draws only from questions tagged with them.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Score trends</span>
                    <span className="mock-elite-feature-desc">Track whether you're improving session over session, across every track.</span>
                  </li>
                  <li className="mock-elite-feature">
                    <span className="mock-elite-feature-name">Per-dimension weak spots</span>
                    <span className="mock-elite-feature-desc">Which kinds of pivots break you — strong on scale, weak on ambiguity, etc.</span>
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

        {/* Recent benchmark sessions */}
        {!historyLoading && benchmarkHistory.length > 0 && (
          <section className="mock-hub-section mock-hub-history">
            <h2 className="mock-hub-history-title">Recent benchmark sessions</h2>
            <div className="mock-history-table-wrap">
            <table className="mock-history-table">
              <thead>
                <tr>
                  <th>Date</th><th>Mode</th><th>Track</th><th>Difficulty</th><th>Score</th><th>Time</th><th></th>
                </tr>
              </thead>
              <tbody>
                {benchmarkHistory.slice(0, 5).map(s => (
                  <tr key={s.session_id}>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{getMockModeDisplayLabel(s.mode)}</td>
                    <td>{TRACK_LABELS[s.track] || s.track}</td>
                    <td>{s.difficulty && <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>}</td>
                    <td>{s.solved_count}/{s.total_count}</td>
                    <td className="mock-history-time">{formatDuration(s.time_limit_s, s.time_used_s)}</td>
                    <td>
                      <Link to={`/mock/${s.session_id}`} className="mock-review-link">
                        {s.status === 'completed' ? 'Review →' : 'Resume →'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        )}

        {!historyLoading && drillHistory.length > 0 && (
          <section className="mock-hub-section mock-hub-history">
            <h2 className="mock-hub-history-title">Recent custom drills</h2>
            <div className="mock-history-table-wrap">
            <table className="mock-history-table">
              <thead>
                <tr>
                  <th>Date</th><th>Track</th><th>Difficulty</th><th>Score</th><th>Time</th><th></th>
                </tr>
              </thead>
              <tbody>
                {drillHistory.slice(0, 5).map(s => (
                  <tr key={s.session_id}>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{TRACK_LABELS[s.track] || s.track}</td>
                    <td>{s.difficulty && <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>}</td>
                    <td>{s.solved_count}/{s.total_count}</td>
                    <td className="mock-history-time">{formatDuration(s.time_limit_s, s.time_used_s)}</td>
                    <td>
                      <Link to={`/mock/${s.session_id}`} className="mock-review-link">
                        {s.status === 'completed' ? 'Review →' : 'Resume →'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        )}

        {!historyLoading && loopHistory.length > 0 && (
          <section className="mock-hub-section mock-hub-history">
            <h2 className="mock-hub-history-title">Recent Interview Loops</h2>
            <div className="mock-history-table-wrap">
            <table className="mock-history-table">
              <thead>
                <tr>
                  {/* No Difficulty column — Interview Loop difficulty is emergent (the chain escalates). */}
                  <th>Date</th><th>Track</th><th>Score</th><th>Time</th><th></th>
                </tr>
              </thead>
              <tbody>
                {loopHistory.slice(0, 5).map(s => (
                  <tr key={s.session_id}>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{TRACK_LABELS[s.track] || s.track}</td>
                    <td>{s.solved_count}/{s.total_count}</td>
                    <td className="mock-history-time">{formatDuration(s.time_limit_s, s.time_used_s)}</td>
                    <td>
                      <Link to={`/mock/${s.session_id}`} className="mock-review-link">
                        {s.status === 'completed' ? 'Review →' : 'Resume →'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        )}

        {showBenchmarkEmptyFraming && (
          <section className="mock-hub-section mock-hub-history-empty mock-hub-history-empty--benchmark">
            <div className="mock-hub-history-empty-kicker">Benchmark history</div>
            <h2 className="mock-hub-history-title">No benchmark sessions yet</h2>
            <p className="mock-hub-history-empty-copy">
              Use one fixed-shape benchmark when you want a clean calibration point for this track. It gives you a comparable score baseline before you start tuning with drills.
            </p>
          </section>
        )}

        {showDrillEmptyFraming && (
          <section className="mock-hub-section mock-hub-history-empty mock-hub-history-empty--drill">
            <div className="mock-hub-history-empty-kicker">Drill history</div>
            <h2 className="mock-hub-history-title">No custom drills yet</h2>
            <p className="mock-hub-history-empty-copy">
              Use custom drills after a benchmark when you want extra reps on one weak area without muddying your benchmark baseline.
            </p>
          </section>
        )}

        {showFirstRunFraming && (
          <section className="mock-hub-section mock-hub-empty-state mock-hub-empty-state--first-run">
            <div className="mock-hub-empty-header">
              <h2 className="mock-hub-history-title">Start with a benchmark, then drill the misses</h2>
              <p className="mock-hub-empty-copy">
                Benchmarks are for clean calibration. Custom drills help you rehearse weak areas once you know where the session broke down.
              </p>
            </div>
            <div className="mock-hub-empty-grid">
              <div className="mock-hub-empty-card mock-hub-empty-card--benchmark">
                <div className="mock-hub-empty-card-kicker">Benchmark first</div>
                <h3 className="mock-hub-empty-card-title">Use benchmarks for comparability</h3>
                <p className="mock-hub-empty-card-copy">
                  Fixed-shape sessions give you the cleanest signal on pace and accuracy. Start here when you want a serious read on interview readiness.
                </p>
              </div>
              <div className="mock-hub-empty-card mock-hub-empty-card--drill">
                <div className="mock-hub-empty-card-kicker">Then drill</div>
                <h3 className="mock-hub-empty-card-title">Use custom drills for targeted reps</h3>
                <p className="mock-hub-empty-card-copy">
                  Custom drills are better for rehearsing one weakness, warming up, or pressure-testing a specific concept after a benchmark. Interview Loop is the Elite option when you want the interviewer to keep digging.
                </p>
              </div>
            </div>
            <div className="mock-hub-empty-actions">
              {(() => { const warmupTrack = isMixedTrack ? 'sql' : track; return (
                <Link to={`/practice/${warmupTrack}`} className="btn btn-secondary btn-compact">Warm up in {TRACK_LABELS[warmupTrack]}</Link>
              ); })()}
              <Link to="/dashboard" className="btn btn-secondary btn-compact">View progress dashboard</Link>
            </div>
          </section>
        )}

      </main>

      {/* How it works modal */}
      {showHelp && (
        <div className="mock-help-overlay" role="dialog" aria-modal="true" aria-labelledby="mock-help-title">
          <div className="mock-help-modal">
            <div className="mock-help-modal-header">
              <h2 id="mock-help-title">How mock modes work</h2>
              <button className="mock-help-close" onClick={() => setShowHelp(false)} aria-label="Close">✕</button>
            </div>
            <ol className="mock-help-steps">
              <li>Choose a session type — Benchmark for the fixed-shape readiness signal, Custom drill for targeted follow-up practice, or Interview Loop for an Elite-only chain where the interviewer keeps pushing deeper.</li>
              <li>Filter by role to see the tracks most relevant to your interview target, then pick a track and difficulty. Mixed draws from {MIXED_MOCK_TRACKS.map(s => TRACK_LABELS[s]).join(', ')} and uses role-based setup.</li>
              <li>Benchmark mode is fixed-shape. Mixed benchmarks and custom drills both require role selection, while Interview Loop stays single-track only.</li>
              <li><strong>(Elite)</strong> Enable <strong>Focus mode</strong> to target specific concepts — your session draws from questions tagged with them.</li>
              <li>During the session — a countdown timer runs. Write your answer and <strong>run it as many times as you like</strong> to test. When ready, <strong>submit once — each question is one shot</strong>. You can keep editing after submitting but your score for that question is locked.</li>
              <li>No solutions are revealed mid-session.</li>
              <li>After finishing — you'll see your score and solutions, plus <strong>(Elite)</strong> a coaching debrief with concept weak-spots and a priority action.</li>
              <li><strong>(Elite)</strong> Check your <strong>Mock analytics</strong> panel to track score trends and concept performance across all sessions.</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
