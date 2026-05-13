import { createContext, useContext } from 'react';
import { useParams } from 'react-router-dom';

export const TRACK_META = {
  sql: {
    label: 'SQL',
    description: 'SQL problems against real datasets — joins, aggregations, window functions, and analytical patterns drawn from actual data engineering interviews.',
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
    description: 'Python coding problems set in real data contexts — processing pipelines, cleaning routines, and analysis logic typical of data engineering and data science interviews.',
    color: '#2D9E6B',
    apiPrefix: '/python',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    totalQuestions: 83,
    tagline: 'data processing · algorithms · scripting',
  },
  'python-data': {
    label: 'Pandas',
    description: 'Practice Pandas and NumPy interview questions: DataFrame manipulation, groupby, reshaping, and time series analysis.',
    color: '#C47F17',
    apiPrefix: '/python-data',
    language: 'python',
    hasRunCode: true,
    hasMCQ: false,
    totalQuestions: 76,
    tagline: 'pandas · numpy · data wrangling',
  },
  pyspark: {
    label: 'PySpark',
    description: 'Practice PySpark interview questions: Spark architecture, streaming, performance optimization, and Delta Lake patterns.',
    color: '#D94F3D',
    apiPrefix: '/pyspark',
    language: 'text',
    hasRunCode: false,
    hasMCQ: true,
    totalQuestions: 102,
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
