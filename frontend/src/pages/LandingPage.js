import { startTransition, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

const SAMPLES = [
  { difficulty: 'easy',   copy: '3 warm-up SQL questions. No progress recorded.' },
  { difficulty: 'medium', copy: '3 mid-tier SQL questions to test your range.' },
  { difficulty: 'hard',   copy: '3 hard SQL questions to find your ceiling.' },
];

export default function LandingPage() {
  const { user, logout } = useAuth();
  const [dashData, setDashData] = useState(null);
  const [activeTab, setActiveTab] = useState('sql');

  useEffect(() => {
    // Fetch progress data for authenticated users
    if (user) {
      api.get('/dashboard').then((res) => setDashData(res.data)).catch(() => {});
      return;
    }
    setDashData(null);
  }, [user]);

  const trackTabs = useMemo(
    () =>
      TOPICS.map((topic) => {
        const meta = TRACK_META[topic];
        const trackData = dashData?.tracks?.[topic];
        const solved = trackData?.solved ?? 0;
        const total = trackData?.total ?? meta.totalQuestions;
        const completion = total > 0 ? Math.round((solved / total) * 100) : 0;
        return {
          id: topic,
          label: meta.label,
          tagline: meta.tagline,
          description: meta.description,
          color: meta.color,
          solved,
          total,
          completion,
        };
      }),
    [dashData]
  );

  const tabs = useMemo(
    () => [
      ...trackTabs,
      {
        id: 'samples',
        label: 'SQL Samples',
        tagline: 'easy · medium · hard',
        description: 'Practice SQL sample questions without affecting challenge progress.',
        color: '#5B6AF0',
      },
    ],
    [trackTabs]
  );

  function handleTabChange(tabId) {
    startTransition(() => setActiveTab(tabId));
  }

  return (
    <>
      <header className="topbar landing-topbar">
        <div className="container topbar-inner landing-topbar-inner">
          <div className="landing-topbar-left">
            <h1 className="landing-brand">Data Interview Practice</h1>
          </div>
          <div className="landing-topbar-right">
            <Link className="topbar-auth-link" to="/dashboard">Dashboard</Link>
            {user ? (
              <div className="topbar-user-pill">
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>
                  Sign out
                </button>
              </div>
            ) : (
              <Link className="topbar-auth-link" to="/auth">Sign in</Link>
            )}
          </div>
        </div>
      </header>

      <main className="container landing-page">
        <section className="landing-tabs-shell">
          <div className="landing-tabs-heading">
            <h2 className="landing-title">Practice by track</h2>
            <p className="landing-copy">
              Choose a focus area, see progress at a glance, and jump straight into practice.
            </p>
          </div>

          <div className="landing-tabs-nav" role="tablist" aria-label="Track tabs">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`landing-tab-panel-${tab.id}`}
                  id={`landing-tab-${tab.id}`}
                  className={`landing-tab-btn ${isActive ? 'is-active' : ''}`}
                  onClick={() => handleTabChange(tab.id)}
                >
                  <span className="landing-tab-label">{tab.label}</span>
                  {tab.id !== 'samples' && (
                    <span className="landing-tab-meta">{tab.solved}/{tab.total}</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="landing-tab-panels">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;

              if (tab.id === 'samples') {
                return (
                  <section
                    key={tab.id}
                    id={`landing-tab-panel-${tab.id}`}
                    role="tabpanel"
                    aria-labelledby={`landing-tab-${tab.id}`}
                    hidden={!isActive}
                    className={`landing-tab-panel ${isActive ? 'is-active' : ''}`}
                  >
                    <div className="landing-panel-header">
                      <div>
                        <h3>SQL sample questions</h3>
                        <p>{tab.description}</p>
                      </div>
                      <span className="landing-panel-tag">No login required</span>
                    </div>
                    <div className="landing-samples-grid">
                      {SAMPLES.map(({ difficulty, copy }) => (
                        <Link key={difficulty} className="sample-tile" to={`/sample/${difficulty}`}>
                          <span className={`badge badge-${difficulty}`}>{difficulty}</span>
                          <p>{copy}</p>
                          <span className="sample-tile-footer">Open sample →</span>
                        </Link>
                      ))}
                    </div>
                  </section>
                );
              }

              const hasStarted = tab.solved > 0;
              const progressLabel = user
                ? `${tab.completion}% complete`
                : `${tab.total} challenge questions`;

              return (
                <section
                  key={tab.id}
                  id={`landing-tab-panel-${tab.id}`}
                  role="tabpanel"
                  aria-labelledby={`landing-tab-${tab.id}`}
                  hidden={!isActive}
                  className={`landing-tab-panel ${isActive ? 'is-active' : ''}`}
                >
                  <div className="landing-panel-header">
                    <div>
                      <h3>{tab.label}</h3>
                      <p>{tab.description}</p>
                    </div>
                    <span className="landing-panel-tag" style={{ borderColor: tab.color, color: tab.color }}>
                      {progressLabel}
                    </span>
                  </div>

                  <div className="landing-panel-body">
                    <div className="landing-panel-progress">
                      <TrackProgressBar solved={tab.solved} total={tab.total} color={tab.color} />
                      <span className="landing-panel-progress-copy">
                        {user
                          ? `${tab.solved} solved out of ${tab.total}`
                          : `Sign in to persist progress across sessions`}
                      </span>
                    </div>
                    <div className="landing-panel-actions">
                      <Link className="btn btn-primary" to={`/practice/${tab.id}`}>
                        {hasStarted ? 'Continue track' : 'Start track'} →
                      </Link>
                      {!user && <Link className="btn btn-secondary" to="/auth">Create account</Link>}
                    </div>
                  </div>
                </section>
              );
            })}
          </div>
        </section>
      </main>
    </>
  );
}
