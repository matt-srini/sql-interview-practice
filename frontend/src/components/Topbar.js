import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { TRACK_SLUGS } from '../trackRegistry';
import { useTheme } from '../App';

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
 */
export default function Topbar({
  active = null,
  variant = 'landing',
  leftSlot = null,
  centerSlot = null,
  userExtras = null,
  belowTopbar = null,
}) {
  const { user, logout } = useAuth();
  const { cycleTheme, themeIcon, themeLabel, isDark } = useTheme();
  const [practiceOpen, setPracticeOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [resendStatus, setResendStatus] = useState('idle'); // 'idle' | 'sending' | 'sent'
  const dropdownRef = useRef(null);
  const mobileMenuRef = useRef(null);
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

  // Close dropdowns on route change
  useEffect(() => {
    setPracticeOpen(false);
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Close practice dropdown on outside click or Escape
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

  // Close mobile menu on outside click or Escape
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const onMouseDown = (e) => {
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(e.target)) {
        setMobileMenuOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setMobileMenuOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [mobileMenuOpen]);

  // Layout classes per variant
  const headerClass = `topbar ${isApp ? 'app-topbar' : 'landing-topbar'}`;
  const innerClass = isApp
    ? 'topbar-inner app-topbar-inner'
    : 'container topbar-inner landing-topbar-inner';
  const brandRegionClass = isApp ? 'app-topbar-brand' : 'landing-topbar-left';
  const brandLinkClass = `${isApp ? 'app-practice-home ' : ''}brand-wordmark`;
  const actionsClass = isApp ? 'app-topbar-actions' : 'landing-topbar-right';
  const practiceDropdownClass = `topbar-practice-dropdown${isApp ? ' app-practice-dropdown' : ''}`;

  const handleBrandClick = (event) => {
    if (location.pathname !== '/') return;
    event.preventDefault();
    window.history.replaceState(null, '', '/');
    window.scrollTo({ top: 0, behavior: 'auto' });
  };

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
            <Link className={brandLinkClass} to="/" onClick={handleBrandClick}>
              <div className="brand-lockup">
                <img
                  src={isDark ? '/branding/mark-reverse-no-bg.svg' : '/branding/mark-no-bg.svg'}
                  alt=""
                  aria-hidden="true"
                  className="brand-mark-img"
                />
                <span className="brand-wordmark-text" aria-hidden="true">
                  <span className="brand-data">data</span><span className="brand-think">think</span>
                </span>
              </div>
            </Link>
          </div>

          {/* Center region — app variant only */}
          {isApp && <div className="app-topbar-center">{centerSlot}</div>}

          {/* Actions region — desktop */}
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
                      {TRACK_SLUGS.map((t) => (
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
                      <div className="topbar-practice-menu-divider" />
                      <NavLink
                        className={({ isActive }) =>
                          `topbar-practice-item topbar-practice-item--secondary${isActive ? ' topbar-practice-item--active' : ''}`
                        }
                        to="/sample"
                        onClick={() => setPracticeOpen(false)}
                      >
                        <span className="topbar-practice-item-glyph" aria-hidden="true">★</span>
                        Try a sample
                      </NavLink>
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
                <NavLink
                  to="/account"
                  className={({ isActive }) =>
                    `topbar-auth-link${isActive ? ' topbar-auth-link--active' : ''}`
                  }
                >
                  Account
                </NavLink>
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

          {/* Hamburger — mobile only (landing ≤640px, app ≤900px) */}
          {!isMinimal && (
            <div className="topbar-mobile-actions" ref={mobileMenuRef}>
              <button
                className="theme-toggle topbar-mobile-theme"
                onClick={cycleTheme}
                aria-label={themeLabel}
                title={themeLabel}
              >
                {themeIcon}
              </button>
              <button
                className={`topbar-hamburger${mobileMenuOpen ? ' topbar-hamburger--open' : ''}`}
                onClick={() => setMobileMenuOpen((v) => !v)}
                aria-label="Toggle navigation menu"
                aria-expanded={mobileMenuOpen}
                type="button"
              >
                <span /><span /><span />
              </button>

              {mobileMenuOpen && (
                <div className="topbar-mobile-menu">
                  {showNav && (
                    <>
                      <div className="topbar-mobile-section-label">Practice</div>
                      {TRACK_SLUGS.map((t) => (
                        <NavLink
                          key={t}
                          className={({ isActive }) =>
                            `topbar-mobile-item${isActive ? ' topbar-mobile-item--active' : ''}`
                          }
                          to={`/practice/${t}`}
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          <span
                            className="topbar-practice-item-dot"
                            style={{ background: TRACK_META[t].color }}
                          />
                          {TRACK_META[t].label}
                        </NavLink>
                      ))}
                      <NavLink
                        className={({ isActive }) =>
                          `topbar-mobile-item topbar-mobile-item--secondary${isActive ? ' topbar-mobile-item--active' : ''}`
                        }
                        to="/sample"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        <span className="topbar-practice-item-glyph" aria-hidden="true">★</span>
                        Try a sample
                      </NavLink>
                      <div className="topbar-mobile-divider" />
                      <NavLink
                        to="/mock"
                        className={({ isActive }) =>
                          `topbar-mobile-item${isActive || active === 'mock' ? ' topbar-mobile-item--active' : ''}`
                        }
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Mock interview
                      </NavLink>
                      <NavLink
                        to="/dashboard"
                        className={({ isActive }) =>
                          `topbar-mobile-item${isActive || active === 'dashboard' ? ' topbar-mobile-item--active' : ''}`
                        }
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Dashboard
                      </NavLink>
                      <div className="topbar-mobile-divider" />
                    </>
                  )}
                  {user && user.email ? (
                    <>
                      <NavLink
                        to="/account"
                        className={({ isActive }) =>
                          `topbar-mobile-item${isActive ? ' topbar-mobile-item--active' : ''}`
                        }
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Account
                      </NavLink>
                      <button
                        type="button"
                        className="topbar-mobile-item topbar-mobile-signout"
                        onClick={() => { setMobileMenuOpen(false); logout(); }}
                      >
                        Sign out
                      </button>
                    </>
                  ) : (
                    showNav && (
                      <Link
                        className="topbar-mobile-item"
                        to="/auth"
                        state={{ from: location.pathname }}
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Sign in
                      </Link>
                    )
                  )}
                </div>
              )}
            </div>
          )}
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
