import { useNavigate } from 'react-router-dom';
import UpgradeButton from './UpgradeButton';

/**
 * One-line banner shown at the top of TrackHubPage.
 *
 * Props:
 *   plan      'free' | 'pro' | 'elite'
 *   returnTo  { path, label? } — where "See plans →" returns the user to from
 *             /pricing. `path` must be an internal route; `label` renders as
 *             "← Back to {label}" (omit for a plain "← Back").
 */
export default function TierBanner({ plan, returnTo }) {
  const navigate = useNavigate();
  const normalisedPlan = plan?.startsWith('lifetime_') ? plan.replace('lifetime_', '') : plan;
  if (normalisedPlan === 'elite' || normalisedPlan === 'pro') {
    const label = normalisedPlan === 'elite' ? 'Elite' : 'Pro';
    return (
      <div className="tier-banner tier-banner-paid">
        <span className="tier-banner-text">{label} plan · Full practice access across all tracks.</span>
      </div>
    );
  }

  // Free plan — Pro is the contextual unlock for medium + hard practice, so the
  // primary action is a direct "Upgrade to Pro" (checkout opens in place).
  // "See plans →" carries the full Pro-vs-Elite comparison at /pricing.
  return (
    <div className="tier-banner tier-banner-free">
      <span className="tier-banner-text">
        Free plan · Easy questions only. Unlock medium &amp; hard:
      </span>
      <div className="tier-banner-actions">
        <UpgradeButton
          tier="pro"
          variant="link"
          source="tier_banner"
          successPath={returnTo?.path ? `${returnTo.path}?upgraded=true` : undefined}
        />
        <button
          type="button"
          className="tier-banner-cta"
          onClick={() => navigate('/pricing', { state: { returnTo } })}
        >
          See plans →
        </button>
      </div>
    </div>
  );
}
