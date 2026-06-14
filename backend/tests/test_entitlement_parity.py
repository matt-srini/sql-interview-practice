"""
Entitlement parity guard — CLAUDE.md § "Linked-docs / single-SoT rule".

The free-tier unlock numbers shown in the frontend display source
(frontend/src/data/tierFeatures.js → FREE_UNLOCK) must agree with the CANONICAL
thresholds enforced in backend/unlock.py. If a render drifts from the source,
these tests fail — so the /pricing page (and the docs that mirror it) can never
silently disagree with what the backend actually enforces.

This is the automated backstop the unlock.py / tierFeatures.js headers reference:
change the numbers in unlock.py, and the render is *required* to follow.
"""
import re
from pathlib import Path

from unlock import (
    _FREE_MEDIUM_THRESHOLDS_CODE,
    _FREE_HARD_THRESHOLDS_CODE,
    FREE_HARD_CAP_CODE,
    _FREE_MEDIUM_THRESHOLDS_MCQ,
    _FREE_HARD_THRESHOLDS_MCQ,
    FREE_HARD_CAP_MCQ,
)

_REPO = Path(__file__).resolve().parents[2]
_TIER_FEATURES = (_REPO / "frontend" / "src" / "data" / "tierFeatures.js").read_text(encoding="utf-8")


def _group_block(label: str) -> str:
    """The FREE_UNLOCK group object text for a given label (e.g. 'Code tracks')."""
    start = _TIER_FEATURES.index(f"label: '{label}'")
    tail = _TIER_FEATURES[start:]
    nxt = tail.find("label: '", 1)
    block = tail if nxt == -1 else tail[:nxt]
    assert "medium:" in block and "hard:" in block, f"could not isolate the {label!r} FREE_UNLOCK block"
    return block


def _display_medium(block: str) -> dict[int, int | None]:
    """{easy_solved: medium_unlocked | None} from the displayed medium ladder ('all' → None)."""
    pairs = re.findall(r"\['Solve (\d+) easy',\s*'(\d+|all) medium open'\]", block)
    assert pairs, "no medium ladder rows parsed"
    return {int(n): (None if to == "all" else int(to)) for n, to in pairs}


def _display_hard(block: str) -> dict[int, int]:
    """{medium_solved: hard_unlocked} from the displayed hard ladder."""
    pairs = re.findall(r"\['Solve (\d+) medium',\s*'(\d+) hard open'\]", block)
    assert pairs, "no hard ladder rows parsed"
    return {int(n): int(to) for n, to in pairs}


def _display_cap(block: str) -> int:
    m = re.search(r"capped at (\d+) per track", block)
    assert m, "no 'capped at N per track' line found"
    return int(m.group(1))


def _src(table) -> dict[int, int | None]:
    return {threshold: unlocked for threshold, unlocked in table}


# ── Medium ladders must equal the source exactly ──────────────────────────────
def test_code_medium_ladder_matches_unlock_py():
    assert _display_medium(_group_block("Code tracks")) == _src(_FREE_MEDIUM_THRESHOLDS_CODE)


def test_mcq_medium_ladder_matches_unlock_py():
    assert _display_medium(_group_block("Conceptual tracks")) == _src(_FREE_MEDIUM_THRESHOLDS_MCQ)


# ── Hard caps must match the source ───────────────────────────────────────────
def test_hard_caps_match_unlock_py():
    assert _display_cap(_group_block("Code tracks")) == FREE_HARD_CAP_CODE
    assert _display_cap(_group_block("Conceptual tracks")) == FREE_HARD_CAP_MCQ


# ── Hard ladders: each displayed tier == source unlock clamped to the cap ──────
# (The display deliberately omits cap-clamped-redundant top tiers, e.g. code's
# "22 medium → 15" collapses into the 8-cap, so we check membership + clamp, not
# set equality.)
def test_code_hard_ladder_matches_source_clamped():
    src = _src(_FREE_HARD_THRESHOLDS_CODE)
    shown = _display_hard(_group_block("Code tracks"))
    for threshold, hard_open in shown.items():
        assert threshold in src, f"displayed hard tier {threshold} not enforced in unlock.py"
        assert hard_open == min(src[threshold], FREE_HARD_CAP_CODE)
    assert max(shown.values()) == FREE_HARD_CAP_CODE, "displayed hard ladder never reaches the cap"


def test_mcq_hard_ladder_matches_source_clamped():
    src = _src(_FREE_HARD_THRESHOLDS_MCQ)
    shown = _display_hard(_group_block("Conceptual tracks"))
    for threshold, hard_open in shown.items():
        assert threshold in src, f"displayed hard tier {threshold} not enforced in unlock.py"
        assert hard_open == min(src[threshold], FREE_HARD_CAP_MCQ)
    assert max(shown.values()) == FREE_HARD_CAP_MCQ, "displayed hard ladder never reaches the cap"
