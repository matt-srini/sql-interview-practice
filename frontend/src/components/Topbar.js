import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { useTheme } from '../App';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

/**
 * Shared top navigation bar used by all standalone pages.
 *
 * Props:
 *   active  — 'mock' | 'dashboard' | null   highlights the matching nav link
 */
export default function Topbar({ active }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [practiceOpen, setPracticeOpen] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [resendStatus, setResendStatus] = useState('idle'); // 'idle' | 'sending' | 'sent'
  const dropdownRef = useRef(null);
  const location = useLocation();

  const showVerifyBanner = !bannerDismissed && user?.email && user?.email_verified === false;

  async function handleResend() {
    setResendStatus('sending');
    try {
      await api.post('/auth/resend-verification');
    } catch {
      // best-effort
    }
    setResendStatus('sent');
  }

  // Close when navigating away
  useEffect(() => { setPracticeOpen(false); }, [location.pathname]);

  // Close on outside click or Escape
  useEffect(() => {
    if (!practiceOpen) return;
    const onMouseDown = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setPracticeOpen(false);
      }
    };
    const onKey = (e) => { if (e.key === 'Escape') setPracticeOpen(false); };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [practiceOpen]);

  const isDark = theme === 'dark';
  function toggleTheme() { setTheme(isDark ? 'light' : 'dark'); }
  const themeIcon = isDark ? '☀' : '☾';

  return (
    <>
    <header className="topbar landing-topbar">
      <div className="container topbar-inner landing-topbar-inner">
        <div className="landing-topbar-left">
          <Link className="brand-wordmark" to="/">datanest</Link>
        </div>
        <nav className="landing-topbar-right" aria-label="Main navigation">
          {/* Practice dropdown */}
          <div className="topbar-practice-dropdown" ref={dropdownRef}>
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
                {TOPICS.map(t => (
                  <Link
                    key={t}
                    className="topbar-practice-item"
                    to={`/practice/${t}`}
                    onClick={() => setPracticeOpen(false)}
                  >
                    {TRACK_META[t].label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <Link
            className={`topbar-auth-link${active === 'mock' ? ' topbar-auth-link--active' : ''}`}
            to="/mock"
          >
            Mock
          </Link>
          <Link
            className={`topbar-auth-link${active === 'dashboard' ? ' topbar-auth-link--active' : ''}`}
            to="/dashboard"
          >
            Dashboard
          </Link>

          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle dark mode">
            {themeIcon}
          </button>
          <div className="topbar-sep" aria-hidden="true" />

          {user ? (
            <>
              <span className="topbar-user-name">{user.name || user.email}</span>
              <button type="button" className="topbar-signout-btn" onClick={logout}>Sign out</button>
            </>
          ) : (
            <Link className="topbar-auth-link" to="/auth">Sign in</Link>
          )}
        </nav>
      </div>
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
          {resendStatus === 'sent' ? 'Email sent!' : resendStatus === 'sending' ? 'Sending…' : 'Resend email'}
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
