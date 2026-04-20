import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useTopic } from '../contexts/TopicContext';
import { useAuth } from '../contexts/AuthContext';
import TrackProgressBar from '../components/TrackProgressBar';
import PathProgressCard from '../components/PathProgressCard';
import TierBanner from '../components/TierBanner';
import UpgradeButton from '../components/UpgradeButton';
import Skeleton from '../components/Skeleton';

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
  const { user } = useAuth();

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

  const easySolved = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'easy');
    return g ? g.questions.filter(q => q.state === 'solved').length : 0;
  }, [catalog]);
  const mediumSolved = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'medium');
    return g ? g.questions.filter(q => q.state === 'solved').length : 0;
  }, [catalog]);
  const easyTotal = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'easy');
    return g ? g.questions.length : 0;
  }, [catalog]);
  const mediumTotal = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'medium');
    return g ? g.questions.length : 0;
  }, [catalog]);
  const hardTotal = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'hard');
    return g ? g.questions.length : 0;
  }, [catalog]);
  const mediumUnlocked = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'medium');
    return g ? g.questions.some(q => q.state !== 'locked') : false;
  }, [catalog]);
  const hardUnlocked = useMemo(() => {
    const g = catalog?.groups?.find(x => x.difficulty === 'hard');
    return g ? g.questions.some(q => q.state !== 'locked') : false;
  }, [catalog]);

  // Milestone detection
  const easyComplete = easyTotal > 0 && easySolved >= easyTotal;
  const mediumComplete = mediumTotal > 0 && mediumSolved >= mediumTotal;
  const hasLockedQuestions = useMemo(
    () => catalog?.groups?.some(g => g.questions.some(q => q.state === 'locked')) ?? false,
    [catalog]
  );
  // User has exhausted all accessible questions (nothing left to solve right now)
  const allAccessibleSolved = continueId === null && totalSolved > 0;

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
        <div className="track-hub-loading" aria-label={`Loading ${meta.label} questions`}>
          <Skeleton width="11rem" height="0.95rem" />
          <Skeleton width="20rem" height="2rem" />
          <Skeleton width="90%" height="0.85rem" />
          <Skeleton width="100%" height="10rem" />
        </div>
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
        <TierBanner
          plan={user?.plan ?? 'free'}
          easySolved={easySolved}
          mediumSolved={mediumSolved}
          easyTotal={easyTotal}
          mediumTotal={mediumTotal}
          mediumUnlocked={mediumUnlocked}
          hardUnlocked={hardUnlocked}
        />
        <div className="track-hub-header">
          <div className="track-hub-title-row">
            <h2 className="track-hub-title">{meta.label} Practice</h2>
            <span className="track-hub-tagline">{meta.tagline}</span>
          </div>
          <p className="track-hub-desc">{meta.description}</p>
        </div>

        <div className="card track-hub-progress-card">
          {continueId ? (
            <div className="track-hub-actions">
              <button className="btn btn-primary" onClick={handleContinue}>
                {totalSolved > 0 ? 'Continue where I left off' : 'Start practicing'} →
              </button>
            </div>
          ) : allAccessibleSolved && (
            <div className="track-hub-actions">
              {hasLockedQuestions ? (
                <UpgradeButton tier="pro" label="Upgrade to unlock the rest" source="hub_allsolved" />
              ) : (
                <Link to="/" className="btn btn-secondary">Explore another track →</Link>
              )}
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

        {/* All-accessible-solved milestone — celebrates completion before showing the upgrade wall */}
        {allAccessibleSolved && (user?.plan === 'free' || user?.plan === 'pro') && hasLockedQuestions && (
          <div className="track-hub-milestone track-hub-milestone-upgrade">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏁</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                You've solved every accessible {meta.label} question!
              </p>
              <p className="track-hub-milestone-desc">
                {user?.plan === 'free'
                  ? `That's ${totalSolved} questions down. Upgrade to unlock the full ${hardTotal > 0 ? `hard track (${hardTotal} questions)` : 'question bank'} and keep building.`
                  : `That's real depth. Upgrade to Elite for full access and unlimited mock interviews.`}
              </p>
              <div className="track-hub-milestone-actions">
                {user?.plan === 'free' && (
                  <UpgradeButton tier="pro" label="Unlock Pro — all medium & hard" compact source="hub_milestone_allsolved" />
                )}
                <UpgradeButton tier="elite" label="Unlock Elite" compact source="hub_milestone_allsolved_elite" />
              </div>
            </div>
          </div>
        )}

        {/* Full track completion — for Pro/Elite users who've solved everything */}
        {allAccessibleSolved && !hasLockedQuestions && totalSolved > 0 && (
          <div className="track-hub-milestone track-hub-milestone-complete">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏆</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                Track complete — all {totalSolved} {meta.label} questions solved!
              </p>
              <p className="track-hub-milestone-desc">
                Outstanding. Take a mock interview to put it under pressure, or pick up another track.
              </p>
              <div className="track-hub-milestone-actions">
                <Link to="/mock" className="btn btn-primary btn-compact">Take a mock interview →</Link>
                <Link to="/" className="btn btn-secondary btn-compact">Explore other tracks</Link>
              </div>
            </div>
          </div>
        )}

        {/* Medium-complete milestone — all medium solved, hard partially locked */}
        {!allAccessibleSolved && mediumComplete && (user?.plan === 'free') && (
          <div className="track-hub-milestone track-hub-milestone-tier">
            <span className="track-hub-milestone-icon" aria-hidden="true">🏆</span>
            <div className="track-hub-milestone-body">
              <p className="track-hub-milestone-title">
                You've mastered all {mediumTotal} medium questions!
              </p>
              <p className="track-hub-milestone-desc">
                Hard questions are partially unlocked. Upgrade to Pro for the full hard track and daily mock interviews.
              </p>
              <div className="track-hub-milestone-actions">
                <UpgradeButton tier="pro" label="Unlock all hard questions" compact source="hub_milestone_medium_complete" />
              </div>
            </div>
          </div>
        )}

        {topicPaths.length > 0 && (
          <section className="trackhub-paths">
            <div className="trackhub-paths-header">
              <h3 className="trackhub-paths-title">Learning paths</h3>
              {topicPaths.length > 2 && (
                <Link to={`/learn/${topic}`} className="trackhub-paths-viewall">
                  View all {topicPaths.length} →
                </Link>
              )}
            </div>
            <div className="trackhub-paths-grid">
              {topicPaths.slice(0, 2).map(p => (
                <PathProgressCard key={p.slug} path={p} compact />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
