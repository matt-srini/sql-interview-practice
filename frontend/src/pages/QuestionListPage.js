import { useNavigate } from 'react-router-dom';
import { useCatalog } from '../catalogContext';

const DIFFICULTY_ORDER = { easy: 0, medium: 1, hard: 2 };

export default function QuestionListPage() {
  const { catalog, loading, error } = useCatalog();
  const navigate = useNavigate();

  // Flatten all questions with unlock state
  const questions = (catalog?.groups || [])
    .flatMap((g) => g.questions.map((q) => ({ ...q, difficulty: g.difficulty, order: q.order })))
    .sort((a, b) => {
      if (DIFFICULTY_ORDER[a.difficulty] !== DIFFICULTY_ORDER[b.difficulty]) {
        return DIFFICULTY_ORDER[a.difficulty] - DIFFICULTY_ORDER[b.difficulty];
      }
      return a.order - b.order;
    });

  return (
    <>
      <nav className="topbar">
        <div className="container topbar-inner">
          <h1>SQL Interview Practice</h1>
        </div>
      </nav>

      <main className="container question-list-page">
        <h2 className="page-title">Question Bank</h2>
        <p className="page-subtitle">
          Choose a question, write your SQL query, and see if you get it right.
        </p>

        {loading && <p className="loading">Loading questions…</p>}
        {error && <p className="error-box">{error}</p>}

        {!loading && !error && (
          <div className="question-grid">
            {questions.map((q) => {
              const isLocked = q.state === 'locked';
              const isSolved = q.state === 'solved';
              const isUnlocked = q.state === 'unlocked';
              return (
                <div
                  key={q.id}
                  className={`question-card question-card-${q.state}`}
                  onClick={() => {
                    if (!isLocked) navigate(`/practice/questions/${q.id}`);
                  }}
                  style={isLocked ? { cursor: 'not-allowed', opacity: 0.6 } : {}}
                  title={isLocked ? 'Locked: Solve previous questions to unlock.' : isSolved ? 'Solved' : isUnlocked ? 'Unlocked' : ''}
                  aria-disabled={isLocked}
                >
                  <h2>{q.title}</h2>
                  <span className={`badge badge-${q.difficulty}`}>{q.difficulty}</span>
                  <span className={`status-dot status-${q.state}`} aria-hidden="true" />
                  {isSolved && <span className="sidebar-solved">Solved</span>}
                  {isLocked && <span className="sidebar-locked">Locked</span>}
                  {isUnlocked && <span className="sidebar-unlocked">Unlocked</span>}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
