import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import CodeEditor from '../components/CodeEditor';
import MCQPanel from '../components/MCQPanel';
import PrintOutputPanel from '../components/PrintOutputPanel';
import ResultsTable from '../components/ResultsTable';
import SchemaViewer from '../components/SchemaViewer';
import TestCasePanel from '../components/TestCasePanel';
import VariablesPanel from '../components/VariablesPanel';
import { TRACK_META } from '../contexts/TopicContext';
import { renderDescription } from '../utils/renderDescription';
import { track } from '../analytics';

const SQL_PLACEHOLDER = '-- Write your SQL query here\nSELECT ';
const PYTHON_PLACEHOLDER = '# Write your solution here\n';

export default function SampleQuestionPage() {
  const { topic: rawTopic, difficulty } = useParams();
  const topic = TRACK_META[rawTopic] ? rawTopic : 'sql';
  const meta = TRACK_META[topic];

  const defaultCode = meta.language === 'python' ? PYTHON_PLACEHOLDER : SQL_PLACEHOLDER;
  const sampleBasePath = `/sample/${topic}`;
  const challengePath = `/practice/${topic}`;
  const runApiPath = meta.language === 'python'
    ? `${sampleBasePath}/run-code`
    : `${sampleBasePath}/run-query`;
  const submitApiPath = `${sampleBasePath}/submit`;

  const [question, setQuestion] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [sampleMeta, setSampleMeta] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [sampleExhausted, setSampleExhausted] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetNotice, setResetNotice] = useState('');
  const [code, setCode] = useState(defaultCode);
  const [selectedOption, setSelectedOption] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [running, setRunning] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSolution, setShowSolution] = useState(false);
  const [editorTall, setEditorTall] = useState(() => {
    try { return localStorage.getItem('editor-height-pref') === 'tall'; } catch { return false; }
  });
  const [draftSaveState, setDraftSaveState] = useState('idle');
  const draftKey = useMemo(
    () => (question ? `sample-draft:${topic}:${difficulty}:${question.id}` : null),
    [topic, difficulty, question]
  );

  // Refs for Monaco keyboard shortcuts
  const handleRunRef = useRef(null);
  const handleSubmitRef = useRef(null);
  const runningRef = useRef(false);
  const submittingRef = useRef(false);
  const draftHydratedRef = useRef(false);
  const draftSaveTimerRef = useRef(null);

  useEffect(() => {
    setQuestion(null);
    setLoadError(null);
    setSampleMeta(null);
    setSampleExhausted(false);
    setResetNotice('');
    setCode(defaultCode);
    setSelectedOption(null);
    setRunResult(null);
    setRunError(null);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    draftHydratedRef.current = false;
    setDraftSaveState('idle');

    api
      .get(`${sampleBasePath}/${difficulty}`)
      .then((res) => {
        const nextQuestion = res.data;
        setQuestion(nextQuestion);
        setSampleMeta(nextQuestion.sample ?? null);
        if (!meta.hasMCQ) {
          const baseCode = meta.language === 'python' && nextQuestion.starter_code ? nextQuestion.starter_code : defaultCode;
          const localDraftKey = `sample-draft:${topic}:${difficulty}:${nextQuestion.id}`;
          let nextCode = baseCode;
          try {
            const savedDraft = localStorage.getItem(localDraftKey);
            if (savedDraft && savedDraft.trim()) {
              nextCode = savedDraft;
              setDraftSaveState('saved');
            }
          } catch {}
          setCode(nextCode);
        }
        draftHydratedRef.current = true;
      })
      .catch((err) => {
        if (err.response?.status === 409) {
          setSampleExhausted(true);
          return;
        }
        setLoadError(err.response?.data?.detail ?? 'Failed to load sample question.');
      });
  }, [defaultCode, difficulty, meta.language, meta.hasMCQ, sampleBasePath, reloadToken, topic]);

  useEffect(() => {
    if (meta.hasMCQ || !question || !draftKey || !draftHydratedRef.current) return undefined;
    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    setDraftSaveState('saving');
    draftSaveTimerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(draftKey, code);
        setDraftSaveState('saved');
      } catch {
        setDraftSaveState('idle');
      }
    }, 350);

    return () => {
      if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
    };
  }, [code, draftKey, meta.hasMCQ, question]);

  useEffect(() => () => {
    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
  }, []);

  const topicLabel = meta.label;
  const shownSamples = sampleMeta?.shown_count ?? 0;
  const totalSamples = sampleMeta?.total ?? 3;
  const remainingSamples = sampleMeta?.remaining ?? 0;
  const servedDifficulty = sampleMeta?.served_difficulty ?? difficulty;
  const sampleStatusLine = useMemo(() => {
    const chunks = [
      `${servedDifficulty.charAt(0).toUpperCase()}${servedDifficulty.slice(1)} sample`,
      `${shownSamples} of ${totalSamples} shown`,
    ];
    if (remainingSamples >= 0) {
      chunks.push(`${remainingSamples} remaining`);
    }
    return chunks.join(' · ');
  }, [remainingSamples, servedDifficulty, shownSamples, totalSamples]);

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
      await api.post(`${sampleBasePath}/${difficulty}/reset`);
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
    if (!question || !meta.hasRunCode) return;

    setRunning(true);
    setRunResult(null);
    setRunError(null);
    try {
      const payload = meta.language === 'python'
        ? { code, question_id: Number(question.id) }
        : { query: code, question_id: Number(question.id) };
      const res = await api.post(runApiPath, payload);
      setRunResult(res.data);
    } catch (err) {
      setRunError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Execution failed.');
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
      let payload;
      if (meta.hasMCQ) {
        payload = { selected_option: selectedOption, question_id: Number(question.id) };
      } else if (meta.language === 'python') {
        payload = { code, question_id: Number(question.id) };
      } else {
        payload = { query: code, question_id: Number(question.id) };
      }
      const res = await api.post(submitApiPath, payload);
      setSubmitResult(res.data);
      track('sample_submitted', { track: topic, difficulty, question_id: Number(question?.id), correct: res.data.correct });
    } catch (err) {
      setSubmitError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  }

  // Keep shortcut refs current on every render
  handleRunRef.current = handleRun;
  handleSubmitRef.current = handleSubmit;
  runningRef.current = running;
  submittingRef.current = submitting;

  function handleEditorMount(editor, monaco) {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!runningRef.current && !submittingRef.current && meta.hasRunCode) {
        handleRunRef.current();
      }
    });
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter,
      () => {
        if (!submittingRef.current && !runningRef.current) {
          handleSubmitRef.current();
        }
      }
    );
  }

  function toggleEditorHeight() {
    setEditorTall((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor-height-pref', next ? 'tall' : 'normal'); } catch {}
      return next;
    });
  }

  function clearDraft() {
    if (meta.hasMCQ || !question || !draftKey) return;
    const resetCode = meta.language === 'python' && question?.starter_code ? question.starter_code : defaultCode;
    try {
      localStorage.removeItem(draftKey);
    } catch {}
    setCode(resetCode);
    setDraftSaveState('idle');
  }

  function renderExhaustedState() {
    return (
      <>
        <header className="topbar">
          <div className="topbar-inner sample-page-topbar">
            <div className="sample-topbar-left">
              <Link className="sample-home-link brand-wordmark" to="/">datathink</Link>
            </div>
            <div className="sample-topbar-center">
              <a className="sample-back-link" href="/#landing-tracks" aria-label="Back to track selection">←</a>
              <span
                className="shell-pill shell-pill-mode shell-pill-mode-sample"
                style={{ '--mode-dot-color': meta.color }}
              >
                <span className="shell-pill-mode-dot" aria-hidden="true" />
                {topicLabel} · Sample
              </span>
            </div>
            <div className="sample-topbar-right">
              <Link className="btn btn-secondary" to={challengePath}>Start the challenge</Link>
            </div>
          </div>
        </header>

        <main className="container" style={{ paddingTop: '2rem' }}>
          {resetNotice && <p className="sample-reset-notice">{resetNotice}</p>}
          <div className="card sample-challenge-card sample-exhausted-card">
            <div className="section-heading">
              <div>
                <span className="section-kicker">Sample track</span>
                <h3>You've seen all {totalSamples} {difficulty} samples for {topicLabel}</h3>
              </div>
              <span className="section-meta">{totalSamples} shown</span>
            </div>
            <p className="sample-challenge-copy">
              Ready for the full {meta.totalQuestions}-question {topicLabel} track? Pro unlocks every medium + hard question.
            </p>
            <div className="sample-challenge-actions">
              <button className="btn btn-secondary sample-challenge-button" onClick={handleResetSamples} disabled={resetting}>
                {resetting ? 'Resetting…' : 'Reset sample progress'}
              </button>
              <Link className="btn btn-primary sample-challenge-button" to={challengePath}>
                Take the challenge
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
        <div className="sample-loading-card">
          <div className="skeleton-line skeleton-shimmer" style={{ width: '8rem', height: '12px' }} />
          <div className="skeleton-line skeleton-shimmer" style={{ width: '65%', height: '26px' }} />
          <div className="skeleton-line skeleton-shimmer" style={{ width: '92%', height: '11px' }} />
          <div className="skeleton-line skeleton-shimmer" style={{ width: '88%', height: '11px' }} />
          <div className="sample-loading-editor skeleton-shimmer" />
        </div>
      </main>
    );
  }

  const showSchema = topic === 'sql';
  const showVariables = topic === 'python-data';
  const schemaTableCount = Object.keys(question.schema ?? {}).length;
  const pythonRunResults = runResult?.results ?? runResult?.test_results ?? [];
  const pythonSubmitResults = submitResult?.public_results ?? submitResult?.test_results ?? [];
  const pythonRunOutput = runResult?.stdout ?? '';
  const pandasRunResult = runResult?.result ?? null;
  const pandasRunOutput = runResult?.print_output ?? runResult?.stdout ?? '';
  const pandasSubmitOutput = submitResult?.print_output ?? '';
  const shouldShowFeedback = submitResult?.feedback?.length > 0
    && !(submitResult.correct && (submitResult.structure_correct ?? true));
  const showSolutionToggle = Boolean(submitResult?.solution_query || submitResult?.solution_code);
  const editorTitle = meta.hasMCQ
    ? 'Code preview'
    : meta.language === 'python'
      ? 'Python editor'
      : 'SQL editor';
  const editorNote = meta.hasMCQ
    ? 'Read-only'
    : meta.language === 'python'
      ? 'Sandboxed execution'
      : 'DuckDB sandbox';

  return (
    <>
      <Helmet>
        <title>Free {meta.label} Sample Questions ({difficulty}) — datathink</title>
        <meta name="description" content={`Try free ${difficulty} ${meta.label} interview questions. No account required — instant feedback in a real execution environment.`} />
        <meta property="og:title" content={`Free ${meta.label} Sample Questions — datathink`} />
      </Helmet>
      <header className="topbar">
        <div className="topbar-inner sample-page-topbar">
          <div className="sample-topbar-left">
            <Link className="sample-home-link brand-wordmark" to="/">datathink</Link>
          </div>
          <div className="sample-topbar-center">
            <a className="sample-back-link" href="/#landing-tracks" aria-label="Back to track selection">←</a>
            <span
              className="shell-pill shell-pill-mode shell-pill-mode-sample"
              style={{ '--mode-dot-color': meta.color }}
            >
              <span className="shell-pill-mode-dot" aria-hidden="true" />
              {topicLabel} · Sample
            </span>
          </div>
          <div className="sample-topbar-right">
            <Link className="btn btn-secondary" to={challengePath}>Start the challenge</Link>
          </div>
        </div>
      </header>

      <main className="container question-page question-page-sample">
        {resetNotice && <p className="sample-reset-notice">{resetNotice}</p>}

        <div className="question-page-inner">
          <aside className="left-panel">
            <div className="card prompt-card prompt-card-main">
              <div className="section-heading">
                <div>
                  <div className="question-title-row">
                    <h2>{question.title}</h2>
                    <span className={`badge badge-${question.difficulty}`}>{question.difficulty}</span>
                  </div>
                  <p className="question-status-line">{sampleStatusLine}</p>
                </div>
              </div>

              {question.concepts?.length > 0 && (
                <div className="concept-tags concept-tags-inline">
                  {question.concepts.map((concept) => (
                    <span key={concept} className="tag-concept">{concept}</span>
                  ))}
                </div>
              )}

              <p className="description-text">{renderDescription(question.description)}</p>

              {meta.hasMCQ && question.code_snippet && (
                <pre className="question-code-snippet">{question.code_snippet}</pre>
              )}

              <div className="locked-callout locked-callout-sample">
                Sample mode is separate from challenge progress. Move to the full track whenever you are ready.
              </div>
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
                schema={question.schema ?? {}}
              />
            )}

            <div className="card sample-challenge-card">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">Sample track</span>
                  <h3>{remainingSamples > 0 ? 'Keep sampling or move into the full flow' : 'Sample set exhausted'}</h3>
                </div>
                <span className="section-meta">{shownSamples}/{totalSamples} shown</span>
              </div>
              <p className="sample-challenge-copy">
                {remainingSamples > 0
                  ? `${remainingSamples} sample ${remainingSamples === 1 ? 'question remains' : 'questions remain'} in this ${difficulty} set.`
                  : `You've seen all ${totalSamples} ${difficulty} samples. The full ${topicLabel} track has ${meta.totalQuestions} questions — Pro unlocks medium + hard.`}
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
                <Link className="btn btn-primary sample-challenge-button" to={challengePath}>
                  Enter challenge track
                </Link>
              </div>
            </div>
          </aside>

          <section className="right-panel">
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
                      disabled={submitting || running || selectedOption === null}
                    >
                      {submitting ? 'Checking…' : 'Submit Answer'}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="editor-wrapper editor-workspace">
                <div className="editor-topbar">
                  <span className="editor-title">{editorTitle}</span>
                  <div className="editor-topbar-actions">
                    <span className="editor-topbar-note">
                      {draftSaveState === 'saving' ? 'Saving draft…' : draftSaveState === 'saved' ? 'Draft saved' : editorNote}
                    </span>
                    <button
                      className="editor-expand-btn"
                      onClick={clearDraft}
                      title="Clear saved draft"
                      aria-label="Clear saved draft"
                    >
                      ✕
                    </button>
                    <button
                      className="editor-expand-btn"
                      onClick={() => setCode(meta.language === 'python' && question?.starter_code ? question.starter_code : defaultCode)}
                      title="Reset to default"
                      aria-label="Reset to default"
                    >
                      ↺
                    </button>
                    <button
                      className="editor-expand-btn"
                      onClick={toggleEditorHeight}
                      title={editorTall ? 'Collapse editor' : 'Expand editor (⌘↵ run · ⌘⇧↵ submit)'}
                      aria-label={editorTall ? 'Collapse editor' : 'Expand editor'}
                    >
                      {editorTall ? '⊟' : '⊞'}
                    </button>
                  </div>
                </div>

                <CodeEditor
                  value={code}
                  onChange={setCode}
                  language={meta.language}
                  height={editorTall ? '560px' : '340px'}
                  onMount={handleEditorMount}
                  ariaLabel={`${topicLabel} sample editor`}
                />

                <div className="editor-footer question-action-dock">
                  <div className="button-row question-action-row">
                    {meta.hasRunCode && (
                      <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting}>
                        {running ? 'Running…' : meta.language === 'python' ? 'Run Code' : 'Run Query'}
                      </button>
                    )}
                    <button className="btn btn-primary" onClick={handleSubmit} disabled={running || submitting}>
                      {submitting ? 'Checking…' : 'Submit Answer'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {runError && <div className="error-box">{runError}</div>}

            {topic === 'sql' && runResult?.rows && (
              <div className="results-card">
                <div className="results-header">
                  <span>Query Result</span>
                  <span>{runResult.rows.length} row{runResult.rows.length !== 1 ? 's' : ''}</span>
                </div>
                <ResultsTable columns={runResult.columns} rows={runResult.rows} />
              </div>
            )}

            {topic === 'python' && pythonRunResults.length > 0 && (
              <>
                <TestCasePanel results={pythonRunResults} hiddenSummary={null} />
                <PrintOutputPanel output={pythonRunOutput} />
              </>
            )}

            {topic === 'python-data' && pandasRunResult && (
              <>
                <div className="results-card">
                  <div className="results-header">
                    <span>Output</span>
                    <span>{(pandasRunResult.rows ?? []).length} rows</span>
                  </div>
                  <ResultsTable columns={pandasRunResult.columns ?? []} rows={pandasRunResult.rows ?? []} />
                </div>
                <PrintOutputPanel output={pandasRunOutput} />
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

            {topic === 'sql' && submitResult?.user_result && (
              <div className="results-compare-grid">
                <div className="results-card">
                  <div className="results-header">
                    <span>Your Output</span>
                    <span>{submitResult.user_result.rows.length} rows</span>
                  </div>
                  <ResultsTable columns={submitResult.user_result.columns} rows={submitResult.user_result.rows} />
                </div>
                <div className="results-card">
                  <div className="results-header">
                    <span>Expected Output</span>
                    <span>{submitResult.expected_result.rows.length} rows</span>
                  </div>
                  <ResultsTable columns={submitResult.expected_result.columns} rows={submitResult.expected_result.rows} />
                </div>
              </div>
            )}

            {topic === 'python' && submitResult && (
              <>
                <TestCasePanel
                  results={pythonSubmitResults}
                  hiddenSummary={submitResult.hidden_summary ?? null}
                />
                <PrintOutputPanel output={submitResult.stdout ?? ''} />
              </>
            )}

            {topic === 'python-data' && submitResult?.user_result && (
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
                <PrintOutputPanel output={pandasSubmitOutput} />
              </div>
            )}

            {showSolutionToggle && (
              <div className="post-submit-stack">
                <button
                  className="btn btn-secondary workspace-inline-action"
                  onClick={() => setShowSolution((value) => !value)}
                >
                  {showSolution ? 'Hide Official Solution' : 'Review Official Solution'}
                </button>

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
    </>
  );
}
