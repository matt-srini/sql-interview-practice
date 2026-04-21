import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api from '../api';
import { identifyUser, resetIdentity } from '../analytics';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me');
      const nextUser = res.data.user ?? null;
      setUser(nextUser);
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
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    setUser(res.data.user);
    identifyUser(res.data.user);
    return res.data.user;
  }, []);

  const register = useCallback(async (email, name, password) => {
    const res = await api.post('/auth/register', { email, name, password });
    setUser(res.data.user);
    identifyUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    await api.post('/auth/logout').catch(() => {});
    setUser(null);
    resetIdentity();
  }, []);

  const requestMagicLink = useCallback(async (email) => {
    await api.post('/auth/magic-link', { email });
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
