# Practice Modality Spec

Status: canonical planning spec
Owner: product + orchestration
Last updated: 2026-05-19

## Purpose

This spec defines the canonical modality model for practice so tracks are not reduced to a false binary of coding vs MCQ.

## Response mechanism is not a question type

Two orthogonal axes:

- **Response mechanism** — how the user answers. `MCQ` (radio buttons, single-best-answer) or `code editor` (executable). Track-level. Encoded as `eval_kind` (`mcq` / `mixed` / `sql` / `python` / `pandas`) and surfaced in `MCQPanel.js` / `hasMCQ`.
- **Question type** — the cognitive skill the question exercises. Per-question. Recorded in the JSON `type` field. Valid values: `conceptual`, `scenario`, `debug`, `predict_output`, `optimization`, `numerical`.

The value `mcq` is **NEVER** a valid question `type`. A `scenario` question and a `conceptual` question may both use MCQ response — they are still different question types because they exercise different reasoning.

Docs that conflate the two ("MCQ / scenario / debug formats") collapse this distinction. Always list real `type` values; if you need to mention the response UI, say so separately: "Question types: conceptual / scenario / debug. Response: MCQ."

This section is the **canonical citation for terminology pushback**. When a doc or prompt says "MCQ / scenario / debug" and means question types, it is wrong. Fix it to real type values.

## Modality families

| Modality | Definition | Typical user action |
|---|---|---|
| Executable problem-solving | User writes code/query and can run it before submit | implement, inspect, refine |
| Code-adjacent reasoning | User reasons about code, execution, debugging, or outputs without full execution | debug, predict, explain, choose |
| Constructed reasoning | User analyzes a scenario, design, tradeoff, or result and commits to a justified answer | diagnose, design, interpret, prioritize |
| Hybrid | Track contains more than one modality family and must expose that difference explicitly | switch between reasoning and execution |

## Canonical track matrix

| Track | Canonical modality | Current execution reality | Product implication |
|---|---|---|---|
| SQL | Executable problem-solving | DuckDB execution | Keep fully executable |
| Python | Executable problem-solving | Sandbox execution | Keep fully executable |
| Pandas | Executable problem-solving | Sandbox execution | Keep fully executable |
| Statistics | Hybrid | Conceptual + numerical split | Surface subtype clearly |
| PySpark | Code-adjacent reasoning | No Spark execution | Uplift beyond thin option-picking |
| Data Engineering | Constructed reasoning | No execution | Focus on systems reasoning |
| Data Modeling | Constructed reasoning | No execution | Focus on design quality and tradeoffs |
| ML Fundamentals | Constructed reasoning with selected code-adjacent cases | No execution today | Prioritize diagnosis over recall |
| Experimentation | Constructed reasoning | No execution | Prioritize interpretation and decision quality |

## Practice UX rules

- Never describe every non-executable track as an MCQ track.
- Use verbs that reflect the real task: debug, predict, diagnose, design, interpret, prioritize.
- Only show `Run` where real execution exists.
- Do not add fake editors to tracks that are not genuinely executable.
- Where a track is hybrid, subtype must be explicit in the payload and UI.

## MCQ wrong-answer journey (gated re-attempt)

On MCQ-response questions a wrong answer is **gated** — neither a free retry loop nor a dead end:

1. **Wrong submit** → verdict "Not quite" (never "Keep iterating" — that copy is code-track-only, where re-running is legitimate). The options lock and Submit disables; the only way forward is the reasoning ladder.
2. **Hint ladder** → hints reveal one at a time, with a quiet "Skip to the answer". The terminal "Reveal the answer" step lights the correct option tile and renders the explanation **in place** (co-located with the trigger — fixes a mobile blind spot where the reveal otherwise landed off-screen).
3. **Re-attempt** → revealing re-opens the options (`MCQPanel canReselect`); the user selects the correct answer and submits → **solved**.

The post-reveal solve **counts as a solve identically to a code-track solve** — there is no reveal penalty (a code-track user can likewise reveal the Official Solution before solving). A raw solve count measures engagement/pacing, not first-try mastery; mastery signals (first-try accuracy) belong on the dashboard. "Next" appears only on a solve and never points at the current question. Runtime SoT: `frontend/src/pages/QuestionPage.js` + `frontend/src/components/MCQPanel.js`. Why: `docs/decisions/DECISIONS.md` 2026-06-26.

## Metadata contract

The modality migration should converge on these concepts:

- `eval_kind`: execution or answer-checking behavior
- `subtype`: track-specific question form
- `interaction_mode`: canonical user interaction framing used by product surfaces

`interaction_mode` is the product-level field that prevents drift back into generic quiz language.

## Track-specific notes

### PySpark

PySpark is the first priority for uplift. It already contains stronger question shapes than the current generic MCQ framing suggests. The product should present it as technical reasoning about Spark behavior, debugging, and execution consequences.

### Statistics

Statistics must remain explicitly hybrid. Conceptual questions and numerical Python questions should not be blurred into one undifferentiated experience.

### Data Engineering / Data Modeling / ML Fundamentals / Experimentation

These tracks should earn depth through scenario quality, diagnosis, tradeoffs, and explanation quality, not through forced execution.

## Anti-patterns

- Rebranding shallow option-picking as deep reasoning without fixing question quality
- Forcing every track into a code editor because coding feels more premium
- Using one generic practice UI label across fundamentally different interaction types
- Hiding subtype distinctions that meaningfully change how a question should be approached

## Quality bar by modality

- Executable tracks must reward correct, transferable implementation.
- Code-adjacent tracks must test execution understanding, debugging logic, or system behavior.
- Constructed-reasoning tracks must test analysis, tradeoffs, and interview-grade judgement.
- Hybrid tracks must make the user aware of which mode they are in before they answer.
