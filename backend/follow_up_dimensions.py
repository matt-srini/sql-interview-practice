"""Canonical follow-up (chain pivot) dimensions for mock Interview Loop chains.

These are the universal interviewer-pivot taxonomy — the single axis a chain
follow-up escalates (see `docs/concept-taxonomy.md` § "The universal follow-up
dimensions"). There are 8 canonical dimensions.

Some chains in the bank (notably Data Engineering) authored the dimension without
the ``_pivot`` suffix (``data_quality`` instead of ``data_quality_pivot``). Those are
accepted as **aliases** and normalised to the canonical token, so analytics and
validation treat the two spellings as one dimension — no content edit required.
This is the machine source of truth; the frontend mirrors it in
``frontend/src/mockModeConfig.js`` (``FOLLOW_UP_DIMENSIONS`` + ``DIMENSION_ALIASES``).
"""
from __future__ import annotations

CANONICAL_FOLLOW_UP_DIMENSIONS: frozenset[str] = frozenset({
    "scale_pivot",
    "business_rule_pivot",
    "ambiguity_pivot",
    "edge_case_pivot",
    "performance_pivot",
    "data_quality_pivot",
    "stakeholder_pivot",
    "abstraction_pivot",
})

# `_pivot`-less spellings accepted as aliases of the canonical token.
FOLLOW_UP_DIMENSION_ALIASES: dict[str, str] = {
    "scale": "scale_pivot",
    "business_rule": "business_rule_pivot",
    "ambiguity": "ambiguity_pivot",
    "edge_case": "edge_case_pivot",
    "performance": "performance_pivot",
    "data_quality": "data_quality_pivot",
    "stakeholder": "stakeholder_pivot",
    "abstraction": "abstraction_pivot",
}


def canonical_dimension(token: str | None) -> str | None:
    """Normalise a ``follow_up_dimension`` to its canonical token, or ``None``.

    Returns the canonical ``*_pivot`` token for any canonical value or accepted
    alias; returns ``None`` for an empty or unrecognised token (callers treat
    ``None`` as "not a valid dimension").
    """
    if not token:
        return None
    resolved = FOLLOW_UP_DIMENSION_ALIASES.get(token, token)
    return resolved if resolved in CANONICAL_FOLLOW_UP_DIMENSIONS else None
