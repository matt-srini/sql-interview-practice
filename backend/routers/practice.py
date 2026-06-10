"""
GET /api/practice/drill — Concept drill: all PRACTICE questions for one concept family.

Pro/Elite only.  Returns every practice question in the requested track whose
concept tags resolve to the same family as the supplied concept name, ordered
unsolved-first → easy→hard → order ascending (a drill leads with the questions
you haven't mastered yet; solved questions trail at the end for review).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from concept_families import concept_matches_focus
from db import get_solved_ids
from deps import get_current_user
from tracks import TRACKS
from unlock import normalize_plan

router = APIRouter()

_TRACK_BY_SLUG: dict[str, Any] = {t.slug: t for t in TRACKS}

_DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}


@router.get("/api/practice/drill")
async def concept_drill(
    track: str,
    concept: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return all practice questions in *track* that exercise *concept*.

    Query parameters
    ----------------
    track   : URL slug (e.g. "pandas", "sql", "data-engineering")
    concept : Concept family name (e.g. "GROUPED AGGREGATION").  Matched via
              the same family-aware resolver used by the mock focus_concepts filter.

    Access
    ------
    Requires Pro or Elite plan.  Returns 403 for Free users.

    Response
    --------
    {
      "track": str,
      "track_label": str,
      "concept": str,
      "total": int,
      "solved_count": int,
      "questions": [
        {
          "id": int,
          "title": str,
          "difficulty": str,
          "order": int,
          "concepts": list[str],
          "state": "solved" | "unlocked"
        },
        ...
      ]
    }

    Questions are ordered: unsolved before solved; within each group
    easy → medium → hard; ties broken by ascending order field.  A drill leads
    with the questions you haven't mastered yet, so the entry point (the first
    unsolved question, chosen by AppShell) lands at position 1.
    An empty match set is not an error (total=0, questions=[]).
    """
    plan = normalize_plan(current_user.get("plan", "free"))
    if plan not in ("pro", "elite"):
        raise HTTPException(status_code=403, detail="Concept drills are a Pro feature.")

    track_cfg = _TRACK_BY_SLUG.get(track)
    if track_cfg is None:
        raise HTTPException(status_code=404, detail="Unknown track")

    grouped = track_cfg.catalog_module.get_questions_by_difficulty()
    solved = await get_solved_ids(current_user["id"], topic=track_cfg.db_topic)

    questions: list[dict[str, Any]] = []
    for difficulty, qs in grouped.items():
        for q in qs:
            tags = q.get("concepts", [])
            if any(concept_matches_focus(tag, concept, track) for tag in tags):
                qid = int(q["id"])
                state = "solved" if qid in solved else "unlocked"
                questions.append(
                    {
                        "id": qid,
                        "title": q["title"],
                        "difficulty": difficulty,
                        "order": int(q.get("order", 0)),
                        "concepts": tags,
                        "state": state,
                    }
                )

    # Unsolved-first (the point of a drill is the questions you haven't mastered),
    # then easy→hard, then by order. Solved questions trail at the end for review.
    questions.sort(
        key=lambda q: (
            0 if q["state"] == "unlocked" else 1,
            _DIFFICULTY_RANK.get(q["difficulty"], 99),
            q["order"],
        )
    )

    solved_count = sum(1 for q in questions if q["state"] == "solved")

    return {
        "track": track,
        "track_label": track_cfg.label,
        "concept": concept,
        "total": len(questions),
        "solved_count": solved_count,
        "questions": questions,
    }
