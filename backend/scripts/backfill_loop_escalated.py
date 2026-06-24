"""Backfill loop_escalated for existing interview_loop mock sessions.

For every interview_loop session where loop_escalated IS NULL, look up the
question_ids stored in mock_session_questions, resolve each question's
difficulty from the current in-memory catalog, and compute whether any
stored question's difficulty rank exceeds the session's declared difficulty
rank.  Then UPDATE mock_sessions.loop_escalated accordingly.

Safe to re-run: only rows where loop_escalated IS NULL are touched.

Usage:
    DATABASE_URL="postgresql://..." python scripts/backfill_loop_escalated.py

The orchestrator runs this script with DATABASE_URL pointing at either the
local dev DB or the production DB — this script never touches a DB itself
without that env var.
"""

import asyncio
import os
import sys

import asyncpg

# ---------------------------------------------------------------------------
# Catalog bootstrap — we need question difficulty from the same files the
# app uses.  Import the loaders directly (no FastAPI startup required).
# ---------------------------------------------------------------------------
# Add backend/ to sys.path so relative imports resolve.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from tracks import TRACKS

_DIFF_RANK: dict[str, int] = {"easy": 0, "medium": 1, "hard": 2}

# ---------------------------------------------------------------------------
# Build a global id→difficulty lookup across all tracks
# ---------------------------------------------------------------------------

def _build_id_to_difficulty() -> dict[int, str]:
    """Map every question id → its difficulty, across all tracks (practice + mock).

    IDs are globally unique across tracks (TXNNN scheme), so a flat id→difficulty
    map is unambiguous. Uses the same catalog loaders the app uses.
    """
    mapping: dict[int, str] = {}
    for t in TRACKS:
        cat = t.catalog_module
        for getter in ("get_questions_by_difficulty", "get_mock_questions_by_difficulty"):
            fn = getattr(cat, getter, None)
            if fn is None:
                continue
            for diff, qs in fn().items():
                for q in qs:
                    mapping[int(q["id"])] = q.get("difficulty", diff)
    return mapping


# ---------------------------------------------------------------------------
# Async backfill
# ---------------------------------------------------------------------------

async def run_backfill(database_url: str) -> None:
    # Strip SQLAlchemy dialect prefixes so asyncpg can parse the DSN directly
    url = database_url
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            url = "postgresql://" + url[len(prefix):]
            break

    id_to_diff = _build_id_to_difficulty()
    print(f"Catalog loaded: {len(id_to_diff)} questions indexed")

    conn = await asyncpg.connect(url)
    try:
        # Fetch all interview_loop sessions with NULL loop_escalated
        sessions = await conn.fetch(
            """
            SELECT ms.id AS session_id, ms.difficulty,
                   array_agg(msq.question_id ORDER BY msq.position) AS question_ids
            FROM mock_sessions ms
            JOIN mock_session_questions msq ON msq.session_id = ms.id
            WHERE ms.mode = 'interview_loop'
              AND ms.loop_escalated IS NULL
            GROUP BY ms.id, ms.difficulty
            """
        )
        print(f"Sessions to backfill: {len(sessions)}")

        updated = 0
        for row in sessions:
            session_id = row["session_id"]
            difficulty = row["difficulty"] or "medium"
            question_ids: list[int] = list(row["question_ids"])

            sess_rank = _DIFF_RANK.get(difficulty, 1)
            escalated = any(
                _DIFF_RANK.get(id_to_diff.get(qid, difficulty), sess_rank) > sess_rank
                for qid in question_ids
            )

            await conn.execute(
                "UPDATE mock_sessions SET loop_escalated = $1 WHERE id = $2",
                escalated,
                session_id,
            )
            updated += 1

        print(f"Updated {updated} session(s)")
    finally:
        await conn.close()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set", file=sys.stderr)
        sys.exit(1)
    asyncio.run(run_backfill(database_url))


if __name__ == "__main__":
    main()
