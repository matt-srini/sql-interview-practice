import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useTopic } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';
import PathProgressCard from '../components/PathProgressCard';

function pickNextQuestionId(catalog) {
  if (!catalog) return null;
  const order = ['easy', 'medium', 'hard'];
  for (const diff of order) {
    const g = catalog.groups?.find((x) => x.difficulty === diff);
    if (!g) continue;
    const next = g.questions.find((q) => q.is_next) ?? g.questions.find((q) => q.state !== 'locked');
    if (next) return next.id;
  }
  return null;
}

function pickFirstQuestionId(catalog) {
  if (!catalog) return null;
  for (const g of (catalog.groups ?? [])) {
    const first = g.questions.find((q) => q.state !== 'locked');
    if (first) return first.id;
  }
  return null;
}

export default function TrackHubPage() {
  const { topic, meta } = useTopic();
  const { catalog, loading, error } = useCatalog();
  const navigate = useNavigate();

  const nextId = useMemo(() => pickNextQuestionId(catalog), [catalog]);
  const firstId = useMemo(() => pickFirstQuestionId(catalog), [catalog]);
  const continueId = nextId ?? firstId;

  const totalSolved = useMemo(() => {
    if (!catalog) return 0;
    return (catalog.groups ?? []).reduce((acc, g) => acc + g.questions.filter((q) => q.state === 'solved').length, 0);
  }, [catalog]);

  const totalQuestions = useMemo(() => {
    if (!catalog) return meta.totalQuestions;
    return (catalog.groups ?? []).reduce((acc, g) => acc + g.questions.length, 0);
  }, [catalog, meta]);

  const [topicPaths, setTopicPaths] = useState([]);
  useEffect(() => {
    api.get('/paths').then(r => setTopicPaths(r.data.filter(p => p.topic === topic))).catch(() => {});
  }, [topic]);

  function handleContinue() {
    if (continueId) {
      navigate(`/practice/${topic}/questions/${continueId}`);
    }
  }

  if (loading) {
    return (
      <main className="container track-hub-page" style={{ paddingTop: '2rem' }}>
        <p className="loading">Loading {meta.label} questions…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="container track-hub-page" style={{ paddingTop: '2rem' }}>
        <p className="error-box">{error}</p>
      </main>
    );
  }

  return (
    <main className="container track-hub-page">
      <div className="track-hub-inner">
        <div className="track-hub-header">
          <div className="track-hub-title-row">
            <h2 className="track-hub-title">{meta.label} Practice</h2>
            <span className="track-hub-tagline">{meta.tagline}</span>
          </div>
          <p className="track-hub-desc">{meta.description}</p>
        </div>

        <div className="card track-hub-progress-card">
          {continueId && (
            <div className="track-hub-actions">
              <button className="btn btn-primary" onClick={handleContinue}>
                {totalSolved > 0 ? 'Continue where I left off' : 'Start practicing'} →
              </button>
            </div>
          )}

          <div className="track-hub-progress-header">
            <span className="track-hub-progress-title">Overall Progress</span>
            <span className="track-hub-progress-count">{totalSolved} / {totalQuestions}</span>
          </div>
          <TrackProgressBar solved={totalSolved} total={totalQuestions} color={meta.color} showLabel={false} />

          {catalog?.groups?.length > 0 && (
            <div className="track-hub-diff-breakdown">
              {catalog.groups.map((g) => {
                const solved = g.questions.filter((q) => q.state === 'solved').length;
                const total = g.questions.length;
                return (
                  <div key={g.difficulty} className="track-hub-diff-row">
                    <span className={`badge badge-${g.difficulty}`}>{g.difficulty}</span>
                    <TrackProgressBar solved={solved} total={total} color={meta.color} showLabel={true} />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {topicPaths.length > 0 && (
          <section className="trackhub-paths">
            <h3 className="trackhub-paths-title">Learning paths</h3>
            <div className="trackhub-paths-grid">
              {topicPaths.map(p => (
                <PathProgressCard key={p.slug} path={p} compact />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
