import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { track } from '../analytics';

/**
 * Shared upgrade CTA button. Opens the Razorpay Checkout modal for the given tier.
 *
 * Props:
 *   tier       'pro' | 'elite' | 'lifetime_pro' | 'lifetime_elite'
 *   label      button label text (default: 'Upgrade to {tier}')
 *   source     analytics tag passed via button title (e.g. 'sidebar_hard')
 *   compact    if true, adds btn-compact class for smaller footprint
 *   className  additional class names
 */

const CHECKOUT_SCRIPT_SRC = 'https://checkout.razorpay.com/v1/checkout.js';

let _scriptPromise = null;

function loadRazorpayScript() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (window.Razorpay) return Promise.resolve();
  if (_scriptPromise) return _scriptPromise;

  _scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${CHECKOUT_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => {
        if (!window.Razorpay) { _scriptPromise = null; reject(new Error('blocked')); return; }
        resolve();
      });
      existing.addEventListener('error', () => { _scriptPromise = null; reject(new Error('blocked')); });
      return;
    }
    const s = document.createElement('script');
    s.src = CHECKOUT_SCRIPT_SRC;
    s.async = true;
    s.onload = () => {
      if (!window.Razorpay) { _scriptPromise = null; reject(new Error('blocked')); return; }
      resolve();
    };
    s.onerror = () => {
      _scriptPromise = null;
      reject(new Error('blocked'));
    };
    document.body.appendChild(s);
  });

  return _scriptPromise;
}

function tierLabel(tier) {
  return {
    pro: 'Pro',
    elite: 'Elite',
    lifetime_pro: 'Lifetime Pro',
    lifetime_elite: 'Lifetime Elite',
  }[tier] || 'Pro';
}

export default function UpgradeButton({ tier = 'pro', label, source, compact = false, className = '', currency = 'INR', successPath = '/practice?upgraded=true' }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const buttonLabel = label ?? `Upgrade to ${tierLabel(tier)}`;

  // Preload the Razorpay checkout script as soon as the button appears so it's
  // already cached when the user clicks. Silently swallow errors here — the
  // real error handling is in handleClick.
  useEffect(() => {
    loadRazorpayScript().catch(() => {});
  }, []);

  async function handleClick() {
    if (!user) {
      navigate('/auth', { state: { from: '/', upgradeTier: tier } });
      return;
    }
    setPending(true);
    setError(null);
    try {
      // Fire the backend order creation and script load in parallel — both are
      // independent and each can take 300–800ms on their own.
      const [orderRes] = await Promise.all([
        api.post('/razorpay/create-order', { plan: tier, currency }),
        loadRazorpayScript(),
      ]);
      const {
        order_id, subscription_id, amount, currency: checkoutCurrency, key_id, name, description,
        prefill_email, prefill_name, is_subscription,
      } = orderRes.data;

      track('plan_upgrade_started', { tier, source });
      if (typeof window.Razorpay !== 'function') {
        throw new Error('Razorpay SDK unavailable after load');
      }

      const opts = {
        key: key_id,
        name,
        description,
        currency: checkoutCurrency,
        prefill: { email: prefill_email || '', name: prefill_name || '' },
        theme: { color: '#5B6AF0' },
        handler: async (resp) => {
          try {
            await api.post('/razorpay/verify-payment', {
              plan: tier,
              razorpay_payment_id: resp.razorpay_payment_id,
              razorpay_signature: resp.razorpay_signature,
              razorpay_order_id: resp.razorpay_order_id,
              razorpay_subscription_id: resp.razorpay_subscription_id,
            });
            track('plan_upgraded', { tier, source });
            window.location.assign(successPath);
          } catch (e) {
            setPending(false);
            setError('Payment received but verification failed. It will be applied shortly.');
          }
        },
        modal: {
          ondismiss: () => setPending(false),
        },
      };

      if (is_subscription) {
        opts.subscription_id = subscription_id;
      } else {
        opts.order_id = order_id;
        opts.amount = amount;
      }

      const rzp = new window.Razorpay(opts);
      rzp.on('payment.failed', () => {
        setPending(false);
        setError('Payment failed. Please try again.');
      });
      rzp.open();
    } catch (e) {
      setPending(false);
      if (
        e?.message === 'blocked'
        || e?.message === 'Razorpay SDK not available'
        || e?.message === 'Razorpay SDK unavailable after load'
        || /Razorpay.*not a constructor/i.test(e?.message || '')
      ) {
        setError('Checkout was blocked — please disable any ad blocker for this site and try again.');
      } else {
        const message =
          e?.response?.data?.error
          || e?.response?.data?.detail
          || e?.message
          || 'Could not start checkout. Please try again.';
        setError(message);
      }
    }
  }

  return (
    <>
      <button
        className={`btn btn-primary${compact ? ' btn-compact' : ''} upgrade-btn upgrade-btn-${tier} ${className}`.trim()}
        onClick={handleClick}
        disabled={pending}
        title={source ? `upgrade-source:${source}` : undefined}
      >
        {pending ? 'Opening…' : buttonLabel}
      </button>
      {error ? <span className="upgrade-btn-error" role="alert">{error}</span> : null}
    </>
  );
}
