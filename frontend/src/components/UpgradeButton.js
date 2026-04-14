import { useState } from 'react';
import api from '../api';

/**
 * Shared upgrade CTA button. Initiates Stripe Checkout for a given plan tier.
 *
 * Props:
 *   tier       'pro' | 'elite'
 *   label      button label text (default: 'Upgrade to {Pro/Elite}')
 *   source     analytics tag passed via button title (e.g. 'sidebar_hard')
 *   compact    if true, adds btn-compact class for smaller footprint
 *   className  additional class names
 */
export default function UpgradeButton({ tier = 'pro', label, source, compact = false, className = '' }) {
  const [pending, setPending] = useState(false);

  const tierLabel = tier === 'elite' ? 'Elite' : 'Pro';
  const buttonLabel = label ?? `Upgrade to ${tierLabel}`;

  async function handleClick() {
    setPending(true);
    try {
      const r = await api.post('/stripe/create-checkout', { plan: tier });
      window.location.assign(r.data.checkout_url);
    } catch {
      setPending(false);
    }
  }

  return (
    <button
      className={`btn btn-primary${compact ? ' btn-compact' : ''} upgrade-btn upgrade-btn-${tier} ${className}`.trim()}
      onClick={handleClick}
      disabled={pending}
      title={source ? `upgrade-source:${source}` : undefined}
    >
      {pending ? 'Redirecting…' : buttonLabel}
    </button>
  );
}
