import { useMemo } from 'react';

const CONCEPT_DETAILS = {
  'window functions': {
    explanation: 'Window functions compute aggregates or rankings across a related set of rows without collapsing the result set.',
    example: 'Use ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC) to mark each user\'s latest event.',
  },
  joins: {
    explanation: 'Joins combine records from two or more tables using matching keys.',
    example: 'LEFT JOIN keeps all rows from the left table even when no matching right-side row exists.',
  },
  aggregation: {
    explanation: 'Aggregation summarizes many rows into grouped metrics with functions like COUNT, SUM, AVG, MIN, and MAX.',
    example: 'GROUP BY country and COUNT(*) to measure active users per country.',
  },
  'time series': {
    explanation: 'Time-series analysis focuses on trends over time using date truncation, rolling windows, and lag/lead comparisons.',
    example: 'DATE_TRUNC(\'week\', created_at) plus SUM(revenue) for weekly revenue trends.',
  },
  arrays: {
    explanation: 'Array operations let you transform, filter, and aggregate list-like structures inside each row.',
    example: 'Explode array columns before counting item-level behavior.',
  },
  recursion: {
    explanation: 'Recursive logic solves problems that can be broken into smaller versions of the same problem.',
    example: 'A depth-first traversal explores children by repeatedly applying the same step.',
  },
};

function slug(value) {
  return String(value || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export default function ConceptPanel({ concept, onClose }) {
  const detail = useMemo(() => {
    if (!concept) return null;
    const raw = CONCEPT_DETAILS[String(concept).toLowerCase()] ?? CONCEPT_DETAILS[slug(concept)] ?? null;
    if (raw) return raw;
    return {
      explanation: 'This concept appears in questions that test a shared interview pattern. Focus on the shape of input, transformation, and expected output.',
      example: 'Explain your approach in steps: filter -> transform -> aggregate -> validate edge cases.',
    };
  }, [concept]);

  if (!concept || !detail) return null;

  return (
    <aside className="concept-panel" role="dialog" aria-label={`Concept details: ${concept}`}>
      <div className="concept-panel-header">
        <div>
          <span className="concept-panel-kicker">Concept</span>
          <h3>{concept}</h3>
        </div>
        <button className="concept-panel-close" onClick={onClose} aria-label="Close concept panel">×</button>
      </div>
      <p className="concept-panel-body">{detail.explanation}</p>
      <div className="concept-panel-example">
        <span className="concept-panel-example-label">Interview example</span>
        <p>{detail.example}</p>
      </div>
    </aside>
  );
}
