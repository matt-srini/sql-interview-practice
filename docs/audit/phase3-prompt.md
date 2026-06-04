# Phase 3 — Paid external-model (OpenAI GPT-5) blind audit — orchestrator prompt

Paste the block below into a **fresh Opus session** to run Phase 3. The OpenAI key
is already in `backend/.env` (`OPENAI_API_KEY`, an `sk-proj-…` value, verified live
2026-06-04). `gpt-5-mini` and `gpt-5` were both probed live (HTTP 200) on the same
date. This file is temporary — delete it (with the findings log + the phase2 prompt)
when the multi-phase audit closes.

---

```
★ MODEL CHECK: This session requires Opus as orchestrator. If you are not Opus,
stop immediately and ask the user to switch before proceeding.

═══════════════════════════════════════════════════════════════
BLIND AUDIT — PHASE 3 (Paid external model: OpenAI GPT-5)
═══════════════════════════════════════════════════════════════

## What this is
Phase 3 of a multi-phase correctness audit of the datathink question bank, using a
THIRD independent model family (OpenAI GPT-5) — orthogonal to Claude (Phase 1) and
to Nvidia NIM's Llama/gpt-oss (Phase 2). Premise unchanged: a question where an
independent external model ALSO disagrees with the key is a high-confidence defect.
Phase 3 adds two things over Phases 1–2:
  (a) a paid, frontier model family as a third independent signal on the 6 MCQ tracks;
  (b) FIRST-EVER coverage of the 3 CODE tracks (SQL / Python / Pandas) via
      EXECUTION-based blind verification — Phases 1–2 were MCQ-only.

You (Opus) plan and orchestrate; offload execution (writing/adapting harnesses,
running batches, blind-solving code tracks, classifying, fixing) to Sonnet subagents
via the Agent tool when useful.

## Read before doing anything (binding context)
Root: /Users/matt/Work/projects/sql-interview-practice
  CLAUDE.md                                   — constraints, standing instructions, model-gate text
  docs/content-authoring.md                   — authoring contract + § Reject on sight (now incl. the
                                                machine-enforced label-collision guard)
  .github/agents/question-authoring.agent.md  — authoring agent process (mandatory for ALL content edits)
  backend/scripts/audit_findings_log.md       — THE PHASE 1 + PHASE 2 RECORD. Read fully. The 28 fixed
                                                Phase-1 key bugs; Phase-2's 0 key errors across 1,235
                                                MCQs; the 23 label-collision fixes + 28 self-matching
                                                cleanup; and the PHASE-3 HOLD LIST (42098, 93019).
  backend/scripts/audit_blind_answer_nim.py   — the Phase-2 OpenAI-SDK harness. REUSE IT for the 6 MCQ
                                                tracks (it already speaks the OpenAI SDK + is resumable);
                                                adapt for OpenAI/GPT-5 per the gotchas below.
  backend/evaluator.py, backend/python_evaluator.py, backend/python_sandbox_harness.py
                                              — the EXECUTION oracles for the 3 code tracks. STUDY THESE
                                                to build the code-track blind-solve harness.

Phases 1–2 already fixed/confirmed the MCQ bank, so a fresh GPT-5 MCQ pass should be
MOSTLY consistent. Phase 3's value: (a) a frontier third opinion on the 6 MCQ tracks
(esp. the 2 hold-list questions); (b) the never-audited code tracks.

## External model — OpenAI GPT-5 (KEY ALREADY IN .env). PAID — cost matters.
Use the `openai` Python SDK with the DEFAULT base_url (api.openai.com/v1):
    api_key = os.environ["OPENAI_API_KEY"]   # already in backend/.env (sk-proj-…), verified live
MODELS (probed live HTTP 200 on 2026-06-04; re-probe with a 1-token call before any run):
  - Pass 1 (blind answer):           gpt-5-mini
  - Pass 2 (explanation consistency): gpt-5
  (Catalog also has gpt-5.1 … gpt-5.5 + o3/o4-mini; the user specified gpt-5-mini /
   gpt-5 — keep those unless a probe shows them retired. Make models CLI-overridable.)

⚠ GPT-5 REASONING-MODEL GOTCHAS (discovered live — DO NOT skip):
  - They use `max_completion_tokens`, NOT `max_tokens` (the old param errors).
  - They are reasoning models: a small token budget is consumed entirely by hidden
    reasoning and returns content='' with finish_reason='length'. Give Pass 1
    ~2000 and Pass 2 ~4000 `max_completion_tokens` so visible content remains.
  - Do NOT set temperature=0 (these models reject non-default temperature on the
    chat endpoint) — OMIT temperature entirely.
  → The NIM harness sets `max_tokens` + `temperature=0`; you MUST adapt it (add a
    `--provider openai` code path or new flags) before it will work against GPT-5.

PAID COST DISCIPLINE (user decision, 2026-06-04): do NOT blanket `--pass2-all`.
  - Pass 1 (gpt-5-mini) on ALL ~1,235 MCQs (cheap-ish).
  - Pass 2 (gpt-5) ONLY on: (a) every Pass-1 DISAGREEMENT, (b) the Phase-3 hold list
    (42098, 93019), and (c) a survivor-class SAMPLE — e.g. a random ~10% of Pass-1
    agreements per track to spot-check for broken_mechanism. NOT all agreements.
  - Estimate token cost from the probe BEFORE the full run and report it; if a track
    looks unexpectedly expensive, pause and confirm.

## Methodology — 6 MCQ tracks (mirror Phase 2, two-pass)
PASS 1 — BLIND. Send ONLY stem (+ scenario_context) + the lettered options. No
correct_option, no explanation. Parse a robust A–D letter (reasoning models emit a
long trace — extract from "ANSWER: X" / "the answer is X" / a trailing letter; raise
max_completion_tokens if content is empty). Compare to correct_option (0=A…3=D).
PASS 2 — EXPLANATION CONSISTENCY (gated + targeted per the cost rule). Send stem +
options + explanation; ask which option the explanation's reasoning actually leads
to. On disagreements it disambiguates inverted_key vs review; on the sampled
agreements it hunts the survivor class (key right, explanation argues to a distractor
→ broken_mechanism).
VERDICTS (same as Phases 1–2): consistent / inverted_key (mechanical) /
broken_mechanism (authoring) / inconsistent (review). Emit the same JSON report
schema, plus a "phase12_cross_reference" field per flag (was it flagged/fixed in
Phase 1 or Phase 2? consult audit_findings_log.md + git log). Resumable per cell.

MCQ tracks in scope (have correct_option):
  pyspark · data-engineering · data-modeling · statistics (subtype=="conceptual" ONLY)
  · ml-fundamentals · experimentation  — each easy/medium/hard.json. MCQ filter =
  int correct_option AND options list ≥2. 18 cells.

## Methodology — 3 CODE tracks (NEW; oracle = EXECUTION, not model opinion)
Tracks: SQL (backend/content/questions/), Python (python_questions/),
Pandas (python_data_questions/). These are NOT MCQ — the stored expected answer is
already execution-validated at authoring time, so DO NOT re-check "does it run."
Phase 3 hunts a DIFFERENT defect class: AMBIGUOUS / NON-UNIQUE / UNDER-SPECIFIED
prompts and wrong expected outputs.

Procedure per code question:
  1. BLIND-SOLVE: give a solver ONLY the prompt (description/schema/starter_code/
     dataframes/test-case signatures) — NOT the expected_*/solution_* — and have it
     produce a candidate solution. The solver may be a Sonnet subagent (cheap, local;
     "do the code tracks here in Claude") and/or gpt-5-mini for an external signal.
  2. EXECUTE both the candidate AND the stored expected through the EXISTING
     evaluators: evaluator.py (SQL → DuckDB, normalized result compare) /
     python_evaluator.py + python_sandbox_harness.py (Python/Pandas → test cases).
  3. COMPARE: candidate passes (matches expected) → question reproduces, key good.
     Candidate is plausibly correct but yields a DIFFERENT result than expected →
     AMBIGUITY / non-unique-answer candidate → flag for human review. Candidate
     repeatedly fails despite sound reasoning → under-specified prompt → flag.
  Run the candidate through the SAME guards users hit (sql_guard.py / python_guard.py)
  so a "correct" answer that the production guard rejects is caught (the SQL CROSS JOIN
  lesson in content-authoring § 8a).

## Verify EVERYTHING (the hardest-won lesson across Phases 1–2)
The model/blind-solve verdict is only a SIGNAL. For every flag, read the source and
adjudicate before acting.
  - inverted_key / "mechanical" verdicts are NOT reliable auto-applies (Phase 1: 2/2
    were actually content defects). NEVER change correct_option without confirming the
    explanation + ground truth support it.
  - The MCQ bank is letter-convention, free of numeric refs and label-collisions
    (validator ERRORs on all three). External disagreements driven by phrasing →
    scrutinise, don't auto-fix.
  - Phase-3 hold list (42098, 93019): keys are defensible but two model families
    already blind-pick the alternative. If GPT-5 ALSO disagrees, ESCALATE from
    "defensible hard question" to a genuine keying decision — surface to the user
    with the three-family evidence; do not unilaterally flip.

## Fix path (same governance as Phases 1–2)
  1. correct_option genuinely wrong (verified): mechanical JSON fix, apply directly
     (the ONLY field editable without the authoring agent). validate + commit.
  2. Content wrong (explanation/option/stem/prompt): MUST go through the authoring
     agent. Do NOT self-edit content text. Any Sonnet handoff that authors/remaps
     content MUST open with the exact model-gate text from CLAUDE.md.
  3. After any fix batch: `cd backend && ../.venv/bin/python scripts/validate_content.py`
     must end "Content validation passed" (ERRORs on numeric option refs, explanations
     refuting their keyed option, and cross-position label collisions). For code-track
     fixes also re-run the relevant evaluator + (SQL) the /api/sample-style guard path.
     Then commit.
  - Work on main. Commit per batch with a clear message + the Opus co-author line.
  - Per the user's audit-workflow preference: verify findings, give a full summary
    with root-cause + doc-gap analysis, then STOP for approval before fixing.

## Work order
  1. Confirm Opus. Read the context files (esp. audit_findings_log.md — Phase 1 + 2).
  2. Confirm OPENAI_API_KEY in backend/.env; probe gpt-5-mini + gpt-5 (1-token each,
     using max_completion_tokens, no temperature); report final models + a token-cost
     estimate for the gated plan.
  3. MCQ side: adapt audit_blind_answer_nim.py for OpenAI/GPT-5 (provider flag:
     default base_url, OPENAI_API_KEY, max_completion_tokens, no temperature; gated
     Pass-2 not pass2-all; phase12 cross-ref). Smoke-test on 2 questions. Then run the
     18 MCQ cells (resumable), reviewing flags against source. Priority: the hold list.
  4. CODE side: build the execution-based blind-solve harness over evaluator.py /
     python_evaluator.py. Smoke-test on 2 questions per code track. Then sweep SQL,
     Python, Pandas — blind-solve, execute candidate + expected, compare, flag
     ambiguity / non-unique / under-specified. Review every flag against source.
  5. Apply verified mechanical fixes; route content defects to the authoring agent.
     validate_content.py (+ evaluators for code) + commit per batch.
  6. Append a Phase-3 section to backend/scripts/audit_findings_log.md: models used,
     gated-Pass-2 cost, per-cell MCQ results, code-track results, cross-reference with
     Phases 1–2, new findings, hold-list resolution. Do NOT delete the log.

## Out of scope
  Any later phase. Finish Phase 3 (6 MCQ tracks via GPT-5 + 3 code tracks via
  execution) and stop for user approval before fixes.

═══════════════════════════════════════════════════════════════
START: confirm Opus → read context → confirm OPENAI_API_KEY → probe GPT-5 models
(max_completion_tokens, no temperature) → adapt MCQ harness + build code harness.
═══════════════════════════════════════════════════════════════
```
