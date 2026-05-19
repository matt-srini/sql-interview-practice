import { describe, expect, it } from 'vitest';
import { getQuestionFormLabel, getQuestionPromptGuidance } from './questionFormLabel';

describe('questionFormLabel helpers', () => {
  it('derives debug badges and prompt guidance for code-adjacent reasoning prompts', () => {
    const question = {
      type: 'debug',
      interaction_mode: 'code_adjacent_reasoning',
      code_snippet: 'df.groupBy("user_id").count()',
      scenario_context: 'AnalysisException: column user_id not found',
    };

    expect(getQuestionFormLabel(question)).toBe('Debug');
    expect(getQuestionPromptGuidance(question, { renderMode: 'mcq', isReasoningTrack: true, isPySparkTrack: true })).toEqual({
      modeLabel: 'Code-adjacent reasoning',
      taskLabel: 'Choose the best fix',
      evidenceLabel: 'Use the snippet and the observed output together before choosing an answer.',
    });
  });

  it('derives scenario guidance for constructed reasoning prompts without code context', () => {
    const question = {
      type: 'scenario',
      interaction_mode: 'constructed_reasoning',
    };

    expect(getQuestionPromptGuidance(question, { renderMode: 'mcq', isReasoningTrack: true, isPySparkTrack: false })).toEqual({
      modeLabel: 'Constructed reasoning',
      taskLabel: 'Choose the best decision',
      evidenceLabel: 'Base your choice on the scenario, constraints, and answer tradeoffs.',
    });
  });

  it('returns null for executable prompts', () => {
    const question = {
      type: 'numerical',
      interaction_mode: 'executable_problem_solving',
    };

    expect(getQuestionPromptGuidance(question, { renderMode: 'code', isReasoningTrack: false })).toBeNull();
  });
});