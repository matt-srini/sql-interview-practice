import { createContext, useContext } from 'react';
import { useParams } from 'react-router-dom';
import { TRACK_META } from '../trackRegistry';

export { TRACK_META };

const TopicContext = createContext(null);

export function TopicProvider({ children }) {
  const params = useParams();
  const topic = (params.topic && TRACK_META[params.topic]) ? params.topic : 'sql';
  const meta = TRACK_META[topic];

  return (
    <TopicContext.Provider value={{ topic, meta }}>
      {children}
    </TopicContext.Provider>
  );
}

export function useTopic() {
  const ctx = useContext(TopicContext);
  if (!ctx) {
    // Fallback for components used outside TopicProvider
    return { topic: 'sql', meta: TRACK_META['sql'] };
  }
  return ctx;
}
