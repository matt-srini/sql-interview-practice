import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { track } from '../analytics';
import { detectCurrency, railForCurrency } from '../utils/currency';

/**
 * Shared upgrade CTA button. Opens the checkout for the given tier on the rail
 * that matches the selected currency: Razorpay for INR (India), Paddle for every
 * other currency (Paddle is Merchant of Record for the rest of the world).
 *
 * Props:
 *   tier       'pro' | 'elite' | 'lifetime_pro' | 'lifetime_elite'
 *   label      button label text (default: 'Upgrade to {tier}')
 *   source     analytics tag passed via button title (e.g. 'sidebar_hard')
 *   compact    if true, adds btn-compact class for smaller footprint
 *   className  additional class names
 *   currency   'INR' | 'USD' — defaults to the stored/detected currency so every
 *              surface picks the right rail without each caller threading it.
 *   autoTrigger  if true and `user` is already set, opens checkout for `tier` on
 *                mount instead of waiting for a click — used to resume an upgrade
 *                a logged-out visitor started before being sent to sign in.
 */

const RAZORPAY_SCRIPT_SRC = 'https://checkout.razorpay.com/v1/checkout.js';
const PADDLE_SCRIPT_SRC = 'https://cdn.paddle.com/paddle/v2/paddle.js';

let _scriptPromise = null;

function loadRazorpayScript() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (window.Razorpay) return Promise.resolve();
  if (_scriptPromise) return _scriptPromise;

  _scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${RAZORPAY_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => {
        if (!window.Razorpay) { _scriptPromise = null; reject(new Error('blocked')); return; }
        resolve();
      });
      existing.addEventListener('error', () => { _scriptPromise = null; reject(new Error('blocked')); });
      return;
    }
    const s = document.createElement('script');
    s.src = RAZORPAY_SCRIPT_SRC;
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

let _paddleScriptPromise = null;

function loadPaddleScript() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (window.Paddle) return Promise.resolve();
  if (_paddleScriptPromise) return _paddleScriptPromise;

  _paddleScriptPromise = new Promise((resolve, reject) => {
    const onload = () => {
      if (!window.Paddle) { _paddleScriptPromise = null; reject(new Error('blocked')); return; }
      resolve();
    };
    const onerror = () => { _paddleScriptPromise = null; reject(new Error('blocked')); };
    const existing = document.querySelector(`script[src="${PADDLE_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', onload);
      existing.addEventListener('error', onerror);
      return;
    }
    const s = document.createElement('script');
    s.src = PADDLE_SCRIPT_SRC;
    s.async = true;
    s.onload = onload;
    s.onerror = onerror;
    document.body.appendChild(s);
  });

  return _paddleScriptPromise;
}

// Paddle.js overlay state is global (one Initialize per page); bridge its events
// back to whichever button instance opened the checkout.
let _activePaddle = null; // { tier, source, successPath, reset }

function paddleEventCallback(ev) {
  if (!ev || !ev.name || !_activePaddle) return;
  if (ev.name === 'checkout.completed') {
    const { tier, source, successPath } = _activePaddle;
    _activePaddle = null;
    track('plan_upgraded', { tier, source, rail: 'paddle' });
    // Paddle's webhook is the authoritative plan-grant; the success page refreshes
    // the user. We navigate ourselves (no client-verifiable signature exists).
    window.location.assign(successPath);
  } else if (ev.name === 'checkout.closed') {
    const { reset } = _activePaddle;
    _activePaddle = null;
    if (reset) reset();
  }
}

function initPaddle(clientToken, environment) {
  // Tie init state to the SDK object (not a module global) so it inits exactly
  // once per loaded Paddle.js in production, while staying isolated across tests
  // that install a fresh window.Paddle each run.
  if (window.Paddle.__dtInitialized) return;
  if (environment === 'sandbox' && window.Paddle.Environment) {
    window.Paddle.Environment.set('sandbox');
  }
  window.Paddle.Initialize({ token: clientToken, eventCallback: paddleEventCallback });
  window.Paddle.__dtInitialized = true;
}

function tierLabel(tier) {
  return {
    pro: 'Pro',
    elite: 'Elite',
    lifetime_pro: 'Lifetime Pro',
    lifetime_elite: 'Lifetime Elite',
  }[tier] || 'Pro';
}

function isBlockedError(e) {
  return (
    e?.message === 'blocked'
    || e?.message === 'Razorpay SDK unavailable after load'
    || e?.message === 'Paddle SDK unavailable after load'
    || /Razorpay.*not a constructor/i.test(e?.message || '')
  );
}

export default function UpgradeButton({ tier = 'pro', label, source, compact = false, className = '', currency, successPath = '/practice?upgraded=true', variant = 'button', autoTrigger = false }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);
  const autoTriggeredRef = useRef(false);

  // Default to the detected currency so the rail is correct on every
  // surface; an explicit currency prop still wins.
  const effectiveCurrency = currency ?? detectCurrency();
  const rail = railForCurrency(effectiveCurrency);

  const buttonLabel = label ?? `Upgrade to ${tierLabel(tier)}`;

  // Preload the right checkout script as soon as the button appears so the click
  // has less to wait on. (No Razorpay customer pre-warm — passing a customer_id
  // to subscription.create is rejected by Razorpay; see routers/razorpay.py.)
  useEffect(() => {
    if (rail === 'paddle') {
      loadPaddleScript().catch(() => {});
    } else {
      loadRazorpayScript().catch(() => {});
    }
  }, [rail]);

  async function startPaddleCheckout() {
    const [checkoutRes] = await Promise.all([
      api.post('/paddle/create-checkout', { plan: tier }),
      loadPaddleScript(),
    ]);
    const { client_token, environment, price_id, customer_email, custom_data } = checkoutRes.data;

    track('plan_upgrade_started', { tier, source, rail: 'paddle' });
    if (!window.Paddle || typeof window.Paddle.Initialize !== 'function') {
      throw new Error('Paddle SDK unavailable after load');
    }
    initPaddle(client_token, environment);

    _activePaddle = { tier, source, successPath, reset: () => setPending(false) };
    window.Paddle.Checkout.open({
      items: [{ priceId: price_id, quantity: 1 }],
      ...(customer_email ? { customer: { email: customer_email } } : {}),
      customData: custom_data,
      settings: { displayMode: 'overlay', theme: 'light' },
    });
    // Overlay is open; pending stays true until checkout.closed/.completed.
  }

  async function startRazorpayCheckout() {
    // Fire the backend order creation and script load in parallel — both are
    // independent and each can take 300–800ms on their own.
    const [orderRes] = await Promise.all([
      api.post('/razorpay/create-order', { plan: tier, currency: effectiveCurrency }),
      loadRazorpayScript(),
    ]);
    const {
      order_id, subscription_id, amount, currency: checkoutCurrency, key_id, name, description,
      prefill_email, prefill_name, is_subscription,
    } = orderRes.data;

    track('plan_upgrade_started', { tier, source, rail: 'razorpay' });
    if (typeof window.Razorpay !== 'function') {
      throw new Error('Razorpay SDK unavailable after load');
    }

    const opts = {
      key: key_id,
      name,
      description,
      currency: checkoutCurrency,
      prefill: { email: prefill_email || '', name: prefill_name || '' },
      theme: { color: '#166534' },
      handler: async (resp) => {
        try {
          await api.post('/razorpay/verify-payment', {
            plan: tier,
            razorpay_payment_id: resp.razorpay_payment_id,
            razorpay_signature: resp.razorpay_signature,
            razorpay_order_id: resp.razorpay_order_id,
            razorpay_subscription_id: resp.razorpay_subscription_id,
          });
          track('plan_upgraded', { tier, source, rail: 'razorpay' });
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
  }

  async function startCheckout() {
    setPending(true);
    setError(null);
    try {
      if (rail === 'paddle') {
        await startPaddleCheckout();
      } else {
        await startRazorpayCheckout();
      }
    } catch (e) {
      setPending(false);
      if (isBlockedError(e)) {
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

  async function handleClick() {
    if (!user) {
      navigate('/auth', { state: { from: location.pathname + location.search, upgradeTier: tier } });
      return;
    }
    await startCheckout();
  }

  // Resume an upgrade the user started before signing in: the caller (e.g. LandingPage,
  // returning from /auth with the tier carried in router state) renders this button with
  // autoTrigger so checkout reopens itself instead of leaving the user to find and click
  // it again. Guarded by a ref (not just `pending`) so React 18 StrictMode's double-invoke
  // of effects in dev can't fire the paid checkout twice.
  useEffect(() => {
    if (!autoTrigger || !user || autoTriggeredRef.current) return;
    autoTriggeredRef.current = true;
    startCheckout();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoTrigger, user]);

  return (
    <>
      <button
        className={
          variant === 'link'
            ? `upgrade-link upgrade-btn-${tier} ${className}`.trim()
            : `btn btn-primary${compact ? ' btn-compact' : ''} upgrade-btn upgrade-btn-${tier} ${className}`.trim()
        }
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
