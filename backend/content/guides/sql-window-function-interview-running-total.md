---
title: "SQL Window Function Interview Questions: The Running Total Trap"
description: "A running total is the SQL window question people think they have solved. Here is the default frame decision that quietly breaks it when two rows tie."
slug: "sql-window-function-interview-running-total"
date: 2026-07-15
updated: 2026-07-15
draft: false
---

Ask a data analyst to write a running total and you will usually get the same answer, typed from memory almost without thinking. Cumulative revenue by day, a running headcount, a rolling balance per account: it is one of the first window-function shapes anyone learns, and it feels finished the moment it runs. That confidence is exactly what makes it a good interview question. The query that passes the first test case and the query that survives the follow-up look almost identical, and the gap between them is one decision most people never make on purpose.

Here is the setup. You have a payments table, one row per payment, and you want the cumulative amount paid on each account after each payment.

```sql
SELECT
  account_id,
  paid_on,
  amount,
  SUM(amount) OVER (PARTITION BY account_id ORDER BY paid_on) AS running_total
FROM payments;
```

On tidy data this is correct. One account, three payments on three different days: 100, then 40, then 60. The running total reads 100, 140, 200. Everyone nods, and in a lot of interviews the conversation moves on. The reasoning it skipped over only shows up when the data stops being tidy.

## The follow-up that exposes the frame

Now the interviewer adds one row. The account made two payments on the same day: a 40 and a 60, both dated the fifth. Run the same query and read the output.

Both same-day rows report 200. There is no 140 anywhere in the result. If you were building a per-payment balance, a statement that shows what stood on the account after each individual payment, that number is wrong. It reports the end-of-day total twice and never shows the step in between.

Nothing errored. The query is the same one that was correct a minute ago. What changed is that the data now has a tie on the column you ordered by, and a tie is where the window frame stops being invisible.

## What the default frame actually does

A window function has three parts: the partition, the order, and the frame. Most people write the first two and let the database fill in the third. When you supply an ORDER BY and no frame clause, SQL applies a default, and that default is RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.

The word doing the damage is RANGE. Under a RANGE frame, "current row" does not mean this one physical row. It means the current row together with all of its peers, every row that shares its value in the ORDER BY expression. Both payments on the fifth are peers, so each one's frame runs all the way through the end of that day, and both sum to 200. That is not a bug in the engine. It is the frame you asked for without knowing you asked.

Switch the frame to ROWS and the meaning of "current row" changes to what most people pictured all along:

```sql
SUM(amount) OVER (
  PARTITION BY account_id
  ORDER BY paid_on
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
```

Now the frame grows one physical row at a time: 100, 140, 200. ROWS counts rows; RANGE counts values. The two agree on every dataset with no ties, which is precisely why the distinction survives so many test cases before it finally bites.

## The second decision hiding underneath

ROWS fixes the sum, but a careful answer does not stop there. Once two payments share a date, which one counts as the 40 and which as the 60 inside the running total is undefined. The database is free to order the tied rows however it likes, so the intermediate value could be 140 on one run and 160 on another. For a report someone acts on, that is not good enough.

The fix is to make the order deterministic. Give the ORDER BY a tiebreaker the data actually supports, usually the primary key or an ingestion timestamp:

```sql
ORDER BY paid_on, payment_id
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
```

Now the sequence within a day is defined, and the running total comes out the same every time. This is the version that holds under questioning: the right frame so the sum means what you think it means, and a unique sort so the result is reproducible.

## Why this is a good interview question

Notice how little separates the two queries. One keyword, ROWS in place of an implied RANGE, plus a column in the ORDER BY. Someone who memorized the running-total template writes the first version and cannot say what the default frame does, because the template never made them look. Someone who reasons about it can tell you what a row means inside the window, why a tie is the moment it matters, and how to make the output stable. Same syntax, very different depth, and the follow-up is what tells them apart.

That generalizes well past running totals. The habit worth building is to stop when a query passes and ask what happens on the awkward row: a tie, a duplicate key, a null, a late arrival. Clean data hides these decisions. Interviews, and production, go looking for them.

If you want to feel the difference rather than read about it, the [data analyst interview prep](/interview-prep/data-analyst) page shows where SQL sits among the other things analyst interviews check, and you can run a window-function problem on a real engine, no login, with a [SQL sample](/sample/sql/medium). Try the naive frame first, then add a tied row and watch the number move. It is a faster teacher than any explanation.
