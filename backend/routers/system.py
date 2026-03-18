from typing import Any

from fastapi import APIRouter

from database import get_loaded_tables

router = APIRouter()


@router.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "tables_loaded": get_loaded_tables(),
    }
