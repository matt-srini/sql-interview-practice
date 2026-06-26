import { useState } from 'react';
import OnboardingTooltip from './OnboardingTooltip';

/**
 * Opt-in new-visitor walkthrough for the landing page.
 *
 * A quiet soft-pill trigger sits on its own row below the hero; clicking it runs a
 * short, 4-step spotlight tour anchored to the current 8-section layout (it never
 * auto-opens). Once the visitor has gone through the tour at least once
 * (`landing_tour_seen`), hovering the pill reveals a small dismiss "×" — click it to
 * remove the shortcut for good (`landing_tour_pref=hide`).
 *
 * Keeping the shortcut is the *default* (do nothing), so there is no terminal
 * "keep" choice to get stuck in: the dismiss path is always one hover away until
 * the visitor deliberately removes it. Rendered only in the logged-out hero.
 */
const SEEN_KEY = 'landing_tour_seen';
const PREF_KEY = 'landing_tour_pref'; // 'hide'

function readKey(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeKey(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // storage disabled — the preference simply isn't remembered
  }
}

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
  const [seen, setSeen] = useState(() => readKey(SEEN_KEY) === '1');
  const [hidden, setHidden] = useState(() => readKey(PREF_KEY) === 'hide');

  if (hidden) return null; // visitor dismissed the shortcut

  const handleClose = () => {
    setOpen(false);
    if (!seen) {
      writeKey(SEEN_KEY, '1');
      setSeen(true);
    }
  };

  const hideShortcut = () => {
    writeKey(PREF_KEY, 'hide');
    setHidden(true);
  };

  return (
    <>
      <span className="lp-tour-wrap">
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

        {seen && (
          <button
            type="button"
            className="lp-tour-dismiss"
            onClick={hideShortcut}
            aria-label="Hide the tour shortcut"
            title="Hide"
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M7 7 L17 17 M17 7 L7 17" />
            </svg>
          </button>
        )}
      </span>

      <OnboardingTooltip isOpen={open} steps={TOUR_STEPS} onClose={handleClose} />
    </>
  );
}
