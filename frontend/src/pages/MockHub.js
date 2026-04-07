import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { useTheme } from '../App';

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
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const navigate = useNavigate();

  const [mode, setMode] = useState('30min');
  const [track, setTrack] = useState('sql');
  const [difficulty, setDifficulty] = useState('medium');
  const [numQuestions, setNumQuestions] = useState(2);
  const [timeMinutes, setTimeMinutes] = useState(30);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    api.get('/mock/history')
      .then(r => setHistory(r.data))
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, []);

  function cycleTheme() {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  }
  const themeIcon = theme === 'system' ? '◐' : resolvedTheme === 'dark' ? '☀' : '☾';

  async function handleStart() {
    setStarting(true);
    setStartError(null);
    try {
      const payload = {
        mode,
        track,
        difficulty,
        ...(mode === 'custom' ? { num_questions: numQuestions, time_minutes: timeMinutes } : {}),
      };
      const r = await api.post('/mock/start', payload);
      navigate(`/mock/${r.data.session_id}`, { state: { sessionData: r.data } });
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to start session. Please try again.';
      setStartError(msg);
      setStarting(false);
    }
  }

  const modeCards = [
    { key: '30min', label: 'Quick', sublabel: '30 min · 2 questions', desc: 'Fast-paced warm-up session' },
    { key: '60min', label: 'Full', sublabel: '60 min · 3 questions', desc: 'Realistic interview length' },
    { key: 'custom', label: 'Custom', sublabel: 'You choose', desc: 'Set your own pace and depth' },
  ];

  return (
    <div className="mock-hub-page">
      {/* Topbar */}
      <header className="topbar landing-topbar">
        <div className="container topbar-inner landing-topbar-inner">
          <div className="landing-topbar-left">
            <Link className="brand-wordmark" to="/">datanest</Link>
          </div>
          <div className="landing-topbar-right">
            <div className="nav-dropdown">
              <button className="topbar-auth-link nav-dropdown-trigger" type="button">
                Practice ▾
              </button>
              <div className="nav-dropdown-menu">
                {['sql', 'python', 'python-data', 'pyspark'].map(t => (
                  <Link key={t} className="nav-dropdown-item" to={`/practice/${t}`}>
                    {TRACK_META[t].label}
                  </Link>
                ))}
              </div>
            </div>
            <Link className="topbar-auth-link topbar-auth-link--active" to="/mock">Mock</Link>
            <Link className="topbar-auth-link" to="/dashboard">Dashboard</Link>
            <button className="theme-toggle" onClick={cycleTheme} aria-label="Toggle theme">
              {themeIcon}
            </button>
            {user && (
              <>
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>Sign out</button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mock-hub-main">
        {/* Hero */}
        <section className="mock-hub-hero">
          <h1 className="mock-hub-title">Mock Interview</h1>
          <p className="mock-hub-subtitle">Simulate real interview conditions with a countdown timer.</p>
        </section>

        {/* Mode selector */}
        <section className="mock-hub-section">
          <div className="mock-mode-cards">
            {modeCards.map(card => (
              <button
                key={card.key}
                type="button"
                className={`mock-mode-card ${mode === card.key ? 'selected' : ''}`}
                onClick={() => setMode(card.key)}
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
                    onClick={() => setTrack(t)}
                  >
                    {TRACK_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>
            <div className="mock-hub-config-row">
              <span className="mock-hub-config-label">Difficulty</span>
              <div className="mock-config-pills">
                {DIFFICULTIES.map(d => (
                  <button
                    key={d}
                    type="button"
                    className={`mock-config-pill ${difficulty === d ? 'active' : ''}`}
                    onClick={() => setDifficulty(d)}
                  >
                    {DIFFICULTY_LABELS[d]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Start button */}
        {startError && <p className="mock-hub-error">{startError}</p>}
        <section className="mock-hub-section">
          <button
            className="btn btn-primary mock-start-btn"
            onClick={handleStart}
            disabled={starting}
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
          <section className="mock-hub-section">
            <p className="mock-hub-empty">No mock sessions yet. Start your first one above.</p>
          </section>
        )}
      </main>
    </div>
  );
}
