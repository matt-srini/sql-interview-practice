---
title: "A/B Test Interview Questions: What a Good Answer Looks Like"
description: "A/B test interview questions test experiment design: metrics, guardrails, power, sample ratio checks, and whether to trust the result."
slug: "ab-test-design-interview-questions"
date: 2026-06-30
updated: 2026-07-14
draft: false
---

A/B test interview questions can sound like statistics questions, but they usually test the full experiment decision. The interviewer wants to know whether you can turn a product question into a clean test, choose a metric that matches the decision, and notice when the result should not be trusted.

You do need the statistics. But a good answer does not start and end with a p-value. It starts with what the team is trying to learn.

## Start With The Decision

Before designing the test, say what decision the experiment is meant to support. Are we deciding whether to ship a checkout change? Whether a recommendation module improves engagement? Whether a new onboarding flow helps users reach activation?

That decision shapes the metric. Button clicks might be useful as a diagnostic, but completed purchases or activated users may be closer to the real goal. Revenue per visitor may be better than conversion rate if order size changes. Retention may matter more than day-one engagement if the product is trying to build a long-term habit.

A strong answer usually names:

- The primary success metric.
- One or two guardrail metrics.
- The user population included in the test.
- The time window for reading the result.

This keeps the test tied to the product question instead of becoming a generic statistics exercise.

## Power Is About Detecting A Useful Effect

"How long should the test run?" is really a question about power. A test needs enough traffic to detect an effect size that would matter. If the team only cares about a 5 percent lift, the design should not be built around chasing a tiny movement that would not change the decision.

You do not usually need to derive the sample size formula in an interview. You should be able to explain the inputs: baseline rate, expected variance, minimum detectable effect, traffic, desired power, and significance level. You should also mention that the run length should be planned before the test starts.

Peeking every day and stopping when the result first becomes significant is a common trap. It increases the chance of finding a false positive. If the team needs continuous monitoring, the analysis method should account for sequential looks rather than pretending every daily check is independent.

## Check The Assignment Before Believing The Lift

One of the most useful experiment sanity checks is sample ratio mismatch. If traffic is supposed to split 50/50 but the final assignment is 48/52 on a large sample, something may be wrong with randomization, eligibility, or logging.

That matters because a broken split can make every downstream metric suspicious. A polished answer that jumps straight to the lift but never checks whether the experiment was assigned correctly is missing an important step.

Other basic trust checks include:

- Did both variants run for the same calendar period?
- Were users assigned once and kept in the same group?
- Did logging change during the test?
- Were there major outages, launches, or campaigns during the window?

These checks do not make the answer complicated. They make it believable.

## Multiple Comparisons Need Care

If a team runs many tests, or slices one test into many subgroups, some results will look significant by chance. Interviewers often ask about this because it comes up constantly in product analytics.

A reasonable answer might use a correction, pre-register a small number of primary metrics, treat subgroup reads as exploratory, or run a follow-up test. The exact choice depends on the context. The key is showing that "one significant result" is not automatically the same as "one true result."

## Sometimes The Right Answer Is Not To A/B Test

Not every product question is a good A/B test. Maybe the traffic is too low. Maybe the change cannot be randomized cleanly. Maybe the risk is too high for a broad experiment. Maybe the outcome takes months to observe. In those cases, a holdout, phased rollout, observational analysis, user research, or a smaller instrumentation pass may be more useful.

This is not a trick answer. It is part of experiment design judgment. The goal is to choose a method that answers the question responsibly.

## How To Prepare

Practice walking through the full test, not just the statistical definition:

1. State the product decision.
2. Choose the primary metric and guardrails.
3. Define the population and randomization unit.
4. Discuss power, run length, and minimum detectable effect.
5. List the checks you would run before trusting the result.
6. Explain the decision you would make from different possible outcomes.

If you want to try this style of question, start with the free Experimentation sample at [/sample/experimentation](/sample/experimentation). If you are preparing for the broader data scientist loop, the [data scientist interview prep page](/interview-prep/data-scientist) shows where experimentation sits among ML, statistics, Product Sense, Python, Pandas, and SQL.

The short version: an A/B test interview is asking whether you can design an experiment that leads to a decision. The math supports that decision, but the design is what makes the math worth trusting.
