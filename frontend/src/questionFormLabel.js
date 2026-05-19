function normalizeToken(value) {
  const raw = String(value ?? '').trim().toLowerCase();
  return raw ? raw.replace(/\s+/g, '_') : '';
}

export function getQuestionFormLabel(question) {
  const questionType = normalizeToken(question?.question_type ?? question?.type);
  const subtype = normalizeToken(question?.subtype);
  const interactionMode = normalizeToken(question?.interaction_mode);

  if (questionType === 'predict_output') return 'Predict output';
  if (questionType === 'debug') return 'Debug';
  if (questionType === 'optimization') return 'Optimization';
  if (questionType === 'scenario') return 'Scenario';
  if (questionType === 'numerical') return 'Numerical';
  if (subtype === 'numerical') return 'Numerical';
  if (subtype === 'conceptual') return 'Conceptual';

  if (interactionMode === 'code_adjacent_reasoning') return 'Reasoning';
  if (interactionMode === 'constructed_reasoning') return 'Reasoning';
  if (interactionMode === 'executable_problem_solving') return 'Code';

  if (questionType === 'mcq') return 'Reasoning';

  return null;
}