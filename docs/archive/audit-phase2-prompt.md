# Phase 2 — External-model (Nvidia NIM) blind-answer audit — orchestrator prompt

Paste the block below into a **fresh Opus session** to run Phase 2. The NVIDIA key
is already in `backend/.env` (`NVIDIA_API_KEY`) and both models below were probed
live (HTTP 200) on 2026-06-04. This file is temporary — delete it (with the
findings log) when the multi-phase audit closes.

---

```
★ MODEL CHECK: This session requires Opus as orchestrator. If you are not Opus,
stop immediately and ask the user to switch before proceeding.

═══════════════════════════════════════════════════════════════
BLIND-ANSWER AUDIT — PHASE 2 (External model: Nvidia NIM)
═══════════════════════════════════════════════════════════════

## What this is
Phase 2 of a multi-phase MCQ correctness audit of the datathink question bank.
Phase 1 (complete) used Anthropic models to blind-answer every MCQ question and
fixed the bugs it found. Phase 2 repeats a COMPLETE, independent blind test using
an EXTERNAL model family (Nvidia NIM) — a signal orthogonal to Claude's own
answers. Premise: a question where an independent external model ALSO disagrees
with the key is a high-confidence defect. Phase 3 (later, separate session) repeats
this with a paid external model.

You (Opus) plan and orchestrate; offload execution (writing the harness, running
batches, classifying, fixing) to Sonnet subagents via the Agent tool when useful.

## Read before doing anything (binding context)
Root: /Users/matt/Work/projects/sql-interview-practice
  CLAUDE.md                                   — constraints, standing instructions
  docs/content-authoring.md                   — authoring contract + § Reject on sight
  .github/agents/question-authoring.agent.md  — authoring agent process (mandatory for content edits)
  backend/scripts/audit_findings_log.md       — THE PHASE 1 RECORD. Read fully. Per-batch verified
                                                findings; the 28 fixed correct_option bugs; the
                                                systemic +1 statistics shift (fixed); the A/B/C/D
                                                explanation normalization; and the OPEN Phase-2
                                                tiebreaker set.
  backend/scripts/audit_blind_answer.py       — the Phase 1 Anthropic harness. STUDY IT — your NIM
                                                harness mirrors its structure (two-pass, verdicts,
                                                report schema, robust answer extraction, retry/backoff).

Phase 1 already FIXED its findings, so a fresh blind run should come back MOSTLY
CONSISTENT. Phase 2's value is therefore: (a) independently regression-confirm the
fixes (esp. the 27 statistics keys and the 93045 re-key to D), and (b) catch
anything Phase 1 + human verification MISSED — the external model surfaces its own
disagreements; some may be genuine defects Claude never flagged.

## External model — Nvidia NIM (KEY ALREADY IN .env)
OpenAI-compatible API. Use the `openai` Python SDK pointed at NIM:
    base_url = "https://integrate.api.nvidia.com/v1"
    api_key  = os.environ["NVIDIA_API_KEY"]   # already in backend/.env (nvapi-...), verified live
  → `openai` SDK may not be in .venv — install it if needed.

FREE TIER = UNLIMITED CALLS, RATE-LIMITED (no credit cap; the older "1,000 credits"
model is retired for the hosted catalog). So the full sweep is fine on cost; the
ONLY constraint is the rate limit → use LOW concurrency (1–2 workers) + generous
exponential backoff + per-(track,difficulty) resumable batching. Do not hammer it.
Because calls are unlimited, run Pass 2 on EVERY question (`--pass2-all`, the
DEFAULT for Phase 2), not just on disagreements — it is slower (the Pass-2 model
runs on all ~1,400 MCQs) but free, and it is the only way to catch the "survivor
class" (key right, candidate agrees, but the explanation argues toward a distractor;
Phase 1 found ml-fundamentals 83081 exactly this way). Run resumable so a
rate-limit stall mid-track can pick up where it left off.

MODELS (probed live HTTP 200 on 2026-06-04 — but the catalog renames/retires models,
so re-probe with a 1-token call before any run; if a model 404s or 504s, GET
/v1/models and pick the nearest strong equivalent, then report your final choice):
  - Pass 1 (blind answer):  meta/llama-3.3-70b-instruct        # confirmed, fast, clean A-D output
  - Pass 2 (explanation consistency / math): deepseek-ai/deepseek-v4-flash   # confirmed, independent
                                              # lineage from Claude, strong math, returns finish=stop
    Pass-2 alternates (also confirmed): nvidia/nemotron-3-super-120b-a12b, nvidia/llama-3.3-nemotron-super-49b-v1.5
  NOTE: deepseek-r1 and qwen2.5-72b are GONE from this catalog (404). The big
  reasoners deepseek-v4-pro (504 timeout) and llama-3.1-nemotron-ultra-253b (404)
  were unreliable — prefer the lighter confirmed models above. Some NIM reasoning
  models populate `message.reasoning_content` separately and/or wrap thinking in
  <think>…</think> — give Pass-2 enough max_tokens (~3000) and extract the final
  letter from the actual answer, not the reasoning trace. Make models CLI-overridable.

## Methodology (mirror Phase 1, two-pass)
PASS 1 — BLIND. Send ONLY stem (+ scenario_context if present) + the 4 options. No
correct_option, no explanation. Parse a letter A–D robustly (models chain-reason on
numerical/predict_output before answering — give ~800 max_tokens for Pass 1 and
extract from "ANSWER: X", "the answer is X", "Option X", or a trailing letter;
truncation→UNPARSED was a real Phase 1 false-positive source). Compare to
correct_option (0-indexed: 0=A,1=B,2=C,3=D). Disagreement = review candidate.
PASS 2 — EXPLANATION CONSISTENCY (run on ALL questions via `--pass2-all` — the
Phase-2 default, since NIM calls are unlimited). Send stem + options + explanation;
ask which option the explanation's reasoning actually leads to. On Pass-1
DISAGREEMENTS it disambiguates inverted_key vs review; on Pass-1 AGREEMENTS it
catches the survivor class — key is right and the candidate agrees, but the
explanation quietly leads to a distractor → verdict broken_mechanism (authoring).
VERDICTS (same as Phase 1): consistent / inverted_key (mechanical) / broken_mechanism
(authoring) / inconsistent (review). Emit a JSON report per the Phase 1 schema, plus
a "phase1_cross_reference" field per flag (was it flagged/fixed in Phase 1? consult
audit_findings_log.md + git log).

## MCQ tracks in scope (have correct_option)
  pyspark            backend/content/pyspark_questions/
  data-engineering   backend/content/data_engineering_questions/
  data-modeling      backend/content/data_modeling_questions/
  statistics         backend/content/statistics_questions/   (subtype=="conceptual" ONLY)
  ml-fundamentals    backend/content/ml_fundamentals_questions/
  experimentation    backend/content/experimentation_questions/
Each: easy/medium/hard.json. MCQ filter = int correct_option AND options list ≥2
(excludes statistics numerical). 18 cells (6 tracks × 3). SQL/Python/Pandas are NOT
MCQ — out of scope.

## Verify EVERYTHING (Phase 1's hardest-won lesson)
The LLM verdict is only a SIGNAL. For every flag, read the source JSON and adjudicate
before acting.
  - inverted_key / "mechanical" verdicts are NOT reliable auto-applies. In Phase 1,
    2/2 inverted_key verdicts were actually CONTENT defects, and one would have flipped
    a CORRECT key to the worst distractor. NEVER change correct_option without confirming
    the explanation + ground truth support it.
  - The bank is now 100% letter-convention (no numeric "Option N") and free of the two
    documented anti-patterns (option-label collision; numeric refs) — validator errors on
    them. If the external model produces disagreements driven by phrasing, scrutinise.
  - Statistics conceptual answers cluster at one position by authoring style — skew alone
    is not a bug.

## Fix path (same governance as Phase 1)
  1. correct_option genuinely wrong (verified): mechanical JSON fix, apply directly (the
     ONLY field editable without the authoring agent). validate + commit.
  2. Content wrong (explanation/option/stem): MUST go through the authoring agent. Do NOT
     self-edit explanation/option/hint text. Any Sonnet handoff that authors/remaps content
     MUST open with the exact model-gate text from CLAUDE.md.
  3. After any fix batch: `cd backend && ../.venv/bin/python scripts/validate_content.py`
     must end "Content validation passed" (it now ERRORS on numeric option refs and on
     explanations refuting their keyed option). Then commit.
  - Work on main. Commit per batch with a clear message + the Opus co-author line.
  - Per the user's audit-workflow preference: verify findings, give a full summary with
    root-cause + doc-gap analysis, then STOP for approval before fixing.

## Work order
  1. Confirm Opus. Read the 5 context files (esp. audit_findings_log.md).
  2. Confirm NVIDIA_API_KEY in backend/.env; probe Pass-1 + Pass-2 model IDs (1-token each);
     report the final models.
  3. Spawn a Sonnet agent to write backend/scripts/audit_blind_answer_nim.py — same CLI +
     report schema as audit_blind_answer.py (including a `--pass2-all` flag), OpenAI SDK
     against NIM, low concurrency, strong backoff, robust answer extraction (handle
     reasoning_content/<think>), phase1 cross-ref, and RESUMABLE per-cell output so a
     rate-limit stall can restart without re-spending the whole batch. Review the script;
     smoke-test on 2 questions before any full run.
  4. Run with `--pass2-all` (the Phase-2 default): ml-fundamentals hard first, then
     experimentation hard/medium, then the rest of the 18 cells. Review each batch's flags
     against source before proceeding. Give special attention to the OPEN Phase-2 tiebreaker
     set (82002, 93066, 42098, 42115, 93018, 93019, 93059): if NIM independently disagrees
     with those defensible keys too, escalate them from "defensible" to "genuine ambiguity →
     fix." Also scan every Pass-1 AGREEMENT whose Pass-2 verdict is broken_mechanism — those
     are survivor-class candidates Claude's Phase 1 may have passed over.
  5. Apply verified mechanical fixes; route content defects to the authoring agent.
     validate_content.py + commit per batch.
  6. Append a Phase-2 section to backend/scripts/audit_findings_log.md: NIM models used,
     per-cell results, cross-reference with Phase 1, new findings, Phase-3 candidate list.
     Do NOT delete the log.

## Out of scope
  Phase 3 (paid external model) is a separate later session. Do not build it now.

═══════════════════════════════════════════════════════════════
START: confirm Opus → read context → confirm NVIDIA_API_KEY → probe NIM models → build harness.
═══════════════════════════════════════════════════════════════
```
