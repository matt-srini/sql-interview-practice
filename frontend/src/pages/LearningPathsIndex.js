import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { TRACK_META } from '../contexts/TopicContext';
import { TRACK_SLUGS } from '../trackRegistry';
import PathProgressCard from '../components/PathProgressCard';
import Topbar from '../components/Topbar';

export default function LearningPathsIndex() {
  const { topic } = useParams(); // present on /learn/:topic, absent on /learn
  const [searchParams] = useSearchParams();
  const q = searchParams.get('q')?.trim().toLowerCase() ?? '';
  const [paths, setPaths] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/paths')
      .then(r => setPaths(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const topicFiltered = topic ? paths.filter(p => p.topic === topic) : paths;
  const filtered = q
    ? topicFiltered.filter(p =>
        p.title.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q) ||
        p.focus_concepts?.some(c => c.toLowerCase().includes(q))
      )
    : topicFiltered;

  // Group by topic when showing all. Within each track, order paths by
  // (level, display_order) — foundational first, then intermediate, then
  // advanced; within each level by the author-curated conceptual progression.
  const _levelOrder = { foundational: 0, intermediate: 1, advanced: 2 };
  const _sortByDisplay = (a, b) => {
    const lvl = (_levelOrder[a.level] ?? 3) - (_levelOrder[b.level] ?? 3);
    if (lvl !== 0) return lvl;
    return (a.display_order ?? 999) - (b.display_order ?? 999);
  };
  const grouped = TRACK_SLUGS.map(t => ({
    topic: t,
    meta: TRACK_META[t],
    paths: filtered.filter(p => p.topic === t).slice().sort(_sortByDisplay),
  })).filter(g => g.paths.length > 0);

  const pageTitle = q
    ? `Search: "${searchParams.get('q')}" — Learning Paths`
    : topic
      ? `${TRACK_META[topic]?.label ?? topic} Learning Paths`
      : 'Learning Paths';

  return (
    <div className="learn-index-page">
      <Helmet>
        <title>{pageTitle} — datathink</title>
        <meta name="description" content={topic ? `Curated ${TRACK_META[topic]?.label ?? topic} learning paths to build interview-ready skills step by step.` : 'Curated SQL, Python, Pandas, and PySpark learning paths to build interview-ready skills step by step.'} />
        <meta property="og:title" content={`${pageTitle} — datathink`} />
        <meta property="og:description" content={topic ? `Curated ${TRACK_META[topic]?.label ?? topic} learning paths to build interview-ready skills step by step.` : 'Curated SQL, Python, Pandas, and PySpark learning paths to build interview-ready skills step by step.'} />
        <meta property="og:url" content={topic ? `https://datathink.co/learn/${topic}` : 'https://datathink.co/learn'} />
        <meta property="og:image" content="https://datathink.co/og-image.png?v=2" />
        <link rel="canonical" href={topic ? `https://datathink.co/learn/${topic}` : 'https://datathink.co/learn'} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://datathink.co/og-image.png?v=2" />
        {paths.length > 0 && <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "ItemList",
          "name": topic ? `${TRACK_META[topic]?.label ?? topic} Learning Paths` : "Data Interview Practice Learning Paths",
          "url": topic ? `https://datathink.co/learn/${topic}` : "https://datathink.co/learn",
          "itemListElement": (topic ? paths.filter(p => p.topic === topic) : paths).map((p, i) => ({
            "@type": "ListItem",
            "position": i + 1,
            "name": p.title,
            "url": `https://datathink.co/learn/${p.topic}/${p.slug}`
          }))
        })}</script>}
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
            Curated routes through the practice catalog — the same questions, in a deliberate order.
            Solve one in either place and it's marked done in both.
          </p>
          <Link
            to={topic ? `/practice/${topic}` : '/practice/sql'}
            className="learn-index-catalog-link"
          >
            Browse the full catalog →
          </Link>

          {!topic && (
            <div className="learn-index-topic-pills">
              {TRACK_SLUGS.filter(t => paths.some(p => p.topic === t)).map(t => (
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
              <p>{q ? `No paths matched "${searchParams.get('q')}".` : 'No paths found for this track yet.'}</p>
              <div className="learn-index-empty-actions">
                {q ? (
                  <Link to="/learn" className="btn btn-primary">Browse all paths</Link>
                ) : (
                  <>
                    <Link to="/practice/sql" className="btn btn-primary">Start SQL practice</Link>
                    <Link to="/dashboard" className="btn btn-secondary">View dashboard</Link>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
