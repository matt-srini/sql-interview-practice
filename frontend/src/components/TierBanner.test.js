/**
 * TierBanner tests.
 *
 * Verifies:
 *   - Free plan: primary "Upgrade to Pro" + secondary "See plans →" that routes
 *     to /pricing carrying returnTo (so /pricing can render a contextual back link).
 *   - Paid plans (incl. lifetime_): a flat "full access" message, no upgrade CTAs.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';

// UpgradeButton loads external checkout scripts — stub it to a plain button.
vi.mock('./UpgradeButton', () => ({
  default: ({ tier }) => <button>{`Upgrade to ${tier}`}</button>,
}));

import TierBanner from './TierBanner';

function LocationProbe() {
  const location = useLocation();
  return (
    <div data-testid="probe">
      {location.pathname}|{JSON.stringify(location.state)}
    </div>
  );
}

function renderBanner(props) {
  return render(
    <MemoryRouter initialEntries={['/practice/sql']}>
      <Routes>
        <Route path="/practice/sql" element={<TierBanner {...props} />} />
        <Route path="/pricing" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('TierBanner', () => {
  const returnTo = { path: '/practice/sql', label: 'SQL Practice' };

  it('free plan shows an Upgrade to Pro CTA and a See plans link', () => {
    renderBanner({ plan: 'free', returnTo });
    expect(screen.getByText(/Unlock medium/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /see plans/i })).toBeInTheDocument();
  });

  it('See plans routes to /pricing carrying the returnTo context', () => {
    renderBanner({ plan: 'free', returnTo });
    fireEvent.click(screen.getByRole('button', { name: /see plans/i }));
    const probe = screen.getByTestId('probe');
    expect(probe).toHaveTextContent('/pricing');
    expect(probe).toHaveTextContent('"path":"/practice/sql"');
    expect(probe).toHaveTextContent('"label":"SQL Practice"');
  });

  it('paid plan shows the full-access message and no upgrade CTAs', () => {
    renderBanner({ plan: 'pro', returnTo });
    expect(screen.getByText(/Full practice access/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /see plans/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /upgrade to/i })).not.toBeInTheDocument();
  });

  it('normalises a lifetime_ plan to the paid banner', () => {
    renderBanner({ plan: 'lifetime_elite', returnTo });
    expect(screen.getByText(/Elite plan · Full practice access/i)).toBeInTheDocument();
  });
});
