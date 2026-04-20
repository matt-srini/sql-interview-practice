import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
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
import { useAuth } from '../contexts/AuthContext';
import UpgradeButton from '../components/UpgradeButton';

const SQL_PLACEHOLDER = '-- Write your SQL query here\nSELECT ';
const PYTHON_PLACEHOLDER = '# Write your solution here\n';

export default function QuestionPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { catalog, refresh } = useCatalog();
  const { topic, meta } = useTopic();
  const navigate = useNavigate();
  const { user } = useAuth();

  // Path context — set when arriving from a learning path (?path=slug)
  const pathSlug = searchParams.get('path');
  const [pathContext, setPathContext] = useState(null);
  useEffect(() => {
    if (!pathSlug) { setPathContext(null); return; }
    api.get(`/paths/${pathSlug}`)
      .then(r => setPathContext(r.data))
      .catch(() => setPathContext(null));
  }, [pathSlug]);

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
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const [solutionAnalysisOpen, setSolutionAnalysisOpen] = useState(false);
  const [showAltSolution, setShowAltSolution] = useState(false);
  const [submissionInsight, setSubmissionInsight] = useState(null);
  const [editorTall, setEditorTall] = useState(() => {
    try { return localStorage.getItem('editor-height-pref') === 'tall'; } catch { return false; }
  });
  const priorAttemptCountRef = useRef(0);
  const verdictRef = useRef(null);

  // Refs used by Monaco keyboard commands to avoid stale closures.
  // Updated inline on every render (before any early return that uses them).
  const handleRunRef = useRef(null);
  const handleSubmitRef = useRef(null);
  const runningRef = useRef(false);
  const submittingRef = useRef(false);
  const isLockedRef = useRef(false);

  // MCQ state for PySpark
  const [selectedOption, setSelectedOption] = useState(null);
  const [schemaSheetOpen, setSchemaSheetOpen] = useState(false);

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
    api.get('/submissions', { params: { track: topic, question_id: id, limit: 20 } })
      .then((res) => setPastAttempts(res.data))
      .catch(() => {});
  }, [id, topic, questionApiPath, meta.language, meta.hasMCQ, defaultCode]);

  useEffect(() => () => {
    try {
      localStorage.setItem('last_seen_question_id', String(id));
    } catch {}
  }, [id]);

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
    setPastAttemptsOpen(() => {
      try {
        return localStorage.getItem('last_seen_question_id') === String(id);
      } catch {
        return false;
      }
    });
    setOpenAttemptCodes(new Set());
    setShortcutHelpOpen(false);
    setSolutionAnalysisOpen(false);
    setShowAltSolution(false);
    setSubmissionInsight(null);
  }, [id, meta.language, meta.hasMCQ]);

  useEffect(() => {
    const isEditableTarget = (target) => {
      if (!target || !(target instanceof Element)) return false;
      if (target.isContentEditable) return true;
      const tag = target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
      return !!target.closest('.monaco-editor');
    };

    const handleKeyDown = (event) => {
      const isHelpKey = event.key === '?' || (event.key === '/' && event.shiftKey);
      if (isHelpKey && !event.metaKey && !event.ctrlKey && !event.altKey) {
        if (isEditableTarget(event.target)) return;
        event.preventDefault();
        setShortcutHelpOpen((open) => !open);
        return;
      }

      if (event.key === 'Escape') {
        setShortcutHelpOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Scroll the verdict into view after submission resolves so users don't
  // have to hunt for results that appeared below the fold.
  useEffect(() => {
    if (submitResult) {
      if (verdictRef.current) {
        const rect = verdictRef.current.getBoundingClientRect();
        if (rect.top < 80 || rect.bottom > window.innerHeight) {
          verdictRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }
  }, [submitResult]);

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
    if (submitting) return;
    priorAttemptCountRef.current = pastAttempts.length;
    setSubmitting(true);
    setSubmitResult(null);
    setSubmitError(null);
    setShowSolution(false);
    setSubmissionInsight(null);
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
      if (res.data.correct) {
        await refresh();
        const prior = priorAttemptCountRef.current;
        if (prior === 0) setSubmissionInsight('First-attempt solve — the system logged your approach.');
        else if (prior >= 3) setSubmissionInsight('Took a few tries — that\'s the shape of real learning.');
        // Auto-open writing notes on first-attempt correct solve
        if (prior === 0) setSolutionAnalysisOpen(true);
      }
      api.get('/submissions', { params: { track: topic, question_id: id, limit: 20 } })
        .then((r) => setPastAttempts(r.data))
        .catch(() => {});
    } catch (err) {
      setSubmitError(err.response?.data?.error ?? err.response?.data?.detail ?? 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  }

  // Keep shortcut refs current on every render (safe to assign outside useEffect).
  // Must appear after handleRun / handleSubmit are defined and before early returns.
  handleRunRef.current = handleRun;
  handleSubmitRef.current = handleSubmit;
  runningRef.current = running;
  submittingRef.current = submitting;
  // isLockedRef.current is set after the !question guard below, where isLocked is computed.

  // Registered as Monaco's onMount callback; wires Cmd/Ctrl+Enter → Run,
  // Cmd/Ctrl+Shift+Enter → Submit. Refs ensure commands always call the latest handlers.
  function handleEditorMount(editor, monaco) {
    // Cmd/Ctrl + Enter → Run Query / Run Code  (safe, reversible, frequent)
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!runningRef.current && !submittingRef.current && !isLockedRef.current && meta.hasRunCode) {
        handleRunRef.current();
      }
    });
    // Cmd/Ctrl + Shift + Enter → Submit Answer  (deliberate, permanent)
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter,
      () => {
        if (!submittingRef.current && !runningRef.current && !isLockedRef.current) {
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

  // Delta hint: row/column diff diagnostic for wrong SQL submissions
  const deltaHint = useMemo(() => {
    if (!submitResult || submitResult.correct || topic !== 'sql') return null;
    const userRows = submitResult.user_result?.rows;
    const expectedRows = submitResult.expected_result?.rows;
    if (!userRows || !expectedRows) return null;
    const rowDiff = userRows.length - expectedRows.length;
    const userCols = submitResult.user_result?.columns?.length ?? 0;
    const expectedCols = submitResult.expected_result?.columns?.length ?? 0;
    if (rowDiff > 0) return `Your output has ${rowDiff} more row${rowDiff !== 1 ? 's' : ''} than expected. Check for a missing filter or a JOIN that multiplies rows.`;
    if (rowDiff < 0) return `Your output has ${Math.abs(rowDiff)} fewer row${Math.abs(rowDiff) !== 1 ? 's' : ''} than expected. You may be filtering too aggressively, or missing a LEFT JOIN.`;
    if (userCols !== expectedCols) return 'Row count matches but columns differ. Check your SELECT clause and column aliases.';
    return 'Row and column counts match — check individual values. Look for rounding, type casting, or NULL handling differences.';
  }, [submitResult, topic]);

  // Path nav bar derived values — must be before early returns (Rules of Hooks)
  const pathNavBar = useMemo(() => {
    if (!pathContext) return null;
    const questions = pathContext.questions ?? [];
    const currentIndex = questions.findIndex(q => String(q.id) === String(id));
    if (currentIndex === -1) return null;
    const prev = questions[currentIndex - 1] ?? null;
    const next = questions[currentIndex + 1] ?? null;
    return { path: pathContext, currentIndex, total: questions.length, prev, next };
  }, [pathContext, id]);

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
  isLockedRef.current = isLocked; // keep Monaco shortcut guard fresh
  const editorHeight = editorTall ? '560px' : '340px';
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
  const canRevealSolution = !!submitResult
    && (submitResult.correct || hintsShown >= (question.hints?.length ?? 0));

  const isSubmitDisabled = submitting || running || isLocked
    || (meta.hasMCQ && selectedOption === null);

  return (
    <main className="container question-page question-page-challenge">
      {pathNavBar && (
        <div className="path-nav-bar">
          <Link to={`/learn/${pathNavBar.path.topic}/${pathNavBar.path.slug}`} className="path-nav-back">
            ← {pathNavBar.path.title}
          </Link>
          <span className="path-nav-pos">
            {pathNavBar.currentIndex + 1} / {pathNavBar.total}
          </span>
          <div className="path-nav-arrows">
            {pathNavBar.prev && !['locked'].includes(pathNavBar.prev.state) ? (
              <Link
                to={`/practice/${topic}/questions/${pathNavBar.prev.id}?path=${pathSlug}`}
                className="path-nav-btn"
              >
                ← Prev
              </Link>
            ) : <span className="path-nav-btn path-nav-btn--disabled">← Prev</span>}
            {pathNavBar.next && !['locked'].includes(pathNavBar.next.state) ? (
              <Link
                to={`/practice/${topic}/questions/${pathNavBar.next.id}?path=${pathSlug}`}
                className="path-nav-btn path-nav-btn--next"
              >
                Next →
              </Link>
            ) : pathNavBar.next ? (
              <span className="path-nav-btn path-nav-btn--disabled" title="Locked — solve more questions to unlock">Next 🔒</span>
            ) : (
              <span className="path-nav-btn path-nav-btn--disabled">Last question</span>
            )}
          </div>
        </div>
      )}
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

            {question.companies?.length > 0 && (
              <div className="concept-tags concept-tags-inline">
                {question.companies.map((company) => (
                  <span key={company} className="tag-company">{company}</span>
                ))}
              </div>
            )}

            <p className="description-text">{question.description}</p>

            {/* PySpark: show code snippet (question stem) if present */}
            {meta.hasMCQ && question.code_snippet && (
              <pre className="question-code-snippet">{question.code_snippet}</pre>
            )}

            {isLocked && (() => {
              const plan = user?.plan ?? 'free';
              const difficulty = question?.difficulty;
              // State 1: threshold-locked (Free, reachable by solving more)
              const isThresholdLocked = plan === 'free' && (difficulty === 'medium' || difficulty === 'hard');

              // Unlock thresholds mirror unlock.py exactly.
              // Each entry: [solvedNeeded, maxQuestionsUnlocked]
              const isPySpark = topic === 'pyspark';
              const MEDIUM_THRESHOLDS = isPySpark
                ? [[12, 3], [20, 8], [30, Infinity]]
                : [[8, 3], [15, 8], [25, Infinity]];
              const HARD_THRESHOLDS = isPySpark
                ? [[15, 5], [22, Infinity]]
                : [[8, 3], [15, 8], [22, Infinity]];

              // 1-indexed position of this question in the sorted difficulty list
              const sortedGroup = (catalogQuestionMeta?.group?.questions ?? [])
                .slice().sort((a, b) => a.order - b.order);
              const questionPos = sortedGroup.findIndex(q => Number(q.id) === Number(id)) + 1;

              // Find the threshold tier that covers this question's position
              const easyThresholdEntry  = MEDIUM_THRESHOLDS.find(([, max]) => questionPos <= max);
              const medThresholdEntry   = HARD_THRESHOLDS.find(([, max]) => questionPos <= max);

              const easySolved   = catalog?.groups?.find(g => g.difficulty === 'easy')?.counts?.solved ?? 0;
              const mediumSolved = catalog?.groups?.find(g => g.difficulty === 'medium')?.counts?.solved ?? 0;

              const nextEasyNeeded   = difficulty === 'medium' && easyThresholdEntry
                ? Math.max(0, easyThresholdEntry[0] - easySolved)
                : null;
              const nextMediumNeeded = difficulty === 'hard' && medThresholdEntry
                ? Math.max(0, medThresholdEntry[0] - mediumSolved)
                : null;
              const solveMoreCopy = difficulty === 'medium' && nextEasyNeeded > 0
                ? `Solve ${nextEasyNeeded} more easy ${topic === 'sql' ? 'SQL' : topic} question${nextEasyNeeded !== 1 ? 's' : ''} to unlock this.`
                : difficulty === 'hard' && nextMediumNeeded > 0
                ? `Solve ${nextMediumNeeded} more medium question${nextMediumNeeded !== 1 ? 's' : ''} to unlock this.`
                : null;

              // Celebration context — lead with what the user has achieved
              const progressSolved = difficulty === 'medium' ? easySolved : mediumSolved;
              const progressLabel = difficulty === 'medium' ? 'easy' : 'medium';
              const progressCelebration = progressSolved >= 15
                ? `You've solved ${progressSolved} ${progressLabel} questions — strong work.`
                : progressSolved >= 8
                ? `You've solved ${progressSolved} ${progressLabel} questions — solid progress.`
                : progressSolved > 0
                ? `You've solved ${progressSolved} ${progressLabel} question${progressSolved !== 1 ? 's' : ''} so far.`
                : null;

              return (
                <div className="preview-locked-callout">
                  {progressCelebration && (
                    <p className="preview-locked-progress">{progressCelebration}</p>
                  )}
                  {isThresholdLocked && solveMoreCopy ? (
                    <>
                      <p className="preview-locked-headline">Preview mode</p>
                      <p className="preview-locked-body">{solveMoreCopy} Or open access now.</p>
                      <div className="preview-locked-actions">
                        <Link to={`/practice/${topic}`} className="btn btn-secondary btn-compact">
                          Go to next {difficulty === 'medium' ? 'easy' : 'medium'} →
                        </Link>
                        <UpgradeButton tier="pro" label="Unlock now with Pro" compact source="question_preview" />
                      </div>
                    </>
                  ) : (
                    <>
                      <p className="preview-locked-headline">
                        {difficulty === 'hard' ? 'Hard practice is included with Pro' : 'Unlock with Pro'}
                      </p>
                      <p className="preview-locked-body">
                        {difficulty === 'hard'
                          ? 'Full hard access across all tracks, plus daily hard mock interviews.'
                          : 'All medium and hard questions, plus full learning path access.'}
                      </p>
                      <div className="preview-locked-actions">
                        <UpgradeButton tier="pro" compact source="question_preview_plan" />
                      </div>
                    </>
                  )}
                </div>
              );
            })()}
          </div>

          {showSchema && (
            <>
              {/* Desktop: inline schema card */}
              <div className="card schema-card schema-card-utility">
                <div className="section-heading">
                  <div>
                    <h3>Table schema</h3>
                  </div>
                  <span className="section-meta">{schemaTableCount} tables</span>
                </div>
                <SchemaViewer schema={question.schema} />
              </div>

              {/* Mobile: trigger button (CSS hides this on desktop) */}
              <button
                className="schema-sheet-trigger"
                onClick={() => setSchemaSheetOpen(true)}
              >
                ⊞ Table schema ({schemaTableCount} {schemaTableCount === 1 ? 'table' : 'tables'})
              </button>

              {/* Mobile: bottom-sheet overlay */}
              <div
                className={`schema-bottom-sheet${schemaSheetOpen ? ' is-open' : ''}`}
                aria-modal="true"
                role="dialog"
                aria-label="Table schema"
              >
                <div
                  className="schema-bottom-sheet-backdrop"
                  onClick={() => setSchemaSheetOpen(false)}
                />
                <div className="schema-bottom-sheet-panel">
                  <div className="schema-bottom-sheet-header">
                    <span className="schema-bottom-sheet-title">Table schema</span>
                    <button
                      className="schema-bottom-sheet-close"
                      onClick={() => setSchemaSheetOpen(false)}
                      aria-label="Close schema"
                    >
                      ×
                    </button>
                  </div>
                  <div className="schema-bottom-sheet-body">
                    <SchemaViewer schema={question.schema} />
                  </div>
                </div>
              </div>
            </>
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
                  {submitResult?.correct && (pathNavBar?.next && !['locked'].includes(pathNavBar.next.state) ? (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${pathNavBar.next.id}?path=${pathSlug}`)}
                    >
                      Next in Path
                    </button>
                  ) : !pathNavBar && nextQuestionId ? (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${nextQuestionId}`)}
                    >
                      Next Question
                    </button>
                  ) : null)}
                </div>
              </div>
            </div>
          ) : (
            /* Code/SQL editor */
            <div className="editor-wrapper editor-workspace">
              <div className="editor-topbar">
                <span className="editor-title">{editorTitle}</span>
                <div className="editor-topbar-actions">
                  <button
                    className="editor-expand-btn"
                    onClick={() => setShortcutHelpOpen((open) => !open)}
                    title="Keyboard shortcuts (?)"
                    aria-label="Keyboard shortcuts"
                    aria-expanded={shortcutHelpOpen}
                  >
                    ?
                  </button>
                  <span className="editor-topbar-note">{editorNote}</span>
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

              {shortcutHelpOpen && (
                <div className="workspace-shortcut-popover" role="dialog" aria-label="Keyboard shortcuts">
                  <div className="workspace-shortcut-row">
                    <span>Run query/code</span>
                    <kbd className="shortcut-kbd">⌘↵</kbd>
                  </div>
                  <div className="workspace-shortcut-row">
                    <span>Submit answer</span>
                    <kbd className="shortcut-kbd">⌘⇧↵</kbd>
                  </div>
                  <div className="workspace-shortcut-row">
                    <span>Toggle this help</span>
                    <kbd className="shortcut-kbd">?</kbd>
                  </div>
                </div>
              )}

              <CodeEditor
                value={code}
                onChange={setCode}
                language={meta.language}
                height={editorHeight}
                onMount={handleEditorMount}
              />

              <div className="editor-footer question-action-dock">
                {(running || submitting) && (
                  <div className="execution-bar" aria-hidden="true" />
                )}
                <div className="button-row question-action-row">
                  {meta.hasRunCode && (
                    <button className="btn btn-secondary" onClick={handleRun} disabled={running || submitting || isLocked}>
                      <span>{running ? 'Running…' : meta.language === 'python' ? 'Run Code' : 'Run Query'}</span>
                      <kbd className="shortcut-kbd">⌘↵</kbd>
                    </button>
                  )}
                  <button className="btn btn-primary" onClick={handleSubmit} disabled={isSubmitDisabled}>
                    <span>{submitBtnLabel}</span>
                    <kbd className="shortcut-kbd">⌘⇧↵</kbd>
                  </button>
                  {submitResult?.correct && (pathNavBar?.next && !['locked'].includes(pathNavBar.next.state) ? (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${pathNavBar.next.id}?path=${pathSlug}`)}
                    >
                      Next in Path
                    </button>
                  ) : !pathNavBar && nextQuestionId ? (
                    <button
                      className="btn btn-success"
                      onClick={() => navigate(`/practice/${topic}/questions/${nextQuestionId}`)}
                    >
                      Next Question
                    </button>
                  ) : null)}
                </div>
              </div>
            </div>
          )}

          {runError && <div className="error-box">{runError}</div>}

          {/* Skeleton run result — visible while query/code is executing */}
          {running && !runError && (
            <div className="results-card">
              <div className="results-header">
                <span>{topic === 'python' ? 'Running tests…' : 'Query Result'}</span>
                <div className="skeleton-line skeleton-shimmer" style={{ width: '2.5rem', height: '11px' }} />
              </div>
              <div className="results-skeleton-body">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className="results-skeleton-row skeleton-shimmer"
                    style={{ animationDelay: `${(i - 1) * 60}ms` }}
                  />
                ))}
              </div>
            </div>
          )}

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

          {/* Skeleton verdict — visible while submission is being evaluated */}
          {submitting && !submitError && (
            <div className="verdict-skeleton">
              <div className="skeleton-line skeleton-shimmer" style={{ width: '5rem', height: '13px' }} />
              <div className="skeleton-line skeleton-shimmer" style={{ width: '70%', height: '11px' }} />
              <div className="skeleton-line skeleton-shimmer" style={{ width: '50%', height: '11px', animationDelay: '80ms' }} />
            </div>
          )}

          {submitting && !submitError && topic === 'sql' && (
            <div className="solution-analysis-skeleton">
              <div className="skeleton-line skeleton-shimmer" style={{ width: '9rem', height: '12px' }} />
              <div className="skeleton-line skeleton-shimmer" style={{ width: '75%', height: '10px' }} />
              <div className="skeleton-line skeleton-shimmer" style={{ width: '84%', height: '10px', animationDelay: '70ms' }} />
            </div>
          )}

          {submitResult && (
            <div className="submit-outcome" ref={verdictRef}>
              <div className={`verdict ${submitResult.correct ? 'verdict-correct' : 'verdict-incorrect'}`}>
                <div className="verdict-header-row">
                  <span className="verdict-label">{submitResult.correct ? 'Correct' : 'Keep iterating'}</span>
                  {canRevealSolution && (
                    <button
                      className="btn btn-secondary workspace-inline-action verdict-solution-toggle"
                      onClick={() => setShowSolution((value) => !value)}
                    >
                      {showSolution ? 'Hide Official Solution' : 'Review Official Solution'}
                    </button>
                  )}
                </div>
                <p className="verdict-copy">
                  {submitResult.correct
                    ? 'Your submission matches the expected result.'
                    : 'Your submission does not match the expected result yet.'}
                </p>
                {submissionInsight && (
                  <p className="verdict-insight">{submissionInsight}</p>
                )}
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

          {/* SQL submit: show compare grid only on wrong answers — correct needs no diff */}
          {submitResult && !submitResult.correct && topic === 'sql' && submitResult.user_result && (
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

          {/* SQL delta hint for wrong submissions */}
          {deltaHint && (
            <div className="delta-hint">
              <span className="delta-hint-label">Output diff</span>
              {deltaHint}
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

          {/* Python-Data submit: show DataFrame output only on wrong answers */}
          {submitResult && !submitResult.correct && topic === 'python-data' && submitResult.user_result && (
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
              {topic === 'sql' && submitResult.quality &&
                (submitResult.quality.efficiency_note ||
                 submitResult.quality.style_notes?.length > 0 ||
                 submitResult.quality.complexity_hint ||
                 submitResult.quality.alternative_solution) && (
                <div className="solution-analysis-card">
                  <button
                    className="solution-analysis-toggle"
                    onClick={() => setSolutionAnalysisOpen((v) => !v)}
                    aria-expanded={solutionAnalysisOpen}
                  >
                    <span>Writing notes</span>
                    <span className="solution-analysis-chevron">{solutionAnalysisOpen ? '▾' : '▸'}</span>
                  </button>
                  {solutionAnalysisOpen && (
                    <div className="solution-analysis-body">
                      <p className="writing-notes-prompt">Interviewers ask you to explain your approach. Make sure you can.</p>
                      {submitResult.quality.efficiency_note && (
                        <div className="quality-metric">
                          <span className={`quality-metric-label${submitResult.quality.efficiency_note.startsWith('Efficient') ? ' quality-metric-label-positive' : ''}`}>Efficiency</span>
                          <p className="quality-metric-note">{submitResult.quality.efficiency_note}</p>
                        </div>
                      )}
                      {submitResult.quality.style_notes?.length > 0 && (
                        <div className="quality-metric">
                          <span className="quality-metric-label">Style</span>
                          {submitResult.quality.style_notes.map((note, i) => (
                            <p key={i} className="quality-metric-note">{note}</p>
                          ))}
                        </div>
                      )}
                      {submitResult.quality.complexity_hint && (
                        <div className="quality-metric">
                          <span className="quality-metric-label">Complexity</span>
                          <p className="quality-metric-note">{submitResult.quality.complexity_hint}</p>
                        </div>
                      )}
                      {submitResult.quality.alternative_solution && (
                        <div className="quality-metric">
                          <span className="quality-metric-label">Alternative approach</span>
                          <button
                            className="btn btn-secondary workspace-inline-action"
                            onClick={() => setShowAltSolution((v) => !v)}
                          >
                            {showAltSolution ? 'Hide' : 'See another approach'}
                          </button>
                          {showAltSolution && (
                            <div className="quality-alt-solution">
                              <pre className="quality-alt-code">{submitResult.quality.alternative_solution.query}</pre>
                              <p className="quality-alt-explanation">{submitResult.quality.alternative_solution.explanation}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {!submitResult.correct && question.hints?.slice(0, hintsShown).map((hint, index) => (
                <div key={index} className="hint-card">
                  <strong>Hint {index + 1}:</strong> {hint}
                </div>
              ))}

              {!submitResult.correct && hintsShown < (question.hints?.length ?? 0) && (
                <button
                  className="btn btn-secondary workspace-inline-action"
                  onClick={() => setHintsShown((count) => count + 1)}
                >
                  Reveal Hint {hintsShown + 1}
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
