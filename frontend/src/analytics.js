/**
 * Analytics wrapper — thin layer over PostHog.
 *
 * When VITE_POSTHOG_KEY is absent (local dev), every call is a no-op.
 * Event names follow a `noun_verb` convention (`question_submitted`, `mock_started`).
 */
import posthog from 'posthog-js';
import { getRuntimeConfig } from './runtimeConfig';

const POSTHOG_KEY = getRuntimeConfig('VITE_POSTHOG_KEY');
const POSTHOG_HOST = getRuntimeConfig('VITE_POSTHOG_HOST') || 'https://us.i.posthog.com';

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

// ── UTM helpers ───────────────────────────────────────────────────────────────

const UTM_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];

/**
 * Parse UTM params from a query string, returning only those that are present.
 * Pure function — safe to unit-test without a DOM.
 *
 * @param {string} search - e.g. window.location.search
 * @returns {Record<string, string>}
 */
export function extractUtmParams(search) {
  try {
    const params = new URLSearchParams(search);
    const result = {};
    for (const key of UTM_KEYS) {
      const value = params.get(key);
      if (value != null && value !== '') {
        result[key] = value;
      }
    }
    return result;
  } catch {
    return {};
  }
}

/**
 * Fire `sample_landed` once per browser session (guarded by sessionStorage).
 *
 * Captures UTM params, referrer, and an optional `?role=` param so we can
 * attribute which channel drove a visitor to the free sample surface.
 *
 * posthog-js already attaches UTM to every event automatically; capturing them
 * explicitly here creates an unambiguous, queryable top-of-funnel arrival event.
 *
 * @param {Record<string, unknown>} [extraProps] - additional properties to merge
 */
export function captureSampleLanded(extraProps = {}) {
  try {
    const SESSION_KEY = 'sample_landed_fired';
    if (typeof sessionStorage !== 'undefined' && sessionStorage.getItem(SESSION_KEY)) {
      return; // already fired this session — internal nav between sample pages
    }
    const utmProps = extractUtmParams(
      typeof window !== 'undefined' ? window.location.search : ''
    );
    const referrer =
      typeof document !== 'undefined' && document.referrer ? document.referrer : undefined;
    const roleParam = (() => {
      try {
        const p = new URLSearchParams(
          typeof window !== 'undefined' ? window.location.search : ''
        ).get('role');
        return p || undefined;
      } catch {
        return undefined;
      }
    })();

    const props = {
      ...utmProps,
      ...(referrer !== undefined ? { referrer } : {}),
      ...(roleParam !== undefined ? { role: roleParam } : {}),
      ...extraProps,
    };

    track('sample_landed', props);

    if (typeof sessionStorage !== 'undefined') {
      try {
        sessionStorage.setItem(SESSION_KEY, '1');
      } catch {
        // sessionStorage unavailable (private-browsing edge case) — no-op
      }
    }
  } catch {
    // Never let analytics throw
  }
}
