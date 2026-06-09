import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import Topbar from './Topbar';
import UpgradeButton from './UpgradeButton';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';
import { useTopic } from '../contexts/TopicContext';
import TrackHubPage from '../pages/TrackHubPage';
import api from '../api';
export default function AppShell() {
  const { catalog, loading, error, refresh } = useCatalog();
  const { user, refreshUser } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches
  );
  const [collapsedByDiff, setCollapsedByDiff] = useState({ easy: false, medium: true, hard: true });
  const [upgradeSuccess, setUpgradeSuccess] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  // Determine if we're at the hub (no question selected)
  const isAtHub = !location.pathname.includes('/questions/');

  // Track mobile breakpoint
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    setIsMobile(mq.matches);
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Close mobile drawer on Escape key
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  // When landing on the hub with ?concepts=..., auto-navigate to the first
  // matching accessible question so the user goes straight to the question page.
  useEffect(() => {
    if (!isAtHub || loading || error || !catalog) return;
    const params = new URLSearchParams(location.search);
    const rawConcepts = params.get('concepts');
    if (!rawConcepts) return;

    // Normalise incoming values: underscores → spaces, trim, lowercase
    const requested = rawConcepts
      .split(',')
      .map((s) => s.trim().toLowerCase().replace(/_/g, ' ').replace(/-/g, ' '))
      .filter(Boolean);
    if (requested.length === 0) return;

    const groups = catalog?.groups ?? [];
    let firstMatch = null;
    outer: for (const group of groups) {
      for (const q of group.questions) {
        if (q.state === 'locked') continue;
        const qConcepts = (q.concepts ?? []).map((c) => String(c).toLowerCase());
        const hit = requested.some((req) => qConcepts.some((qc) => qc.includes(req) || req.includes(qc)));
        if (hit) { firstMatch = q; break outer; }
      }
    }

    if (firstMatch) {
      navigate(`${location.pathname}/questions/${firstMatch.id}`, { replace: true });
    }
  }, [isAtHub, loading, error, catalog, location.pathname, location.search, navigate]);


  useEffect(() => {
    if (!location.search.includes('upgraded=true')) return;
    setUpgradeSuccess(true);
    refreshUser().catch(() => {});
    refresh().catch(() => {});
    const params = new URLSearchParams(location.search);
    params.delete('upgraded');
    navigate({ pathname: location.pathname, search: params.toString() ? `?${params.toString()}` : '' }, { replace: true });
  }, [location.pathname, location.search, navigate, refresh, refreshUser]);

  function toggleDiff(diff) {
    setCollapsedByDiff((prev) => ({ ...prev, [diff]: !prev[diff] }));
  }

  function handleNavigateFromSidebar() {
    if (typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches) {
      setMobileOpen(false);
    }
  }

  function handleSidebarToggle() {
    if (typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches) {
      setMobileOpen((value) => !value);
      return;
    }
    setDesktopCollapsed((value) => !value);
  }

  const { topic, meta } = useTopic();
  const pathSlug = new URLSearchParams(location.search).get('path');
  const focusMode = new URLSearchParams(location.search).get('focus') === '1';

  // Path data — fetched when ?path= is present
  const [pathData, setPathData] = useState(null);
  useEffect(() => {
    if (!pathSlug) { setPathData(null); return; }
    api.get(`/paths/${pathSlug}`)
      .then(r => setPathData(r.data))
      .catch(() => setPathData(null));
  }, [pathSlug]);

  const modeLabel = pathData ? pathData.title : pathSlug ? `${meta.label} · Path` : `${meta.label} · Challenge`;

  // Session goal tracking
  const [sessionGoal, setSessionGoal] = useState(() => {
    try { return Math.max(1, Math.min(20, parseInt(localStorage.getItem('session-goal') ?? '5', 10))); } catch { return 5; }
  });
  const totalSolvedSidebar = catalog?.groups?.reduce(
    (sum, g) => sum + g.questions.filter(q => q.state === 'solved').length, 0
  ) ?? 0;

  const [sessionStartSolved, setSessionStartSolved] = useState(null);
  useEffect(() => {
    if (!catalog || sessionStartSolved !== null) return;
    const stored = sessionStorage.getItem('session-start-solved');
    if (stored !== null) {
      setSessionStartSolved(parseInt(stored, 10));
    } else {
      sessionStorage.setItem('session-start-solved', String(totalSolvedSidebar));
      setSessionStartSolved(totalSolvedSidebar);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog]);

  const sessionSolvedNow = sessionStartSolved !== null ? Math.max(0, totalSolvedSidebar - sessionStartSolved) : 0;
  const goalProgress = Math.min(1, sessionGoal > 0 ? sessionSolvedNow / sessionGoal : 0);
  const goalMet = sessionSolvedNow >= sessionGoal;

  const normalisedPlan = user?.plan?.startsWith('lifetime_') ? user.plan.replace('lifetime_', '') : (user?.plan ?? 'free');
  const showUpgradeControls = user && (normalisedPlan === 'free' || normalisedPlan === 'pro');
  const planPillClass = `shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`;

  const planLabel = normalisedPlan === 'elite' ? 'Elite' : normalisedPlan === 'pro' ? 'Pro' : 'Free';
  const mediumGroup = catalog?.groups?.find(g => g.difficulty === 'medium');
  const lockedMediumCount = mediumGroup?.questions?.filter(q => q.state === 'locked').length ?? 0;
  const lockedHardCount = (catalog?.groups?.find(g => g.difficulty === 'hard'))?.questions?.filter(q => q.state === 'locked').length ?? 0;
  const showUnlockNudge = !!(normalisedPlan === 'free' && (lockedMediumCount > 0 || lockedHardCount > 0) && catalog);
  const unlockNudgeByTrack = {
    sql: 'Medium unlocks at 8, 15, and 25 easy solves. Hard unlocks at 8, 15, and 22 medium solves (capped at 15 hard).',
    python: 'Medium unlocks at 8, 15, and 25 easy solves. Hard unlocks at 8, 15, and 22 medium solves (capped at 15 hard).',
    'python-data': 'Medium unlocks at 8, 15, and 25 easy solves. Hard unlocks at 8, 15, and 22 medium solves (capped at 15 hard).',
    pyspark: 'Medium unlocks at 10, 17, and 25 easy solves. Hard unlocks at 12 medium solves (capped at 5 hard).',
    'data-engineering': 'Medium unlocks at 10, 17, and 25 easy solves. Hard unlocks at 12 medium solves (capped at 5 hard).',
  };
  const unlockNudgeCopy = unlockNudgeByTrack[topic] ?? unlockNudgeByTrack.sql;

  const sidebarToggleNode = isMobile ? (
    <button
      className="btn btn-secondary sidebar-toggle"
      onClick={handleSidebarToggle}
      aria-label="Toggle question bank"
      aria-expanded={mobileOpen}
      aria-controls="sidebar"
    >
      <span className="sidebar-toggle-icon" aria-hidden="true">☰</span>
      <span className="sidebar-toggle-label">Questions</span>
    </button>
  ) : null;

  const modePillNode = !isAtHub ? (
    <span
      className={`shell-pill shell-pill-mode${pathSlug ? ' shell-pill-mode-path' : ''}`}
      style={{ '--mode-dot-color': meta.color }}
      aria-label={modeLabel}
    >
      <span className="shell-pill-mode-dot" aria-hidden="true" />
      {modeLabel}
    </span>
  ) : null;

  const planPillNode = user ? (
    <span className={planPillClass}>{planLabel}</span>
  ) : null;

  const streakPillNode = user && typeof user.streak_days === 'number' && user.streak_days > 0 ? (
    <span
      className={`shell-pill shell-pill-streak${user.streak_at_risk ? ' shell-pill-streak-risk' : ''}`}
      title={user.streak_at_risk ? 'Streak at risk: solve one question today' : 'Current solve streak'}
    >
      {user.streak_days}-day streak
    </span>
  ) : null;

  const userExtrasNode = (
    <>
      {streakPillNode}
      {planPillNode}
    </>
  );

  const focusToggleNode = !isAtHub ? (
    <a
      href={focusMode
        ? location.pathname + (location.search.replace(/[?&]focus=1/, '').replace(/^&/, '?') || '')
        : location.pathname + (location.search ? location.search + '&focus=1' : '?focus=1')
      }
      className={`shell-pill shell-pill-focus${focusMode ? ' shell-pill-focus--active' : ''}`}
      title={focusMode ? 'Exit focus mode' : 'Enter focus mode (hides sidebar)'}
      aria-label={focusMode ? 'Exit focus mode' : 'Enter focus mode'}
    >
      {focusMode ? '⊡ Focus' : '⊞ Focus'}
    </a>
  ) : null;

  const banner = upgradeSuccess ? (
    <div className="app-banner app-banner-success">
      Upgrade confirmed. Your access is refreshing now.
    </div>
  ) : null;

  return (
    <div className={`app-shell ${desktopCollapsed || focusMode ? 'sidebar-collapsed' : ''}`}>
      <Topbar
        variant="app"
        leftSlot={sidebarToggleNode}
        centerSlot={modePillNode}
        userExtras={<>{focusToggleNode}{userExtrasNode}</>}
        belowTopbar={banner}
      />

      <div className="app-body">
        <aside id="sidebar" className={`sidebar ${mobileOpen ? 'sidebar-open' : ''} ${pathSlug ? 'sidebar--path-mode' : ''}`}>
          {!isMobile && (
            <button
              className="sidebar-collapse-btn"
              onClick={handleSidebarToggle}
              aria-label={desktopCollapsed ? 'Show question bank' : 'Hide question bank'}
              title={desktopCollapsed ? 'Show question bank' : 'Hide question bank'}
            >
              ‹
            </button>
          )}
          {pathSlug ? (
            <PathSidebar
              pathData={pathData}
              pathSlug={pathSlug}
              topic={topic}
              meta={meta}
              currentId={location.pathname.match(/\/questions\/([^/?]+)/)?.[1]}
              onNavigate={handleNavigateFromSidebar}
              plan={user?.plan ?? 'free'}
            />
          ) : (
            <>
              {loading && <SidebarNav isLoading />}
              {error && <div className="sidebar-error">{error}</div>}
              {!loading && !error && catalog && (
                <SidebarNav
                  catalog={catalog}
                  collapsedByDiff={collapsedByDiff}
                  toggleDiff={toggleDiff}
                  onNavigate={handleNavigateFromSidebar}
                  plan={user?.plan ?? 'free'}
                />
              )}
              {showUnlockNudge && (
                <div className="sidebar-unlock-nudge">
                  Questions unlock as you solve them. {unlockNudgeCopy} The sequence builds real competence.
                </div>
              )}
              {/* Session goal widget */}
              {user && (
                <div className={`session-goal-widget${goalMet ? ' session-goal-widget--met' : ''}`}>
                  <div className="session-goal-row">
                    <span className="session-goal-label">Session goal</span>
                    <div className="session-goal-controls">
                      <button
                        className="session-goal-adj"
                        aria-label="Decrease goal"
                        onClick={() => setSessionGoal((g) => {
                          const next = Math.max(1, g - 1);
                          try { localStorage.setItem('session-goal', String(next)); } catch {}
                          return next;
                        })}
                      >−</button>
                      <span className="session-goal-count">{sessionSolvedNow}/{sessionGoal}</span>
                      <button
                        className="session-goal-adj"
                        aria-label="Increase goal"
                        onClick={() => setSessionGoal((g) => {
                          const next = Math.min(20, g + 1);
                          try { localStorage.setItem('session-goal', String(next)); } catch {}
                          return next;
                        })}
                      >+</button>
                    </div>
                  </div>
                  <div className="session-goal-bar" role="progressbar" aria-valuenow={sessionSolvedNow} aria-valuemax={sessionGoal}>
                    <div className="session-goal-fill" style={{ width: `${goalProgress * 100}%` }} />
                  </div>
                  {goalMet && <p className="session-goal-met">Goal reached — great session!</p>}
                </div>
              )}
              {showUpgradeControls && (
                <div className="sidebar-upgrade-panel">
                  <p className="sidebar-upgrade-panel-copy">
                    {normalisedPlan === 'free' && totalSolvedSidebar >= 10
                      ? `${totalSolvedSidebar} solved — upgrade for instant access to every question.`
                      : normalisedPlan === 'free' && totalSolvedSidebar > 0
                      ? `${totalSolvedSidebar} question${totalSolvedSidebar !== 1 ? 's' : ''} down — or get full access instantly.`
                      : normalisedPlan === 'free'
                      ? 'Questions unlock as you solve — or get full access instantly.'
                      : 'Unlimited mocks, Interview Loop, and per-session coaching.'}
                  </p>
                  <div className="upgrade-actions">
                    {normalisedPlan === 'free' && (
                      <UpgradeButton
                        tier="pro"
                        label="Unlock Pro"
                        source="sidebar_pro"
                        compact
                        successPath={location.pathname + (pathSlug ? `?path=${encodeURIComponent(pathSlug)}&upgraded=true` : '?upgraded=true')}
                      />
                    )}
                    <UpgradeButton
                      tier="elite"
                      label={normalisedPlan === 'free' ? 'Unlock Elite' : 'Upgrade to Elite'}
                      source="sidebar_elite"
                      compact
                      successPath={location.pathname + (pathSlug ? `?path=${encodeURIComponent(pathSlug)}&upgraded=true` : '?upgraded=true')}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </aside>

        {mobileOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setMobileOpen(false)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                setMobileOpen(false);
              }
            }}
            role="button"
            tabIndex={0}
            aria-label="Close question list"
          />
        )}

        <main className="content">
          {desktopCollapsed && !isMobile && (
            <div className="content-toolbar">
              <button
                className="sidebar-expand-btn"
                onClick={handleSidebarToggle}
                aria-label="Show question bank"
                title="Show question bank"
              >
                ›
              </button>
            </div>
          )}
          {isAtHub ? <TrackHubPage /> : (
            <div key={location.key} className="route-transition">
              <Outlet />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// MCQ tracks use different thresholds than code tracks
const _MCQ_TOPICS = new Set(['pyspark', 'data-engineering']);

function _unlockRules(topic) {
  if (_MCQ_TOPICS.has(topic)) {
    return [
      { easy: 10, unlocks: '3 medium' },
      { easy: 17, unlocks: '8 medium' },
      { easy: 25, unlocks: 'all medium' },
      { medium: 12, unlocks: '5 hard (cap)' },
    ];
  }
  return [
    { easy: 8,  unlocks: '3 medium' },
    { easy: 15, unlocks: '8 medium' },
    { easy: 25, unlocks: 'all medium' },
    { medium: 8,  unlocks: '3 hard' },
    { medium: 15, unlocks: '8 hard' },
    { medium: 22, unlocks: 'all hard (cap: 8)' },
  ];
}

// ── Path sidebar panel ────────────────────────────────────────────────────────
function PathSidebar({ pathData, pathSlug, topic, meta, currentId, onNavigate, plan }) {
  const [hintOpen, setHintOpen] = useState(false);
  const navigate = useNavigate();
  if (!pathData) {
    return (
      <div className="path-sidebar-loading">
        <div className="path-sidebar-shimmer" />
        <div className="path-sidebar-shimmer path-sidebar-shimmer--short" />
      </div>
    );
  }

  const questions = pathData.questions ?? [];
  const solvedCount = questions.filter(q => q.state === 'solved').length;

  return (
    <div className="path-sidebar">
      <div className="path-sidebar-header">
        <Link to={`/learn/${topic}`} className="path-sidebar-back">
          ← All paths
        </Link>
        <div className="path-sidebar-title">{pathData.title}</div>
        <div className="path-sidebar-meta">
          <span className="path-sidebar-dot" style={{ background: meta.color }} />
          {meta.label} · {questions.length} questions
        </div>
        <div className="path-sidebar-progress-bar">
          <div
            className="path-sidebar-progress-fill"
            style={{ width: `${questions.length > 0 ? (solvedCount / questions.length) * 100 : 0}%`, background: meta.color }}
          />
        </div>
        <span className="path-sidebar-progress-label">{solvedCount}/{questions.length} complete</span>
      </div>

      <nav className="path-sidebar-list" aria-label="Path questions">
        {questions.map((q, i) => {
          const isCurrent = String(q.id) === String(currentId);
          const isSolved = q.state === 'solved';
          const isLocked = q.state === 'locked';
          const url = `/practice/${topic}/questions/${q.id}?path=${pathSlug}`;

          return (
            <Link
              key={q.id}
              to={isLocked ? '#' : url}
              className={`path-sidebar-item${isCurrent ? ' path-sidebar-item--active' : ''}${isSolved ? ' path-sidebar-item--solved' : ''}${isLocked ? ' path-sidebar-item--locked' : ''}`}
              aria-current={isCurrent ? 'page' : undefined}
              onClick={isLocked ? e => e.preventDefault() : onNavigate}
            >
              <span className="path-sidebar-item-num">{i + 1}</span>
              <span className="path-sidebar-item-title">{q.title}</span>
              <span className="path-sidebar-item-state" aria-hidden="true">
                {isSolved ? '✓' : isLocked ? '🔒' : null}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Unlock hint — free users only, shown when any question is locked */}
      {plan === 'free' && questions.some(q => q.state === 'locked') && (
        <div className="path-sidebar-hint">
          <div className="path-sidebar-hint-row">
            <p className="path-sidebar-hint-text">Some questions are locked — free tier.</p>
            <div className="path-sidebar-hint-help-wrap">
              <button
                className="path-sidebar-hint-help"
                aria-label="How unlocking works"
                aria-expanded={hintOpen}
                onClick={() => setHintOpen(o => !o)}
              >?</button>
              {hintOpen && (
                <div className="path-sidebar-hint-popover" role="tooltip">
                  <p className="path-sidebar-hint-popover-title">How questions unlock</p>
                  <p className="path-sidebar-hint-popover-sub">Solves in this track count globally — not just within this path.</p>
                  <table className="path-sidebar-hint-table">
                    <tbody>
                      {_unlockRules(topic).map((r, i) => (
                        <tr key={i}>
                          <td>{r.easy != null ? `${r.easy} easy solved` : `${r.medium} medium solved`}</td>
                          <td>→ {r.unlocks}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {pathData.unlock_hint && (
                    <p className="path-sidebar-hint-popover-next">Your next step: {pathData.unlock_hint.replace(/\.$/, '')}</p>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="path-sidebar-hint-actions">
            <button type="button" className="path-sidebar-hint-link path-sidebar-hint-link--pro" onClick={() => navigate('/', { state: { scrollTo: 'landing-pricing' } })}>Pro — unlock all ↗</button>
            <button type="button" className="path-sidebar-hint-link path-sidebar-hint-link--elite" onClick={() => navigate('/', { state: { scrollTo: 'landing-pricing' } })}>Elite — unlock all ↗</button>
          </div>
        </div>
      )}

      <div className="path-sidebar-footer">
        <Link to={`/practice/${topic}`} className="path-sidebar-exit">
          Exit path → Practice
        </Link>
      </div>
    </div>
  );
}
