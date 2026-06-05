# Phase 4 — Final confirmation audit prompt (gpt-5-mini + gpt-5, all 9 tracks)

Working artifact (gitignored sibling of phase2/phase3 prompts). Paste the block below
into a fresh **Opus** session to run the final pre-launch question-bank audit.

**Cost (recomputed from Phase-3 actual token usage):** MCQ Pass-1 ~$1.6 · MCQ Pass-2
**all** ~$7.2 · code blind-solve ~$1.6 · stats-numerical ~$0.2 → **≈ $10.6 total**.
That is right at a $10.70 balance and will likely exhaust mid-run — **recharge to ~$20–25**
before running pass2-all. **Toggle:** to fit a smaller balance, drop `--pass2-all` (use the
gated default: disagreements + ~10% survivor sample) → MCQ ≈ $2.7, **~$4.5 total**. Phase 3
gated found 0 survivors; pass2-all is belt-and-suspenders.

---

```
★ MODEL CHECK: This session requires Opus as orchestrator. If you are not Opus,
stop immediately and ask the user to switch before proceeding.

═══════════════════════════════════════════════════════════════
FINAL CONFIRMATION AUDIT (Phase 4) — gpt-5-mini + gpt-5, ALL NINE TRACKS
Pre-launch hardening: one last green light before closing the question-bank audit.
═══════════════════════════════════════════════════════════════

## What this is
A comprehensive FINAL re-audit of the entire datathink question bank with the same
paid frontier family used in Phase 3 (OpenAI gpt-5-mini for Pass-1 / blind-solve,
gpt-5 for Pass-2), but now exhaustive on three axes:
  (a) ALL NINE tracks (Phase 3 was 6 MCQ + 3 code; this adds Statistics-numerical);
  (b) pass2-all — gpt-5 explanation-consistency on EVERY MCQ, not a gated sample;
  (c) practice + mock-only (the full bank).
Goal: confirm 0 wrong keys / 0 ungradeable questions remain before launch, and that
nothing this session changed regressed. You (Opus) plan + adjudicate; offload bulk
execution to Sonnet subagents when useful.

## Read before doing anything (binding context)
Root: /Users/matt/Work/projects/sql-interview-practice
  backend/scripts/audit_findings_log.md          — THE Phase 1+2+3 RECORD incl. the 6
       Phase-3 remediations. Read fully. Phase 3 closed with 0 wrong MCQ keys (3 model
       families) and all 24 ungradeable code questions fixed.
  backend/scripts/audit_blind_answer_openai.py   — the two-pass MCQ harness (provider
       flag, max_completion_tokens, no temperature, --pass2-all, phase12 xref). REUSE.
  backend/scripts/audit_code_tracks.py           — the execution-based code harness
       (deterministic expected-reproduction + gpt-5-mini blind-solve; _DUCKDB_LOCK
       serializes the non-threadsafe DuckDB engine). REUSE + extend for Statistics.
  docs/decisions/DECISIONS.md                     — the grade-full/preview model +
       MAX_JOINS 5→9 decisions (so you don't re-litigate them).
  CLAUDE.md, docs/content-authoring.md, .github/agents/question-authoring.agent.md
       — constraints + the authoring-agent contract (mandatory for any content edit).

## What changed since Phase 3 (re-verify these are clean — no regression)
  - MCQ: 93019 (exp hard) sharpened — key B now uniquely correct (was contested A-vs-B).
  - Python: 21031 / 21032 / 21033 / 22040 reframed to no-import algorithmic versions.
  - SQL: 13018 / 13021 / 13024 references CTE-cleaned; sql_guard MAX_JOINS raised 5→9.
  - Pandas: datetime + row-cap fixed at the PLATFORM layer (no content change);
       31018 / 32090 date columns now display YYYY-MM-DD.
  - Grading platform: SQL + pandas now grade on the FULL result and return a 200-row
       display preview; datetimes are ISO-serialized + date-normalized.
Confirm each of these specific IDs comes back clean in the relevant sweep.

## External model — OpenAI gpt-5-mini (Pass-1) + gpt-5 (Pass-2). PAID — KEY in backend/.env.
Use the openai SDK, DEFAULT base_url, OPENAI_API_KEY. GPT-5 reasoning-model gotchas
(verified live in Phase 3): use max_completion_tokens (NOT max_tokens), OMIT temperature,
give Pass-1 ~2000 / Pass-2 ~4000 budget (small budgets return content='' /
finish_reason='length'). The harnesses already handle this. Re-probe both models with a
1-token call before any run; report a token-cost estimate BEFORE the full run. If the
user's API balance is under ~$15, warn them (pass2-all ≈ $10.6) or fall back to the gated
default before running.

## Methodology
A) MCQ tracks (6) — pyspark, data-engineering, data-modeling, statistics(conceptual),
   ml-fundamentals, experimentation. Two-pass, PASS2-ALL:
     audit_blind_answer_openai.py --pass2-all --workers 8 --output scripts/audit_final_mcq.json
   (loads practice + mock from the files; statistics-numerical auto-skipped by the
   harness's subtype filter). Resumable per cell. Verdicts: consistent / inverted_key
   (mechanical) / broken_mechanism (authoring) / inconsistent (review). Because Pass-2
   runs on every question, the survivor class (key right, explanation argues to a
   distractor → broken_mechanism) is FULLY checked, not sampled.

B) Code tracks (3) — SQL, Python, Pandas. Execution oracle, practice + mock:
     audit_code_tracks.py --track sql    --scope all
     audit_code_tracks.py --track python --scope all
     audit_code_tracks.py --track pandas --scope all
   The DETERMINISTIC expected-reproduction layer is the high-precision signal (free).
   The gpt-5-mini blind-solve layer is LOW-PRECISION (Phase-3 lesson: defensible-variance
   + solver noise → many false mismatches); treat its flags as advisory and adjudicate a
   sample, do NOT mass-flag. Expected baseline (already known-clean): SQL 283 ok / Python
   182 ok / Pandas 206 ok, 0 deterministic defects.

C) Statistics-numerical (71) — NOT covered by either harness today. EXTEND
   audit_code_tracks.py: add a "statistics" track that loads
   content/statistics_questions/{easy,medium,hard}.json filtered to subtype=='numerical'
   and treats them as kind="python" (they carry expected_code + test_cases +
   public_test_cases and grade via python_evaluator.evaluate_python_code — identical to
   the Python track). Smoke-test 2, then run --track statistics --scope all. The
   deterministic expected-reproduction check (run expected_code vs its test_cases) is the
   key signal; blind-solve optional.

## Verify EVERYTHING (the hardest-won lesson)
A model verdict is a SIGNAL, not a fix. For every flag, read the source and adjudicate.
inverted_key/"mechanical" verdicts are NOT auto-applies (Phase 1: they were content
defects). NEVER change correct_option without confirming the explanation + ground truth.
The MCQ bank is letter-convention, free of numeric refs + label-collisions (validator
ERRORs on all three) — external disagreements driven by phrasing → scrutinise, don't fix.

## Fix path (same governance as Phases 1–3)
  1. correct_option genuinely wrong (verified): mechanical JSON fix, apply directly (the
     ONLY field editable without the authoring agent). validate + commit.
  2. Content wrong (explanation/option/stem/prompt): MUST go through the authoring agent
     (.github/agents/question-authoring.agent.md). Any Sonnet handoff that authors content
     MUST open with the exact model-gate text from CLAUDE.md.
  3. After any fix batch: cd backend && ../.venv/bin/python scripts/validate_content.py
     must end "Content validation passed". Code-track fixes also re-run the relevant
     evaluator. Then commit on main with the Opus co-author line.
  Per the user's audit-workflow preference: verify findings, give a full summary with
  root-cause + doc-gap analysis, then STOP for approval before fixing.

## Work order
  1. Confirm Opus. Read the context (esp. audit_findings_log.md — all of Phases 1–3).
  2. Confirm OPENAI_API_KEY; probe gpt-5-mini + gpt-5 (1-token, max_completion_tokens, no
     temperature); report a token-cost estimate for: MCQ pass2-all (~1,235 P1 + ~1,235 P2)
     + code blind-solve + stats-numerical. If anything looks unexpectedly expensive, pause.
  3. Run A (MCQ pass2-all, 6 tracks). Review every non-consistent flag vs source.
  4. Run B (SQL/Python/Pandas, scope all). Trust the deterministic layer; sample-adjudicate
     blind-solve flags. Confirm the changed IDs (13018/13021/13024, 21031/21032/21033/22040,
     31018/32090) are clean.
  5. Extend the harness for C (statistics-numerical) and run it.
  6. Apply only VERIFIED mechanical fixes; route content defects to the authoring agent;
     validate_content.py + evaluators; commit per batch. STOP for approval before fixes.
  7. Append a "Phase 4 — final confirmation" section to backend/scripts/audit_findings_log.md:
     models, pass2-all cost, per-cell MCQ results, code + stats-numerical results, explicit
     confirmation that this-session's changed IDs are clean, cross-reference Phases 1–3, any
     new findings. Do NOT delete the log.

## Out of scope
  Any feature work or new content. This is a confirmation pass: re-audit, adjudicate, and
  report whether the bank is launch-clean. Stop for user approval before applying any fix.

═══════════════════════════════════════════════════════════════
START: confirm Opus → read context → confirm OPENAI_API_KEY → probe gpt-5 models →
run MCQ pass2-all + code execution-audit + statistics-numerical → adjudicate → report.
═══════════════════════════════════════════════════════════════
```
