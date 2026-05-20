import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api';
import CodeEditor from '../components/CodeEditor';
import MCQPanel from '../components/MCQPanel';
import ResultsTable from '../components/ResultsTable';
import TestCasePanel from '../components/TestCasePanel';
import PrintOutputPanel from '../components/PrintOutputPanel';
import VariablesPanel from '../components/VariablesPanel';
import SchemaViewer from '../components/SchemaViewer';
import Skeleton from '../components/Skeleton';
import { TRACK_META } from '../contexts/TopicContext';
import { TRACK_LABELS } from '../trackRegistry';
import { track as trackEvent } from '../analytics';
import { renderDescription } from '../utils/renderDescription';
import { getMockSessionDescriptor } from '../mockModeConfig';

function formatTime(s) {
  if (s == null || s < 0) return '00:00';
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function timerClass(s) {
  if (s < 180) return 'mock-timer mock-timer--danger';
  if (s < 600) return 'mock-timer mock-timer--warning';
  return 'mock-timer';
}

function conceptSlug(concept) {
  return String(concept || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

const DEFAULT_CODE = {
  sql: '-- Write your SQL query here\n',
  python: '# Write your Python solution here\n\ndef solution():\n    pass\n',
  'python-data': '# Write your pandas/numpy code here\n# result should be assigned to a variable named `result`\n',
  pyspark: '',
};

export default function MockSession() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isElite = user?.plan === 'elite' || user?.plan === 'lifetime_elite';
  const isPro = user?.plan === 'pro' || user?.plan === 'lifetime_pro';
  const isProOrElite = isPro || isElite;

  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [activeQ, setActiveQ] = useState(0);
  const [codes, setCodes] = useState({});
  const [results, setResults] = useState({});       // {qId: verdict}
  const [solved, setSolved] = useState({});         // {qId: bool}
  const [flagged, setFlagged] = useState({});       // {qId: bool}
  const [mcqSelections, setMcqSelections] = useState({}); // {qId: int}
  const [submitting, setSubmitting] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState({});
  const [remainingS, setRemainingS] = useState(null);
  const [status, setStatus] = useState('loading');  // 'loading'|'active'|'finishing'|'completed'
  const [summary, setSummary] = useState(null);
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  const [showDiscardPrompt, setShowDiscardPrompt] = useState(false);
  const [questionView, setQuestionView] = useState('description');  // 'description'|'schema'
  const [mobileQuestionOpen, setMobileQuestionOpen] = useState(false);
  const [expandedSolutions, setExpandedSolutions] = useState({}); // {qId: bool}
  const [loadError, setLoadError] = useState(null);
  const [insights, setInsights] = useState(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [submitted, setSubmitted] = useState({});   // {qId: bool} — locked after any real submit; never cleared by Run
  const [submitNetworkError, setSubmitNetworkError] = useState(null);

  const [showFollowUpBanner, setShowFollowUpBanner] = useState(false);
  const [focusFallback, setFocusFallback] = useState(false);
  const [fontSize, setFontSize] = useState(() => {
    try { return parseInt(localStorage.getItem('mock-editor-font-size') || '14', 10); } catch { return 14; }
  });
  const [editorTall, setEditorTall] = useState(false);
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);

  const editorHeight = editorTall ? '560px' : '340px';

  const finishCalled = useRef(false);
  const bannerTimerRef = useRef(null);
  const handleRunRef = useRef(null);
  const handleSubmitRef = useRef(null);
  const runningRef = useRef(false);
  const submittingRef = useRef(false);

  const handleFinish = useCallback(async () => {
    if (finishCalled.current) return;
    finishCalled.current = true;
    setStatus('finishing');
    try {
      const r = await api.post(`/mock/${id}/finish`);
      setSummary(r.data);
      trackEvent('mock_completed', { session_id: id, score: r.data.score, total: r.data.total, track: r.data.track });
      setStatus('completed');
    } catch (err) {
      console.error('Failed to finish session', err);
      setStatus('completed');
    }
  }, [id]);

  function initFromData(data) {
    setSession({
      session_id: data.session_id,
      mode: data.mode,
      track: data.track,
      difficulty: data.difficulty,
      started_at: data.started_at,
      time_limit_s: data.time_limit_s,
      status: data.status,
    });
    setQuestions(data.questions || []);
    if (data.focus_fallback) setFocusFallback(true);

    // Restore codes, solved, and submitted state from server
    const initialCodes = {};
    const initialSolved = {};
    const initialSubmitted = {};
    (data.questions || []).forEach(q => {
      // Debug questions pre-fill the editor with starter_code unless the user already submitted
      initialCodes[q.id] = q.final_code || (q.type === 'debug' ? (q.starter_code || '') : null) || DEFAULT_CODE[q.track] || '';
      initialSolved[q.id] = q.is_solved || false;
      initialSubmitted[q.id] = q.submitted_at != null;
    });
    setCodes(initialCodes);
    setSolved(initialSolved);
    setSubmitted(initialSubmitted);

    if (data.status === 'completed') {
      // Already finished — fetch summary
      api.post(`/mock/${id}/finish`)
        .then(r => { setSummary(r.data); setStatus('completed'); })
        .catch(() => setStatus('completed'));
    } else {
      // Compute remaining time from server's started_at
      const elapsed = Math.floor((Date.now() - new Date(data.started_at)) / 1000);
      const remaining = Math.max(0, data.time_limit_s - elapsed);
      setRemainingS(remaining);
      setStatus('active');
    }
  }

  useEffect(() => {
    const sessionData = location.state?.sessionData;
    if (sessionData) {
      initFromData(sessionData);
    } else {
      api.get(`/mock/${id}`)
        .then(r => initFromData(r.data))
        .catch(() => setLoadError('Failed to load session.'));
    }

    if (isProOrElite) {
      api.get('/dashboard/insights')
        .then(r => setInsights(r.data))
        .catch(() => setInsights(null));
    }
  }, [id, isElite]); // eslint-disable-line react-hooks/exhaustive-deps

  // Countdown timer
  useEffect(() => {
    if (remainingS === null || status !== 'active') return;
    if (remainingS <= 0) {
      handleFinish();
      return;
    }
    const t = setInterval(() => {
      setRemainingS(s => {
        if (s <= 1) {
          clearInterval(t);
          handleFinish();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [remainingS === null, status]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentQuestion = questions[activeQ] || null;
  const sessionTrack = session?.track || currentQuestion?.track || 'sql';
  const sessionDescriptor = getMockSessionDescriptor(session?.mode, sessionTrack);

  // Follow-up banner: show for 3s when user navigates to an is_follow_up question
  useEffect(() => {
    if (!currentQuestion?.is_follow_up) {
      setShowFollowUpBanner(false);
      return;
    }
    setShowFollowUpBanner(true);
    if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
    bannerTimerRef.current = setTimeout(() => setShowFollowUpBanner(false), 3000);
    return () => {
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
    };
  }, [currentQuestion?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Browser tab title
  useEffect(() => {
    if (status === 'active' && remainingS != null) {
      document.title = `${formatTime(remainingS)} — Mock Interview | datathink`;
    } else if (status === 'completed') {
      document.title = 'Mock Interview Summary | datathink';
    }
    return () => { document.title = 'datathink'; };
  }, [remainingS, status]);

  function getCode(q) {
    if (!q) return '';
    return codes[q.id] !== undefined ? codes[q.id] : (DEFAULT_CODE[q.track] || '');
  }

  function setCode(qId, value) {
    setCodes(prev => ({ ...prev, [qId]: value }));
  }

  async function handleRun() {
    if (!currentQuestion || running) return;
    const q = currentQuestion;
    const track = q.track;
    const meta = TRACK_META[track];
    if (!meta || !meta.hasRunCode) return;

    setRunning(true);
    setRunResults(prev => ({ ...prev, [q.id]: null }));
    try {
      const endpoint = track === 'sql'
        ? '/run-query'
        : `${meta.apiPrefix}/run-code`;
      const payload = track === 'sql'
        ? { query: getCode(q), question_id: q.id }
        : { code: getCode(q), question_id: q.id };
      const r = await api.post(endpoint, payload);
      setRunResults(prev => ({ ...prev, [q.id]: r.data }));
    } catch (err) {
      const errMsg = err?.response?.data?.error || err?.response?.data?.detail || 'Run failed';
      setRunResults(prev => ({ ...prev, [q.id]: { error: errMsg } }));
    } finally {
      setRunning(false);
    }
  }

  async function handleSubmit() {
    if (!currentQuestion || submitting || submitted[currentQuestion.id]) return;
    const q = currentQuestion;

    setSubmitting(true);
    setSubmitNetworkError(null);
    try {
      const payload = {
        question_id: q.id,
        track: q.track,
        time_spent_s: null,
      };
      if (q.track === 'pyspark') {
        payload.selected_option = mcqSelections[q.id] !== undefined ? mcqSelections[q.id] : null;
      } else {
        payload.code = getCode(q);
      }
      const r = await api.post(`/mock/${id}/submit`, payload);
      // Lock the question — no feedback shown, outcome reflected only in button state
      setSubmitted(prev => ({ ...prev, [q.id]: true }));
      if (r.data.correct) {
        setSolved(prev => ({ ...prev, [q.id]: true }));
        // If a follow-up was injected, re-fetch the session to get the updated question list
        if (r.data.follow_up_injected) {
          try {
            const sessionResp = await api.get(`/mock/${id}`);
            const updatedQuestions = sessionResp.data.questions || [];
            setQuestions(updatedQuestions);
            // Init codes for any newly injected questions
            setCodes(prev => {
              const next = { ...prev };
              updatedQuestions.forEach(uq => {
                if (next[uq.id] === undefined) {
                  next[uq.id] = uq.final_code || (uq.type === 'debug' ? (uq.starter_code || '') : null) || DEFAULT_CODE[uq.track] || '';
                }
              });
              return next;
            });
          } catch (_) { /* session state is still correct, follow-up is just missing */ }
        }
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        // Already submitted on the server — sync the UI to match
        setSubmitted(prev => ({ ...prev, [q.id]: true }));
      } else if (!status || status >= 500) {
        // Genuine network/server failure — don't lock; let the user retry
        setSubmitNetworkError('Submission failed — check your connection and try again.');
      }
      // 422 (blank input caught by UI guard) and other 4xx: no lock, user can retry
    } finally {
      setSubmitting(false);
    }
  }

  function handleExitConfirm() {
    setShowExitConfirm(false);
    handleFinish().then(() => navigate('/mock'));
  }

  // Early-exit discard helpers
  const elapsedS = session ? (session.time_limit_s - (remainingS ?? session.time_limit_s)) : 0;
  const hasNoActivity = Object.keys(results).length === 0 && Object.keys(runResults).length === 0;
  const isEarlyExit = status === 'active' && elapsedS < 60 && hasNoActivity;

  function handleExitClick() {
    if (isEarlyExit) setShowDiscardPrompt(true);
    else setShowExitConfirm(true);
  }

  async function handleDiscard() {
    try { await api.delete(`/mock/${id}`); } catch (_) {}
    navigate('/mock');
  }

  function toggleFlag(qId) {
    setFlagged(prev => ({ ...prev, [qId]: !prev[qId] }));
  }

  function goToFirstIncomplete() {
    setShowExitConfirm(false);
    const firstFlagged = questions.findIndex(q => flagged[q.id] && !solved[q.id]);
    const firstUnsolved = questions.findIndex(q => !solved[q.id]);
    const target = firstFlagged !== -1 ? firstFlagged : firstUnsolved;
    if (target !== -1) setActiveQ(target);
  }

  // Keep shortcut refs current on every render (safe to assign outside useEffect)
  handleRunRef.current = handleRun;
  handleSubmitRef.current = handleSubmit;
  runningRef.current = running;
  submittingRef.current = submitting;

  function adjustFontSize(delta) {
    setFontSize(prev => {
      const next = Math.min(24, Math.max(11, prev + delta));
      try { localStorage.setItem('mock-editor-font-size', String(next)); } catch {}
      return next;
    });
  }

  function handleEditorMount(editor, monaco) {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      if (!runningRef.current && !submittingRef.current) handleRunRef.current?.();
    });
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter,
      () => { if (!submittingRef.current) handleSubmitRef.current?.(); }
    );
  }

  // ── Loading / error states ─────────────────────────────────────────────────
  if (loadError) {
    return (
      <div className="mock-shell" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--danger)' }}>{loadError}</p>
        <Link to="/mock" className="btn btn-secondary" style={{ marginTop: '1rem' }}>Back to Mock</Link>
      </div>
    );
  }

  if (status === 'loading') {
    return <div className="mock-shell" style={{ alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: 'var(--text-secondary)' }}>Loading session…</p>
    </div>;
  }

  // ── Summary view ───────────────────────────────────────────────────────────
  if (status === 'completed' || status === 'finishing') {
    const sum = summary;
    const qs = sum?.questions || questions;
    const solvedCount = sum?.solved_count ?? Object.values(solved).filter(Boolean).length;
    const totalCount = sum?.total_count ?? questions.length;
    const sessionAccuracy = totalCount > 0 ? (solvedCount / totalCount) : 0;
    const timeUsedS = sum?.time_used_s;
    const timeLimitS = sum?.time_limit_s ?? session?.time_limit_s;
    const comparisonTrack = (sum?.track || session?.track) === 'mixed'
      ? (qs[0]?.track || 'sql')
      : (sum?.track || session?.track || 'sql');
    const baselineAccuracy = isProOrElite ? insights?.per_track?.[comparisonTrack]?.accuracy_pct : undefined;

    const conceptStats = {};
    qs.forEach((question) => {
      const questionTrack = question.track || comparisonTrack;
      const keySolved = question.is_solved ?? solved[question.id];
      (question.concepts || []).forEach((concept) => {
        const key = `${questionTrack}::${concept}`;
        if (!conceptStats[key]) {
          conceptStats[key] = {
            concept,
            track: questionTrack,
            attempts: 0,
            correct: 0,
          };
        }
        conceptStats[key].attempts += 1;
        if (keySolved) conceptStats[key].correct += 1;
      });
    });

    const conceptRows = Object.values(conceptStats)
      .map((row) => ({
        ...row,
        accuracy: row.attempts > 0 ? row.correct / row.attempts : 0,
      }))
      .sort((a, b) => (a.accuracy - b.accuracy) || (b.attempts - a.attempts) || a.concept.localeCompare(b.concept));

    // For mixed sessions: pick the track with the most weak concepts, so the
    // drill link targets the most actionable single track rather than whichever
    // track happened to appear first in the question list.
    const sessionTrack = sum?.track || session?.track || 'sql';
    const summaryDescriptor = getMockSessionDescriptor(sum?.mode || session?.mode, sessionTrack);
    let drillTrack;
    if (sessionTrack === 'mixed') {
      const weakByTrack = {};
      conceptRows.forEach((row) => {
        if (row.attempts > 0 && row.accuracy < 1) {
          weakByTrack[row.track] = (weakByTrack[row.track] ?? 0) + 1;
        }
      });
      const bestEntry = Object.entries(weakByTrack).sort((a, b) => b[1] - a[1])[0];
      drillTrack = bestEntry ? bestEntry[0] : (conceptRows[0]?.track || 'sql');
    } else {
      drillTrack = sessionTrack;
    }
    const drillConcepts = conceptRows
      .filter((row) => row.track === drillTrack && row.attempts > 0 && row.accuracy < 1)
      .slice(0, 2)
      .map((row) => conceptSlug(row.concept))
      .filter(Boolean);
    const recommendedDrillDifficulty = (sum?.difficulty || session?.difficulty || 'easy') === 'mixed'
      ? 'medium'
      : (sum?.difficulty || session?.difficulty || 'easy');
    const drillPreset = {
      mode: 'custom',
      track: drillTrack,
      difficulty: recommendedDrillDifficulty,
      numQuestions: 2,
      timeMinutes: 30,
      note: summaryDescriptor.isBenchmark
        ? 'Follow up on this benchmark with a short targeted drill while the weak spots are still fresh.'
        : 'Stay in drill mode and keep pressure on the same weak area with a short focused follow-up.',
    };

    let comparisonCopy = null;
    if (typeof baselineAccuracy === 'number') {
      const delta = Math.round((sessionAccuracy - baselineAccuracy) * 100);
      if (delta > 0) comparisonCopy = `${delta}% above your historical accuracy`;
      else if (delta < 0) comparisonCopy = `${Math.abs(delta)}% below your historical accuracy`;
      else comparisonCopy = 'on par with your historical accuracy';
    }

    function shareText() {
      const diff = sum?.difficulty || session?.difficulty || '';
      const trk = TRACK_LABELS[sum?.track || session?.track] || '';
      const diffLabel = diff ? diff.charAt(0).toUpperCase() + diff.slice(1) : '';
      const pct = totalCount > 0 ? Math.round((solvedCount / totalCount) * 100) : 0;
      const modeLabel = summaryDescriptor.isBenchmark ? 'benchmark' : 'drill';

      const lines = [
        `${trk} ${modeLabel} · ${diffLabel} · ${solvedCount}/${totalCount} (${pct}%)`,
      ];

      if (typeof baselineAccuracy === 'number') {
        const delta = Math.round((sessionAccuracy - baselineAccuracy) * 100);
        if (delta > 0) lines.push(`${delta}% above my avg accuracy`);
        else if (delta < 0) lines.push(`${Math.abs(delta)}% below my avg accuracy`);
        else lines.push('on par with my avg accuracy');
      }

      const weakConcepts = conceptRows
        .filter((r) => r.attempts > 0 && r.accuracy < 1)
        .slice(0, 2)
        .map((r) => r.concept);
      if (weakConcepts.length > 0) lines.push(`Weak spots: ${weakConcepts.join(', ')}`);

      lines.push('datathink.co');
      return lines.join('\n');
    }

    async function handleShare() {
      const text = shareText();
      if (navigator.share) {
        try {
          await navigator.share({ text });
          return;
        } catch (e) {
          if (e.name === 'AbortError') return;
        }
      }
      navigator.clipboard?.writeText(text).catch(() => {});
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    }

    return (
      <div className="mock-shell">
        <header className="mock-topbar">
          <Link to="/mock" className="btn btn-secondary btn-compact">← Back to Mock</Link>
          <span className="mock-topbar-title">{summaryDescriptor.isBenchmark ? 'Benchmark summary' : 'Drill summary'}</span>
          <span />
        </header>
        <div className="mock-summary-scroll">
          <div className="mock-summary-card">
            <div className="mock-session-summary-intro">
              <span className={`mock-session-summary-badge${summaryDescriptor.isBenchmark ? ' mock-session-summary-badge--benchmark' : ''}`}>
                {summaryDescriptor.modeLabel}
              </span>
              <div className="mock-session-summary-title">{summaryDescriptor.title}</div>
              {summaryDescriptor.summaryLine && (
                <div className="mock-session-summary-copy">{summaryDescriptor.summaryLine}</div>
              )}
            </div>
            <div className="mock-summary-score" style={{
              color: solvedCount === 0 ? 'var(--danger)' : solvedCount > totalCount / 2 ? 'var(--success)' : 'var(--text-strong)',
            }}>
              {status === 'finishing'
                ? 'Finishing…'
                : comparisonCopy
                  ? `${solvedCount}/${totalCount} correct, ${comparisonCopy}`
                  : `${solvedCount}/${totalCount} questions solved`}
            </div>
            {timeUsedS != null && (
              <div className="mock-summary-time">
                Used {formatTime(timeUsedS)} of {formatTime(timeLimitS)}
              </div>
            )}
            {/* Elite coaching debrief — shown before per-question detail */}
            {sum?.debrief && (
              <>
                <hr className="mock-summary-divider" />
                <div className="mock-debrief">
                  <div className="mock-debrief-header">
                    <span className="mock-debrief-badge">Session debrief</span>
                  </div>
                  <p className="mock-debrief-headline">{sum.debrief.headline}</p>
                  {sum.debrief.patterns?.length > 0 && (
                    <ul className="mock-debrief-patterns">
                      {sum.debrief.patterns.map((p, i) => (
                        <li key={i} className="mock-debrief-pattern">{p}</li>
                      ))}
                    </ul>
                  )}
                  {sum.debrief.priority_action && (
                    <div className="mock-debrief-action">
                      <span className="mock-debrief-action-label">Next step</span>
                      {sum.debrief.priority_path_slug ? (
                        <span>
                          {sum.debrief.priority_action.replace(/^Work through the "[^"]+" path to reinforce /, 'Reinforce ')}
                          {' '}
                          <Link
                            to={`/learn/${sum.track || session?.track || 'sql'}/${sum.debrief.priority_path_slug}`}
                            className="mock-debrief-path-link"
                          >
                            {sum.debrief.priority_path_title} →
                          </Link>
                        </span>
                      ) : (
                        <span>{sum.debrief.priority_action}</span>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
            <hr className="mock-summary-divider" />
            {qs.map((q, i) => {
              const isSolved = q.is_solved ?? solved[q.id];
              const expanded = expandedSolutions[q.id];
              return (
                <div key={q.id} className="mock-summary-row">
                  <div className="mock-summary-row-main">
                    <span className="mock-summary-qnum">Q{q.position ?? i + 1}</span>
                    <span className="mock-summary-qtitle">{q.title}</span>
                    <span className={`mock-summary-status ${isSolved ? 'solved' : 'unsolved'}`}>
                      {isSolved ? '✓ solved' : '✗ unsolved'}
                    </span>
                    {q.time_spent_s != null && (
                      <span className="mock-summary-time-spent">{formatTime(q.time_spent_s)}</span>
                    )}
                    {(q.solution_query || q.solution_code || q.explanation) && (
                      <button
                        className="mock-solution-toggle"
                        onClick={() => setExpandedSolutions(prev => ({ ...prev, [q.id]: !expanded }))}
                      >
                        {expanded ? 'Hide solution ▲' : 'See solution ▾'}
                      </button>
                    )}
                  </div>
                  {expanded && (
                    <div className="mock-solution-body">
                      {q.explanation && <p className="mock-solution-explanation">{q.explanation}</p>}
                      {(q.solution_query || q.solution_code) && (
                        <pre className="mock-solution-code">{q.solution_query || q.solution_code}</pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            <hr className="mock-summary-divider" />
            {isProOrElite && conceptRows.length > 0 && (
              <div className="mock-concept-summary">
                <div className="mock-concept-summary-title">Concept breakdown</div>
                <div className="mock-concept-summary-rows">
                  {conceptRows.map((row) => {
                    const knownWeak = isElite && insights?.weakest_concepts?.find(
                      w => w.concept === row.concept && w.track === row.track
                    );
                    return (
                      <div key={`${row.track}-${row.concept}`} className={`mock-concept-summary-row${knownWeak ? ' mock-concept-summary-row--known-weak' : ''}`}>
                        <span className="mock-concept-name">{row.concept}</span>
                        {knownWeak && (
                          <span className="mock-concept-known-weak-badge">known weakness</span>
                        )}
                        <span className="mock-concept-score">{row.correct} / {row.attempts}</span>
                      </div>
                    );
                  })}
                </div>
                {summaryDescriptor.isBenchmark && drillConcepts.length > 0 && (() => {
                  // Elite: prefer a path recommendation for the top weak session concept
                  if (isElite) {
                    const topWeak = conceptRows.find(r => r.track === drillTrack && r.accuracy < 1);
                    const matchedInsight = topWeak && insights?.weakest_concepts?.find(
                      w => w.concept === topWeak.concept && w.track === topWeak.track
                    );
                    if (matchedInsight?.recommended_path_slug) {
                      return (
                        <Link
                          to={`/learn/${matchedInsight.track}/${matchedInsight.recommended_path_slug}`}
                          className="btn btn-secondary btn-compact"
                        >
                          Study {matchedInsight.recommended_path_title} →
                        </Link>
                      );
                    }
                  }
                  return (
                    <Link
                      to={`/practice/${drillTrack}?concepts=${drillConcepts.join(',')}`}
                      className="btn btn-secondary btn-compact"
                    >
                      Drill weak concepts →
                    </Link>
                  );
                })()}
              </div>
            )}
            <hr className="mock-summary-divider" />
            <div className="mock-summary-actions">
              <button
                className="btn btn-secondary"
                onClick={handleShare}
              >
                {shareCopied ? '✓ Copied!' : 'Share result'}
              </button>
              {summaryDescriptor.isBenchmark ? (
                <>
                  <button className="btn btn-secondary" onClick={() => navigate('/mock')}>
                    Back to Mock
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => navigate('/mock', { state: { mockPreset: drillPreset } })}
                  >
                    Plan follow-up drill
                  </button>
                </>
              ) : (
                <>
                  {isProOrElite && drillConcepts.length > 0 ? (
                    <Link
                      to={`/practice/${drillTrack}?concepts=${drillConcepts.join(',')}`}
                      className="btn btn-primary"
                    >
                      Drill weak concepts →
                    </Link>
                  ) : (
                    <button
                      className="btn btn-primary"
                      onClick={() => navigate('/mock', { state: { mockPreset: drillPreset } })}
                    >
                      Continue targeted drill
                    </button>
                  )}
                  <button className="btn btn-secondary" onClick={() => navigate('/mock')}>
                    Back to drill lobby
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Active session ─────────────────────────────────────────────────────────
  const q = currentQuestion;
  const meta = q ? TRACK_META[q.track] : null;
  const currentResult = q ? results[q.id] : null;
  const currentRunResult = q ? runResults[q.id] : null;

  return (
    <div className="mock-shell">
      {/* Mock topbar */}
      <header className="mock-topbar">
        <button
          className="btn btn-secondary btn-compact"
          onClick={handleExitClick}
        >
          ◀ Exit
        </button>

        {/* Question navigation */}
        <div className="mock-q-nav">
          <button
            className="mock-nav-arrow"
            onClick={() => setActiveQ(a => a - 1)}
            disabled={activeQ === 0}
            aria-label="Previous question"
          >←</button>
          <div className="mock-q-tabs">
            {questions.map((question, i) => (
              <button
                key={question.id}
                type="button"
                className={`mock-q-tab ${activeQ === i ? 'active' : ''}`}
                onClick={() => setActiveQ(i)}
              >
                Q{i + 1}
                {question.is_follow_up && (
                  <span className="mock-follow-up-badge" title="Interviewer follow-up">↩</span>
                )}
                <span className={`mock-q-dot ${solved[question.id] ? 'solved' : flagged[question.id] ? 'flagged' : 'unsolved'}`} />
              </button>
            ))}
          </div>
          <button
            className="mock-nav-arrow"
            onClick={() => setActiveQ(a => a + 1)}
            disabled={activeQ >= questions.length - 1}
            aria-label="Next question"
          >→</button>
        </div>

        {/* Timer */}
        <span className={timerClass(remainingS ?? 0)}>
          {formatTime(remainingS)}
        </span>

        <button
          className="btn btn-secondary btn-compact"
          onClick={handleExitClick}
        >
          End session
        </button>
      </header>

      {/* Body */}
      <div className="mock-body">
        {/* Left panel — question info */}
        <div className={`mock-left-panel ${mobileQuestionOpen ? 'open' : ''}`}>
          {mobileQuestionOpen && (
            <button
              className="btn btn-secondary btn-compact mock-close-panel"
              onClick={() => setMobileQuestionOpen(false)}
            >
              ✕ Close
            </button>
          )}

          {/* Focus mode fallback notice */}
          {focusFallback && (
            <div className="mock-focus-fallback-notice">
              Not enough focus concept questions — session includes similar questions to fill the gap.
            </div>
          )}

          <div className={`mock-session-context${sessionDescriptor.isBenchmark ? ' mock-session-context--benchmark' : ''}`}>
            <div className="mock-session-context-head">
              <span className={`mock-session-context-badge${sessionDescriptor.isBenchmark ? ' mock-session-context-badge--benchmark' : ''}`}>
                {sessionDescriptor.modeLabel}
              </span>
              <span className="mock-session-context-track">{TRACK_LABELS[session?.track] || TRACK_LABELS[currentQuestion?.track] || session?.track}</span>
            </div>
            <div className="mock-session-context-title">{sessionDescriptor.title}</div>
            {sessionDescriptor.summaryLine && (
              <div className="mock-session-context-summary">{sessionDescriptor.summaryLine}</div>
            )}
            {sessionDescriptor.description && (
              <p className="mock-session-context-copy">{sessionDescriptor.description}</p>
            )}
          </div>

          <div className="mock-session-rule">
            <span>
              {meta && !meta.hasMCQ
                ? 'Each question is one shot — run freely before you commit.'
                : 'Each question is one shot — select carefully before you commit.'}
            </span>
            <span>Use ← → at the top to move between questions.</span>
          </div>

          {q && (
            <>
              {/* Follow-up fade-in banner */}
              {q.is_follow_up && showFollowUpBanner && (
                <div className="mock-follow-up-banner" aria-live="polite">
                  Interviewer follow-up ↓
                </div>
              )}

              <div className="mock-question-meta">
                <span className={`badge badge-${q.difficulty}`}>{q.difficulty}</span>
                {q.is_follow_up && (
                  <span className="mock-follow-up-badge">Follow-up</span>
                )}
                <span className="mock-question-track">{TRACK_LABELS[q.track]}</span>
              </div>
              <h2 className="mock-question-title">{q.title}</h2>

              <button
                className={`mock-flag-btn ${flagged[q.id] ? 'mock-flag-btn--active' : ''}`}
                onClick={() => toggleFlag(q.id)}
                title={flagged[q.id] ? 'Remove flag' : 'Flag for review'}
              >
                {flagged[q.id] ? '⚑ Flagged' : '⚐ Flag for review'}
              </button>

              {/* Description / Schema toggle (SQL only, skip for reverse which has its own view) */}
              {q.track === 'sql' && q.schema && q.type !== 'reverse' && (
                <div className="mock-view-toggle">
                  <button
                    className={`mock-view-btn ${questionView === 'description' ? 'active' : ''}`}
                    onClick={() => setQuestionView('description')}
                  >
                    Description
                  </button>
                  <button
                    className={`mock-view-btn ${questionView === 'schema' ? 'active' : ''}`}
                    onClick={() => setQuestionView('schema')}
                  >
                    Schema
                  </button>
                </div>
              )}

              {questionView === 'description' || q.type === 'reverse' ? (
                <>
                  {/* Scenario framing: description IS the scenario brief */}
                  {q.framing === 'scenario' && (
                    <div className="mock-scenario-brief">
                      <span className="mock-scenario-brief-label">Scenario</span>
                      <p>{renderDescription(q.description)}</p>
                    </div>
                  )}

                  {/* Reverse SQL: show target result table instead of description */}
                  {q.type === 'reverse' ? (
                    <div className="mock-reverse-block">
                      <p className="mock-reverse-prompt">Write a query that produces this result:</p>
                      {q.result_preview?.length > 0 && (
                        <div className="results-scroll">
                          <table className="results-table">
                            <thead>
                              <tr>
                                {Object.keys(q.result_preview[0]).map(col => (
                                  <th key={col}>{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {q.result_preview.map((row, i) => (
                                <tr key={i}>
                                  {Object.values(row).map((cell, j) => (
                                    <td key={j}>{String(cell ?? '')}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ) : q.framing !== 'scenario' ? (
                    /* Normal description (hidden for scenario — already shown above) */
                    <p className="mock-question-description">{renderDescription(q.description)}</p>
                  ) : null}
                </>
              ) : (
                <SchemaViewer schema={q.schema || {}} />
              )}

              {q.concepts?.length > 0 && (
                <div className="concept-tags" style={{ marginTop: '1rem' }}>
                  {q.concepts.map(c => (
                    <span key={c} className="tag-concept">{c}</span>
                  ))}
                </div>
              )}

              {q.track === 'python-data' && Object.keys(q.dataframes ?? {}).length > 0 && (
                <VariablesPanel dataframes={q.dataframes} schema={{}} />
              )}
            </>
          )}
        </div>

        {/* Right panel — editor + results */}
        <div className="mock-right-panel">
          {/* Mobile: "Question" button to open left panel */}
          <button
            className="btn btn-secondary btn-compact mock-show-question-btn"
            onClick={() => setMobileQuestionOpen(true)}
          >
            Question ↑
          </button>

          {q && meta && !meta.hasMCQ && (
            <>
              {/* Debug question: show error callout and "fix the bug" prompt */}
              {q.type === 'debug' && (
                <p className="mock-debug-prompt">Fix the bug in the code below.</p>
              )}
              {q.type === 'debug' && q.debug_error && (
                <div className="mock-debug-error" role="alert">
                  <span className="mock-debug-error-label">Error output</span>
                  <pre className="mock-debug-error-pre">{q.debug_error}</pre>
                </div>
              )}

              <div className="editor-wrapper editor-workspace">
                <div className="editor-topbar">
                  <span className="editor-title">
                    {q.track === 'sql' ? 'SQL Editor' : q.track === 'python' ? 'Python' : q.track === 'python-data' ? 'Pandas' : 'Code Editor'}
                  </span>
                  <div className="editor-topbar-actions">
                    <button className="editor-expand-btn" onClick={() => adjustFontSize(-1)} title="Decrease font size" aria-label="Decrease font size">A−</button>
                    <button className="editor-expand-btn" onClick={() => adjustFontSize(+1)} title="Increase font size" aria-label="Increase font size">A+</button>
                    <button
                      className="editor-expand-btn"
                      onClick={() => setShortcutHelpOpen(v => !v)}
                      title="Keyboard shortcuts"
                      aria-label="Keyboard shortcuts"
                      aria-expanded={shortcutHelpOpen}
                    >?</button>
                    <button
                      className="editor-expand-btn"
                      onClick={() => setCode(q.id, DEFAULT_CODE[q.track] || '')}
                      title="Reset to default"
                      aria-label="Reset to default"
                    >↺</button>
                    <button
                      className="editor-expand-btn"
                      onClick={() => setEditorTall(v => !v)}
                      title={editorTall ? 'Collapse editor' : 'Expand editor'}
                      aria-label={editorTall ? 'Collapse editor' : 'Expand editor'}
                    >{editorTall ? '⊟' : '⊞'}</button>
                  </div>
                </div>

                {shortcutHelpOpen && (
                  <div className="workspace-shortcut-popover" role="dialog" aria-label="Keyboard shortcuts">
                    {meta.hasRunCode && (
                      <div className="workspace-shortcut-row">
                        <span>{q.track === 'sql' ? 'Run query' : 'Run code'}</span>
                        <kbd className="shortcut-kbd">⌘↵</kbd>
                      </div>
                    )}
                    <div className="workspace-shortcut-row">
                      <span>Submit answer</span>
                      <kbd className="shortcut-kbd">⌘⇧↵</kbd>
                    </div>
                  </div>
                )}

                <CodeEditor
                  value={getCode(q)}
                  onChange={val => setCode(q.id, val)}
                  language={meta.language}
                  height={editorHeight}
                  fontSize={fontSize}
                  onMount={handleEditorMount}
                  ariaLabel={`${TRACK_LABELS[q.track]} mock interview editor`}
                />
                <div className="editor-footer question-action-dock">
                  <div className="button-row question-action-row">
                    {meta.hasRunCode && (
                      <button
                        className="btn btn-secondary"
                        onClick={handleRun}
                        disabled={running || submitting}
                      >
                        <span>{running ? 'Running…' : q.track === 'sql' ? 'Run Query' : 'Run Code'}</span>
                        <kbd className="shortcut-kbd">⌘↵</kbd>
                      </button>
                    )}
                    <button
                      className="btn btn-primary"
                      onClick={handleSubmit}
                      disabled={submitting || submitted[q.id] || !getCode(q)?.trim()}
                    >
                      <span>
                        {submitting ? 'Checking…' : solved[q.id] ? '✓ Solved' : submitted[q.id] ? '✗ Submitted' : 'Submit'}
                      </span>
                      <kbd className="shortcut-kbd">⌘⇧↵</kbd>
                    </button>
                  </div>
                </div>
              </div>

              {/* Skeleton while running */}
              {running && !currentRunResult && (
                <div className="results-card">
                  <div className="results-header">
                    <span>{q.track === 'python' ? 'Running tests…' : 'Query Result'}</span>
                    <Skeleton className="skeleton-line" width="2.5rem" height="11px" />
                  </div>
                  <div className="results-skeleton-body">
                    {[1, 2, 3, 4, 5].map(i => (
                      <Skeleton key={i} className="results-skeleton-row" style={{ animationDelay: `${(i - 1) * 60}ms` }} />
                    ))}
                  </div>
                </div>
              )}

              {/* SQL run result */}
              {q.track === 'sql' && currentRunResult && !currentRunResult.error && currentRunResult.columns && (
                <div className="results-card">
                  <div className="results-header">
                    <span>Query Result</span>
                    <span>{(currentRunResult.rows ?? []).length} row{(currentRunResult.rows ?? []).length !== 1 ? 's' : ''}</span>
                  </div>
                  <ResultsTable columns={currentRunResult.columns} rows={currentRunResult.rows ?? []} />
                </div>
              )}

              {/* Python run results */}
              {q.track === 'python' && currentRunResult && !currentRunResult.error && (
                <>
                  <TestCasePanel results={currentRunResult.test_results ?? []} hiddenSummary={null} />
                  <PrintOutputPanel output={currentRunResult.stdout ?? ''} />
                </>
              )}

              {/* Pandas run result */}
              {q.track === 'python-data' && currentRunResult && !currentRunResult.error && (
                <>
                  {currentRunResult.columns && (
                    <div className="results-card">
                      <div className="results-header">
                        <span>Output</span>
                        <span>{(currentRunResult.rows ?? []).length} rows</span>
                      </div>
                      <ResultsTable columns={currentRunResult.columns} rows={currentRunResult.rows ?? []} />
                    </div>
                  )}
                  <PrintOutputPanel output={currentRunResult.stdout ?? ''} />
                </>
              )}

              {currentRunResult?.error && (
                <div className="mock-run-error">{currentRunResult.error}</div>
              )}
            </>
          )}

          {q && meta?.hasMCQ && (
            <div className="card">
              <div className="section-heading">
                <h3>Choose the correct answer</h3>
              </div>
              <MCQPanel
                options={q.options || []}
                selectedOption={mcqSelections[q.id] !== undefined ? mcqSelections[q.id] : null}
                onSelect={idx => setMcqSelections(prev => ({ ...prev, [q.id]: idx }))}
                submitted={!!currentResult}
                correct={currentResult?.correct ?? null}
                correctIndex={null}  // not revealed mid-session
                explanation=""
              />
              <div className="editor-footer editor-footer-plain question-action-dock">
                <div className="button-row question-action-row">
                  <button
                    className="btn btn-primary"
                    onClick={handleSubmit}
                    disabled={submitting || submitted[q.id] || mcqSelections[q.id] === undefined}
                  >
                    {submitting ? 'Checking…' : solved[q.id] ? '✓ Solved' : submitted[q.id] ? '✗ Submitted' : 'Submit'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Network/server error on submit (not shown for validation errors or feedback) */}
          {submitNetworkError && !submitted[q?.id] && (
            <div className="mock-verdict mock-verdict--error">{submitNetworkError}</div>
          )}

          {/* Post-submit navigation — no feedback, just move forward */}
          {submitted[q?.id] && activeQ < questions.length - 1 && (
            <button
              className="btn btn-secondary"
              onClick={() => setActiveQ(activeQ + 1)}
            >
              Next question →
            </button>
          )}
          {submitted[q?.id] && activeQ === questions.length - 1 && (
            <p className="mock-all-done">All questions answered — end your session when ready.</p>
          )}
        </div>
      </div>

      {/* Pre-submission review modal */}
      {showExitConfirm && (() => {
        const flaggedUnsolved = questions.filter(q => flagged[q.id] && !solved[q.id]);
        const unattempted = questions.filter(q => !submitted[q.id] && !solved[q.id]);
        const hasIncomplete = flaggedUnsolved.length > 0 || unattempted.length > 0;
        const warningParts = [
          flaggedUnsolved.length > 0 && `${flaggedUnsolved.length} flagged question${flaggedUnsolved.length > 1 ? 's' : ''}`,
          unattempted.length > 0 && `${unattempted.length} unattempted question${unattempted.length > 1 ? 's' : ''}`,
        ].filter(Boolean);
        return (
          <div className="mock-modal-overlay" onClick={() => setShowExitConfirm(false)}>
            <div className="mock-modal mock-modal--review" onClick={e => e.stopPropagation()}>
              <h3 className="mock-modal-title">
                {hasIncomplete ? 'Review before submitting' : 'Ready to end your session?'}
              </h3>
              <ul className="mock-review-list">
                {questions.map((question, i) => {
                  const isSolved = solved[question.id];
                  const isFlagged = flagged[question.id] && !solved[question.id];
                  return (
                    <li
                      key={question.id}
                      className={`mock-review-item ${isSolved ? 'mock-review-item--solved' : isFlagged ? 'mock-review-item--flagged' : 'mock-review-item--unsolved'}`}
                      onClick={() => { setShowExitConfirm(false); setActiveQ(i); }}
                    >
                      <span className="mock-review-qnum">Q{i + 1}</span>
                      <span className="mock-review-qtitle">{question.title}</span>
                      <span className="mock-review-status">
                        {isSolved ? '✓' : isFlagged ? '⚑' : '○'}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {hasIncomplete && (
                <p className="mock-modal-warning">
                  {warningParts.join(' and ')} remaining. Go back to review, or end the session now.
                </p>
              )}
              <div className="mock-modal-actions">
                {hasIncomplete ? (
                  <>
                    <button className="btn btn-secondary" onClick={goToFirstIncomplete}>
                      Go back and review
                    </button>
                    <button className="btn btn-primary mock-btn--end" onClick={handleExitConfirm}>
                      End session anyway
                    </button>
                  </>
                ) : (
                  <>
                    <button className="btn btn-secondary" onClick={() => setShowExitConfirm(false)}>
                      Keep going
                    </button>
                    <button className="btn btn-primary" onClick={handleExitConfirm}>
                      End session
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        );
      })()}

      {/* Early-exit discard prompt */}
      {showDiscardPrompt && (
        <div className="mock-modal-overlay" onClick={() => setShowDiscardPrompt(false)}>
          <div className="mock-modal" onClick={e => e.stopPropagation()}>
            <h3 className="mock-modal-title">Barely started — want to keep this?</h3>
            <p className="mock-modal-body">
              You're less than a minute in and haven't run or submitted anything yet.
              You can discard this session and it won't appear in your history or affect any stats.
            </p>
            <div className="mock-modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowDiscardPrompt(false)}>
                Keep going
              </button>
              <button className="btn btn-secondary" onClick={() => { setShowDiscardPrompt(false); setShowExitConfirm(true); }}>
                End normally
              </button>
              <button className="btn btn-danger" onClick={handleDiscard}>
                Discard session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
