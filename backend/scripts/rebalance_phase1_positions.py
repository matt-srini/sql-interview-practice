"""Deterministic Phase 1 position-debiasing transform for MCQ answer keys.

PURPOSE
-------
Permutes each MCQ question's ``options`` array so that correct-answer
POSITIONS trend toward uniform distribution across each question group,
then updates ``correct_option`` and remaps "Option A/B/C/D" letter
references in the explanation through the SAME permutation.

This is CONTENT-PRESERVING: it changes option ORDER and the corresponding
letter references in the explanation — never option text, never which
answer is semantically correct.

MODES
-----
--dry-run  (default)
    Print per-group statistics (current vs projected distribution, validator
    pass/fail projection) and the full ``skipped_noncanonical`` list.
    Writes NOTHING.

--apply
    Rewrite JSON files in place (2-space indent, ensure_ascii=False,
    trailing newline).  Only run after --dry-run has been reviewed.

INVOCATION
----------
    cd backend
    ../.venv/bin/python scripts/rebalance_phase1_positions.py --dry-run
    ../.venv/bin/python scripts/rebalance_phase1_positions.py --apply  # Phase 1 only
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from backend/
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 6 MCQ-capable tracks and their content directories.
# sample_* keys are virtual — their files are in content/sample_questions/.
_MCQ_TRACKS: dict[str, Path] = {
    "data-engineering":  BACKEND_ROOT / "content" / "data_engineering_questions",
    "data-modeling":     BACKEND_ROOT / "content" / "data_modeling_questions",
    "pyspark":           BACKEND_ROOT / "content" / "pyspark_questions",
    "ml-fundamentals":   BACKEND_ROOT / "content" / "ml_fundamentals_questions",
    "experimentation":   BACKEND_ROOT / "content" / "experimentation_questions",
    "statistics":        BACKEND_ROOT / "content" / "statistics_questions",
}

_SAMPLE_FILES: dict[str, Path] = {
    "data-engineering": BACKEND_ROOT / "content" / "sample_questions" / "data_engineering.json",
    "data-modeling":    BACKEND_ROOT / "content" / "sample_questions" / "data_modeling.json",
    "pyspark":          BACKEND_ROOT / "content" / "sample_questions" / "pyspark.json",
    "ml-fundamentals":  BACKEND_ROOT / "content" / "sample_questions" / "ml_fundamentals.json",
    "experimentation":  BACKEND_ROOT / "content" / "sample_questions" / "experimentation.json",
    "statistics":       BACKEND_ROOT / "content" / "sample_questions" / "statistics.json",
}

# Debias thresholds (must match _validate_answer_position_balance)
MAX_POSITION_SHARE = 0.40
MAX_RUN = 5

# Non-canonical prose patterns that mechanical remap CANNOT safely handle.
# A question matching any of these is skipped.
_NONCANONICAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'\b(first|second|third|fourth|last)\s+(option|choice|answer)\b', re.IGNORECASE),
    re.compile(r'\bOptions\s+[A-D]\b', re.IGNORECASE),   # plural "Options A" etc.
    re.compile(r'\([A-D]\)', re.IGNORECASE),              # parenthesised letter: (A), (B)
    re.compile(r'\bchoice\s+[A-D]\b', re.IGNORECASE),
    re.compile(r'\banswer\s+[A-D]\b', re.IGNORECASE),
    re.compile(r'\b[A-D]\s+and\s+[A-D]\b', re.IGNORECASE),
    re.compile(r'\b[A-D]/[A-D]\b'),
]

# Patterns that indicate a question's STEM or OPTION TEXT couples letters to
# position — permuting those would corrupt the question content.
_LETTER_COUPLING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'\bOption [A-D]\b'),
    re.compile(r'\([A-D]\)', re.IGNORECASE),
    re.compile(
        r'\b(Model|Variant|Approach|Option|Group|Config|Plan|Design|Method|'
        r'Strategy|Proposal|Scenario|Schema|Choice|Arm)\s+\(?[A-D]\)?\b'
    ),
    re.compile(r'\b[A-D]\)\s'),
    re.compile(r'(?m)^\s*[A-D][:.]\s'),
    re.compile(r'\b[A-D]\s+(and|or|vs\.?|/)\s+[A-D]\b'),
]

# Canonical explanation letter-reference pattern — the ONLY form we remap.
_CANONICAL_OPTION_REF = re.compile(r'\bOption ([A-D])\b')

# Fixed seed base for deterministic assignment
_SEED_BASE = "datathink-phase1-debias"


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _is_mcq(q: dict) -> bool:
    """Return True iff question is a valid MCQ (int correct_option + list options len>=2)."""
    if not isinstance(q.get("correct_option"), int):
        return False
    opts = q.get("options")
    return isinstance(opts, list) and len(opts) >= 2


def _collect_file_records() -> list[dict]:
    """Return a flat list of records, one per JSON file that contains MCQ questions.

    Each record:
        {
            "file_path": Path,
            "is_sample": bool,
            "track": str,        # e.g. "data-engineering"
            "difficulty": str,   # file stem for practice/mock; mixed for samples
            "questions": list[dict],   # ALL questions in the file (including non-MCQ)
        }
    """
    records = []

    for track, directory in _MCQ_TRACKS.items():
        for file_path in sorted(directory.glob("*.json")):
            if file_path.stem == "schemas":
                continue
            with file_path.open("r", encoding="utf-8") as fh:
                questions = json.load(fh)
            records.append({
                "file_path": file_path,
                "is_sample": False,
                "track": track,
                "difficulty": file_path.stem,
                "questions": questions,
            })

    for track, file_path in _SAMPLE_FILES.items():
        if not file_path.exists():
            continue
        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)
        records.append({
            "file_path": file_path,
            "is_sample": True,
            "track": track,
            "difficulty": "all",
            "questions": questions,
        })

    return records


def _build_groups(records: list[dict]) -> dict[tuple, list[dict]]:
    """Build group_key -> [question, ...] mapping for qualifying MCQ questions.

    Group key:
      Practice/mock  : (track, difficulty, pool)   pool = "mock"|"practice"
      Sample         : ("sample", track, "all")
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for rec in records:
        for q in rec["questions"]:
            if not _is_mcq(q):
                continue
            if rec["is_sample"]:
                key = ("sample", rec["track"], "all")
            else:
                pool = "mock" if q.get("mock_only") else "practice"
                key = (rec["track"], rec["difficulty"], pool)
            groups[key].append(q)
    return dict(groups)


# ---------------------------------------------------------------------------
# Non-canonical check
# ---------------------------------------------------------------------------

def _find_noncanonical_snippet(explanation: str) -> str | None:
    """Return the first non-canonical positional snippet, or None if clean."""
    for pat in _NONCANONICAL_PATTERNS:
        m = pat.search(explanation)
        if m:
            return m.group(0)
    return None


def _find_letter_coupling_snippet(q: dict) -> str | None:
    """Return the first letter-coupling snippet in stem fields or option texts, or None.

    Checks the joined stem fields (description, scenario_context, code_snippet,
    question, prompt) AND each option's text.  A match means the question couples
    an option letter to a specific position in its CONTENT — permuting options
    would change the question's meaning.
    """
    # Collect stem text
    stem_parts: list[str] = []
    for field in ("description", "scenario_context", "code_snippet", "question", "prompt"):
        val = q.get(field)
        if val:
            stem_parts.append(str(val))
    stem_text = "\n".join(stem_parts)

    # Check stem
    for pat in _LETTER_COUPLING_PATTERNS:
        m = pat.search(stem_text)
        if m:
            return m.group(0)

    # Check each option's text
    for opt_text in q.get("options", []):
        if not isinstance(opt_text, str):
            continue
        for pat in _LETTER_COUPLING_PATTERNS:
            m = pat.search(opt_text)
            if m:
                return m.group(0)

    return None


# ---------------------------------------------------------------------------
# Balanced target multiset construction
# ---------------------------------------------------------------------------

def _build_balanced_targets(
    n: int,
    n_options: int,
    rng: random.Random,
    seed_str: str,
    sorted_qs: list[dict],
    locked_counts: dict[int, int] | None = None,
) -> list[int]:
    """Return a length-n list of target positions (0..n_options-1).

    When ``locked_counts`` is provided the target allocation accounts for
    questions in the same group that are locked/skipped at each position,
    so the OVERALL group stays within MAX_POSITION_SHARE.

    Without skip awareness each position gets floor(n/n_options) or
    ceil(n/n_options), which is always <= 1/n_options + epsilon (well
    under 40% for n_options=4 and n>=4).

    The list is shuffled deterministically, then verified for runs.
    Up to 10 retry attempts are made (re-seeded) if a run of >= MAX_RUN is
    found.  If all retries fail, local swaps are applied to break runs.
    """
    targets = _make_flat_target_list(n, n_options, locked_counts)

    for attempt in range(10):
        rng = random.Random(f"{seed_str}:attempt{attempt}")
        rng.shuffle(targets)
        if not _has_run(targets):
            return targets

    # Fallback: local swap to break every run
    targets = _make_flat_target_list(n, n_options, locked_counts)
    random.Random(f"{seed_str}:fallback").shuffle(targets)
    targets = _break_runs(targets)
    return targets


def _make_flat_target_list(
    n: int,
    n_options: int,
    locked_counts: dict[int, int] | None = None,
) -> list[int]:
    """Build a flat list of n target positions (0..n_options-1).

    If ``locked_counts`` is provided (a mapping from position -> count of
    questions in the same group that are locked/skipped at that position),
    the target allocation for each position is reduced by the locked count
    before the uniform floor/ceil split is applied to the remaining capacity.
    This ensures that the OVERALL group (locked + permutable) stays within
    the MAX_POSITION_SHARE threshold even when some positions are pre-filled
    by skipped questions.

    Without ``locked_counts`` the allocation is the standard uniform split:
    each position gets floor(n/n_options) or ceil(n/n_options).
    """
    if locked_counts is None:
        locked_counts = {}

    # Total group size = n (permutable) + sum(locked_counts)
    total_n = n + sum(locked_counts.values())
    # Target for each position in the full group ≈ total_n / n_options
    # (floor or ceil to sum to total_n)
    full_base = total_n // n_options
    full_remainder = total_n % n_options
    full_targets = {
        pos: full_base + (1 if pos < full_remainder else 0)
        for pos in range(n_options)
    }

    # Capacity for permutable questions = full_target - locked_count (min 0)
    capacities = {
        pos: max(0, full_targets[pos] - locked_counts.get(pos, 0))
        for pos in range(n_options)
    }

    # If total capacity != n, there's overflow (too many locked at some position).
    # Fall back to a best-effort allocation that still minimises the oversubscribed
    # positions: cap each position's permutable allocation at the threshold-limited
    # maximum, then distribute the remaining slots to the least-filled positions.
    if sum(capacities.values()) != n:
        # Max total each position can hold in the full group without exceeding
        # MAX_POSITION_SHARE (use floor to be conservative).
        max_per_pos = max(1, int(total_n * MAX_POSITION_SHARE))
        adjusted: dict[int, int] = {}
        for pos in range(n_options):
            locked_here = locked_counts.get(pos, 0)
            adjusted[pos] = max(0, min(n, max_per_pos - locked_here))

        # If adjusted sums to more than n, scale down uniformly.
        total_adj = sum(adjusted.values())
        if total_adj > n:
            # Reduce the positions with highest adjusted counts first.
            excess = total_adj - n
            for pos in sorted(adjusted, key=lambda p: -adjusted[p]):
                if excess <= 0:
                    break
                cut = min(excess, adjusted[pos])
                adjusted[pos] -= cut
                excess -= cut
        elif total_adj < n:
            # Not enough capacity in any position — fall back to pure uniform split.
            base = n // n_options
            remainder = n % n_options
            targets: list[int] = []
            for pos in range(n_options):
                targets.extend([pos] * (base + (1 if pos < remainder else 0)))
            return targets

        targets = []
        for pos in range(n_options):
            targets.extend([pos] * adjusted[pos])
        return targets

    targets = []
    for pos in range(n_options):
        targets.extend([pos] * capacities[pos])
    return targets


def _has_run(seq: list[int]) -> bool:
    """Return True if seq contains a run of >= MAX_RUN identical values."""
    if not seq:
        return False
    run = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
            if run >= MAX_RUN:
                return True
        else:
            run = 1
    return False


def _break_runs(targets: list[int]) -> list[int]:
    """Greedily swap elements to eliminate all runs of >= MAX_RUN."""
    seq = list(targets)
    n = len(seq)
    changed = True
    while changed:
        changed = False
        run_start = 0
        for i in range(1, n + 1):
            if i < n and seq[i] == seq[run_start]:
                continue
            run_len = i - run_start
            if run_len >= MAX_RUN:
                # Find a swap candidate: search after the run for a different value
                for j in range(i, n):
                    if seq[j] != seq[run_start]:
                        # Swap the end of the run with j
                        swap_idx = run_start + MAX_RUN - 1
                        seq[swap_idx], seq[j] = seq[j], seq[swap_idx]
                        changed = True
                        break
            run_start = i
    return seq


# ---------------------------------------------------------------------------
# Permutation building
# ---------------------------------------------------------------------------

def _build_permutation(c_old: int, c_new: int, n_options: int) -> list[int]:
    """Return old_index -> new_index mapping for all n_options slots.

    The correct option moves from c_old to c_new.  All other options are
    placed into the remaining slots preserving their original relative order.

    Returns a list P of length n_options where P[old_idx] = new_idx.
    """
    other_old = [i for i in range(n_options) if i != c_old]
    other_new = [j for j in range(n_options) if j != c_new]
    # other_old is already in original relative order; map to other_new in order
    perm = [0] * n_options
    perm[c_old] = c_new
    for old, new in zip(other_old, other_new):
        perm[old] = new
    return perm


def _apply_permutation_to_options(options: list[str], perm: list[int]) -> list[str]:
    """Return new options list reordered by perm (perm[old_idx] = new_idx)."""
    new_options = [""] * len(options)
    for old_idx, new_idx in enumerate(perm):
        new_options[new_idx] = options[old_idx]
    return new_options


def _remap_explanation_letters(explanation: str, perm: list[int]) -> str:
    """Replace every 'Option X' canonical reference via a single-pass substitution.

    perm[old_idx] = new_idx where old_idx = ord(letter) - ord('A').
    The old->new letter map is built once, then applied atomically via re.sub
    to avoid double-remapping (e.g. A->C then C->A).
    """
    # Build letter -> letter map
    letter_map: dict[str, str] = {}
    for old_idx, new_idx in enumerate(perm):
        if old_idx >= 26 or new_idx >= 26:
            continue
        old_letter = chr(ord("A") + old_idx)
        new_letter = chr(ord("A") + new_idx)
        letter_map[old_letter] = new_letter

    def _replacer(m: re.Match) -> str:
        letter = m.group(1).upper()
        return f"Option {letter_map.get(letter, letter)}"

    return _CANONICAL_OPTION_REF.sub(_replacer, explanation)


# ---------------------------------------------------------------------------
# Validator pass-check (mirrors _validate_answer_position_balance logic)
# ---------------------------------------------------------------------------

def _group_passes_position_check(qs: list[dict]) -> bool:
    """Return True iff the group would pass _validate_answer_position_balance."""
    n = len(qs)
    is_sample = False  # caller ensures correct threshold
    if n == 0:
        return True
    counter = Counter(q["correct_option"] for q in qs)
    for pos, cnt in counter.items():
        if cnt / n > MAX_POSITION_SHARE:
            return False
    sorted_qs = sorted(qs, key=lambda q: (q.get("order") or 0))
    positions = [q["correct_option"] for q in sorted_qs]
    return not _has_run(positions)


# ---------------------------------------------------------------------------
# Main transform logic
# ---------------------------------------------------------------------------

def _run(apply: bool) -> None:
    records = _collect_file_records()
    groups = _build_groups(records)

    # Build a map: question_id -> question dict reference (for mutation in --apply)
    # We need to work on the actual dicts inside records so that file writes pick
    # up the changes.  Use object identity (id()) to track which qs were processed.
    # Actually simpler: store mutations as {qid: (new_options, new_correct_option,
    # new_explanation)} keyed globally.

    # For each group, determine target positions and build per-question mutations.
    # mutations[qid] = dict of fields to update
    mutations: dict[int, dict] = {}
    # Each entry: {id, track, reason, snippet}
    # reason is one of: "explanation-prose" | "letter-coupling" | "both"
    skipped_noncanonical: list[dict] = []
    skipped_ids: set[int] = set()

    MIN_N_PRACTICE = 10
    MIN_N_SAMPLE = 6

    # Sort groups for deterministic processing order
    for key in sorted(groups.keys()):
        qs = groups[key]
        is_sample = key[0] == "sample"
        min_n = MIN_N_SAMPLE if is_sample else MIN_N_PRACTICE
        if len(qs) < min_n:
            continue

        sorted_qs = sorted(qs, key=lambda q: (q.get("order") or 0))
        seed_str = f"{_SEED_BASE}:{'|'.join(str(k) for k in key)}"

        # --- Pre-scan for skippable questions BEFORE target assignment.
        # A question is skipped if EITHER the explanation-prose guard OR the
        # letter-coupling guard fires.  Skipped questions keep their current
        # position; targets are only assigned to the permutable subset so the
        # full balanced multiset is consumed without waste.
        for q in sorted_qs:
            explanation = q.get("explanation", "")
            prose_snippet = _find_noncanonical_snippet(explanation)
            coupling_snippet = _find_letter_coupling_snippet(q)

            if prose_snippet is not None or coupling_snippet is not None:
                qid = q.get("id")
                if prose_snippet is not None and coupling_snippet is not None:
                    reason = "both"
                    snippet = prose_snippet  # report the prose snippet for both
                elif prose_snippet is not None:
                    reason = "explanation-prose"
                    snippet = prose_snippet
                else:
                    reason = "letter-coupling"
                    snippet = coupling_snippet
                skipped_noncanonical.append({
                    "id": qid,
                    "track": key[1] if is_sample else key[0],
                    "reason": reason,
                    "snippet": snippet,
                })
                skipped_ids.add(qid)

        # Bucket permutable questions by option count (handles the lone 3-option
        # experimentation sample question alongside the standard 4-option ones).
        # Separately count locked/skipped positions so _build_balanced_targets
        # can produce skip-aware targets and keep the overall group <= 40%.
        option_count_buckets: dict[int, list[dict]] = defaultdict(list)
        locked_count_by_opts: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        for q in sorted_qs:
            n_opts_q = len(q["options"])
            if q.get("id") in skipped_ids:
                locked_count_by_opts[n_opts_q][q["correct_option"]] += 1
            else:
                option_count_buckets[n_opts_q].append(q)

        for n_opts, bucket_qs in sorted(option_count_buckets.items()):
            n_bucket = len(bucket_qs)
            bucket_seed = f"{seed_str}:opts{n_opts}"
            rng = random.Random(bucket_seed)
            locked = dict(locked_count_by_opts.get(n_opts, {}))
            targets = _build_balanced_targets(n_bucket, n_opts, rng, bucket_seed, bucket_qs, locked_counts=locked)

            for q, c_new in zip(bucket_qs, targets):
                qid = q.get("id")
                c_old = q["correct_option"]
                options = q["options"]
                explanation = q.get("explanation", "")

                # If already at target, no permutation needed
                if c_old == c_new:
                    continue

                perm = _build_permutation(c_old, c_new, n_opts)
                new_options = _apply_permutation_to_options(options, perm)
                new_explanation = _remap_explanation_letters(explanation, perm)

                mutations[qid] = {
                    "correct_option": c_new,
                    "options": new_options,
                    "explanation": new_explanation,
                }

    # -----------------------------------------------------------------------
    # Report (always printed, even in --apply mode)
    # -----------------------------------------------------------------------
    print("=" * 72)
    print("PHASE 1 POSITION REBALANCE — DRY RUN REPORT" if not apply else "PHASE 1 POSITION REBALANCE — APPLY MODE")
    print("=" * 72)
    print()

    # Per-group table
    print("PER-GROUP POSITION DISTRIBUTION (current → projected)")
    print("-" * 72)

    for key in sorted(groups.keys()):
        qs = groups[key]
        is_sample = key[0] == "sample"
        min_n = MIN_N_SAMPLE if is_sample else MIN_N_PRACTICE
        if len(qs) < min_n:
            continue

        n = len(qs)
        key_str = "/".join(str(k) for k in key)

        # Current distribution
        current_counts = Counter(q["correct_option"] for q in qs)

        # Projected distribution (apply mutations to a copy)
        projected_qs = []
        for q in qs:
            qid = q.get("id")
            if qid in mutations:
                proj_q = dict(q)
                proj_q["correct_option"] = mutations[qid]["correct_option"]
                projected_qs.append(proj_q)
            elif qid in skipped_ids:
                projected_qs.append(q)  # unchanged
            else:
                projected_qs.append(q)  # already at target or below min_n
        projected_counts = Counter(q["correct_option"] for q in projected_qs)

        current_pass = _group_passes_position_check(qs)
        projected_pass = _group_passes_position_check(projected_qs)

        def _fmt_dist(counts, total):
            parts = []
            for pos in range(4):
                cnt = counts.get(pos, 0)
                lbl = chr(ord("A") + pos)
                pct = cnt / total * 100 if total else 0
                parts.append(f"{lbl}:{cnt}({pct:.0f}%)")
            return "  ".join(parts)

        print(f"\n  GROUP: {key_str}  n={n}")
        print(f"  CURRENT  : {_fmt_dist(current_counts, n)}  {'PASS' if current_pass else 'FAIL'}")
        print(f"  PROJECTED: {_fmt_dist(projected_counts, n)}  {'PASS' if projected_pass else 'FAIL'}")

    print()
    print("=" * 72)
    print("SKIPPED (explanation-prose guard + letter-coupling guard)")
    print("-" * 72)
    if skipped_noncanonical:
        total_skipped = len(skipped_noncanonical)
        reason_counts: dict[str, int] = Counter(e["reason"] for e in skipped_noncanonical)
        track_counts: dict[str, int] = Counter(e["track"] for e in skipped_noncanonical)

        print(f"Total skipped: {total_skipped}")
        print(f"  By reason:")
        for reason in ("explanation-prose", "letter-coupling", "both"):
            cnt = reason_counts.get(reason, 0)
            if cnt:
                print(f"    {reason}: {cnt}")
        print(f"  By track:")
        for track, cnt in sorted(track_counts.items()):
            print(f"    {track}: {cnt}")
        print()
        print(f"  {'id':<10}  {'track':<20}  {'reason':<20}  snippet")
        print(f"  {'-'*10}  {'-'*20}  {'-'*20}  {'-'*30}")
        for entry in skipped_noncanonical:
            print(
                f"  {str(entry['id']):<10}  {entry['track']:<20}  "
                f"{entry['reason']:<20}  {entry['snippet']!r}"
            )
    else:
        print("None skipped — all questions are clean.")

    print()
    print("=" * 72)
    total_would_permute = len(mutations)
    total_would_skip = len(skipped_noncanonical)
    reason_counts_total: dict[str, int] = Counter(e["reason"] for e in skipped_noncanonical)
    print(f"TOTALS: would permute={total_would_permute}  would skip={total_would_skip}")
    print(f"  skip breakdown: explanation-prose={reason_counts_total.get('explanation-prose', 0)}  "
          f"letter-coupling={reason_counts_total.get('letter-coupling', 0)}  "
          f"both={reason_counts_total.get('both', 0)}")
    print("=" * 72)

    # -----------------------------------------------------------------------
    # Apply mutations to files (--apply only)
    # -----------------------------------------------------------------------
    if not apply:
        print("\nDRY RUN — no files written.")
        return

    # Apply mutations to in-memory question dicts
    for rec in records:
        changed = False
        for q in rec["questions"]:
            qid = q.get("id")
            if qid in mutations:
                m = mutations[qid]
                q["correct_option"] = m["correct_option"]
                q["options"] = m["options"]
                q["explanation"] = m["explanation"]
                changed = True
        if changed:
            # Build canonical JSON (ensure_ascii=False — safe post-normalization)
            content = json.dumps(rec["questions"], indent=2, ensure_ascii=False)
            if not content.endswith("\n"):
                content += "\n"
            rec["file_path"].write_text(content, encoding="utf-8")

            # POST-WRITE self-verification: re-read and assert deep equality.
            with rec["file_path"].open("r", encoding="utf-8") as fh:
                written_back = json.load(fh)
            if written_back != rec["questions"]:
                print(
                    f"ABORT: POST-WRITE VERIFICATION FAILED for {rec['file_path']}",
                    file=sys.stderr,
                )
                print(
                    "  The file as written does not deep-equal the in-memory "
                    "mutated question list.  No further files will be written.",
                    file=sys.stderr,
                )
                sys.exit(1)

            print(f"WROTE (verified): {rec['file_path']}")

    print("\nApply complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic MCQ position-debiasing transform (Phase 1)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print per-group stats and skipped list; write nothing (default).",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Rewrite JSON files in place after review.",
    )
    args = parser.parse_args()
    _run(apply=args.apply)


if __name__ == "__main__":
    main()
