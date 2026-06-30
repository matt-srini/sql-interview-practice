---
title: "A/B Test Interview Questions: What a Good Answer Looks Like"
description: "A/B test interview questions probe experiment design judgment: choosing the metric, powering the test, and trusting the result, not reciting p-values."
slug: "ab-test-design-interview-questions"
date: 2026-06-30
updated: 2026-06-30
draft: false
---

A/B test questions look, on the surface, like they want a definition of a p-value. They almost never do. What the interviewer is really after is whether you can design an experiment that answers the question being asked, and whether you can tell when an experiment is quietly broken. Those are the skills that decide whether an experimentation program produces real decisions or a steady stream of confident, wrong ones.

I have asked some version of "how would you test this" many times, and the answers split fast. Some people reach immediately for the statistics, compute a sample size, and never stop to ask what they are actually trying to measure. Others start where the job starts, with the metric and the decision, and the statistics fall into place behind it. The second group is who you want running your experiments, and the interview is built to tell them apart.

## Pick the metric before you touch the statistics

"We changed the checkout button. Did it work?" Work how? More clicks on the button is trivial to move and almost meaningless. Completed purchases is better. Revenue per visitor is better still, but now you have variance to worry about. And whatever you pick as the success metric, you need guardrail metrics next to it, because a change that lifts conversion while quietly tanking refund rate or load time is not a win.

A strong answer defines the primary metric, names a guardrail or two, and explains why, before any mention of significance. Interviewers hand you a vague goal on purpose and watch whether you turn it into a measurable, sensible outcome or just start computing. The choice of metric is the part most likely to make the whole experiment pointless, so it is the part they probe hardest.

## "How long do we run it" is really a question about power

Once the metric is set, the natural question is how long the test needs to run, and that is where power, sample size, and minimum detectable effect come in. The reasoning they want is roughly: how big an effect would actually matter to the business, how much traffic do we get, how much variance is in the metric, and therefore how long until we could detect an effect that size with reasonable confidence. You do not usually need to derive the formula in the room. You need to show you understand that a test too small to detect the effect you care about is a waste of time, and that the run length is a decision you make before you start, not after you peek.

And you do not peek. The follow-up here is often about stopping early. If you check the results every day and stop the moment you see significance, you will "find" effects that are not real, because you gave yourself many chances to cross the line by luck. Knowing why that is a problem, and that the run length should be fixed up front or analyzed with a method built for sequential looks, is a real signal of experience.

## The result you should not trust: sample ratio mismatch

Here is the check most candidates never mention, which is exactly why it impresses interviewers when you do. You split traffic 50/50, and the results come back with 48% in one arm and 52% in the other on a large sample. That imbalance should not happen by chance, and when it does, something is wrong with the assignment or the logging, which means the comparison itself is suspect no matter how pretty the lift looks. A good experimenter validates that the split came out as designed before they believe a single downstream number. Mentioning sample ratio mismatch unprompted tells the interviewer you have actually shipped experiments, not just read about them.

## "A PM ran eight tests and one came back significant"

This one is about multiple comparisons, and it is a favorite because it is so common in real life. Run enough tests, or slice one test enough ways, and something will cross the significance threshold by chance alone. The candidate who treats that one winning result as a discovery has failed the question. The one who says "with eight tests, I'd expect a false positive or two, so I'd want a correction, or a holdout to confirm it before we act" has passed it. The deeper point they are testing is whether you understand that significance is not truth, especially once you have gone looking in many places.

## Knowing when not to run a test at all

The most senior answer sometimes is "I would not A/B test this." Not enough traffic to ever reach power. A change you cannot cleanly randomize. Something irreversible or ethically fraught where a controlled rollout or a different method fits better. Recognizing the limits of the tool is itself part of the judgment, and interviewers will sometimes hand you a scenario specifically to see whether you reach for an experiment reflexively or think about whether it is the right instrument.

## How to actually prepare for it

The preparation follows the test. You are being asked to design and defend, so practice designing and defending, end to end.

Take a vague product goal and walk the whole path out loud: the metric, the guardrails, the hypothesis, the traffic and power, the run length, the checks you would run before trusting the result. Saying it out loud matters, because the gaps in your reasoning are obvious the moment you have to narrate them and invisible when you only nod along.

Then attack your own design the way the follow-ups will. Why that metric? What if the split is off? What if it is significant on day two? What would make you not trust the result? Reasoning from the mechanism means the follow-ups are just the same understanding viewed from another angle. Reciting definitions means the first real twist ends the conversation.

If you want to test that reasoning against real questions, try a free experimentation sample, no account required, at [/sample/experimentation](/sample/experimentation). And if you are preparing for the full data science loop, the [data scientist interview prep guide](/interview-prep/data-scientist) covers the six tracks the role spans and where experimentation sits among them.

The p-value definition you can look up. The judgment about what to measure, how long to run it, and whether to believe the answer is what the interview is built to find, and it is the same judgment that keeps an experimentation program honest long after the interview is over.
