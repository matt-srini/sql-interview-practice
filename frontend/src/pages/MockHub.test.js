import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';

const { mockApiGet, mockUseAuth, mockState } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockUseAuth: vi.fn(),
  mockState: {
    history: [],
  },
}));

vi.mock('../api', () => ({
  default: {
    get: (...args) => mockApiGet(...args),
    post: vi.fn(),
  },
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../components/Topbar', () => ({
  default: () => <div data-testid="topbar" />,
}));

vi.mock('../components/UpgradeButton', () => ({
  default: ({ label }) => <button type="button">{label}</button>,
}));

vi.mock('../analytics', () => ({ track: vi.fn() }));

import MockHub from './MockHub';

function renderHub(entryState) {
  return render(
    <HelmetProvider>
      <MemoryRouter initialEntries={[{ pathname: '/mock', state: entryState }]}>
        <Routes>
          <Route path="/mock" element={<MockHub />} />
        </Routes>
      </MemoryRouter>
    </HelmetProvider>
  );
}

beforeEach(() => {
  mockUseAuth.mockReturnValue({
    user: { id: 'u1', plan: 'elite', email: 'test@datathink.co', name: 'Tester' },
  });
  mockState.history = [];

  mockApiGet.mockImplementation((path) => {
    if (path === '/mock/history') return Promise.resolve({ data: mockState.history });
    if (path === '/mock/analytics') {
      return Promise.resolve({
        data: {
          benchmark_summary: { total_sessions: 0 },
          drill_summary: { total_sessions: 0 },
          mode_breakdown: { benchmark: 0, drill: 0 },
          top_concepts: [],
          weak_concepts: [],
        },
      });
    }
    if (path === '/mock/access') {
      return Promise.resolve({
        data: {
          access: {
            easy: { can_start: true },
            medium: { can_start: true },
            hard: { can_start: true },
            mixed: { can_start: true },
          },
        },
      });
    }
    return Promise.resolve({ data: {} });
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  localStorage.clear();
});

describe('MockHub preset intake', () => {
  it('applies a recommended drill preset from summary navigation', async () => {
    renderHub({
      mockPreset: {
        mode: 'custom',
        track: 'python',
        difficulty: 'medium',
        numQuestions: 3,
        timeMinutes: 45,
        note: 'Follow up on this benchmark with a short targeted drill while the weak spots are still fresh.',
      },
    });

    await waitFor(() => {
      expect(screen.getByText('Recommended next step')).toBeInTheDocument();
      expect(screen.getByText(/weak spots are still fresh/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Python' }).className).toMatch(/active/);
      expect(screen.getByDisplayValue('3')).toBeInTheDocument();
      expect(screen.getByDisplayValue('45')).toBeInTheDocument();
    });
  });
});

describe('MockHub history framing', () => {
  it('shows benchmark-versus-drill onboarding when there is no history yet', async () => {
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Use benchmarks for a consistent interview-style check, then use custom drills or Interview Loop to work on the gaps you find.')).toBeInTheDocument();
      expect(screen.getByText('Start with a benchmark, then drill the misses')).toBeInTheDocument();
      expect(screen.getByText('Use benchmarks for comparability')).toBeInTheDocument();
      expect(screen.getByText('Use custom drills for targeted reps')).toBeInTheDocument();
    });
  });

  it('shows benchmark empty framing when only drill history exists', async () => {
    mockState.history = [
      {
        session_id: 'drill-1',
        mode: '30min',
        track: 'sql',
        difficulty: 'easy',
        solved_count: 1,
        total_count: 2,
        time_limit_s: 1800,
        status: 'completed',
        started_at: '2026-05-20T00:00:00Z',
      },
    ];

    renderHub();

    await waitFor(() => {
      // Phase 3: heading renamed from "Recent drill sessions" to "Recent custom drills"
      expect(screen.getByText('Recent custom drills')).toBeInTheDocument();
      expect(screen.getByText('No benchmark sessions yet')).toBeInTheDocument();
      expect(screen.queryByText('Start with a benchmark, then drill the misses')).not.toBeInTheDocument();
    });
  });

  it('shows drill empty framing when only benchmark history exists', async () => {
    mockState.history = [
      {
        session_id: 'benchmark-1',
        mode: 'benchmark',
        track: 'sql',
        difficulty: 'easy',
        solved_count: 2,
        total_count: 3,
        time_limit_s: 3600,
        status: 'completed',
        started_at: '2026-05-20T00:00:00Z',
      },
    ];

    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Recent benchmark sessions')).toBeInTheDocument();
      expect(screen.getByText('No custom drills yet')).toBeInTheDocument();
      expect(screen.queryByText('Start with a benchmark, then drill the misses')).not.toBeInTheDocument();
    });
  });
});

describe('MockHub mixed-track framing', () => {
  it('shows role selector for mixed track in benchmark mode (Phase 3: role-based benchmark)', async () => {
    // Phase 3 replaced "Mixed is drill-only" with a role-selection flow for mixed benchmark
    renderHub({
      mockPreset: {
        mode: 'benchmark',
        track: 'mixed',
        difficulty: 'mixed',
      },
    });

    await waitFor(() => {
      // Hint shown before a role is selected (unique to mixed benchmark role-selector section)
      expect(screen.getByText('Select a role to see the benchmark blueprint for your track mix.')).toBeInTheDocument();
    });
  });

  it('keeps the help button outside the subtitle paragraph flow', async () => {
    renderHub();

    await waitFor(() => {
      expect(screen.getByText('Use benchmarks for a consistent interview-style check, then use custom drills or Interview Loop to work on the gaps you find.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'How it works' })).toBeInTheDocument();
    });

    const subtitle = screen.getByText('Use benchmarks for a consistent interview-style check, then use custom drills or Interview Loop to work on the gaps you find.');
    const helpButton = screen.getByRole('button', { name: 'How it works' });
    expect(subtitle.parentElement).not.toBe(helpButton.parentElement?.closest('p'));
    fireEvent.click(helpButton);
    await waitFor(() => {
      expect(screen.getByText('How mock modes work')).toBeInTheDocument();
    });
  });
});