import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import CodeEditor from '../components/CodeEditor';
import ResultsTable from '../components/ResultsTable';
import SchemaViewer from '../components/SchemaViewer';
import TestCasePanel from '../components/TestCasePanel';
import PrintOutputPanel from '../components/PrintOutputPanel';
import VariablesPanel from '../components/VariablesPanel';
import MCQPanel from '../components/MCQPanel';
import { useCatalog } from '../catalogContext';
import { useTopic } from '../contexts/TopicContext';

const SQL_PLACEHOLDER = '-- Write your SQL query here\nSELECT ';
const PYTHON_PLACEHOLDER = '# Write your solution here\n';

export default function QuestionPage() {
  const { id } = useParams();
  const { catalog, refresh } = useCatalog();
  const { topic, meta } = useTopic();
  const navigate = useNavigate();

  // Derive API paths from topic
  const apiPrefix = meta.apiPrefix; // '', '/python', '/python-data', '/pyspark'

  const questionApiPath = apiPrefix ? `${apiPrefix}/questions/${id}` : `/questions/${id}`;
  const runApiPath = apiPrefix ? `${apiPrefix}/run-code` : '/run-query';
  const submitApiPath = apiPrefix ? `${apiPrefix}/submit` : '/submit';

  const defaultCode = meta.language === 'python' ? PYTHON_PLACEHOLDER : SQL_PLACEHOLDER;

  const nextQuestionId = useMemo(() => {
    if (!catalog) return null;
    for (const group of (catalog.groups ?? [])) {
      const next = group.questions.find((question) => question.is_next);
      if (next) return next.id;
    }
    return null;
  }, [catalog]);
  const catalogQuestionMeta = useMemo(() => {
    if (!catalog) return null;
    const targetId = Number(id);
    for (const group of (catalog.groups ?? [])) {
      const matched = group.questions.find((question) => question.id === targetId);
      if (matched) {
        return { group, question: matched };
      }
    }
    return null;
  }, [catalog, id]);
  const workspaceStatus = useMemo(() => {
    if (!catalogQuestionMeta) return null;
    const group = catalogQuestionMeta.group;
    const groupTitle = group?.difficulty
      ? `${group.difficulty.charAt(0).toUpperCase()}${group.difficulty.slice(1)}`
      : null;
    const total = group?.counts?.total ?? group?.questions?.length ?? null;
    const order = catalogQuestionMeta.question?.order ?? null;
    const openNow = group?.questions?.filter((entry) => entry.state !== 'locked').length ?? null;
    const chunks = [];
    if (groupTitle) chunks.push(groupTitle);
    if (order && total) chunks.push(`Question ${order} of ${total}`);
    if (typeof openNow === 'number') chunks.push(`${openNow} open now`);
    return chunks.length > 0 ? chunks.join(' · ') : null;
  }, [catalogQuestionMeta]);

  const [question, setQuestion] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [code, setCode] = useState(defaultCode);
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [running, setRunning] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSolution, setShowSolution] = useState(false);
  const [hintsShown, setHintsShown] = useState(0);
  const [pastAttempts, setPastAttempts] = useState([]);
  const [pastAttemptsOpen, setPastAttemptsOpen] = useState(false);
  const [openAttemptCodes, setOpenAttemptCodes] = useState(new Set());

  // MCQ state for PySpark
  const [selectedOption, setSelectedOption] = useState(null);

  useEffect(() => {
    setQuestion(null);
    setLoadError(null);
    api
      .get(questionApiPath)
      .then((res) => {
        const q = res.data;
        setQuestion(q);
        // For Python tracks use starter_code from question if available
        if (meta.language === 'python' && q.starter_code) {
          setCode(q.starter_code);
        } else if (!meta.hasMCQ) {
          setCode(defaultCode);
        }
      })
      .catch((err) => setLoadError(err.response?.data?.detail ?? 'Failed to load question.'));
    api.get('/submissions', { params: { track: topic, question_id: id, limit: 5 } })
      .then((res) => setPastAttempts(res.data))
      .catch(() => {});
  }, [id, topic, questionApiPath, meta.language, meta.hasMCQ, defaultCode]);

  useEffect(() => {
    if (meta.language === 'python') {
      setCode(PYTHON_PLACEHOLDER);
    } else if (!meta.hasMCQ) {
      setCode(SQL_PLACEHOLDER);
    }
    setRunResult(null);
    setRunError(null);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    setHintsShown(0);
    setSelectedOption(null);
    setPastAttempts([]);
    setPastAttemptsOpen(false);
    setOpenAttemptCodes(new Set());
  }, [id, meta.language, meta.hasMCQ]);

  function formatRelativeTime(isoString) {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  const toggleAttemptCode = (attemptId) => setOpenAttemptCodes((prev) => {
    const next = new Set(prev);
    if (next.has(attemptId)) next.delete(attemptId); else next.add(attemptId);
    return next;
  });

  async function handleRun() {
    if (!meta.hasRunCode) return;
    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const payload = meta.language === 'python'
        ? { code, question_id: Number(id) }
        : { query: code, question_id: Number(id) };
      const res = await api.post(runApiPath, payload);
      setRunResult(res.data);
    } catch (err) {
      setRunError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Execution failed.');
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
      let payload;
      if (meta.hasMCQ) {
        payload = { selected_option: selectedOption, question_id: Number(id) };
      } else if (meta.language === 'python') {
        payload = { code, question_id: Number(id) };
      } else {
        payload = { query: code, question_id: Number(id) };
      }
      const res = await api.post(submitApiPath, payload);
      setSubmitResult(res.data);
      if (res.data.correct) await refresh();
      api.get('/submissions', { params: { track: topic, question_id: id, limit: 5 } })
        .then((r) => setPastAttempts(r.data))
        .catch(() => {});
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

  // Determine what to show in left panel
  const showSchema = topic === 'sql';
  const showVariables = topic === 'python-data';

  // For Python run results — detect shape
  const isPythonRunResult = topic !== 'sql' && runResult;
  const isSQLRunResult = topic === 'sql' && runResult;

  // Editor title based on topic
  const editorTitle = meta.hasMCQ
    ? 'Code preview'
    : meta.language === 'python'
    ? 'Python editor'
    : 'SQL editor';
  const editorNote = meta.hasMCQ
    ? 'Read-only'
    : meta.language === 'python'
    ? 'Python sandbox'
    : 'DuckDB sandbox';

  // Submit button label
  const submitBtnLabel = submitting
    ? 'Checking…'
    : meta.hasMCQ
    ? 'Submit Answer'
    : 'Submit Answer';

  const isSubmitDisabled = submitting || running || isLocked
    || (meta.hasMCQ && selectedOption === null);

  return (
    <main className="container question-page question-page-challenge">
      <div className="question-page-inner">
        <aside className="left-panel">
          <div className="card prompt-card prompt-card-main">
            <div className="section-heading">
              <div>
                <div className="question-title-row">
                  <h2>{question.title}</h2>
                  <span className={`badge badge-${question.difficulty}`}>{question.difficulty}</span>
                </div>
                {workspaceStatus && (
                  <p className="question-status-line">{workspaceStatus}</p>
                )}
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

            {/* PySpark: show code snippet (question stem) if present */}
            {meta.hasMCQ && question.code_snippet && (
              <pre className="question-code-snippet">{question.code_snippet}</pre>
            )}

            {isLocked && (
              <div className="locked-callout">
                This question is locked. Solve previous questions in this difficulty first.
              </div>
            )}
          </div>

          {showSchema && (
            <div className="card schema-card schema-card-utility">
              <div className="section-heading">
                <div>
                  <h3>Table schema</h3>
                </div>
                <span className="section-meta">{schemaTableCount} tables</span>
              </div>
              <SchemaViewer schema={question.schema} />
            </div>
          )}

          {showVariables && (
            <VariablesPanel
              dataframes={question.dataframes ?? {}}
              schema={question.dataframe_schema ?? {}}
            />
          )}
        </aside>

        <section className="right-panel">
          {/* PySpark: MCQ panel instead of editor */}
          {meta.hasMCQ ? (
            <div className="card">
              <div className="section-heading">
                <h3>Choose the correct answer</h3>
              </div>
              <MCQPanel
                options={question.options ?? []}
                selectedOption={selectedOption}
                onSelect={setSelectedOption}
                submitted={!!submitResult}
                correct={submitResult?.correct ?? null}
                correctIndex={submitResult?.correct_index ?? null}
                explanation={submitResult?.explanation ?? ''}
              />
              <div className="editor-footer editor-footer-plain question-action-dock">
                <div className="button-row question-action-row">
                  <button
                    className="btn btn-primary"
                    onClick={handleSubmit}
                    disabled={isSubmitDisabled}
                  >
                    {submitBtnLabel}
                  </button>
                  {submitResult?.correct && nextQuestionId && (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${nextQuestionId}`)}
                    >
                      Next Question
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* Code/SQL editor */
            <div className="editor-wrapper editor-workspace">
              <div className="editor-topbar">
                <span className="editor-title">{editorTitle}</span>
                <span className="editor-topbar-note">{editorNote}</span>
              </div>

              <CodeEditor
                value={code}
                onChange={setCode}
                language={meta.language}
              />

              <div className="editor-footer question-action-dock">
                <div className="button-row question-action-row">
                  {meta.hasRunCode && (
                    <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting || isLocked}>
                      {running ? 'Running…' : meta.language === 'python' ? 'Run Code' : 'Run Query'}
                    </button>
                  )}
                  <button className="btn btn-primary" onClick={handleSubmit} disabled={isSubmitDisabled}>
                    {submitBtnLabel}
                  </button>
                  {submitResult?.correct && nextQuestionId && (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${nextQuestionId}`)}
                    >
                      Next Question
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {runError && <div className="error-box">{runError}</div>}

          {/* SQL run result */}
          {isSQLRunResult && (
            <div className="results-card">
              <div className="results-header">
                <span>Query Result</span>
                <span>{runResult.rows.length} row{runResult.rows.length !== 1 ? 's' : ''}</span>
              </div>
              <ResultsTable columns={runResult.columns} rows={runResult.rows} />
            </div>
          )}

          {/* Python run results */}
          {isPythonRunResult && topic === 'python' && (
            <>
              <TestCasePanel results={runResult.test_results ?? []} hiddenSummary={null} />
              <PrintOutputPanel output={runResult.stdout ?? ''} />
            </>
          )}

          {isPythonRunResult && topic === 'python-data' && (
            <>
              {runResult.columns && (
                <div className="results-card">
                  <div className="results-header">
                    <span>Output</span>
                    <span>{(runResult.rows ?? []).length} rows</span>
                  </div>
                  <ResultsTable columns={runResult.columns} rows={runResult.rows ?? []} />
                </div>
              )}
              <PrintOutputPanel output={runResult.stdout ?? ''} />
            </>
          )}

          {submitError && <div className="error-box">{submitError}</div>}

          {submitResult && (
            <div className="submit-outcome">
              <div className={`verdict ${submitResult.correct ? 'verdict-correct' : 'verdict-incorrect'}`}>
                <span className="verdict-label">{submitResult.correct ? 'Correct' : 'Keep iterating'}</span>
                <p className="verdict-copy">
                  {submitResult.correct
                    ? 'Your submission matches the expected result.'
                    : 'Your submission does not match the expected result yet.'}
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

          {/* SQL submit: show compare grid */}
          {submitResult && topic === 'sql' && submitResult.user_result && (
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

          {/* Python submit: show test case results */}
          {submitResult && topic === 'python' && (
            <>
              <TestCasePanel
                results={submitResult.test_results ?? []}
                hiddenSummary={submitResult.hidden_summary ?? null}
              />
              <PrintOutputPanel output={submitResult.stdout ?? ''} />
            </>
          )}

          {/* Python-Data submit: show DataFrame output */}
          {submitResult && topic === 'python-data' && submitResult.user_result && (
            <div className="results-compare-grid">
              <div className="results-card">
                <div className="results-header">
                  <span>Your Output</span>
                  <span>{(submitResult.user_result.rows ?? []).length} rows</span>
                </div>
                <ResultsTable
                  columns={submitResult.user_result.columns ?? []}
                  rows={submitResult.user_result.rows ?? []}
                />
              </div>
              <div className="results-card">
                <div className="results-header">
                  <span>Expected Output</span>
                  <span>{(submitResult.expected_result.rows ?? []).length} rows</span>
                </div>
                <ResultsTable
                  columns={submitResult.expected_result.columns ?? []}
                  rows={submitResult.expected_result.rows ?? []}
                />
              </div>
            </div>
          )}

          {pastAttempts.length > 0 && (
            <div className="past-attempts">
              <button
                className="past-attempts-toggle"
                onClick={() => setPastAttemptsOpen((v) => !v)}
                aria-expanded={pastAttemptsOpen}
              >
                Past attempts ({pastAttempts.length})
                <span className="past-attempts-chevron">{pastAttemptsOpen ? '▾' : '▸'}</span>
              </button>
              {pastAttemptsOpen && (
                <div className="past-attempts-list">
                  {pastAttempts.map((attempt) => (
                    <div key={attempt.id} className={`past-attempt-row past-attempt-row--${attempt.is_correct ? 'correct' : 'wrong'}`}>
                      <span className={`past-attempt-badge ${attempt.is_correct ? 'past-attempt-badge--correct' : 'past-attempt-badge--wrong'}`}>
                        {attempt.is_correct ? '✓' : '✗'}
                      </span>
                      <span className="past-attempt-time">{formatRelativeTime(attempt.submitted_at)}</span>
                      {attempt.code && (
                        <button
                          className="past-attempt-code-toggle"
                          onClick={() => toggleAttemptCode(attempt.id)}
                        >
                          {openAttemptCodes.has(attempt.id) ? 'Hide code' : 'Show code'}
                        </button>
                      )}
                      {attempt.code && openAttemptCodes.has(attempt.id) && (
                        <pre className="past-attempt-code">{attempt.code}</pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
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
                  <pre>{submitResult.solution_query ?? submitResult.solution_code ?? ''}</pre>
                  {submitResult.explanation && (
                    <>
                      <h3 style={{ marginBottom: '0.5rem' }}>Explanation</h3>
                      <p>{submitResult.explanation}</p>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
