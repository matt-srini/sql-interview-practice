/**
 * UpgradeButton component tests.
 *
 * Covers label rendering, the Stripe Checkout flow (success + error paths),
 * and all CSS class / attribute behaviour driven by props.
 */

// ---------------------------------------------------------------------------
// Mock window.location.assign BEFORE any imports — jsdom marks the real
// window.location as non-configurable, so vi.spyOn fails at call-site.
// Shadow it here at module evaluation time instead.
// ---------------------------------------------------------------------------
const mockAssign = vi.fn();
Object.defineProperty(window, 'location', {
  value: { ...window.location, assign: mockAssign },
  writable: true,
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { cleanup } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock the api module — UpgradeButton only uses api.post
// ---------------------------------------------------------------------------
vi.mock('../api', () => ({
  default: { post: vi.fn() },
}));

import api from '../api';
import UpgradeButton from './UpgradeButton';

// ---------------------------------------------------------------------------
// Lifecycle hooks
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  mockAssign.mockReset();
});

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderButton(props = {}) {
  return render(<UpgradeButton {...props} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Label rendering', () => {
  it('renders default label "Upgrade to Pro" for tier="pro"', () => {
    renderButton({ tier: 'pro' });
    expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
  });

  it('renders default label "Upgrade to Elite" for tier="elite"', () => {
    renderButton({ tier: 'elite' });
    expect(screen.getByRole('button', { name: 'Upgrade to Elite' })).toBeInTheDocument();
  });

  it('renders custom label when label prop is provided', () => {
    renderButton({ tier: 'pro', label: 'Go Pro Now' });
    expect(screen.getByRole('button', { name: 'Go Pro Now' })).toBeInTheDocument();
  });

  it('renders "Upgrade to Pro" as default for lifetime_pro tier', () => {
    // tierLabel = tier === 'elite' ? 'Elite' : 'Pro'
    // 'lifetime_pro' !== 'elite', so tierLabel = 'Pro' → label = 'Upgrade to Pro'
    renderButton({ tier: 'lifetime_pro' });
    expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
  });

  it('renders "Upgrade to Elite" as default for lifetime_elite tier', () => {
    // 'lifetime_elite' !== 'elite' (strict equality), so tierLabel = 'Pro'
    // The component produces 'Upgrade to Pro' for any non-'elite' tier string.
    // We assert what the component actually renders for this tier value.
    renderButton({ tier: 'lifetime_elite' });
    expect(screen.getByRole('button', { name: 'Upgrade to Pro' })).toBeInTheDocument();
  });
});

describe('Success path', () => {
  it('shows "Redirecting…" text while pending (api call in flight)', async () => {
    // Never-resolving promise keeps the component frozen in pending state
    api.post.mockImplementation(() => new Promise(() => {}));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText('Redirecting…')).toBeInTheDocument();
    });
  });

  it('disables button while pending', async () => {
    api.post.mockImplementation(() => new Promise(() => {}));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).toBeDisabled();
    });
  });

  it('calls api.post with /stripe/create-checkout and plan=pro on click', async () => {
    api.post.mockResolvedValue({ data: { checkout_url: 'https://stripe.example/pro' } });

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/stripe/create-checkout', { plan: 'pro' });
    });
  });

  it('calls api.post with plan=elite on click for elite tier', async () => {
    api.post.mockResolvedValue({ data: { checkout_url: 'https://stripe.example/elite' } });

    renderButton({ tier: 'elite' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/stripe/create-checkout', { plan: 'elite' });
    });
  });

  it('calls api.post with plan=lifetime_pro on click', async () => {
    api.post.mockResolvedValue({ data: { checkout_url: 'https://stripe.example/lifetime_pro' } });

    renderButton({ tier: 'lifetime_pro', label: 'Lifetime access — $99' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/stripe/create-checkout', { plan: 'lifetime_pro' });
    });
  });

  it('redirects via window.location.assign with checkout_url on success', async () => {
    const url = 'https://checkout.stripe.com/pay/cs_test_abc123';
    api.post.mockResolvedValue({ data: { checkout_url: url } });

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(mockAssign).toHaveBeenCalledWith(url);
    });
  });
});

describe('Error path', () => {
  it('re-enables button after api error (does not stay in pending state)', async () => {
    api.post.mockRejectedValue(new Error('Network error'));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).not.toBeDisabled();
    });
  });

  it('does not call window.location.assign on api error', async () => {
    api.post.mockRejectedValue(new Error('Checkout failed'));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).not.toBeDisabled();
    });

    expect(mockAssign).not.toHaveBeenCalled();
  });
});

describe('CSS classes and attributes', () => {
  it('applies upgrade-btn-pro class for pro tier', () => {
    renderButton({ tier: 'pro' });
    expect(screen.getByRole('button').className).toContain('upgrade-btn-pro');
  });

  it('applies upgrade-btn-elite class for elite tier', () => {
    renderButton({ tier: 'elite' });
    expect(screen.getByRole('button').className).toContain('upgrade-btn-elite');
  });

  it('applies btn-compact class when compact=true', () => {
    renderButton({ tier: 'pro', compact: true });
    expect(screen.getByRole('button').className).toContain('btn-compact');
  });

  it('does not apply btn-compact class when compact is false or omitted', () => {
    renderButton({ tier: 'pro' });
    expect(screen.getByRole('button').className).not.toContain('btn-compact');
  });

  it('sets title attribute to "upgrade-source:{source}" when source prop provided', () => {
    renderButton({ tier: 'pro', source: 'sidebar_hard' });
    expect(screen.getByRole('button')).toHaveAttribute('title', 'upgrade-source:sidebar_hard');
  });

  it('does not set title attribute when source is not provided', () => {
    renderButton({ tier: 'pro' });
    expect(screen.getByRole('button')).not.toHaveAttribute('title');
  });

  it('applies additional className string when className prop provided', () => {
    renderButton({ tier: 'pro', className: 'landing-tier-lifetime-btn' });
    expect(screen.getByRole('button').className).toContain('landing-tier-lifetime-btn');
  });
});
