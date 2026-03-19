import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import SQLEditor from '../components/SQLEditor';
import ResultsTable from '../components/ResultsTable';
import SchemaViewer from '../components/SchemaViewer';
import { useCatalog } from '../catalogContext';

const PLACEHOLDER = '-- Write your SQL query here\nSELECT ';

export default function QuestionPage() {
  const { id } = useParams();
  const { catalog, refresh } = useCatalog();
  const navigate = useNavigate();

  // After a correct submission the catalog is refreshed; the newly-unlocked
  // question gets is_next:true. Derive its id so we can offer a Next button.
  const nextQuestionId = useMemo(() => {
    if (!catalog) return null;
    for (const g of catalog.groups) {
      const next = g.questions.find((q) => q.is_next);
      if (next) return next.id;
    }
    return null;
  }, [catalog]);

  const [question, setQuestion] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [query, setQuery] = useState(PLACEHOLDER);

  // Run query state
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [running, setRunning] = useState(false);

  // Submit state
  const [submitResult, setSubmitResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [showSolution, setShowSolution] = useState(false);
  const [hintsShown, setHintsShown] = useState(0);

  useEffect(() => {
    setQuestion(null);
    setLoadError(null);
    api
      .get(`/questions/${id}`)
      .then((res) => setQuestion(res.data))
      .catch((err) => setLoadError(err.response?.data?.detail ?? 'Failed to load question.'));
  }, [id]);

  // Reset state when navigating to a different question
  useEffect(() => {
    setQuery(PLACEHOLDER);
    setRunResult(null);
    setRunError(null);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    setHintsShown(0);
  }, [id]);

  async function handleRun() {
    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const res = await api.post('/run-query', { query, question_id: Number(id) });
      setRunResult(res.data);
    } catch (err) {
      setRunError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Query execution failed.');
    } finally {
      setRunning(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    try {
      const res = await api.post('/submit', { query, question_id: Number(id) });
      setSubmitResult(res.data);
      if (res.data.correct) await refresh();
    } catch (err) {
      setSubmitError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return (
      <main className="container" style={{ paddingTop: '2rem' }}>
        <p className="error-box">{loadError}</p>
      </main>
    );
  }

  if (!question) {
    return (
      <main className="container" style={{ paddingTop: '2rem' }}>
        <p className="loading">Loading question…</p>
      </main>
    );
  }

  const isLocked = question.progress && question.progress.unlocked === false;

  return (
    <>
      <main className="container question-page">
        <div className="question-page-inner">
          {/* ── Left panel ── */}
          <aside className="left-panel">
            <div className="card">
              <div className="question-title-row">
                <h2>{question.title}</h2>
                <span className={`badge badge-${question.difficulty}`}>{question.difficulty}</span>
              </div>
              <p className="description-text">{question.description}</p>
              {question.concepts?.length > 0 && (
                <div className="concept-tags">
                  {question.concepts.map((c) => (
                    <span key={c} className="tag-concept">{c}</span>
                  ))}
                </div>
              )}
              {isLocked && (
                <div className="locked-callout">
                  This question is locked. Solve previous questions in this difficulty first.
                </div>
              )}
            </div>

            <div className="card">
              <h3>Table Schema</h3>
              <SchemaViewer schema={question.schema} />
            </div>
          </aside>

          {/* ── Right panel ── */}
          <section className="right-panel">
            {/* Editor */}
            <div className="editor-wrapper">
              <div className="editor-topbar">SQL Editor</div>
              <SQLEditor value={query} onChange={setQuery} />
            </div>

            {/* Action buttons */}
            <div className="button-row">
              <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting || isLocked}>
                {running ? 'Running…' : '▶ Run Query'}
              </button>
              <button className="btn btn-primary" onClick={handleSubmit} disabled={running || submitting || isLocked}>
                {submitting ? 'Checking…' : '✓ Submit Answer'}
              </button>
              {submitResult?.correct && nextQuestionId && (
                <button
                  className="btn btn-success"
                  onClick={() => navigate(`/practice/questions/${nextQuestionId}`)}
                >
                  Next Question →
                </button>
              )}
            </div>

            {/* Run error */}
            {runError && <div className="error-box">{runError}</div>}

            {/* Run results */}
            {runResult && (
              <div className="results-card">
                <div className="results-header">
                  <span>Query Result</span>
                  <span>{runResult.rows.length} row{runResult.rows.length !== 1 ? 's' : ''}</span>
                </div>
                <ResultsTable columns={runResult.columns} rows={runResult.rows} />
              </div>
            )}

            {/* Submit verdict */}
            {submitError && <div className="error-box">{submitError}</div>}
            {submitResult && (
              <>
                <div className={`verdict ${submitResult.correct ? 'verdict-correct' : 'verdict-incorrect'}`}>
                  {submitResult.correct ? '✓ Correct! Your answer matches the expected output.' : '✗ Incorrect. Your output does not match the expected result.'}
                </div>
                {submitResult.feedback?.length > 0 && (
                  <div className="feedback-card">
                    {submitResult.feedback.map((message, index) => (
                      <p key={`${index}-${message}`} className="feedback-message">{message}</p>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Expected vs user result diff (on incorrect) */}
            {submitResult && !submitResult.correct && (
              <>
                <div className="results-card">
                  <div className="results-header">
                    <span>Your Output</span>
                    <span>{submitResult.user_result.rows.length} row{submitResult.user_result.rows.length !== 1 ? 's' : ''}</span>
                  </div>
                  <ResultsTable columns={submitResult.user_result.columns} rows={submitResult.user_result.rows} />
                </div>
                <div className="results-card">
                  <div className="results-header">
                    <span>Expected Output</span>
                    <span>{submitResult.expected_result.rows.length} row{submitResult.expected_result.rows.length !== 1 ? 's' : ''}</span>
                  </div>
                  <ResultsTable columns={submitResult.expected_result.columns} rows={submitResult.expected_result.rows} />
                </div>
              </>
            )}

            {/* Hints and Solution */}
            {submitResult && (
              <>
                {question.hints?.slice(0, hintsShown).map((hint, i) => (
                  <div key={i} className="hint-card">
                    <strong>Hint {i + 1}:</strong> {hint}
                  </div>
                ))}
                {hintsShown < (question.hints?.length ?? 0) && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => setHintsShown((n) => n + 1)}
                  >
                    Show Hint {hintsShown + 1}
                  </button>
                )}
                {hintsShown >= (question.hints?.length ?? 0) && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowSolution((v) => !v)}
                  >
                    {showSolution ? 'Hide Solution' : 'Show Solution'}
                  </button>
                )}
                {showSolution && (
                  <div className="solution-card">
                    <h3>Official Solution</h3>
                    <pre>{submitResult.solution_query}</pre>
                    <h3 style={{ marginBottom: '0.5rem' }}>Explanation</h3>
                    <p>{submitResult.explanation}</p>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
