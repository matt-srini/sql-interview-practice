import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { TRACK_META } from '../contexts/TopicContext';
import PathProgressCard from '../components/PathProgressCard';
import Topbar from '../components/Topbar';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

export default function LearningPathsIndex() {
  const { topic } = useParams(); // present on /learn/:topic, absent on /learn
  const [paths, setPaths] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/paths')
      .then(r => setPaths(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = topic ? paths.filter(p => p.topic === topic) : paths;
  const inProgressPaths = filtered
    .filter((p) => p.solved_count >= 1 && p.solved_count < p.question_count)
    .slice()
    .sort((a, b) => {
      const aPct = a.question_count > 0 ? a.solved_count / a.question_count : 0;
      const bPct = b.question_count > 0 ? b.solved_count / b.question_count : 0;
      return bPct - aPct;
    });

  // Group by topic when showing all
  const grouped = TOPICS.map(t => ({
    topic: t,
    meta: TRACK_META[t],
    paths: filtered.filter(p => p.topic === t),
  })).filter(g => g.paths.length > 0);

  const pageTitle = topic
    ? `${TRACK_META[topic]?.label ?? topic} Learning Paths`
    : 'Learning Paths';

  return (
    <div className="learn-index-page">
      <Helmet>
        <title>{pageTitle} — datanest</title>
        <meta name="description" content={topic ? `Curated ${TRACK_META[topic]?.label ?? topic} learning paths to build interview-ready skills step by step.` : 'Curated SQL, Python, Pandas, and PySpark learning paths to build interview-ready skills step by step.'} />
        <meta property="og:title" content={`${pageTitle} — datanest`} />
      </Helmet>
      <Topbar />

      <section className="learn-index-header">
        <div className="container">
          <nav className="learn-breadcrumb" aria-label="breadcrumb">
            <Link to="/">Practice</Link>
            {topic ? (
              <>
                <span className="learn-breadcrumb-sep">›</span>
                <Link to="/learn">Learning Paths</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <span>{TRACK_META[topic]?.label ?? topic}</span>
              </>
            ) : (
              <>
                <span className="learn-breadcrumb-sep">›</span>
                <span>Learning Paths</span>
              </>
            )}
          </nav>
          <h1 className="learn-index-title">{pageTitle}</h1>
          <p className="learn-index-sub">
            Curated question sequences that build a skill from fundamentals to advanced.
          </p>

          {!topic && (
            <div className="learn-index-topic-pills">
              {TOPICS.filter(t => paths.some(p => p.topic === t)).map(t => (
                <Link
                  key={t}
                  className="learn-index-topic-pill"
                  to={`/learn/${t}`}
                  style={{ '--pill-color': TRACK_META[t].color }}
                >
                  {TRACK_META[t].label}
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="learn-index-body">
        <div className="container">
          {loading && <p className="loading">Loading paths…</p>}

          {!loading && inProgressPaths.length > 0 && (
            <div className="learn-index-progress-rail">
              <div className="learn-index-group-header">
                <h2 className="learn-index-group-title">In progress</h2>
              </div>
              <div className="learn-index-grid">
                {inProgressPaths.map((p) => (
                  <PathProgressCard key={`in-progress-${p.slug}`} path={p} />
                ))}
              </div>
            </div>
          )}

          {!loading && grouped.map(({ topic: t, meta, paths: tPaths }) => (
            <div key={t} className="learn-index-group">
              {!topic && (
                <div className="learn-index-group-header">
                  <h2 className="learn-index-group-title">
                    <span className="learn-index-group-dot" style={{ background: meta.color }} />
                    {meta.label}
                  </h2>
                  <Link className="learn-index-group-link" to={`/learn/${t}`}>
                    All {meta.label} paths →
                  </Link>
                </div>
              )}
              <div className="learn-index-grid">
                {tPaths.map(p => (
                  <PathProgressCard key={p.slug} path={p} />
                ))}
              </div>
            </div>
          ))}

          {!loading && filtered.length === 0 && (
            <div className="learn-index-empty">
              <p>No paths found for this track yet.</p>
              <div className="learn-index-empty-actions">
                <Link to="/practice/sql" className="btn btn-primary">Start SQL practice</Link>
                <Link to="/dashboard" className="btn btn-secondary">View dashboard</Link>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
