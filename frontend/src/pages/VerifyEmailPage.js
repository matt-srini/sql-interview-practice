import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import Topbar from '../components/Topbar';
import { useAuth } from '../contexts/AuthContext';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const [status, setStatus] = useState('loading'); // loading | success | error

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }
    api
      .post('/auth/verify-email', { token })
      .then(async () => {
        await refreshUser();
        setStatus('success');
      })
      .catch(() => setStatus('error'));
  }, [token, refreshUser]);

  return (
    <div className="auth-page">
      <Topbar variant="minimal" />

      <main className="auth-main">
        <div className="auth-card" role="main">
          <div className="auth-card-header">
            <h1 className="auth-card-title">Email verification</h1>
          </div>

          {status === 'loading' && (
            <div className="auth-alert auth-alert-info" role="status">
              Verifying your email address…
            </div>
          )}

          {status === 'success' && (
            <>
              <div className="auth-alert auth-alert-info" role="status">
                Your email has been verified. You're all set!
              </div>
              <div className="auth-post-success">
                <button
                  type="button"
                  className="btn btn-primary auth-submit"
                  onClick={() => navigate('/dashboard')}
                >
                  Go to dashboard
                </button>
              </div>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="auth-alert auth-alert-error" role="alert">
                This verification link is invalid or has expired.
              </div>
              <div className="auth-post-success">
                <button
                  type="button"
                  className="btn btn-secondary auth-submit"
                  onClick={() => navigate('/')}
                >
                  Go to practice
                </button>
              </div>
            </>
          )}

          <div className="auth-footer">
            <span className="auth-footer-text">Need a new link?</span>
            <button type="button" className="auth-link-btn" onClick={() => navigate('/auth')}>
              Sign in to resend
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
