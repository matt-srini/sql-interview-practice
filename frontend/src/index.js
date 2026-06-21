import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import App from './App';
import { initAnalytics } from './analytics';
import { getRuntimeConfig } from './runtimeConfig';
import { hasAnalyticsConsent } from './consent';
import './App.css';

// ── Sentry (frontend error capture) ─────────────────────────
const SENTRY_DSN = getRuntimeConfig('VITE_SENTRY_DSN');
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({ maskAllText: true, blockAllMedia: false }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,
  });
}

// ── PostHog (product analytics) — gated on cookie consent ───
// First-time visitors opt in via the CookieConsent banner (its Accept handler
// calls initAnalytics). Here we only re-init for a returning visitor who already
// accepted, so analytics never runs before consent.
if (hasAnalyticsConsent()) initAnalytics();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
