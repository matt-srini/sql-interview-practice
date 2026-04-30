/**
 * LandingPage tier section tests.
 *
 * Verifies that anonymous/free users see the Free / Pro / Elite pricing
 * columns, and that paid users no longer see landing-tier upgrade CTAs.
 *
 * The tier section is now intentionally hidden for all paying users.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ---------------------------------------------------------------------------
// Module-level mocks — must be declared before any component imports
// ---------------------------------------------------------------------------

vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// AuthContext — controlled per test via renderWithPlan()
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

// useTheme — minimal stub; LandingPage and Topbar both call it
vi.mock('../App', () => ({
  useTheme: () => ({ theme: 'light', setTheme: () => {}, resolvedTheme: 'light' }),
}));

// TopicContext — LandingPage imports TRACK_META from here; provide a minimal stub
vi.mock('../contexts/TopicContext', () => ({
  TRACK_META: {
    sql: {
      label: 'SQL',
      description: 'Write queries against realistic datasets',
      color: '#5B6AF0',
      totalQuestions: 95,
    },
    python: {
      label: 'Python',
      description: 'Algorithms and data structures',
      color: '#2D9E6B',
      totalQuestions: 83,
    },
    'python-data': {
      label: 'Pandas',
      description: 'pandas and numpy data manipulation',
      color: '#C47F17',
      totalQuestions: 76,
    },
    pyspark: {
      label: 'PySpark',
      description: 'Spark architecture and concepts',
      color: '#D94F3D',
      totalQuestions: 90,
    },
  },
  TopicProvider: ({ children }) => children,
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL' } }),
}));

vi.mock('../utils/currency', () => ({
  detectCurrency: () => 'INR',
  PRICES: {
    INR: {
      pro: '₹999',
      elite: '₹1,999',
      period: '/mo',
      lifetimePro: '₹11,999',
      lifetimeElite: '₹19,999',
    },
  },
}));

import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import LandingPage from './LandingPage';

// ---------------------------------------------------------------------------
// Browser API stubs required by LandingPage in jsdom
// ---------------------------------------------------------------------------

// IntersectionObserver is used by the showcase section visibility effect
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// window.location.assign is called by UpgradeButton on checkout success
const mockAssign = vi.fn();
Object.defineProperty(window, 'location', {
  value: { ...window.location, assign: mockAssign },
  writable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Render LandingPage with a mocked user whose plan is `plan`.
 * Pass plan=null to simulate a logged-out / anonymous visitor.
 * userPlan = user?.plan ?? 'free', so null → 'free' from the tier section's view.
 */
function renderWithPlan(plan) {
  const user = plan === null ? null : { id: 1, email: 'user@example.com', plan };
  useAuth.mockReturnValue({ user, logout: vi.fn() });

  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  // Default API stubs — return minimal shapes so the page doesn't crash
  api.get.mockImplementation((url) => {
    if (url === '/dashboard') return Promise.resolve({ data: {} });
    if (url === '/paths')    return Promise.resolve({ data: [] });
    return Promise.resolve({ data: {} });
  });
  api.post.mockResolvedValue({ data: {} });
});

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LandingPage tier section', () => {

  // ── Pricing display ────────────────────────────────────────────────────────

  describe('Pricing display', () => {
    it('shows section heading "Straightforward pricing"', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Straightforward pricing')).toBeInTheDocument();
      });
    });

    it('shows "Free" in the Free column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Free', { selector: '.landing-tier-price-amount' })).toBeInTheDocument();
      });
    });

    it('shows ₹999 in the Pro column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('₹999')).toBeInTheDocument();
      });
    });

    it('shows /mo price period in the Pro column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        // Both Pro and Elite have /mo — assert at least one exists
        const periods = screen.getAllByText('/mo');
        expect(periods.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('shows ₹1,999 in the Elite column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('₹1,999')).toBeInTheDocument();
      });
    });

    it('shows "Most popular" badge in the Pro column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Most popular')).toBeInTheDocument();
      });
    });
  });

  // ── free user (plan='free') ────────────────────────────────────────────────

  describe("free user (plan='free')", () => {
    it('shows "Current plan" in the Free column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByText('Current plan')).toBeInTheDocument();
      });
    });

    it('shows "Upgrade to Pro" button in the Pro column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
      });
    });

    it('shows "Lifetime access — ₹11,999" button in the Pro column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹11,999' })).toBeInTheDocument();
      });
    });

    it('shows "Upgrade to Elite" button in the Elite column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('shows "Lifetime access — ₹19,999" button in the Elite column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹19,999' })).toBeInTheDocument();
      });
    });

    it('does not show "Current plan" badge in Pro or Elite columns', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        // Only one "Current plan" span should exist — in the Free column
        expect(screen.getAllByText('Current plan')).toHaveLength(1);
      });
    });
  });

  // ── paying users ─────────────────────────────────────────────────────────

  describe('paying users', () => {
    it.each(['pro', 'lifetime_pro', 'elite', 'lifetime_elite'])(
      "hides the pricing section for plan='%s'",
      async (plan) => {
        renderWithPlan(plan);
        await waitFor(() => {
          expect(screen.queryByText('Straightforward pricing')).not.toBeInTheDocument();
          expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
          expect(screen.queryByRole('button', { name: 'Upgrade to Elite' })).not.toBeInTheDocument();
          expect(screen.queryByRole('button', { name: /Switch to lifetime/ })).not.toBeInTheDocument();
          expect(screen.queryByRole('button', { name: /Lifetime access/ })).not.toBeInTheDocument();
        });
      }
    );
  });
});
