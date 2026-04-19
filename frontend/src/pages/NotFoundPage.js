import { Link } from 'react-router-dom';
import { useTheme } from '../App';
import { useAuth } from '../contexts/AuthContext';

export default function NotFoundPage() {
  const { cycleTheme, themeIcon, themeLabel } = useTheme();
  const { user, logout } = useAuth();

  return (
    <div className="auth-page">
      {/* Topbar — matches all standalone pages */}
      <header className="topbar landing-topbar">
        <div className="container topbar-inner landing-topbar-inner">
          <div className="landing-topbar-left">
            <Link className="landing-brand brand-wordmark" to="/">datanest</Link>
          </div>
          <div className="landing-topbar-right">
            <button
              className="theme-toggle"
              onClick={cycleTheme}
              aria-label={themeLabel}
              title={themeLabel}
            >
              {themeIcon}
            </button>
            {user?.email ? (
              <div className="topbar-user-pill">
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>
                  Sign out
                </button>
              </div>
            ) : (
              <Link to="/auth" className="btn btn-secondary btn-sm">Sign in</Link>
            )}
          </div>
        </div>
      </header>

      <main className="auth-main">
        <div className="auth-card not-found-card" role="main">
          <div className="not-found-code" aria-hidden="true">404</div>
          <h1 className="auth-card-title">Page not found</h1>
          <p className="auth-card-subtitle" style={{ marginTop: '0.5rem' }}>
            This page doesn't exist. You may have followed a broken link or mistyped the URL.
          </p>
          <div className="not-found-actions">
            <Link to="/" className="btn btn-primary">
              Go to home
            </Link>
            <Link to="/practice/sql" className="btn btn-secondary">
              Start practising
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
