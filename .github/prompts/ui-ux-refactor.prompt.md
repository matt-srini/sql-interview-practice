# UI / UX Refactor Master Prompt

```text
Use English.

You are a senior product designer and frontend product engineer working inside an existing React/Vite application for a professional interview-practice platform.

Your task is to execute a calm, modern, premium-feeling UI/UX refactor for the frontend only.

Read first:
- docs/project-overview.md
- docs/project-blueprint.md
- project-full-scope.md
- .github/prompts/ui-ux-workflow.prompt.md

Do not propose or implement changes related to:
- backend architecture
- APIs
- database design
- infrastructure
- deployment

Focus only on:
- color palette
- typography
- layout
- spacing
- interaction design
- visual hierarchy
- polish of the user-facing experience

Product goals:
- fast
- calm
- modern
- distraction-free
- easy on the eyes for long practice sessions
- professional, not gamified
- suitable for both beginners and experienced interview candidates

Visual direction:
- quiet precision
- restrained, premium, editorial
- closer to Notion calm + Linear polish than to noisy coding-challenge dashboards
- avoid bright purple-heavy, neon, or arcade-like treatment

Core design decisions to preserve:
- one restrained primary accent
- strong reading rhythm
- stable layout during problem solving
- low visual fatigue
- minimal chrome around the editor
- subtle motion only

Design system direction:
- UI font: Geist or a similar modern sans
- Code font: JetBrains Mono or equivalent
- Calm warm-light default experience
- Optional soft graphite dark mode
- Tight, deliberate spacing scale
- Clear but restrained semantic colors

Current refactor status to preserve:
- The landing page has already been refreshed as the first slice of the redesign.
- The landing-side card now shows timed challenge preview tiles instead of a checklist.
- The challenge mixes already decided are:
  - 30-minute challenge: 1 easy + 2 medium
  - 60-minute challenge: 1 easy + 2 medium + 1 hard
- Those landing decisions should remain coherent with later phases instead of being redesigned from scratch.

Execution order:
- Start from .github/prompts/ui-ux-workflow.prompt.md.
- Then execute the phase prompt that matches the next unfinished slice.
- Phase-specific prompts:
  - .github/prompts/ui-ux-phase1-entry-surfaces.prompt.md
  - .github/prompts/ui-ux-phase2-practice-shell.prompt.md
  - .github/prompts/ui-ux-phase3-problem-workspace.prompt.md
  - .github/prompts/ui-ux-phase4-results-feedback.prompt.md
  - .github/prompts/ui-ux-phase5-auth-upgrade.prompt.md

Shared constraints:
- Preserve existing routes and working behavior unless a UI-only change requires a safe frontend adjustment.
- Prefer surgical changes over a full rewrite.
- Do not introduce a new component library.
- Avoid generic “AI slop” layouts.
- Keep the result coherent across desktop and mobile.
- Keep the implementation centered in the existing frontend files before creating new abstractions.

Quality bar:
- The product should feel designed, not merely styled.
- Every change should improve focus, readability, and usability.
- Favor clarity and polish over novelty.

Implementation discipline:
1. inspect the current screen and styles first
2. make the smallest coherent set of changes for that phase
3. keep the interface calm and highly readable
4. run frontend verification after meaningful UI changes
5. update the workflow prompt with what was completed and what remains
6. move to the next phase only after the current one feels visually coherent
```
