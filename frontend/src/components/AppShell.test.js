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
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';

const { mockApiGet, mockUseAuth, mockUseCatalog } = vi.hoisted(() => ({
  mockApiGet: vi.fn(),
  mockUseAuth: vi.fn(),
  mockUseCatalog: vi.fn(),
}));

vi.mock('../api', () => ({ default: { get: (...a) => mockApiGet(...a) } }));
vi.mock('../catalogContext', () => ({ useCatalog: () => mockUseCatalog() }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => mockUseAuth() }));
vi.mock('../contexts/TopicContext', () => ({
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL', color: '#3B7DD8', apiPrefix: '' } }),
}));
vi.mock('./SidebarNav', () => ({ default: () => <div data-testid="sidebar-nav" /> }));
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
