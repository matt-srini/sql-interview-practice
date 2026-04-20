import { Link } from 'react-router-dom';
import Topbar from '../components/Topbar';
import { useAuth } from '../contexts/AuthContext';

export default function NotFoundPage() {
  const { user } = useAuth();

  return (
    <div className="auth-page">
      <Topbar variant="minimal" />

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
            {user ? (
              <Link to="/practice/sql" className="btn btn-secondary">
                Start practising
              </Link>
            ) : (
              <Link to="/auth" className="btn btn-secondary">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
