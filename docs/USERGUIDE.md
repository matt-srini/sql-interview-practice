# User Guide

`datathink` is a data interview practice platform built around 9 tracks, 4 hiring-role lenses, a full practice curriculum, and a separate mock benchmark layer.

## Modes

### Practice mode (`/practice/:topic`)
The main curriculum. Practice is the full bank: 878 questions across SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation. Progress and unlocks are tracked independently per topic.

### Sample mode (`/sample`)
Low-stakes trial mode. No login required and no effect on practice progress. The Sample Hub at `/sample` is the entry point — pick any of the 9 tracks and any difficulty (Easy / Medium / Hard) from a single grid. Every track has 3 questions per difficulty (81 total) that are completely separate from the practice and mock banks. Once inside a sample (`/sample/:topic/:difficulty`), an in-page switcher lets you pivot to a different track or difficulty without going back to the Hub. Logged-in users see which (track, difficulty) cells they've already tried.

### Mock mode (`/mock`)
Timed benchmark sessions for authenticated users. Mock sessions hide solutions until the end, track time usage, and generate post-session review. Mock-only questions are used where available.

### Dashboard (`/dashboard`)
Cross-track coaching hub. It shows solved totals, per-track pace and accuracy, streak state, recent activity, weak concepts, and for Elite users, readiness scores and a study plan.

## Getting started

You can begin without an account. The platform creates an anonymous session automatically so your progress is still tracked. Registering upgrades that session in place, and logging into an existing account merges anonymous progress.

## Track styles

- SQL, Python, Pandas, and numerical Statistics are executable tracks: you can run code before submitting.
- PySpark is code-adjacent reasoning: questions often show snippets, execution context, or debugging scenarios, but do not run Spark.
- Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and conceptual Statistics are reasoning-first tracks focused on diagnosis, interpretation, and decision-making.

## Workspace basics

Each question lives in the same core workspace:

- Left side: prompt, supporting context, schema or variables when relevant, hints, and solution controls
- Right side: editor for executable questions, or answer panel for reasoning questions
- Result area: result table, test cases, stdout, or explanation panel depending on track

## Run vs submit

- `Run` is only available on executable questions. It lets you inspect output without affecting progress.
- `Submit` is the scoring action. A correct submit marks the question solved and can unlock more questions.
- On reasoning-first tracks there is no fake `Run` step. You read, reason, and submit.

## Hints and solutions

Hints are progressive. The platform reveals them one at a time after you submit. Full solutions stay gated behind the hint ladder so you do not short-circuit the learning loop.

## Unlock system

Free users get all easy questions and unlock medium and hard in batches as they solve more of the curriculum. Thresholds differ by modality (code vs MCQ tracks).

Pro unlocks all practice difficulties across all tracks. Elite keeps full catalog access and adds the premium mock and dashboard layers.

## Learning paths

Learning paths are curated 5–9 question walks layered on top of the practice bank. They are not a separate curriculum and they do not shortcut unlocks. Each path masters one *pattern* (a practitioner skill like "Window Functions" or "Causal Inference") by walking through existing practice questions easy → hard within that pattern.

## Mock sessions

Mocks are for benchmarking, not answer-peeking.

- You choose track, difficulty, and session mode
- The timer starts immediately
- Solutions are hidden during the session
- Review happens after finish, with concept breakdowns and plan-gated coaching depth

## Dashboard coaching

The dashboard combines practice and mock signals:

- per-track solved totals and difficulty breakdowns
- median solve time and submission accuracy
- streak state and recent activity
- weak concepts and recommended next work
- Elite-only readiness scores and study plan

## Accounts and sessions

- No account is required to explore samples or start practicing
- Registered accounts preserve progress across devices
- Sessions use server-side cookies
- Progress is permanent unless content itself changes

## Limits and guardrails

- SQL execution is read-only
- SQL results are capped at 200 rows and time out after 3 seconds
- Python-family execution runs in a sandbox with strict time and memory limits
- Non-executable tracks intentionally do not pretend to execute code when that would not reflect the real interview skill
