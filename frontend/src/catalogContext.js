import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api from './api';
import { useTopic } from './contexts/TopicContext';

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
    } catch (e) {
      setError('Failed to load question catalog. Is the backend running?');
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
