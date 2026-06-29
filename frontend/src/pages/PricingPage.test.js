/**
 * PricingPage smoke test.
 *
 * Verifies:
 *   - The three tier names render (Free / Pro / Elite)
 *   - Feature names from the real data file render
 *   - The page heading renders
 *   - Upgrade buttons render for anonymous users
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';

// ── Module mocks ──────────────────────────────────────────────────────────────

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

// UpgradeButton makes API calls and loads external scripts — stub it out
vi.mock('../components/UpgradeButton', () => ({
  default: ({ tier }) => <button>{`Upgrade to ${tier}`}</button>,
}));

// Topbar pulls in useTheme from App
vi.mock('../App', () => ({
  useTheme: () => ({ theme: 'light', setTheme: () => {}, resolvedTheme: 'light' }),
}));

// Topbar also calls useAuth, and may call useTopic
vi.mock('../contexts/TopicContext', () => ({
  TRACK_META: {},
  TopicProvider: ({ children }) => children,
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL' } }),
}));

// ── Import the component AFTER mocks ─────────────────────────────────────────

import PricingPage from './PricingPage';

// ── Render helper ─────────────────────────────────────────────────────────────

function renderPricingPage() {
  return render(
    <MemoryRouter>
      <HelmetProvider>
        <PricingPage />
      </HelmetProvider>
    </MemoryRouter>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PricingPage', () => {
  it('renders all three tier names', () => {
    renderPricingPage();
    expect(screen.getAllByText('Free').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Pro').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Elite').length).toBeGreaterThanOrEqual(1);
  });

  it('renders feature names from the comparison table', () => {
    renderPricingPage();
    // These strings come directly from COMPARISON_GROUPS in tierFeatures.js
    expect(screen.getByText('Interview Loop')).toBeInTheDocument();
    expect(screen.getByText('Personalised study plan')).toBeInTheDocument();
  });

  it('renders the page heading', () => {
    renderPricingPage();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Every feature, spelled out.');
  });

  it('does not render the unlock ladder section', () => {
    renderPricingPage();
    expect(screen.queryByText('How Free unlocks questions')).not.toBeInTheDocument();
    expect(screen.queryByText('Solve 8 easy')).not.toBeInTheDocument();
  });

  it('shows upgrade buttons for an anonymous user', () => {
    renderPricingPage();
    const upgradeButtons = screen.getAllByRole('button', { name: /upgrade to/i });
    expect(upgradeButtons.length).toBeGreaterThanOrEqual(2);
  });
});
