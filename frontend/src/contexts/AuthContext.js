import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import * as Sentry from '@sentry/react';
import api from '../api';
import { identifyUser, resetIdentity, track } from '../analytics';

function setSentryUser(user) {
  // Only tag authenticated users (anonymous rows have no email).
  Sentry.setUser(user?.email ? { id: String(user.id), email: user.email } : null);
}

// Persist a lightweight "this browser has an authenticated session" hint (a boolean —
// no PII). The landing page reads it synchronously on mount to paint the correct
// (logged-in) shell on first render after a refresh, instead of flashing the logged-out
// marketing page while GET /auth/me is still in flight. Set/cleared only at the points
// where auth is definitively known — never during the initial loading window.
function rememberAuth(isAuthed) {
  try {
    if (isAuthed) localStorage.setItem('dt_authed', '1');
    else localStorage.removeItem('dt_authed');
  } catch { /* storage unavailable — landing falls back to the non-optimistic path */ }
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      const nextUser = res.data.user ?? null;
      setUser(nextUser);
      rememberAuth(!!nextUser);
      return nextUser;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    api
      .get('/auth/me')
      .then((res) => {
        const u = res.data.user ?? null;
        setUser(u);
        identifyUser(u);
        setSentryUser(u);
        rememberAuth(!!u);
      })
      .catch((err) => {
        setUser(null);
        // 401 = session is definitively gone → clear the hint so the next refresh
        // doesn't optimistically flash the logged-in shell. A network error (no
        // response) is transient → keep the hint so a still-logged-in user stays
        // flash-free once connectivity returns.
        if (err?.response?.status === 401) rememberAuth(false);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    setUser(res.data.user);
    identifyUser(res.data.user);
    setSentryUser(res.data.user);
    rememberAuth(true);
    return res.data; // includes merged_solves for post-login toast
  }, []);

  const register = useCallback(async (email, name, password) => {
    const res = await api.post('/auth/register', { email, name, password });
    setUser(res.data.user);
    identifyUser(res.data.user);
    setSentryUser(res.data.user);
    rememberAuth(true);
    // Fire account_created only for new password registrations (not logins).
    // OAuth and magic-link sign-ins both redirect through the backend without
    // returning a "is_new" signal to the frontend, so account_created is not
    // fired for those paths.
    // TODO: fire account_created for OAuth/magic-link too — needs a backend
    // "created" flag in the /api/auth/me response or a redirect param from the
    // OAuth/magic-link callback.
    if (!res.data.password_added) {
      // password_added=true means the user added a password to an existing OAuth
      // account — not a new account creation, so don't fire.
      track('account_created', { method: 'password' });
    }
    return res.data;
  }, []);

  const logout = useCallback(async () => {
    await api.post('/auth/logout').catch(() => {});
    setUser(null);
    rememberAuth(false);
    resetIdentity();
    Sentry.setUser(null);
  }, []);

  const requestMagicLink = useCallback(async (email) => {
    const res = await api.post('/auth/magic-link', { email });
    return res.data;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, requestMagicLink, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
