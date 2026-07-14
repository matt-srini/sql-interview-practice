/**
 * ProgressDashboard component tests.
 *
 * Focuses on the API→render pipeline so dashboard response-shape drift is caught
 * against the current 9-track track-overview and mock-history UI.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProgressDashboard from './ProgressDashboard';

// ---------------------------------------------------------------------------
// Mock the api module and AuthContext so the component renders in isolation
// ---------------------------------------------------------------------------

vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(() => Promise.resolve({})),
  },
}));

// Mutable auth so individual tests can exercise free / pro / elite branches.
const { mockUseAuth } = vi.hoisted(() => ({ mockUseAuth: vi.fn() }));
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Topbar uses useTheme — provide a minimal stub so it doesn't crash in jsdom
vi.mock('../App', () => ({
  useTheme: () => ({ theme: 'light', setTheme: () => {}, resolvedTheme: 'light' }),
}));

import api from '../api';

function renderDashboard() {
  return render(
    <MemoryRouter>
      <ProgressDashboard />
    </MemoryRouter>
  );
}

// Minimal dashboard payload matching the correct API shape
function makeDashboardPayload(overrides = {}) {
  return {
    tracks: {
      sql: {
        solved: 47,
        total: 112,
        by_difficulty: {
          easy:   { solved: 25, total: 37 },
          medium: { solved: 22, total: 45 },
          hard:   { solved: 0,  total: 30 },
        },
      },
      python: {
        solved: 0,
        total: 95,
        by_difficulty: {
          easy:   { solved: 0, total: 39 },
          medium: { solved: 0, total: 32 },
          hard:   { solved: 0, total: 24 },
        },
      },
      'pandas': {
        solved: 0,
        total: 86,
        by_difficulty: {
          easy:   { solved: 0, total: 27 },
          medium: { solved: 0, total: 36 },
          hard:   { solved: 0, total: 23 },
        },
      },
      pyspark: {
        solved: 0,
        total: 106,
        by_difficulty: {
          easy:   { solved: 0, total: 41 },
          medium: { solved: 0, total: 39 },
          hard:   { solved: 0, total: 26 },
        },
      },
      'data-engineering': {
        solved: 0,
        total: 86,
        by_difficulty: {
          easy:   { solved: 0, total: 30 },
          medium: { solved: 0, total: 33 },
          hard:   { solved: 0, total: 23 },
        },
      },
      'data-modeling': {
        solved: 0,
        total: 76,
        by_difficulty: {
          easy:   { solved: 0, total: 25 },
          medium: { solved: 0, total: 28 },
          hard:   { solved: 0, total: 23 },
        },
      },
      statistics: {
        solved: 0,
        total: 97,
        by_difficulty: {
          easy:   { solved: 0, total: 31 },
          medium: { solved: 0, total: 41 },
          hard:   { solved: 0, total: 25 },
        },
      },
      'ml-fundamentals': {
        solved: 0,
        total: 90,
        by_difficulty: {
          easy:   { solved: 0, total: 30 },
          medium: { solved: 0, total: 35 },
          hard:   { solved: 0, total: 25 },
        },
      },
      experimentation: {
        solved: 0,
        total: 80,
        by_difficulty: {
          easy:   { solved: 0, total: 30 },
          medium: { solved: 0, total: 30 },
          hard:   { solved: 0, total: 20 },
        },
      },
      'product-sense': {
        solved: 0,
        total: 87,
        by_difficulty: {
          easy:   { solved: 0, total: 30 },
          medium: { solved: 0, total: 33 },
          hard:   { solved: 0, total: 24 },
        },
      },
    },
    concepts_by_track: {},
    recent_activity: [],
    ...overrides,
  };
}

function makeInsightsPayload(overrides = {}) {
  return {
    per_track: {
      sql: { solve_count: 47, accuracy_pct: 0.82, attempts: 60, practice_attempts: 54, mock_attempts: 6, first_try_accuracy_pct: 0.741, first_try_correct: 40, first_try_attempted: 54 },
      python: { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      'pandas': { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      pyspark: { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      'data-engineering': { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      'data-modeling': { solve_count: 0, accuracy_pct: 1.0, attempts: 7, practice_attempts: 0, mock_attempts: 7, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      statistics: { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      'ml-fundamentals': { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      experimentation: { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
      'product-sense': { solve_count: 0, accuracy_pct: null, attempts: 0, practice_attempts: 0, mock_attempts: 0, first_try_accuracy_pct: null, first_try_correct: 0, first_try_attempted: 0 },
    },
    weakest_concepts: [],
    streak_days: 0,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  // Default: an authenticated free user (no plan) — individual tests override the plan.
  mockUseAuth.mockReturnValue({ user: { name: 'Test User', email: 'test@example.com' }, loading: false });
  // Default: mock history returns empty list
  api.get.mockImplementation((url) => {
    if (url === '/mock/history') return Promise.resolve({ data: [] });
    if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload() });
    return Promise.resolve({ data: makeDashboardPayload() });
  });
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProgressDashboard', () => {
  it('renders track overview counts in X/Y format', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('47/112')).toBeInTheDocument();
      expect(screen.getAllByText('0/95').length).toBeGreaterThan(0);
      expect(screen.getAllByText('0/90').length).toBeGreaterThan(0);
    });
  });

  it('renders the overall progress bar totals', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('47/112')).toBeInTheDocument();
    });
  });

  it('renders all ten track rows', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getAllByText('SQL').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Python').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Pandas').length).toBeGreaterThan(0);
      expect(screen.getAllByText('PySpark').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Data Engineering').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Data Modeling').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Statistics').length).toBeGreaterThan(0);
      expect(screen.getAllByText('ML Fundamentals').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Experimentation').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Product Sense').length).toBeGreaterThan(0);
    });
  });

  it('shows "N in mock" on any track with mock attempts, and "—" for zero-attempt tracks', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('6 in mock')).toBeInTheDocument();   // sql — mixed practice + mock
      expect(screen.getByText('7 in mock')).toBeInTheDocument();   // data-modeling — purely mock
    });
    // zero-attempt tracks render an em-dash, never a misleading "0% acc"
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('does NOT render X/Y when by_difficulty values are plain integers (regression guard)', async () => {
    // Simulate the old broken API shape: by_difficulty returns plain ints
    const brokenPayload = makeDashboardPayload();
    brokenPayload.tracks.sql.by_difficulty = { easy: 25, medium: 22, hard: 0 };

    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
      if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload() });
      return Promise.resolve({ data: brokenPayload });
    });

    renderDashboard();

    // With the broken shape, counts render as "/" — assert that doesn't happen
    await waitFor(() => {
      // The "/" pattern from undefined.solved / undefined.total should not appear
      const slashOnlyElements = screen.queryAllByText('/');
      expect(slashOnlyElements).toHaveLength(0);
    });
  });

  it('renders zero counts correctly as 0/total in track overview rows', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getAllByText('0/95').length).toBeGreaterThan(0);
      expect(screen.getAllByText('0/86').length).toBeGreaterThan(0);
      expect(screen.getAllByText('0/80').length).toBeGreaterThan(0);
    });
  });

  it('shows loading state before data arrives', async () => {
    let resolve;
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
      if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload() });
      return new Promise((res) => { resolve = res; });
    });

    renderDashboard();
    expect(screen.getByLabelText(/loading dashboard/i)).toBeInTheDocument();

    resolve({ data: makeDashboardPayload() });
    await waitFor(() => {
      expect(screen.queryByLabelText(/loading dashboard/i)).not.toBeInTheDocument();
    });
  });

  it('shows error state when the API fails', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
      if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload() });
      return Promise.reject(new Error('Network error'));
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('renders recent mock session history when present', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') {
        return Promise.resolve({
          data: [
            {
              session_id: 42,
              mode: '30min',
              track: 'sql',
              difficulty: 'hard',
              started_at: new Date().toISOString(),
              solved_count: 1,
              total_count: 2,
              status: 'completed',
            },
          ],
        });
      }
      if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload() });
      return Promise.resolve({ data: makeDashboardPayload() });
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Mock interviews')).toBeInTheDocument();
      expect(screen.getByText('1/2')).toBeInTheDocument();
      expect(screen.getByText('Review →')).toBeInTheDocument();
    });
  });

  // ── Concept drill coaching (drill-primary, path-secondary) ─────────────────

  function wirePaidInsights(weakest_concepts) {
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
      if (url === '/dashboard/insights') return Promise.resolve({ data: makeInsightsPayload({ weakest_concepts }) });
      return Promise.resolve({ data: makeDashboardPayload() });
    });
  }

  it('focus card drills the top weak concept for paying users (?drill=, not a question deep-link)', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'P', email: 'p@e.com', plan: 'pro' }, loading: false });
    wirePaidInsights([{ concept: 'GROUPED AGGREGATION', track: 'pandas', accuracy_pct: 0.33, attempts: 21 }]);

    renderDashboard();

    const card = (await screen.findByText('Drill GROUPED AGGREGATION')).closest('.db-focus-card');
    const cta = within(card).getByText('Go →');
    expect(cta.closest('a').getAttribute('href')).toMatch(/^\/practice\/pandas\?drill=/);
  });

  it('weak row offers a concept drill (primary) and the matching path as an honest secondary', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'P', email: 'p@e.com', plan: 'pro' }, loading: false });
    wirePaidInsights([{
      concept: 'GROUPED AGGREGATION', track: 'pandas', accuracy_pct: 0.33, attempts: 21,
      recommended_path_slug: 'groupby', recommended_path_title: 'GroupBy Aggregation',
    }]);

    renderDashboard();

    const primary = await screen.findByText('Drill this concept →');
    expect(primary.closest('a').getAttribute('href')).toMatch(/^\/practice\/pandas\?drill=/);
    const secondary = screen.getByText(/Or take the GroupBy Aggregation path/i);
    expect(secondary.closest('a').getAttribute('href')).toBe('/learn/pandas/groupby');
  });

  it('Pro sees the full weak-areas gap list — no Elite lock (decision B, 2026-06-13)', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'P', email: 'p@e.com', plan: 'pro' }, loading: false });
    wirePaidInsights([
      { concept: 'WINDOW FUNCTIONS', track: 'sql', accuracy_pct: 0.2, attempts: 12 },
      { concept: 'HASH JOIN', track: 'python', accuracy_pct: 0.3, attempts: 9 },
      { concept: 'SHUFFLE PARTITIONS', track: 'pyspark', accuracy_pct: 0.4, attempts: 6 },
    ]);
    renderDashboard();
    // Every gap is drillable for Pro — the full list, not just the top one.
    const drills = await screen.findAllByText('Drill this concept →');
    expect(drills).toHaveLength(3);
    // The old Elite-lock teaser is gone.
    expect(screen.queryByText(/Elite members see all gaps/i)).toBeNull();
  });

  it('Free sees the upgrade-to-Pro gate, not the weak concepts', async () => {
    mockUseAuth.mockReturnValue({ user: { name: 'F', email: 'f@e.com' }, loading: false });
    wirePaidInsights([
      { concept: 'WINDOW FUNCTIONS', track: 'sql', accuracy_pct: 0.2, attempts: 12 },
    ]);
    renderDashboard();
    expect(await screen.findByText(/Upgrade to Pro to see your weakest concepts/i)).toBeInTheDocument();
    expect(screen.queryByText('Drill this concept →')).toBeNull();
  });

  it('renders First-try accuracy section with fraction for SQL track', async () => {
    renderDashboard();

    expect(await screen.findByText('First-try accuracy')).toBeInTheDocument();
    expect(await screen.findByText('40/54')).toBeInTheDocument();
  });
});
