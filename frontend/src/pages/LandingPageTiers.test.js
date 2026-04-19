/**
 * LandingPage tier section tests.
 *
 * Verifies that the Free / Pro / Elite pricing columns show the correct CTAs
 * (upgrade buttons, "Current plan" badge, lifetime-switch links) for every
 * plan state a user can be in.
 *
 * The tier CTA logic lives in proColCta() / eliteColCta() inside LandingPage:
 *   proColCta():  'lifetime_pro' → 'current' | 'pro' → 'lifetime_only' |
 *                 'free' → 'both' | elite variants → 'none'
 *   eliteColCta(): 'lifetime_elite' → 'current' | 'elite' → 'lifetime_only' |
 *                  others → 'both'
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
      totalQuestions: 82,
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
    it('shows section heading "Simple pricing"', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Simple pricing')).toBeInTheDocument();
      });
    });

    it('shows ₹0 in the Free column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('₹0')).toBeInTheDocument();
      });
    });

    it('shows ₹799 in the Pro column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('₹799')).toBeInTheDocument();
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

    it('shows ₹1,599 in the Elite column', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('₹1,599')).toBeInTheDocument();
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

    it('shows "Lifetime access — ₹7,999" button in the Pro column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹7,999' })).toBeInTheDocument();
      });
    });

    it('shows "Upgrade to Elite" button in the Elite column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('shows "Lifetime access — ₹14,999" button in the Elite column', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹14,999' })).toBeInTheDocument();
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

  // ── monthly pro user (plan='pro') ─────────────────────────────────────────

  describe("monthly pro user (plan='pro')", () => {
    it('does not show "Upgrade to Pro" monthly button in Pro column', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
      });
    });

    it('shows "Switch to lifetime — ₹7,999" button in Pro column', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Switch to lifetime — ₹7,999' })).toBeInTheDocument();
      });
    });

    it('shows "Upgrade to Elite" button in Elite column', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('shows "Lifetime access — ₹14,999" button in Elite column', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹14,999' })).toBeInTheDocument();
      });
    });
  });

  // ── lifetime_pro user (plan='lifetime_pro') ────────────────────────────────

  describe("lifetime_pro user (plan='lifetime_pro')", () => {
    it('shows "Current plan" in the Pro column', async () => {
      renderWithPlan('lifetime_pro');
      await waitFor(() => {
        expect(screen.getByText('Current plan')).toBeInTheDocument();
      });
    });

    it('does not show any upgrade button in the Pro column', async () => {
      renderWithPlan('lifetime_pro');
      await waitFor(() => {
        // proColCta() === 'current' — neither monthly nor lifetime Pro button rendered
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /₹7,999/ })).not.toBeInTheDocument();
      });
    });

    it('shows "Upgrade to Elite" button in Elite column', async () => {
      renderWithPlan('lifetime_pro');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('shows "Lifetime access — ₹14,999" button in Elite column', async () => {
      renderWithPlan('lifetime_pro');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Lifetime access — ₹14,999' })).toBeInTheDocument();
      });
    });
  });

  // ── monthly elite user (plan='elite') ─────────────────────────────────────

  describe("monthly elite user (plan='elite')", () => {
    it('shows no CTA buttons in the Pro column', async () => {
      renderWithPlan('elite');
      await waitFor(() => {
        // proColCta() === 'none' — neither monthly Pro nor lifetime Pro rendered
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /₹7,999/ })).not.toBeInTheDocument();
      });
    });

    it('shows "Switch to lifetime — ₹14,999" in the Elite column', async () => {
      renderWithPlan('elite');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Switch to lifetime — ₹14,999' })).toBeInTheDocument();
      });
    });

    it('does not show "Upgrade to Elite" monthly button', async () => {
      renderWithPlan('elite');
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: 'Upgrade to Elite' })).not.toBeInTheDocument();
      });
    });
  });

  // ── lifetime_elite user (plan='lifetime_elite') ────────────────────────────

  describe("lifetime_elite user (plan='lifetime_elite')", () => {
    it('shows "Current plan" in the Elite column', async () => {
      renderWithPlan('lifetime_elite');
      await waitFor(() => {
        expect(screen.getByText('Current plan')).toBeInTheDocument();
      });
    });

    it('does not render any upgrade buttons', async () => {
      renderWithPlan('lifetime_elite');
      await waitFor(() => {
        // proColCta() === 'none', eliteColCta() === 'current' — no buttons at all
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Upgrade to Elite' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Switch to lifetime/ })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /Lifetime access/ })).not.toBeInTheDocument();
      });
    });
  });
});
