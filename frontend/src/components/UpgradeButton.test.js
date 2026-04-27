/**
 * UpgradeButton component tests — Razorpay flow.
 *
 * Covers label rendering, the Razorpay Checkout flow (success + error paths),
 * and all CSS class / attribute behaviour driven by props.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { cleanup } from '@testing-library/react';

const { mockApiPost, mockTrack, mockAssign } = vi.hoisted(() => ({
  mockApiPost: vi.fn(),
  mockTrack: vi.fn(),
  mockAssign: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Mock window.location.assign BEFORE any imports — jsdom marks the real
// window.location as non-configurable, so vi.spyOn fails at call-site.
// Shadow it here at module evaluation time instead.
// ---------------------------------------------------------------------------
Object.defineProperty(window, 'location', {
  value: { ...window.location, assign: mockAssign },
  writable: true,
});

vi.mock('../api', () => ({
  default: {
    post: (...args) => mockApiPost(...args),
  },
}));

vi.mock('../analytics', () => ({
  track: (...args) => mockTrack(...args),
}));

import UpgradeButton from './UpgradeButton';

// ---------------------------------------------------------------------------
// Razorpay SDK mock — the real SDK is loaded via <script>; in jsdom we stub
// window.Razorpay so loadRazorpayScript() short-circuits.
// ---------------------------------------------------------------------------
let lastRazorpayOpts = null;
let lastRazorpayInstance = null;

function installRazorpayMock() {
  lastRazorpayOpts = null;
  lastRazorpayInstance = null;
  window.Razorpay = vi.fn().mockImplementation((opts) => {
    lastRazorpayOpts = opts;
    const inst = {
      open: vi.fn(),
      on: vi.fn(),
      _trigger: (event, payload) => {
        const handlers = inst.on.mock.calls.filter(([e]) => e === event);
        handlers.forEach(([, cb]) => cb(payload));
      },
    };
    lastRazorpayInstance = inst;
    return inst;
  });
}

beforeEach(() => {
  mockApiPost.mockReset();
  mockTrack.mockReset();
  mockAssign.mockReset();
  installRazorpayMock();
});

afterEach(() => {
  cleanup();
  delete window.Razorpay;
});

function renderButton(props = {}) {
  return render(<UpgradeButton {...props} />);
}

// ---------------------------------------------------------------------------
// Label rendering
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

  it('renders "Upgrade to Lifetime Pro" for lifetime_pro tier', () => {
    renderButton({ tier: 'lifetime_pro' });
    expect(screen.getByRole('button', { name: 'Upgrade to Lifetime Pro' })).toBeInTheDocument();
  });

  it('renders "Upgrade to Lifetime Elite" for lifetime_elite tier', () => {
    renderButton({ tier: 'lifetime_elite' });
    expect(screen.getByRole('button', { name: 'Upgrade to Lifetime Elite' })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Success path — create-order + Razorpay modal + verify-payment
// ---------------------------------------------------------------------------

describe('Success path (subscription)', () => {
  const subscriptionOrderResponse = {
    data: {
      subscription_id: 'sub_test_123',
      order_id: null,
      amount: 0,
      currency: 'INR',
      key_id: 'rzp_test_key',
      name: 'datathink',
      description: 'datathink Pro (monthly)',
      prefill_email: 'u@example.com',
      prefill_name: 'u',
      is_subscription: true,
    },
  };

  it('calls /razorpay/create-order with plan=pro on click', async () => {
    mockApiPost.mockResolvedValueOnce(subscriptionOrderResponse);

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith('/razorpay/create-order', { plan: 'pro', currency: 'INR' });
    });
  });

  it('opens Razorpay modal with subscription_id for subscription plans', async () => {
    mockApiPost.mockResolvedValueOnce(subscriptionOrderResponse);

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(window.Razorpay).toHaveBeenCalled();
      expect(lastRazorpayOpts.subscription_id).toBe('sub_test_123');
      expect(lastRazorpayOpts.order_id).toBeUndefined();
      expect(lastRazorpayInstance.open).toHaveBeenCalled();
    });
  });

  it('verifies payment and redirects on successful handler callback', async () => {
    mockApiPost
      .mockResolvedValueOnce(subscriptionOrderResponse)      // create-order
      .mockResolvedValueOnce({ data: { plan: 'pro' } });     // verify-payment

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => expect(lastRazorpayOpts).not.toBeNull());

    // Simulate Razorpay's success callback
    await lastRazorpayOpts.handler({
      razorpay_payment_id: 'pay_test_abc',
      razorpay_signature: 'sig_test',
      razorpay_subscription_id: 'sub_test_123',
    });

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenNthCalledWith(2, '/razorpay/verify-payment', {
        plan: 'pro',
        razorpay_payment_id: 'pay_test_abc',
        razorpay_signature: 'sig_test',
        razorpay_order_id: undefined,
        razorpay_subscription_id: 'sub_test_123',
      });
      expect(mockAssign).toHaveBeenCalledWith('/practice?upgraded=true');
    });
  });
});

describe('Success path (one-time lifetime)', () => {
  const lifetimeOrderResponse = {
    data: {
      order_id: 'order_test_lt',
      subscription_id: null,
      amount: 799900,
      currency: 'INR',
      key_id: 'rzp_test_key',
      name: 'datathink',
      description: 'datathink Lifetime Pro',
      prefill_email: 'u@example.com',
      prefill_name: 'u',
      is_subscription: false,
    },
  };

  it('opens Razorpay modal with order_id + amount for lifetime plans', async () => {
    mockApiPost.mockResolvedValueOnce(lifetimeOrderResponse);

    renderButton({ tier: 'lifetime_pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(lastRazorpayOpts.order_id).toBe('order_test_lt');
      expect(lastRazorpayOpts.amount).toBe(799900);
      expect(lastRazorpayOpts.subscription_id).toBeUndefined();
    });
  });
});

// ---------------------------------------------------------------------------
// Error path
// ---------------------------------------------------------------------------

describe('Error path', () => {
  it('re-enables button after create-order error', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('Network error'));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).not.toBeDisabled();
    });
  });

  it('does not redirect on create-order error', async () => {
    mockApiPost.mockRejectedValueOnce(new Error('Network error'));

    renderButton({ tier: 'pro' });
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByRole('button')).not.toBeDisabled();
    });
    expect(mockAssign).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// CSS classes and attributes
// ---------------------------------------------------------------------------

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
