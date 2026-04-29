import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api';
import CodeEditor from '../components/CodeEditor';
import MCQPanel from '../components/MCQPanel';
import { TRACK_META } from '../contexts/TopicContext';
import { track as trackEvent } from '../analytics';

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

const TRACK_LABELS = {
  sql: 'SQL', python: 'Python', 'python-data': 'Pandas', pyspark: 'PySpark', mixed: 'Mixed',
};

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
  const [mcqSelections, setMcqSelections] = useState({}); // {qId: int}
  const [submitting, setSubmitting] = useState(false);
  const [running, setRunning] = useState(false);
  const [runResults, setRunResults] = useState({});
  const [remainingS, setRemainingS] = useState(null);
  const [status, setStatus] = useState('loading');  // 'loading'|'active'|'finishing'|'completed'
  const [summary, setSummary] = useState(null);
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  const [questionView, setQuestionView] = useState('description');  // 'description'|'schema'
  const [mobileQuestionOpen, setMobileQuestionOpen] = useState(false);
  const [expandedSolutions, setExpandedSolutions] = useState({}); // {qId: bool}
  const [loadError, setLoadError] = useState(null);
  const [insights, setInsights] = useState(null);

  const [showFollowUpBanner, setShowFollowUpBanner] = useState(false);

  const finishCalled = useRef(false);
  const bannerTimerRef = useRef(null);

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

    // Restore codes and solved state from server
    const initialCodes = {};
    const initialSolved = {};
    (data.questions || []).forEach(q => {
      // Debug questions pre-fill the editor with starter_code unless the user already submitted
      initialCodes[q.id] = q.final_code || (q.type === 'debug' ? (q.starter_code || '') : null) || DEFAULT_CODE[q.track] || '';
      initialSolved[q.id] = q.is_solved || false;
    });
    setCodes(initialCodes);
    setSolved(initialSolved);

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

  const currentQuestion = questions[activeQ] || null;

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
    if (!currentQuestion || submitting || solved[currentQuestion.id]) return;
    const q = currentQuestion;

    setSubmitting(true);
    setResults(prev => ({ ...prev, [q.id]: null }));
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
      setResults(prev => ({ ...prev, [q.id]: r.data }));
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
      const errMsg = err?.response?.data?.detail || 'Submission failed';
      setResults(prev => ({ ...prev, [q.id]: { error: errMsg } }));
    } finally {
      setSubmitting(false);
    }
  }

  function handleExitConfirm() {
    setShowExitConfirm(false);
    handleFinish().then(() => navigate('/mock'));
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

    let comparisonCopy = null;
    if (typeof baselineAccuracy === 'number') {
      const delta = Math.round((sessionAccuracy - baselineAccuracy) * 100);
      if (delta > 0) comparisonCopy = `${delta}% above your historical accuracy`;
      else if (delta < 0) comparisonCopy = `${Math.abs(delta)}% below your historical accuracy`;
      else comparisonCopy = 'on par with your historical accuracy';
    }

    function shareText() {
      const diff = session?.difficulty || sum?.difficulty || '';
      const trk = TRACK_LABELS[session?.track || sum?.track] || '';
      const mins = timeUsedS ? Math.floor(timeUsedS / 60) : '?';
      return `${solvedCount}/${totalCount} ${diff} ${trk} questions in ${mins}m`;
    }

    return (
      <div className="mock-shell">
        <header className="mock-topbar">
          <Link to="/mock" className="btn btn-secondary btn-compact">← Back to Mock</Link>
          <span className="mock-topbar-title">Session Summary</span>
          <span />
        </header>
        <div className="mock-summary-scroll">
          <div className="mock-summary-card">
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
                {drillConcepts.length > 0 && (() => {
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
                onClick={() => {
                  navigator.clipboard?.writeText(shareText()).catch(() => {});
                }}
              >
                Share result
              </button>
              <button className="btn btn-primary" onClick={() => navigate('/mock')}>
                New mock interview
              </button>
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
          onClick={() => setShowExitConfirm(true)}
        >
          ◀ Exit
        </button>

        {/* Question dots */}
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
              <span className={`mock-q-dot ${solved[question.id] ? 'solved' : 'unsolved'}`} />
            </button>
          ))}
        </div>

        {/* Timer */}
        <span className={timerClass(remainingS ?? 0)}>
          {formatTime(remainingS)}
        </span>

        <button
          className="btn btn-secondary btn-compact"
          onClick={() => setShowExitConfirm(true)}
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
                      <p>{q.description}</p>
                    </div>
                  )}

                  {/* Reverse SQL: show target result table instead of description */}
                  {q.type === 'reverse' ? (
                    <div className="mock-reverse-block">
                      <p className="mock-reverse-prompt">Write a query that produces this result:</p>
                      {q.result_preview?.length > 0 && (
                        <div className="result-table-wrap">
                          <table className="result-table">
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
                    <p className="mock-question-description">{q.description}</p>
                  ) : null}
                </>
              ) : (
                <div className="mock-schema">
                  {Object.entries(q.schema || {}).map(([table, cols]) => (
                    <div key={table} className="mock-schema-table">
                      <div className="mock-schema-table-name">{table}</div>
                      <ul className="mock-schema-cols">
                        {cols.map(col => <li key={col}>{col}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {q.concepts?.length > 0 && (
                <div className="concept-tags" style={{ marginTop: '1rem' }}>
                  {q.concepts.map(c => (
                    <span key={c} className="tag-concept">{c}</span>
                  ))}
                </div>
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

              <div className="mock-editor-wrapper">
                <CodeEditor
                  value={getCode(q)}
                  onChange={val => setCode(q.id, val)}
                  language={meta.language}
                  height="340px"
                />
              </div>
              <div className="mock-action-row">
                {meta.hasRunCode && (
                  <button
                    className="btn btn-secondary"
                    onClick={handleRun}
                    disabled={running || submitting}
                  >
                    {running ? 'Running…' : 'Run'}
                  </button>
                )}
                <button
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={submitting || solved[q.id]}
                >
                  {submitting ? 'Checking…' : solved[q.id] ? '✓ Solved' : 'Submit'}
                </button>
              </div>

              {/* Run result */}
              {currentRunResult && !currentRunResult.error && currentRunResult.columns && (
                <div className="mock-run-result">
                  <div className="mock-run-result-label">Run result</div>
                  <div className="result-table-wrap">
                    <table className="result-table">
                      <thead>
                        <tr>{currentRunResult.columns.map(c => <th key={c}>{c}</th>)}</tr>
                      </thead>
                      <tbody>
                        {currentRunResult.rows?.slice(0, 20).map((row, i) => (
                          <tr key={i}>{row.map((cell, j) => <td key={j}>{String(cell ?? '')}</td>)}</tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              {currentRunResult?.error && (
                <div className="mock-run-error">{currentRunResult.error}</div>
              )}
            </>
          )}

          {q && meta?.hasMCQ && (
            <>
              <MCQPanel
                options={q.options || []}
                selectedOption={mcqSelections[q.id] !== undefined ? mcqSelections[q.id] : null}
                onSelect={idx => setMcqSelections(prev => ({ ...prev, [q.id]: idx }))}
                submitted={!!currentResult}
                correct={currentResult?.correct ?? null}
                correctIndex={null}  // not revealed mid-session
                explanation=""
              />
              <div className="mock-action-row">
                <button
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={submitting || solved[q.id] || mcqSelections[q.id] === undefined}
                >
                  {submitting ? 'Checking…' : solved[q.id] ? '✓ Solved' : 'Submit'}
                </button>
              </div>
            </>
          )}

          {/* Submit verdict */}
          {currentResult && (
            <div className={`mock-verdict ${currentResult.correct ? 'mock-verdict--correct' : currentResult.error ? 'mock-verdict--error' : 'mock-verdict--wrong'}`}>
              {currentResult.error
                ? `Error: ${currentResult.error}`
                : currentResult.correct
                  ? '✓ Correct! Move to the next question.'
                  : '✗ Not quite — review your logic and try again.'}
              {!currentResult.error && !currentResult.correct && currentResult.feedback?.length > 0 && (
                <ul className="mock-feedback-list">
                  {currentResult.feedback.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              )}
            </div>
          )}

          {/* Next question prompt */}
          {solved[q?.id] && activeQ < questions.length - 1 && (
            <button
              className="btn btn-secondary"
              onClick={() => setActiveQ(activeQ + 1)}
            >
              Next question →
            </button>
          )}
        </div>
      </div>

      {/* Exit confirmation modal */}
      {showExitConfirm && (
        <div className="mock-modal-overlay" onClick={() => setShowExitConfirm(false)}>
          <div className="mock-modal" onClick={e => e.stopPropagation()}>
            <h3 className="mock-modal-title">End this session?</h3>
            <p className="mock-modal-body">Your progress will be saved and you'll see a summary.</p>
            <div className="mock-modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowExitConfirm(false)}>
                Keep going
              </button>
              <button className="btn btn-primary" onClick={handleExitConfirm}>
                End and see summary
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
