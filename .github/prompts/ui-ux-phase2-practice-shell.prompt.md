# UI / UX Phase 2 Prompt: Practice Shell and Sidebar Hierarchy

```text
Use English.

You are implementing the next unfinished UI/UX slice after the landing refresh.

Scope:
- practice shell
- top bar
- sidebar grouping
- current state
- solved state
- locked state
- navigation hierarchy

Primary files to inspect and likely edit:
- frontend/src/components/AppShell.js
- frontend/src/components/SidebarNav.js
- frontend/src/components/SidebarNav.test.js
- frontend/src/App.css

Secondary file to inspect if needed:
- frontend/src/pages/QuestionListPage.js

Current realities to preserve:
- The app shell already supports mobile sidebar behavior and upgrade actions.
- Sidebar groups are organized by difficulty.
- The current sidebar includes solved, next, and locked states.
- Existing navigation behavior must keep working.
- SidebarNav tests must keep passing or be safely updated to reflect intentional UI-only structure changes.

Problems this phase should solve:
- top bar feels too utilitarian and visually busy
- sidebar hierarchy is functional but not calm or premium yet
- difficulty groups and question states can scan better
- current, solved, next, and locked states should be clearer without becoming louder
- the shell should feel more like a focused workspace and less like a generic dashboard

Design direction:
- simplify the top bar
- reduce noisy pill clutter
- create clearer spacing and stronger grouping
- make the sidebar easier to scan during long sessions
- keep the current question clearly anchored
- make locked questions feel unavailable but still legible
- keep solved states affirming but subtle

Implementation guidance:
- keep the current routing and sidebar behavior intact
- do not redesign the information architecture
- prefer visual hierarchy, spacing, and calmer state styling over new interaction patterns
- treat the shell as the visual frame for the rest of the product
- preserve mobile usability

Specific goals:
- refine topbar spacing, title treatment, utility grouping, and upgrade-action placement
- improve sidebar header hierarchy and helper copy
- make difficulty section headers feel deliberate rather than plain utility rows
- restyle question rows so the active row, solved row, next row, and locked row are more readable
- reduce the “busy list” feeling without hiding important state

Acceptance checks:
- the shell feels noticeably calmer
- scanning the sidebar takes less effort
- the current question stands out without shouting
- solved and locked states are distinct but restrained
- mobile sidebar behavior still works
- tests and build still pass
```
