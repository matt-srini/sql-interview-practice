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

  const nextQuestionId = useMemo(() => {
    if (!catalog) return null;
    for (const group of catalog.groups) {
      const next = group.questions.find((question) => question.is_next);
      if (next) return next.id;
    }
    return null;
  }, [catalog]);

  const [question, setQuestion] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [query, setQuery] = useState(PLACEHOLDER);
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [running, setRunning] = useState(false);
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
  const shouldShowFeedback = submitResult?.feedback?.length > 0
    && !(submitResult.correct && (submitResult.structure_correct ?? true));
  const schemaTableCount = Object.keys(question.schema ?? {}).length;

  return (
    <main className="container question-page question-page-challenge">
      <div className="question-page-inner">
        <aside className="left-panel">
          <div className="card prompt-card">
            <div className="section-heading">
              <div>
                <div className="question-title-row">
                  <h2>{question.title}</h2>
                  <span className={`badge badge-${question.difficulty}`}>{question.difficulty}</span>
                </div>
              </div>
            </div>

            {question.concepts?.length > 0 && (
              <div className="concept-tags concept-tags-inline">
                {question.concepts.map((concept) => (
                  <span key={concept} className="tag-concept">{concept}</span>
                ))}
              </div>
            )}

            <p className="description-text">{question.description}</p>

            {isLocked && (
              <div className="locked-callout">
                This question is locked. Solve previous questions in this difficulty first.
              </div>
            )}
          </div>

          <div className="card schema-card">
            <div className="section-heading">
              <div>
                <h3>Table schema</h3>
              </div>
              <span className="section-meta">{schemaTableCount} tables</span>
            </div>
            <SchemaViewer schema={question.schema} />
          </div>
        </aside>

        <section className="right-panel">
          <div className="editor-wrapper editor-workspace">
            <div className="editor-topbar">
              <span className="editor-title">SQL editor</span>
              <span className="editor-topbar-note">DuckDB sandbox</span>
            </div>

            <SQLEditor value={query} onChange={setQuery} />

            <div className="editor-footer">
              <div className="button-row">
                <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting || isLocked}>
                  {running ? 'Running…' : 'Run Query'}
                </button>
                <button className="btn btn-primary" onClick={handleSubmit} disabled={running || submitting || isLocked}>
                  {submitting ? 'Checking…' : 'Submit Answer'}
                </button>
                {submitResult?.correct && nextQuestionId && (
                  <button
                    className="btn btn-success"
                    onClick={() => navigate(`/practice/questions/${nextQuestionId}`)}
                  >
                    Next Question
                  </button>
                )}
              </div>
            </div>
          </div>

          {runError && <div className="error-box">{runError}</div>}

          {runResult && (
            <div className="results-card">
              <div className="results-header">
                <span>Query Result</span>
                <span>{runResult.rows.length} row{runResult.rows.length !== 1 ? 's' : ''}</span>
              </div>
              <ResultsTable columns={runResult.columns} rows={runResult.rows} />
            </div>
          )}

          {submitError && <div className="error-box">{submitError}</div>}
          {submitResult && (
            <div className="submit-outcome">
              <div className={`verdict ${submitResult.correct ? 'verdict-correct' : 'verdict-incorrect'}`}>
                <span className="verdict-label">{submitResult.correct ? 'Correct' : 'Keep iterating'}</span>
                <p className="verdict-copy">
                  {submitResult.correct ? 'Submission matches the expected result.' : 'Submission does not match the expected result yet.'}
                </p>
              </div>
              {shouldShowFeedback && (
                <div className="feedback-card">
                  <div className="feedback-title">What to adjust</div>
                  {submitResult.feedback.map((message, index) => (
                    <p key={`${index}-${message}`} className="feedback-message">
                      <span className="feedback-icon" aria-hidden="true">i</span>
                      <span>{message}</span>
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          {submitResult && (
            <div className="results-compare-grid">
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
            </div>
          )}

          {submitResult && (
            <div className="post-submit-stack">
              {question.hints?.slice(0, hintsShown).map((hint, index) => (
                <div key={index} className="hint-card">
                  <strong>Hint {index + 1}:</strong> {hint}
                </div>
              ))}

              {hintsShown < (question.hints?.length ?? 0) && (
                <button
                  className="btn btn-secondary workspace-inline-action"
                  onClick={() => setHintsShown((count) => count + 1)}
                >
                  Reveal Hint {hintsShown + 1}
                </button>
              )}

              {hintsShown >= (question.hints?.length ?? 0) && (
                <button
                  className="btn btn-secondary workspace-inline-action"
                  onClick={() => setShowSolution((value) => !value)}
                >
                  {showSolution ? 'Hide Official Solution' : 'Review Official Solution'}
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
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
