from typing import Any

from fastapi import APIRouter, Depends

from db import get_submissions
from deps import get_current_user

router = APIRouter()


@router.get("/api/submissions")
async def list_submissions(
    track: str,
    question_id: int,
    limit: int = 5,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await get_submissions(
        user_id=current_user["id"],
        track=track,
        question_id=question_id,
        limit=min(limit, 20),
    )
