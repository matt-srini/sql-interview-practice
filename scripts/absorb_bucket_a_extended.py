"""Absorb Bucket A.live extended-range (16-20) orphans into 4 target paths.

Per the path-size policy (default cap 15, exception 16-20 with explicit
approval), the user has authorized expanding these 4 paths:

  python-data data-cleaning:                 15 → 18 (+3)
  statistics applied-stats:                   8 → 18 (+10)
  experimentation experiment-design-and-power: 10 → 18 (+8)
  pyspark spark-memory-and-driver-executor:   6 → 12 (+6, safe-green)

All 27 orphans verified to align with each path's focus_concepts under
validator rule 5 (question-tag alignment). No question-content edits.

Re-runnable: idempotent (sorts + dedupes the resulting questions[]).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATHS_DIR = REPO / "backend" / "content" / "paths"

ABSORPTIONS: dict[str, list[int]] = {
    "data-cleaning": [33016, 33023, 33038],
    "applied-stats": [73002, 73006, 73007, 73008, 73018, 73027, 72011, 72012, 72013, 72023],
    "experiment-design-and-power": [91008, 91013, 91017, 91019, 91023, 92009, 92021, 92027],
    "spark-memory-and-driver-executor": [41032, 41034, 43002, 43013, 43046, 42010],
}


def execute():
    print("=== Bucket A.live extended-range absorption ===\n")
    for slug, new_qids in ABSORPTIONS.items():
        f = PATHS_DIR / f"{slug}.json"
        d = json.loads(f.read_text())
        before = list(d["questions"])
        merged = sorted(set(before) | set(new_qids))
        d["questions"] = merged
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        added = sorted(set(new_qids) - set(before))
        already = sorted(set(new_qids) & set(before))
        print(f"{slug}:")
        print(f"  before: {len(before)} Qs")
        print(f"  added:  {added}")
        if already:
            print(f"  skipped (already present): {already}")
        print(f"  after:  {len(merged)} Qs  (≤20 ceiling: {'✓' if len(merged) <= 20 else '✗'})")
        print()


if __name__ == "__main__":
    execute()
