import { useState } from 'react';
import OnboardingTooltip from './OnboardingTooltip';

/**
 * Opt-in new-visitor walkthrough for the landing page.
 *
 * Deliberately NOT auto-opening (the prior version ambushed readers after 10s).
 * A quiet trigger link in the hero starts a short, 4-step spotlight tour anchored
 * to the current 8-section editorial layout. Reuses the OnboardingTooltip engine
 * (portal-to-body, viewport-clamped positioning, Esc/Skip/Back/Next, target
 * highlight). Rendered only in the logged-out hero, so it never shows to users
 * who already know the product.
 */
const TOUR_STEPS = [
  {
    title: 'Start with your role',
    body: 'Pick the role you are targeting — Analyst, Engineer, Analytics Engineer, or Scientist — and we highlight the exact tracks that matter for it.',
    targetSelector: '#lp-roles',
  },
  {
    title: 'Try a real question, free',
    body: 'Open any track and solve a question in the live sandbox — no signup. This is where you feel the reasoning depth, not just multiple-choice recall.',
    targetSelector: '#lp-tracks',
  },
  {
    title: 'Follow a guided path',
    body: 'Curated 5–9 question walks through one reasoning pattern at a time — the fastest way to build durable depth instead of grinding volume.',
    targetSelector: '#lp-paths',
  },
  {
    title: 'Free to start',
    body: 'Every easy question is free, no card. Upgrade only when you want the full bank and timed mock interviews.',
    targetSelector: '#landing-pricing',
  },
];

export default function LandingTour() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" className="lp-tour-link" onClick={() => setOpen(true)}>
        <svg
          className="lp-tour-icon"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M8 16 l2 -6 l6 -2 l-2 6 z" />
        </svg>
        Take the 60-second tour
      </button>
      <OnboardingTooltip isOpen={open} steps={TOUR_STEPS} onClose={() => setOpen(false)} />
    </>
  );
}
