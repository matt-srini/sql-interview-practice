/**
 * ProgressDashboard component tests.
 *
 * Focuses on the API→render pipeline so dashboard response-shape drift is caught
 * against the current 9-track track-overview and mock-history UI.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../contexts/AuthContext', () => {
  // Stable reference so useEffect([authLoading, user]) doesn't re-fire on every render
  const stableUser = { name: 'Test User', email: 'test@example.com' };
  return {
    useAuth: () => ({ user: stableUser, loading: false }),
  };
});

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
      'python-data': {
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
    },
    concepts_by_track: {},
    recent_activity: [],
    ...overrides,
  };
}

function makeInsightsPayload(overrides = {}) {
  return {
    per_track: {
      sql: { solve_count: 47, median_solve_seconds: 540, accuracy_pct: 0.82 },
      python: { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      'python-data': { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      pyspark: { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      'data-engineering': { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      'data-modeling': { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      statistics: { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      'ml-fundamentals': { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
      experimentation: { solve_count: 0, median_solve_seconds: null, accuracy_pct: 0 },
    },
    weakest_concepts: [],
    cross_track_insight: null,
    streak_days: 0,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
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

  it('renders all nine track rows', async () => {
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
    });
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
});
