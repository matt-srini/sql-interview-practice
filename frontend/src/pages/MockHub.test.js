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

describe('MockHub B4: access-fetch failure disables Start and shows Retry', () => {
  it('disables Start and shows Retry button when /mock/access rejects', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/mock/history') return Promise.resolve({ data: [] });
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
      if (path === '/mock/access') return Promise.reject(new Error('network error'));
      return Promise.resolve({ data: {} });
    });

    renderHub();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Start/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });
});

describe('MockHub B5: analytics fetch error', () => {
  it('shows error message with Retry button when /mock/analytics rejects', async () => {
    mockApiGet.mockImplementation((path) => {
      if (path === '/mock/history') return Promise.resolve({ data: [] });
      if (path === '/mock/analytics') return Promise.reject(new Error('network error'));
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

    renderHub();

    await waitFor(() => {
      expect(screen.getByText(/Couldn't load analytics/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
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
      // Mixed needs a role — surfaced as a helper note (the Role selector stays in its fixed position above).
      expect(screen.getByText(/Mixed track needs a role/i)).toBeInTheDocument();
    });
    // Role lives in exactly ONE place (the fixed top row, whose "All" option is unique to it) —
    // no separate relocated role selector for Mixed.
    expect(screen.getAllByRole('button', { name: 'All' })).toHaveLength(1);
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

describe('MockHub Interview Loop difficulty gating', () => {
  // Interview Loop draws only from mock-only chains, which never exist at easy.
  // The access endpoint reports easy as blocked (no_chains); the UI must disable
  // that pill and auto-select the first available difficulty so Start is usable.
  function mockLoopAccess() {
    mockApiGet.mockImplementation((path, config) => {
      if (path === '/mock/history') return Promise.resolve({ data: [] });
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
        const mode = config?.params?.mode;
        const track = config?.params?.track;
        if (mode === 'interview_loop') {
          return Promise.resolve({
            data: {
              mode, track,
              access: {
                easy: {
                  can_start: false,
                  block_reason: 'no_chains',
                  block_copy: 'Interview Loop has no chains at this difficulty — pick an enabled difficulty.',
                },
                medium: { can_start: true },
                hard: { can_start: true },
                mixed: { can_start: true },
              },
            },
          });
        }
        return Promise.resolve({
          data: {
            mode, track,
            access: { easy: { can_start: true }, medium: { can_start: true }, hard: { can_start: true }, mixed: { can_start: true } },
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
  }

  it('shows NO difficulty selector for Interview Loop and gates Start on chain availability', async () => {
    mockLoopAccess(); // sql: access.mixed.can_start = true
    renderHub({ mockPreset: { mode: 'interview_loop', track: 'sql' } });

    // We're in Interview Loop mode (the Start CTA reflects it)…
    const start = await screen.findByRole('button', { name: /Start Interview Loop/ });
    // … and there is NO difficulty selector at all — no Easy/Medium/Hard pills.
    expect(screen.queryByRole('button', { name: 'Easy' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Hard' })).not.toBeInTheDocument();
    // sql has chains (access.mixed) → Start is enabled.
    await waitFor(() => expect(start).not.toBeDisabled());
  });

  it('disables Start for Interview Loop when the track pool is exhausted, with a track-level message', async () => {
    mockApiGet.mockImplementation((path, config) => {
      if (path === '/mock/history') return Promise.resolve({ data: [] });
      if (path === '/mock/analytics') {
        return Promise.resolve({ data: { benchmark_summary: { total_sessions: 0 }, drill_summary: { total_sessions: 0 }, mode_breakdown: { benchmark: 0, drill: 0 }, top_concepts: [], weak_concepts: [] } });
      }
      if (path === '/mock/access') {
        return Promise.resolve({
          data: {
            mode: config?.params?.mode, track: config?.params?.track,
            access: {
              easy: { can_start: false, block_reason: 'no_chains' },
              medium: { can_start: false, block_reason: 'pool_exhausted' },
              hard: { can_start: false, block_reason: 'pool_exhausted' },
              mixed: { can_start: false, block_reason: 'pool_exhausted', block_copy: "You've completed every Interview Loop chain for this track. Try another track, or check back as new chains are added." },
            },
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    renderHub({ mockPreset: { mode: 'interview_loop', track: 'sql' } });

    const start = await screen.findByRole('button', { name: /Start Interview Loop/ });
    await waitFor(() => expect(start).toBeDisabled());
    expect(screen.getByText(/completed every Interview Loop chain for this track/i)).toBeInTheDocument();
  });
});

describe('MockHub Interview Loop + Mixed track', () => {
  it('keeps Interview Loop selectable on Mixed and auto-switches the track with an explanatory note', async () => {
    renderHub({ mockPreset: { mode: 'custom', track: 'mixed' } });

    // The Interview Loop mode card is NOT disabled on Mixed (it used to be, with no reason shown).
    const loopCard = await screen.findByRole('button', { name: /Interview Loop/ });
    expect(loopCard).not.toBeDisabled();

    fireEvent.click(loopCard);

    // Selecting it moved off Mixed to a single track (SQL, no role) and states the constraint.
    await waitFor(() => {
      expect(screen.getByText(/Interview Loop runs on one track — can't choose Mixed/i)).toBeInTheDocument();
    });
    // The track actually switched off Mixed (to SQL).
    expect(screen.getByRole('button', { name: 'SQL' }).className).toMatch(/active/);
    // …and we're now in Interview Loop mode (no dead-end).
    expect(screen.getByRole('button', { name: /Start Interview Loop/ })).toBeInTheDocument();
  });
});