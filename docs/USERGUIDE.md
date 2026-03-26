# User Guide

A SQL interview practice platform. Write SQL, get instant feedback, work through progressively harder questions.

---

## Two practice modes

### Challenge mode (`/practice`)
The main track. 86 questions across three difficulty tiers — Easy (30), Medium (30), Hard (26). Your progress is saved. Questions unlock as you solve them. This is where you build up.

### Sample mode (`/sample/easy`, `/sample/medium`, `/sample/hard`)
A no-stakes sandbox. 3 questions per difficulty, served in random order. No login required, no effect on your challenge progress. Good for getting a feel for the platform before committing.

---

## Getting started

You don't need an account. Land on the homepage and you can jump straight into sample questions or start the challenge track. An anonymous session is created automatically and your progress is saved to it.

When you register, your anonymous progress carries over. Nothing is lost.

---

## The question screen

Each question has two panels:

**Left panel**
- The question prompt — what you need to return
- The schema — which tables and columns are available for this question
- Hints and solution (revealed progressively after you submit)

**Right panel**
- The SQL editor — write your query here
- Run and Submit buttons
- Results table showing your query output

---

## Running vs. submitting

**Run** — executes your query and shows the results. No judgement, no progress impact. Use it as often as you like to check your output.

**Submit** — evaluates your query against the expected answer. This is what marks a question solved and unlocks the next one.

You can run as many times as you want before submitting.

---

## How answer matching works

Your result is compared against the expected result set — not against a specific query. If your query produces the same data, it's accepted.

A few specifics:
- **Column order doesn't matter** — you can return columns in any order
- **Row order doesn't matter** — unless the question explicitly asks you to order results. If the expected answer uses `ORDER BY`, your result needs to match that order too
- **Duplicate rows are preserved** — if your query returns extra duplicates, it won't match
- **Float precision** — small rounding differences are tolerated
- **NULL values** — handled correctly; a NULL in the expected output must be NULL in yours

If your result doesn't match, you'll see both your output and the expected output side by side so you can spot the difference.

---

## Hints and solutions

Each question has 1–2 hints. They're hidden by default and revealed one at a time after you submit. If your answer is wrong, you'll see a "Show hint" option.

The full solution (correct query + explanation) only appears after you've seen all hints for that question. This is intentional — hints first, solution as a last resort.

---

## Unlock system

**Free plan**
- All 30 Easy questions are available immediately
- Medium unlocks in batches as you solve Easy: 10 solved → first batch, 20 → second, 30 → all
- Hard unlocks the same way as you solve Medium questions

**Pro plan**
- All Easy + all Medium unlocked immediately
- First 22 Hard questions unlocked

**Elite plan**
- Full catalog — all 86 questions unlocked

Solved questions stay solved permanently, regardless of plan changes.

The sidebar shows your progress and the state of each question: solved, unlocked (available to attempt), or locked.

---

## The sidebar

Questions are grouped by difficulty. Easy is open by default; Medium and Hard are collapsed until you have something to work on there.

Each question shows one of these states:
- **Solved** — you've submitted a correct answer
- **Next** — the recommended next question to tackle
- **Unlocked** — available but not yet attempted
- **Locked** — not yet accessible at your current plan or progress level

---

## Accounts and sessions

- No account needed to start
- Register to persist progress across devices and browsers
- Login merges any anonymous progress into your account
- Sessions are cookie-based; you stay logged in until you log out

---

## Sample mode details

- 3 questions per difficulty (9 total)
- Each question is shown once per session — you won't see the same sample twice until you reset
- When all 3 are exhausted, a reset button appears
- Run and submit work the same as challenge mode; you see the solution after submitting
- Nothing here affects your challenge progress or unlock state

---

## Limits

- Queries are read-only. `INSERT`, `UPDATE`, `DELETE`, `DROP`, etc. are blocked
- Results are capped at 200 rows in the display
- Queries time out after 3 seconds
- Rate limiting applies per IP (60 requests per minute)
