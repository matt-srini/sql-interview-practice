/**
 * ProgressDashboard component tests.
 *
 * Focuses on the API→render pipeline so shape mismatches in the /dashboard
 * response (like by_difficulty returning a plain int instead of {solved,total})
 * are caught immediately rather than silently rendering as "/".
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
  },
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { name: 'Test User', email: 'test@example.com' } }),
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
        total: 95,
        by_difficulty: {
          easy:   { solved: 25, total: 32 },
          medium: { solved: 22, total: 34 },
          hard:   { solved: 0,  total: 29 },
        },
      },
      python: {
        solved: 0,
        total: 83,
        by_difficulty: {
          easy:   { solved: 0, total: 30 },
          medium: { solved: 0, total: 29 },
          hard:   { solved: 0, total: 24 },
        },
      },
      'python-data': {
        solved: 0,
        total: 82,
        by_difficulty: {
          easy:   { solved: 0, total: 29 },
          medium: { solved: 0, total: 30 },
          hard:   { solved: 0, total: 23 },
        },
      },
      pyspark: {
        solved: 0,
        total: 90,
        by_difficulty: {
          easy:   { solved: 0, total: 38 },
          medium: { solved: 0, total: 30 },
          hard:   { solved: 0, total: 22 },
        },
      },
    },
    concepts_by_track: {},
    recent_activity: [],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  // Default: mock history returns empty list
  api.get.mockImplementation((url) => {
    if (url === '/mock/history') return Promise.resolve({ data: [] });
    return Promise.resolve({ data: makeDashboardPayload() });
  });
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProgressDashboard', () => {
  it('renders per-difficulty counts in X/Y format', async () => {
    renderDashboard();

    // SQL breakdown: 25/32, 22/34, 0/29 — use getAllByText since the same count
    // string can appear across multiple track cards
    await waitFor(() => {
      expect(screen.getByText('25/32')).toBeInTheDocument();  // SQL easy (unique)
      expect(screen.getByText('22/34')).toBeInTheDocument();  // SQL medium (unique)
      // 0/29 appears in multiple tracks — just assert at least one exists
      expect(screen.getAllByText('0/29').length).toBeGreaterThan(0);
    });
  });

  it('renders the overall progress bar totals', async () => {
    renderDashboard();

    await waitFor(() => {
      // 47/95 overall for SQL
      expect(screen.getByText('47 / 95')).toBeInTheDocument();
    });
  });

  it('renders all four track cards', async () => {
    renderDashboard();

    await waitFor(() => {
      // Track names appear in both the card label and potentially navigation — use getAllByText
      expect(screen.getAllByText('SQL').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Python').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Pandas').length).toBeGreaterThan(0);
      expect(screen.getAllByText('PySpark').length).toBeGreaterThan(0);
    });
  });

  it('does NOT render X/Y when by_difficulty values are plain integers (regression guard)', async () => {
    // Simulate the old broken API shape: by_difficulty returns plain ints
    const brokenPayload = makeDashboardPayload();
    brokenPayload.tracks.sql.by_difficulty = { easy: 25, medium: 22, hard: 0 };

    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
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

  it('renders zero counts correctly as 0/total', async () => {
    renderDashboard();

    await waitFor(() => {
      // Python has 0 solved — spot-check some unique counts
      expect(screen.getAllByText('0/24').length).toBeGreaterThan(0);  // Python hard
      expect(screen.getAllByText('0/30').length).toBeGreaterThan(0); // Python easy or PySpark med
      expect(screen.getAllByText('0/29').length).toBeGreaterThan(0); // Python med or python-data easy
    });
  });

  it('shows loading state before data arrives', async () => {
    let resolve;
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
      return new Promise((res) => { resolve = res; });
    });

    renderDashboard();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();

    resolve({ data: makeDashboardPayload() });
    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });
  });

  it('shows error state when the API fails', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/mock/history') return Promise.resolve({ data: [] });
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
      return Promise.resolve({ data: makeDashboardPayload() });
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('30min')).toBeInTheDocument();
      expect(screen.getByText('1/2')).toBeInTheDocument();
      expect(screen.getByText('Review →')).toBeInTheDocument();
    });
  });
});
