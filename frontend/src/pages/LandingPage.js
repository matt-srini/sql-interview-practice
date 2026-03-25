import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const SAMPLE_TILES = [
  {
    difficulty: 'easy',
    title: 'Warm up with an easy sample',
    copy: 'Start with the easy dedicated sample set. No challenge progress is recorded.',
  },
  {
    difficulty: 'medium',
    title: 'Try a medium sample',
    copy: 'Work through the medium dedicated sample set before committing to the challenge path.',
  },
  {
    difficulty: 'hard',
    title: 'Test a hard sample',
    copy: 'Use the hard dedicated sample set if you want to assess your ceiling immediately.',
  },
];

const TIMED_CHALLENGE_TILES = [
  {
    duration: '30 min',
    title: 'Paced interview set',
    mix: '1 easy + 2 medium',
    copy: 'Built for shorter recruiter screens and warm-up reps. You get one quick opener, then two medium questions that reward clean execution.',
    detail: 'Best for keeping pace without stretching into a full session.',
  },
  {
    duration: '60 min',
    title: 'Full round simulation',
    mix: '1 easy + 2 medium + 1 hard',
    copy: 'Closer to a full SQL interview arc. Start with a fast confidence builder, work through two core mediums, then finish with one deeper stretch problem.',
    detail: 'Best for realistic interview stamina and recovery after a miss.',
  },
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
              <button
                type="button"
                className="topbar-signout-btn"
                onClick={logout}
                aria-label="Sign out"
              >
                Sign out
              </button>
            </div>
          ) : (
            <Link className="topbar-auth-link" to="/auth">
              Sign in
            </Link>
          )}
        </div>
      </header>

      <main className="container landing-page">
        <section className="landing-hero">
          <div className="landing-hero-card">
            <span className="landing-kicker">Practice first, then commit</span>
            <h2 className="landing-title">Try a sample question or start the guided challenge.</h2>
            <p className="landing-copy">
              Each difficulty has a dedicated 3-question sample track separate from the challenge bank. When you are ready,
              move into structured practice and upcoming timed challenge formats designed around real interview pacing.
            </p>
            <div className="landing-actions">
              <Link className="btn btn-primary" to="/practice">
                Start the challenge
              </Link>
              <Link className="btn btn-secondary" to="/sample/easy">
                Try an easy sample
              </Link>
            </div>
          </div>

          <div className="landing-side-card">
            <span className="landing-side-kicker">Timed practice formats</span>
            <h2>Train for the shape of the interview, not just the questions.</h2>
            <p>
              The guided challenge remains the main path. Alongside it, timed modes should feel focused and realistic rather
              than gamified or random.
            </p>
            <div className="timed-mode-list">
              {TIMED_CHALLENGE_TILES.map((tile) => (
                <div key={tile.duration} className="timed-mode-tile" aria-label={`${tile.duration} challenge preview`}>
                  <div className="timed-mode-top">
                    <span className="timed-mode-duration">{tile.duration}</span>
                    <span className="timed-mode-status">Planned</span>
                  </div>
                  <h3>{tile.title}</h3>
                  <p className="timed-mode-mix">{tile.mix}</p>
                  <p className="timed-mode-copy">{tile.copy}</p>
                  <p className="timed-mode-detail">{tile.detail}</p>
                </div>
              ))}
            </div>
            <p className="landing-side-note">Samples stay sandboxed. Structured practice remains your persistent path.</p>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-section-header">
            <h2>Try a sample</h2>
            <p>Each tile launches the next unseen sample from that difficulty until all 3 are exhausted.</p>
          </div>

          <div className="sample-grid">
            {SAMPLE_TILES.map((tile) => (
              <Link key={tile.difficulty} className="sample-tile" to={`/sample/${tile.difficulty}`}>
                <span className={`badge badge-${tile.difficulty}`}>{tile.difficulty}</span>
                <h3>{tile.title}</h3>
                <p>{tile.copy}</p>
                <span className="sample-tile-footer">Open sample</span>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
