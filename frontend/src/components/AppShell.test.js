/**
 * AppShell concept-drill hub redirect (2026-06-18).
 *
 * Regression guard for the bug where a Pro/Elite user who followed a concept-drill
 * link to the hub (/practice/{track}?drill={concept}) was stranded on the TrackHub
 * page — never redirected to the first drill question — whenever the concept family
 * name contained a hyphen (e.g. "MULTI-TABLE ENTITY LINKING"). Root cause: AppShell
 * re-derived the entry question with a frontend substring match that normalized
 * hyphens on the requested concept but not on the catalog's question concepts, so a
 * hyphenated family never matched. Fix: navigate to the BACKEND drill result's
 * questions[0] (family-aware + unsolved-first), independent of the catalog.
 *
 * These tests render with an EMPTY catalog on purpose: the redirect must work off the
 * backend drill result alone (the old catalog re-match would have found nothing here).
 */
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation, useOutletContext } from 'react-router-dom';

const { mockApiGet, mockUseAuth, mockUseCatalog, sidebarProps } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockUseAuth: vi.fn(),
  mockUseCatalog: vi.fn(),
  sidebarProps: { current: null },
}));

vi.mock('../api', () => ({ default: { get: (...a) => mockApiGet(...a) } }));
vi.mock('../catalogContext', () => ({ useCatalog: () => mockUseCatalog() }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => mockUseAuth() }));
vi.mock('../contexts/TopicContext', () => ({
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL', color: '#3B7DD8', apiPrefix: '' } }),
}));
vi.mock('./SidebarNav', () => ({
  default: (props) => {
    sidebarProps.current = props;
    return <div data-testid="sidebar-nav" />;
  },
}));
vi.mock('./Topbar', () => ({ default: ({ belowTopbar }) => <div data-testid="topbar">{belowTopbar}</div> }));
vi.mock('./UpgradeButton', () => ({ default: () => <button type="button">upgrade</button> }));
vi.mock('../pages/TrackHubPage', () => ({ default: () => <div data-testid="track-hub">TRACK HUB</div> }));

import AppShell from './AppShell';

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="loc">{loc.pathname + loc.search}</div>;
}

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <LocationProbe />
      <Routes>
        <Route path="/practice/:topic" element={<AppShell />}>
          <Route path="questions/:id" element={<div>QUESTION ROUTE</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

const DRILL_RESULT = {
  concept: 'Multi-table entity linking',
  track_label: 'SQL',
  total: 1,
  solved_count: 0,
  questions: [
    { id: 99001, title: 'Orphan order audit', difficulty: 'hard', order: 1, concepts: ['MULTI-TABLE ENTITY LINKING'], state: 'unlocked' },
  ],
};

beforeAll(() => {
  window.matchMedia = window.matchMedia || ((query) => ({
    matches: false, media: query, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {},
    addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  }));
});

beforeEach(() => {
  mockApiGet.mockReset();
  mockApiGet.mockImplementation((url) => {
    if (url === '/practice/drill') return Promise.resolve({ data: DRILL_RESULT });
    return Promise.resolve({ data: {} });
  });
  // Empty catalog on purpose — proves the redirect uses the backend drill result,
  // not a frontend catalog re-match.
  mockUseCatalog.mockReturnValue({ catalog: { groups: [] }, loading: false, error: null, refresh: vi.fn() });
});

afterEach(cleanup);

describe('AppShell concept-drill hub redirect', () => {
  it('Pro: redirects a hyphenated-concept drill link to the first backend drill question (was stranded on the hub)', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'pro', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    renderAt('/practice/sql?drill=' + encodeURIComponent('MULTI-TABLE ENTITY LINKING'));

    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toContain('/practice/sql/questions/99001');
    });
    expect(screen.getByTestId('loc').textContent).toContain('drill=');
    expect(mockApiGet).toHaveBeenCalledWith('/practice/drill', { params: { track: 'sql', concept: 'MULTI-TABLE ENTITY LINKING' } });
  });

  it('Elite: same hyphenated-concept drill link redirects identically (plan parity)', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'elite', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    renderAt('/practice/sql?drill=' + encodeURIComponent('MULTI-TABLE ENTITY LINKING'));

    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toContain('/practice/sql/questions/99001');
    });
  });

  it('Free: drill link is inert — no Pro-only fetch, ?drill= stripped, not pushed into a question', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'free', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    renderAt('/practice/sql?drill=' + encodeURIComponent('MULTI-TABLE ENTITY LINKING'));

    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).not.toContain('drill=');
    });
    expect(mockApiGet).not.toHaveBeenCalledWith('/practice/drill', expect.anything());
    expect(screen.getByTestId('loc').textContent).not.toContain('/questions/');
  });
});

/**
 * AppShell ?resume= redirect (2026-06-26).
 *
 * The logged-in landing "Resume" card links to /practice/<topic>?resume=1 (not a
 * hard-coded question id), so AppShell must redirect to the user's NEXT-UP
 * question — never re-open one they already solved. Reuses pickContinueQuestionId,
 * the same next-up resolver the hub's Continue button uses.
 */
describe('AppShell ?resume= redirect', () => {
  const RESUME_CATALOG = {
    groups: [
      { difficulty: 'easy', questions: [
        { id: 5001, state: 'solved' },
        { id: 5002, state: 'unlocked', is_next: true },
      ] },
    ],
  };

  it('redirects ?resume=1 to the next-up question (not a solved one) and strips the param', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'free', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({ catalog: RESUME_CATALOG, loading: false, error: null, refresh: vi.fn() });
    renderAt('/practice/sql?resume=1');

    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe('/practice/sql/questions/5002');
    });
    expect(screen.getByTestId('loc').textContent).not.toContain('resume=');
  });

  it('does not redirect without ?resume= — the bare hub stays on the hub', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'free', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({ catalog: RESUME_CATALOG, loading: false, error: null, refresh: vi.fn() });
    renderAt('/practice/sql');

    await waitFor(() => {
      expect(screen.getByTestId('track-hub')).toBeInTheDocument();
    });
    expect(screen.getByTestId('loc').textContent).toBe('/practice/sql');
  });

  it('stays on the hub when there is no next-up (track fully solved), stripping ?resume=', async () => {
    const SOLVED_CATALOG = {
      groups: [
        { difficulty: 'easy', questions: [
          { id: 6001, state: 'solved' },
          { id: 6002, state: 'solved' },
        ] },
      ],
    };
    mockUseAuth.mockReturnValue({ user: { plan: 'elite', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({ catalog: SOLVED_CATALOG, loading: false, error: null, refresh: vi.fn() });
    renderAt('/practice/sql?resume=1');

    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe('/practice/sql');
    });
    expect(screen.getByTestId('loc').textContent).not.toContain('/questions/');
    expect(screen.getByTestId('track-hub')).toBeInTheDocument();
  });
});

describe('AppShell reveals the active question difficulty group', () => {
  it('expands the active question group (medium) so the active row is shown', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'pro', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({
      catalog: { groups: [
        { difficulty: 'easy', questions: [{ id: 1, state: 'solved' }] },
        { difficulty: 'medium', questions: [{ id: 7001, state: 'unlocked' }] },
        { difficulty: 'hard', questions: [{ id: 9001, state: 'locked' }] },
      ] },
      loading: false, error: null, refresh: vi.fn(),
    });
    renderAt('/practice/sql/questions/7001');
    await waitFor(() => {
      expect(sidebarProps.current?.collapsedByDiff?.medium).toBe(false);
    });
    // other groups keep their default (only the active group is force-expanded)
    expect(sidebarProps.current?.collapsedByDiff?.hard).toBe(true);
  });
});

/**
 * AppShell path data refresh via Outlet context (2026-06-28).
 *
 * Regression guard for the bug where the PathSidebar tick (✓) did not appear after a
 * solve until the user left and re-entered the path. Root cause: pathData was fetched
 * once per pathSlug change only. Fix: AppShell exposes `refreshPathData` via
 * `<Outlet context>` so QuestionPage can call it on a correct solve.
 *
 * This test renders a probe child that reads the outlet context and calls
 * refreshPathData() on button click, then asserts the path GET was re-issued.
 */
function OutletContextProbe() {
  const ctx = useOutletContext();
  return (
    <button
      data-testid="refresh-btn"
      onClick={() => ctx?.refreshPathData?.()}
    >
      refresh
    </button>
  );
}

describe('AppShell path data refresh', () => {
  const PATH_PAYLOAD = {
    title: 'Joins & Filtering Mastery',
    topic: 'sql',
    questions: [{ id: 1, title: 'Q1', order: 1, state: 'unlocked' }],
    unlock_hint: null,
  };

  it('exposes refreshPathData via Outlet context; clicking it re-fetches the path', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'pro', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({ catalog: { groups: [] }, loading: false, error: null, refresh: vi.fn() });
    mockApiGet.mockImplementation((url) => {
      if (url === '/paths/joins-and-filtering') return Promise.resolve({ data: PATH_PAYLOAD });
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/practice/sql/questions/1?path=joins-and-filtering']}>
        <Routes>
          <Route path="/practice/:topic" element={<AppShell />}>
            <Route path="questions/:id" element={<OutletContextProbe />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    // Wait for initial fetch
    await waitFor(() => {
      const calls = mockApiGet.mock.calls.filter(c => c[0] === '/paths/joins-and-filtering');
      expect(calls.length).toBeGreaterThanOrEqual(1);
    });

    const callsBefore = mockApiGet.mock.calls.filter(c => c[0] === '/paths/joins-and-filtering').length;

    // Trigger the refresher via the probe button
    fireEvent.click(screen.getByTestId('refresh-btn'));

    await waitFor(() => {
      const callsAfter = mockApiGet.mock.calls.filter(c => c[0] === '/paths/joins-and-filtering').length;
      expect(callsAfter).toBe(callsBefore + 1);
    });
  });
});

/**
 * PathSidebar free-tier upgrade hint (2026-07-13).
 *
 * Regression guard: the hint's "Pro/Elite — all difficulties" buttons must route
 * to /pricing carrying returnTo = the current location. This caught a real bug —
 * PathSidebar had no `location` in scope, so the onClick threw "location is not
 * defined" and the button silently did nothing.
 */
describe('AppShell PathSidebar upgrade hint (free plan)', () => {
  const LOCKED_PATH = {
    title: 'Window Functions Mastery',
    topic: 'sql',
    questions: [
      { id: 1, title: 'Q1', order: 1, state: 'unlocked' },
      { id: 2, title: 'Q2', order: 2, state: 'locked' },
    ],
    unlock_hint: null,
  };

  function PricingProbe() {
    const loc = useLocation();
    return <div data-testid="pricing-probe">{JSON.stringify(loc.state)}</div>;
  }

  it('free user: the Pro hint button routes to /pricing with the current path as returnTo', async () => {
    mockUseAuth.mockReturnValue({ user: { plan: 'free', streak_days: 0 }, loading: false, refreshUser: vi.fn() });
    mockUseCatalog.mockReturnValue({ catalog: { groups: [] }, loading: false, error: null, refresh: vi.fn() });
    mockApiGet.mockImplementation((url) => {
      if (url === '/paths/window-functions-mastery') return Promise.resolve({ data: LOCKED_PATH });
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/practice/sql/questions/1?path=window-functions-mastery']}>
        <Routes>
          <Route path="/practice/:topic" element={<AppShell />}>
            <Route path="questions/:id" element={<div>question</div>} />
          </Route>
          <Route path="/pricing" element={<PricingProbe />} />
        </Routes>
      </MemoryRouter>
    );

    const proBtn = await screen.findByRole('button', { name: /Pro.*all difficulties/i });
    fireEvent.click(proBtn);

    const probe = await screen.findByTestId('pricing-probe');
    expect(probe).toHaveTextContent('/practice/sql/questions/1');
    expect(probe).toHaveTextContent('window-functions-mastery');
  });
});
