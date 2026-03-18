from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from config import FRONTEND_DIST_DIR

router = APIRouter()


def _serve_frontend_path(asset_path: str) -> Response:
    if not FRONTEND_DIST_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend bundle not found")

    requested_path = (FRONTEND_DIST_DIR / asset_path).resolve()
    dist_root = FRONTEND_DIST_DIR.resolve()
    if requested_path.is_file() and requested_path.is_relative_to(dist_root):
        return FileResponse(requested_path)

    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index not found")
    return FileResponse(index_path)


@router.get("/")
def serve_frontend_root() -> Response:
    return _serve_frontend_path("index.html")


@router.get("/{asset_path:path}")
def serve_frontend(asset_path: str) -> Response:
    if asset_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_frontend_path(asset_path)
