import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const DIFFICULTY_ORDER = { easy: 0, medium: 1, hard: 2 };

export default function QuestionListPage() {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .get('/questions')
      .then((res) => {
        const sorted = [...res.data].sort(
          (a, b) => DIFFICULTY_ORDER[a.difficulty] - DIFFICULTY_ORDER[b.difficulty]
        );
        setQuestions(sorted);
      })
      .catch(() => setError('Failed to load questions. Is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

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
            {questions.map((q) => (
              <div
                key={q.id}
                className="question-card"
                onClick={() => navigate(`/practice/questions/${q.id}`)}
              >
                <h2>{q.title}</h2>
                <span className={`badge badge-${q.difficulty}`}>{q.difficulty}</span>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
