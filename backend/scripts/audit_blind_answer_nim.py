"""
audit_blind_answer_nim.py — Two-pass automated MCQ audit using the Nvidia NIM API.

Pass 1: Blind-answer each question (no key, no explanation) via a fast model to
        detect disagreements with the keyed answer.
Pass 2: For flagged questions (and all questions by default in Phase 2), check
        whether the explanation's reasoning actually leads to the keyed option.

This script is a near-clone of audit_blind_answer.py (Anthropic API version) but:
  - Talks to the Nvidia NIM OpenAI-compatible API.
  - Is resumable per-cell via a checkpoint sidecar (.partial.jsonl).
  - Defaults --pass2-all to ON (Phase 2 behavior).
  - Uses NIM-appropriate models and retry logic.

Usage examples
--------------
# Smoke test — 2 questions from ml-fundamentals hard, pass2-all is default ON
python backend/scripts/audit_blind_answer_nim.py \\
    --track ml-fundamentals --difficulty hard --limit 2 \\
    --output backend/scripts/_smoke_nim.json

# Full audit of all MCQ tracks
python backend/scripts/audit_blind_answer_nim.py

# Audit a single track + difficulty
python backend/scripts/audit_blind_answer_nim.py --track experimentation --difficulty hard

# Re-run only Pass 2 on a prior report's flagged questions
python backend/scripts/audit_blind_answer_nim.py \\
    --pass2-only --input backend/scripts/prior_report.json

# Audit first 10 questions across all tracks (cheap smoke)
python backend/scripts/audit_blind_answer_nim.py --limit 10

# Disable pass2-all (only run Pass 2 on Pass-1 disagreements)
python backend/scripts/audit_blind_answer_nim.py --no-pass2-all

Notes
-----
- Run from repo root or any directory; paths are resolved relative to this script.
- NVIDIA_API_KEY is loaded from backend/.env (or os.environ as fallback).
- Output is a JSON report with per-question verdicts and a meta summary.
- A checkpoint sidecar (<output>.partial.jsonl) is maintained for resumability.
  Re-running the same command resumes from the sidecar — no duplicate API calls.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — resolve relative to this script file, not CWD
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = SCRIPT_DIR.parent                        # backend/
REPO_ROOT = BACKEND_DIR.parent                         # repo root

# Load .env before importing openai (dotenv may not be strictly needed but
# we honour it to match the project's convention)
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env", override=True)
except ImportError:
    # python-dotenv not available — fall through to os.environ
    pass

import openai  # noqa: E402 — must come after .env is loaded

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRACKS: dict[str, str] = {
    "pyspark":           "content/pyspark_questions",
    "data-engineering":  "content/data_engineering_questions",
    "data-modeling":     "content/data_modeling_questions",
    "statistics":        "content/statistics_questions",
    "ml-fundamentals":   "content/ml_fundamentals_questions",
    "experimentation":   "content/experimentation_questions",
}
DIFFICULTY_ORDER = ["easy", "medium", "hard"]
TRACK_ORDER = list(TRACKS.keys())

DEFAULT_PASS1_MODEL = "meta/llama-3.3-70b-instruct"
# Pass 2 default is gpt-oss-20b: an OpenAI-lineage reasoning model (independent of
# both Claude and the Llama Pass-1 model), ~1.5-2.5s/call warm, and it reliably
# emits the full LEADS_TO|MATCHES_KEY|WHY format. Its bigger sibling
# openai/gpt-oss-120b is stronger but ~4-9s/call (too slow for a 1,235-Q pass2-all
# sweep); use it via --pass2-model as a deeper tiebreaker on individual flags.
DEFAULT_PASS2_MODEL = "openai/gpt-oss-20b"

PASS1_SYSTEM = (
    "You are an expert data professional answering a multiple-choice question. "
    "Select the single best answer. You may work through the problem briefly if the "
    "question requires calculation, but your reply MUST contain a line in exactly this "
    "format (this line is mandatory and must use one of A, B, C, or D): "
    "ANSWER: [letter] | REASONING: [one sentence]"
)

PASS2_SYSTEM = "You are reviewing a multiple-choice question and its explanation."

VERDICT_CONSISTENT = "consistent"
VERDICT_INVERTED = "inverted_key"
VERDICT_BROKEN = "broken_mechanism"
VERDICT_INCONSISTENT = "inconsistent"

FIX_NONE = "none"
FIX_MECHANICAL = "mechanical"
FIX_AUTHORING = "authoring_agent"
FIX_REVIEW = "review"

MAX_RETRIES = 6
BACKOFF_BASE = 5  # seconds (base for NIM backoff)


# ---------------------------------------------------------------------------
# Phase 1 cross-reference findings
# ---------------------------------------------------------------------------
PHASE1_FINDINGS: dict[int, str] = {
    # --- FIXED mechanical key bugs ---
    43112: "FIXED P1: correct_option 1->2 (key C), commit 2474cfc",
    # stats medium +1 key-shift, all FIXED commit a85fdca:
    72001: "FIXED P1: stats +1 key-shift (a85fdca)", 72004: "FIXED P1: stats +1 key-shift (a85fdca)",
    72006: "FIXED P1: stats +1 key-shift (a85fdca)", 72007: "FIXED P1: stats +1 key-shift (a85fdca)",
    72008: "FIXED P1: stats +1 key-shift (a85fdca)", 72010: "FIXED P1: stats +1 key-shift (a85fdca)",
    72012: "FIXED P1: stats +1 key-shift (a85fdca)", 72013: "FIXED P1: stats +1 key-shift (a85fdca)",
    72015: "FIXED P1: stats +1 key-shift (a85fdca)", 72019: "FIXED P1: stats +1 key-shift (a85fdca)",
    72020: "FIXED P1: stats +1 key-shift (a85fdca)", 72023: "FIXED P1: stats +1 key-shift (a85fdca)",
    72024: "FIXED P1: stats +1 key-shift (a85fdca)", 72027: "FIXED P1: stats +1 key-shift (a85fdca)",
    72029: "FIXED P1: stats +1 key-shift (a85fdca)", 72030: "FIXED P1: stats +1 key-shift (a85fdca)",
    72031: "FIXED P1: stats +1 key-shift (a85fdca)", 72032: "FIXED P1: stats +1 key-shift (a85fdca)",
    72033: "FIXED P1: stats +1 key-shift (a85fdca)", 72034: "FIXED P1: stats +1 key-shift (a85fdca)",
    72035: "FIXED P1: stats +1 key-shift (a85fdca)", 72036: "FIXED P1: stats +1 key-shift (a85fdca)",
    72037: "FIXED P1: stats +1 key-shift (a85fdca)", 72038: "FIXED P1: stats +1 key-shift (a85fdca)",
    72039: "FIXED P1: stats +1 key-shift (a85fdca)", 72040: "FIXED P1: stats +1 key-shift (a85fdca)",
    72041: "FIXED P1: stats +1 key-shift (a85fdca)",
    # --- Content defects flagged P1 (routed to authoring; some edited 24f2a0e/df70c19/206ce65) ---
    42088: "P1 CONTENT: Delta exactly-once explanation contradicts key B (authoring)",
    43066: "P1 CONTENT: predict_output 3 identical outputs (authoring)",
    93045: "P1 CONTENT: multiple-correct B/C/D; option labels edited 206ce65",
    83011: "P1 CONTENT: label-collision approach-letter vs option-position (authoring)",
    83081: "P1 CONTENT(low): explanation over-concedes SHAP, reads as endorsing D; key A",
    93024: "P1 CONTENT: stem 'unrelated' stipulation undercuts key D",
    93026: "P1 CONTENT: ranking non-unique key D",
    43081: "P1 CONTENT: label-collision + synthesis key D",
    # --- Phase-2 TIEBREAKER set (defensible keys; escalate if NIM also disagrees) ---
    82002: "P1 TIEBREAKER: stem A-vs-C tension; key A defensible",
    93066: "P1 TIEBREAKER: index leak + A/B framing tension; key A",
    42098: "P1 TIEBREAKER: index leak + awkward stem; key A defensible",
    42115: "P1 TIEBREAKER: index leak + CSE-vs-pushdown debatable",
    93018: "P1 TIEBREAKER: Bayesian PBE vs threshold; key D",
    93019: "P1 TIEBREAKER: 'most fundamental'; key B (interaction test)",
    93059: "P1 TIEBREAKER: DiD/ITS both-valid key D",
    # --- Exp medium fixes ---
    92009: "FIXED P1: mechanism fix (448f7ee)", 92078: "FIXED P1: arithmetic fix (448f7ee)",
    92002: "FIXED P1: polish (448f7ee)", 92068: "FIXED P1: polish (448f7ee)",
    # --- Verified-clean / acceptable-hard / false-positive (no action P1) ---
    83075: "P1 FALSE-POSITIVE: harness truncation; key A correct",
    93022: "P1 acceptable-hard, no action", 93028: "P1 acceptable-hard, no action",
    92060: "P1 acceptable-hard, no action", 91019: "P1 verified clean (key A)",
}


# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------
def get_api_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        print(
            "ERROR: NVIDIA_API_KEY not found. "
            "Set it in backend/.env or as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


# ---------------------------------------------------------------------------
# Letter helpers
# ---------------------------------------------------------------------------
def idx_to_letter(i: int) -> str:
    return chr(ord("A") + i)


def letter_to_idx(letter: str) -> int:
    return ord(letter.upper()) - ord("A")


def extract_answer_letter(raw: str) -> str:
    """Robustly pull an A-D answer letter from a Pass-1 reply.

    Tolerates models that ignore the requested format or run a long chain of
    thought before stating the answer (which previously truncated to UNPARSED).
    Tries, in order: explicit ANSWER: line, 'the answer is X', a choose/select
    verb, the LAST 'Option X' mention (the conclusion), then a leading letter.
    """
    # 1. Explicit ANSWER: X (the requested format)
    m = re.search(r"ANSWER\s*:\s*\(?([A-Da-d])\)?", raw, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # 2. "the answer is X" / "answer: X"
    m = re.search(r"answer\s+is\s*:?\s*\(?([A-Da-d])\)?\b", raw, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # 3. choose/select/pick (option) X
    m = re.search(
        r"\b(?:choose|select|pick|chose|selected|going with)\s+(?:option\s+)?\(?([A-Da-d])\)?\b",
        raw,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()
    # 4. LAST 'Option X' mention — the conclusion usually comes last
    matches = re.findall(r"\bOption\s+\(?([A-Da-d])\)?\b", raw, re.IGNORECASE)
    if matches:
        return matches[-1].upper()
    # 5. Leading bare letter
    m = re.match(r"^\s*\(?([A-Da-d])\)?[\).:\s]", raw)
    if m:
        return m.group(1).upper()
    return "UNPARSED"


# ---------------------------------------------------------------------------
# Reasoning-model message text extraction
# ---------------------------------------------------------------------------
def message_text(msg: Any) -> str:
    """Return the answer-bearing text from a chat message, tolerant of reasoning models.

    NIM reasoning models may (a) put the final answer in message.content while
    putting chain-of-thought in message.reasoning_content, and/or (b) wrap
    thinking in <think>...</think> inside content. We prefer the text AFTER
    the last </think> if present, then fall back to reasoning_content.
    """
    content = (getattr(msg, "content", None) or "")
    # If content wraps thinking in <think>..</think>, prefer the text AFTER the last </think>
    if "</think>" in content:
        tail = content.rsplit("</think>", 1)[-1].strip()
        if tail:
            content = tail
    if content.strip():
        return content
    # Fallback: some models emit only reasoning_content
    rc = getattr(msg, "reasoning_content", None) or ""
    return rc


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------
def load_questions(
    tracks: list[str],
    difficulties: list[str],
) -> list[dict[str, Any]]:
    """Load all MCQ-eligible questions for the given tracks and difficulties."""
    questions: list[dict[str, Any]] = []
    for track in tracks:
        rel_dir = TRACKS[track]
        track_dir = BACKEND_DIR / rel_dir
        for diff in difficulties:
            file_path = track_dir / f"{diff}.json"
            if not file_path.exists():
                print(
                    f"WARNING: {file_path} not found — skipping.",
                    file=sys.stderr,
                )
                continue
            with open(file_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for q in data:
                # MCQ filter: must have integer correct_option AND options list >= 2
                if not isinstance(q.get("correct_option"), int):
                    continue
                opts = q.get("options")
                if not isinstance(opts, list) or len(opts) < 2:
                    continue
                # Statistics track: skip numerical subtype (conceptual-only in scope)
                if track == "statistics" and q.get("subtype") == "numerical":
                    continue
                # Enrich with track/difficulty metadata
                q["_track"] = track
                q["_difficulty"] = diff
                questions.append(q)
    return questions


def sort_key(q: dict[str, Any]) -> tuple[int, int, int]:
    track_idx = TRACK_ORDER.index(q["_track"])
    diff_idx = DIFFICULTY_ORDER.index(q["_difficulty"])
    return (track_idx, diff_idx, q.get("id", 0))


# ---------------------------------------------------------------------------
# Stem builder
# ---------------------------------------------------------------------------
def build_stem(q: dict[str, Any]) -> str:
    parts: list[str] = []
    title = q.get("title", "").strip()
    if title:
        parts.append(title)
        parts.append("")

    desc = q.get("description", "").strip()
    if desc:
        parts.append(desc)
        parts.append("")

    sc = q.get("scenario_context", "")
    if isinstance(sc, str) and sc.strip():
        parts.append(sc.strip())
        parts.append("")

    options = q.get("options", [])
    parts.append("Options:")
    for i, opt in enumerate(options):
        parts.append(f"{idx_to_letter(i)}) {opt}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Retry wrapper (OpenAI SDK + NIM)
# ---------------------------------------------------------------------------
def call_with_retry(
    client: openai.OpenAI,
    *,
    model: str,
    system: str,
    user_content: str,
    max_tokens: int,
) -> str:
    """Call the NIM API with exponential backoff. Returns message text or raises."""
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=0,
            )
            return message_text(resp.choices[0].message)
        except openai.RateLimitError as exc:
            last_exc = exc
        except openai.APITimeoutError as exc:
            last_exc = exc
        except openai.APIConnectionError as exc:
            last_exc = exc
        except openai.InternalServerError as exc:
            last_exc = exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                last_exc = exc
            else:
                raise

        # Fixed backoff with deterministic jitter (no random)
        wait = min(60, BACKOFF_BASE * (2 ** attempt)) + (attempt * 0.7)
        print(
            f"  [retry] attempt {attempt + 1}/{MAX_RETRIES} failed "
            f"({type(last_exc).__name__}), waiting {wait:.1f}s …",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed") from last_exc


# ---------------------------------------------------------------------------
# Pass 1
# ---------------------------------------------------------------------------
def run_pass1(
    q: dict[str, Any],
    client: openai.OpenAI,
    model: str,
) -> dict[str, Any]:
    """Run Pass 1 on a single question. Returns partial result dict."""
    stem = build_stem(q)
    keyed = idx_to_letter(q["correct_option"])

    try:
        raw = call_with_retry(
            client,
            model=model,
            system=PASS1_SYSTEM,
            user_content=stem,
            max_tokens=800,
        )
    except Exception as exc:
        return {
            "pass1_answer": "ERROR",
            "pass1_reasoning": str(exc),
            "pass1_agrees": False,
        }

    # Parse the answer letter (robust to CoT / format drift)
    pass1_answer = extract_answer_letter(raw)

    # Parse REASONING:
    m_reasoning = re.search(r"REASONING\s*:\s*(.*)", raw, re.IGNORECASE | re.DOTALL)
    pass1_reasoning = m_reasoning.group(1).strip() if m_reasoning else raw.strip()

    return {
        "pass1_answer": pass1_answer,
        "pass1_reasoning": pass1_reasoning,
        "pass1_agrees": pass1_answer == keyed,
    }


# ---------------------------------------------------------------------------
# Pass 2
# ---------------------------------------------------------------------------
def build_pass2_prompt(q: dict[str, Any]) -> str:
    stem = build_stem(q)
    keyed = idx_to_letter(q["correct_option"])
    explanation = q.get("explanation", "").strip()
    return (
        f"{stem}\n\n"
        f"Explanation:\n{explanation}\n\n"
        f"The intended correct answer is Option {keyed}. "
        f"If you followed ONLY the reasoning in this explanation step by step — "
        f"ignoring any prior knowledge of the right answer — which single option "
        f"does the explanation's reasoning actually lead to? "
        f"Then state whether that matches the intended Option {keyed}.\n\n"
        f"IMPORTANT: identify the option strictly by its A/B/C/D position in the Options "
        f"list above. The option text or explanation may reference a DIFFERENT lettering "
        f"scheme (e.g. a scenario that labels its approaches 'A/B/C/D' in a different order "
        f"than the options are listed). Map the explanation's conclusion to the OPTION "
        f"LETTER whose text matches it — not to any label embedded inside the text.\n\n"
        f"Respond in EXACTLY this format:\n"
        f"LEADS_TO: [letter] | MATCHES_KEY: [yes/no] | WHY: [one or two sentences explaining the discrepancy if any]"
    )


def run_pass2(
    q: dict[str, Any],
    client: openai.OpenAI,
    model: str,
) -> dict[str, Any]:
    """Run Pass 2 on a single question. Returns partial result dict."""
    prompt = build_pass2_prompt(q)

    try:
        raw = call_with_retry(
            client,
            model=model,
            system=PASS2_SYSTEM,
            user_content=prompt,
            max_tokens=3000,
        )
    except Exception as exc:
        return {
            "pass2_ran": True,
            "pass2_explanation_leads_to": "ERROR",
            "pass2_consistent": False,
            "pass2_reasoning": str(exc),
        }

    # Parse LEADS_TO
    m_leads = re.search(r"LEADS_TO\s*:\s*([A-Da-d])", raw, re.IGNORECASE)
    leads = m_leads.group(1).upper() if m_leads else "UNPARSED"

    # Parse MATCHES_KEY
    m_matches = re.search(r"MATCHES_KEY\s*:\s*(yes|no)", raw, re.IGNORECASE)
    if m_matches:
        pass2_consistent = m_matches.group(1).lower() == "yes"
    else:
        keyed = idx_to_letter(q["correct_option"])
        pass2_consistent = (leads == keyed) if leads not in ("UNPARSED", "ERROR") else False

    # Parse WHY
    m_why = re.search(r"WHY\s*:\s*(.*)", raw, re.IGNORECASE | re.DOTALL)
    pass2_reasoning = m_why.group(1).strip() if m_why else raw.strip()

    return {
        "pass2_ran": True,
        "pass2_explanation_leads_to": leads,
        "pass2_consistent": pass2_consistent,
        "pass2_reasoning": pass2_reasoning,
    }


# ---------------------------------------------------------------------------
# Verdict classifier
# ---------------------------------------------------------------------------
def classify(
    q: dict[str, Any],
    pass1: dict[str, Any],
    pass2: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Return verdict, fix_category, suggested_correct_option given Pass 1 + Pass 2 outputs.
    """
    keyed = idx_to_letter(q["correct_option"])
    p1_agrees: bool = pass1["pass1_agrees"]
    p1_answer: str = pass1["pass1_answer"]

    if pass2 is None:
        # Pass 2 did not run
        return {
            "pass2_ran": False,
            "pass2_explanation_leads_to": None,
            "pass2_consistent": None,
            "pass2_reasoning": None,
            "verdict": VERDICT_CONSISTENT,
            "fix_category": FIX_NONE,
            "suggested_correct_option": None,
        }

    leads: str | None = pass2.get("pass2_explanation_leads_to")

    if p1_agrees:
        # Pass 2 ran on a Pass-1 agreement (--pass2-all mode)
        if leads in (keyed, "UNPARSED", "ERROR", None):
            verdict, fix_cat = VERDICT_CONSISTENT, FIX_NONE
        else:
            verdict, fix_cat = VERDICT_BROKEN, FIX_AUTHORING
        suggested = None
    else:
        # Pass 2 ran on a Pass-1 disagreement
        if leads in ("UNPARSED", "ERROR", None):
            verdict, fix_cat = VERDICT_INCONSISTENT, FIX_REVIEW
            suggested = None
        elif leads == keyed:
            verdict, fix_cat = VERDICT_INCONSISTENT, FIX_REVIEW
            suggested = None
        elif leads == p1_answer:
            verdict, fix_cat = VERDICT_INVERTED, FIX_MECHANICAL
            suggested = letter_to_idx(leads)
        else:
            verdict, fix_cat = VERDICT_BROKEN, FIX_AUTHORING
            suggested = None

    return {
        **pass2,
        "verdict": verdict,
        "fix_category": fix_cat,
        "suggested_correct_option": suggested if verdict == VERDICT_INVERTED else None,
    }


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------
def build_result(
    q: dict[str, Any],
    pass1: dict[str, Any],
    classified: dict[str, Any],
) -> dict[str, Any]:
    keyed = idx_to_letter(q["correct_option"])
    q_id = q.get("id")
    return {
        "id": q_id,
        "track": q["_track"],
        "difficulty": q["_difficulty"],
        "type": q.get("type"),
        "mock_only": bool(q.get("mock_only", False)),
        "title": q.get("title", ""),
        "correct_option": q["correct_option"],
        "keyed_letter": keyed,
        "pass1_answer": pass1["pass1_answer"],
        "pass1_reasoning": pass1["pass1_reasoning"],
        "pass1_agrees": pass1["pass1_agrees"],
        "pass2_ran": classified["pass2_ran"],
        "pass2_explanation_leads_to": classified["pass2_explanation_leads_to"],
        "pass2_consistent": classified["pass2_consistent"],
        "pass2_reasoning": classified["pass2_reasoning"],
        "verdict": classified["verdict"],
        "fix_category": classified["fix_category"],
        "suggested_correct_option": classified["suggested_correct_option"],
        "phase1_cross_reference": PHASE1_FINDINGS.get(q_id) if q_id is not None else None,
    }


# ---------------------------------------------------------------------------
# Per-question unit of work (Pass 1 + Pass 2 combined, for resumable executor)
# ---------------------------------------------------------------------------
def is_clean(result: dict[str, Any]) -> bool:
    """A result is safe to checkpoint only if NO API error occurred in either pass.

    Errored questions (transient rate-limit / timeout / 5xx that exhausted the
    retry budget) are deliberately left OUT of the sidecar so a resume retries
    them rather than poisoning them as permanent ERROR verdicts. This is the
    exact Phase-1 failure mode (credit exhausted mid-stats-run -> errors baked
    into the report); we must not persist errors as "done".
    """
    if result.get("pass1_answer") == "ERROR":
        return False
    if result.get("pass2_ran") and result.get("pass2_explanation_leads_to") == "ERROR":
        return False
    return True


def process_question(
    q: dict[str, Any],
    client: openai.OpenAI,
    pass1_model: str,
    pass2_model: str,
    pass2_all: bool,
    pass1_override: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run the full pipeline (Pass 1 then optionally Pass 2) for one question."""
    if pass1_override is not None:
        pass1 = pass1_override
    else:
        pass1 = run_pass1(q, client, pass1_model)

    needs_p2 = (not pass1["pass1_agrees"]) or pass2_all
    if needs_p2:
        pass2 = run_pass2(q, client, pass2_model)
    else:
        pass2 = None

    classified = classify(q, pass1, pass2)
    return build_result(q, pass1, classified)


# ---------------------------------------------------------------------------
# Resumable orchestration
# ---------------------------------------------------------------------------
def run_audit(
    questions: list[dict[str, Any]],
    client: openai.OpenAI,
    pass1_model: str,
    pass2_model: str,
    pass2_all: bool,
    workers: int,
    output_path: Path,
    pass1_results: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Full two-pass audit with per-cell resumability via a .partial.jsonl sidecar.

    If pass1_results is provided (--pass2-only mode), Pass 1 is skipped for
    those questions and the stored results are used instead.
    """
    sidecar_path = Path(str(output_path) + ".partial.jsonl")
    sidecar_lock = threading.Lock()

    # ---- Load already-done results from sidecar (resume) ----
    done_results: dict[int, dict[str, Any]] = {}
    if sidecar_path.exists():
        with open(sidecar_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    qid = r.get("id")
                    if qid is not None:
                        done_results[qid] = r
                except json.JSONDecodeError:
                    pass  # skip malformed lines
        if done_results:
            print(
                f"[resume] {len(done_results)} already-done results loaded from {sidecar_path}",
                file=sys.stderr,
                flush=True,
            )

    # ---- Filter to not-yet-done questions ----
    remaining = [q for q in questions if q.get("id") not in done_results]
    total = len(questions)
    already_done = len(done_results)

    print(
        f"[audit] {already_done} already done, {len(remaining)} to process "
        f"(total {total}), workers={workers}",
        file=sys.stderr,
        flush=True,
    )

    if remaining:
        completed = 0

        def task(q: dict[str, Any]) -> dict[str, Any]:
            qid = q.get("id", 0)
            p1_override = None
            if pass1_results is not None and qid in pass1_results:
                p1_override = pass1_results[qid]
            result = process_question(
                q, client, pass1_model, pass2_model, pass2_all, p1_override
            )
            # Append to sidecar immediately (thread-safe) — but ONLY clean
            # results, so a transient-error question is retried on resume
            # instead of being skipped as permanently "done".
            if is_clean(result):
                with sidecar_lock:
                    with open(sidecar_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            return result

        new_results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(task, q): q for q in remaining}
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                    new_results.append(result)
                    done_results[result["id"]] = result
                except Exception as exc:
                    q = futures[fut]
                    print(
                        f"  [error] question id={q.get('id')} failed: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
                completed += 1
                if completed % 5 == 0 or completed == len(remaining):
                    print(
                        f"[audit] {already_done + completed}/{total} processed …",
                        file=sys.stderr,
                        flush=True,
                    )

    # ---- Merge all results (done + new) and sort deterministically ----
    all_results = list(done_results.values())
    all_results.sort(
        key=lambda r: (
            TRACK_ORDER.index(r["track"]) if r["track"] in TRACK_ORDER else 99,
            DIFFICULTY_ORDER.index(r["difficulty"]) if r["difficulty"] in DIFFICULTY_ORDER else 99,
            r["id"] if r["id"] is not None else 0,
        )
    )
    return all_results


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------
def write_report(
    results: list[dict[str, Any]],
    output_path: Path,
    tracks: list[str],
    difficulties: list[str],
    pass1_model: str,
    pass2_model: str,
    pass2_all: bool,
) -> None:
    now = datetime.now(timezone.utc)
    verdict_counts: dict[str, int] = {
        VERDICT_CONSISTENT: 0,
        VERDICT_INVERTED: 0,
        VERDICT_BROKEN: 0,
        VERDICT_INCONSISTENT: 0,
    }
    flagged_ids: list[int] = []
    external_ids: list[int] = []

    for r in results:
        v = r["verdict"]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        if v != VERDICT_CONSISTENT:
            flagged_ids.append(r["id"])
        if v in (VERDICT_INCONSISTENT, VERDICT_BROKEN, VERDICT_INVERTED):
            external_ids.append(r["id"])

    report = {
        "meta": {
            "generated_at_utc": now.isoformat(),
            "api": "nvidia-nim",
            "phase": "phase2-nim",
            "tracks": tracks,
            "difficulties": difficulties,
            "pass1_model": pass1_model,
            "pass2_model": pass2_model,
            "pass2_all": pass2_all,
            "total_audited": len(results),
            "counts_by_verdict": verdict_counts,
            "flagged_ids": sorted(flagged_ids),
            "external_llm_candidate_ids": sorted(external_ids),
        },
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"\nReport written to: {output_path}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
def print_summary(results: list[dict[str, Any]]) -> None:
    verdict_counts: dict[str, int] = {}
    flagged: list[dict[str, Any]] = []
    for r in results:
        v = r["verdict"]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        if v != VERDICT_CONSISTENT:
            flagged.append(r)

    print("\n" + "=" * 60, file=sys.stderr)
    print("AUDIT SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"{'Verdict':<22} {'Count':>6}", file=sys.stderr)
    print("-" * 30, file=sys.stderr)
    for verdict in [VERDICT_CONSISTENT, VERDICT_INVERTED, VERDICT_BROKEN, VERDICT_INCONSISTENT]:
        n = verdict_counts.get(verdict, 0)
        print(f"  {verdict:<20} {n:>6}", file=sys.stderr)
    print(f"  {'TOTAL':<20} {len(results):>6}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if flagged:
        print(f"\nFlagged questions ({len(flagged)}):", file=sys.stderr)
        print(f"  {'ID':<8} {'Track':<20} {'Diff':<8} {'Verdict':<18} {'Fix'}", file=sys.stderr)
        print("  " + "-" * 70, file=sys.stderr)
        for r in sorted(flagged, key=lambda x: (TRACK_ORDER.index(x["track"]) if x["track"] in TRACK_ORDER else 99, x["id"])):
            print(
                f"  {r['id']:<8} {r['track']:<20} {r['difficulty']:<8} "
                f"{r['verdict']:<18} {r['fix_category']}",
                file=sys.stderr,
            )
    else:
        print("\nNo flagged questions.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Two-pass MCQ audit using the Nvidia NIM API (OpenAI-compatible).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--track",
        choices=list(TRACKS.keys()),
        default=None,
        help="Audit a single track (default: all 6).",
    )
    parser.add_argument(
        "--difficulty",
        choices=DIFFICULTY_ORDER,
        default=None,
        help="Audit a single difficulty (default: all three).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output report path (default: auto-derived from track/difficulty or timestamp).",
    )
    parser.add_argument(
        "--pass2-only",
        action="store_true",
        help="Skip Pass 1; re-run Pass 2 from --input report.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Prior report path (required with --pass2-only).",
    )
    parser.add_argument(
        "--pass2-all",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also run Pass 2 on Pass-1 agreements (default: ON for Phase 2). Use --no-pass2-all to disable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Audit only the first N matching questions (smoke testing).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Thread-pool size for API calls (default: 2; NIM is rate-limited).",
    )
    parser.add_argument(
        "--pass1-model",
        default=DEFAULT_PASS1_MODEL,
        help=f"Pass 1 model (default: {DEFAULT_PASS1_MODEL}).",
    )
    parser.add_argument(
        "--pass2-model",
        default=DEFAULT_PASS2_MODEL,
        help=f"Pass 2 model (default: {DEFAULT_PASS2_MODEL}).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()

    # Validate --pass2-only requires --input
    if args.pass2_only and not args.input:
        print("ERROR: --pass2-only requires --input <prior_report.json>", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key()
    client = openai.OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        timeout=120.0,
        max_retries=0,
    )

    # Resolve scope
    tracks = [args.track] if args.track else TRACK_ORDER
    difficulties = [args.difficulty] if args.difficulty else DIFFICULTY_ORDER

    # Resolve output path
    if args.output:
        output_path = Path(args.output)
    elif args.track and args.difficulty:
        output_path = SCRIPT_DIR / f"audit_nim_{args.track}_{args.difficulty}.json"
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = SCRIPT_DIR / f"audit_nim_{ts}.json"

    # Load questions
    pass1_results_map: dict[int, dict[str, Any]] | None = None
    if args.pass2_only:
        # Load from prior report; filter to requested scope
        if not args.input:
            print("ERROR: --pass2-only requires --input <prior_report.json>", file=sys.stderr)
            sys.exit(1)
        input_path = Path(args.input)
        with open(input_path, encoding="utf-8") as fh:
            prior = json.load(fh)
        prior_results = prior["results"]
        # Re-load questions for the scope so we have full q dicts (explanation etc.)
        all_questions = load_questions(tracks, difficulties)
        q_by_id = {q.get("id"): q for q in all_questions}
        # Build pass1_results from prior report
        pass1_results_map = {}
        questions_to_audit: list[dict[str, Any]] = []
        for r in prior_results:
            qid = r["id"]
            if qid not in q_by_id:
                continue
            # Only include if the prior had pass1_agrees == False (or pass2_all)
            if not r.get("pass1_agrees", True) or args.pass2_all:
                questions_to_audit.append(q_by_id[qid])
                pass1_results_map[qid] = {
                    "pass1_answer": r.get("pass1_answer", "UNPARSED"),
                    "pass1_reasoning": r.get("pass1_reasoning", ""),
                    "pass1_agrees": r.get("pass1_agrees", False),
                }
        if args.limit:
            questions_to_audit = questions_to_audit[: args.limit]
    else:
        all_questions = load_questions(tracks, difficulties)
        if args.limit:
            all_questions = all_questions[: args.limit]
        questions_to_audit = all_questions

    total = len(questions_to_audit)
    if total == 0:
        print("No questions matched the filter. Exiting.", file=sys.stderr)
        sys.exit(0)

    # Estimate API calls
    p1_calls = 0 if args.pass2_only else total
    p2_upper = total if args.pass2_all else total
    mode_flags = []
    if args.pass2_only:
        mode_flags.append("pass2-only")
    if args.pass2_all:
        mode_flags.append("pass2-all")
    mode_str = " + ".join(mode_flags) if mode_flags else "default"

    sidecar_path = Path(str(output_path) + ".partial.jsonl")

    print(
        f"\n{'='*60}\n"
        f"  API:         nvidia-nim\n"
        f"  Audit scope: {tracks} × {difficulties}\n"
        f"  Questions:   {total}\n"
        f"  Mode:        {mode_str}\n"
        f"  Pass 1:      {p1_calls} calls ({args.pass1_model})\n"
        f"  Pass 2:      up to {p2_upper} calls ({args.pass2_model})\n"
        f"  Workers:     {args.workers}\n"
        f"  Output:      {output_path}\n"
        f"  Sidecar:     {sidecar_path}\n"
        f"{'='*60}\n",
        file=sys.stderr,
        flush=True,
    )

    results = run_audit(
        questions=questions_to_audit,
        client=client,
        pass1_model=args.pass1_model,
        pass2_model=args.pass2_model,
        pass2_all=args.pass2_all,
        workers=args.workers,
        output_path=output_path,
        pass1_results=pass1_results_map,
    )

    write_report(
        results=results,
        output_path=output_path,
        tracks=tracks,
        difficulties=difficulties,
        pass1_model=args.pass1_model,
        pass2_model=args.pass2_model,
        pass2_all=args.pass2_all,
    )

    print_summary(results)
    print(f"\nFinal report: {output_path}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
