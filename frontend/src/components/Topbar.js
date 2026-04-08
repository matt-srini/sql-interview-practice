import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
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
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [practiceOpen, setPracticeOpen] = useState(false);
  const dropdownRef = useRef(null);
  const location = useLocation();

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

  function cycleTheme() {
    setTheme(t => t === 'system' ? 'light' : t === 'light' ? 'dark' : 'system');
  }
  const themeIcon = theme === 'system' ? '◐' : resolvedTheme === 'dark' ? '☀' : '☾';

  return (
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
                <div className="topbar-practice-label">Switch track</div>
                {TOPICS.map(t => (
                  <Link
                    key={t}
                    className="topbar-practice-item"
                    to={`/practice/${t}`}
                    onClick={() => setPracticeOpen(false)}
                  >
                    <span className="topbar-practice-dot" style={{ background: TRACK_META[t].color }} />
                    <span className="topbar-practice-name">{TRACK_META[t].label}</span>
                    <span className="topbar-practice-sub">{TRACK_META[t].tagline}</span>
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

          <button className="theme-toggle" onClick={cycleTheme} aria-label="Toggle theme">
            {themeIcon}
          </button>

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
  );
}
