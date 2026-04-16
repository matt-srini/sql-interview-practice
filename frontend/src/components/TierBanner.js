import { Link } from 'react-router-dom';

/**
 * One-line banner shown at the top of TrackHubPage for Free users,
 * summarising what they can access and what the next unlock condition is.
 *
 * Props:
 *   plan          'free' | 'pro' | 'elite'
 *   easySolved    number of easy questions solved in this track
 *   mediumSolved  number of medium questions solved in this track
 *   easyTotal     total easy questions in this track
 *   mediumTotal   total medium questions in this track
 *   mediumUnlocked  bool — has at least 1 medium unlocked?
 *   hardUnlocked    bool — has at least 1 hard unlocked?
 */
export default function TierBanner({
  plan,
  easySolved = 0,
  mediumSolved = 0,
  easyTotal = 0,
  mediumTotal = 0,
  mediumUnlocked = false,
  hardUnlocked = false,
}) {
  if (plan === 'elite' || plan === 'pro') {
    const label = plan === 'elite' ? 'Elite' : 'Pro';
    return (
      <div className="tier-banner tier-banner-paid">
        <span className="tier-banner-text">{label} plan · Full practice access across all tracks.</span>
      </div>
    );
  }

  // Free plan — celebrate tier completions before asking for the next step
  const easyComplete = easyTotal > 0 && easySolved >= easyTotal;
  const mediumComplete = mediumTotal > 0 && mediumSolved >= mediumTotal;

  let celebrate = null;
  let message;

  if (mediumComplete && !hardUnlocked) {
    // All medium done but hard still locked — prime upgrade moment
    celebrate = `🏆 You've mastered all ${mediumTotal} medium questions!`;
    message = 'Upgrade to Pro to unlock the full hard track.';
  } else if (easyComplete && !hardUnlocked) {
    // All easy done, medium open — encourage continuing
    celebrate = `🎉 You've mastered all ${easyTotal} easy questions!`;
    message = mediumUnlocked
      ? 'Medium is fully open — keep the momentum going.'
      : 'Solve 8 easy to unlock medium, or complete a learning path.';
  } else if (!mediumUnlocked) {
    const needed = Math.max(0, 8 - easySolved);
    message = needed > 0
      ? `Free plan · All easy unlocked. Solve ${needed} more easy to unlock medium, or complete a learning path.`
      : 'Free plan · All easy unlocked. Complete a learning path or solve 8 easy to unlock medium.';
  } else if (!hardUnlocked) {
    const needed = Math.max(0, 8 - mediumSolved);
    message = needed > 0
      ? `Medium unlocked · Solve ${needed} more medium to unlock hard, or complete the intermediate path.`
      : 'Medium unlocked · Complete the intermediate path or solve 8 medium to unlock hard.';
  } else {
    message = 'Hard unlocked · Upgrade to Pro for instant access to all questions.';
  }

  return (
    <div className={`tier-banner${celebrate ? ' tier-banner-celebrate' : ' tier-banner-free'}`}>
      <span className="tier-banner-text">
        {celebrate && <strong className="tier-banner-celebrate-lead">{celebrate} </strong>}
        {message}
      </span>
      <Link to="/auth?upgrade=1" className="tier-banner-cta">See plans →</Link>
    </div>
  );
}
