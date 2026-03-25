import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import SQLEditor from '../components/SQLEditor';
import ResultsTable from '../components/ResultsTable';
import SchemaViewer from '../components/SchemaViewer';

const PLACEHOLDER = '-- Write your SQL query here\nSELECT ';

export default function SampleQuestionPage() {
  const { difficulty } = useParams();

  const [question, setQuestion] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [sampleMeta, setSampleMeta] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [sampleExhausted, setSampleExhausted] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetNotice, setResetNotice] = useState('');
  const [query, setQuery] = useState(PLACEHOLDER);
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [running, setRunning] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSolution, setShowSolution] = useState(false);
  const [hintsShown, setHintsShown] = useState(0);

  const shouldShowFeedback = submitResult?.feedback?.length > 0
    && !(submitResult.correct && (submitResult.structure_correct ?? true));

  useEffect(() => {
    setQuestion(null);
    setLoadError(null);
    setSampleMeta(null);
    setSampleExhausted(false);
    setResetNotice('');
    setQuery(PLACEHOLDER);
    setRunResult(null);
    setRunError(null);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    setHintsShown(0);

    api
      .get(`/sample/${difficulty}`)
      .then((res) => {
        setQuestion(res.data);
        setSampleMeta(res.data.sample ?? null);
      })
      .catch((err) => {
        if (err.response?.status === 409) {
          setSampleExhausted(true);
          return;
        }
        setLoadError(err.response?.data?.detail ?? 'Failed to load sample question.');
      });

    return undefined;
  }, [difficulty, reloadToken]);

  function handleAnotherSample() {
    if (sampleMeta && sampleMeta.remaining <= 0) {
      setSampleExhausted(true);
      return;
    }
    setResetNotice('');
    setReloadToken((value) => value + 1);
  }

  async function handleResetSamples() {
    setResetting(true);
    try {
      await api.post(`/sample/${difficulty}/reset`);
      setSampleExhausted(false);
      setLoadError(null);
      setResetNotice('Sample progress reset. Started this set from question 1.');
      setReloadToken((value) => value + 1);
    } catch (err) {
      setLoadError(err.response?.data?.detail ?? 'Failed to reset sample progress.');
    } finally {
      setResetting(false);
    }
  }

  async function handleRun() {
    if (!question) return;

    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const res = await api.post('/sample/run-query', { query, question_id: Number(question.id) });
      setRunResult(res.data);
    } catch (err) {
      setRunError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Query execution failed.');
    } finally {
      setRunning(false);
    }
  }

  async function handleSubmit() {
    if (!question) return;

    setSubmitting(true);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    try {
      const res = await api.post('/sample/submit', { query, question_id: Number(question.id) });
      setSubmitResult(res.data);
    } catch (err) {
      setSubmitError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  }

  function renderExhaustedState() {
    return (
      <>
        <header className="topbar">
          <div className="container topbar-inner sample-page-topbar">
            <Link className="back-link" to="/">
              ← Back to landing page
            </Link>
            <h1>Sample question</h1>
            <Link className="btn btn-secondary" to="/practice">
              Start the challenge
            </Link>
          </div>
        </header>

        <main className="container" style={{ paddingTop: '2rem' }}>
          {resetNotice && <p className="sample-reset-notice">{resetNotice}</p>}
          <div className="card sample-challenge-card sample-exhausted-card">
            <div className="section-heading">
              <div>
                <span className="section-kicker">Sample track</span>
                <h3>Sample set exhausted for {difficulty}</h3>
              </div>
              <span className="section-meta">3 of 3 shown</span>
            </div>
            <p className="sample-challenge-copy">
              You have seen all 3 dedicated {difficulty} sample questions. Continue with the ordered challenge flow.
            </p>
            <div className="sample-challenge-actions">
              <button className="btn btn-secondary sample-challenge-button" onClick={handleResetSamples} disabled={resetting}>
                {resetting ? 'Resetting…' : 'Reset sample progress'}
              </button>
              <Link className="btn btn-primary sample-challenge-button" to="/practice">
                Take the Challenge
              </Link>
            </div>
          </div>
        </main>
      </>
    );
  }

  if (loadError) {
    return (
      <main className="container" style={{ paddingTop: '2rem' }}>
        <p className="error-box">{loadError}</p>
      </main>
    );
  }

  if (sampleExhausted) {
    return renderExhaustedState();
  }

  if (!question) {
    return (
      <main className="container" style={{ paddingTop: '2rem' }}>
        <p className="loading">Loading sample question…</p>
      </main>
    );
  }

  const remainingSamples = sampleMeta?.remaining ?? 0;
  const shownSamples = sampleMeta?.shown_count ?? 0;
  const totalSamples = sampleMeta?.total ?? 3;
  const schemaTableCount = Object.keys(question.schema ?? {}).length;

  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner sample-page-topbar">
          <Link className="back-link" to="/">
            ← Back to landing page
          </Link>
          <h1>Sample question</h1>
          <Link className="btn btn-secondary" to="/practice">
            Start the challenge
          </Link>
        </div>
      </header>

      <main className="container question-page question-page-sample">
        {resetNotice && <p className="sample-reset-notice">{resetNotice}</p>}

        <div className="question-page-inner">
          <aside className="left-panel">
            <div className="card prompt-card">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">Sample question</span>
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

              <div className="locked-callout locked-callout-sample">
                Sample mode does not change your challenge progress. {shownSamples}/{totalSamples} shown.
              </div>
            </div>

            <div className="card schema-card">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">Reference</span>
                  <h3>Table schema</h3>
                </div>
                <span className="section-meta">{schemaTableCount} tables</span>
              </div>
              <SchemaViewer schema={question.schema} />
            </div>

            <div className="card sample-challenge-card">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">Sample track</span>
                  <h3>{remainingSamples > 0 ? 'Keep sampling or move into the real flow' : 'Sample set exhausted'}</h3>
                </div>
                <span className="section-meta">{shownSamples}/{totalSamples} shown</span>
              </div>
              <p className="sample-challenge-copy">
                {remainingSamples > 0
                  ? `${remainingSamples} sample ${remainingSamples === 1 ? 'question remains' : 'questions remain'} in this ${difficulty} set.`
                  : 'You have seen all dedicated samples in this difficulty. Continue with the guided sequence.'}
              </p>
              <div className="sample-challenge-actions">
                {remainingSamples > 0 && (
                  <button className="btn btn-secondary sample-challenge-button" onClick={handleAnotherSample}>
                    Show next sample
                  </button>
                )}
                <button className="btn btn-secondary sample-challenge-button" onClick={handleResetSamples} disabled={resetting}>
                  {resetting ? 'Resetting…' : 'Reset sample progress'}
                </button>
                <Link className="btn btn-primary sample-challenge-button" to="/practice">
                  Take the Challenge
                </Link>
              </div>
            </div>
          </aside>

          <section className="right-panel">
            <div className="editor-wrapper editor-workspace">
              <div className="editor-topbar">
                <div className="editor-topbar-copy">
                  <span className="section-kicker">Workspace</span>
                  <span className="editor-title">SQL editor</span>
                </div>
                <span className="editor-topbar-note">Sample mode uses the same read-only dataset model</span>
              </div>

              <SQLEditor value={query} onChange={setQuery} />

              <div className="editor-footer">
                <div className="editor-footer-copy">
                  <span className="editor-footer-title">Use samples to test your approach without affecting the challenge track.</span>
                  <span className="editor-footer-note">Run the query for quick iteration, then submit to compare with the expected result.</span>
                </div>
                <div className="button-row">
                  <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting}>
                    {running ? 'Running…' : 'Run Query'}
                  </button>
                  <button className="btn btn-primary" onClick={handleSubmit} disabled={running || submitting}>
                    {submitting ? 'Checking…' : 'Submit Answer'}
                  </button>
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
              <>
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
              </>
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
    </>
  );
}
