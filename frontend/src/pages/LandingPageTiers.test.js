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
    'pandas':      { label: 'Pandas',           description: 'Pandas wrangling',            color: '#C47F17', totalQuestions: 86,  tagline: 'Pandas · sandbox' },
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
  TRACK_SLUGS:     ['sql', 'python', 'pandas', 'pyspark', 'data-engineering', 'data-modeling', 'statistics', 'ml-fundamentals', 'experimentation'],
  ALL_TRACK_SLUGS: ['sql', 'python', 'pandas', 'pyspark', 'data-engineering', 'data-modeling', 'statistics', 'ml-fundamentals', 'experimentation'],
  TRACK_META: {
    sql:                { label: 'SQL',              description: 'SQL queries',              color: '#5B6AF0', totalQuestions: 112, tagline: 'SQL · DuckDB' },
    python:             { label: 'Python',           description: 'Python algorithms',         color: '#2D9E6B', totalQuestions: 95,  tagline: 'Python · sandbox' },
    'pandas':      { label: 'Pandas',           description: 'Pandas wrangling',          color: '#C47F17', totalQuestions: 86,  tagline: 'Pandas · sandbox' },
    pyspark:            { label: 'PySpark',          description: 'Spark concepts',            color: '#D94F3D', totalQuestions: 106, tagline: 'reasoning · predict output' },
    'data-engineering': { label: 'Data Engineering', description: 'DE concepts',               color: '#B9762B', totalQuestions: 86,  tagline: 'reasoning · scenario' },
    'data-modeling':    { label: 'Data Modeling',    description: 'Dimensional modeling',      color: '#3F8E8C', totalQuestions: 76,  tagline: 'reasoning · schema design' },
    statistics:         { label: 'Statistics',       description: 'Probability and inference', color: '#7A5AF0', totalQuestions: 97,  tagline: 'conceptual + numerical' },
    'ml-fundamentals':  { label: 'ML Fundamentals',  description: 'ML interview reasoning',    color: '#E0456A', totalQuestions: 90,  tagline: 'model reasoning · scenario · debug' },
    experimentation:    { label: 'Experimentation',  description: 'A/B testing and inference', color: '#0EA5E9', totalQuestions: 80,  tagline: 'experiment reasoning · scenario · predict output' },
  },
  TRACK_LABELS: {
    sql: 'SQL', python: 'Python', 'pandas': 'Pandas', pyspark: 'PySpark',
    'data-engineering': 'Data Engineering', 'data-modeling': 'Data Modeling',
    statistics: 'Statistics', 'ml-fundamentals': 'ML Fundamentals', experimentation: 'Experimentation', mixed: 'Mixed',
  },
}));

vi.mock('../utils/currency', () => ({
  detectCurrency: () => 'INR',
  railForCurrency: (c) => (c === 'INR' ? 'razorpay' : 'paddle'),
  PRICES: {
    INR: { pro: '₹999', elite: '₹1,999', period: '/mo', lifetimePro: '₹11,999', lifetimeElite: '₹19,999' },
    USD: { pro: '$15', elite: '$25', period: '/mo', lifetimePro: '$149', lifetimeElite: '$249' },
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

const MOCK_DASHBOARD_DATA = {
  tracks: {
    sql:                { solved: 5, total: 37, by_difficulty: {} },
    python:             { solved: 2, total: 33, by_difficulty: {} },
    'pandas':      { solved: 0, total: 28, by_difficulty: {} },
    pyspark:            { solved: 0, total: 40, by_difficulty: {} },
    'data-engineering': { solved: 0, total: 30, by_difficulty: {} },
    'data-modeling':    { solved: 0, total: 25, by_difficulty: {} },
    statistics:         { solved: 0, total: 31, by_difficulty: {} },
    'ml-fundamentals':  { solved: 0, total: 30, by_difficulty: {} },
    experimentation:    { solved: 0, total: 30, by_difficulty: {} },
  },
  recent_activity: [{ topic: 'sql', question_id: 1 }],
};

const MOCK_INSIGHTS_DATA = {
  weakest_concepts: [],
  streak_days: 3,
};

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation((url) => {
    if (url === '/dashboard')          return Promise.resolve({ data: MOCK_DASHBOARD_DATA });
    if (url === '/dashboard/insights') return Promise.resolve({ data: MOCK_INSIGHTS_DATA });
    if (url === '/paths')              return Promise.resolve({ data: [] });
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
        // The hero CTA points at the Sample Hub discovery surface (/sample), not a
        // hard-coded per-track deep link.
        expect(links.some((link) => link.getAttribute('href') === '/sample')).toBe(true);
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

    it('Data Engineer tab is selected by default', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Data Engineer' })).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('Data Analyst panel shows SQL track', async () => {
      renderWithPlan(null);
      await waitFor(() => screen.getByRole('tab', { name: 'Data Analyst' }));
      fireEvent.click(screen.getByRole('tab', { name: 'Data Analyst' }));
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
      await waitFor(() => screen.getByRole('tab', { name: 'Data Analyst' }));
      fireEvent.click(screen.getByRole('tab', { name: 'Data Analyst' }));
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

    // Logged-in users see UpgradeNudge (slim banner), NOT the full PricingSection.
    it('free logged-in user sees upgrade nudge — not the full pricing table', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        // Slim nudge copy — not the full pricing heading
        expect(screen.queryByText('Practice free. Prepare seriously.')).not.toBeInTheDocument();
        // Both Pro and Elite upgrade buttons are present in the slim nudge
        expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
      });
    });

    it('pro logged-in user sees Elite nudge — not the full pricing table', async () => {
      renderWithPlan('pro');
      await waitFor(() => {
        expect(screen.queryByText('Practice free. Prepare seriously.')).not.toBeInTheDocument();
        // Only the Elite upgrade button in the nudge
        expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
      });
    });

    it('lifetime_elite logged-in user sees neither pricing table nor nudge', async () => {
      renderWithPlan('lifetime_elite');
      await waitFor(() => {
        expect(screen.queryByText('Practice free. Prepare seriously.')).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Upgrade to Pro' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Upgrade to Elite' })).not.toBeInTheDocument();
      });
    });
  });

  // ── Learning paths showcase (06.5) ────────────────────────────────────────

  describe('Learning paths showcase', () => {
    // 6 SQL paths (>SPINE_MAX of 5 → triggers "+1 more") spanning all 3 levels,
    // deliberately out of arc order to prove the component sorts by (level,
    // display_order). Plus one path each in two other tracks for the breadth strip.
    const MOCK_PATHS = [
      { slug: 'sql-sub',    title: 'Subqueries & Existence', topic: 'sql',    level: 'advanced',     display_order: 1, question_count: 6,  solved_count: 0 },
      { slug: 'sql-agg',    title: 'Aggregation Patterns',   topic: 'sql',    level: 'foundational', display_order: 1, question_count: 15, solved_count: 0 },
      { slug: 'sql-window', title: 'Window Functions',       topic: 'sql',    level: 'intermediate', display_order: 2, question_count: 9,  solved_count: 3 },
      { slug: 'sql-joins',  title: 'Joins & Filtering',      topic: 'sql',    level: 'intermediate', display_order: 1, question_count: 15, solved_count: 0 },
      { slug: 'sql-pivot',  title: 'Pivot & Conditional',    topic: 'sql',    level: 'intermediate', display_order: 3, question_count: 7,  solved_count: 0 },
      { slug: 'sql-adv',    title: 'Advanced Patterns',      topic: 'sql',    level: 'advanced',     display_order: 2, question_count: 8,  solved_count: 0 },
      { slug: 'py-arrays',  title: 'Arrays & Hashing',       topic: 'python', level: 'foundational', display_order: 1, question_count: 10, solved_count: 0 },
      { slug: 'spark-dag',  title: 'Spark DAG',              topic: 'pyspark',level: 'foundational', display_order: 1, question_count: 8,  solved_count: 0 },
    ];

    function mockPaths(paths) {
      api.get.mockImplementation((url) => {
        if (url === '/dashboard')          return Promise.resolve({ data: MOCK_DASHBOARD_DATA });
        if (url === '/dashboard/insights') return Promise.resolve({ data: MOCK_INSIGHTS_DATA });
        if (url === '/paths')              return Promise.resolve({ data: paths });
        return Promise.resolve({ data: {} });
      });
    }

    it('renders the section headline and funnels to /learn (not a single path)', async () => {
      mockPaths(MOCK_PATHS);
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('Systematic patterns, not scattered reps.')).toBeInTheDocument();
      });
      const cta = screen.getByRole('link', { name: /explore all paths/i });
      expect(cta).toHaveAttribute('href', '/learn');
    });

    it('shows the featured SQL arc sorted foundational→advanced, capped at 5 steps', async () => {
      mockPaths(MOCK_PATHS);
      const { container } = renderWithPlan(null);
      await waitFor(() => expect(container.querySelector('.lp-paths-arc')).toBeInTheDocument());

      const titles = [...container.querySelectorAll('.lp-paths-step-title')].map(e => e.textContent);
      // SPINE_MAX = 5; foundational first, then intermediate by display_order, then advanced
      expect(titles).toEqual([
        'Aggregation Patterns',
        'Joins & Filtering',
        'Window Functions',
        'Pivot & Conditional',
        'Subqueries & Existence',
      ]);
      const levels = [...container.querySelectorAll('.lp-paths-step-level')].map(e => e.textContent);
      expect(levels[0]).toBe('foundational');
      expect(levels[4]).toBe('advanced');

      // The whole arc links to the track's /learn page, never a leaf path
      expect(container.querySelector('.lp-paths-arc')).toHaveAttribute('href', '/learn/sql');
      // 6 SQL paths − 5 shown = "+1 more"
      expect(screen.getByText(/\+1 more in SQL/i)).toBeInTheDocument();
    });

    it('shows a breadth chip per track with path counts, each linking to /learn/:topic', async () => {
      mockPaths(MOCK_PATHS);
      const { container } = renderWithPlan(null);
      await waitFor(() => expect(container.querySelector('.lp-paths-tracklist')).toBeInTheDocument());

      const chips = [...container.querySelectorAll('.lp-paths-trackchip')];
      // Only the 3 tracks that have paths appear (sql, python, pyspark)
      expect(chips).toHaveLength(3);
      const sqlChip = chips.find(c => c.getAttribute('href') === '/learn/sql');
      expect(sqlChip).toBeTruthy();
      // count is number-only on screen; the unit lives in the aria-label
      const sqlCount = sqlChip.querySelector('.lp-paths-trackchip-count');
      expect(sqlCount.textContent).toBe('6');
      expect(sqlCount.getAttribute('aria-label')).toMatch(/6 paths/);
      const pyCount = chips.find(c => c.getAttribute('href') === '/learn/python').querySelector('.lp-paths-trackchip-count');
      expect(pyCount.textContent).toBe('1');
      expect(pyCount.getAttribute('aria-label')).toMatch(/1 path\b/);
      // Stat reflects derived totals (3 tracks · 8 paths)
      const stat = container.querySelector('.lp-paths-breadth-stat').textContent;
      expect(stat).toMatch(/3/);
      expect(stat).toMatch(/8/);
    });

    it('has no shuffle control (the old random-4 pattern is gone)', async () => {
      mockPaths(MOCK_PATHS);
      renderWithPlan(null);
      await waitFor(() => screen.getByText('Systematic patterns, not scattered reps.'));
      expect(screen.queryByRole('button', { name: /shuffle/i })).not.toBeInTheDocument();
    });

    it('shows in-progress paths for logged-in users via ContinuePathsSection', async () => {
      mockPaths(MOCK_PATHS);
      renderWithPlan('pro');
      // sql-window is the only in-progress path (3/9) → appears in ContinuePathsSection
      await waitFor(() => {
        expect(screen.getByText('Window Functions')).toBeInTheDocument();
      });
      // The PathProgressCard links to /learn/sql/sql-window
      const pathLinks = screen.getAllByRole('link', { name: /window functions/i });
      expect(pathLinks.some(l => l.getAttribute('href') === '/learn/sql/sql-window')).toBe(true);
    });

    it('shows no resume hook for logged-out visitors even with prior progress', async () => {
      mockPaths(MOCK_PATHS);
      renderWithPlan(null);
      await waitFor(() => screen.getByText('Systematic patterns, not scattered reps.'));
      expect(screen.queryByText(/continue:/i)).not.toBeInTheDocument();
    });

    it('renders nothing when there are no paths', async () => {
      mockPaths([]);
      renderWithPlan(null);
      // Other sections still render; the paths headline must be absent
      await waitFor(() => expect(screen.getByText('Practice free. Prepare seriously.')).toBeInTheDocument());
      expect(screen.queryByText('Systematic patterns, not scattered reps.')).not.toBeInTheDocument();
    });
  });

  // ── Logged-in home vs. marketing pitch ───────────────────────────────────

  describe('Logged-in home utility vs. logged-out marketing', () => {
    it('logged-in user sees utility sections and NOT the marketing tracks pitch', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        // Utility sections present
        expect(screen.getByText('Continue your paths.')).toBeInTheDocument();
        expect(screen.getByText('Jump back in.')).toBeInTheDocument();
      });
      // Marketing tracks pitch absent
      expect(screen.queryByText('A curriculum, not a question bank.')).not.toBeInTheDocument();
      // Role selector absent
      expect(screen.queryByRole('tablist', { name: /select your data role/i })).not.toBeInTheDocument();
    });

    it('logged-out user sees the marketing tracks pitch and NOT the utility home', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        expect(screen.getByText('A curriculum, not a question bank.')).toBeInTheDocument();
      });
      // Utility sections absent
      expect(screen.queryByText('Jump back in.')).not.toBeInTheDocument();
      expect(screen.queryByText('Continue your paths.')).not.toBeInTheDocument();
    });
  });

  // ── Logged-in home: Topbar Paths link, All-paths link, role filter ────────
  describe('Logged-in home — Paths reachability & role filter', () => {
    it('Topbar exposes a Paths link to /learn', async () => {
      renderWithPlan('free');
      await waitFor(() => {
        const paths = screen.getByRole('link', { name: 'Paths' });
        expect(paths).toHaveAttribute('href', '/learn');
      });
    });

    it('logged-out also exposes the Topbar Paths link to /learn', async () => {
      renderWithPlan(null);
      await waitFor(() => {
        const paths = screen.getByRole('link', { name: 'Paths' });
        expect(paths).toHaveAttribute('href', '/learn');
      });
    });

    it('ContinuePathsSection header has a persistent All paths → link to /learn', async () => {
      renderWithPlan('free');
      await waitFor(() => screen.getByText('Continue your paths.'));
      const link = screen.getByRole('link', { name: /all paths/i });
      expect(link).toHaveAttribute('href', '/learn');
    });

    it('YourTracksSection defaults to All — shows all 9 tracks', async () => {
      const { container } = renderWithPlan('free');
      await waitFor(() => screen.getByText('Jump back in.'));
      const section = container.querySelector('.lp-your-tracks');
      expect(section.querySelectorAll('.lp-your-track-card')).toHaveLength(9);
      const allBtn = within(section).getByRole('button', { name: 'All' });
      expect(allBtn).toHaveAttribute('aria-pressed', 'true');
    });

    it('selecting Data Engineer filters the grid to its 5 tracks in order', async () => {
      const { container } = renderWithPlan('free');
      await waitFor(() => screen.getByText('Jump back in.'));
      const section = container.querySelector('.lp-your-tracks');
      fireEvent.click(within(section).getByRole('button', { name: 'Data Engineer' }));
      await waitFor(() => {
        const cards = [...section.querySelectorAll('.lp-your-track-card')];
        expect(cards).toHaveLength(5);
        expect(cards.map((c) => c.getAttribute('href'))).toEqual([
          '/practice/python',
          '/practice/sql',
          '/practice/pyspark',
          '/practice/data-engineering',
          '/practice/data-modeling',
        ]);
      });
      expect(within(section).queryByText('Statistics')).not.toBeInTheDocument();
    });
  });

});

// ---------------------------------------------------------------------------
// Weak-spots coaching — concept drill vs path, and the Pro+ gate
// ---------------------------------------------------------------------------

describe('LandingPage — Weak spots coaching (drill)', () => {
  const WEAK_INSIGHTS = {
    weakest_concepts: [
      {
        concept: 'WINDOW & ROLLING OPERATIONS',
        track: 'pandas',
        accuracy_pct: 0.25,
        attempts: 4,
        recommended_path_slug: 'reshaping-and-pivoting',
        recommended_path_title: 'Reshaping & Pivoting',
      },
    ],
    streak_days: 0,
  };

  function wireInsights(insights) {
    api.get.mockImplementation((url) => {
      if (url === '/dashboard') return Promise.resolve({ data: MOCK_DASHBOARD_DATA });
      if (url === '/dashboard/insights') return Promise.resolve({ data: insights });
      if (url === '/paths') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: {} });
    });
  }

  it('paid user: the weak-spot CTA drills the concept and offers no path secondary (drill-only tile)', async () => {
    wireInsights(WEAK_INSIGHTS);
    renderWithPlan('pro');

    const drill = await screen.findByText('Drill this →');
    expect(drill.closest('a').getAttribute('href')).toMatch(/^\/practice\/pandas\?drill=/);

    // Landing keeps the coaching tile minimal — no path option here (the dashboard carries the path secondary).
    expect(screen.queryByText(/Or take the .* path/i)).not.toBeInTheDocument();
  });

  it('free user with weak data: shows an upgrade gate and never leaks a concept name or a drill link', async () => {
    wireInsights(WEAK_INSIGHTS);
    renderWithPlan('free');

    expect(await screen.findByText(/Upgrade to Pro to see your weak concepts/i)).toBeInTheDocument();
    // The concept name and any drill affordance must NOT be exposed to free users.
    expect(screen.queryByText('WINDOW & ROLLING OPERATIONS')).not.toBeInTheDocument();
    expect(screen.queryByText('Drill this →')).not.toBeInTheDocument();
  });

  it('free user with no weak data: the section is hidden entirely (no dangling upsell)', async () => {
    wireInsights({ weakest_concepts: [], streak_days: 0 });
    renderWithPlan('free');

    // Wait for the insights fetch to resolve into render, then assert the coaching heading is absent.
    await waitFor(() => expect(api.get).toHaveBeenCalledWith('/dashboard/insights'));
    await waitFor(() => {
      expect(screen.queryByText('Sharpen your weak spots.')).not.toBeInTheDocument();
    });
  });
});
