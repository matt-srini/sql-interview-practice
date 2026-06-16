import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
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
import { TRACK_SLUGS } from '../trackRegistry';
import { useCatalogCounts } from '../contexts/CatalogCountsContext';
import { useTheme } from '../App';
import { renderDescription } from '../utils/renderDescription';
import { normalizeRunResult, rowCountLabel } from '../normalizeResult';
import { track } from '../analytics';

const SQL_PLACEHOLDER = '-- Write your SQL query here\nSELECT ';
const PYTHON_PLACEHOLDER = '# Write your solution here\n';
const DIFFICULTIES = ['easy', 'medium', 'hard'];

// In-page track + difficulty switcher so users can pivot without leaving
// the sample surface. Lives in the SampleQuestionPage topbar (both states).
function SampleSwitcher({ topic, difficulty, navigate }) {
  return (
    <div className="sample-switcher">
      <select
        className="sample-switcher-track"
        value={topic}
        onChange={(e) => navigate(`/sample/${e.target.value}/${difficulty}`)}
        aria-label="Switch sample track"
      >
        {TRACK_SLUGS.map((slug) => (
          <option key={slug} value={slug}>{TRACK_META[slug].label}</option>
        ))}
      </select>
      <div className="sample-switcher-diffs" role="group" aria-label="Switch sample difficulty">
        {DIFFICULTIES.map((d) => (
          <Link
            key={d}
            to={`/sample/${topic}/${d}`}
            className={`sample-switcher-diff${d === difficulty ? ' is-active' : ''}`}
          >
            {d.charAt(0).toUpperCase() + d.slice(1)}
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function SampleQuestionPage() {
  const { topic: rawTopic, difficulty } = useParams();
  const topic = TRACK_META[rawTopic] ? rawTopic : 'sql';
  const meta = TRACK_META[topic];
  const allCounts = useCatalogCounts();
  const trackTotal = allCounts[topic]?.total ?? 0;
  const { isDark } = useTheme();
  const navigate = useNavigate();

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

  // For mixed-subtype tracks (Statistics), derive render mode from the loaded question's subtype.
  // For all other tracks use the static track-level hasMCQ flag.
  const renderMode = useMemo(() => {
    if (meta.mixedSubtype) {
      return question?.subtype === 'numerical' ? 'code' : 'mcq';
    }
    return meta.hasMCQ ? 'mcq' : 'code';
  }, [meta.mixedSubtype, meta.hasMCQ, question?.subtype]);

  // Refs for Monaco keyboard shortcuts
  const handleRunRef = useRef(null);
  const handleSubmitRef = useRef(null);
  const runningRef = useRef(false);
  const submittingRef = useRef(false);
  const editorRef = useRef(null);
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
        const isCodeMode = meta.mixedSubtype ? nextQuestion.subtype === 'numerical' : !meta.hasMCQ;
        if (isCodeMode) {
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
    if (renderMode !== 'code' || !question || !draftKey || !draftHydratedRef.current) return undefined;
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
  }, [code, draftKey, renderMode, question]);

  useEffect(() => () => {
    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
  }, []);

  const topicLabel = meta.label;
  const position = sampleMeta?.position ?? sampleMeta?.shown_count ?? 1;
  const totalSamples = sampleMeta?.total ?? 3;
  const attemptedCount = sampleMeta?.attempted ?? 0;
  const servedDifficulty = sampleMeta?.served_difficulty ?? difficulty;
  const sampleStatusLine = useMemo(() => {
    const chunks = [
      `${servedDifficulty.charAt(0).toUpperCase()}${servedDifficulty.slice(1)} sample`,
      `Question ${position} of ${totalSamples}`,
    ];
    if (attemptedCount > 0) {
      chunks.push(`${attemptedCount} attempted`);
    }
    return chunks.join(' · ');
  }, [attemptedCount, position, servedDifficulty, totalSamples]);

  async function handleAnotherSample() {
    if (!question) return;
    // Resume-model: skip is an explicit commit — POST it before re-fetching.
    // This is what marks the current question as attempted; pure GET no longer
    // advances the user's progress.
    try {
      await api.post(`${sampleBasePath}/${difficulty}/skip`, { question_id: Number(question.id) });
      setResetNotice('');
      setReloadToken((value) => value + 1);
    } catch (err) {
      if (err.response?.status === 409) {
        setSampleExhausted(true);
        return;
      }
      setLoadError(err.response?.data?.detail ?? 'Failed to load the next sample.');
    }
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
      setRunResult(normalizeRunResult(res.data));
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
      if (renderMode === 'mcq') {
        payload = { selected_option: selectedOption, question_id: Number(question.id) };
      } else if (meta.language === 'python') {
        payload = { code, question_id: Number(question.id) };
      } else {
        payload = { query: code, question_id: Number(question.id) };
      }
      const res = await api.post(submitApiPath, payload);
      setSubmitResult(normalizeRunResult(res.data));
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
    editorRef.current = editor;
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

  async function handleCopy() {
    if (!editorRef.current) return;
    const editor = editorRef.current;
    const sel = editor.getSelection();
    const text = (sel && sel.startLineNumber === sel.endLineNumber && sel.startColumn === sel.endColumn)
      ? editor.getValue()
      : editor.getModel().getValueInRange(sel);
    try { await navigator.clipboard.writeText(text); } catch (_) {}
  }

  async function handlePaste() {
    try {
      const text = await navigator.clipboard.readText();
      if (!text || !editorRef.current) return;
      const editor = editorRef.current;
      const selection = editor.getSelection();
      editor.executeEdits('paste-btn', [{ range: selection, text, forceMoveMarkers: true }]);
      editor.focus();
    } catch (_) { /* permission denied or clipboard empty — silently skip */ }
  }

  function toggleEditorHeight() {
    setEditorTall((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor-height-pref', next ? 'tall' : 'normal'); } catch {}
      return next;
    });
  }

  function clearDraft() {
    if (renderMode !== 'code' || !question || !draftKey) return;
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
              <Link className="sample-home-link brand-wordmark" to="/">
                <div className="brand-lockup">
                  <img
                    src={isDark ? '/branding/mark-reverse-no-bg.svg' : '/branding/mark-no-bg.svg'}
                    alt=""
                    aria-hidden="true"
                    className="brand-mark-img"
                  />
                  <span className="brand-wordmark-text" aria-hidden="true">
                    <span className="brand-data">data</span><span className="brand-think">think</span>
                  </span>
                </div>
              </Link>
            </div>
            <div className="sample-topbar-center">
              <button
                type="button"
                className="sample-back-link"
                aria-label="Back to sample hub"
                onClick={() => navigate('/sample')}
              >←</button>
              <span
                className="shell-pill shell-pill-mode shell-pill-mode-sample"
                style={{ '--mode-dot-color': meta.color }}
              >
                <span className="shell-pill-mode-dot" aria-hidden="true" />
                {topicLabel} · Sample
              </span>
              <SampleSwitcher topic={topic} difficulty={difficulty} navigate={navigate} />
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
                <h3>You've attempted all {totalSamples} {difficulty} samples for {topicLabel}</h3>
              </div>
              <span className="section-meta">{totalSamples} attempted</span>
            </div>
            <p className="sample-challenge-copy">
              Ready for the full {trackTotal ? `${trackTotal}-question ` : ''}{topicLabel} track? Pro unlocks every medium + hard question.
            </p>
            <div className="sample-challenge-actions">
              <Link className="btn btn-primary sample-challenge-button" to={challengePath}>
                Take the challenge
              </Link>
            </div>
            <button
              type="button"
              className="sample-reset-link"
              onClick={handleResetSamples}
              disabled={resetting}
            >
              {resetting ? 'Resetting…' : 'Or redo this set from scratch →'}
            </button>
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
  const showVariables = topic === 'pandas';
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
  const editorTitle = renderMode === 'mcq'
    ? 'Code preview'
    : meta.language === 'python'
      ? 'Python editor'
      : 'SQL editor';
  const editorNote = renderMode === 'mcq'
    ? 'Read-only'
    : meta.language === 'python'
      ? 'Sandboxed execution'
      : 'DuckDB sandbox';

  return (
    <>
      <Helmet>
        <title>Free {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} {meta.label} Sample Questions — datathink</title>
        <meta name="description" content={`Try free ${difficulty} ${meta.label} interview questions — no account required. Real execution environment with instant feedback.`} />
        <meta property="og:title" content={`Free ${difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} ${meta.label} Sample Questions — datathink`} />
        <meta property="og:description" content={`Try free ${difficulty} ${meta.label} interview questions — no account required. Real execution environment with instant feedback.`} />
        <meta property="og:url" content={`https://datathink.co/sample/${topic}/${difficulty}`} />
        <meta property="og:image" content="https://datathink.co/og-image.png?v=4" />
        <link rel="canonical" href={`https://datathink.co/sample/${topic}/${difficulty}`} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:image" content="https://datathink.co/og-image.png?v=4" />
        <script type="application/ld+json">{JSON.stringify({
          "@context": "https://schema.org",
          "@type": "Quiz",
          "name": `Free ${difficulty.charAt(0).toUpperCase() + difficulty.slice(1)} ${meta.label} Interview Questions`,
          "description": `Practice free ${difficulty} ${meta.label} interview questions with instant execution and feedback. No account required.`,
          "educationalLevel": difficulty,
          "inLanguage": "en",
          "isAccessibleForFree": true,
          "about": { "@type": "Thing", "name": `${meta.label} interview preparation` },
          "learningResourceType": "Practice problems",
          "provider": { "@type": "Organization", "name": "datathink", "url": "https://datathink.co" }
        })}</script>
      </Helmet>
      <header className="topbar">
        <div className="topbar-inner sample-page-topbar">
          <div className="sample-topbar-left">
            <Link className="sample-home-link brand-wordmark" to="/">
              <div className="brand-lockup">
                <img
                  src={isDark ? '/branding/mark-reverse-no-bg.svg' : '/branding/mark-no-bg.svg'}
                  alt=""
                  aria-hidden="true"
                  className="brand-mark-img"
                />
                <span className="brand-wordmark-text" aria-hidden="true">
                  <span className="brand-data">data</span><span className="brand-think">think</span>
                </span>
              </div>
            </Link>
          </div>
          <div className="sample-topbar-center">
            <button
              type="button"
              className="sample-back-link"
              aria-label="Back to sample hub"
              onClick={() => navigate('/sample')}
            >←</button>
            <span
              className="shell-pill shell-pill-mode shell-pill-mode-sample"
              style={{ '--mode-dot-color': meta.color }}
            >
              <span className="shell-pill-mode-dot" aria-hidden="true" />
              {topicLabel} · Sample
            </span>
            <SampleSwitcher topic={topic} difficulty={difficulty} navigate={navigate} />
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

              <div className="description-text">{renderDescription(question.description)}</div>

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
                  <h3>{attemptedCount < totalSamples ? 'Keep sampling or move into the full flow' : 'Sample set exhausted'}</h3>
                </div>
                <span className="section-meta">{attemptedCount}/{totalSamples} attempted</span>
              </div>
              <p className="sample-challenge-copy">
                {attemptedCount < totalSamples
                  ? `Question ${position} of ${totalSamples} in this ${difficulty} set. Submitting or "Another sample →" advances; refreshing keeps you here.`
                  : `You've attempted all ${totalSamples} ${difficulty} samples. The full ${topicLabel} track has ${trackTotal || 'many'} questions — Pro unlocks medium + hard.`}
              </p>
              <div className="sample-challenge-actions">
                {attemptedCount < totalSamples && (
                  <button className="btn btn-secondary sample-challenge-button" onClick={handleAnotherSample}>
                    Another sample →
                  </button>
                )}
                <Link className="btn btn-primary sample-challenge-button" to={challengePath}>
                  Enter challenge track
                </Link>
              </div>
              <button
                type="button"
                className="sample-reset-link"
                onClick={handleResetSamples}
                disabled={resetting}
              >
                {resetting ? 'Resetting…' : 'Or redo this set from scratch →'}
              </button>
            </div>
          </aside>

          <section className="right-panel">
            {renderMode === 'mcq' ? (
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
                    <div className="editor-clipboard-group">
                      <button className="editor-expand-btn" onClick={handleCopy} title="Copy (selection or all)" aria-label="Copy code">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                      </button>
                      <button className="editor-expand-btn" onClick={handlePaste} title="Paste from clipboard" aria-label="Paste from clipboard">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>
                      </button>
                    </div>
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
                        <span>{running ? 'Running…' : meta.language === 'python' ? 'Run Code' : 'Run Query'}</span>
                        <kbd className="shortcut-kbd">⌘↵</kbd>
                      </button>
                    )}
                    <button className="btn btn-primary" onClick={handleSubmit} disabled={running || submitting}>
                      <span>{submitting ? 'Checking…' : 'Submit Answer'}</span>
                      <kbd className="shortcut-kbd">⌘⇧↵</kbd>
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
                  <span>{rowCountLabel(runResult)}</span>
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

            {topic === 'pandas' && pandasRunResult && (
              <>
                <div className="results-card">
                  <div className="results-header">
                    <span>Output</span>
                    <span>{rowCountLabel(pandasRunResult)}</span>
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
                    <span>{rowCountLabel(submitResult.user_result)}</span>
                  </div>
                  <ResultsTable columns={submitResult.user_result.columns} rows={submitResult.user_result.rows} />
                </div>
                <div className="results-card">
                  <div className="results-header">
                    <span>Expected Output</span>
                    <span>{rowCountLabel(submitResult.expected_result)}</span>
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

            {topic === 'statistics' && renderMode === 'code' && submitResult && (
              <>
                <TestCasePanel
                  results={pythonSubmitResults}
                  hiddenSummary={submitResult.hidden_summary ?? null}
                />
                <PrintOutputPanel output={submitResult.stdout ?? ''} />
              </>
            )}

            {topic === 'pandas' && submitResult?.user_result && (
              <div className="results-compare-grid">
                <div className="results-card">
                  <div className="results-header">
                    <span>Your Output</span>
                    <span>{rowCountLabel(submitResult.user_result)}</span>
                  </div>
                  <ResultsTable
                    columns={submitResult.user_result.columns ?? []}
                    rows={submitResult.user_result.rows ?? []}
                  />
                </div>
                <div className="results-card">
                  <div className="results-header">
                    <span>Expected Output</span>
                    <span>{rowCountLabel(submitResult.expected_result)}</span>
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
