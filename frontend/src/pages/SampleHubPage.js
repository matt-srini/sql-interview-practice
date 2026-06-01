import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import Topbar from '../components/Topbar';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_SLUGS, TRACK_META } from '../trackRegistry';

const DIFFICULTIES = ['easy', 'medium', 'hard'];

/**
 * Sample Hub — discovery surface for all 81 sample questions.
 *
 * Logged-in users see tried/total markers per (track, difficulty) tile.
 * Logged-out users see plain difficulty pills (no login required to try a sample).
 *
 * Reachable from:
 *   - Landing hero CTA "Try a free sample →"
 *   - Landing closer CTA "Try a free sample →"
 *   - Tracks Index secondary "Try sample →" links
 *   - Topbar Practice dropdown "Try a sample"
 */
export default function SampleHubPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);

  // Fetch tried-counts when logged in. Anonymous users skip — we don't show
  // the tried markers for them (matches the "no friction" promise — we don't
  // want them to feel surveilled before sign-up).
  useEffect(() => {
    if (!user) {
      setSummary(null);
      return;
    }
    api.get('/sample/summary')
      .then((res) => setSummary(res.data?.tracks ?? null))
      .catch(() => setSummary(null));
  }, [user]);

  return (
    <>
      <Helmet>
        <title>Free interview practice samples — datathink</title>
        <meta name="description" content="Try free interview practice questions across SQL, Python, Pandas, PySpark, statistics, ML fundamentals, experimentation, data engineering, and data modeling. No account required." />
        <meta property="og:title" content="Free interview practice samples — datathink" />
        <meta property="og:description" content="Try free interview practice questions across nine data tracks. No account required." />
        <meta property="og:url" content="https://datathink.co/sample" />
        <link rel="canonical" href="https://datathink.co/sample" />
      </Helmet>

      <Topbar />

      <main className="container sample-hub">
        <header className="sample-hub-header">
          <p className="lp-eyebrow">Free samples · no account required</p>
          <h1 className="sample-hub-title">Try any track. Pick a difficulty.</h1>
          <p className="sample-hub-sub">
            Nine tracks · three difficulties · three questions per cell — 81 free samples in total. Real execution where it applies. Reasoning questions where it matters.
          </p>
        </header>

        <div className="sample-hub-grid" role="list">
          {TRACK_SLUGS.map((slug) => {
            const meta = TRACK_META[slug];
            const trackCounts = summary?.[slug] ?? null;
            return (
              <article
                key={slug}
                role="listitem"
                className="sample-hub-card"
                style={{ '--track-color': meta.color }}
              >
                <div className="sample-hub-card-header">
                  <span className="lp-track-dot" style={{ background: meta.color }} aria-hidden="true" />
                  <h2 className="sample-hub-card-name">{meta.label}</h2>
                </div>
                <p className="sample-hub-card-desc">{meta.description}</p>
                <div className="sample-hub-diffs" role="group" aria-label={`${meta.label} difficulty`}>
                  {DIFFICULTIES.map((diff) => {
                    const cell = trackCounts?.[diff];
                    const tried = cell?.tried ?? 0;
                    const total = cell?.total ?? 3;
                    const isDone = user && tried >= total;
                    return (
                      <Link
                        key={diff}
                        to={`/sample/${slug}/${diff}`}
                        className={`sample-hub-diff-btn sample-hub-diff-btn--${diff}${isDone ? ' is-done' : ''}`}
                        aria-label={`Try ${diff} ${meta.label} sample${user ? ` — ${tried} of ${total} attempted` : ''}`}
                      >
                        <span className="sample-hub-diff-label">{diff.charAt(0).toUpperCase() + diff.slice(1)}</span>
                        {user && cell ? (
                          <span className="sample-hub-diff-meta">
                            {isDone ? '✓ all attempted' : tried > 0 ? `${tried}/${total} attempted` : 'Start →'}
                          </span>
                        ) : (
                          <span className="sample-hub-diff-meta sample-hub-diff-meta--ghost">
                            3 questions
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>

        <div className="sample-hub-footer">
          <p className="sample-hub-foot-copy">
            Samples don't unlock anything — they're a no-commitment way to see how each track thinks. Ready for the full {' '}
            <Link to="/" className="sample-hub-foot-link">876-question practice catalog</Link>?
          </p>
          <div className="sample-hub-foot-actions">
            <Link to="/auth" className="btn btn-primary">Create a free account →</Link>
          </div>
        </div>
      </main>
    </>
  );
}
