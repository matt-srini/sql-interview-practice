---
title: "The Data Engineer SQL Interview: What It Really Tests"
description: "Data engineer SQL interviews test judgment, not syntax: grain, fan-out, idempotency, and queries that stay correct as tables outgrow memory."
slug: "data-engineer-sql-interview-reasoning"
date: 2026-06-29
updated: 2026-06-29
draft: false
---

Search "data engineer SQL interview" and you get a stack of articles that all reduce to the same checklist: learn window functions, learn CTEs, memorize the join types, grind fifty problems. None of it is bad advice. It is just pointed at the wrong target. I have interviewed people who could recite all of that and still wrote a query that would have double-billed customers in production, and I have passed people who stopped, asked what the grain of the table was, and worked the rest out slowly. The second kind tends to get the offer.

Here is what the checklist misses. When an analyst gets a SQL question, the unspoken version is usually "given this data, give me this number." When a data engineer gets one, the unspoken version is closer to "this query is going to run every night for two years, against tables that keep growing and a source that occasionally lies, so is it still correct on night six hundred?" Same SELECT statement, very different question. A lot of interview prompts are quietly built to find out which of those two you actually hear.

Four situations come up again and again, and each one is really probing the same thing: does this person reason about the data, or just about the syntax.

## The double-count nobody catches until finance does

Give a candidate an `orders` table and an `order_items` table and ask for revenue per customer. A lot of them will join orders to items and sum the order total. The trouble is that the order total now appears once per line item, so a three-item order counts its revenue three times. The query runs clean, the dashboard renders, everyone moves on. Then three weeks later someone in finance pings you asking why the numbers do not tie out, and you spend a Friday afternoon reverse-engineering your own join.

The habit that prevents this is not a rule you memorize, it is a question you ask before you type the join: what is one row in each table, and what is one row in the result? Orders joined to items gives you one row per item, not per order. If your SUM is written as though there is one row per order, the answer is already wrong and nothing about the query will tell you so. In the interview, the candidates who say "wait, what is the grain here" out loud before touching the keyboard are usually the ones who have been burned by exactly this, and it shows.

## "Latest status per user", and the reflex to reach for DISTINCT

This one looks trivial and is not. Ask for the most recent status per user and watch where people go first. DISTINCT dedupes whole rows, which is not what was asked. GROUP BY user_id collapses the rows, sure, but now which status survives? You wanted the latest one, and GROUP BY has no concept of latest.

The shape the interviewer is hoping to see is `ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY updated_at DESC)`, filtered to the first row. Honestly though, the syntax matters less than whether you can say why it works: a window function ranks within a group while holding on to the detail row, where an aggregate would throw that detail away. Explain that and you have demonstrated the exact thing the question is there to find. Pattern-match the template without it and the follow-up will catch you, because there is always a follow-up. "What if two rows share the same timestamp?" is the usual one, and it is not a gotcha. It is a real problem you will hit the first week you run this against live data.

## Idempotency, or what happens when the job runs twice

If I had to name the single question that separates a data engineer from a strong SQL writer, it is this one, and it almost always shows up as an operational story rather than a query. "Your nightly job loads yesterday's events into a fact table. It dies halfway through. You rerun it. Now what?" If the load is a plain INSERT, the rerun writes everything it already wrote a second time. And it gets worse before it gets better, because an at-least-once source can hand you the same event twice with no failure at all. That is just what at-least-once delivery means.

The word the interviewer is fishing for is idempotency: running the load twice should leave you in the same state as running it once. In SQL that usually means a MERGE keyed on a business key, or deleting the target partition before you insert, or deduping on a stable event id before the write. Nobody is grading your MERGE syntax. They want to know whether the word "rerun" makes you slightly tense, and whether your first instinct is to reach for a key. If you have ever been on call when a backfill double-fired at 2am, you already have that instinct. If you have not, this is the concept worth internalizing before the screen, because it surfaces constantly once you are in the room.

## When the table outgrows the laptop

The last cluster is about scale, and it is where memorized vocabulary comes apart fastest. A self-join to compute a running total is O(n squared) and will cheerfully fall over on a real table, while the `SUM(...) OVER (ORDER BY ...)` version is linear and happens to read better too. Wrap a function around an indexed column in your WHERE clause and you have quietly switched the index off. Reach for SELECT DISTINCT to paper over a fan-out and now you are sorting a heap of rows that should never have existed in the first place.

Interviewers poke at this with "okay, now make it faster," and what they are listening for is whether you can say why one form is cheaper, not whether you happened to stumble onto a quicker query. The reasoning is the part being graded.

## So how do you actually prepare

The way you study should follow from what is being tested, and what is being tested is judgment that survives the data getting awkward. Grinding problems where you reproduce a template you already know does not build that, because the template is precisely the thing the real interview takes away from you. A few things help more than sheer volume.

Run your SQL against ugly data. Reading a query and nodding is a different activity from feeding it a three-item order, a duplicated event, and a tie in the sort column, and watching it hand back a number you know is wrong. The fan-out you debugged yourself sticks with you. The one you read a warning about does not.

Practice saying the why out loud, even on your own. Every situation above has a follow-up waiting behind it, and the follow-ups are where offers are actually decided. If you are reasoning from the mechanism, why the fan-out happens, why the window beats the self-join, why this load is not safe to rerun, then the next twist is just another version of something you already understand. If you are reciting shapes, the first twist that does not fit the shape tends to end the conversation.

And work with scenarios that feel like the job rather than a pile of disconnected puzzles. A data engineer SQL screen is really a small set of recurring judgments wearing different business clothes. Train the judgment and the clothes stop throwing you.

If you want an honest read on where your SQL reasoning stands right now, try a free SQL sample, no account required, at [/sample/sql](/sample/sql). And if you are prepping for the full loop and not just the SQL round, the [data engineer interview prep guide](/interview-prep/data-engineer) walks through the five tracks the role leans on and how they fit together.

You can always look the functions up mid-thought. The judgment about grain, duplication, replays, and scale is the part the interview is built to find, and it is the part that keeps paying you back long after the offer is signed.
