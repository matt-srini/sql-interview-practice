import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import api from '../api';
import { useAuth } from './AuthContext';

const AnonProgressContext = createContext({ total: 0, refresh: async () => {} });

export function AnonProgressProvider({ children }) {
  const { user } = useAuth();
  const isAnonymous = !user?.email;
  const [total, setTotal] = useState(0);
  const fetchingRef = useRef(false);

  const refresh = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    try {
      const res = await api.get('/progress/solved-total');
      setTotal(res.data.total ?? 0);
    } catch {}
    finally {
      fetchingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (isAnonymous) {
      refresh();
    } else {
      setTotal(0);
    }
  }, [isAnonymous, refresh]);

  return (
    <AnonProgressContext.Provider value={{ total, refresh }}>
      {children}
    </AnonProgressContext.Provider>
  );
}

export function useAnonProgress() {
  return useContext(AnonProgressContext);
}
