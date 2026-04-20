import { createContext, useContext } from 'react';
import { useParams } from 'react-router-dom';

export const TRACK_META = {
  sql: {
    label: 'SQL',
    description: 'Write queries against realistic datasets',
    color: '#5B6AF0',
    apiPrefix: '',
    language: 'sql',
    hasRunCode: true,
    hasMCQ: false,
    totalQuestions: 95,
    tagline: 'easy · medium · hard',
  },
  python: {
    label: 'Python',
    description: 'Algorithms and data structures',
    color: '#2D9E6B',
    apiPrefix: '/python',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    totalQuestions: 83,
    tagline: 'algorithms · data structures · OOP',
  },
  'python-data': {
    label: 'Pandas',
    description: 'pandas and numpy data manipulation',
    color: '#C47F17',
    apiPrefix: '/python-data',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    totalQuestions: 82,
    tagline: 'pandas · numpy · data wrangling',
  },
  pyspark: {
    label: 'PySpark',
    description: 'Spark architecture and concepts',
    color: '#D94F3D',
    apiPrefix: '/pyspark',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    totalQuestions: 90,
    tagline: 'conceptual · MCQ · predict output',
  },
};

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
