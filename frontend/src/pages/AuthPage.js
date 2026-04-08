import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../App';

// ─── Password validation ─────────────────────────────────────────────────────

function validatePassword(password) {
  if (password.length < 8) return 'Must be at least 8 characters.';
  if (!/[A-Z]/.test(password)) return 'Must include at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Must include at least one lowercase letter.';
  if (!/[0-9]/.test(password)) return 'Must include at least one number.';
  return null;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const VALID_MODES = ['signin', 'signup', 'magic', 'forgot'];

const MODE_META = {
  signin: { title: 'Sign in', subtitle: 'Pick up your practice session' },
  signup: { title: 'Create account', subtitle: 'Save progress and unlock more practice' },
  magic: { title: 'Magic link', subtitle: 'Get a one-time sign-in link by email' },
  forgot: { title: 'Reset password', subtitle: 'Recover access to your account' },
};

// ─── AuthPage component ───────────────────────────────────────────────────────

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const initialMode = VALID_MODES.includes(searchParams.get('mode'))
    ? searchParams.get('mode')
    : 'signin';

  const [mode, setMode] = useState(initialMode);
  const [fields, setFields] = useState({ email: '', name: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success'
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);

  const [passwordError, setPasswordError] = useState(null);

  const { login, register, requestMagicLink, user, logout } = useAuth();
  const navigate = useNavigate();
  const { cycleTheme, themeIcon, themeLabel } = useTheme();
  const firstFieldRef = useRef(null);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  function switchMode(next) {
    setMode(next);
    setError(null);
    setInfo(null);
    setPasswordError(null);
    setStatus('idle');
    // Move focus to first input on mode switch for keyboard users.
    requestAnimationFrame(() => firstFieldRef.current?.focus());
  }

  function handleChange(e) {
    setFields((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    if (error) setError(null);
    if (e.target.name === 'password' && passwordError) setPasswordError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setStatus('loading');

    try {
      if (mode === 'signin') {
        await login(fields.email, fields.password);
        navigate('/');
      } else if (mode === 'signup') {
        const complexityErr = validatePassword(fields.password);
        if (complexityErr) {
          setStatus('idle');
          setPasswordError(complexityErr);
          return;
        }
        await register(fields.email, fields.name, fields.password);
        navigate('/');
      } else if (mode === 'magic') {
        try {
          await requestMagicLink(fields.email);
          setStatus('success');
          setInfo('If an account exists for that address, a sign-in link is on its way.');
        } catch (err) {
          setStatus('success'); // always look like success to avoid enumeration
          setInfo(
            err?.response?.status === 501
              ? 'Magic link sign-in is not yet available. Please sign in with email and password.'
              : 'If an account exists for that address, a sign-in link is on its way.'
          );
        }
        return;
      }
    } catch (err) {
      setStatus('idle');
      const msg = err?.response?.data?.error;
      setError(msg || 'Something went wrong. Please try again.');
    }
  }

  const isLoading = status === 'loading';
  const isSuccess = status === 'success';
  const meta = MODE_META[mode];
  const showPasswordField = mode === 'signin' || mode === 'signup';
  const showNameField = mode === 'signup';

  return (
    <div className="auth-page">
      {/* ── Topbar ── */}
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
            {user && user.email ? (
              <div className="topbar-user-pill">
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {/* ── Centered card ── */}
      <main className="auth-main">
        <div className="auth-card" role="main">

          {/* Header */}
          <div className="auth-card-header">
            <h1 className="auth-card-title">{meta.title}</h1>
            <p className="auth-card-subtitle">{meta.subtitle}</p>
          </div>

          {/* Forgot password — static message, no submit */}
          {mode === 'forgot' && (
            <div className="auth-forgot-info">
              <p className="auth-forgot-message">
                Password reset by email isn't available yet.
                <br />
                To regain access, sign in with email and password, or create a new account.
              </p>
              <button
                type="button"
                className="btn btn-secondary auth-submit"
                onClick={() => switchMode('signin')}
              >
                Back to sign in
              </button>
            </div>
          )}

          {/* Global error */}
          {error && (
            <div className="auth-alert auth-alert-error" role="alert" aria-live="assertive">
              {error}
            </div>
          )}

          {/* Info / success message */}
          {info && (
            <div className="auth-alert auth-alert-info" role="status" aria-live="polite">
              {info}
            </div>
          )}

          {/* Form */}
          {!isSuccess && mode !== 'forgot' && (
            <form className="auth-form" onSubmit={handleSubmit} noValidate>

              {/* Name — signup only */}
              {showNameField && (
                <div className="auth-field">
                  <label className="auth-label" htmlFor="auth-name">Full name</label>
                  <input
                    ref={firstFieldRef}
                    id="auth-name"
                    name="name"
                    type="text"
                    className="auth-input"
                    value={fields.name}
                    onChange={handleChange}
                    autoComplete="name"
                    required
                    placeholder="Ada Lovelace"
                    aria-required="true"
                  />
                </div>
              )}

              {/* Email */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="auth-email">Email address</label>
                <input
                  ref={showNameField ? undefined : firstFieldRef}
                  id="auth-email"
                  name="email"
                  type="email"
                  className="auth-input"
                  value={fields.email}
                  onChange={handleChange}
                  autoComplete="email"
                  required
                  placeholder="you@example.com"
                  aria-required="true"
                />
              </div>

              {/* Password */}
              {showPasswordField && (
                <div className="auth-field">
                  <div className="auth-label-row">
                    <label className="auth-label" htmlFor="auth-password">Password</label>
                    {mode === 'signin' && (
                      <button
                        type="button"
                        className="auth-link-btn"
                        onClick={() => switchMode('forgot')}
                        tabIndex={0}
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="auth-password-wrap">
                    <input
                      id="auth-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      className="auth-input auth-input-password"
                      value={fields.password}
                      onChange={handleChange}
                      autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                      required
                      minLength={8}
                      placeholder={mode === 'signup' ? 'Min. 8 characters' : ''}
                      aria-required="true"
                    />
                    <button
                      type="button"
                      className="auth-eye-btn"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      tabIndex={0}
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
                  {mode === 'signup' && (
                    <p className={`auth-field-hint${passwordError ? ' auth-field-hint--error' : ''}`}>
                      {passwordError || 'Min 8 chars, uppercase, lowercase, and a number'}
                    </p>
                  )}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                className="btn btn-primary auth-submit"
                disabled={isLoading}
                aria-busy={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="auth-spinner" aria-hidden="true" />
                    {mode === 'signin' ? 'Signing in…' : mode === 'signup' ? 'Creating account…' : 'Sending link…'}
                  </>
                ) : (
                  <>
                    {mode === 'signin' && 'Sign in'}
                    {mode === 'signup' && 'Create account'}
                    {mode === 'magic'  && 'Send magic link'}
                  </>
                )}
              </button>
            </form>
          )}

          {/* Post-success actions */}
          {isSuccess && mode === 'magic' && (
            <div className="auth-post-success">
              <button
                type="button"
                className="btn btn-secondary auth-submit"
                onClick={() => switchMode('signin')}
              >
                Back to sign in
              </button>
            </div>
          )}

          {/* Footer links */}
          <div className="auth-footer">
            {(mode === 'signin' || mode === 'magic') && (
              <>
                <span className="auth-footer-text">Don't have an account?</span>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => switchMode('signup')}
                >
                  Create one
                </button>
              </>
            )}
            {mode === 'signup' && (
              <>
                <span className="auth-footer-text">Already have an account?</span>
                <button
                  type="button"
                  className="auth-link-btn"
                  onClick={() => switchMode('signin')}
                >
                  Sign in
                </button>
              </>
            )}
          </div>

          {/* Magic link shortcut */}
          {(mode === 'signin' || mode === 'signup') && (
            <div className="auth-magic-link-cta">
              <button
                type="button"
                className="auth-link-btn auth-link-subtle"
                onClick={() => switchMode('magic')}
              >
                Send me a magic link instead
              </button>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
