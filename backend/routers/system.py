from typing import Any

from fastapi import APIRouter

from database import get_loaded_tables
from db import ping

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, Any]:
    postgres_ok = await ping()
    tables_loaded = get_loaded_tables()
    if not postgres_ok or not tables_loaded:
        return {
            "status": "unhealthy",
            "postgres": postgres_ok,
            "tables_loaded": tables_loaded,
        }
    return {
        "status": "healthy",
        "postgres": True,
        "tables_loaded": tables_loaded,
    }
