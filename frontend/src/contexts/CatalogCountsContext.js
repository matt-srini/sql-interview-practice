import { createContext, useContext, useEffect, useState } from 'react';
import api from '../api';
import { TRACK_SLUGS } from '../trackRegistry';

const defaultCounts = Object.fromEntries(
  TRACK_SLUGS.map(s => [s, { total: 0, easy: 0, medium: 0, hard: 0 }])
);

const CatalogCountsContext = createContext(defaultCounts);

export function CatalogCountsProvider({ children }) {
  const [counts, setCounts] = useState(defaultCounts);

  useEffect(() => {
    api.get('/catalog/counts')
      .then(r => setCounts(r.data))
      .catch(() => {});
  }, []);

  return (
    <CatalogCountsContext.Provider value={counts}>
      {children}
    </CatalogCountsContext.Provider>
  );
}

export function useCatalogCounts() {
  return useContext(CatalogCountsContext);
}
