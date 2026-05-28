/**
 * LandingPage — Phase E tests.
 *
 * Covers: hero variants (logged-out / logged-in), role selector,
 * tracks index (live + coming-soon), and pricing section visibility.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ---------------------------------------------------------------------------
// Module-level mocks
// ---------------------------------------------------------------------------

vi.mock('../api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('../App', () => ({
  useTheme: () => ({ theme: 'light', setTheme: () => {} }),
}));

// TRACK_META mock — includes the full 9-track catalog
vi.mock('../contexts/TopicContext', () => ({
  TRACK_META: {
    sql:                { label: 'SQL',              description: 'SQL queries',                color: '#5B6AF0', totalQuestions: 112, tagline: 'SQL · DuckDB' },
    python:             { label: 'Python',           description: 'Python algorithms',           color: '#2D9E6B', totalQuestions: 95,  tagline: 'Python · sandbox' },
    'python-data':      { label: 'Pandas',           description: 'Pandas wrangling',            color: '#C47F17', totalQuestions: 86,  tagline: 'Pandas · sandbox' },
    pyspark:            { label: 'PySpark',          description: 'Spark concepts',              color: '#D94F3D', totalQuestions: 106, tagline: 'reasoning · predict output' },
    'data-engineering': { label: 'Data Engineering', description: 'DE concepts',                 color: '#B9762B', totalQuestions: 86,  tagline: 'reasoning · scenario' },
    'data-modeling':    { label: 'Data Modeling',    description: 'Dimensional modeling',        color: '#3F8E8C', totalQuestions: 76,  tagline: 'reasoning · schema design' },
    statistics:         { label: 'Statistics',       description: 'Probability and inference',   color: '#7A5AF0', totalQuestions: 97,  tagline: 'conceptual + numerical' },
    'ml-fundamentals':  { label: 'ML Fundamentals',  description: 'ML interview reasoning',      color: '#E0456A', totalQuestions: 90,  tagline: 'model reasoning · scenario · debug' },
    experimentation:    { label: 'Experimentation',  description: 'A/B testing and inference',   color: '#0EA5E9', totalQuestions: 80,  tagline: 'experiment reasoning · scenario · predict output' },
  },
  TopicProvider: ({ children }) => children,
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL' } }),
}));

// trackRegistry mock — must match TRACK_META above
vi.mock('../trackRegistry', () => ({
  TRACK_SLUGS:     ['sql', 'python', 'python-data', 'pyspark', 'data-engineering', 'data-modeling', 'statistics', 'ml-fundamentals', 'experimentation'],
  ALL_TRACK_SLUGS: ['sql', 'python', 'python-data', 'pyspark', 'data-engineering', 'data-modeling', 'statistics', 'ml-fundamentals', 'experimentation'],
  TRACK_META: {
    sql:                { label: 'SQL',              description: 'SQL queries',              color: '#5B6AF0', totalQuestions: 112, tagline: 'SQL · DuckDB' },
    python:             { label: 'Python',           description: 'Python algorithms',         color: '#2D9E6B', totalQuestions: 95,  tagline: 'Python · sandbox' },
    'python-data':      { label: 'Pandas',           description: 'Pandas wrangling',          color: '#C47F17', totalQuestions: 86,  tagline: 'Pandas · sandbox' },
    pyspark:            { label: 'PySpark',          description: 'Spark concepts',            color: '#D94F3D', totalQuestions: 106, tagline: 'reasoning · predict output' },
    'data-engineering': { label: 'Data Engineering', description: 'DE concepts',               color: '#B9762B', totalQuestions: 86,  tagline: 'reasoning · scenario' },
    'data-modeling':    { label: 'Data Modeling',    description: 'Dimensional modeling',      color: '#3F8E8C', totalQuestions: 76,  tagline: 'reasoning · schema design' },
    statistics:         { label: 'Statistics',       description: 'Probability and inference', color: '#7A5AF0', totalQuestions: 97,  tagline: 'conceptual + numerical' },
    'ml-fundamentals':  { label: 'ML Fundamentals',  description: 'ML interview reasoning',    color: '#E0456A', totalQuestions: 90,  tagline: 'model reasoning · scenario · debug' },
    experimentation:    { label: 'Experimentation',  description: 'A/B testing and inference', color: '#0EA5E9', totalQuestions: 80,  tagline: 'experiment reasoning · scenario · predict output' },
  },
  TRACK_LABELS: {
    sql: 'SQL', python: 'Python', 'python-data': 'Pandas', pyspark: 'PySpark',
    'data-engineering': 'Data Engineering', 'data-modeling': 'Data Modeling',
    statistics: 'Statistics', 'ml-fundamentals': 'ML Fundamentals', experimentation: 'Experimentation', mixed: 'Mixed',
  },
}));

vi.mock('../utils/currency', () => ({
  detectCurrency: () => 'INR',
  PRICES: {
    INR: { pro: '₹999', elite: '₹1,999', period: '/mo', lifetimePro: '₹11,999', lifetimeElite: '₹19,999' },
  },
}));

import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import LandingPage from './LandingPage';

// ---------------------------------------------------------------------------
// Browser stubs
// ---------------------------------------------------------------------------

global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// jsdom does not implement matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn((query) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

const mockAssign = vi.fn();
Object.defineProperty(window, 'location', {
  value: { ...window.location, assign: mockAssign },
  writable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderWithPlan(plan) {
  const user = plan === null ? null : { id: 1, email: 'user@example.com', plan, streak_days: 0 };
  useAuth.mockReturnValue({ user, logout: vi.fn(), refreshUser: vi.fn() });
  return render(<MemoryRouter><LandingPage /></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation((url) => {
    if (url === '/dashboard') return Promise.resolve({ data: {} });
    if (url === '/paths')     return Promise.resolve({ data: [] });
    return Promise.resolve({ data: {} });
  });
  api.post.mockResolvedValue({ data: {} });
});

afterEach(() => cleanup());

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('LandingPage', () => {

  // ── Hero section ──────────────────────────────────────────────────────────

  describe('Hero — logged-out', () => {
    it('shows the hero headline', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
      });
      expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(/reason/i);
    });

    it('shows a no-login free sample CTA link', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        const links = screen.getAllByRole('link', { name: /try a free sample/i });
        expect(links.length).toBeGreaterThanOrEqual(1);
        expect(links.some((link) => link.getAttribute('href') === '/sample/sql/easy')).toBe(true);
      });
    });
  });

  describe('Hero — logged-in', () => {
    it('shows resume, dashboard, and mock cards', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByText('Resume')).toBeInTheDocument();
        // "Dashboard" also appears in Topbar nav — verify the card title specifically
        expect(screen.getByText('Dashboard', { selector: '.lp-li-card-title' })).toBeInTheDocument();
        expect(screen.getByText('Mock session')).toBeInTheDocument();
      });
    });

    it('does not show the hero headline for logged-in users', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.queryByText(/test how you reason/i)).not.toBeInTheDocument();
      });
    });
  });

  // ── Role selector ─────────────────────────────────────────────────────────

  describe('Role selector', () => {
    it('renders all 4 role tabs', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Data Analyst' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Data Engineer' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Analytics Engineer' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Data Scientist' })).toBeInTheDocument();
      });
    });

    it('Data Analyst tab is selected by default', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Data Analyst' })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('Data Analyst panel shows SQL track', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        const panel = screen.getByRole('tabpanel');
        expect(panel).toBeInTheDocument();
        expect(panel.textContent).toMatch(/SQL/);
      });
    });

    it('switching to Data Engineer shows Python and PySpark tracks', async () => {
      renderWithPlan(null);
      await waitFor(() => screen.getByRole('tab', { name: 'Data Engineer' }));
      fireEvent.click(screen.getByRole('tab', { name: 'Data Engineer' }));
      await waitFor(() => {
        const panel = screen.getByRole('tabpanel');
        expect(panel.textContent).toMatch(/Python/);
        expect(panel.textContent).toMatch(/PySpark/);
      });
    });

    it('Data Engineer panel shows Data Modeling as an active track', async () => {
      renderWithPlan(null);
      await waitFor(() => screen.getByRole('tab', { name: 'Data Engineer' }));
      fireEvent.click(screen.getByRole('tab', { name: 'Data Engineer' }));
      await waitFor(() => {
        const panel = screen.getByRole('tabpanel');
        expect(panel.textContent).toMatch(/Data Modeling/);
        const panelLinks = within(panel).getAllByRole('link', { name: /open track/i });
        expect(panelLinks.some((link) => link.getAttribute('href') === '/practice/data-modeling')).toBe(true);
      });
    });

    it('Data Analyst panel shows Statistics as an active track', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        const panel = screen.getByRole('tabpanel');
        expect(panel.textContent).toMatch(/Statistics/);
        expect(panel.textContent).not.toMatch(/Coming soon/);
      });
    });

    it('Data Scientist panel shows ML Fundamentals and Experimentation', async () => {
      renderWithPlan(null);
      await waitFor(() => screen.getByRole('tab', { name: 'Data Scientist' }));
      fireEvent.click(screen.getByRole('tab', { name: 'Data Scientist' }));
      await waitFor(() => {
        const panel = screen.getByRole('tabpanel');
        expect(panel.textContent).toMatch(/ML Fundamentals/);
        expect(panel.textContent).toMatch(/Experimentation/);
      });
    });
  });

  // ── Tracks index ──────────────────────────────────────────────────────────

  describe('Tracks index', () => {
    it('shows all 9 tracks', async () => {
      renderWithPlan(null);
      const trackNames = ['SQL', 'Python', 'Pandas', 'PySpark', 'Data Engineering', 'Data Modeling', 'Statistics', 'ML Fundamentals', 'Experimentation'];
      // Use the tracks section specifically
      for (const name of trackNames) {
        await waitFor(() => {
          const els = screen.getAllByText(name);
          expect(els.length).toBeGreaterThanOrEqual(1);
        });
      }
    });

    it('shows no "Coming soon" badges for the canonical 9-track catalog', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.queryByText('Coming soon')).not.toBeInTheDocument();
      });
    });

    it('shows "Enter →" links for active tracks', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        const enterLinks = screen.getAllByRole('link', { name: /open .* track/i });
        expect(enterLinks.length).toBeGreaterThanOrEqual(9);
      });
    });
  });

  // ── Pricing section ───────────────────────────────────────────────────────

  describe('Pricing display', () => {
    it('shows "Practice free. Prepare seriously." heading for anonymous users', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Practice free. Prepare seriously.')).toBeInTheDocument();
      });
    });

    it('shows ₹999 in the Pro column', async () => {
      renderWithPlan(null);
      await waitFor(() => expect(screen.getByText('₹999')).toBeInTheDocument());
    });

    it('shows ₹1,999 in the Elite column', async () => {
      renderWithPlan(null);
      await waitFor(() => expect(screen.getByText('₹1,999')).toBeInTheDocument());
    });

    it('shows "Most popular" badge', async () => {
      renderWithPlan(null);
      await waitFor(() => expect(screen.getByText('Most popular')).toBeInTheDocument());
    });

    it('free user sees "Current plan" in the Free column', async () => {
      renderWithPlan('free');
      await waitFor(() => expect(screen.getByText('Current plan')).toBeInTheDocument());
    });

    it('free user sees Upgrade to Pro and Upgrade to Elite buttons', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('hides the pricing section for lifetime_elite users', async () => {
      renderWithPlan('lifetime_elite');
      await waitFor(() => {
        expect(screen.queryByText('Practice free. Prepare seriously.')).not.toBeInTheDocument();
      });
    });

    it('shows pricing for pro users (so they can see Elite upgrade)', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.getByText('Practice free. Prepare seriously.')).toBeInTheDocument();
      });
    });
  });

});
