# UI / UX Phase 3 Prompt: Problem-Solving Workspace

```text
Use English.

You are redesigning the core problem-solving surface after the shell hierarchy is in better shape.

Scope:
- question page layout
- sample question page layout
- editor prominence
- prompt/schema structure
- action placement
- panel rhythm and spacing

Primary files to inspect and likely edit:
- frontend/src/pages/QuestionPage.js
- frontend/src/pages/SampleQuestionPage.js
- frontend/src/components/SchemaViewer.js
- frontend/src/App.css

Secondary file to inspect if needed:
- frontend/src/components/SQLEditor.js

Current realities to preserve:
- The product already has a left-panel and right-panel structure.
- The editor, run, submit, results, hints, and solution flow already work.
- Sample mode has its own helper cards and reset flow.
- Locked challenge questions already show a locked callout.

Problems this phase should solve:
- the workspace still feels like stacked cards rather than a refined solving environment
- the editor should become the visual center of gravity once the user is active
- run and submit actions should feel clearer and more intentional
- prompt, schema, and supporting information should read more cleanly
- sample mode should feel consistent with the main workspace rather than like a different product

Design direction:
- preserve the two-column solving model on desktop
- give the editor more authority and breathing room
- make supporting panels calmer and easier to scan
- keep schema visible and useful without overpowering the prompt
- reduce visual fragmentation

Implementation guidance:
- do not change the actual run/submit behavior
- favor stable layout over clever motion
- avoid introducing extra tabs or nested panels unless they reduce cognitive load
- keep the workspace comfortable for long SQL sessions
- align sample and challenge experiences more closely, while keeping their mode-specific callouts clear

Specific goals:
- rebalance left-panel vs right-panel proportions
- refine question title, metadata, and concept-tag hierarchy
- improve editor framing and topbar treatment
- create a clearer action cluster for Run Query and Submit Answer
- make sample challenge helper surfaces calmer and more integrated
- improve spacing between editor, run output, verdict, hints, and solution sections

Acceptance checks:
- the editor feels central without hiding the prompt
- the solve flow feels smoother and less cluttered
- prompt and schema are easier to read
- sample mode feels like a first-class part of the same product
- layout still works on narrower viewports
- tests and build still pass
```
