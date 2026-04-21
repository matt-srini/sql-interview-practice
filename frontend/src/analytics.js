/**
 * Analytics wrapper — thin layer over PostHog.
 *
 * When VITE_POSTHOG_KEY is absent (local dev), every call is a no-op.
 * Event names follow a `noun_verb` convention (`question_submitted`, `mock_started`).
 */
import posthog from 'posthog-js';

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

let _initialized = false;

export function initAnalytics() {
  if (_initialized || !POSTHOG_KEY) return;
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    autocapture: true,
    capture_pageview: false,   // manual via trackPageView for SPA
    capture_pageleave: true,
    persistence: 'localStorage+cookie',
    loaded: (ph) => {
      if (import.meta.env.DEV) ph.debug();
    },
  });
  _initialized = true;
}

/** Call on SPA route change. */
export function trackPageView() {
  if (!_initialized) return;
  posthog.capture('$pageview');
}

/** Identify a logged-in user (called after login/register/session restore). */
export function identifyUser(user) {
  if (!_initialized || !user) return;
  posthog.identify(String(user.id), {
    email: user.email || undefined,
    name: user.name || undefined,
    plan: user.plan || 'free',
    is_anonymous: user.is_anonymous ?? true,
  });
}

/** Reset identity on logout. */
export function resetIdentity() {
  if (!_initialized) return;
  posthog.reset();
}

/** Generic event capture. */
export function track(event, properties) {
  if (!_initialized) return;
  posthog.capture(event, properties);
}
