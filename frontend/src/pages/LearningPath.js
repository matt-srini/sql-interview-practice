import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { useTheme } from '../App';

const DIFFICULTY_COLORS = {
  easy: 'var(--success)',
  medium: 'var(--warning)',
  hard: 'var(--danger)',
};

export default function LearningPath() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();

  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);

  function cycleTheme() {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  }
  const themeIcon = theme === 'system' ? '◐' : resolvedTheme === 'dark' ? '☀' : '☾';

  useEffect(() => {
    api.get(`/paths/${slug}`)
      .then(r => setPath(r.data))
      .catch(err => {
        if (err?.response?.status === 404) {
          navigate('/', { replace: true });
        }
      })
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  const meta = path ? (TRACK_META[path.topic] || TRACK_META['sql']) : TRACK_META['sql'];
  const pct = path && path.question_count > 0 ? (path.solved_count / path.question_count) * 100 : 0;

  // Find the first non-solved unlocked question index for highlighting
  const nextIndex = path
    ? path.questions.findIndex(q => q.state === 'unlocked')
    : -1;

  return (
    <div className="learn-page">
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
            <Link className="topbar-auth-link" to="/mock">Mock</Link>
            <Link className="topbar-auth-link" to="/dashboard">Dashboard</Link>
            <button className="theme-toggle" onClick={cycleTheme} aria-label="Toggle theme">
              {themeIcon}
            </button>
            {user ? (
              <>
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>Sign out</button>
              </>
            ) : (
              <Link className="topbar-auth-link" to="/auth">Sign in</Link>
            )}
          </div>
        </div>
      </header>

      {loading && (
        <div className="learn-loading">Loading path…</div>
      )}

      {!loading && path && (
        <>
          {/* Path header */}
          <section className="learn-header">
            <div className="container learn-header-inner">
              <nav className="learn-breadcrumb" aria-label="breadcrumb">
                <Link to="/">Practice</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <span>Learning Paths</span>
                <span className="learn-breadcrumb-sep">›</span>
                <span>{path.title}</span>
              </nav>
              <h1 className="learn-title">{path.title}</h1>
              <p className="learn-description">{path.description}</p>
              <div className="learn-progress">
                <div className="learn-progress-bar">
                  <div
                    className="learn-progress-fill"
                    style={{ width: `${pct}%`, background: meta.color }}
                  />
                </div>
                <span className="learn-progress-label">
                  {path.solved_count} / {path.question_count} complete
                </span>
              </div>
            </div>
          </section>

          {/* Question list */}
          <section className="learn-body">
            <div className="learn-question-list">
              {path.questions.map((q, i) => {
                const isNext = i === nextIndex;
                const isSolved = q.state === 'solved';
                const isLocked = q.state === 'locked';

                let rowClass = 'learn-question-row';
                if (isSolved) rowClass += ' learn-question-row--solved';
                else if (isNext) rowClass += ' learn-question-row--next';
                else if (isLocked) rowClass += ' learn-question-row--locked';

                const questionUrl = `/practice/${path.topic}/questions/${q.id}`;

                return (
                  <div key={q.id} className={rowClass}>
                    <span className="learn-question-num">{i + 1}</span>
                    <span className="learn-question-status" aria-label={q.state}>
                      {isSolved ? '✓' : isLocked ? '🔒' : '→'}
                    </span>
                    <span className="learn-question-title">
                      {isLocked ? q.title : (
                        <Link to={questionUrl}>{q.title}</Link>
                      )}
                    </span>
                    <span
                      className="learn-question-difficulty"
                      style={{ color: DIFFICULTY_COLORS[q.difficulty] }}
                    >
                      {q.difficulty}
                    </span>
                    {!isLocked && (
                      <Link
                        to={questionUrl}
                        className="learn-question-btn"
                      >
                        {isSolved ? 'Review →' : isNext ? 'Start →' : 'Open →'}
                      </Link>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
