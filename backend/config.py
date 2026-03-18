import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", BACKEND_DIR.parent / "frontend" / "dist"))
