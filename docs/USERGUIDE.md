# User Guide

`datanest` is a data interview practice platform. Write SQL or Python, answer PySpark MCQs, get instant feedback, and work through progressively harder tracks.

---

## Two practice modes

### Challenge mode (`/practice/:topic`)
The main track. Each topic has its own guided question bank and saved progress. Questions unlock as you solve them.

### Sample mode (`/sample/:topic/:difficulty`)
A no-stakes sandbox. Every track has easy, medium, and hard sample rounds with 3 questions per round. No login required, no effect on your challenge progress. Good for getting a feel for the platform before committing.

---

## Getting started

You don't need an account. Land on the homepage and you can jump straight into sample questions or start the challenge track. An anonymous session is created automatically and your progress is saved to it.

When you register, your anonymous progress carries over. Nothing is lost.

---

## The question screen

Each question uses a two-column workspace:

**Left panel**
- The question prompt — what you need to return
- The schema or available dataframe variables, depending on track
- Hints and solution (revealed progressively after you submit)

**Right panel**
- The code editor or answer area
- Run and Submit buttons when the track supports execution
- Results, test cases, or MCQ feedback depending on track

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
- All Easy questions are available immediately
- Medium unlocks in batches as you solve Easy questions (thresholds vary by track):
  - SQL / Python / Pandas: 8 solved → 3 medium · 15 → 8 medium · 25 → all medium
  - PySpark: 12 solved → 3 medium · 20 → 8 medium · 30 → all medium
- Hard unlocks the same way as you solve Medium (capped at 15 for code tracks, 10 for PySpark)
- **Shortcut:** Completing a learning path unlocks the full medium or hard tier for that track immediately

**Pro plan**
- All Easy + all Medium + all Hard unlocked immediately (no cap)

**Elite plan**
- Full catalog across all four tracks — 350 questions total

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

- 3 questions per track+difficulty
- Each question is shown once per session — you won't see the same sample twice until you reset that track+difficulty
- When all 3 are exhausted, a reset button appears
- Run and submit mirror the main track behavior for that topic, and samples reveal the official solution/explanation after submit where applicable
- Nothing here affects your challenge progress or unlock state

---

## Limits

- Queries are read-only. `INSERT`, `UPDATE`, `DELETE`, `DROP`, etc. are blocked
- Results are capped at 200 rows in the display
- Queries time out after 3 seconds
- Rate limiting applies per IP (60 requests per minute)
