import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackHubPage from '../pages/TrackHubPage';
import { useTheme } from '../App';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

export default function AppShell() {
  const { catalog, loading, error, refresh } = useCatalog();
  const { user, refreshUser } = useAuth();
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

  const showUpgradeControls = user && (user.plan === 'free' || user.plan === 'pro');
  const sessionId = catalog?.user_id ? catalog.user_id.slice(0, 8) : null;

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

            <div className="app-title-group">
              <div className="app-title-row app-title-row-nav">
                <Link className="app-practice-home brand-wordmark" to="/">datanest</Link>
                <div className="app-practice-dropdown">
                  <button
                    className={`app-track-link app-practice-dropdown-trigger${practiceOpen ? ' active' : ''}`}
                    onClick={() => setPracticeOpen(v => !v)}
                    aria-haspopup="true"
                    aria-expanded={practiceOpen}
                  >
                    Practice <span className="app-practice-dropdown-caret">{practiceOpen ? '▴' : '▾'}</span>
                  </button>
                  {practiceOpen && (
                    <div className="app-practice-dropdown-menu">
                      <div className="app-practice-dropdown-label">Switch track</div>
                      {TOPICS.map((track) => {
                        const trackMeta = TRACK_META[track];
                        return (
                          <NavLink
                            key={track}
                            className={({ isActive }) => `app-practice-dropdown-item${isActive ? ' active' : ''}`}
                            to={`/practice/${track}`}
                          >
                            <span className="app-practice-dropdown-dot" style={{ background: trackMeta.color }} />
                            <span className="app-practice-dropdown-name">{trackMeta.label}</span>
                            <span className="app-practice-dropdown-desc">{trackMeta.tagline}</span>
                          </NavLink>
                        );
                      })}
                    </div>
                  )}
                </div>
                <nav className="app-track-nav" aria-label="Practice tracks">
                  <NavLink
                    className={({ isActive }) =>
                      `app-track-link ${isActive ? 'app-track-link-active' : ''}`
                    }
                    to="/mock"
                  >
                    Mock
                  </NavLink>
                </nav>
              </div>
            </div>
          </div>

          <div className="app-topbar-actions">
            <button
              className="theme-toggle"
              onClick={cycleTheme}
              aria-label={themeLabel}
              title={themeLabel}
            >
              {themeIcon}
            </button>
            {sessionId && (
              <div className="app-context app-context-secondary">
                {sessionId && <span className="shell-pill shell-pill-session">Session {sessionId}</span>}
              </div>
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
            />
          )}
          {showUpgradeControls && (
            <div className="sidebar-upgrade-panel">
              <span className="upgrade-panel-label">
                {user.plan === 'free' ? 'Expand question access' : 'Unlock the full challenge track'}
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
