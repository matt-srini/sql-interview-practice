import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { useTheme } from '../App';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

/**
 * Shared top navigation bar used by every page.
 *
 * Variants:
 *   - 'landing' (default) — container-bounded shell used on Landing / Mock /
 *     Dashboard / Learning paths. Full nav.
 *   - 'app' — full-bleed workspace chrome used inside the practice shell.
 *     Has a center slot for the mode pill, extras slot for plan pill, and
 *     a below-topbar slot for upgrade banners.
 *   - 'minimal' — brand + theme toggle + user pill only. Used on the
 *     auth / verify / reset / 404 pages where the extra nav is distracting.
 *
 * Props:
 *   active          — 'mock' | 'dashboard' | null   force-highlight a nav link
 *                                                   (NavLink auto-detection is
 *                                                   the primary mechanism; this
 *                                                   is a fallback for callers
 *                                                   using the legacy API)
 *   variant         — 'landing' | 'app' | 'minimal' (default 'landing')
 *   leftSlot        — ReactNode rendered after the brand (e.g. mobile sidebar
 *                     toggle)
 *   centerSlot      — ReactNode rendered in the center region (only used
 *                     when variant='app')
 *   userExtras      — ReactNode rendered before the user name (e.g. plan pill)
 *   belowTopbar     — ReactNode rendered under the topbar (e.g. upgrade banner)
 *   showPricingLink — show a Pricing anchor (logged-out visitors only)
 */
export default function Topbar({
  active = null,
  variant = 'landing',
  leftSlot = null,
  centerSlot = null,
  userExtras = null,
  belowTopbar = null,
  showPricingLink = false,
}) {
  const { user, logout } = useAuth();
  const { cycleTheme, themeIcon, themeLabel } = useTheme();
  const [practiceOpen, setPracticeOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [resendStatus, setResendStatus] = useState('idle'); // 'idle' | 'sending' | 'sent'
  const dropdownRef = useRef(null);
  const location = useLocation();

  const showVerifyBanner = !bannerDismissed && user?.email && user?.email_verified === false;

  const isApp = variant === 'app';
  const isMinimal = variant === 'minimal';
  const showNav = !isMinimal;

  async function handleResend() {
    setResendStatus('sending');
    try {
      await api.post('/auth/resend-verification');
    } catch {
      // best-effort
    }
    setResendStatus('sent');
  }

  // Close dropdown on route change
  useEffect(() => {
    setPracticeOpen(false);
  }, [location.pathname]);

  // Close dropdown on outside click or Escape
  useEffect(() => {
    if (!practiceOpen) return;
    const onMouseDown = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setPracticeOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setPracticeOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [practiceOpen]);

  // Layout classes per variant
  const headerClass = `topbar ${isApp ? 'app-topbar' : 'landing-topbar'}`;
  const innerClass = isApp
    ? 'topbar-inner app-topbar-inner'
    : 'container topbar-inner landing-topbar-inner';
  const brandRegionClass = isApp ? 'app-topbar-brand' : 'landing-topbar-left';
  const brandLinkClass = `${isApp ? 'app-practice-home ' : ''}brand-wordmark`;
  const actionsClass = isApp ? 'app-topbar-actions' : 'landing-topbar-right';
  const practiceDropdownClass = `topbar-practice-dropdown${isApp ? ' app-practice-dropdown' : ''}`;

  // Pricing anchor — stay on page if we're already on the landing page
  const pricingHref =
    location.pathname === '/' ? '#landing-pricing' : '/#landing-pricing';

  // Show separator only when we have something on both sides of it
  const hasRightOfSep = !!userExtras || !!user || (!user && showNav && !isMinimal);
  const showSep = (showNav || !!user) && hasRightOfSep;

  return (
    <>
      <header className={headerClass}>
        <div className={innerClass}>
          {/* Brand region */}
          <div className={brandRegionClass}>
            {leftSlot}
            <Link className={brandLinkClass} to="/">
              <span className="brand-data">data</span><span className="brand-think">think</span>
            </Link>
          </div>

          {/* Center region — app variant only */}
          {isApp && <div className="app-topbar-center">{centerSlot}</div>}

          {/* Actions region */}
          <nav className={actionsClass} aria-label="Main navigation">
            {showNav && (
              <>
                <div className={practiceDropdownClass} ref={dropdownRef}>
                  <button
                    className={`topbar-auth-link topbar-practice-trigger${practiceOpen ? ' topbar-practice-trigger--open' : ''}${location.pathname.startsWith('/practice') ? ' topbar-auth-link--active' : ''}`}
                    onClick={() => setPracticeOpen((v) => !v)}
                    aria-haspopup="true"
                    aria-expanded={practiceOpen}
                    type="button"
                  >
                    Practice{' '}
                    <span className="topbar-practice-caret">
                      {practiceOpen ? '▴' : '▾'}
                    </span>
                  </button>
                  {practiceOpen && (
                    <div className="topbar-practice-menu">
                      <div className="topbar-practice-menu-header">Tracks</div>
                      {TOPICS.map((t) => (
                        <NavLink
                          key={t}
                          className={({ isActive }) =>
                            `topbar-practice-item${isActive ? ' topbar-practice-item--active' : ''}`
                          }
                          to={`/practice/${t}`}
                          onClick={() => setPracticeOpen(false)}
                        >
                          <span
                            className="topbar-practice-item-dot"
                            style={{ background: TRACK_META[t].color }}
                          />
                          {TRACK_META[t].label}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>

                <NavLink
                  to="/mock"
                  className={({ isActive }) =>
                    `topbar-auth-link${isActive || active === 'mock' ? ' topbar-auth-link--active' : ''}`
                  }
                >
                  Mock
                </NavLink>
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) =>
                    `topbar-auth-link${isActive || active === 'dashboard' ? ' topbar-auth-link--active' : ''}`
                  }
                >
                  Dashboard
                </NavLink>

                {showPricingLink && !user && (
                  <a className="topbar-auth-link" href={pricingHref}>
                    Pricing
                  </a>
                )}
              </>
            )}

            <button
              className="theme-toggle"
              onClick={cycleTheme}
              aria-label={themeLabel}
              title={themeLabel}
            >
              {themeIcon}
            </button>

            {showSep && <div className="topbar-sep" aria-hidden="true" />}

            {userExtras}

            {user && user.email ? (
              <>
                <span className="topbar-user-name">
                  {user.name || user.email}
                </span>
                <button
                  type="button"
                  className="topbar-signout-btn"
                  onClick={logout}
                >
                  Sign out
                </button>
              </>
            ) : (
              showNav && (
                <Link className="topbar-auth-link" to="/auth" state={{ from: location.pathname }}>
                  Sign in
                </Link>
              )
            )}
          </nav>
        </div>
        {belowTopbar}
      </header>
      {showVerifyBanner && (
        <div className="verify-email-banner" role="alert">
          <span className="verify-email-banner__text">
            Please verify your email address to access all features.
          </span>
          <button
            type="button"
            className="verify-email-banner__action"
            disabled={resendStatus !== 'idle'}
            onClick={handleResend}
          >
            {resendStatus === 'sent'
              ? 'Email sent!'
              : resendStatus === 'sending'
              ? 'Sending…'
              : 'Resend email'}
          </button>
          <button
            type="button"
            className="verify-email-banner__dismiss"
            aria-label="Dismiss"
            onClick={() => setBannerDismissed(true)}
          >
            ✕
          </button>
        </div>
      )}
    </>
  );
}
