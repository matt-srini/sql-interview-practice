import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import Topbar from '../components/Topbar';
import UpgradeButton from '../components/UpgradeButton';
import { track as trackEvent } from '../analytics';

const TRACKS = ['sql', 'python', 'python-data', 'pyspark', 'mixed'];
const DIFFICULTIES = ['easy', 'medium', 'hard', 'mixed'];

const TRACK_LABELS = {
  sql: 'SQL',
  python: 'Python',
  'python-data': 'Pandas',
  pyspark: 'PySpark',
  mixed: 'Mixed',
};

const DIFFICULTY_LABELS = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
  mixed: 'Mixed',
};

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

  const [mode, setMode] = useState('30min');
  const [track, setTrack] = useState('sql');
  const [difficulty, setDifficulty] = useState('easy');
  const [companyFilter, setCompanyFilter] = useState('');
  const [numQuestions, setNumQuestions] = useState(2);
  const [timeMinutes, setTimeMinutes] = useState(30);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState(null);
  const [showHelp, setShowHelp] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Pre-flight access state from /api/mock/access
  const [accessState, setAccessState] = useState(null);
  const [accessLoading, setAccessLoading] = useState(false);

  useEffect(() => {
    api.get('/mock/history')
      .then(r => setHistory(r.data))
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, []);

  // Fetch access state whenever track changes
  useEffect(() => {
    setAccessState(null);
    setAccessLoading(true);
    api.get('/mock/access', { params: { track } })
      .then(r => setAccessState(r.data))
      .catch(() => setAccessState(null))
      .finally(() => setAccessLoading(false));
  }, [track]);

  async function handleStart() {
    // Pre-flight check before submitting
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
        ...(companyFilter ? { company_filter: companyFilter } : {}),
      };
      const r = await api.post('/mock/start', payload);
      trackEvent('mock_started', { mode, track, difficulty, session_id: r.data.session_id });
      navigate(`/mock/${r.data.session_id}`, { state: { sessionData: r.data } });
    } catch (err) {
      const msg = err?.response?.data?.error || err?.response?.data?.detail || 'Failed to start session. Please try again.';
      setStartError(msg);
      setStarting(false);
    }
  }

  function getDifficultyButtonState(diff) {
    if (!accessState) return { blocked: false, chip: null };
    const a = accessState.access?.[diff];
    if (!a) return { blocked: false, chip: null };
    if (a.can_start) {
      // Show usage chip for capped difficulties
      if (a.daily_limit != null && a.daily_used != null) {
        const remaining = a.daily_limit - a.daily_used;
        if (remaining <= 0) return { blocked: true, chip: `Used today · resets tomorrow`, chipAction: a.needs_upgrade ? <UpgradeButton tier={a.needs_upgrade} label={`Unlimited with ${a.needs_upgrade === 'elite' ? 'Elite' : 'Pro'}`} compact source={`mock_${diff}_daily`} /> : null };
        return { blocked: false, chip: `${remaining} remaining today` };
      }
      return { blocked: false, chip: diff === 'easy' ? 'Unlimited' : null };
    }
    // Blocked
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

  const modeCards = [
    { key: '30min', label: 'Quick', sublabel: '30 min · 2 questions', desc: 'Fast-paced warm-up session' },
    { key: '60min', label: 'Full', sublabel: '60 min · 3 questions', desc: 'Realistic interview length' },
    { key: 'custom', label: 'Custom', sublabel: 'You choose', desc: 'Set your own pace and depth' },
  ];

  return (
    <div className="mock-hub-page">
      <Helmet>
        <title>Mock Interview — datanest</title>
        <meta name="description" content="Simulate real data interview conditions with timed SQL, Python, Pandas, and PySpark mock sessions." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <Topbar active="mock" />

      <main className="mock-hub-main">
        {/* Hero */}
        <section className="mock-hub-hero">
          <h1 className="mock-hub-title">Mock Interview</h1>
          <p className="mock-hub-subtitle">Simulate real interview conditions with a countdown timer.<button className="mock-help-btn" onClick={() => setShowHelp(true)} aria-label="How it works">?</button></p>
        </section>

        {/* Mode selector */}
        <section className="mock-hub-section">
          <div className="mock-mode-cards">
            {modeCards.map(card => (
              <button
                key={card.key}
                type="button"
                className={`mock-mode-card ${mode === card.key ? 'selected' : ''}`}
                onClick={() => { setMode(card.key); setStartError(null); }}
              >
                <div className="mock-mode-card-label">{card.label}</div>
                <div className="mock-mode-card-sublabel">{card.sublabel}</div>
                <div className="mock-mode-card-desc">{card.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Custom controls */}
        {mode === 'custom' && (
          <section className="mock-hub-section mock-custom-controls">
            <div className="mock-custom-row">
              <label className="mock-custom-label">Questions</label>
              <input
                className="mock-custom-input"
                type="number"
                min="1"
                max="5"
                value={numQuestions}
                onChange={e => setNumQuestions(Math.max(1, Math.min(5, Number(e.target.value))))}
              />
              <span className="mock-custom-hint">(1–5)</span>
            </div>
            <div className="mock-custom-row">
              <label className="mock-custom-label">Time (minutes)</label>
              <input
                className="mock-custom-input"
                type="number"
                min="10"
                max="90"
                value={timeMinutes}
                onChange={e => setTimeMinutes(Math.max(10, Math.min(90, Number(e.target.value))))}
              />
              <span className="mock-custom-hint">(10–90)</span>
            </div>
          </section>
        )}

        {/* Configuration */}
        <section className="mock-hub-section">
          <div className="mock-hub-config">
            <div className="mock-hub-config-row">
              <span className="mock-hub-config-label">Track</span>
              <div className="mock-config-pills">
                {TRACKS.map(t => (
                  <button
                    key={t}
                    type="button"
                    className={`mock-config-pill ${track === t ? 'active' : ''}`}
                    onClick={() => { setTrack(t); setCompanyFilter(''); setStartError(null); }}
                  >
                    {TRACK_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            {/* Company filter — Elite only, SQL track only */}
            {track === 'sql' && (() => {
              const normalisedPlan = user?.plan?.startsWith('lifetime_') ? user.plan.replace('lifetime_', '') : (user?.plan ?? 'free');
              const isElite = normalisedPlan === 'elite';
              return isElite ? (
                <div className="mock-hub-config-row">
                  <span className="mock-hub-config-label">Company</span>
                  <select
                    className="mock-config-select"
                    value={companyFilter}
                    onChange={e => setCompanyFilter(e.target.value)}
                  >
                    <option value="">All companies</option>
                    {['Airbnb','Amazon','Amplitude','Databricks','Google','LinkedIn','Meta','Microsoft','Netflix','PayPal','Salesforce','Shopify','Snowflake','Stripe','Zendesk','eBay'].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              ) : null;
            })()}

            {/* Difficulty with per-button pre-flight state */}
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

        {/* Difficulty notice — shown below config card for medium/hard/mixed */}
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

        {/* Start error (fallback for unexpected server errors) */}
        {startError && (
          <p className="mock-hub-error">{startError}</p>
        )}

        <section className="mock-hub-section mock-hub-start-row">
          <button
            className="btn btn-primary mock-start-btn"
            onClick={handleStart}
            disabled={starting || accessLoading || (accessState && !accessState.access?.[difficulty]?.can_start)}
          >
            {starting ? 'Starting…' : 'Start Mock Interview'}
          </button>
        </section>

        {/* Recent sessions */}
        {!historyLoading && history.length > 0 && (
          <section className="mock-hub-section mock-hub-history">
            <h2 className="mock-hub-history-title">Recent sessions</h2>
            <table className="mock-history-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Mode</th>
                  <th>Track</th>
                  <th>Difficulty</th>
                  <th>Score</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 5).map(s => (
                  <tr key={s.session_id}>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{s.mode}</td>
                    <td>{TRACK_LABELS[s.track] || s.track}</td>
                    <td>
                      {s.difficulty && (
                        <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>
                      )}
                    </td>
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
      {showHelp && (
        <div className="mock-help-overlay" role="dialog" aria-modal="true" aria-labelledby="mock-help-title">
          <div className="mock-help-modal">
            <div className="mock-help-modal-header">
              <h2 id="mock-help-title">How mock interviews work</h2>
              <button className="mock-help-close" onClick={() => setShowHelp(false)} aria-label="Close">✕</button>
            </div>
            <ol className="mock-help-steps">
              <li>Choose mode — Quick (30 min, 2 questions), Full (60 min, 3 questions), or Custom.</li>
              <li>Pick your track (SQL, Python, Pandas, PySpark, or Mixed) and difficulty.</li>
              <li>During the session — a countdown timer runs. Write your answer and submit each question independently.</li>
              <li>No solutions are revealed mid-session.</li>
              <li>After finishing — you'll see your score, time used, and (Elite) concept weak-spots with a drill link.</li>
            </ol>
          </div>
        </div>
      )}
      </main>
    </div>
  );
}
