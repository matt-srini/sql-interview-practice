/**
 * tierFeatures.js — SINGLE SOURCE for the user-facing tier comparison (/pricing page).
 *
 * Plain-language, customer-appropriate copy — NO internal jargon (no `unlock_profile`,
 * `focus_concepts`, file paths). The point of /pricing is honesty: we say exactly what
 * each tier gives you, no hiding behind short adjectives.
 *
 * Entitlement source of truth (keep this in sync when those change):
 *   · docs/features/pricing.md   (tier matrix)
 *   · docs/features/mock.md      (mock plan-tier matrix)
 *   · backend/unlock.py          (free-tier unlock thresholds)
 *   · docs/tier-wise-features.html  (internal mirror of this same data)
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
        blurb: 'On Free, medium opens in batches as you solve easy (see the unlock ladder below). Pro & Elite: open from the start.',
        free: 'Unlocks as you solve', pro: 'All', elite: 'All',
      },
      {
        feature: 'Hard questions',
        blurb: 'On Free, hard opens as you solve medium, up to a per-track cap. Pro & Elite: no cap.',
        free: 'Up to the free cap', pro: 'All', elite: 'All',
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
 * Free-tier difficulty unlocking, in plain language. Thresholds mirror backend/unlock.py:
 * code tracks (medium 8/15/25, hard 8/15, cap 8) and conceptual tracks
 * (medium 10/17/25, hard 12→5, cap 5).
 */
export const FREE_UNLOCK = {
  intro:
    'Free starts with every easy question. Medium opens in batches as you solve easy; hard opens as you solve medium, up to a per-track cap. It runs separately for each track — and finishing a learning path also opens all of that track’s medium. Pro and Elite skip all of this: every difficulty is open from the start.',
  groups: [
    {
      label: 'Code tracks',
      tracks: 'SQL · Python · Pandas · Statistics',
      medium: [
        ['Solve 8 easy', '3 medium open'],
        ['Solve 15 easy', '8 medium open'],
        ['Solve 25 easy', 'all medium open'],
      ],
      hard: [
        ['Solve 8 medium', '3 hard open'],
        ['Solve 15 medium', '8 hard open'],
      ],
      cap: 'Free hard is capped at 8 per track — lifting the cap is a Pro upgrade, not more grinding.',
    },
    {
      label: 'Conceptual tracks',
      tracks: 'PySpark · Data Engineering · Data Modeling · ML Fundamentals · Experimentation',
      medium: [
        ['Solve 10 easy', '3 medium open'],
        ['Solve 17 easy', '8 medium open'],
        ['Solve 25 easy', 'all medium open'],
      ],
      hard: [
        ['Solve 12 medium', '5 hard open'],
      ],
      cap: 'Free hard is capped at 5 per track — lifting the cap is a Pro upgrade.',
    },
  ],
};

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
