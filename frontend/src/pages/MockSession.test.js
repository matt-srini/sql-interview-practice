/**
 * MockSession verdict message tests.
 *
 * Verifies that the correct-answer feedback message is context-aware:
 *   - Non-last question → "Move to the next question."
 *   - Last question     → "All done — end your session."
 *
 * Also covers: wrong-answer message, "Next question →" button visibility.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const { mockApiGet, mockApiPost, mockUseAuth } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockApiPost: vi.fn(),
  mockUseAuth: vi.fn(),
}));

vi.mock('../api', () => ({
  default: {
    get: (...a) => mockApiGet(...a),
    post: (...a) => mockApiPost(...a),
  },
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../components/CodeEditor', () => ({
  default: ({ value, onChange }) => (
    <textarea
      data-testid="code-editor"
      value={value || ''}
      onChange={e => onChange?.(e.target.value)}
    />
  ),
}));

vi.mock('../components/MCQPanel', () => ({
  default: () => <div data-testid="mcq-panel" />,
}));

vi.mock('../components/SchemaViewer', () => ({
  default: () => <div data-testid="schema-viewer" />,
}));

vi.mock('../analytics', () => ({ track: vi.fn() }));

vi.mock('../contexts/TopicContext', () => ({
  TRACK_META: {
    sql: { label: 'SQL' },
    python: { label: 'Python' },
    'python-data': { label: 'Pandas' },
    pyspark: { label: 'PySpark' },
  },
}));

import MockSession from './MockSession';

function makeQuestion(id) {
  return {
    id,
    title: `Question ${id}`,
    prompt: `Write a query for question ${id}.`,
    track: 'sql',
    difficulty: 'easy',
    type: 'query',
    concepts: [],
    hints: [],
    companies: [],
    schema: [],
    is_solved: false,
    final_code: null,
    starter_code: null,
    is_follow_up: false,
  };
}

function makeSessionData(numQuestions = 2) {
  return {
    session_id: 1,
    mode: 'custom',
    track: 'sql',
    difficulty: 'easy',
    started_at: new Date(Date.now() - 120000).toISOString(),
    time_limit_s: 1800,
    status: 'active',
    questions: Array.from({ length: numQuestions }, (_, i) => makeQuestion(i + 1)),
    focus_fallback: false,
  };
}

function makeCompletedSummary(overrides = {}) {
  return {
    session_id: 1,
    mode: 'benchmark',
    track: 'sql',
    difficulty: 'easy',
    score: 1,
    solved_count: 1,
    total_count: 1,
    time_used_s: 420,
    time_limit_s: 1800,
    questions: [
      {
        ...makeQuestion(1),
        concepts: ['WINDOW FUNCTIONS', 'JOINS'],
        is_solved: false,
        solution_query: 'select 1',
      },
    ],
    ...overrides,
  };
}

function renderSession(sessionData) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/mock/1', state: { sessionData } }]}>
      <Routes>
        <Route path="/mock/:id" element={<MockSession />} />
        <Route path="/mock" element={<div>Mock Hub</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  mockUseAuth.mockReturnValue({
    user: { id: 'u1', plan: 'elite', email: 'test@test.com', name: 'Tester' },
  });
  mockApiPost.mockResolvedValue({ data: { correct: true, feedback: [] } });
  mockApiGet.mockResolvedValue({ data: {} });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function submitCurrentQuestion() {
  const btn = await screen.findByRole('button', { name: /^Submit/ });
  fireEvent.click(btn);
}

// ── Submit lock and button state ──────────────────────────────────────────────
// Mock mode shows no verdict text — only the button label changes and navigation appears.

describe('MockSession submit lock', () => {
  it('shows "✓ Solved" on the button after a correct submission', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /✓ Solved/ })).toBeInTheDocument();
    });
  });

  it('shows "✗ Submitted" on the button after a wrong submission', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: [] } });
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /✗ Submitted/ })).toBeInTheDocument();
    });
  });

  it('disables the Submit button after any submission', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /✓ Solved/ });
      expect(btn).toBeDisabled();
    });
  });

  it('shows "All questions answered" nudge on the last question after submit', async () => {
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByText('All questions answered — end your session when ready.')).toBeInTheDocument();
    });
  });

  it('does NOT show "All questions answered" nudge on a non-last question', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.queryByText('All questions answered — end your session when ready.')).not.toBeInTheDocument();
    });
  });

  it('shows "end session or go back" nudge when only the last question is submitted', async () => {
    // Regression: "All questions answered" must NOT appear — but the user
    // should still see an actionable nudge on the last question.
    renderSession(makeSessionData(2));

    // Navigate to Q2 (last question) without submitting Q1
    const q2Tab = await screen.findByRole('button', { name: /Q2/ });
    fireEvent.click(q2Tab);

    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.queryByText('All questions answered — end your session when ready.')).not.toBeInTheDocument();
      expect(screen.getByText('End your session when ready, or go back to answer remaining questions.')).toBeInTheDocument();
    });
  });

  it('shows no verdict error text after a wrong submission', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: ['hint'] } });
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /✗ Submitted/ })).toBeInTheDocument();
    });
    // No feedback text visible
    expect(screen.queryByText('hint')).not.toBeInTheDocument();
  });
});

// (Next question → button tests consolidated in "MockSession next-question button after submit" below)

// ── Flag button ────────────────────────────────────────────────────────────────

describe('MockSession flag button', () => {
  it('renders the flag button for the active question', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Flag for review/i })).toBeInTheDocument();
    });
  });

  it('toggles to "Flagged" when clicked and back when clicked again', async () => {
    renderSession(makeSessionData(2));
    const flagBtn = await screen.findByRole('button', { name: /Flag for review/i });
    fireEvent.click(flagBtn);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /⚑ Flagged/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /⚑ Flagged/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Flag for review/i })).toBeInTheDocument();
    });
  });
});

// ── Navigation arrows ──────────────────────────────────────────────────────────

describe('MockSession navigation arrows', () => {
  it('renders ← and → arrows', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Previous question' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Next question' })).toBeInTheDocument();
    });
  });

  it('← is disabled on the first question', async () => {
    renderSession(makeSessionData(2));
    const prev = await screen.findByRole('button', { name: 'Previous question' });
    expect(prev).toBeDisabled();
  });

  it('→ is disabled on the last question of a 1-question session', async () => {
    renderSession(makeSessionData(1));
    const next = await screen.findByRole('button', { name: 'Next question' });
    expect(next).toBeDisabled();
  });

  it('→ navigates to Q2', async () => {
    renderSession(makeSessionData(2));
    const next = await screen.findByRole('button', { name: 'Next question' });
    fireEvent.click(next);
    await waitFor(() => {
      const q2Tab = screen.getByRole('button', { name: /Q2/ });
      expect(q2Tab.className).toMatch(/active/);
    });
  });

  it('← navigates back to Q1 after advancing', async () => {
    renderSession(makeSessionData(2));
    const next = await screen.findByRole('button', { name: 'Next question' });
    fireEvent.click(next);
    await waitFor(() => screen.getByRole('button', { name: /Q2/ }));

    const prev = screen.getByRole('button', { name: 'Previous question' });
    fireEvent.click(prev);
    await waitFor(() => {
      const q1Tab = screen.getByRole('button', { name: /Q1/ });
      expect(q1Tab.className).toMatch(/active/);
    });
  });
});

// ── "Next question →" button ────────────────────────────────────────────────────
// Shows after ANY submit (correct or wrong) when not the last question.

describe('MockSession next-question button after submit', () => {
  it('shows "Next question →" after a wrong answer on a non-last question', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: [] } });
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Next question →' })).toBeInTheDocument();
    });
  });

  it('shows "Next question →" after a correct answer on a non-last question', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Next question →' })).toBeInTheDocument();
    });
  });

  it('does NOT show "Next question →" after submit on the last question', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: [] } });
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Next question →' })).not.toBeInTheDocument();
    });
  });

  it('"Next question →" advances to Q2', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: [] } });
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();
    await waitFor(() => screen.getByRole('button', { name: 'Next question →' }));
    fireEvent.click(screen.getByRole('button', { name: 'Next question →' }));
    await waitFor(() => {
      const q2Tab = screen.getByRole('button', { name: /Q2/ });
      expect(q2Tab.className).toMatch(/active/);
    });
  });
});

// ── Pre-submission review modal ────────────────────────────────────────────────

describe('MockSession review modal', () => {
  it('opens when "End session" is clicked', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => screen.getByRole('button', { name: 'End session' }));
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      expect(screen.getByText('Review before submitting')).toBeInTheDocument();
    });
  });

  it('shows all questions in the checklist', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => screen.getByRole('button', { name: 'End session' }));
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      // Each question number appears in both the tab and the review list — use getAllBy
      expect(screen.getAllByText('Q1').length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText('Q2').length).toBeGreaterThanOrEqual(2);
    });
  });

  it('shows warning and "Go back and review" when questions are unattempted', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => screen.getByRole('button', { name: 'End session' }));
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Go back and review' })).toBeInTheDocument();
      expect(screen.getByText(/remaining/)).toBeInTheDocument();
    });
  });

  it('shows "End session anyway" when questions are incomplete', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => screen.getByRole('button', { name: 'End session' }));
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'End session anyway' })).toBeInTheDocument();
    });
  });

  it('"Go back and review" closes modal and goes to first unsolved question', async () => {
    renderSession(makeSessionData(2));
    // Advance to Q2 first
    const next = await screen.findByRole('button', { name: 'Next question' });
    fireEvent.click(next);
    await waitFor(() => screen.getByRole('button', { name: /Q2/ }));

    // Open modal and click Go back
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => screen.getByRole('button', { name: 'Go back and review' }));
    fireEvent.click(screen.getByRole('button', { name: 'Go back and review' }));

    await waitFor(() => {
      expect(screen.queryByText('Review before submitting')).not.toBeInTheDocument();
      const q1Tab = screen.getByRole('button', { name: /Q1/ });
      expect(q1Tab.className).toMatch(/active/);
    });
  });

  it('shows simple confirm ("Keep going" / "End session") when all questions are solved', async () => {
    // Single-question session — solve it
    renderSession(makeSessionData(1));
    await submitCurrentQuestion(); // correct by default
    await waitFor(() => screen.getByText('All questions answered — end your session when ready.'));

    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      expect(screen.getByText('Ready to end your session?')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Keep going' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Go back and review' })).not.toBeInTheDocument();
    });
  });

  it('clicking a question row in the modal closes modal and navigates to that question', async () => {
    renderSession(makeSessionData(2));
    await waitFor(() => screen.getByRole('button', { name: 'End session' }));
    fireEvent.click(screen.getByRole('button', { name: 'End session' }));

    // Click Q2 row in the checklist
    await waitFor(() => screen.getByText('Question 2'));
    fireEvent.click(screen.getByText('Question 2'));

    await waitFor(() => {
      expect(screen.queryByText('Review before submitting')).not.toBeInTheDocument();
      const q2Tab = screen.getByRole('button', { name: /Q2/ });
      expect(q2Tab.className).toMatch(/active/);
    });
  });

  it('shows flagged question as ⚑ in the review modal', async () => {
    renderSession(makeSessionData(2));
    // Flag Q1
    const flagBtn = await screen.findByRole('button', { name: /Flag for review/i });
    fireEvent.click(flagBtn);

    fireEvent.click(screen.getByRole('button', { name: 'End session' }));
    await waitFor(() => {
      // The modal review list should have a ⚑ marker
      expect(screen.getByText('⚑')).toBeInTheDocument();
    });
  });
});

describe('MockSession summary actions', () => {
  it('shows review and follow-up drill actions for benchmark summaries', async () => {
    const completedSession = { ...makeSessionData(1), status: 'completed', mode: 'benchmark' };
    mockApiPost.mockResolvedValueOnce({ data: makeCompletedSummary({ mode: 'benchmark' }) });

    renderSession(completedSession);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Back to Mock' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Plan follow-up drill' })).toBeInTheDocument();
    });
  });

  it('shows targeted follow-up CTA for drill summaries', async () => {
    const completedSession = { ...makeSessionData(1), status: 'completed', mode: 'custom' };
    mockApiPost.mockResolvedValueOnce({ data: makeCompletedSummary({ mode: 'custom' }) });

    renderSession(completedSession);

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Drill weak concepts →' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Back to drill lobby' })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Plan follow-up drill' })).not.toBeInTheDocument();
    });
  });
});
