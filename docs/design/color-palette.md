# Color Palette

This file is the authoritative color reference for datathink. All new UI work must use these tokens. Do not introduce ad-hoc colors outside this system.

---

## Active theme: Forest & Ink

Chosen for its calm, authoritative feel — deep forest greens ground the interface without feeling flashy. The warm off-white background reads as premium and focused.

> **Active theme launch status: light-only.** datathink ships **light mode only** at launch. Dark mode (the `[data-theme="dark"]` token table below + the charcoal code surfaces) is **deferred to a future version and sits dormant** — the CSS and the `isDark` plumbing remain, but `ThemeProvider` (`App.js`) and the `index.html` pre-paint bootstrap lock the app to `theme='light'` / `isDark=false` (ignoring `localStorage` + OS `prefers-color-scheme`), and the theme toggle is removed from `Topbar`. The dark tokens below are **reference for when dark is re-enabled** (a near-one-line flip), not a currently-reachable theme. See [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-17 defer-dark-to-a-future-version).

### Light mode

| Token | Value | Role |
|---|---|---|
| `--bg-page` | `#F5F7F4` | Page background (very slight green tint) |
| `--surface-canvas` | `#FFFFFF` | Pristine white surface (editor, modal backdrops) |
| `--surface-card` | `#FFFFFF` | Card / panel background |
| `--surface-card-alt` | `#EDF3EF` | Alternate card (sidebar rows, table stripes) |
| `--surface-card-soft` | `#F0F5F1` | Soft inset surface |
| `--surface-highlight` | `#E3EDE6` | Hover highlight, selection |
| `--border-subtle` | `rgba(20, 41, 27, 0.08)` | Default hairline border |
| `--border-strong` | `rgba(20, 41, 27, 0.16)` | Prominent border (focused inputs, dividers) |
| `--text-strong` | `#14291B` | Headings, primary labels |
| `--text-primary` | `#1D3526` | Body text |
| `--text-secondary` | `#4B6858` | Secondary labels, captions |
| `--text-muted` | `#7A9485` | Placeholder, metadata |
| `--text-soft` | `#A8BDB4` | Disabled, faint context |
| `--accent` | `#166534` | Primary action color (buttons, links, active states) |
| `--accent-strong` | `#0F4F26` | Hover/pressed accent |
| `--accent-soft` | `rgba(22, 101, 52, 0.08)` | Accent tint background |
| `--accent-soft-strong` | `rgba(22, 101, 52, 0.18)` | Stronger accent tint |
| `--success` | `#15803D` | Correct answer, solved state |
| `--success-soft` | `rgba(21, 128, 61, 0.10)` | Success background tint |
| `--success-text` | `#14532D` | Success text on tinted bg |
| `--warning` | `#C47F17` | Hint, partial, at-risk streak |
| `--warning-soft` | `rgba(196, 127, 23, 0.10)` | Warning background tint |
| `--warning-text` | `#7A4A0A` | Warning text on tinted bg |
| `--danger` | `#D94F3D` | Wrong answer, error, locked |
| `--danger-soft` | `rgba(217, 79, 61, 0.10)` | Danger background tint |
| `--danger-text` | `#7A1A12` | Danger text on tinted bg |
| `--shadow-sm` | `0 1px 4px rgba(20, 41, 27, 0.08)` | Card shadow |
| `--shadow-md` | `0 4px 16px rgba(20, 41, 27, 0.10)` | Dropdown / popover shadow |
| `--shadow-lg` | `0 8px 40px rgba(20, 41, 27, 0.12)` | Modal shadow |
| `--brand-accent` | `#166534` | Razorpay checkout theme color |

### Dark mode (`[data-theme="dark"]`) — DORMANT (deferred to a future version)

**Charcoal, not forest (2026-06-12).** The dark theme uses near-neutral charcoal
surfaces (WhatsApp / ChatGPT style) so the brand green reads as the one **accent**
that pops, not the environment. The earlier green-tinted "Forest" dark surfaces
(`#0D1A10` page, `#132218` cards) put the brand hue into the background, text, and
accent all at once, so it read as "too green / neon" for a distraction-free study
tool. The fix demotes green from the environment to an accent on a calm charcoal
ground — a crisp emerald **`#2FBE6B`** (HSL 145/60/47, 2026-06-17). The hue arrived in
three steps: (1) a *bright* emerald `#43D27C` (2026-06-13, de-neoned from the original
`#4ADE80`); (2) when even that still *glowed* on charcoal across dense screens (~20 green
hits per page), a **chroma drop** to a muted sage `#5FB98C` (HSL 150/39/55, saturation
61%→39%) — calm, but at 39% it read **pale/washed-out and minty** (hue 150 leans teal)
and the crisp track colors drowned it; (3) a **re-sharpen** to `#2FBE6B` — hue pulled off
the mint edge toward emerald (150→145), saturation back up to ~60%, held slightly darker
(L 47%) so it stays vivid and legible (~7.2:1 on cards) without radiating. A broader pass
that *demoted* links / kickers / numerals / upgrade-washes to neutral was trialed and
**reverted** in the mute era — on a dark ground, color was the click/affordance signal,
so those kept the green and the CTA keeps its deep `#1C8A4F`; only the **SESSION DEBRIEF**
results panel stays neutral (a green wash there competed with the page CTA). *(A
deliberate role-differentiation pass — reserving solid green, giving success an outlined
treatment — is tracked separately under `dark_accent_differentiation`.)* Light mode is
unchanged (still Forest & Ink — deep-green `#166534` on warm paper). See
[`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-12 charcoal,
2026-06-13 accent tone-down, 2026-06-17 `dark_accent_mute` + `dark_accent_resharpen`).

| Token | Value | Role |
|---|---|---|
| `--bg-page` | `#121315` | Charcoal page background (near-neutral) |
| `--surface-canvas` | `#1A1B1E` | Canvas surface |
| `--surface-card` | `#1A1B1E` | Card background |
| `--surface-card-alt` | `#212327` | Alternate card |
| `--surface-card-soft` | `#1B1C1F` | Soft inset |
| `--surface-highlight` | `#282A2E` | Hover highlight |
| `--border-subtle` | `rgba(228, 231, 235, 0.08)` | Hairline border |
| `--border-strong` | `rgba(228, 231, 235, 0.14)` | Prominent border |
| `--text-strong` | `#ECEEF0` | Headings |
| `--text-primary` | `#CDD1D6` | Body text |
| `--text-secondary` | `#9BA1A9` | Secondary labels |
| `--text-muted` | `#6E747D` | Placeholder |
| `--text-soft` | `#474C54` | Disabled / faint |
| `--accent` | `#2FBE6B` | Brand green accent — active states, links, small fills (NOT the primary button). Muted `#43D27C`→`#5FB98C` then re-sharpened `#5FB98C`→`#2FBE6B` on 2026-06-17 |
| `--accent-strong` | `#56D289` | Hover/pressed accent |
| `--accent-soft` | `rgba(47, 190, 107, 0.12)` | Accent tint |
| `--accent-soft-strong` | `rgba(47, 190, 107, 0.22)` | Stronger accent tint |
| `--success` | `#4CAF82` | Correct answer |
| `--success-soft` | `rgba(76, 175, 130, 0.12)` | Success tint |
| `--success-text` | `#8BD2B0` | Success text |
| `--warning` | `#D4973A` | Warning |
| `--warning-soft` | `rgba(212, 151, 58, 0.12)` | Warning tint |
| `--warning-text` | `#E2BD79` | Warning text |
| `--danger` | `#E06B5A` | Error / wrong |
| `--danger-soft` | `rgba(224, 107, 90, 0.12)` | Danger tint |
| `--danger-text` | `#F0B8B1` | Danger text |
| `--brand-accent` | `#2FBE6B` | Brand green accent for dark surfaces (Razorpay checkout theme) |

**Primary button (dark) is NOT `--accent`.** On charcoal, white text on the
green `--accent` (`#2FBE6B`) fails contrast for white text (~2.4:1, harsh). The primary
action button (`.btn-primary` and everything that composes it — `.mock-start-btn`,
both `UpgradeButton` tiers, plus `.auth-submit-btn` / `.acct-save-btn` /
`.path-nav-btn--next` / `.lp-paths-cta-primary`) uses a deep **"action green"
`#1C8A4F` + white** (~4.4:1 on a 600-weight label), hover `#229B5A`. This is the
two-tier green system: *green `#2FBE6B` for accents, deep `#1C8A4F` for the
solid action button.* The **Elite** upgrade button keeps the two-tone
**green→teal gradient** `#1C8A4F → #109488` (hover `#229B5A → #14A498`); **Pro**
is the solid deep green. These are literals on the button rules, not tokens,
because `--accent` stays the muted accent. Small decorative accent chips/badges
that fill with `--accent` flip their *text* to forest-ink `#0D1A10` (~8:1)
rather than white.

### Logo mark

Two diagonal rounded squares — big block anchored bottom-left, small block floating top-right — creating a thought-bubble feel.

**Light:** big block `#166534`, small block `#4B6858`  
**Dark:** big block `#2FBE6B`, small block `#87B09A`

The dark mark green is **`#2FBE6B`** — it tracks the UI `--accent` (re-matched
`#43D27C` 2026-06-13 → `#5FB98C` 2026-06-17 → re-sharpened to `#2FBE6B` same day). **The in-app
mark is rendered as inline SVG** in `frontend/src/components/BrandMark.js` (the two rects, light
fills baked in as `fill` attributes; the dark override is dormant `[data-theme="dark"]` CSS in
App.css). It is **no longer an `<img>` fetching `/branding/mark-*.svg`** — that runtime fetch was
the recurring "logo missing" prod-blocker (any server blip / moved file / SPA-fallback mis-serve
→ broken-image icon); inline SVG makes the mark zero-network and unbreakable. See
[`../decisions/DECISIONS.md`](../decisions/DECISIONS.md) (2026-06-21 inline-brand-mark). The
`/branding/mark-*.svg` files **remain the artwork source** (for favicon/OG regeneration + design
reference) but are not loaded by the app — **changing the mark colour means updating BOTH
`BrandMark.js`/App.css AND those SVGs** so the favicons stay in sync. The favicons / app icons /
Open Graph card are
PNGs **re-rendered from the SVG sources** (`favicon.svg`, `icon-maskable.svg`,
`og-image.svg`) via `frontend/scripts/render-brand-assets.mjs` whenever the mark colour
changes; the ground stays `#0D1A10` (a brand-asset choice, not the in-app charcoal
surface). The small block `#87B09A` (a muted secondary tone) is unchanged. *Exception:*
the unused `branding/lockup-bar-reverse-no-bg.{svg,png}` is **not** updated — it isn't
referenced in-app, and its transparent PNG isn't covered by the (opaque-background)
render script; re-export it manually if it ever goes into use.

### Code editor & sandbox surfaces (theme-aware)

The code-writing/output surfaces are **always dark**, but match the page theme's
*flavor*: **forest-green under light pages** (the praised warm two-tone island on paper),
**neutral charcoal `#16181C` under dark pages** (so code reads as part of the calm
charcoal UI, not a green island). Changed 2026-06-17 — see
[`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) (editor charcoal-dark; it
superseded the editor sub-decision of the 2026-06-12 charcoal entry).

| Surface | Light (base) | Dark (`[data-theme="dark"]`) |
|---|---|---|
| Monaco editor (`CodeEditor.js`) | `forest-dark` theme — `editor.background #0F2218` | `charcoal-dark` theme — `editor.background #16181C` (switched via `useTheme().isDark`) |
| `.editor-wrapper` chrome | `#0F2218` | `#16181C` |
| Code/output panels — `.question-code-snippet`, `.question-evidence-card`, `.scenario-context-pre`, `.solution-card pre`, `.quality-alt-code`, `.test-case-error-content`, `.print-output-content` | `#0F1C13` / `#0B1710` | `#16181C` |

Syntax highlighting (vs-dark base — keyword blue, string orange, etc.) is shared across
both editor themes; only the chrome (bg / gutter / line-highlight / indent) differs. The
landing HeroIDE (`.lp-ide`) is a separate marketing surface and stays forest in both.

Files: `frontend/public/branding/lockup-bar-no-bg.svg` (light) · `lockup-bar-reverse-no-bg.svg` (dark)

The same mark drives every favicon, app icon, and the Open Graph social card — rendered on the deep forest-ink ground `#0D1A10` with the bright-green (dark-theme) mark colours so it reads on any browser chrome. Sources + the render pipeline: see [`docs/frontend.md`](../frontend.md) § Brand icons & social card.

### Track colors (fixed — do not override with theme accent)

These are each track's own brand identity and must remain stable across theme changes:

| Track | Color |
|---|---|
| SQL | `#5B6AF0` (indigo) |
| Python | `#2D9E6B` (emerald) |
| Pandas | `#C47F17` (amber) |
| PySpark | `#D94F3D` (coral) |
| Data Engineering | `#B9762B` (sienna) |
| Data Modeling | `#3F8E8C` (teal) |
| Statistics | `#7A5AF0` (violet) |
| ML Fundamentals | `#E0456A` (rose) |
| Experimentation | `#0EA5E9` (sky) |

---

## Alternative: Teal & Stone

Documented as a considered alternative. **Not applied anywhere in the codebase.** Revisit if the brand direction shifts toward a more tech/data-forward feel.

| Token | Value |
|---|---|
| `--bg-page` | `#FAFAF9` |
| `--surface-card` | `#FFFFFF` |
| `--accent` | `#0D9488` |
| `--text-strong` | `#1C1917` |
| `--text-secondary` | `#78716C` |
| `--border-subtle` | `rgba(28, 25, 23, 0.08)` |
| Editor bg | `#134E4A` |
| Dark accent | `#2DD4BF` |

Character: calm, data-forward, slightly cooler than Forest & Ink. Works well if the product leans more toward analytics tooling branding.

---

## Theme picker

An interactive preview of all 8 evaluated palettes lives at [`frontend/public/theme-preview.html`](../../frontend/public/theme-preview.html). Load it via the Vite dev server at `/theme-preview.html`.
