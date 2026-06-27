from __future__ import annotations

from typing import Any

VALID_INTERACTION_MODES = {
    "executable_problem_solving",
    "code_adjacent_reasoning",
    "constructed_reasoning",
}


def derive_interaction_mode(track: str, question: dict[str, Any]) -> str:
    if track == "statistics":
        return (
            "executable_problem_solving"
            if question.get("subtype") == "numerical"
            else "constructed_reasoning"
        )

    if track == "pyspark":
        return "code_adjacent_reasoning"

    if track in {
        "data-engineering",
        "data-modeling",
        "ml-fundamentals",
        "experimentation",
        "product-sense",
    }:
        return "constructed_reasoning"

    raise ValueError(f"Unsupported interaction_mode track: {track}")


def resolve_interaction_mode(track: str, question: dict[str, Any]) -> str:
    derived_mode = derive_interaction_mode(track, question)
    supplied_mode = question.get("interaction_mode")

    if supplied_mode is None:
        return derived_mode

    if supplied_mode not in VALID_INTERACTION_MODES:
        raise ValueError(
            f"Invalid interaction_mode: {supplied_mode}, must be one of {sorted(VALID_INTERACTION_MODES)}"
        )

    if supplied_mode != derived_mode:
        raise ValueError(
            f"Invalid interaction_mode: {supplied_mode}, must resolve to {derived_mode} for this question"
        )

    return supplied_mode