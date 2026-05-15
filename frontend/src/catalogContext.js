import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import api from './api';
import { useTopic } from './contexts/TopicContext';
import { useAuth } from './contexts/AuthContext';

const CatalogContext = createContext(null);

function apiPathForTopic(topic) {
  switch (topic) {
    case 'python': return '/python/catalog';
    case 'python-data': return '/python-data/catalog';
    case 'pyspark': return '/pyspark/catalog';
    case 'sql':
    default: return '/catalog';
  }
}

export function CatalogProvider({ children }) {
  // useTopic() returns { topic: 'sql' } as default when no TopicProvider is present
  const { topic } = useTopic();
  const { user } = useAuth();
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const path = apiPathForTopic(topic);
      const res = await api.get(path);
      setCatalog(res.data);
      return res.data;
    } catch (e) {
      setError('Failed to load question catalog. Is the backend running?');
      return null;
    } finally {
      setLoading(false);
    }
  }, [topic]);

  useEffect(() => {
    // Reset catalog when topic changes so stale data isn't shown
    setCatalog(null);
    setLoading(true);
    refresh();
  }, [refresh]);

  // Refresh catalog when the user's identity changes (login / logout).
  // Skip the initial mount — the effect above already handles the first fetch.
  const prevUserIdRef = useRef('__initial__');
  useEffect(() => {
    const curr = user?.id ?? null;
    if (prevUserIdRef.current === '__initial__') {
      prevUserIdRef.current = curr;
      return;
    }
    if (prevUserIdRef.current === curr) return;
    prevUserIdRef.current = curr;
    refresh();
  }, [user, refresh]);

  const value = useMemo(
    () => ({ catalog, loading, error, refresh }),
    [catalog, loading, error, refresh]
  );

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

export function useCatalog() {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog must be used within CatalogProvider');
  return ctx;
}
