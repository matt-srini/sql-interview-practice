/**
 * AccountPage tests.
 *
 * Covers:
 *   - Paddle subscriber: manage-via-Paddle note shown, no Razorpay action buttons,
 *     invoice amounts formatted in USD with Intl.NumberFormat
 *   - Razorpay subscriber: Switch plan + Cancel subscription buttons present,
 *     Razorpay payment note shown, no Paddle note shown
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';

// ── Module mocks ──────────────────────────────────────────────────────────────

// Mock the api module so we can control GET /account/billing
vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'usr_abc12345', email: 'test@example.com', name: 'Test User', plan: 'pro' },
    refreshUser: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock('../App', () => ({
  useTheme: () => ({ theme: 'light', setTheme: () => {}, resolvedTheme: 'light' }),
}));

vi.mock('../contexts/TopicContext', () => ({
  TRACK_META: {},
  TopicProvider: ({ children }) => children,
  useTopic: () => ({ topic: 'sql', meta: { label: 'SQL' } }),
}));

// react-helmet-async is real but HelmetProvider is in the wrapper — no mock needed

// ── Import AFTER mocks ────────────────────────────────────────────────────────

import api from '../api';
import AccountPage from './AccountPage';

// ── Render helper ─────────────────────────────────────────────────────────────

function renderAccountPage() {
  return render(
    <MemoryRouter>
      <HelmetProvider>
        <AccountPage />
      </HelmetProvider>
    </MemoryRouter>
  );
}

// ── Shared billing fixtures ───────────────────────────────────────────────────

const PADDLE_BILLING = {
  provider: 'paddle',
  managed_externally: true,
  plan: 'pro',
  is_subscription: true,
  is_lifetime: false,
  plan_currency: 'USD',
  subscription_status: 'active',
  billing_cycle_end: 1720000000,
  cancelled_at_cycle_end: false,
  invoices: [
    {
      id: 'txn_1',
      amount: 3000,
      currency: 'USD',
      status: 'paid',
      date: 1718600000,
      pdf_url: null,
      plan: 'pro',
    },
  ],
};

const RAZORPAY_BILLING = {
  provider: 'razorpay',
  managed_externally: false,
  plan: 'pro',
  is_subscription: true,
  is_lifetime: false,
  plan_currency: 'INR',
  subscription_status: 'active',
  billing_cycle_end: 1720000000,
  cancelled_at_cycle_end: false,
  invoices: [
    {
      id: 'pay_rzp_1',
      amount: 99900,
      currency: 'INR',
      status: 'paid',
      date: 1718600000,
      pdf_url: 'https://razorpay.com/receipt/123',
      plan: 'pro',
    },
  ],
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AccountPage — Paddle subscriber', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.get.mockResolvedValue({ data: PADDLE_BILLING });
  });

  it('(a) shows the manage-via-Paddle note with support@datathink.co', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByText(/Billed through Paddle/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('link', { name: /support@datathink\.co/i })).toBeInTheDocument();
  });

  it('(b) does NOT render Switch plan or Cancel subscription buttons', async () => {
    renderAccountPage();
    // Wait for billing to load (the Paddle note appears)
    await waitFor(() => {
      expect(screen.getByText(/Billed through Paddle/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /switch plan/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel subscription/i })).not.toBeInTheDocument();
  });

  it('(c) renders the invoice amount as USD "$30.00" (not ₹)', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByText(/Billed through Paddle/i)).toBeInTheDocument();
    });
    // Intl.NumberFormat renders $30.00 for 3000 minor units of USD
    expect(screen.getByText('$30.00')).toBeInTheDocument();
    // Must NOT contain the rupee symbol
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
  });

  it('(d) shows an "Emailed by Paddle" receipt hint instead of a bare dash', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByText(/Billed through Paddle/i)).toBeInTheDocument();
    });
    // Paddle (Merchant of Record) has no downloadable invoice URL — the receipt
    // cell shows a hint rather than the misleading "—".
    expect(screen.getByText(/Emailed by Paddle/i)).toBeInTheDocument();
  });
});

describe('AccountPage — Razorpay subscriber', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.get.mockResolvedValue({ data: RAZORPAY_BILLING });
  });

  it('shows Switch plan and Cancel subscription buttons', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /switch plan/i })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /cancel subscription/i })).toBeInTheDocument();
  });

  it('shows the Razorpay payment failure note', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByText(/Razorpay will email you/i)).toBeInTheDocument();
    });
  });

  it('does NOT show the Paddle management note', async () => {
    renderAccountPage();
    await waitFor(() => {
      // Wait for billing to load by checking something that only appears post-load
      expect(screen.getByText(/Razorpay will email you/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/Billed through Paddle/i)).not.toBeInTheDocument();
  });

  it('renders the invoice amount in INR', async () => {
    renderAccountPage();
    await waitFor(() => {
      expect(screen.getByText(/Razorpay will email you/i)).toBeInTheDocument();
    });
    // 99900 minor units of INR = ₹999.00
    // Intl.NumberFormat for INR typically renders as ₹999.00
    const amountCell = screen.getByText(/₹/);
    expect(amountCell).toBeInTheDocument();
  });
});
