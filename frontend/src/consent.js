/**
 * Cookie-consent state (analytics).
 *
 * Opt-in model: non-essential analytics (PostHog) stay OFF until the visitor
 * explicitly accepts. The essential session cookie (HttpOnly auth) is exempt and
 * always set. The choice is persisted in localStorage so the banner shows once.
 *
 * Values: 'accepted' | 'rejected' | null (undecided).
 */
const CONSENT_KEY = 'cookie_consent_v1';

export function getConsent() {
  try {
    return localStorage.getItem(CONSENT_KEY);
  } catch {
    // localStorage unavailable (private mode / disabled) — treat as undecided.
    return null;
  }
}

export function setConsent(value) {
  try {
    localStorage.setItem(CONSENT_KEY, value);
  } catch {
    // Storage disabled — the choice simply isn't remembered across sessions.
  }
}

/** True only when the visitor has actively accepted analytics. */
export function hasAnalyticsConsent() {
  return getConsent() === 'accepted';
}

/** True once the visitor has made any choice (so the banner can hide). */
export function hasDecidedConsent() {
  return getConsent() !== null;
}
