# UI / UX Workflow Prompt

```text
Use English.

This file is the source of truth for the pending frontend visual refactor.

Purpose:
- preserve the full UI/UX context outside of chat history
- keep the redesign sequenced in a clean order
- record what has already been decided
- prevent future UI work from drifting into backend or architecture changes

North star:
- fast
- calm
- modern
- distraction-free
- easy on the eyes for long sessions
- professional enough for interview preparation
- future-ready for other data-tool and language tracks without changing the product's visual identity

What is already decided:
- The interface should feel like a focused workspace, not a coding contest arena.
- The editor should become the visual center of gravity once solving begins.
- The product should use a restrained premium visual language, closer to Notion calm and Linear polish.
- The experience should avoid bright purple-heavy treatment, loud badges, dense chrome, and celebratory noise.
- Timed challenge mixes are:
  - 30-minute challenge: 1 easy + 2 medium
  - 60-minute challenge: 1 easy + 2 medium + 1 hard

What has already been implemented:
- Landing-page timed challenge preview tiles in frontend/src/pages/LandingPage.js
- Supporting landing styles in frontend/src/App.css
- Phase 2 shell hierarchy refinements in frontend/src/components/AppShell.js
- Phase 2 sidebar hierarchy refinements in frontend/src/components/SidebarNav.js
- Supporting shell and sidebar styling updates in frontend/src/App.css
- Phase 3 challenge workspace refinements in frontend/src/pages/QuestionPage.js
- Phase 3 sample workspace refinements in frontend/src/pages/SampleQuestionPage.js
- Phase 3 schema and editor refinements in frontend/src/components/SchemaViewer.js and frontend/src/components/SQLEditor.js
- Phase 4 results and feedback refinements in frontend/src/components/ResultsTable.js
- Phase 4 verdict and comparison refinements in frontend/src/pages/QuestionPage.js and frontend/src/pages/SampleQuestionPage.js
- Phase 5 auth surface refinements in frontend/src/pages/AuthPage.js
- Phase 5 upgrade grouping refinements in frontend/src/components/AppShell.js

Do not lose these product truths:
- SQL interview practice is the current focus.
- The product should feel ready for future tracks like Python and broader data-tool interview prep.
- The UI must support long thinking sessions with low cognitive load.
- The product must feel polished for professionals, while still being welcoming to beginners.

Do not change:
- backend behavior
- routes unless a small UI-only frontend adjustment is required
- APIs
- database concerns
- infrastructure

Shared files most likely to be touched during the remaining work:
- frontend/src/App.css
- frontend/src/components/AppShell.js
- frontend/src/components/SidebarNav.js
- frontend/src/components/ResultsTable.js
- frontend/src/components/SchemaViewer.js
- frontend/src/pages/QuestionPage.js
- frontend/src/pages/SampleQuestionPage.js
- frontend/src/pages/AuthPage.js
- frontend/src/pages/QuestionListPage.js
- frontend/src/components/SidebarNav.test.js

Remaining execution order:

Phase 2. Practice shell and sidebar hierarchy
- Prompt file: .github/prompts/ui-ux-phase2-practice-shell.prompt.md
- Reason this comes first:
  - it sets the visual frame for the rest of the app
  - it reduces noise before deeper workspace changes
  - it creates the shared hierarchy that later pages inherit

Phase 3. Problem-solving workspace layout
- Prompt file: .github/prompts/ui-ux-phase3-problem-workspace.prompt.md
- Reason this comes second:
  - it is the core product experience
  - it should build on the calmer shell established in Phase 2

Phase 4. Results and feedback states
- Prompt file: .github/prompts/ui-ux-phase4-results-feedback.prompt.md
- Reason this comes third:
  - it refines the solve loop after the layout is stable
  - it should tune feedback inside the new workspace structure

Phase 5. Auth and upgrade surfaces
- Prompt file: .github/prompts/ui-ux-phase5-auth-upgrade.prompt.md
- Reason this comes last:
  - it should inherit the same refined visual language
  - it is important, but not the primary workspace users spend the most time in

Workflow for each phase:
1. Read the phase prompt and inspect the real screen files first.
2. Make only the smallest coherent set of changes needed for that phase.
3. Keep class names and structure stable unless a clearer layout requires safe adjustment.
4. Avoid introducing a new component library or a large redesign framework.
5. Verify after each meaningful phase:
   - cd frontend && npm test
   - cd frontend && npm run build
6. At the end of the phase, update this workflow file with:
   - what was completed
   - what files were touched
   - any remaining follow-up items worth carrying forward

Completion ledger:
- Phase 1 entry surfaces: started and partially implemented
- Phase 2 practice shell: completed
- Phase 3 problem workspace: completed
- Phase 4 results and feedback: completed
- Phase 5 auth and upgrade: completed

Phase notes:
- Phase 2 completed
  - Calm, lower-noise challenge topbar with clearer workspace framing, compact upgrade controls, and quieter plan/session context.
  - Sidebar now has a durable overview block, clearer difficulty-group hierarchy, and subtler current / next / solved / locked row states.
  - Mobile sidebar behavior and routing were preserved.
  - Files touched:
    - frontend/src/App.css
    - frontend/src/components/AppShell.js
    - frontend/src/components/SidebarNav.js
    - frontend/src/components/SidebarNav.test.js
  - Carry-forward notes:
    - Keep the shell palette restrained and avoid reintroducing loud state pills in later phases.
    - Build the problem workspace so the active question row remains visually anchored against the calmer shell.
    - Continue using the subtler accent and softer semantic colors rather than returning to bright purple or saturated success/error fills.
- Phase 3 completed
  - Rebalanced the challenge and sample workspaces so the editor has more authority, with integrated workspace headers and calmer action clusters.
  - Reworked prompt and schema cards for clearer reading rhythm, including structured schema table headers and column tokens.
  - Brought sample mode closer to the main product language with aligned helper cards, sample-track controls, and exhausted-state treatment.
  - Files touched:
    - frontend/src/App.css
    - frontend/src/components/SchemaViewer.js
    - frontend/src/components/SQLEditor.js
    - frontend/src/pages/QuestionPage.js
    - frontend/src/pages/SampleQuestionPage.js
  - Carry-forward notes:
    - Phase 4 should refine the new results stack rather than changing the workspace proportions again.
    - Keep run / submit / hint / solution controls within the calmer editor and post-submit rhythm now established.
    - Results tables, verdict blocks, and solution styling should inherit the same softer surfaces and typography hierarchy.
- Phase 4 completed
  - Reworked verdict blocks to use calmer structured language instead of loud success / error banners.
  - Improved results-table readability with clearer empty and null states plus a side-by-side comparison grid for user vs expected output.
  - Tuned hint and official-solution reveal controls to feel more progressive and review-oriented.
  - Files touched:
    - frontend/src/App.css
    - frontend/src/components/ResultsTable.js
    - frontend/src/pages/QuestionPage.js
    - frontend/src/pages/SampleQuestionPage.js
  - Carry-forward notes:
    - Phase 5 should keep auth alerts, post-success states, and upgrade messaging at the same restrained intensity as the new feedback surfaces.
    - Preserve the calmer accent hierarchy and avoid slipping back into bright marketing-style treatment for upgrade actions.
- Phase 5 completed
  - Aligned the auth page to the calmer product language with quieter background treatment, steadier card rhythm, and more trustworthy helper copy.
  - Refined the shell upgrade grouping so plan context and upgrade actions feel integrated instead of bolted onto the topbar.
  - Tuned auth alerts, inputs, OAuth buttons, and link treatments to match the rest of the refactor without changing auth or checkout behavior.
  - Files touched:
    - frontend/src/App.css
    - frontend/src/components/AppShell.js
    - frontend/src/pages/AuthPage.js
  - Carry-forward notes:
    - Remaining future work should mostly be small coherence passes on the partially-refreshed landing slice rather than new structural refactors.
    - Keep the single restrained accent and the softer semantic colors as the baseline across future UI work.

Quality checks for every phase:
- Does the screen feel calmer than before?
- Is the primary action clearer than before?
- Is the reading rhythm better?
- Is visual noise lower?
- Does the UI still feel fast and lightweight?
- Would this be comfortable for a 60 to 90 minute session?
```
