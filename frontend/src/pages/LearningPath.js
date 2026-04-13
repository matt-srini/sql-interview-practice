import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { TRACK_META } from '../contexts/TopicContext';
import { useAuth } from '../contexts/AuthContext';
import Topbar from '../components/Topbar';

const DIFFICULTY_COLORS = {
  easy: 'var(--success)',
  medium: 'var(--warning)',
  hard: 'var(--danger)',
};

function getUnlockHint(plan, difficulty) {
  if (!difficulty || plan === 'elite') return null;
  if (difficulty === 'medium') {
    return {
      progress: 'Solve 10 easy questions across all tracks to unlock medium questions.',
      upgradeTarget: plan === 'free' ? 'pro' : null,
      upgradeLabel: 'Upgrade to Pro for instant access',
    };
  }
  if (difficulty === 'hard') {
    if (plan === 'pro') {
      return { progress: null, upgradeTarget: 'elite', upgradeLabel: 'Upgrade to Elite for full hard access' };
    }
    return {
      progress: 'Solve 10 medium questions across all tracks to unlock hard questions.',
      upgradeTarget: 'pro',
      upgradeLabel: 'Upgrade to Pro for instant access',
    };
  }
  return { progress: 'Upgrade your plan to unlock these questions.', upgradeTarget: null, upgradeLabel: null };
}

export default function LearningPath() {
  const { topic, slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgradePending, setUpgradePending] = useState(false);

  async function handleUpgrade(plan) {
    setUpgradePending(true);
    try {
      const r = await api.post('/stripe/create-checkout', { plan });
      window.location.assign(r.data.checkout_url);
    } catch {
      setUpgradePending(false);
    }
  }

  useEffect(() => {
    api.get(`/paths/${slug}`)
      .then(r => setPath(r.data))
      .catch(err => {
        if (err?.response?.status === 404) {
          navigate('/learn', { replace: true });
        }
      })
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  const meta = path ? (TRACK_META[path.topic] || TRACK_META['sql']) : TRACK_META['sql'];
  const pct = path && path.question_count > 0 ? (path.solved_count / path.question_count) * 100 : 0;
  const nextIndex = path ? path.questions.findIndex(q => q.state === 'unlocked') : -1;
  const topicLabel = meta.label;

  const firstLockedIdx = path ? path.questions.findIndex(q => q.state === 'locked') : -1;
  const firstLockedDiff = firstLockedIdx >= 0 ? path.questions[firstLockedIdx].difficulty : null;
  const unlockHint = getUnlockHint(user?.plan ?? 'free', firstLockedDiff);

  return (
    <div className="learn-page">
      <Topbar />

      {loading && <div className="learn-loading">Loading path…</div>}

      {!loading && path && (
        <>
          <section className="learn-header">
            <div className="container learn-header-inner">
              <nav className="learn-breadcrumb" aria-label="breadcrumb">
                <Link to="/">Practice</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <Link to="/learn">Learning Paths</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <Link to={`/learn/${topic}`}>{topicLabel}</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <span>{path.title}</span>
              </nav>
              <h1 className="learn-title">{path.title}</h1>
              <p className="learn-description">{path.description}</p>
              <div className="learn-progress">
                <div className="learn-progress-bar">
                  <div
                    className="learn-progress-fill"
                    style={{ width: `${pct}%`, background: meta.color }}
                  />
                </div>
                <span className="learn-progress-label">
                  {path.solved_count} / {path.question_count} complete
                </span>
              </div>
            </div>
          </section>

          <section className="learn-body">
            <div className="learn-question-list">
              {path.questions.map((q, i) => {
                const isNext = i === nextIndex;
                const isSolved = q.state === 'solved';
                const isLocked = q.state === 'locked';

                let rowClass = 'learn-question-row';
                if (isSolved) rowClass += ' learn-question-row--solved';
                else if (isNext) rowClass += ' learn-question-row--next';
                else if (isLocked) rowClass += ' learn-question-row--locked';

                const questionUrl = `/practice/${path.topic}/questions/${q.id}?path=${slug}`;

                return (
                  <div key={q.id}>
                    {i === firstLockedIdx && unlockHint && (
                      <div className="learn-unlock-hint">
                        <span className="learn-unlock-hint-icon">🔒</span>
                        {unlockHint.progress && (
                          <span className="learn-unlock-hint-text">{unlockHint.progress}</span>
                        )}
                        {unlockHint.upgradeTarget && (
                          <button
                            className="btn btn-primary btn-compact"
                            onClick={() => handleUpgrade(unlockHint.upgradeTarget)}
                            disabled={upgradePending}
                          >
                            {upgradePending ? 'Redirecting…' : unlockHint.upgradeLabel}
                          </button>
                        )}
                      </div>
                    )}
                    <div className={rowClass}>
                      <span className="learn-question-num">{i + 1}</span>
                      <span className="learn-question-status" aria-label={q.state}>
                        {isSolved ? '✓' : isLocked ? '🔒' : '→'}
                      </span>
                      <span className="learn-question-title">
                        {isLocked ? q.title : <Link to={questionUrl}>{q.title}</Link>}
                      </span>
                      <span
                        className="learn-question-difficulty"
                        style={{ color: DIFFICULTY_COLORS[q.difficulty] }}
                      >
                        {q.difficulty}
                      </span>
                      {!isLocked && (
                        <Link to={questionUrl} className="learn-question-btn">
                          {isSolved ? 'Review →' : isNext ? 'Start →' : 'Open →'}
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
