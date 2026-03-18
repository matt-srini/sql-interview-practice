import { Link } from 'react-router-dom';

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

export default function LandingPage() {
  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <h1>SQL Interview Practice</h1>
        </div>
      </header>

      <main className="container landing-page">
        <section className="landing-hero">
          <div className="landing-hero-card">
            <span className="landing-kicker">Practice first, then commit</span>
            <h2 className="landing-title">Try a sample question or start the guided challenge.</h2>
            <p className="landing-copy">
              Each difficulty has a dedicated 3-question sample track separate from the challenge bank. When you are ready,
              switch into challenge mode and unlock questions in order.
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
            <h2>How it works</h2>
            <p>The challenge path tracks what you have solved in this browser session. Sample mode is a sandbox.</p>
            <ul className="landing-checklist">
              <li>Each difficulty has exactly 3 dedicated sample questions.</li>
              <li>Samples are separate from the challenge pool and do not affect progression.</li>
              <li>Challenge mode unlocks the next problem only after you solve the current one.</li>
              <li>Direct links to locked questions are blocked by the backend.</li>
            </ul>
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