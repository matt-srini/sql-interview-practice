import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META, useTopic } from '../contexts/TopicContext';
import TrackHubPage from '../pages/TrackHubPage';
import { useTheme } from '../App';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

export default function AppShell() {
  const { catalog, loading, error, refresh } = useCatalog();
  const { user, logout, refreshUser } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [practiceOpen, setPracticeOpen] = useState(false);
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

  // Close Practice dropdown on outside click or Escape
  useEffect(() => {
    if (!practiceOpen) return;
    const handleClick = (e) => {
      if (!e.target.closest('.app-practice-dropdown')) setPracticeOpen(false);
    };
    const handleKey = (e) => { if (e.key === 'Escape') setPracticeOpen(false); };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [practiceOpen]);

  // Close Practice dropdown on route change
  useEffect(() => { setPracticeOpen(false); }, [location.pathname]);

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

  const { meta } = useTopic();
  const pathSlug = new URLSearchParams(location.search).get('path');
  const modeLabel = pathSlug ? `${meta.label} · Path` : `${meta.label} · Challenge`;

  const showUpgradeControls = user && (user.plan === 'free' || user.plan === 'pro');

  const planLabel = user?.plan === 'elite' ? 'Elite' : user?.plan === 'pro' ? 'Pro' : 'Free';
  const planPillClass = `shell-pill shell-pill-plan shell-pill-plan-${user?.plan ?? 'free'}`;

  // Unlock nudge for free-plan users with locked questions
  const easyGroup = catalog?.groups?.find(g => g.difficulty === 'easy');
  const mediumGroup = catalog?.groups?.find(g => g.difficulty === 'medium');
  const lockedMediumCount = mediumGroup?.questions?.filter(q => q.state === 'locked').length ?? 0;
  const lockedHardCount = (catalog?.groups?.find(g => g.difficulty === 'hard'))?.questions?.filter(q => q.state === 'locked').length ?? 0;
  const showUnlockNudge = !!(user?.plan === 'free' && (lockedMediumCount > 0 || lockedHardCount > 0) && catalog);
  const totalSolvedSidebar = catalog?.groups?.reduce(
    (sum, g) => sum + g.questions.filter(q => q.state === 'solved').length, 0
  ) ?? 0;

  function cycleTheme() {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  }
  const themeIcon = theme === 'system' ? '◐' : resolvedTheme === 'dark' ? '☀' : '☾';
  const themeLabel = theme === 'system' ? 'Theme: system' : theme === 'light' ? 'Theme: light' : 'Theme: dark';

  return (
    <div className={`app-shell ${desktopCollapsed ? 'sidebar-collapsed' : ''}`}>
      <header className="topbar app-topbar">
        <div className="topbar-inner app-topbar-inner">
          <div className="app-topbar-brand">
            {isMobile && (
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
            )}
            <Link className="app-practice-home brand-wordmark" to="/">datanest</Link>
          </div>

          <div className="app-topbar-center">
            {!isAtHub && (
              <span
                className={`shell-pill shell-pill-mode${pathSlug ? ' shell-pill-mode-path' : ''}`}
                style={{ '--mode-dot-color': meta.color }}
                aria-label={modeLabel}
              >
                <span className="shell-pill-mode-dot" aria-hidden="true" />
                {modeLabel}
              </span>
            )}
          </div>

          <div className="app-topbar-actions">
            <div className="topbar-practice-dropdown app-practice-dropdown">
              <button
                className={`topbar-auth-link topbar-practice-trigger${practiceOpen ? ' topbar-practice-trigger--open' : ''}`}
                onClick={() => setPracticeOpen(v => !v)}
                aria-haspopup="true"
                aria-expanded={practiceOpen}
                type="button"
              >
                Practice <span className="topbar-practice-caret">{practiceOpen ? '▴' : '▾'}</span>
              </button>
              {practiceOpen && (
                <div className="topbar-practice-menu">
                  {TOPICS.map((track) => {
                    const trackMeta = TRACK_META[track];
                    return (
                      <NavLink
                        key={track}
                        className={({ isActive }) => `topbar-practice-item${isActive ? ' topbar-practice-item--active' : ''}`}
                        to={`/practice/${track}`}
                        onClick={() => setPracticeOpen(false)}
                      >
                        {trackMeta.label}
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
            <NavLink
              className={({ isActive }) => `topbar-auth-link${isActive ? ' topbar-auth-link--active' : ''}`}
              to="/mock"
            >
              Mock
            </NavLink>
            <NavLink
              className={({ isActive }) => `topbar-auth-link${isActive ? ' topbar-auth-link--active' : ''}`}
              to="/dashboard"
            >
              Dashboard
            </NavLink>
            <button
              className="theme-toggle"
              onClick={cycleTheme}
              aria-label={themeLabel}
              title={themeLabel}
            >
              {themeIcon}
            </button>
            <div className="topbar-sep" aria-hidden="true" />
            {user ? (
              <>
                {<span className={planPillClass}>{planLabel}</span>}
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>Sign out</button>
              </>
            ) : (
              <Link className="topbar-auth-link" to="/auth">Sign in</Link>
            )}
          </div>
        </div>
        {(upgradeError || upgradeSuccess) && (
          <div className={`app-banner ${upgradeError ? 'app-banner-error' : 'app-banner-success'}`}>
            {upgradeError || 'Upgrade confirmed. Your access is refreshing now.'}
          </div>
        )}
      </header>

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
          {loading && <div className="sidebar-loading">Loading…</div>}
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
              Questions unlock as you solve them — medium opens after 10 easy solves, hard after 10 medium. The sequence builds real competence.
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

        {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}

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
