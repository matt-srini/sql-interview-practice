"""Learning path catalog loaded from JSON config files."""

import json
from pathlib import Path
from typing import Optional

PATHS_DIR = Path(__file__).parent / "content" / "paths"


def get_all_paths() -> list[dict]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(PATHS_DIR.glob("*.json"))
    ]


def get_path(slug: str) -> Optional[dict]:
    f = PATHS_DIR / f"{slug}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
