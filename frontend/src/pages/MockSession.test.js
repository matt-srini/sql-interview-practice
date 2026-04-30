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
    started_at: new Date(Date.now() - 30000).toISOString(),
    time_limit_s: 1800,
    status: 'active',
    questions: Array.from({ length: numQuestions }, (_, i) => makeQuestion(i + 1)),
    focus_fallback: false,
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
  const btn = await screen.findByRole('button', { name: 'Submit' });
  fireEvent.click(btn);
}

// ── Verdict message ────────────────────────────────────────────────────────────

describe('MockSession verdict message', () => {
  it('shows "Move to the next question." on a correct answer when not the last question', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByText('✓ Correct! Move to the next question.')).toBeInTheDocument();
    });
  });

  it('shows "All done — end your session." on a correct answer on the last question', async () => {
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByText('✓ Correct! All done — end your session.')).toBeInTheDocument();
    });
  });

  it('never shows the last-question message on the first of two questions', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.queryByText('✓ Correct! All done — end your session.')).not.toBeInTheDocument();
    });
  });

  it('shows the wrong-answer message when submission is incorrect', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { correct: false, feedback: ['Check your WHERE clause'] } });
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByText('✗ Not quite — review your logic and try again.')).toBeInTheDocument();
    });
  });
});

// ── "Next question →" button ───────────────────────────────────────────────────

describe('MockSession next-question button', () => {
  it('shows "Next question →" after a correct answer on a non-last question', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Next question →' })).toBeInTheDocument();
    });
  });

  it('does NOT show "Next question →" after a correct answer on the last question', async () => {
    renderSession(makeSessionData(1));
    await submitCurrentQuestion();

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Next question →' })).not.toBeInTheDocument();
    });
  });

  it('clicking "Next question →" advances to Q2', async () => {
    renderSession(makeSessionData(2));
    await submitCurrentQuestion();

    await waitFor(() => screen.getByRole('button', { name: 'Next question →' }));
    fireEvent.click(screen.getByRole('button', { name: 'Next question →' }));

    await waitFor(() => {
      // Q2 tab becomes active — the active tab button has class "active"
      const q2Tab = screen.getByRole('button', { name: /Q2/ });
      expect(q2Tab.className).toMatch(/active/);
    });
  });
});
