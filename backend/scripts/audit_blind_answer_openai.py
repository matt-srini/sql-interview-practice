"""
audit_blind_answer_openai.py — Two-pass MCQ audit, Phase 3 (OpenAI GPT-5).

A provider-generalized descendant of audit_blind_answer_nim.py. The resumable
per-cell orchestration (Pass 1 blind-answer → gated Pass 2 explanation-consistency,
sidecar checkpointing, verdict classifier) is identical; this file adds:

  * --provider {openai,nvidia}.  Default openai (Phase 3).
  * OpenAI GPT-5 *reasoning-model* contract: max_completion_tokens (not
    max_tokens), NO temperature (non-default is rejected), large token budgets
    (Pass1 2000 / Pass2 4000) because hidden reasoning consumes the budget, and a
    budget-doubling retry when a call returns empty content with
    finish_reason='length' (Phase-2 Finding C: never let a silent UNPARSED mask a
    defect).
  * Cost discipline: Pass-2 is GATED (NOT pass2-all) for openai. Pass 2 runs on
    (a) every Pass-1 disagreement, (b) the Phase-3 hold list (42098, 93019),
    (c) a deterministic ~10% survivor-class sample of Pass-1 agreements per track.
  * Token accounting → meta.token_usage for a real cost report.
  * phase12_cross_reference: per-question note from BOTH Phase 1 and Phase 2.
  * --sample flag: audit sample questions from content/sample_questions/<track>.json
    instead of the practice/mock pool.  Sample files contain all difficulties in a
    single file; difficulty is read from each question's own "difficulty" field.

Usage examples
--------------
# Smoke test — 2 questions, openai provider (default)
python backend/scripts/audit_blind_answer_openai.py \\
    --track pyspark --difficulty medium --limit 2 \\
    --output backend/scripts/_smoke_openai.json

# Full audit of a single MCQ cell (resumable)
python backend/scripts/audit_blind_answer_openai.py --track <t> --difficulty <d>

# Force Pass-2 on extra ids
python backend/scripts/audit_blind_answer_openai.py --track experimentation \\
    --difficulty hard --pass2-force-ids 93019,93045

# Audit sample questions for a track (all difficulties in one file)
python backend/scripts/audit_blind_answer_openai.py --sample --track data-engineering

# Audit sample questions + force Pass-2 on specific ids
python backend/scripts/audit_blind_answer_openai.py --sample --track data-engineering \\
    --pass2-force-ids 511,512

Notes
-----
- OPENAI_API_KEY (or NVIDIA_API_KEY for --provider nvidia) is loaded from backend/.env.
- A checkpoint sidecar (<output>.partial.jsonl) makes re-runs resume without
  duplicate API calls. Only error-free results are checkpointed.
- Sample runs produce a distinct output file (audit_gpt5_sample_<track>.json) so
  they never collide with practice/mock run outputs.
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

SCRIPT_DIR = Path(__file__).resolve().parent          # backend/scripts/
BACKEND_DIR = SCRIPT_DIR.parent                        # backend/
REPO_ROOT = BACKEND_DIR.parent                         # repo root

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env", override=True)
except ImportError:
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

# Sample questions: one file per track; difficulty is embedded per-question.
# Keys match TRACKS keys; values are relative paths from BACKEND_DIR.
SAMPLE_TRACK_FILES: dict[str, str] = {
    "pyspark":           "content/sample_questions/pyspark.json",
    "data-engineering":  "content/sample_questions/data_engineering.json",
    "data-modeling":     "content/sample_questions/data_modeling.json",
    "statistics":        "content/sample_questions/statistics.json",
    "ml-fundamentals":   "content/sample_questions/ml_fundamentals.json",
    "experimentation":   "content/sample_questions/experimentation.json",
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]
TRACK_ORDER = list(TRACKS.keys())

# ---------------------------------------------------------------------------
# Provider configuration (Phase 3 adds OpenAI/GPT-5 as a third family)
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, dict[str, Any]] = {
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_API_KEY",
        "pass1_model": "meta/llama-3.3-70b-instruct",
        "pass2_model": "openai/gpt-oss-20b",
        "uses_completion_tokens": False,
        "send_temperature": True,
        "pass1_budget": 800,
        "pass2_budget": 3000,
    },
    "openai": {
        "base_url": None,  # default api.openai.com/v1
        "key_env": "OPENAI_API_KEY",
        "pass1_model": "gpt-5-mini",
        "pass2_model": "gpt-5",
        "uses_completion_tokens": True,   # GPT-5 reasoning models
        "send_temperature": False,        # non-default temperature is rejected
        "pass1_budget": 2000,             # hidden reasoning eats the budget
        "pass2_budget": 4000,
    },
}
DEFAULT_PROVIDER = "openai"

# Hold-list questions whose key was contested across earlier phases — always
# force Pass 2 regardless of Pass-1 agreement (cost rule item b).
PHASE3_HOLD_LIST: set[int] = {42098, 93019}

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
BACKOFF_BASE = 4  # seconds

# ---------------------------------------------------------------------------
# Thread-safe token accounting (cost report)
# ---------------------------------------------------------------------------
_TOKEN_LOCK = threading.Lock()
_TOKEN_USAGE: dict[str, int] = {
    "pass1_in": 0, "pass1_out": 0, "pass1_calls": 0,
    "pass2_in": 0, "pass2_out": 0, "pass2_calls": 0,
}


def _record_usage(pass_no: int, usage: Any) -> None:
    if usage is None:
        return
    pin = getattr(usage, "prompt_tokens", 0) or 0
    pout = getattr(usage, "completion_tokens", 0) or 0
    with _TOKEN_LOCK:
        _TOKEN_USAGE[f"pass{pass_no}_in"] += pin
        _TOKEN_USAGE[f"pass{pass_no}_out"] += pout
        _TOKEN_USAGE[f"pass{pass_no}_calls"] += 1


# ---------------------------------------------------------------------------
# Phase 1 + Phase 2 cross-reference findings
# ---------------------------------------------------------------------------
PHASE1_FINDINGS: dict[int, str] = {
    43112: "FIXED P1: correct_option 1->2 (key C), commit 2474cfc",
    **{qid: "FIXED P1: stats +1 key-shift (a85fdca)" for qid in (
        72001, 72004, 72006, 72007, 72008, 72010, 72012, 72013, 72015, 72019,
        72020, 72023, 72024, 72027, 72029, 72030, 72031, 72032, 72033, 72034,
        72035, 72036, 72037, 72038, 72039, 72040, 72041)},
    42088: "P1 CONTENT: Delta exactly-once explanation contradicts key B (authoring)",
    43066: "P1 CONTENT: predict_output 3 identical outputs (authoring)",
    93045: "P1 CONTENT: multiple-correct B/C/D; option labels edited 206ce65",
    83011: "P1 CONTENT: label-collision approach-letter vs option-position (authoring)",
    83081: "P1 CONTENT(low): explanation over-concedes SHAP, reads as endorsing D; key A",
    93024: "P1 CONTENT: stem 'unrelated' stipulation undercuts key D",
    93026: "P1 CONTENT: ranking non-unique key D",
    43081: "P1 CONTENT: label-collision + synthesis key D",
    82002: "P1 TIEBREAKER: stem A-vs-C tension; key A defensible",
    93066: "P1 TIEBREAKER: index leak + A/B framing tension; key A",
    42098: "P1 TIEBREAKER: index leak + awkward stem; key A defensible",
    42115: "P1 TIEBREAKER: index leak + CSE-vs-pushdown debatable",
    93018: "P1 TIEBREAKER: Bayesian PBE vs threshold; key D",
    93019: "P1 TIEBREAKER: 'most fundamental'; key B (interaction test)",
    93059: "P1 TIEBREAKER: DiD/ITS both-valid key D",
    83075: "P1 FALSE-POSITIVE: harness truncation; key A correct",
}

# Phase 2 (NIM Llama + gpt-oss): 0 new key errors; remediation results.
PHASE2_FINDINGS: dict[int, str] = {
    82002: "P2: stem sharpened (0527c9a) -> both NIM models now blind-pick key A. RESOLVED.",
    93066: "P2: stem sharpened (0527c9a) -> both NIM models now blind-pick key A. RESOLVED.",
    42098: "P2 HOLD-LIST: key A defensible; NIM both blind-pick alt after sharpening -> Phase-3 tiebreak.",
    93019: "P2 HOLD-LIST: key B defensible; NIM both blind-pick alt after sharpening -> Phase-3 tiebreak.",
    **{qid: "P2: label-collision option text fixed (authoring); key unchanged" for qid in (
        42075, 42078, 42090, 42119, 43052, 43076, 43092, 43108, 43109,
        82022, 82056, 83021, 83022, 83124, 52051, 52081, 53078, 63030,
        72073, 73049, 73064, 83034)},
    **{qid: "P2: self-matching option-prefix stripped (descriptive rename); key unchanged" for qid in (
        63001, 63002, 63003, 63004, 63005, 63006, 63007, 63008, 63009, 63010,
        63011, 63012, 63013, 63014, 63015, 63016, 63017, 63018, 63019, 63020,
        63021, 63033, 63048, 63049, 63050, 53021, 93003)},
    93005: "P2 FALSE-POSITIVE: 'Variant A/B/C/D' are legitimate experiment arms; not re-lettered.",
}


def phase12_xref(qid: int | None) -> str | None:
    if qid is None:
        return None
    parts = []
    if qid in PHASE1_FINDINGS:
        parts.append(PHASE1_FINDINGS[qid])
    if qid in PHASE2_FINDINGS:
        parts.append(PHASE2_FINDINGS[qid])
    return " || ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Letter helpers
# ---------------------------------------------------------------------------
def idx_to_letter(i: int) -> str:
    return chr(ord("A") + i)


def letter_to_idx(letter: str) -> int:
    return ord(letter.upper()) - ord("A")


def extract_answer_letter(raw: str) -> str:
    """Robustly pull an A-D answer letter from a Pass-1 reply (tolerates CoT)."""
    m = re.search(r"ANSWER\s*:\s*\(?([A-Da-d])\)?", raw, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(r"answer\s+is\s*:?\s*\(?([A-Da-d])\)?\b", raw, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(
        r"\b(?:choose|select|pick|chose|selected|going with)\s+(?:option\s+)?\(?([A-Da-d])\)?\b",
        raw, re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()
    matches = re.findall(r"\bOption\s+\(?([A-Da-d])\)?\b", raw, re.IGNORECASE)
    if matches:
        return matches[-1].upper()
    m = re.match(r"^\s*\(?([A-Da-d])\)?[\).:\s]", raw)
    if m:
        return m.group(1).upper()
    return "UNPARSED"


def message_text(msg: Any) -> str:
    """Answer-bearing text, tolerant of reasoning models (<think> tags / reasoning_content)."""
    content = (getattr(msg, "content", None) or "")
    if "</think>" in content:
        tail = content.rsplit("</think>", 1)[-1].strip()
        if tail:
            content = tail
    if content.strip():
        return content
    rc = getattr(msg, "reasoning_content", None) or ""
    return rc


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------
def load_questions(tracks: list[str], difficulties: list[str]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for track in tracks:
        track_dir = BACKEND_DIR / TRACKS[track]
        for diff in difficulties:
            file_path = track_dir / f"{diff}.json"
            if not file_path.exists():
                print(f"WARNING: {file_path} not found — skipping.", file=sys.stderr)
                continue
            with open(file_path, encoding="utf-8") as fh:
                data = json.load(fh)
            for q in data:
                if not isinstance(q.get("correct_option"), int):
                    continue
                opts = q.get("options")
                if not isinstance(opts, list) or len(opts) < 2:
                    continue
                if track == "statistics" and q.get("subtype") == "numerical":
                    continue
                q["_track"] = track
                q["_difficulty"] = diff
                questions.append(q)
    return questions


def load_sample_questions(track: str, difficulties: list[str]) -> list[dict[str, Any]]:
    """Load MCQ-eligible questions from the sample pool for a single track.

    Sample files live at content/sample_questions/<slug>.json (one file per track,
    all difficulties mixed).  The per-question ``difficulty`` field is used for
    ``_difficulty``; the filename-based diff loop used by load_questions does not
    apply here.

    The same MCQ filter as load_questions is applied:
    - correct_option must be an int
    - options must be a list with ≥ 2 entries
    - statistics numerical subtype is skipped (no options/correct_option anyway)
    - questions whose difficulty is not in *difficulties* are skipped (so
      --difficulty still works as a filter when --sample is set)
    """
    if track not in SAMPLE_TRACK_FILES:
        print(f"ERROR: --sample is not supported for track '{track}'. "
              f"Supported: {sorted(SAMPLE_TRACK_FILES.keys())}", file=sys.stderr)
        sys.exit(1)

    file_path = BACKEND_DIR / SAMPLE_TRACK_FILES[track]
    if not file_path.exists():
        print(f"ERROR: Sample file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(file_path, encoding="utf-8") as fh:
        data = json.load(fh)

    questions: list[dict[str, Any]] = []
    for q in data:
        diff = q.get("difficulty", "")
        if diff not in difficulties:
            continue
        if not isinstance(q.get("correct_option"), int):
            continue
        opts = q.get("options")
        if not isinstance(opts, list) or len(opts) < 2:
            continue
        if track == "statistics" and q.get("subtype") == "numerical":
            continue
        q["_track"] = track
        q["_difficulty"] = diff
        questions.append(q)

    print(f"[sample] Loaded {len(questions)} eligible MCQ questions from {file_path}",
          file=sys.stderr, flush=True)
    return questions


# ---------------------------------------------------------------------------
# Stem builder
# ---------------------------------------------------------------------------
def build_stem(q: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ("title", "description"):
        v = q.get(k, "")
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
            parts.append("")
    sc = q.get("scenario_context", "")
    if isinstance(sc, str) and sc.strip():
        parts.append(sc.strip())
        parts.append("")
    parts.append("Options:")
    for i, opt in enumerate(q.get("options", [])):
        parts.append(f"{idx_to_letter(i)}) {opt}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Retry wrapper (provider-aware) — returns (text, finish_reason, usage)
# ---------------------------------------------------------------------------
def call_with_retry(
    client: openai.OpenAI,
    *,
    provider_cfg: dict[str, Any],
    model: str,
    system: str,
    user_content: str,
    budget: int,
) -> tuple[str, str, Any]:
    """Call the API with backoff + (for reasoning models) an empty-content retry.

    When finish_reason='length' AND no visible content was returned (the budget
    was wholly consumed by hidden reasoning), retry once with 2x budget so a
    silent UNPARSED cannot mask a real defect (Phase-2 Finding C).
    """
    use_ct = provider_cfg["uses_completion_tokens"]
    send_temp = provider_cfg["send_temperature"]

    def _one_call(tok_budget: int) -> tuple[str, str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        }
        if use_ct:
            kwargs["max_completion_tokens"] = tok_budget
        else:
            kwargs["max_tokens"] = tok_budget
        if send_temp:
            kwargs["temperature"] = 0
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return (
            message_text(choice.message),
            getattr(choice, "finish_reason", "") or "",
            getattr(resp, "usage", None),
        )

    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            text, finish, usage = _one_call(budget)
            if (not text.strip()) and finish == "length":
                text2, finish2, usage2 = _one_call(budget * 2)
                _record_usage_raw(usage)  # count the wasted first call too
                if text2.strip():
                    return text2, finish2, usage2
                return text, finish, usage2 if usage2 is not None else usage
            return text, finish, usage
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

        wait = min(60, BACKOFF_BASE * (2 ** attempt)) + (attempt * 0.7)
        print(
            f"  [retry] attempt {attempt + 1}/{MAX_RETRIES} failed "
            f"({type(last_exc).__name__}), waiting {wait:.1f}s …",
            file=sys.stderr, flush=True,
        )
        time.sleep(wait)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed") from last_exc


def _record_usage_raw(usage: Any) -> None:
    """Add a stray (empty-retry) call's tokens to the Pass-1 bucket as overhead."""
    if usage is None:
        return
    with _TOKEN_LOCK:
        _TOKEN_USAGE["pass1_in"] += getattr(usage, "prompt_tokens", 0) or 0
        _TOKEN_USAGE["pass1_out"] += getattr(usage, "completion_tokens", 0) or 0


# ---------------------------------------------------------------------------
# Pass 1
# ---------------------------------------------------------------------------
def run_pass1(q: dict[str, Any], client: openai.OpenAI,
              provider_cfg: dict[str, Any], model: str, budget: int) -> dict[str, Any]:
    stem = build_stem(q)
    keyed = idx_to_letter(q["correct_option"])
    try:
        raw, _finish, usage = call_with_retry(
            client, provider_cfg=provider_cfg, model=model,
            system=PASS1_SYSTEM, user_content=stem, budget=budget,
        )
        _record_usage(1, usage)
    except Exception as exc:
        return {"pass1_answer": "ERROR", "pass1_reasoning": str(exc), "pass1_agrees": False}

    pass1_answer = extract_answer_letter(raw)
    m_reasoning = re.search(r"REASONING\s*:\s*(.*)", raw, re.IGNORECASE | re.DOTALL)
    pass1_reasoning = m_reasoning.group(1).strip() if m_reasoning else raw.strip()[:500]
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


def run_pass2(q: dict[str, Any], client: openai.OpenAI,
              provider_cfg: dict[str, Any], model: str, budget: int) -> dict[str, Any]:
    prompt = build_pass2_prompt(q)
    try:
        raw, _finish, usage = call_with_retry(
            client, provider_cfg=provider_cfg, model=model,
            system=PASS2_SYSTEM, user_content=prompt, budget=budget,
        )
        _record_usage(2, usage)
    except Exception as exc:
        return {
            "pass2_ran": True, "pass2_explanation_leads_to": "ERROR",
            "pass2_consistent": False, "pass2_reasoning": str(exc),
        }

    m_leads = re.search(r"LEADS_TO\s*:\s*([A-Da-d])", raw, re.IGNORECASE)
    leads = m_leads.group(1).upper() if m_leads else "UNPARSED"
    m_matches = re.search(r"MATCHES_KEY\s*:\s*(yes|no)", raw, re.IGNORECASE)
    if m_matches:
        pass2_consistent = m_matches.group(1).lower() == "yes"
    else:
        keyed = idx_to_letter(q["correct_option"])
        pass2_consistent = (leads == keyed) if leads not in ("UNPARSED", "ERROR") else False
    m_why = re.search(r"WHY\s*:\s*(.*)", raw, re.IGNORECASE | re.DOTALL)
    pass2_reasoning = m_why.group(1).strip() if m_why else raw.strip()[:500]
    return {
        "pass2_ran": True,
        "pass2_explanation_leads_to": leads,
        "pass2_consistent": pass2_consistent,
        "pass2_reasoning": pass2_reasoning,
    }


# ---------------------------------------------------------------------------
# Verdict classifier (identical semantics to the NIM harness)
# ---------------------------------------------------------------------------
def classify(q: dict[str, Any], pass1: dict[str, Any],
             pass2: dict[str, Any] | None) -> dict[str, Any]:
    keyed = idx_to_letter(q["correct_option"])
    p1_agrees: bool = pass1["pass1_agrees"]
    p1_answer: str = pass1["pass1_answer"]

    if pass2 is None:
        return {
            "pass2_ran": False, "pass2_explanation_leads_to": None,
            "pass2_consistent": None, "pass2_reasoning": None,
            "verdict": VERDICT_CONSISTENT, "fix_category": FIX_NONE,
            "suggested_correct_option": None,
        }

    leads: str | None = pass2.get("pass2_explanation_leads_to")
    if p1_agrees:
        if leads in (keyed, "UNPARSED", "ERROR", None):
            verdict, fix_cat = VERDICT_CONSISTENT, FIX_NONE
        else:
            verdict, fix_cat = VERDICT_BROKEN, FIX_AUTHORING
        suggested = None
    else:
        if leads in ("UNPARSED", "ERROR", None):
            verdict, fix_cat, suggested = VERDICT_INCONSISTENT, FIX_REVIEW, None
        elif leads == keyed:
            verdict, fix_cat, suggested = VERDICT_INCONSISTENT, FIX_REVIEW, None
        elif leads == p1_answer:
            verdict, fix_cat, suggested = VERDICT_INVERTED, FIX_MECHANICAL, letter_to_idx(leads)
        else:
            verdict, fix_cat, suggested = VERDICT_BROKEN, FIX_AUTHORING, None

    return {
        **pass2,
        "verdict": verdict,
        "fix_category": fix_cat,
        "suggested_correct_option": suggested if verdict == VERDICT_INVERTED else None,
    }


def build_result(q: dict[str, Any], pass1: dict[str, Any],
                 classified: dict[str, Any]) -> dict[str, Any]:
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
        "phase12_cross_reference": phase12_xref(q_id),
    }


# ---------------------------------------------------------------------------
# Per-question pipeline + gated Pass-2 policy
# ---------------------------------------------------------------------------
def is_clean(result: dict[str, Any]) -> bool:
    if result.get("pass1_answer") == "ERROR":
        return False
    if result.get("pass2_ran") and result.get("pass2_explanation_leads_to") == "ERROR":
        return False
    return True


def should_run_pass2(q: dict[str, Any], pass1: dict[str, Any], *,
                     pass2_all: bool, force_ids: set[int], sample_residue: int | None) -> bool:
    """Gated Pass-2 policy (cost rule): disagreement OR forced OR survivor-sample."""
    if pass2_all:
        return True
    if not pass1["pass1_agrees"]:           # (a) every disagreement
        return True
    qid = q.get("id")
    if qid in force_ids:                     # (b) hold list / explicit force
        return True
    if sample_residue is not None and qid is not None and (qid % 10) == sample_residue:
        return True                          # (c) deterministic ~10% agreement sample
    return False


def process_question(q: dict[str, Any], client: openai.OpenAI, provider_cfg: dict[str, Any],
                     pass1_model: str, pass2_model: str, pass1_budget: int, pass2_budget: int,
                     pass2_all: bool, force_ids: set[int], sample_residue: int | None,
                     pass1_override: dict[str, Any] | None) -> dict[str, Any]:
    if pass1_override is not None:
        pass1 = pass1_override
    else:
        pass1 = run_pass1(q, client, provider_cfg, pass1_model, pass1_budget)

    if should_run_pass2(q, pass1, pass2_all=pass2_all, force_ids=force_ids,
                        sample_residue=sample_residue):
        pass2 = run_pass2(q, client, provider_cfg, pass2_model, pass2_budget)
    else:
        pass2 = None

    classified = classify(q, pass1, pass2)
    return build_result(q, pass1, classified)


# ---------------------------------------------------------------------------
# Resumable orchestration
# ---------------------------------------------------------------------------
def run_audit(questions, client, provider_cfg, pass1_model, pass2_model,
              pass1_budget, pass2_budget, pass2_all, force_ids, sample_residue,
              workers, output_path, pass1_results=None):
    sidecar_path = Path(str(output_path) + ".partial.jsonl")
    sidecar_lock = threading.Lock()

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
                    pass
        if done_results:
            print(f"[resume] {len(done_results)} already-done results loaded from {sidecar_path}",
                  file=sys.stderr, flush=True)

    remaining = [q for q in questions if q.get("id") not in done_results]
    total = len(questions)
    already_done = len(done_results)
    print(f"[audit] {already_done} already done, {len(remaining)} to process "
          f"(total {total}), workers={workers}", file=sys.stderr, flush=True)

    if remaining:
        completed = 0

        def task(q: dict[str, Any]) -> dict[str, Any]:
            qid = q.get("id", 0)
            p1_override = None
            if pass1_results is not None and qid in pass1_results:
                p1_override = pass1_results[qid]
            result = process_question(
                q, client, provider_cfg, pass1_model, pass2_model,
                pass1_budget, pass2_budget, pass2_all, force_ids, sample_residue, p1_override,
            )
            if is_clean(result):
                with sidecar_lock:
                    with open(sidecar_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(result, ensure_ascii=False) + "\n")
            return result

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(task, q): q for q in remaining}
            for fut in as_completed(futures):
                try:
                    result = fut.result()
                    done_results[result["id"]] = result
                except Exception as exc:
                    q = futures[fut]
                    print(f"  [error] question id={q.get('id')} failed: {exc}",
                          file=sys.stderr, flush=True)
                completed += 1
                if completed % 5 == 0 or completed == len(remaining):
                    print(f"[audit] {already_done + completed}/{total} processed …",
                          file=sys.stderr, flush=True)

    all_results = list(done_results.values())
    all_results.sort(key=lambda r: (
        TRACK_ORDER.index(r["track"]) if r["track"] in TRACK_ORDER else 99,
        DIFFICULTY_ORDER.index(r["difficulty"]) if r["difficulty"] in DIFFICULTY_ORDER else 99,
        r["id"] if r["id"] is not None else 0,
    ))
    return all_results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _cost_usd(u: dict[str, int]) -> float:
    # Widely-cited GPT-5 pricing per 1M tokens: mini $0.25/$2, gpt-5 $1.25/$10.
    return (u["pass1_in"] * 0.25 + u["pass1_out"] * 2.0
            + u["pass2_in"] * 1.25 + u["pass2_out"] * 10.0) / 1_000_000


def write_report(results, output_path, provider, tracks, difficulties,
                 pass1_model, pass2_model, pass2_all, *, is_sample: bool = False):
    now = datetime.now(timezone.utc)
    verdict_counts = {VERDICT_CONSISTENT: 0, VERDICT_INVERTED: 0,
                      VERDICT_BROKEN: 0, VERDICT_INCONSISTENT: 0}
    flagged_ids, external_ids = [], []
    for r in results:
        v = r["verdict"]
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        if v != VERDICT_CONSISTENT:
            flagged_ids.append(r["id"])
        if v in (VERDICT_INCONSISTENT, VERDICT_BROKEN, VERDICT_INVERTED):
            external_ids.append(r["id"])

    with _TOKEN_LOCK:
        usage = dict(_TOKEN_USAGE)

    report = {
        "meta": {
            "generated_at_utc": now.isoformat(),
            "api": provider,
            "phase": "phase3-openai",
            "pool": "sample" if is_sample else "practice_mock",
            "tracks": tracks,
            "difficulties": difficulties,
            "pass1_model": pass1_model,
            "pass2_model": pass2_model,
            "pass2_all": pass2_all,
            "total_audited": len(results),
            "counts_by_verdict": verdict_counts,
            "flagged_ids": sorted(flagged_ids),
            "external_llm_candidate_ids": sorted(external_ids),
            "token_usage": usage,
            "est_cost_usd": round(_cost_usd(usage), 4),
        },
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nReport written to: {output_path}", file=sys.stderr, flush=True)


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
    for verdict in [VERDICT_CONSISTENT, VERDICT_INVERTED, VERDICT_BROKEN, VERDICT_INCONSISTENT]:
        print(f"  {verdict:<20} {verdict_counts.get(verdict, 0):>6}", file=sys.stderr)
    print(f"  {'TOTAL':<20} {len(results):>6}", file=sys.stderr)
    with _TOKEN_LOCK:
        u = dict(_TOKEN_USAGE)
    print(f"  tokens P1 in/out={u['pass1_in']}/{u['pass1_out']} ({u['pass1_calls']} calls) "
          f"P2 in/out={u['pass2_in']}/{u['pass2_out']} ({u['pass2_calls']} calls)", file=sys.stderr)
    print(f"  est_cost_usd ≈ ${_cost_usd(u):.4f}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if flagged:
        print(f"\nFlagged questions ({len(flagged)}):", file=sys.stderr)
        for r in sorted(flagged, key=lambda x: (TRACK_ORDER.index(x["track"])
                        if x["track"] in TRACK_ORDER else 99, x["id"])):
            xref = f"  [{r['phase12_cross_reference']}]" if r.get("phase12_cross_reference") else ""
            print(f"  {r['id']:<8} {r['track']:<18} {r['difficulty']:<7} "
                  f"p1={r['pass1_answer']}->key={r['keyed_letter']} "
                  f"p2={r['pass2_explanation_leads_to']} {r['verdict']:<14} {r['fix_category']}{xref}",
                  file=sys.stderr)
    else:
        print("\nNo flagged questions.", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Two-pass MCQ audit — Phase 3 (OpenAI GPT-5 default).",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--provider", choices=list(PROVIDERS.keys()), default=DEFAULT_PROVIDER)
    p.add_argument("--track", choices=list(TRACKS.keys()), default=None)
    p.add_argument("--difficulty", choices=DIFFICULTY_ORDER, default=None)
    p.add_argument("--sample", action="store_true", default=False,
                   help=(
                       "Audit sample questions (content/sample_questions/<track>.json) "
                       "instead of the practice/mock pool.  Requires --track.  "
                       "Output defaults to audit_gpt5_sample_<track>.json."
                   ))
    p.add_argument("--output", default=None)
    p.add_argument("--pass2-only", action="store_true")
    p.add_argument("--input", default=None)
    p.add_argument("--pass2-all", action=argparse.BooleanOptionalAction, default=False,
                   help="Run Pass 2 on ALL agreements (default OFF for openai cost discipline).")
    p.add_argument("--pass2-force-ids", default="",
                   help="Comma-separated ids to always Pass-2 (hold list is always included).")
    p.add_argument("--pass2-sample-residue", type=int, default=3,
                   help="Pass-2 agreements where id%%10==residue (~10%% survivor sample). -1 disables.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--pass1-model", default=None)
    p.add_argument("--pass2-model", default=None)
    p.add_argument("--pass1-budget", type=int, default=None)
    p.add_argument("--pass2-budget", type=int, default=None)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.pass2_only and not args.input:
        print("ERROR: --pass2-only requires --input <prior_report.json>", file=sys.stderr)
        sys.exit(1)
    if args.sample and not args.track:
        print("ERROR: --sample requires --track <track>.", file=sys.stderr)
        sys.exit(1)

    provider_cfg = PROVIDERS[args.provider]
    api_key = os.environ.get(provider_cfg["key_env"], "").strip()
    if not api_key:
        print(f"ERROR: {provider_cfg['key_env']} not found in env/.env.", file=sys.stderr)
        sys.exit(1)

    client = openai.OpenAI(base_url=provider_cfg["base_url"], api_key=api_key,
                           timeout=180.0, max_retries=0)

    pass1_model = args.pass1_model or provider_cfg["pass1_model"]
    pass2_model = args.pass2_model or provider_cfg["pass2_model"]
    pass1_budget = args.pass1_budget or provider_cfg["pass1_budget"]
    pass2_budget = args.pass2_budget or provider_cfg["pass2_budget"]
    sample_residue = None if args.pass2_sample_residue < 0 else args.pass2_sample_residue
    force_ids = set(PHASE3_HOLD_LIST)
    if args.pass2_force_ids.strip():
        force_ids |= {int(x) for x in args.pass2_force_ids.split(",") if x.strip()}

    tracks = [args.track] if args.track else TRACK_ORDER
    difficulties = [args.difficulty] if args.difficulty else DIFFICULTY_ORDER

    if args.output:
        output_path = Path(args.output)
    elif args.sample:
        # Distinct filename so sample runs never collide with practice/mock outputs.
        output_path = SCRIPT_DIR / f"audit_gpt5_sample_{args.track}.json"
    elif args.track and args.difficulty:
        output_path = SCRIPT_DIR / f"audit_gpt5_{args.track}_{args.difficulty}.json"
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = SCRIPT_DIR / f"audit_gpt5_{ts}.json"

    # -----------------------------------------------------------------------
    # Question loading — sample pool vs practice/mock pool
    # -----------------------------------------------------------------------
    def _load_all() -> list[dict[str, Any]]:
        if args.sample:
            return load_sample_questions(args.track, difficulties)
        return load_questions(tracks, difficulties)

    pass1_results_map: dict[int, dict[str, Any]] | None = None
    if args.pass2_only:
        with open(Path(args.input), encoding="utf-8") as fh:
            prior = json.load(fh)
        all_questions = _load_all()
        q_by_id = {q.get("id"): q for q in all_questions}
        pass1_results_map = {}
        questions_to_audit = []
        for r in prior["results"]:
            qid = r["id"]
            if qid not in q_by_id:
                continue
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
        all_questions = _load_all()
        if args.limit:
            all_questions = all_questions[: args.limit]
        questions_to_audit = all_questions

    total = len(questions_to_audit)
    if total == 0:
        print("No questions matched the filter. Exiting.", file=sys.stderr)
        sys.exit(0)

    sidecar_path = Path(str(output_path) + ".partial.jsonl")
    mode_str = "pass2-all" if args.pass2_all else (
        f"gated (disagree + hold{sorted(force_ids)} + sample id%10=={sample_residue})")
    pool_label = f"SAMPLE ({args.track})" if args.sample else f"{tracks} × {difficulties}"
    print(
        f"\n{'='*64}\n"
        f"  Provider:    {args.provider}\n"
        f"  Pool:        {'sample' if args.sample else 'practice/mock'}\n"
        f"  Audit scope: {pool_label}\n"
        f"  Questions:   {total}\n"
        f"  Pass-2 mode: {mode_str}\n"
        f"  Pass 1:      {pass1_model} (budget {pass1_budget})\n"
        f"  Pass 2:      {pass2_model} (budget {pass2_budget})\n"
        f"  Workers:     {args.workers}\n"
        f"  Output:      {output_path}\n"
        f"  Sidecar:     {sidecar_path}\n"
        f"{'='*64}\n", file=sys.stderr, flush=True)

    results = run_audit(
        questions=questions_to_audit, client=client, provider_cfg=provider_cfg,
        pass1_model=pass1_model, pass2_model=pass2_model,
        pass1_budget=pass1_budget, pass2_budget=pass2_budget,
        pass2_all=args.pass2_all, force_ids=force_ids, sample_residue=sample_residue,
        workers=args.workers, output_path=output_path, pass1_results=pass1_results_map,
    )
    write_report(results, output_path, args.provider, tracks, difficulties,
                 pass1_model, pass2_model, args.pass2_all, is_sample=args.sample)
    print_summary(results)
    print(f"\nFinal report: {output_path}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
