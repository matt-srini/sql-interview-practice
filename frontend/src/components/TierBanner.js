import { useNavigate } from 'react-router-dom';

/**
 * One-line banner shown at the top of TrackHubPage.
 *
 * Props:
 *   plan  'free' | 'pro' | 'elite'
 */
export default function TierBanner({ plan }) {
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

  // Free plan — flat message
  return (
    <div className="tier-banner tier-banner-free">
      <span className="tier-banner-text">
        Free plan · Easy questions only. Upgrade to Pro for medium and hard.
      </span>
      <button
        type="button"
        className="tier-banner-cta"
        onClick={() => navigate('/', { state: { scrollTo: 'landing-pricing' } })}
      >
        See plans →
      </button>
    </div>
  );
}
