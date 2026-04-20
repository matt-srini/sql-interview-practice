import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';
import Topbar from '../components/Topbar';
import InsightStrip from '../components/InsightStrip';
import Skeleton from '../components/Skeleton';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const TRACK_LABELS = {
  sql: 'SQL', python: 'Python', 'python-data': 'Pandas', pyspark: 'PySpark', mixed: 'Mixed',
};

function formatMockTime(s) {
  if (s == null) return '—';
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export default function ProgressDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mockHistory, setMockHistory] = useState([]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get('/dashboard')
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load dashboard data.'))
      .finally(() => setLoading(false));

    api
      .get('/dashboard/insights')
      .then((res) => setInsights(res.data))
      .catch(() => setInsights(null));

    api.get('/mock/history')
      .then(r => setMockHistory(r.data.slice(0, 5)))
      .catch(() => {});
  }, []);

  const totalSolved = TOPICS.reduce((sum, topic) => {
    const trackData = data?.tracks?.[topic];
    return sum + (trackData?.solved ?? 0);
  }, 0);
  const showDashboardEmpty = !loading && !error && totalSolved === 0;

  return (
    <>
      <Topbar active="dashboard" />

      <main className="container dashboard-page">
        <div className="dashboard-heading">
          <h2 className="page-title">My Progress</h2>
          {user && <p className="page-subtitle">{user.name || user.email}</p>}
        </div>

        {loading && (
          <div className="dashboard-loading" aria-label="Loading dashboard">
            <p className="loading">Loading dashboard…</p>
            <Skeleton width="10rem" height="0.95rem" />
            <div className="dashboard-loading-strip">
              <Skeleton height="7rem" />
              <Skeleton height="7rem" />
              <Skeleton height="7rem" />
            </div>
            <Skeleton width="100%" height="15rem" />
          </div>
        )}
        {error && <p className="error-box">{error}</p>}

        {!loading && !error && (
          <>
            {showDashboardEmpty ? (
              <section className="dashboard-section dashboard-empty-state">
                <h3 className="dashboard-section-title">No progress yet</h3>
                <p className="dashboard-empty-copy">
                  Start solving any track to unlock your streak, concept weaknesses, and cross-track coaching.
                </p>
                <div className="dashboard-empty-actions">
                  <Link to="/practice/sql" className="btn btn-primary">Start SQL practice</Link>
                  <Link to="/learn" className="btn btn-secondary">Browse learning paths</Link>
                </div>
              </section>
            ) : (
              <InsightStrip insights={insights} />
            )}

            <div className="dashboard-split">
              <div className="dashboard-split-main">
                <section className="dashboard-section">
                  <h3 className="dashboard-section-title">Track Overview</h3>
                  <div className="dashboard-track-grid">
                    {TOPICS.map((topic) => {
                      const meta = TRACK_META[topic];
                      const trackData = data?.tracks?.[topic];
                      const solved = trackData?.solved ?? 0;
                      const total = trackData?.total ?? meta.totalQuestions;
                      const byDiff = trackData?.by_difficulty ?? {};

                      return (
                        <Link key={topic} className="dashboard-track-card" to={`/practice/${topic}`}>
                          <div className="dashboard-track-card-header" style={{ borderTopColor: meta.color }}>
                            <span className="dashboard-track-label">{meta.label}</span>
                            <span className="dashboard-track-tagline">{meta.tagline}</span>
                          </div>
                          <div className="dashboard-track-card-body">
                            <TrackProgressBar solved={solved} total={total} color={meta.color} />
                            <div className="dashboard-track-metrics">
                              <div className="dashboard-track-metric-row">
                                <span>Median solve time</span>
                                <strong>
                                  {typeof insights?.per_track?.[topic]?.median_solve_seconds === 'number'
                                    ? `${Math.round(insights.per_track[topic].median_solve_seconds / 60)} min`
                                    : '—'}
                                </strong>
                              </div>
                              <div className="dashboard-track-metric-row">
                                <span>Accuracy</span>
                                <strong>
                                  {typeof insights?.per_track?.[topic]?.accuracy_pct === 'number'
                                    ? `${Math.round(insights.per_track[topic].accuracy_pct * 100)}%`
                                    : '—'}
                                </strong>
                              </div>
                            </div>
                            {Object.entries(byDiff).length > 0 && (
                              <div className="dashboard-diff-breakdown">
                                {Object.entries(byDiff).map(([diff, counts]) => (
                                  <div key={diff} className="dashboard-diff-row">
                                    <span className={`badge badge-${diff}`}>{diff}</span>
                                    <span className="dashboard-diff-count">{counts.solved}/{counts.total}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </section>
              </div>

              <div className="dashboard-split-aside">
                <section className="dashboard-section">
                  <h3 className="dashboard-section-title">Recent Activity</h3>
                  {data?.recent_activity?.length > 0 ? (
                    <div className="dashboard-activity-list">
                      {data.recent_activity.slice(0, 10).map((item, i) => {
                        const meta = TRACK_META[item.topic];
                        return (
                          <div key={i} className="dashboard-activity-row">
                            <span className="dashboard-activity-icon" style={{ color: meta?.color }}>✓</span>
                            <span className="dashboard-activity-track">{meta?.label ?? item.topic}</span>
                            <span className={`badge badge-${item.difficulty}`}>{item.difficulty}</span>
                            <span className="dashboard-activity-title">#{item.question_id} {item.title}</span>
                            <span className="dashboard-activity-time">{formatRelativeTime(item.solved_at)}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="dashboard-activity-empty">
                      <span>You haven't solved any questions yet.</span>
                      <Link to="/learn/sql" className="dashboard-activity-empty-cta">Start the SQL learning paths →</Link>
                    </div>
                  )}
                </section>

                {data?.concepts_by_track && Object.keys(data.concepts_by_track).length > 0 && (
                  <section className="dashboard-section">
                    <h3 className="dashboard-section-title">Concepts by Track</h3>
                    {Object.entries(data.concepts_by_track).map(([topic, concepts]) => {
                      const meta = TRACK_META[topic];
                      if (!meta || !concepts?.length) return null;
                      return (
                        <div key={topic} className="dashboard-concepts-group">
                          <div className="dashboard-concepts-track-label" style={{ color: meta.color }}>
                            {meta.label}
                          </div>
                          <div className="concept-tags concept-tags-inline">
                            {concepts.map((c) => (
                              <span key={c} className="tag-concept">{c}</span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </section>
                )}
              </div>
            </div>

            {mockHistory.length > 0 && (
              <section className="dashboard-section dashboard-mock-section">
                <div className="dashboard-section-header">
                  <h3 className="dashboard-section-title">Mock Interviews</h3>
                  <Link to="/mock" className="dashboard-link">Start new →</Link>
                </div>
                <table className="mock-history-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Mode</th>
                      <th>Track</th>
                      <th>Difficulty</th>
                      <th>Score</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockHistory.map(s => (
                      <tr key={s.session_id}>
                        <td>{formatRelativeTime(s.started_at)}</td>
                        <td>{s.mode}</td>
                        <td>{TRACK_LABELS[s.track] || s.track}</td>
                        <td>
                          {s.difficulty && (
                            <span className={`badge badge-${s.difficulty}`}>{s.difficulty}</span>
                          )}
                        </td>
                        <td>{s.solved_count}/{s.total_count}</td>
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
          </>
        )}
      </main>
    </>
  );
}
