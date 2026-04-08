import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import { useTheme } from '../App';

function validatePassword(password) {
  if (password.length < 8) return 'Must be at least 8 characters.';
  if (!/[A-Z]/.test(password)) return 'Must include at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Must include at least one lowercase letter.';
  if (!/[0-9]/.test(password)) return 'Must include at least one number.';
  return null;
}

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();
  const { cycleTheme, themeIcon, themeLabel } = useTheme();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | loading | success | invalid
  const [error, setError] = useState(null);
  const [passwordError, setPasswordError] = useState(null);

  useEffect(() => {
    if (!token) setStatus('invalid');
  }, [token]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setPasswordError(null);

    const complexityErr = validatePassword(password);
    if (complexityErr) {
      setPasswordError(complexityErr);
      return;
    }
    if (password !== confirm) {
      setPasswordError('Passwords do not match.');
      return;
    }

    setStatus('loading');
    try {
      await api.post('/auth/reset-password', { token, password });
      setStatus('success');
    } catch (err) {
      setStatus('idle');
      const msg = err?.response?.data?.error;
      setError(msg || 'Something went wrong. Please try again.');
    }
  }

  return (
    <div className="auth-page">
      <header className="topbar landing-topbar">
        <div className="container topbar-inner landing-topbar-inner">
          <div className="landing-topbar-left">
            <Link className="landing-brand brand-wordmark" to="/">datanest</Link>
          </div>
          <div className="landing-topbar-right">
            <button className="theme-toggle" onClick={cycleTheme} aria-label={themeLabel} title={themeLabel}>
              {themeIcon}
            </button>
          </div>
        </div>
      </header>

      <main className="auth-main">
        <div className="auth-card" role="main">
          <div className="auth-card-header">
            <h1 className="auth-card-title">Set new password</h1>
            <p className="auth-card-subtitle">Choose a strong password for your account</p>
          </div>

          {status === 'invalid' && (
            <div className="auth-alert auth-alert-error" role="alert">
              This reset link is missing or invalid.{' '}
              <button type="button" className="auth-link-btn" onClick={() => navigate('/auth?mode=forgot')}>
                Request a new one
              </button>
            </div>
          )}

          {status === 'success' && (
            <>
              <div className="auth-alert auth-alert-info" role="status">
                Your password has been updated successfully.
              </div>
              <div className="auth-post-success">
                <button
                  type="button"
                  className="btn btn-primary auth-submit"
                  onClick={() => navigate('/auth')}
                >
                  Sign in
                </button>
              </div>
            </>
          )}

          {error && (
            <div className="auth-alert auth-alert-error" role="alert" aria-live="assertive">
              {error}{' '}
              {error.includes('expired') && (
                <button type="button" className="auth-link-btn" onClick={() => navigate('/auth?mode=forgot')}>
                  Request a new link
                </button>
              )}
            </div>
          )}

          {status !== 'invalid' && status !== 'success' && (
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              <div className="auth-field">
                <label className="auth-label" htmlFor="rp-password">New password</label>
                <div className="auth-password-wrap">
                  <input
                    id="rp-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input auth-input-password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setPasswordError(null); }}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    placeholder="Min. 8 characters"
                    aria-required="true"
                  />
                  <button
                    type="button"
                    className="auth-eye-btn"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clipRule="evenodd" />
                        <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                </div>
                <p className={`auth-field-hint${passwordError ? ' auth-field-hint--error' : ''}`}>
                  {passwordError || 'Min 8 chars, uppercase, lowercase, and a number'}
                </p>
              </div>

              <div className="auth-field">
                <label className="auth-label" htmlFor="rp-confirm">Confirm password</label>
                <input
                  id="rp-confirm"
                  name="confirm"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  value={confirm}
                  onChange={(e) => { setConfirm(e.target.value); setPasswordError(null); }}
                  autoComplete="new-password"
                  required
                  placeholder="Re-enter your password"
                  aria-required="true"
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary auth-submit"
                disabled={status === 'loading'}
                aria-busy={status === 'loading'}
              >
                {status === 'loading' ? (
                  <><span className="auth-spinner" aria-hidden="true" /> Updating…</>
                ) : 'Set new password'}
              </button>
            </form>
          )}

          <div className="auth-footer">
            <span className="auth-footer-text">Remember your password?</span>
            <button type="button" className="auth-link-btn" onClick={() => navigate('/auth')}>
              Sign in
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
