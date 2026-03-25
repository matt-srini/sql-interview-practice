import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const SAMPLES = [
  { difficulty: 'easy',   copy: '3 warm-up questions. No progress recorded.' },
  { difficulty: 'medium', copy: '3 mid-tier questions to test your range.' },
  { difficulty: 'hard',   copy: '3 hard questions to find your ceiling.' },
];

export default function LandingPage() {
  const { user, logout } = useAuth();

  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <h1>SQL Interview Practice</h1>
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
      </header>

      <main className="container landing-page">
        <section className="landing-hero">
          <span className="landing-kicker">86 questions · easy, medium, hard</span>
          <h2 className="landing-title">Get sharp at SQL interviews.</h2>
          <p className="landing-copy">
            Structured practice with real queries and realistic datasets.
            Work through the challenge bank or warm up with a free sample.
          </p>
          <div className="landing-actions">
            <Link className="btn btn-primary" to="/practice">Start the challenge</Link>
            <Link className="btn btn-secondary" to="/sample/easy">Try a sample</Link>
          </div>
        </section>

        <section className="landing-samples">
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
