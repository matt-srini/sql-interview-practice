import { useState } from 'react';
import { Link } from 'react-router-dom';
import { getConsent, setConsent } from '../consent';
import { initAnalytics, trackPageView } from '../analytics';

/**
 * Bottom cookie-consent banner (opt-in).
 *
 * Analytics (PostHog) is NOT initialized until the visitor clicks Accept — so no
 * non-essential cookies are set before consent. The essential session cookie is
 * unaffected. Shown once, until a choice is stored in localStorage.
 */
export default function CookieConsent() {
  const [decided, setDecided] = useState(() => getConsent() !== null);
  if (decided) return null;

  const accept = () => {
    setConsent('accepted');
    initAnalytics();   // first-time opt-in — spin PostHog up now
    trackPageView();   // record the current page (init sets capture_pageview:false)
    setDecided(true);
  };

  const reject = () => {
    setConsent('rejected');
    setDecided(true);
  };

  return (
    <div className="cookie-consent" role="region" aria-label="Cookie consent">
      <p className="cookie-consent-text">
        We use privacy-friendly product analytics to understand how datathink is used and
        improve it. Your sign-in session works either way. See our{' '}
        <Link to="/privacy">Privacy Policy</Link>.
      </p>
      <div className="cookie-consent-actions">
        <button type="button" className="btn btn-secondary btn-compact" onClick={reject}>
          Reject
        </button>
        <button type="button" className="btn btn-primary btn-compact" onClick={accept}>
          Accept
        </button>
      </div>
    </div>
  );
}
