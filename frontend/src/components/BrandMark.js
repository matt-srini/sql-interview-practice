import React from 'react';

/**
 * BrandMark — the datathink monogram, rendered as inline SVG.
 *
 * WHY INLINE (and not <img src="/branding/mark-no-bg.svg">):
 * The logo has gone "missing" repeatedly because it was a *runtime-fetched*
 * public asset — a separate HTTP request that fails on ANY transient server
 * blip (dev-server HMR restart, prod cold start, CDN hiccup, an SPA-fallback
 * mis-serve, or a renamed/moved file with no build error). A broken-image icon
 * is the result. Inlining the markup removes the network request entirely, so
 * the mark can never fail to load — in dev or prod — regardless of server state
 * or where the source file lives. This is the durable fix for that whole class
 * of bug. See docs/decisions/DECISIONS.md (2026-06-21 inline-brand-mark).
 *
 * Source artwork (kept for favicons / external/design reference, NOT loaded by
 * the app): frontend/public/branding/mark-no-bg.svg (+ -reverse for dark). If
 * the mark art changes, update BOTH this component and those files.
 *
 * Theme: light fills are baked in as attributes so the mark renders correctly
 * even if the stylesheet fails to load; the dormant dark-theme override lives in
 * App.css ([data-theme="dark"] .brand-mark-primary/secondary), consistent with
 * the deferred-dark pattern (CLAUDE.md § Design system).
 */
export default function BrandMark({ className = '' }) {
  return (
    <svg
      className={`brand-mark-img ${className}`.trim()}
      viewBox="0 2 40 48"
      role="presentation"
      aria-hidden="true"
      focusable="false"
    >
      <rect className="brand-mark-primary" x="2" y="22" width="26" height="26" rx="6" fill="#166534" />
      <rect className="brand-mark-secondary" x="22" y="4" width="15" height="15" rx="4" fill="#4B6858" />
    </svg>
  );
}
