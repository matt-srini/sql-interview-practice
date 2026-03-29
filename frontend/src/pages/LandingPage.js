import { useEffect, useState } from 'react';
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

  useEffect(() => {
    // Fetch progress data for authenticated users
    if (user) {
      api.get('/dashboard').then((res) => setDashData(res.data)).catch(() => {});
    }
  }, [user]);

  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <h1>Data Interview Practice</h1>
          <div className="topbar-right">
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
        {!user && (
          <section className="landing-hero">
            <span className="landing-kicker">SQL · Python · PySpark · pandas</span>
            <h2 className="landing-title">Get sharp at data interviews.</h2>
            <p className="landing-copy">
              Four tracks covering SQL, algorithms, data manipulation, and Spark.
              Work through structured question banks with instant feedback.
            </p>
            <div className="landing-actions">
              <a className="btn btn-primary" href="#tracks">Explore tracks ↓</a>
              <Link className="btn btn-secondary" to="/auth">Create account</Link>
            </div>
          </section>
        )}

        <section className="track-tiles" id="tracks">
          {TOPICS.map((topic) => {
            const meta = TRACK_META[topic];
            const trackData = dashData?.tracks?.[topic];
            const solved = trackData?.solved ?? 0;
            const total = trackData?.total ?? meta.totalQuestions;
            const hasStarted = solved > 0;

            return (
              <Link key={topic} className="track-tile" to={`/practice/${topic}`}>
                <div className="track-tile-header" style={{ borderLeftColor: meta.color }}>
                  <span className="track-tile-label">{meta.label}</span>
                  <span className="track-tile-tagline">{meta.tagline}</span>
                </div>
                <div className="track-tile-body">
                  <p className="track-tile-desc">{meta.description}</p>
                  <div className="track-tile-footer">
                    {user && (
                      <TrackProgressBar solved={solved} total={total} color={meta.color} />
                    )}
                    {!user && (
                      <span className="track-tile-count">{meta.totalQuestions} questions</span>
                    )}
                    <span className="track-tile-cta" style={{ color: meta.color }}>
                      {hasStarted ? 'Continue →' : 'Start →'}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </section>

        <section className="landing-samples">
          <p className="landing-samples-label">SQL Samples — try without an account</p>
          {SAMPLES.map(({ difficulty, copy }) => (
            <Link key={difficulty} className="sample-tile" to={`/sample/${difficulty}`}>
              <span className={`badge badge-${difficulty}`}>{difficulty}</span>
              <p>{copy}</p>
              <span className="sample-tile-footer">Open sample →</span>
            </Link>
          ))}
        </section>
      </main>
    </>
  );
}
