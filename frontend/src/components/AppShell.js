import { useEffect, useMemo, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import SidebarNav from './SidebarNav';
import api from '../api';
import { useCatalog } from '../catalogContext';
import { useAuth } from '../contexts/AuthContext';

function pickStartQuestionId(catalog) {
  const order = ['easy', 'medium', 'hard'];
  for (const diff of order) {
    const g = catalog.groups.find((x) => x.difficulty === diff);
    if (!g) continue;
    const next = g.questions.find((q) => q.is_next) ?? g.questions.find((q) => q.state !== 'locked');
    if (next) return next.id;
  }
  return null;
}

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

  const startQuestionId = useMemo(() => (catalog ? pickStartQuestionId(catalog) : null), [catalog]);

  // Track mobile breakpoint so aria-expanded reflects actual sidebar visibility.
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    setIsMobile(mq.matches);
    const handler = (e) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Close mobile drawer on Escape key.
  useEffect(() => {
    if (!mobileOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mobileOpen]);

  useEffect(() => {
    if (!loading && !error && catalog && location.pathname === '/practice' && startQuestionId) {
      navigate(`/practice/questions/${startQuestionId}`, { replace: true });
    }
  }, [loading, error, catalog, location.pathname, startQuestionId, navigate]);

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

  return (
    <div className={`app-shell ${desktopCollapsed ? 'sidebar-collapsed' : ''}`}>
      <header className="topbar app-topbar">
        <div className="topbar-inner app-topbar-inner">
          <button
            className="btn btn-secondary sidebar-toggle"
            onClick={handleSidebarToggle}
            aria-label="Toggle sidebar"
            aria-expanded={isMobile ? mobileOpen : !desktopCollapsed}
            aria-controls="sidebar"
          >
            ☰
          </button>
          <h1>SQL Interview Practice</h1>
          <Link className="back-link" to="/">
            Home
          </Link>
          {showUpgradeControls && (
            <div className="upgrade-actions">
              {user.plan === 'free' && (
                <button className="btn btn-primary" onClick={() => startCheckout('pro')} disabled={upgradePending}>
                  Upgrade to Pro
                </button>
              )}
              <button className="btn btn-secondary" onClick={() => startCheckout('elite')} disabled={upgradePending}>
                Upgrade to Elite
              </button>
            </div>
          )}
          {user && <span className="plan-pill">Plan: {user.plan}</span>}
          {catalog?.user_id && <span className="user-pill">Session: {catalog.user_id.slice(0, 8)}</span>}
        </div>
        {(upgradeError || upgradeSuccess) && (
          <div className={`app-banner ${upgradeError ? 'app-banner-error' : 'app-banner-success'}`}>
            {upgradeError || 'Upgrade confirmed. Your access is refreshing now.'}
          </div>
        )}
      </header>

      <div className="app-body">
        <aside id="sidebar" className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
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
        </aside>

        {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
