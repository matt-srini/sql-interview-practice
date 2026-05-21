import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import Topbar from '../components/Topbar';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../App';

// ─── Password validation ─────────────────────────────────────────────────────

function validatePassword(password) {
  if (password.length < 8) return 'Must be at least 8 characters.';
  if (!/[A-Z]/.test(password)) return 'Must include at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Must include at least one lowercase letter.';
  if (!/[0-9]/.test(password)) return 'Must include at least one number.';
  return null;
}

// ─── SVG icons ───────────────────────────────────────────────────────────────

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}

function GithubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

// ─── Constants ───────────────────────────────────────────────────────────────

const VALID_MODES = ['signin', 'signup', 'magic', 'forgot'];

async function resendVerification() {
  try {
    await api.post('/auth/resend-verification');
  } catch {
    // Best-effort; ignore errors
  }
}

const MODE_META = {
  signin: { title: 'Sign in', subtitle: 'Pick up your practice session' },
  signup: { title: 'Create account', subtitle: 'Save progress and unlock more practice' },
  magic: { title: 'Magic link', subtitle: 'Get a one-time sign-in link by email' },
  forgot: { title: 'Reset password', subtitle: 'We\'ll send a reset link to your email' },
};

// ─── AuthPage component ───────────────────────────────────────────────────────

export default function AuthPage() {
  const [searchParams] = useSearchParams();
  const initialMode = VALID_MODES.includes(searchParams.get('mode'))
    ? searchParams.get('mode')
    : 'signin';

  const [mode, setMode] = useState(initialMode);
  const [fields, setFields] = useState({ email: '', name: '', password: '', passwordConfirm: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success'
  const [error, setError] = useState(null);
  const [info, setInfo] = useState(null);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordConfirmError, setPasswordConfirmError] = useState(null);
  const [signupEmail, setSignupEmail] = useState('');
  const [resendStatus, setResendStatus] = useState('idle'); // 'idle' | 'sending' | 'sent'
  const [oauthProviders, setOauthProviders] = useState(null); // null = loading
  const [devMagicLink, setDevMagicLink] = useState(null);

  const { login, register, requestMagicLink, user: _authUser } = useAuth();
  const { notify } = useToast();

  // Pre-fill email/name when a logged-in OAuth user visits signup to add a password
  useEffect(() => {
    if (mode === 'signup' && _authUser?.email) {
      setFields((prev) => ({
        ...prev,
        email: prev.email || _authUser.email,
        name: prev.name || _authUser.name || '',
      }));
    }
  }, [mode, _authUser]);

  // Show error from OAuth redirect (e.g. ?error=...)
  useEffect(() => {
    const oauthError = searchParams.get('error');
    if (oauthError) setError(oauthError);
  }, [searchParams]);
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = location.state?.from || null;
  const upgradeTier = location.state?.upgradeTier || null;
  const firstFieldRef = useRef(null);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    let active = true;
    api
      .get('/config')
      .then((res) => {
        if (!active) return;
        const providers = Array.isArray(res?.data?.oauth_providers) ? res.data.oauth_providers : [];
        setOauthProviders(providers);
      })
      .catch(() => {
        if (!active) return;
        setOauthProviders([]);
      });
    return () => {
      active = false;
    };
  }, []);

  function switchMode(next) {
    setMode(next);
    setError(null);
    setInfo(null);
    setPasswordError(null);
    setPasswordConfirmError(null);
    setDevMagicLink(null);
    setStatus('idle');
    requestAnimationFrame(() => firstFieldRef.current?.focus());
  }

  async function handleOAuth(provider) {
    setError(null);
    setInfo(null);
    // OAuth does a full-page redirect — React Router state is lost.
    // Persist any upgrade intent in sessionStorage so AppRoutes can
    // consume it once the user lands back after the OAuth callback.
    if (upgradeTier) {
      sessionStorage.setItem('pendingUpgrade', JSON.stringify({
        tier: upgradeTier,
        returnTo: returnTo || '/dashboard',
      }));
    }
    try {
      const { data } = await api.get(`/auth/oauth/${provider}/authorize`);
      if (!data?.url) {
        sessionStorage.removeItem('pendingUpgrade');
        setError('OAuth provider is unavailable right now. Please try email sign-in.');
        return;
      }
      window.location.href = data.url;
    } catch (err) {
      sessionStorage.removeItem('pendingUpgrade');
      const msg = err?.response?.data?.error;
      setError(msg || 'Could not start OAuth sign-in. Please try again.');
    }
  }

  function handleChange(e) {
    setFields((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    if (error) setError(null);
    if (e.target.name === 'password' && passwordError) setPasswordError(null);
    if (e.target.name === 'passwordConfirm' && passwordConfirmError) setPasswordConfirmError(null);
  }

  function handlePasswordConfirmBlur() {
    if (fields.passwordConfirm && fields.passwordConfirm !== fields.password) {
      setPasswordConfirmError('Passwords do not match.');
    } else {
      setPasswordConfirmError(null);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setDevMagicLink(null);
    setStatus('loading');

    try {
      if (mode === 'signin') {
        const loginData = await login(fields.email, fields.password);
        if (loginData?.merged_solves > 0) {
          const n = loginData.merged_solves;
          notify({
            title: `${n} ${n === 1 ? 'solve' : 'solves'} saved`,
            message: 'Your practice progress from this session has been added to your account.',
            tone: 'success',
            durationMs: 5000,
          });
        }
        navigate(returnTo || '/', { state: upgradeTier ? { upgradeTier } : undefined });
      } else if (mode === 'signup') {
        const complexityErr = validatePassword(fields.password);
        if (complexityErr) {
          setStatus('idle');
          setPasswordError(complexityErr);
          return;
        }
        if (fields.passwordConfirm !== fields.password) {
          setStatus('idle');
          setPasswordConfirmError('Passwords do not match.');
          return;
        }
        const result = await register(fields.email, fields.name, fields.password);
        setSignupEmail(fields.email);
        setStatus('success');
        if (result?.password_added) {
          setInfo('Password added to your account. You can now sign in with your email and password.');
        } else {
          setInfo(`We've sent a verification email to ${fields.email}. Click the link to verify your account. Check your spam folder if it doesn't arrive within a minute — links expire after 24 hours.`);
        }
        return;
      } else if (mode === 'magic') {
        const res = await requestMagicLink(fields.email);
        setStatus('success');
        setInfo('If an account exists for that address, a sign-in link is on its way.');
        if (res?.dev_magic_link) {
          setDevMagicLink(res.dev_magic_link);
        }
        return;
      } else if (mode === 'forgot') {
        await api.post('/auth/forgot-password', { email: fields.email });
        setStatus('success');
        setInfo(
          'If an account exists for that email, a reset link is on its way. Check your inbox (and spam folder).'
        );
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
  const showOAuth = mode === 'signin' || mode === 'signup';
  const oauthLoading = oauthProviders === null;
  const hasGoogle = !oauthLoading && oauthProviders.includes('google');
  const hasGithub = !oauthLoading && oauthProviders.includes('github');
  const hasAnyOAuth = hasGoogle || hasGithub;
  const showPasswordField = mode === 'signin' || mode === 'signup';
  const showNameField = mode === 'signup';
  const signupConfirmMismatch = mode === 'signup' && fields.passwordConfirm.length > 0 && fields.passwordConfirm !== fields.password;

  return (
    <div className="auth-page">
      <Helmet>
        <title>Sign In — datathink</title>
        <meta name="description" content="Sign in or create a free account to develop the data-professional reasoning that matters on the job — across SQL, Python, Pandas, PySpark, and more." />
        <meta name="robots" content="noindex" />
      </Helmet>
      <Topbar variant="minimal" />

      {/* ── Centered card ── */}
      <main className="auth-main">
        <div className="auth-card" role="main">

          {/* Upgrade-intent context banner */}
          {upgradeTier && (
            <div className="auth-upgrade-banner">
              <span className="auth-upgrade-banner-icon" aria-hidden="true">⬆</span>
              <span>Sign in or create an account to complete your upgrade to <strong>{{ pro: 'Pro', elite: 'Elite', lifetime_pro: 'Pro (lifetime)', lifetime_elite: 'Elite (lifetime)' }[upgradeTier] ?? upgradeTier}</strong>.</span>
            </div>
          )}

          {/* Header */}
          <div className="auth-card-header">
            <button type="button" className="auth-back-link" onClick={() => window.history.length > 1 ? navigate(-1) : navigate('/')}>
              <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13L5 8l5-5"/></svg>
              Back
            </button>
            <h1 className="auth-card-title">{meta.title}</h1>
            <p className="auth-card-subtitle">{meta.subtitle}</p>
          </div>

          {/* OAuth buttons — sign-in / sign-up only */}
          {showOAuth && (oauthLoading || hasAnyOAuth) && (
            <div className="auth-oauth">
              {oauthLoading ? (
                <>
                  <div className="auth-oauth-btn skeleton-shimmer" style={{ height: '3rem', border: 'none' }} aria-hidden="true" />
                  <div className="auth-oauth-btn skeleton-shimmer" style={{ height: '3rem', border: 'none' }} aria-hidden="true" />
                </>
              ) : (
                <>
                  {hasGoogle && (
                    <button
                      type="button"
                      className="auth-oauth-btn"
                      onClick={() => handleOAuth('google')}
                      aria-label="Continue with Google"
                    >
                      <GoogleIcon />
                      <span>Continue with Google</span>
                    </button>
                  )}
                  {hasGithub && (
                    <button
                      type="button"
                      className="auth-oauth-btn"
                      onClick={() => handleOAuth('github')}
                      aria-label="Continue with GitHub"
                    >
                      <GithubIcon />
                      <span>Continue with GitHub</span>
                    </button>
                  )}
                </>
              )}
              <div className="auth-divider" role="separator">
                <span>or continue with email</span>
              </div>
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
          {!isSuccess && (
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

              {/* Confirm password — signup only */}
              {mode === 'signup' && (
                <div className="auth-field">
                  <label className="auth-label" htmlFor="auth-password-confirm">Confirm password</label>
                  <input
                    id="auth-password-confirm"
                    name="passwordConfirm"
                    type={showPassword ? 'text' : 'password'}
                    className={`auth-input${passwordConfirmError ? ' auth-input--error' : ''}`}
                    value={fields.passwordConfirm}
                    onChange={handleChange}
                    onBlur={handlePasswordConfirmBlur}
                    autoComplete="new-password"
                    required
                    placeholder="Re-enter your password"
                    aria-required="true"
                    aria-describedby={passwordConfirmError ? 'auth-password-confirm-error' : undefined}
                  />
                  {passwordConfirmError && (
                    <p id="auth-password-confirm-error" className="auth-field-hint auth-field-hint--error" role="alert">
                      {passwordConfirmError}
                    </p>
                  )}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                className="btn btn-primary auth-submit"
                disabled={isLoading || signupConfirmMismatch}
                aria-busy={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="auth-spinner" aria-hidden="true" />
                    {mode === 'signin' ? 'Signing in…' : mode === 'signup' ? 'Creating account…' : 'Sending…'}
                  </>
                ) : (
                  <>
                    {mode === 'signin'  && 'Sign in'}
                    {mode === 'signup'  && 'Create account'}
                    {mode === 'magic'   && 'Send magic link'}
                    {mode === 'forgot'  && 'Send reset link'}
                  </>
                )}
              </button>
            </form>
          )}

          {/* Post-success: signup — check inbox */}
          {isSuccess && mode === 'signup' && (
            <div className="auth-post-success">
              <button
                type="button"
                className="btn btn-primary auth-submit"
                onClick={() => navigate(returnTo || '/')}
              >
                Continue to practice
              </button>
              <button
                type="button"
                className="auth-link-btn auth-link-subtle"
                disabled={resendStatus !== 'idle'}
                onClick={async () => {
                  setResendStatus('sending');
                  await resendVerification();
                  setResendStatus('sent');
                }}
              >
                {resendStatus === 'sent' ? 'Email resent!' : resendStatus === 'sending' ? 'Sending…' : `Resend verification email`}
              </button>
            </div>
          )}

          {/* Post-success: back to sign in */}
          {isSuccess && (mode === 'magic' || mode === 'forgot') && (
            <div className="auth-post-success">
              {mode === 'magic' && devMagicLink && (
                <a className="auth-link-btn" href={devMagicLink}>
                  Open dev magic link
                </a>
              )}
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
            {(mode === 'signin' || mode === 'magic' || mode === 'forgot') && (
              <>
                <span className="auth-footer-text">Don't have an account?</span>
                <button type="button" className="auth-link-btn" onClick={() => switchMode('signup')}>
                  Create one
                </button>
              </>
            )}
            {mode === 'signup' && (
              <>
                <span className="auth-footer-text">Already have an account?</span>
                <button type="button" className="auth-link-btn" onClick={() => switchMode('signin')}>
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
