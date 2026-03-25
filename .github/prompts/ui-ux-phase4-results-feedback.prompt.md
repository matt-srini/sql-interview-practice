# UI / UX Phase 4 Prompt: Results and Feedback States

```text
Use English.

You are refining the solve-loop feedback after the workspace layout is stable.

Scope:
- run results
- submission verdicts
- feedback messages
- expected vs actual results
- hints
- solution reveal

Primary files to inspect and likely edit:
- frontend/src/components/ResultsTable.js
- frontend/src/pages/QuestionPage.js
- frontend/src/pages/SampleQuestionPage.js
- frontend/src/App.css

Secondary file to inspect if needed:
- frontend/src/components/SchemaViewer.js

Current realities to preserve:
- run results already render in a reusable ResultsTable component
- submit results already show verdict, feedback, output comparison, hints, and official solution
- the current flow is functional and should remain so

Problems this phase should solve:
- verdicts are still louder and more mechanical than the desired product tone
- results tables and comparison blocks can feel heavy and repetitive
- hint and solution reveals should feel progressive and calm
- feedback should help users recover without making failure feel dramatic

Design direction:
- keep semantic feedback clear but restrained
- avoid loud green and red blocks
- treat results as structured information, not celebration or punishment
- make table output feel precise, readable, and lightweight

Implementation guidance:
- do not change the meaning of correctness or the evaluation flow
- keep the output comparison easy to understand at a glance
- use spacing, typography, and subtle accents before reaching for strong color fills
- make empty states, null values, and zero-row results feel intentional

Specific goals:
- refine verdict hierarchy and tone
- improve feedback-card readability
- improve results-table presentation, including empty and null cells
- make “Your Output” vs “Expected Output” easier to compare
- make hint reveal controls and official solution presentation calmer and more polished

Acceptance checks:
- results and feedback feel more professional and less noisy
- revision after an incorrect answer feels guided, not punitive
- tables remain easy to scan
- hints and solution reveals feel progressive and trustworthy
- tests and build still pass
```
