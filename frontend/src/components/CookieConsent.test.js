import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CookieConsent from './CookieConsent';

// Analytics must never be touched until Accept — mock it to assert that.
vi.mock('../analytics', () => ({
  initAnalytics: vi.fn(),
  trackPageView: vi.fn(),
}));
import { initAnalytics, trackPageView } from '../analytics';

const renderBanner = () =>
  render(
    <MemoryRouter>
      <CookieConsent />
    </MemoryRouter>
  );

describe('CookieConsent', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('shows the banner when no choice has been made', () => {
    renderBanner();
    expect(screen.getByRole('region', { name: /cookie consent/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^accept$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^reject$/i })).toBeInTheDocument();
    // Opt-in: nothing starts before a choice.
    expect(initAnalytics).not.toHaveBeenCalled();
  });

  it('Accept stores consent, starts analytics, and hides the banner', () => {
    renderBanner();
    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }));
    expect(localStorage.getItem('cookie_consent_v1')).toBe('accepted');
    expect(initAnalytics).toHaveBeenCalledTimes(1);
    expect(trackPageView).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('region', { name: /cookie consent/i })).not.toBeInTheDocument();
  });

  it('Reject stores the choice, does NOT start analytics, and hides the banner', () => {
    renderBanner();
    fireEvent.click(screen.getByRole('button', { name: /^reject$/i }));
    expect(localStorage.getItem('cookie_consent_v1')).toBe('rejected');
    expect(initAnalytics).not.toHaveBeenCalled();
    expect(screen.queryByRole('region', { name: /cookie consent/i })).not.toBeInTheDocument();
  });

  it('does not render once a choice is already stored', () => {
    localStorage.setItem('cookie_consent_v1', 'accepted');
    renderBanner();
    expect(screen.queryByRole('region', { name: /cookie consent/i })).not.toBeInTheDocument();
  });
});
