/**
 * tierFeatures.js — CANONICAL SINGLE DISPLAY SOURCE for the user-facing tier comparison.
 *
 * Every frontend surface that shows tier features renders from THIS file — `/pricing`
 * (PricingPage.js), and (as they get wired in) the landing pricing cards, the §06
 * editorial, and TierBanner. Don't re-type tier copy/values in a component; add it here.
 *
 * Plain-language, customer-appropriate copy — NO internal jargon (no `unlock_profile`,
 * `focus_concepts`, file paths). The point of /pricing is honesty: we say exactly what
 * each tier gives you, no hiding behind short adjectives.
 *
 * The *enforcement* SoTs this copy must agree with (this file is a render of them —
 * keep in sync in the same commit; see CLAUDE.md § "Linked-docs / single-SoT rule"):
 *   · backend/unlock.py          (free-tier access policy — canonical)
 *   · docs/features/mock.md      (mock plan-tier matrix — canonical SoT)
 *   · docs/features/pricing.md   (entitlement matrix) · docs/features/dashboard.md (coaching gates)
 * Internal mirror of this same data: docs/tier-wise-features.html (manual — keep in step).
 *
 * Cell value convention: `true` = included, `false` = not included,
 * a string = the specific limit/detail to show in that tier's column.
 */

export const COMPARISON_TIERS = [
  {
    id: 'free',
    name: 'Free',
    blurb: 'Build the fundamentals. Every easy question, free forever — no account required.',
  },
  {
    id: 'pro',
    name: 'Pro',
    blurb: 'The full question bank, daily timed mock practice, and your weak-spot coaching.',
    featured: true,
  },
  {
    id: 'elite',
    name: 'Elite',
    blurb: 'Everything in Pro, plus your readiness score, a plan to close the gaps, and the deepest interview simulation.',
  },
];

export const COMPARISON_GROUPS = [
  {
    group: 'Practice',
    rows: [
      {
        feature: 'Easy questions',
        blurb: 'Every easy question across all nine tracks.',
        free: 'All', pro: 'All', elite: 'All',
      },
      {
        feature: 'Medium questions',
        blurb: 'Free covers easy questions only. Pro and Elite include all difficulties.',
        free: false, pro: 'All', elite: 'All',
      },
      {
        feature: 'Hard questions',
        blurb: 'Free covers easy questions only. Pro and Elite include all difficulties.',
        free: false, pro: 'All', elite: 'All',
      },
      {
        feature: 'Learning paths',
        blurb: 'Curated, ordered walks through one pattern at a time.',
        free: 'Free paths', pro: 'All', elite: 'All',
        notes: { feature: 'paths' },
      },
    ],
  },
  {
    group: 'Mock interviews',
    rows: [
      {
        feature: 'Benchmark — easy',
        blurb: 'A fixed-shape, timed readiness check on a track.',
        free: '1 / week', pro: '3 / day', elite: 'Unlimited',
        notes: { pro: 'caps' },
      },
      {
        feature: 'Benchmark — medium & hard',
        blurb: 'The serious readiness signal, at full difficulty.',
        free: false, pro: '3 / day', elite: 'Unlimited',
        notes: { pro: 'caps' },
      },
      {
        feature: 'Custom drill',
        blurb: 'A timed mock you tune yourself — choose the length and depth.',
        free: false, pro: '3 / day', elite: 'Unlimited',
        notes: { pro: 'caps' },
      },
      {
        feature: 'Mock-only question bank',
        blurb: 'Over 1,000 interview-shaped questions across the tracks — medium and hard only — that you meet only under the clock, never in practice. Separate from the ~100-per-track practice catalog.',
        free: false, pro: true, elite: true,
      },
    ],
  },
  {
    group: 'Interview depth',
    rows: [
      {
        feature: 'Interview Loop',
        blurb: 'One anchor problem, then the interviewer’s escalating follow-ups — the closest thing to a real onsite round.',
        free: false, pro: false, elite: true,
      },
      {
        feature: 'Focus a mock on a weak concept',
        blurb: 'Aim a timed mock squarely at the concepts you keep missing.',
        free: false, pro: false, elite: true,
      },
      {
        feature: 'Coaching debrief',
        blurb: 'A written post-mortem after a mock: what held up, what broke, and what to do next.',
        free: false, pro: false, elite: true,
      },
      {
        feature: 'Trend & breakdown analytics',
        blurb: 'How you’re trending over time, and which kinds of interview pivots break you. Pro gets detailed session history; Elite adds the trend line and the per-dimension breakdown.',
        free: false, pro: 'Session history', elite: 'History + trend + breakdown',
      },
    ],
  },
  {
    group: 'Coaching & readiness',
    rows: [
      {
        feature: 'Weak-spot diagnosis',
        blurb: 'Your weakest concepts, ranked, each with accuracy and a one-tap drill. The full list — not just one.',
        free: false, pro: true, elite: true,
      },
      {
        feature: 'Interview-readiness score',
        blurb: 'A per-track 0–100 read on how ready you are, blending coverage, accuracy, and timed mock performance.',
        free: false, pro: false, elite: true,
      },
      {
        feature: 'Personalised study plan',
        blurb: 'An ordered 3–5 step plan to close your gaps — the what-to-do-next, not just the what’s-wrong.',
        free: false, pro: false, elite: true,
      },
    ],
  },
];

/**
 * Footnotes referenced from the comparison (by `notes: { feature | free | pro | elite: <id> }`
 * on a row). Markers render as superscripts; the text shows in a footnotes block below the table.
 */
export const FOOTNOTES = [
  {
    id: 'paths',
    symbol: '†',
    text: 'Practice and learning paths are the same questions, arranged differently — practice is the full catalog in any order; a path is a short, ordered walk through one pattern. Solve one in either place and it’s marked done in both. Paths don’t add or unlock extra questions; they’re a guided route through what’s already there.',
  },
  {
    id: 'caps',
    symbol: '‡',
    text: 'Three sessions a day suits most people — enough to benchmark one track and drill another, every day. If you’re prepping intensively (several tracks, daily mocks) or want Interview Loop, weigh Elite’s unlimited sessions to see if it fits you better.',
  },
];
