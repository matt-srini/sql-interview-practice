import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { TRACK_META } from '../contexts/TopicContext';
import { useAuth } from '../contexts/AuthContext';
import Topbar from '../components/Topbar';
import UpgradeButton from '../components/UpgradeButton';

const DIFFICULTY_COLORS = {
  easy: 'var(--success)',
  medium: 'var(--warning)',
  hard: 'var(--danger)',
};

export default function LearningPath() {
  const { topic, slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);

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
  const isCompleted = Boolean(path && path.question_count > 0 && path.solved_count === path.question_count);

  const firstLockedIdx = path ? path.questions.findIndex(q => q.state === 'locked') : -1;
  const firstLockedDiff = firstLockedIdx >= 0 ? path.questions[firstLockedIdx].difficulty : null;
  const plan = user?.plan ?? 'free';
  const role = path?.role;
  const accessible = path?.accessible !== false;

  // Determine unlock hint messaging
  function getUnlockCards() {
    if (!firstLockedDiff || plan === 'elite') return null;
    const trackLabel = meta.label;

    // Earn-it card (threshold-based)
    let earnCard = null;
    if (plan === 'free') {
      if (firstLockedDiff === 'medium') {
        earnCard = {
          copy: `Solve 8 more easy ${trackLabel} questions to unlock medium.`,
          ctaLink: `/practice/${path.topic}`,
          ctaLabel: `Open ${trackLabel} practice →`,
        };
      } else if (firstLockedDiff === 'hard') {
        earnCard = {
          copy: `Solve 8 more medium ${trackLabel} questions to unlock hard.`,
          ctaLink: `/practice/${path.topic}`,
          ctaLabel: `Open ${trackLabel} practice →`,
        };
      }
    }

    // Skip-ahead card (upgrade)
    const skipCard = plan !== 'elite' ? {
      copy: firstLockedDiff === 'hard' && plan === 'pro'
        ? null
        : `Or unlock all ${firstLockedDiff} + ${firstLockedDiff === 'medium' ? 'hard' : ''} questions instantly with Pro.`,
      upgradeTier: plan === 'free' ? 'pro' : 'elite',
    } : null;

    return { earnCard, skipCard };
  }

  const unlockCards = path ? getUnlockCards() : null;

  // Path role chip copy
  function getRoleChip() {
    if (!role || !path) return null;
    const pathState = path.path_state;
    if (role === 'starter') {
      if (pathState?.starter_done) return { text: 'Completed · medium unlocked', done: true };
      return { text: 'Complete to unlock all medium in this track', done: false };
    }
    if (role === 'intermediate') {
      if (pathState?.intermediate_done) return { text: 'Completed · hard unlocked', done: true };
      return { text: 'Complete to unlock hard questions in this track', done: false };
    }
    return null;
  }

  const roleChip = getRoleChip();

  return (
    <div className="learn-page">
      <Helmet>
        <title>{path ? `${path.title} — datanest` : 'Learning Path — datanest'}</title>
        {path && <meta name="description" content={`${path.title}: a curated ${meta.label} learning path on datanest. Practice interview-style questions with instant feedback.`} />}
        <meta property="og:title" content={path ? `${path.title} — datanest` : 'Learning Path — datanest'} />
      </Helmet>
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

              {/* Role chip — shown on free starter/intermediate paths */}
              {roleChip && plan === 'free' && (
                <div className={`learn-role-chip${roleChip.done ? ' learn-role-chip--done' : ''}`}>
                  {roleChip.done ? '✓' : '→'} {roleChip.text}
                </div>
              )}

              {/* Path not accessible — show tier badge */}
              {!accessible && (
                <span className="learn-tier-badge learn-tier-badge--pro">Pro</span>
              )}

              {accessible && (
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
              )}

              {accessible && isCompleted && (
                <div className="learn-path-complete-banner" role="status" aria-live="polite">
                  <div>
                    <strong>Path complete.</strong> You finished every question in this path.
                  </div>
                  <Link to={`/learn/${path.topic}`} className="btn btn-secondary btn-compact">
                    What's next →
                  </Link>
                </div>
              )}
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

                // Locked questions are navigable in preview mode
                const questionUrl = `/practice/${path.topic}/questions/${q.id}?path=${slug}`;

                return (
                  <div key={q.id}>
                    <div className={rowClass}>
                      <span className="learn-question-num">{i + 1}</span>
                      <span className="learn-question-status" aria-label={q.state}>
                        {isSolved ? '✓' : isLocked ? '🔒' : '→'}
                      </span>
                      <span className="learn-question-title">
                        {/* All questions are now navigable (preview mode for locked) */}
                        <Link to={questionUrl}>{q.title}</Link>
                      </span>
                      <span
                        className="learn-question-difficulty"
                        style={{ color: DIFFICULTY_COLORS[q.difficulty] }}
                      >
                        {q.difficulty}
                      </span>
                      <Link to={questionUrl} className="learn-question-btn">
                        {isSolved ? 'Review →' : isNext ? 'Start →' : isLocked ? 'Preview →' : 'Open →'}
                      </Link>
                    </div>
                  </div>
                );
              })}

              {/* Unlock hint: two stacked cards at the bottom */}
              {unlockCards && (unlockCards.earnCard || unlockCards.skipCard?.copy) && (
                <div className="learn-unlock-cards">
                  {unlockCards.earnCard && (
                    <div className="learn-unlock-card learn-unlock-card--earn">
                      <p className="learn-unlock-card-copy">{unlockCards.earnCard.copy}</p>
                      <Link to={unlockCards.earnCard.ctaLink} className="btn btn-secondary btn-compact">
                        {unlockCards.earnCard.ctaLabel}
                      </Link>
                    </div>
                  )}
                  {unlockCards.skipCard?.copy && (
                    <div className="learn-unlock-card learn-unlock-card--upgrade">
                      <p className="learn-unlock-card-copy">{unlockCards.skipCard.copy}</p>
                      <UpgradeButton
                        tier={unlockCards.skipCard.upgradeTier}
                        compact
                        source="learning_path_hint"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
