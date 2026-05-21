# Color Token Review — 2026-05-21

> **Delete this file when the recommendation is acted on (or rejected and recorded elsewhere).** Temporary memo, not canonical doc.

## Brief

Evaluate whether `--bg-page: #F5F7F4` (the pale forest-tinted page background) is doing the right job in the current "Forest & Ink" theme, or whether pulling it closer to pure white (`#FAFBFA` / `#F8FAF8`) or all the way to `#FFFFFF` would feel more professional while preserving the brand. Delivered as a written recommendation with eyes-on the live render, not a token change.

## What I did

1. Read the live design tokens from `App.css` (page = `#F5F7F4`, card surface = `#FFFFFF`, accent = `#166534`, accent-tinted card = `rgba(22, 101, 52, 0.08)`)
2. Started the Vite dev server and inspected the rendered landing page top-of-fold AND the pricing section (the most card-heavy surface on the site)
3. Verified background-color computed values via `getComputedStyle()` rather than relying on screenshot color fidelity

## Findings

### Top of fold (hero)
The pale forest tint is **barely perceptible** — the page reads as warm off-white. The brand signature comes from the green dot in the logo mark and the accent colors used in CTAs, not from the bg-page itself. Hero copy is high-contrast and readable. **No issue here.**

### Pricing section (the card-heavy test)
This is where the bg-page earns or loses its place:

- The Free and Elite columns are pure `#FFFFFF` cards
- The Pro column uses `rgba(22, 101, 52, 0.08)` (accent at 8% opacity — a faint forest tint)
- All three sit on the pale forest `#F5F7F4` page background

The white cards **visibly lift** off the page background. The accent-tinted Pro card distinguishes itself cleanly as the featured tier. The three-card hierarchy works *because* the page is slightly tinted — that's the depth signal.

### Inspected computed colors

```
body:           rgb(245, 247, 244)  // #F5F7F4 — the page tint
body text:      rgb(29, 53, 38)     // dark forest, near-black
landing-tier-col (white): rgb(255, 255, 255)  // #FFFFFF
landing-tier-col (Pro):   rgba(22, 101, 52, 0.08)  // accent 8%
```

## Analysis against the three candidate paths

### Option A — Keep `#F5F7F4` (my recommendation)
- **Pros:** white cards lift cleanly without needing borders/shadows; subtle brand identity in micro-doses; the existing forest signature works as designed; no migration work
- **Cons:** none meaningful in the surfaces I inspected
- **Verdict:** doing its job

### Option B — Pull closer to white (`#FAFBFA` or `#F8FAF8`)
- **Pros:** ~1% increase in "professional / serious tool" feel; slightly less green signature
- **Cons:** white cards lose visible lift (white-on-near-white); brand signature weakens; the depth hierarchy on pricing cards breaks; needs subtle card borders or shadows to compensate, which is *new* visual noise
- **Verdict:** worse on net. The improvement is imperceptible; the cost is real visual-hierarchy debt.

### Option C — Pure `#FFFFFF` page bg
- **Pros:** maximally "professional" SaaS aesthetic (LinkedIn / Stripe docs style)
- **Cons:** white cards become invisible without forced borders/shadows; brand evaporates (the page bg was a major part of "Forest & Ink"); pricing tier hierarchy breaks; introduces visual-noise debt to compensate
- **Verdict:** reject. Would convert datathink from "Forest & Ink" theme to "generic SaaS with green accents."

## Recommendation

**Keep `--bg-page: #F5F7F4`. Do not change.**

The pale forest tint is doing four things at once that I'd otherwise need to engineer separately:
1. Subtle brand signature on every surface
2. Page-vs-card depth differentiation without borders or shadows
3. A neutral canvas that the forest accent (in CTAs, the Pro card tint, the logo) reads cleanly against
4. A warmth that reads "considered tool" rather than "generic SaaS template"

Any move toward pure white loses items 1, 2, and 4 and forces compensation that adds visual noise. The instinct "I want this to feel more professional" is real, but the cure for that instinct lives elsewhere in the design system (typographic refinement, spacing discipline, micro-interactions) — not in flattening the page bg.

## What I'd revisit (separate concern, not Phase 1)

Two adjacent observations that came up while looking, not strictly the color question:

1. **Topbar background = page background.** They share `#F5F7F4`. The topbar has a 1-px subtle border-bottom doing the separation, which works for editorial surfaces (landing, dashboard) but might feel thin in the workspace where the topbar holds more interactive elements. Worth a separate UX pass on workspace-specific topbar treatment if interaction density grows.

2. **Pro card 8% accent tint is the right touch.** Faint enough to coexist with white siblings; saturated enough to read as "featured." Don't change this either.

## Status

- Recommendation: **keep current `--bg-page` token; no change to App.css.**
- This memo can be deleted once the recommendation is acknowledged or contested.
