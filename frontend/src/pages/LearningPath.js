import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { TRACK_META } from '../contexts/TopicContext';
import Topbar from '../components/Topbar';

const DIFFICULTY_COLORS = {
  easy: 'var(--success)',
  medium: 'var(--warning)',
  hard: 'var(--danger)',
};

export default function LearningPath() {
  const { slug } = useParams();
  const navigate = useNavigate();

  const [path, setPath] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/paths/${slug}`)
      .then(r => setPath(r.data))
      .catch(err => {
        if (err?.response?.status === 404) {
          navigate('/', { replace: true });
        }
      })
      .finally(() => setLoading(false));
  }, [slug, navigate]);

  const meta = path ? (TRACK_META[path.topic] || TRACK_META['sql']) : TRACK_META['sql'];
  const pct = path && path.question_count > 0 ? (path.solved_count / path.question_count) * 100 : 0;

  // Find the first non-solved unlocked question index for highlighting
  const nextIndex = path
    ? path.questions.findIndex(q => q.state === 'unlocked')
    : -1;

  return (
    <div className="learn-page">
      <Topbar />

      {loading && (
        <div className="learn-loading">Loading path…</div>
      )}

      {!loading && path && (
        <>
          {/* Path header */}
          <section className="learn-header">
            <div className="container learn-header-inner">
              <nav className="learn-breadcrumb" aria-label="breadcrumb">
                <Link to="/">Practice</Link>
                <span className="learn-breadcrumb-sep">›</span>
                <span>Learning Paths</span>
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

          {/* Question list */}
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

                const questionUrl = `/practice/${path.topic}/questions/${q.id}?path=${path.slug}`;

                return (
                  <div key={q.id} className={rowClass}>
                    <span className="learn-question-num">{i + 1}</span>
                    <span className="learn-question-status" aria-label={q.state}>
                      {isSolved ? '✓' : isLocked ? '🔒' : '→'}
                    </span>
                    <span className="learn-question-title">
                      {isLocked ? q.title : (
                        <Link to={questionUrl}>{q.title}</Link>
                      )}
                    </span>
                    <span
                      className="learn-question-difficulty"
                      style={{ color: DIFFICULTY_COLORS[q.difficulty] }}
                    >
                      {q.difficulty}
                    </span>
                    {!isLocked && (
                      <Link
                        to={questionUrl}
                        className="learn-question-btn"
                      >
                        {isSolved ? 'Review →' : isNext ? 'Start →' : 'Open →'}
                      </Link>
                    )}
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
