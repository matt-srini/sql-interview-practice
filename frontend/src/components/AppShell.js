import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import Topbar from './Topbar';
import UpgradeButton from './UpgradeButton';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';
import { useTopic } from '../contexts/TopicContext';
import TrackHubPage from '../pages/TrackHubPage';
import { pickNextUpQuestionId } from '../utils/catalogNav';
import { getDailySolves, EVENT_NAME as DAILY_SOLVES_EVENT } from '../utils/dailyGoal';
import api from '../api';
export default function AppShell() {
  const { catalog, loading, error, refresh } = useCatalog();
  const { user, loading: authLoading, refreshUser } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(max-width: 900px)').matches
  );
  const [collapsedByDiff, setCollapsedByDiff] = useState({ easy: false, medium: true, hard: true });
  const [upgradeSuccess, setUpgradeSuccess] = useState(false);
  const [drillUpsellDismissed, setDrillUpsellDismissed] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  // Determine if we're at the hub (no question selected)
  const isAtHub = !location.pathname.includes('/questions/');

  // Concept drills are a Pro+ feature. Fail closed while auth is still loading, so we
  // never flash drill chrome (or fire a Pro-only request) before the plan is known.
  const drillPlan = user?.plan?.startsWith('lifetime_') ? user.plan.replace('lifetime_', '') : (user?.plan ?? 'free');
  const canDrill = !authLoading && (drillPlan === 'pro' || drillPlan === 'elite');
  // A non-Pro user who followed a drill link gets redirected to the clean URL with this
  // flag in router state (see the redirect effect below) → we surface a dismissible Pro
  // upsell banner instead of silently dropping the drill intent.
  const drillUpsell = location.state?.drillUpsell ?? null;

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

  // When landing on the hub with ?concepts=..., auto-navigate to the first matching
  // accessible question so the user goes straight to the question page. (The ?drill=
  // hub redirect is handled separately below, off the backend drill result — not a
  // frontend re-match; see the drill-redirect effect.)
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


  // ── Resume entry (?resume=1) ────────────────────────────────────────────────
  // The landing "Resume" card links to /practice/<topic>?resume=1 instead of a
  // hard-coded question id, so it lands the user on their NEXT-UP question (the
  // SidebarNav "NEXT") rather than re-opening one they already solved. The catalog
  // (and thus next-up) isn't available on the landing page, so we resolve it here
  // once it loads. Crucially we use pickNextUpQuestionId (is_next only): if the
  // track has NO actionable next-up (every accessible question solved), we do NOT
  // fall back to a solved question — we strip ?resume= and stay on the hub, which
  // shows the completed state (Explore tracks / Unlock more).
  useEffect(() => {
    if (!isAtHub || loading || error || !catalog) return;
    const params = new URLSearchParams(location.search);
    if (!params.get('resume')) return;
    const targetId = pickNextUpQuestionId(catalog);
    if (targetId) {
      navigate(`${location.pathname}/questions/${targetId}`, { replace: true });
    } else {
      params.delete('resume');
      const qs = params.toString();
      navigate(`${location.pathname}${qs ? `?${qs}` : ''}`, { replace: true });
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

  // Reveal the active question's difficulty group. The sidebar's collapse state
  // otherwise keeps its initial easy-only view as you advance (AppShell does not
  // remount between questions in a topic), so on a Medium/Hard question the active
  // row sits inside a collapsed group and is never shown. Derive the active
  // question's difficulty from the URL + catalog and ensure that group is expanded.
  // Only expands — never force-collapses the others — so manual toggles are kept.
  const activeQuestionId = useMemo(() => {
    const m = location.pathname.match(/\/questions\/(\d+)/);
    return m ? Number(m[1]) : null;
  }, [location.pathname]);

  const activeDifficulty = useMemo(() => {
    if (activeQuestionId == null || !catalog?.groups) return null;
    const group = catalog.groups.find((g) =>
      g.questions?.some((q) => Number(q.id) === activeQuestionId)
    );
    return group?.difficulty ?? null;
  }, [activeQuestionId, catalog]);

  useEffect(() => {
    if (!activeDifficulty) return;
    setCollapsedByDiff((prev) =>
      prev[activeDifficulty] ? { ...prev, [activeDifficulty]: false } : prev
    );
  }, [activeQuestionId, activeDifficulty]);

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
  // Honor ?drill= only for Pro+; for Free/anonymous it's inert — they get the normal
  // practice question + catalog sidebar (no drill chrome, no Pro-only fetch, no shimmer).
  const rawDrillParam = new URLSearchParams(location.search).get('drill');
  const drillConcept = canDrill ? rawDrillParam : null;
  const focusMode = new URLSearchParams(location.search).get('focus') === '1';

  // Path data — fetched when ?path= is present
  const [pathData, setPathData] = useState(null);
  const refreshPathData = useCallback(() => {
    if (!pathSlug) { setPathData(null); return; }
    api.get(`/paths/${pathSlug}`)
      .then(r => setPathData(r.data))
      .catch(() => setPathData(null));
  }, [pathSlug]);
  useEffect(() => {
    refreshPathData();
  }, [refreshPathData]);

  // Drill data — fetched when ?drill= is present (Pro+ only); scopes the sidebar to one concept.
  const [drillData, setDrillData] = useState(null);
  const [drillLoading, setDrillLoading] = useState(false);
  useEffect(() => {
    if (!drillConcept) { setDrillData(null); setDrillLoading(false); return; }
    setDrillLoading(true);
    api.get('/practice/drill', { params: { track: topic, concept: drillConcept } })
      .then(r => setDrillData(r.data))
      .catch(() => setDrillData(null))
      .finally(() => setDrillLoading(false));
  }, [drillConcept, topic]);

  // On the hub with ?drill= (Pro+ → drillConcept is set; null/inert for everyone else),
  // redirect to the first drill question. The backend drill result is the single source
  // of truth for both membership (family-aware match — resolves hyphenated / non-substring
  // family names the catalog substring match can't) and order (unsolved-first), so we
  // navigate to questions[0] instead of re-deriving the match against the catalog. This is
  // the fix for hyphenated families (e.g. "Multi-table entity linking") stranding Pro/Elite
  // users on the hub.
  useEffect(() => {
    if (!isAtHub || !drillConcept) return;
    const questions = drillData?.questions ?? [];
    if (questions.length === 0) return; // not loaded yet, or concept has no practice questions
    navigate(
      `${location.pathname}/questions/${questions[0].id}?drill=${encodeURIComponent(drillConcept)}`,
      { replace: true },
    );
  }, [isAtHub, drillConcept, drillData, location.pathname, navigate]);

  // Non-Pro followed a drill link → strip the inert ?drill= (clean, shareable URL) and
  // flag the Pro upsell in router state, shown as a dismissible banner below the topbar.
  // (drillConcept is already null for them, so no drill chrome ever rendered.)
  useEffect(() => {
    if (authLoading || !rawDrillParam || canDrill) return;
    const params = new URLSearchParams(location.search);
    params.delete('drill');
    const qs = params.toString();
    navigate(location.pathname + (qs ? `?${qs}` : ''), { replace: true, state: { drillUpsell: rawDrillParam } });
  }, [authLoading, rawDrillParam, canDrill, location.pathname, location.search, navigate]);

  // Re-arm the (dismissible) upsell banner on each navigation, so a fresh drill link
  // shows it again even after a previous dismiss.
  useEffect(() => { setDrillUpsellDismissed(false); }, [location.key]);

  const modeLabel = pathData ? pathData.title
    : pathSlug ? `${meta.label} · Path`
    : drillConcept ? `Drilling: ${drillData?.concept ?? drillConcept}`
    : `${meta.label} · Challenge`;

  // Session goal tracking
  const [sessionGoal, setSessionGoal] = useState(() => {
    try { return Math.max(1, Math.min(20, parseInt(localStorage.getItem('session-goal') ?? '5', 10))); } catch { return 5; }
  });
  const totalSolvedSidebar = catalog?.groups?.reduce(
    (sum, g) => sum + g.questions.filter(q => q.state === 'solved').length, 0
  ) ?? 0;

  // Today's goal: global, day-scoped daily solve counter (event-driven, resets at local midnight).
  const [dailySolves, setDailySolves] = useState(() => getDailySolves());
  useEffect(() => {
    // Refresh on mount and whenever the count changes (same tab) or is updated from another tab.
    setDailySolves(getDailySolves());
    const handleSolvesChanged = () => setDailySolves(getDailySolves());
    window.addEventListener(DAILY_SOLVES_EVENT, handleSolvesChanged);
    window.addEventListener('storage', handleSolvesChanged);
    // Re-read on focus/visibility so a tab left open past midnight resets cleanly.
    window.addEventListener('focus', handleSolvesChanged);
    document.addEventListener('visibilitychange', handleSolvesChanged);
    return () => {
      window.removeEventListener(DAILY_SOLVES_EVENT, handleSolvesChanged);
      window.removeEventListener('storage', handleSolvesChanged);
      window.removeEventListener('focus', handleSolvesChanged);
      document.removeEventListener('visibilitychange', handleSolvesChanged);
    };
  }, []);

  const goalProgress = Math.min(1, sessionGoal > 0 ? dailySolves / sessionGoal : 0);
  const goalMet = dailySolves >= sessionGoal;

  const normalisedPlan = user?.plan?.startsWith('lifetime_') ? user.plan.replace('lifetime_', '') : (user?.plan ?? 'free');
  const showUpgradeControls = user && (normalisedPlan === 'free' || normalisedPlan === 'pro');
  const planPillClass = `shell-pill shell-pill-plan shell-pill-plan-${normalisedPlan}`;

  const planLabel = normalisedPlan === 'elite' ? 'Elite' : normalisedPlan === 'pro' ? 'Pro' : 'Free';
  const sidebarToggleNode = isMobile ? (
    <button
      className="btn btn-secondary sidebar-toggle"
      onClick={handleSidebarToggle}
      aria-label="Toggle question bank"
      aria-expanded={mobileOpen}
      aria-controls="sidebar"
    >
      <svg className="sidebar-toggle-icon" aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1" y="2" width="4" height="12" rx="1" fill="currentColor" opacity="0.85"/>
        <rect x="7" y="4" width="8" height="1.5" rx="0.75" fill="currentColor"/>
        <rect x="7" y="7.25" width="6" height="1.5" rx="0.75" fill="currentColor"/>
        <rect x="7" y="10.5" width="7" height="1.5" rx="0.75" fill="currentColor"/>
      </svg>
      <span className="sidebar-toggle-label">Questions</span>
    </button>
  ) : null;

  const modePillNode = !isAtHub ? (
    <span
      className={`shell-pill shell-pill-mode${(pathSlug || drillConcept) ? ' shell-pill-mode-path' : ''}`}
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

  const banner = (drillUpsell && !canDrill && !drillUpsellDismissed) ? (
    <DrillUpsellBanner onDismiss={() => setDrillUpsellDismissed(true)} />
  ) : upgradeSuccess ? (
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
        <aside id="sidebar" className={`sidebar ${mobileOpen ? 'sidebar-open' : ''} ${(pathSlug || drillConcept) ? 'sidebar--path-mode' : ''}`}>
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
          ) : drillConcept ? (
            <DrillSidebar
              drillData={drillData}
              drillLoading={drillLoading}
              drillConcept={drillConcept}
              topic={topic}
              meta={meta}
              currentId={location.pathname.match(/\/questions\/([^/?]+)/)?.[1]}
              onNavigate={handleNavigateFromSidebar}
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
              {/* Today's goal widget */}
              {user && (
                <div className={`session-goal-widget${goalMet ? ' session-goal-widget--met' : ''}`}>
                  <div className="session-goal-row">
                    <span className="session-goal-label">Today</span>
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
                      <span className="session-goal-count">{dailySolves}/{sessionGoal}</span>
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
                  <div className="session-goal-bar" role="progressbar" aria-valuenow={dailySolves} aria-valuemax={sessionGoal}>
                    <div className="session-goal-fill" style={{ width: `${goalProgress * 100}%` }} />
                  </div>
                  {goalMet && <p className="session-goal-met">Goal reached — nice work today!</p>}
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
                      ? 'Easy questions are free — upgrade for all medium and hard.'
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
              <Outlet context={{ refreshPathData }} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// ── Path sidebar panel ────────────────────────────────────────────────────────
function PathSidebar({ pathData, pathSlug, topic, meta, currentId, onNavigate, plan }) {
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
            <p className="path-sidebar-hint-text">Some questions are locked — the free tier covers easy. Medium and hard are part of Pro.</p>
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

// Dismissible Pro upsell shown below the topbar after a Free/anonymous user follows a
// drill link (AppShell redirects them to the clean URL + flags this). Concept drills
// stay Pro+; the banner explains why and offers the upgrade (UpgradeButton routes
// anonymous users through sign-in, Free users to checkout).
function DrillUpsellBanner({ onDismiss }) {
  return (
    <div className="app-banner app-banner-upsell" role="status">
      <span className="app-banner-upsell-copy">
        <strong>Concept drills are a Pro feature.</strong>{' '}
        Drill one weak concept at a time — your unsolved questions first.
      </span>
      <span className="app-banner-upsell-actions">
        <UpgradeButton tier="pro" source="drill_gate" compact label="Upgrade to Pro" />
        <button
          type="button"
          className="app-banner-dismiss"
          aria-label="Dismiss"
          onClick={onDismiss}
        >
          ✕
        </button>
      </span>
    </div>
  );
}

// Scoped sidebar for a concept drill (?drill=<concept>). Mirrors PathSidebar but
// sources its questions from GET /api/practice/drill instead of a curated path.
// Pro+ only, so every question is accessible — no locked-state handling needed.
export function DrillSidebar({ drillData, drillLoading, drillConcept, topic, meta, currentId, onNavigate }) {
  if (drillLoading) {
    return (
      <div className="path-sidebar-loading">
        <div className="path-sidebar-shimmer" />
        <div className="path-sidebar-shimmer path-sidebar-shimmer--short" />
      </div>
    );
  }
  if (!drillData) {
    // Fetch finished with no data (transient error). Don't shimmer forever — give a way out.
    return (
      <div className="path-sidebar-header">
        <div className="path-sidebar-title">Drill unavailable</div>
        <p className="path-sidebar-meta">Couldn't load this concept drill right now.</p>
        <Link to={`/practice/${topic}`} className="path-sidebar-back">← Back to {meta.label}</Link>
      </div>
    );
  }

  const questions = drillData.questions ?? [];
  const solvedCount = questions.filter(q => q.state === 'solved').length;
  const conceptParam = encodeURIComponent(drillConcept);

  return (
    <div className="path-sidebar path-sidebar--drill">
      <div className="path-sidebar-header">
        <span className="path-sidebar-kicker">Concept drill</span>
        <div className="path-sidebar-title">{drillData.concept}</div>
        <div className="path-sidebar-meta">
          <span className="path-sidebar-dot" style={{ background: meta.color }} />
          {meta.label} · {questions.length} question{questions.length === 1 ? '' : 's'}
        </div>
        <div className="path-sidebar-progress-bar">
          <div
            className="path-sidebar-progress-fill"
            style={{ width: `${questions.length > 0 ? (solvedCount / questions.length) * 100 : 0}%`, background: meta.color }}
          />
        </div>
        <span className="path-sidebar-progress-label">{solvedCount}/{questions.length} cleared</span>
      </div>

      <nav className="path-sidebar-list" aria-label="Drill questions">
        {questions.map((q, i) => {
          const isCurrent = String(q.id) === String(currentId);
          const isSolved = q.state === 'solved';
          const url = `/practice/${topic}/questions/${q.id}?drill=${conceptParam}`;

          return (
            <Link
              key={q.id}
              to={url}
              className={`path-sidebar-item${isCurrent ? ' path-sidebar-item--active' : ''}${isSolved ? ' path-sidebar-item--solved' : ''}`}
              aria-current={isCurrent ? 'page' : undefined}
              onClick={onNavigate}
            >
              <span className="path-sidebar-item-num">{i + 1}</span>
              <span className="path-sidebar-item-title">{q.title}</span>
              <span className="path-sidebar-item-state" aria-hidden="true">
                {isSolved ? '✓' : null}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="path-sidebar-footer">
        <Link to={`/practice/${topic}`} className="path-sidebar-exit">
          Exit drill → Practice
        </Link>
      </div>
    </div>
  );
}
