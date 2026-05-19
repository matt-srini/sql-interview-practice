function normalizeToken(value) {
  const raw = String(value ?? '').trim().toLowerCase();
  return raw ? raw.replace(/\s+/g, '_') : '';
}

function getModeLabel(interactionMode) {
  if (interactionMode === 'code_adjacent_reasoning') return 'Code-adjacent reasoning';
  if (interactionMode === 'constructed_reasoning') return 'Constructed reasoning';
  if (interactionMode === 'executable_problem_solving') return 'Executable problem-solving';
  return 'Prompt mode';
}

function getTaskLabel(questionType, isPySparkTrack) {
  if (questionType === 'predict_output') return 'Predict the output';
  if (questionType === 'debug') return 'Choose the best fix';
  if (questionType === 'optimization') return 'Choose the best optimization';
  if (questionType === 'scenario') {
    return isPySparkTrack ? 'Choose the best engineering decision' : 'Choose the best decision';
  }
  if (isPySparkTrack) return 'Choose the strongest Spark reasoning';
  return 'Choose the strongest response';
}

function getEvidenceLabel(question, interactionMode) {
  if (question?.code_snippet && question?.scenario_context) {
    return 'Use the snippet and the observed output together before choosing an answer.';
  }
  if (question?.code_snippet) {
    return 'Use the code snippet as the primary evidence for your choice.';
  }
  if (question?.scenario_context) {
    return 'Use the observed output or logs as the primary evidence for your choice.';
  }
  if (interactionMode === 'code_adjacent_reasoning') {
    return 'Look for execution clues, API behavior, and tradeoffs in the prompt.';
  }
  return 'Base your choice on the scenario, constraints, and answer tradeoffs.';
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

export function getQuestionPromptGuidance(question, options = {}) {
  const { renderMode = 'mcq', isReasoningTrack = false, isPySparkTrack = false } = options;
  if (renderMode !== 'mcq' || !question || !isReasoningTrack) return null;

  const questionType = normalizeToken(question?.question_type ?? question?.type);
  const interactionMode = normalizeToken(question?.interaction_mode) || 'mcq';

  return {
    modeLabel: getModeLabel(interactionMode),
    taskLabel: getTaskLabel(questionType, isPySparkTrack),
    evidenceLabel: getEvidenceLabel(question, interactionMode),
  };
}

export function summarizeQuestionForms(groups = [], options = {}) {
  const { limit = 4 } = options;
  const counts = new Map();

  groups.forEach((group) => {
    (group?.questions ?? []).forEach((question) => {
      const label = getQuestionFormLabel(question);
      if (!label) return;
      counts.set(label, (counts.get(label) ?? 0) + 1);
    });
  });

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([label, count]) => ({ label, count }));
}