# UI Design System

The frontend uses a single global stylesheet (`frontend/src/App.css`) with CSS custom properties as design tokens. No CSS framework. No CSS modules.

---

## Design Philosophy

Professional tool aesthetic — calm, fast, distraction-free. Designed for long sessions (30–90 min). Light mode primary, warm dark mode via `prefers-color-scheme`. The SQL editor pane always uses a dark background (`#1e1e1e`) regardless of color scheme — intentional two-tone split between light UI chrome and dark code editor.

---

## Color Tokens

Defined in `:root` in `App.css`. Dark mode overrides in `@media (prefers-color-scheme: dark)`.

### Light mode
| Token | Value | Use |
|---|---|---|
| `--bg-page` | `#F7F7F5` | Page background |
| `--surface-card` | `#FFFFFF` | Cards, panels |
| `--surface-card-alt` | `#F0EFED` | Sidebar, secondary surfaces |
| `--surface-highlight` | `#ECEAE7` | Hover states |
| `--border-subtle` | `rgba(26,26,24,0.08)` | Default borders |
| `--border-strong` | `rgba(26,26,24,0.16)` | Focused borders |
| `--text-strong` | `#1A1A18` | Headings |
| `--text-primary` | `#2D2D2B` | Body text |
| `--text-secondary` | `#6B6862` | Labels, metadata |
| `--text-muted` | `#A8A49F` | Placeholders, disabled |
| `--accent` | `#5B6AF0` | Interactive elements, links |
| `--accent-strong` | `#4A59DF` | Hover accent |
| `--accent-soft` | `rgba(91,106,240,0.08)` | Accent tint backgrounds |
| `--success` | `#2D9E6B` | Correct answer |
| `--warning` | `#C47F17` | Hints, locked |
| `--danger` | `#D94F3D` | Errors, wrong answer |

### Dark mode (warm, not cold)
| Token | Value |
|---|---|
| `--bg-page` | `#141413` |
| `--surface-card` | `#1C1C1A` |
| `--surface-card-alt` | `#242422` |
| `--accent` | `#7B8AF5` |
| `--text-strong` | `#F0EEE9` |
| `--text-primary` | `#D8D5CE` |

---

## Typography

```
--font-sans: "Inter", "Avenir Next", "Segoe UI", sans-serif
--font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace
```

Both loaded from Google Fonts in `frontend/index.html`. Inter for all UI; JetBrains Mono for the editor, results table cells, and code blocks.

---

## Buttons

Three tiers. Defined in `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-success`.

- **Primary**: `--accent` fill, white text — used for Submit
- **Secondary**: outlined — used for Run, navigation actions. *Context-sensitive*: inside the dark editor wrapper uses `rgba(255,255,255,0.07)` bg; outside in light UI uses `rgba(0,0,0,0.03)` bg
- **Success**: success-soft tint — used for Next Question

All hover states use `translateY(-1px)`. No transforms on disabled. Transitions: `150ms ease-out`.

---

## Layout

### Landing page
- Centered flex column; hero section `max-width: 560px`, sample tiles `max-width: 800px`
- Hero: kicker pill → headline → copy → two CTAs (centered)
- Sample tiles: 3-column grid (`repeat(3, minmax(0,1fr))`), flex column cards with `align-items: flex-start`
- Mobile (<900px): hero left-aligned, tiles stack to 1 column

### App shell (challenge workspace)
- **Sidebar**: 328px, sticky, collapsible (`display:none` on `.sidebar-collapsed`)
- **Top bar**: 64px on desktop, sticky, blurred backdrop
- **Question page**: CSS Grid `minmax(330px,400px) / minmax(0,1fr)` — left panel sticky at `top: 88px`
- **Left panel cards**: tight padding, `14px` radius, prompt card slightly stronger than schema card
- **Right panel**: tighter vertical rhythm than the previous 1rem stack
- **Mobile breakpoint**: 900px — sidebar becomes fixed overlay
- **Mobile header**: stripped to menu button + current track switcher
- **Container**: max-width 1180px centered

### Question page chrome
- No section kickers — content is self-evident from titles and badges
- Prompt header includes a compact uppercase status line (difficulty / question position / open count)
- Editor topbar: single line, "SQL editor" left + "DuckDB sandbox" right, slightly tightened padding
- Editor footer: buttons only (Run Query, Submit Answer, Next Question), right-aligned on desktop and presented as a low-profile sticky dock on mobile
- Post-submit: `.submit-outcome` wrapper with overflow hidden groups verdict + feedback cards; hint-card has no box-shadow
- Sidebar intentionally begins with the question bank; no separate progress/summary card above it

---

## Editor Pane

Always dark. Uses `#1e1e1e` background to match Monaco `vs-dark`. Editor config in `frontend/src/components/SQLEditor.js`:
- Theme: `vs-dark`
- Font: JetBrains Mono, 14px
- No minimap, word wrap on, tab size 2

---

## Radii and Shadows

```
--radius-lg: 20px   (editor wrapper)
--radius-md: 14px   (inner cards, schema blocks)
--radius-sm: 10px   (badges, tokens)

--shadow-sm: 0 1px 4px rgba(26,26,24,0.08)
--shadow-md: 0 4px 16px rgba(26,26,24,0.10)
--shadow-lg: 0 8px 40px rgba(26,26,24,0.12)
```
