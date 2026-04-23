import { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import Topbar from './Topbar';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';
import { useTopic } from '../contexts/TopicContext';
import TrackHubPage from '../pages/TrackHubPage';

export default function AppShell() {
  const { catalog, loading, error, refresh } = useCatalog();
  const { user, refreshUser } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [collapsedByDiff, setCollapsedByDiff] = useState({ easy: false, medium: true, hard: true });
  const [upgradePending, setUpgradePending] = useState(false);
  const [upgradeError, setUpgradeError] = useState('');
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

  // Only auto-navigate to first question when the user lands on the old /practice path
  // For the new /:topic paths we show TrackHubPage instead
  useEffect(() => {
    // No auto-redirect needed for the new topic-aware routing
  }, [loading, error, catalog, location.pathname, navigate]);

  useEffect(() => {
    if (!location.search.includes('upgraded=true')) return;
    setUpgradeSuccess(true);
    setUpgradeError('');
    refreshUser().catch(() => {});
    refresh().catch(() => {});
    navigate({ pathname: location.pathname }, { replace: true });
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

  async function startCheckout(plan) {
    setUpgradePending(true);
    setUpgradeError('');
    try {
      const response = await api.post('/stripe/create-checkout', { plan });
      window.location.assign(response.data.checkout_url);
    } catch (err) {
      const message = err?.response?.data?.error || 'Unable to start checkout right now.';
      setUpgradeError(message);
      setUpgradePending(false);
    }
  }

  const { topic, meta } = useTopic();
  const pathSlug = new URLSearchParams(location.search).get('path');
  const focusMode = new URLSearchParams(location.search).get('focus') === '1';
  const modeLabel = pathSlug ? `${meta.label} · Path` : `${meta.label} · Challenge`;

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
    pyspark: 'Medium unlocks at 12, 20, and 30 easy solves. Hard unlocks at 15 and 22 medium solves (capped at 10 hard).',
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

  const banner = (upgradeError || upgradeSuccess) ? (
    <div className={`app-banner ${upgradeError ? 'app-banner-error' : 'app-banner-success'}`}>
      {upgradeError || 'Upgrade confirmed. Your access is refreshing now.'}
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
        <aside id="sidebar" className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
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
              <span className="upgrade-panel-label">
                {user.plan === 'free' && totalSolvedSidebar >= 10
                  ? `${totalSolvedSidebar} solved — upgrade for instant access to every question.`
                  : user.plan === 'free' && totalSolvedSidebar > 0
                  ? `${totalSolvedSidebar} question${totalSolvedSidebar !== 1 ? 's' : ''} down. Upgrade to unlock the full track.`
                  : user.plan === 'free'
                  ? 'Questions unlock as you solve — or get full access instantly.'
                  : 'Unlock the full challenge track'}
              </span>
              <div className="upgrade-actions">
                {user.plan === 'free' && (
                  <button className="btn btn-secondary btn-compact" onClick={() => startCheckout('pro')} disabled={upgradePending}>
                    Unlock Pro
                  </button>
                )}
                <button className="btn btn-primary btn-compact" onClick={() => startCheckout('elite')} disabled={upgradePending}>
                  {user.plan === 'free' ? 'Unlock Elite' : 'Upgrade to Elite'}
                </button>
              </div>
            </div>
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
          {isAtHub ? <TrackHubPage /> : <Outlet />}
        </main>
      </div>
    </div>
  );
}
