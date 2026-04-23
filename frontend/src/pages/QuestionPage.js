import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { format as formatSQL } from 'sql-formatter';
import api from '../api';
import CodeEditor from '../components/CodeEditor';
import ResultsTable from '../components/ResultsTable';
import SchemaViewer from '../components/SchemaViewer';
import TestCasePanel from '../components/TestCasePanel';
import PrintOutputPanel from '../components/PrintOutputPanel';
import VariablesPanel from '../components/VariablesPanel';
import MCQPanel from '../components/MCQPanel';
import ConceptPanel from '../components/ConceptPanel';
import Skeleton from '../components/Skeleton';
import { useCatalog } from '../catalogContext';
import { useTopic } from '../contexts/TopicContext';
import { useAuth } from '../contexts/AuthContext';
import UpgradeButton from '../components/UpgradeButton';
import { parseSqlError } from '../utils/sqlErrorParser';
import { renderDescription } from '../utils/renderDescription';
import { useToast } from '../App';
import { track } from '../analytics';

const HINT_STEP_LABELS = ['Conceptual hint', 'Approach hint', 'Structure hint', 'Final hint'];
const STREAK_MILESTONES = [3, 7, 14, 30, 60, 100];

const SQL_PLACEHOLDER = '-- Write your SQL query here\nSELECT ';
const PYTHON_PLACEHOLDER = '# Write your solution here\n';



export default function QuestionPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const { catalog, refresh } = useCatalog();
  const { topic, meta } = useTopic();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const { notify } = useToast();

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
  const draftKey = useMemo(() => `draft:${topic}:${id}`, [topic, id]);

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
  const [celebrateSolve, setCelebrateSolve] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [activeConcept, setActiveConcept] = useState(null);
  const [editorTall, setEditorTall] = useState(() => {
    try { return localStorage.getItem('editor-height-pref') === 'tall'; } catch { return false; }
  });
  const [draftSaveState, setDraftSaveState] = useState('idle');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [timerHidden, setTimerHidden] = useState(() => localStorage.getItem('timer-hidden') === '1');

  // Split pane
  const [leftPanelWidth, setLeftPanelWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('split-pane-width');
      if (saved) return Math.max(280, Math.min(600, parseInt(saved, 10)));
    } catch {}
    return 380;
  });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartXRef = useRef(0);
  const dragStartWidthRef = useRef(0);

  // Monaco: font-size persistence
  const [fontSize, setFontSize] = useState(() => {
    try { return Math.max(11, Math.min(24, parseInt(localStorage.getItem('editor-font-size') ?? '14', 10))); } catch { return 14; }
  });

  // Run history (sessionStorage, per question)
  const runHistoryKey = useMemo(() => `run-history:${topic}:${id}`, [topic, id]);
  const [runHistory, setRunHistory] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem(`run-history:${topic}:${id}`) ?? '[]'); } catch { return []; }
  });
  const [historyOpen, setHistoryOpen] = useState(false);
  const priorAttemptCountRef = useRef(0);
  const verdictRef = useRef(null);

  // Refs used by Monaco keyboard commands to avoid stale closures.
  // Updated inline on every render (before any early return that uses them).
  const handleRunRef = useRef(null);
  const handleSubmitRef = useRef(null);
  const runningRef = useRef(false);
  const submittingRef = useRef(false);
  const isLockedRef = useRef(false);
  const draftHydratedRef = useRef(false);
  const draftSaveTimerRef = useRef(null);
  const timerAccumRef = useRef(0);
  const timerSegmentStartRef = useRef(null);
  const timerIntervalRef = useRef(null);

  // Monaco instance refs (for schema autocomplete + format shortcut)
  const monacoRef = useRef(null);
  const editorRef = useRef(null);
  const completionDisposableRef = useRef(null);
  const questionRef = useRef(null);

  // MCQ state for PySpark
  const [selectedOption, setSelectedOption] = useState(null);
  const [schemaSheetOpen, setSchemaSheetOpen] = useState(false);

  function pauseTimer() {
    if (timerSegmentStartRef.current == null) return;
    timerAccumRef.current += Date.now() - timerSegmentStartRef.current;
    timerSegmentStartRef.current = null;
    setElapsedMs(timerAccumRef.current);
  }

  function resumeTimer() {
    if (!question || timerSegmentStartRef.current != null) return;
    timerSegmentStartRef.current = Date.now();
  }

  function getElapsedDurationMs() {
    const liveSegment = timerSegmentStartRef.current == null ? 0 : (Date.now() - timerSegmentStartRef.current);
    return Math.max(0, Math.round(timerAccumRef.current + liveSegment));
  }

  function formatDuration(ms) {
    if (!ms || ms <= 0) return null;
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
  }

  function getBookmarkKey() {
    return `bookmarks:${topic}`;
  }

  function readBookmarks() {
    try {
      const raw = localStorage.getItem(getBookmarkKey());
      const parsed = JSON.parse(raw ?? '[]');
      if (!Array.isArray(parsed)) return [];
      return parsed.filter((value) => Number.isInteger(value));
    } catch {
      return [];
    }
  }

  function writeBookmarks(ids) {
    try {
      localStorage.setItem(getBookmarkKey(), JSON.stringify(ids.slice(0, 20)));
      window.dispatchEvent(new CustomEvent('bookmarks-updated', { detail: { topic } }));
    } catch {}
  }

  useEffect(() => {
    setQuestion(null);
    setLoadError(null);
    draftHydratedRef.current = false;
    setDraftSaveState('idle');
    api
      .get(questionApiPath)
      .then((res) => {
        const q = res.data;
        setQuestion(q);
        if (!meta.hasMCQ) {
          const baseCode = meta.language === 'python' && q.starter_code ? q.starter_code : defaultCode;
          let nextCode = baseCode;
          try {
            const savedDraft = localStorage.getItem(draftKey);
            if (savedDraft && savedDraft.trim()) {
              nextCode = savedDraft;
              setDraftSaveState('saved');
            }
          } catch {}
          setCode(nextCode);
        }
        draftHydratedRef.current = true;
      })
      .catch((err) => setLoadError(err.response?.data?.detail ?? 'Failed to load question.'));
    api.get('/submissions', { params: { track: topic, question_id: id, limit: 20 } })
      .then((res) => setPastAttempts(res.data))
      .catch(() => {});
  }, [id, topic, questionApiPath, meta.language, meta.hasMCQ, defaultCode, draftKey]);

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
    draftHydratedRef.current = false;
    setDraftSaveState('idle');
    timerAccumRef.current = 0;
    timerSegmentStartRef.current = null;
    setElapsedMs(0);
    setBookmarked(false);
    setHistoryOpen(false);
    try {
      const saved = sessionStorage.getItem(`run-history:${topic}:${id}`);
      setRunHistory(saved ? JSON.parse(saved) : []);
    } catch { setRunHistory([]); }
  }, [id, meta.language, meta.hasMCQ]);

  useEffect(() => {
    const qid = Number(id);
    setBookmarked(readBookmarks().includes(qid));
  }, [id, topic]);

  useEffect(() => {
    if (!question) return undefined;
    timerAccumRef.current = 0;
    timerSegmentStartRef.current = document.hidden ? null : Date.now();
    setElapsedMs(0);

    const handleVisibility = () => {
      if (document.hidden) pauseTimer();
      else resumeTimer();
    };
    document.addEventListener('visibilitychange', handleVisibility);

    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    timerIntervalRef.current = setInterval(() => {
      setElapsedMs(getElapsedDurationMs());
    }, 1000);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
      pauseTimer();
    };
  }, [question]);

  useEffect(() => {
    if (meta.hasMCQ || !question || !draftHydratedRef.current) return undefined;
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
  }, [code, question, meta.hasMCQ, draftKey]);

  useEffect(() => () => {
    if (draftSaveTimerRef.current) clearTimeout(draftSaveTimerRef.current);
  }, []);

  // Keep questionRef current for Monaco completion provider
  useEffect(() => { questionRef.current = question; }, [question]);

  // Register/update SQL schema autocomplete when question or monaco instance changes
  useEffect(() => {
    if (!monacoRef.current || topic !== 'sql') return undefined;
    if (completionDisposableRef.current) {
      completionDisposableRef.current.dispose();
      completionDisposableRef.current = null;
    }
    const schema = question?.schema;
    if (!schema || Object.keys(schema).length === 0) return undefined;
    const disposable = monacoRef.current.languages.registerCompletionItemProvider('sql', {
      triggerCharacters: ['.', ' '],
      provideCompletionItems: (model, position) => {
        const currentSchema = questionRef.current?.schema;
        if (!currentSchema) return { suggestions: [] };
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
          startColumn: word.startColumn, endColumn: word.endColumn,
        };
        const lineBefore = model.getValueInRange({
          startLineNumber: position.lineNumber, startColumn: 1,
          endLineNumber: position.lineNumber, endColumn: position.column,
        });
        // After a dot: suggest columns for that table
        const dotMatch = lineBefore.match(/(\w+)\.(\w*)$/);
        if (dotMatch) {
          const tbl = dotMatch[1].toLowerCase();
          const cols = currentSchema[tbl] ?? currentSchema[Object.keys(currentSchema).find((k) => k.toLowerCase() === tbl)];
          if (cols) {
            return {
              suggestions: cols.map((col) => ({
                label: col, kind: monacoRef.current.languages.CompletionItemKind.Field,
                insertText: col, range, detail: `Column of ${tbl}`,
              })),
            };
          }
        }
        // Default: suggest tables + all columns
        const suggestions = [];
        Object.entries(currentSchema).forEach(([tbl, cols]) => {
          suggestions.push({
            label: tbl, kind: monacoRef.current.languages.CompletionItemKind.Struct,
            insertText: tbl, range, detail: `Table (${cols.length} columns)`,
          });
          cols.forEach((col) => suggestions.push({
            label: col, kind: monacoRef.current.languages.CompletionItemKind.Field,
            insertText: col, range, detail: `Column of ${tbl}`,
          }));
        });
        return { suggestions };
      },
    });
    completionDisposableRef.current = disposable;
    return () => {
      if (completionDisposableRef.current) {
        completionDisposableRef.current.dispose();
        completionDisposableRef.current = null;
      }
    };
  }, [question?.schema, topic]); // eslint-disable-line react-hooks/exhaustive-deps

  // Split pane drag handlers
  useEffect(() => {
    if (!isDragging) return undefined;
    function onMouseMove(e) {
      const delta = e.clientX - dragStartXRef.current;
      const newWidth = Math.max(260, Math.min(620, dragStartWidthRef.current + delta));
      setLeftPanelWidth(newWidth);
      try { localStorage.setItem('split-pane-width', String(newWidth)); } catch {}
    }
    function onMouseUp() {
      setIsDragging(false);
    }
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [isDragging]);

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

  function formatExecutionError(err, fallback) {
    const raw = err.response?.data?.error ?? err.response?.data?.detail ?? fallback;
    if (meta.language === 'sql') {
      return parseSqlError(raw) ?? fallback;
    }
    return raw;
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
    // Push to run history
    if (code.trim()) {
      setRunHistory((prev) => {
        const deduped = [code, ...prev.filter((h) => h !== code)].slice(0, 20);
        try { sessionStorage.setItem(runHistoryKey, JSON.stringify(deduped)); } catch {}
        return deduped;
      });
    }
    try {
      const payload = meta.language === 'python'
        ? { code, question_id: Number(id) }
        : { query: code, question_id: Number(id) };
      const res = await api.post(runApiPath, payload);
      setRunResult(res.data);
    } catch (err) {
      setRunError(formatExecutionError(err, 'Execution failed.'));
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
        payload = { selected_option: selectedOption, question_id: Number(id), duration_ms: getElapsedDurationMs() };
      } else if (meta.language === 'python') {
        payload = { code, question_id: Number(id), duration_ms: getElapsedDurationMs() };
      } else {
        payload = { query: code, question_id: Number(id), duration_ms: getElapsedDurationMs() };
      }
      const res = await api.post(submitApiPath, payload);
      setSubmitResult(res.data);
      track('question_submitted', { track: topic, question_id: Number(id), difficulty: question?.difficulty, correct: res.data.correct });
      if (res.data.correct) {
        track('question_solved', { track: topic, question_id: Number(id), difficulty: question?.difficulty, first_try: priorAttemptCountRef.current === 0 });
        const lockedBefore = catalog?.groups?.reduce(
          (sum, group) => sum + group.questions.filter((entry) => entry.state === 'locked').length,
          0
        ) ?? 0;
        const previousStreakDays = user?.streak_days ?? 0;
        const refreshedCatalog = await refresh();
        const lockedAfter = refreshedCatalog?.groups?.reduce(
          (sum, group) => sum + group.questions.filter((entry) => entry.state === 'locked').length,
          0
        ) ?? lockedBefore;
        const unlockedNow = Math.max(0, lockedBefore - lockedAfter);
        if (unlockedNow > 0) {
          notify({
            tone: 'success',
            title: `${unlockedNow} new question${unlockedNow !== 1 ? 's' : ''} unlocked`,
            message: 'You just opened the next tier in this track.',
          });
        }

        const prior = priorAttemptCountRef.current;
        if (prior === 0) {
          setSubmissionInsight('First-attempt solve — the system logged your approach.');
          setCelebrateSolve(true);
          notify({
            tone: 'success',
            title: 'First-try solve',
            message: 'Clean execution under pressure. Keep that tempo.',
          });
        }
        else if (prior >= 3) setSubmissionInsight('Took a few tries — that\'s the shape of real learning.');
        // Auto-open writing notes on first-attempt correct solve
        if (prior === 0) setSolutionAnalysisOpen(true);

        const refreshedUser = await refreshUser();
        const nextStreakDays = refreshedUser?.streak_days ?? previousStreakDays;
        if (nextStreakDays > previousStreakDays) {
          if (STREAK_MILESTONES.includes(nextStreakDays)) {
            notify({
              tone: 'success',
              title: `${nextStreakDays}-day streak milestone`,
              message: 'Consistency compounds. Keep your streak alive today.',
              durationMs: 4200,
            });
          } else if (nextStreakDays === 1) {
            notify({
              tone: 'info',
              title: 'Streak started',
              message: 'You are on the board. Solve tomorrow to continue it.',
            });
          }
        }
      }
      api.get('/submissions', { params: { track: topic, question_id: id, limit: 20 } })
        .then((r) => setPastAttempts(r.data))
        .catch(() => {});
    } catch (err) {
      setSubmitError(formatExecutionError(err, 'Submission failed.'));
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
    monacoRef.current = monaco;
    editorRef.current = editor;

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
    // Cmd/Ctrl + Shift + F → Format SQL
    if (meta.language === 'sql') {
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
        const current = editor.getValue();
        try {
          const formatted = formatSQL(current, { language: 'duckdb', tabWidth: 2, keywordCase: 'upper' });
          editor.setValue(formatted);
        } catch {}
      });
    }
    // Cmd/Ctrl + = / + → increase font size
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Equal, () => {
      setFontSize((prev) => {
        const next = Math.min(24, prev + 1);
        try { localStorage.setItem('editor-font-size', String(next)); } catch {}
        return next;
      });
    });
    // Cmd/Ctrl + - → decrease font size
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Minus, () => {
      setFontSize((prev) => {
        const next = Math.max(11, prev - 1);
        try { localStorage.setItem('editor-font-size', String(next)); } catch {}
        return next;
      });
    });
  }

  function toggleEditorHeight() {
    setEditorTall((prev) => {
      const next = !prev;
      try { localStorage.setItem('editor-height-pref', next ? 'tall' : 'normal'); } catch {}
      return next;
    });
  }

  function handleDividerMouseDown(e) {
    e.preventDefault();
    dragStartXRef.current = e.clientX;
    dragStartWidthRef.current = leftPanelWidth;
    setIsDragging(true);
  }

  function handleDividerReset() {
    setLeftPanelWidth(380);
    try { localStorage.removeItem('split-pane-width'); } catch {}
  }

  function adjustFontSize(delta) {
    setFontSize((prev) => {
      const next = Math.max(11, Math.min(24, prev + delta));
      try { localStorage.setItem('editor-font-size', String(next)); } catch {}
      return next;
    });
  }

  function clearDraft() {
    if (meta.hasMCQ) return;
    const resetCode = meta.language === 'python' && question?.starter_code ? question.starter_code : defaultCode;
    try {
      localStorage.removeItem(draftKey);
    } catch {}
    setCode(resetCode);
    setDraftSaveState('idle');
  }

  function toggleBookmark() {
    const qid = Number(id);
    const current = readBookmarks();
    let next;
    if (current.includes(qid)) {
      next = current.filter((value) => value !== qid);
      setBookmarked(false);
    } else {
      next = [qid, ...current.filter((value) => value !== qid)].slice(0, 20);
      setBookmarked(true);
    }
    writeBookmarks(next);
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

  useEffect(() => {
    if (!celebrateSolve) return undefined;
    const timer = window.setTimeout(() => setCelebrateSolve(false), 1600);
    return () => window.clearTimeout(timer);
  }, [celebrateSolve]);

  const recommendedQuestions = useMemo(() => {
    if (!submitResult?.correct || !question?.concepts?.length || !catalog?.groups) return [];
    const conceptSet = new Set(question.concepts);
    const matches = [];
    for (const group of catalog.groups) {
      for (const candidate of group.questions ?? []) {
        if (Number(candidate.id) === Number(id)) continue;
        if (candidate.state === 'solved') continue;
        const overlap = (candidate.concepts ?? []).some((concept) => conceptSet.has(concept));
        if (!overlap) continue;
        matches.push(candidate);
      }
    }
    const unique = [];
    const seen = new Set();
    for (const match of matches) {
      if (seen.has(match.id)) continue;
      seen.add(match.id);
      unique.push(match);
    }
    unique.sort((a, b) => {
      if (a.state === b.state) return (a.order ?? 999) - (b.order ?? 999);
      if (a.state === 'unlocked') return -1;
      if (b.state === 'unlocked') return 1;
      return 0;
    });
    return unique.slice(0, 2);
  }, [submitResult, question, catalog, id]);

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
  const timerLabel = formatDuration(elapsedMs) ?? '0:00';

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
      <Helmet>
        <title>{question ? `${question.title} — ${meta.label} — datanest` : `${meta.label} Practice — datanest`}</title>
        {question && <meta name="description" content={`${question.title}: a ${question.difficulty} ${meta.label} interview question on datanest.`} />}
        <meta name="robots" content="noindex" />
      </Helmet>
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
      <div
        className={`question-page-inner${isDragging ? ' split-dragging' : ''}`}
        style={{ gridTemplateColumns: `${leftPanelWidth}px 6px minmax(0, 1fr)`, columnGap: '0.6rem' }}
      >
        <aside className="left-panel">
          <div className="card prompt-card prompt-card-main">
            <div className="section-heading">
              <div>
                <div className="question-title-row">
                  <h2>{question.title}</h2>
                  <div className="question-title-actions">
                    <button
                      className={`question-bookmark-btn${bookmarked ? ' question-bookmark-btn-active' : ''}`}
                      onClick={toggleBookmark}
                      aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark question'}
                      title={bookmarked ? 'Remove bookmark' : 'Bookmark question'}
                    >
                      {bookmarked ? '★ Bookmarked' : '☆ Bookmark'}
                    </button>
                    <span className={`badge badge-${question.difficulty}`}>{question.difficulty}</span>
                  </div>
                </div>
                {workspaceStatus && (
                  <p className="question-status-line">{workspaceStatus}</p>
                )}
              </div>
            </div>

            {question.concepts?.length > 0 && (
              <div className="concept-tags concept-tags-inline">
                {question.concepts.map((concept) => (
                  <button key={concept} className="tag-concept tag-concept-btn" onClick={() => setActiveConcept(concept)}>{concept}</button>
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

            <p className="description-text">{renderDescription(question.description)}</p>

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

        {/* Draggable split divider */}
        <div
          className={`split-divider${isDragging ? ' split-divider--dragging' : ''}`}
          onMouseDown={handleDividerMouseDown}
          onDoubleClick={handleDividerReset}
          title="Drag to resize · double-click to reset"
          role="separator"
          aria-label="Resize panels"
        />

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
                    type="button"
                    className={`editor-topbar-timer${timerHidden ? ' editor-topbar-timer--hidden' : ''}`}
                    title={timerHidden ? 'Show timer' : 'Hide timer'}
                    aria-label={timerHidden ? 'Show timer' : 'Hide timer'}
                    onClick={() => setTimerHidden(v => { const next = !v; localStorage.setItem('timer-hidden', next ? '1' : '0'); return next; })}
                  >{timerHidden ? '--:--' : timerLabel}</button>
                  <span className="editor-topbar-note">
                    {draftSaveState === 'saving' ? 'Saving draft…' : draftSaveState === 'saved' ? 'Draft saved' : editorNote}
                  </span>
                  {runHistory.length > 0 && (
                    <div className="editor-history-wrap">
                      <button
                        className="editor-expand-btn"
                        onClick={() => setHistoryOpen((v) => !v)}
                        title="Run history"
                        aria-label="Run history"
                        aria-expanded={historyOpen}
                      >
                        ↑
                      </button>
                      {historyOpen && (
                        <div className="history-popover" role="listbox" aria-label="Run history">
                          {runHistory.map((entry, i) => (
                            <button
                              key={i}
                              className="history-item"
                              role="option"
                              onClick={() => { setCode(entry); setHistoryOpen(false); }}
                              title={entry}
                            >
                              {entry.slice(0, 60).replace(/\n/g, ' ')}{entry.length > 60 ? '…' : ''}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="editor-font-controls">
                    <button className="editor-expand-btn" onClick={() => adjustFontSize(-1)} title="Decrease font size" aria-label="Decrease font size">A−</button>
                    <button className="editor-expand-btn" onClick={() => adjustFontSize(+1)} title="Increase font size" aria-label="Increase font size">A+</button>
                  </div>
                  <button
                    className="editor-expand-btn"
                    onClick={() => setShortcutHelpOpen((open) => !open)}
                    title="Keyboard shortcuts (?)"
                    aria-label="Keyboard shortcuts"
                    aria-expanded={shortcutHelpOpen}
                  >
                    ?
                  </button>
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
                  {meta.language === 'sql' && (
                    <div className="workspace-shortcut-row">
                      <span>Format SQL</span>
                      <kbd className="shortcut-kbd">⌘⇧F</kbd>
                    </div>
                  )}
                  <div className="workspace-shortcut-row">
                    <span>Font size</span>
                    <span className="shortcut-pair">
                      <kbd className="shortcut-kbd">⌘+</kbd>
                      <kbd className="shortcut-kbd">⌘−</kbd>
                    </span>
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
                fontSize={fontSize}
                onMount={handleEditorMount}
                ariaLabel={`${meta.label} challenge editor`}
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
                <Skeleton className="skeleton-line" width="2.5rem" height="11px" />
              </div>
              <div className="results-skeleton-body">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton
                    key={i}
                    className="results-skeleton-row"
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
              <Skeleton className="skeleton-line" width="5rem" height="13px" />
              <Skeleton className="skeleton-line" width="70%" height="11px" />
              <Skeleton className="skeleton-line" width="50%" height="11px" style={{ animationDelay: '80ms' }} />
            </div>
          )}

          {submitting && !submitError && topic === 'sql' && (
            <div className="solution-analysis-skeleton">
              <Skeleton className="skeleton-line" width="9rem" height="12px" />
              <Skeleton className="skeleton-line" width="75%" height="10px" />
              <Skeleton className="skeleton-line" width="84%" height="10px" style={{ animationDelay: '70ms' }} />
            </div>
          )}

          {submitResult && (
            <div className={`submit-outcome${celebrateSolve ? ' submit-outcome-celebrate' : ''}`} ref={verdictRef}>
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
                <ResultsTable
                  columns={submitResult.user_result.columns}
                  rows={submitResult.user_result.rows}
                  diffMode
                  expectedColumns={submitResult.expected_result.columns}
                  expectedRows={submitResult.expected_result.rows}
                />
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
                  diffMode
                  expectedColumns={submitResult.expected_result.columns ?? []}
                  expectedRows={submitResult.expected_result.rows ?? []}
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
                      {attempt.duration_ms ? (
                        <span className="past-attempt-duration">{formatDuration(attempt.duration_ms)}</span>
                      ) : null}
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
              {recommendedQuestions.length > 0 && (
                <div className="recommend-card">
                  <div className="recommend-title">Similar questions to drill next</div>
                  <div className="recommend-list">
                    {recommendedQuestions.map((candidate) => (
                      <Link key={candidate.id} className="recommend-link" to={`/practice/${topic}/questions/${candidate.id}`}>
                        <span className="recommend-link-title">{candidate.title}</span>
                        <span className="recommend-link-meta">{candidate.difficulty} · {candidate.state === 'locked' ? 'locked' : 'available'}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

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

              {!submitResult.correct && question.hints?.length > 0 && (
                <div className="hint-stepper">
                  <div className="hint-stepper-header">
                    <span className="hint-stepper-title">Hints</span>
                    <span className="hint-stepper-progress">{hintsShown}/{question.hints.length} revealed</span>
                  </div>
                  {question.hints.slice(0, hintsShown).map((hint, index) => (
                    <div key={index} className="hint-step hint-step--revealed">
                      <div className="hint-step-meta">
                        <span className="hint-step-num">{index + 1}</span>
                        <span className="hint-step-label">{HINT_STEP_LABELS[index] ?? `Hint ${index + 1}`}</span>
                      </div>
                      <p className="hint-step-content">{hint}</p>
                    </div>
                  ))}
                  {hintsShown < question.hints.length && (
                    <button
                      className="hint-reveal-btn"
                      onClick={() => setHintsShown((c) => c + 1)}
                    >
                      <span className="hint-reveal-arrow">→</span>
                      Reveal {HINT_STEP_LABELS[hintsShown] ?? `Hint ${hintsShown + 1}`}
                    </button>
                  )}
                </div>
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

      {activeConcept && (
        <ConceptPanel concept={activeConcept} onClose={() => setActiveConcept(null)} />
      )}
    </main>
  );
}
