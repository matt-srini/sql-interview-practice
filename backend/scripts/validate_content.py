from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from backend/ as `python scripts/validate_content.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from path_loader import get_all_paths
from pyspark_questions import get_questions_by_difficulty as get_pyspark_by_difficulty
from python_data_questions import get_questions_by_difficulty as get_python_data_by_difficulty
from python_questions import get_questions_by_difficulty as get_python_by_difficulty
from questions import get_questions_by_difficulty


BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _load_json_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def main() -> None:
    # Validate all raw JSON files parse cleanly.
    content_dirs = [
        BACKEND_ROOT / "content" / "questions",
        BACKEND_ROOT / "content" / "python_questions",
        BACKEND_ROOT / "content" / "python_data_questions",
        BACKEND_ROOT / "content" / "pyspark_questions",
        BACKEND_ROOT / "content" / "paths",
    ]
    for content_dir in content_dirs:
        for file_path in sorted(content_dir.glob("*.json")):
            _load_json_file(file_path)

    # Validate loader-level schemas and references.
    get_questions_by_difficulty()
    get_python_by_difficulty()
    get_python_data_by_difficulty()
    get_pyspark_by_difficulty()
    get_all_paths()

    print("Content validation passed")


if __name__ == "__main__":
    main()
