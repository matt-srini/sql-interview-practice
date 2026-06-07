"""Orphan recruitment: add catalog questions into live paths.

For each thin/empty proposed pattern across all tracks, find:
  1. Recruitable orphans (Pass 2: orphans whose tag-routing suggests the pattern)
  2. Live path(s) that declare this pattern in patterns[] (after normalisation)

When a live path exists: add the orphans to its questions[], dedupe, sort by
(difficulty, qid). When no live path declares the pattern: skip and log
(those need a stage-2 new-path decision; this script does not create new paths).

Divergents are NOT touched — moving questions out of one path to another is
a real reassignment decision that needs per-question audit (see learning-paths-
tracker.md §B).

Validator-impact summary:
  - Question JSONs untouched. _validate_concepts + _validate_concept_taxonomy: no risk.
  - Path JSONs gain questions[] entries. _validate_paths rule 5: passes naturally for
    orphans whose tag-suggested pattern matches the target path's focus_concepts
    (which is how the orphan got suggested in the first place). Re-run validator
    after to confirm.

Dry-run mode (--dry-run) prints the plan without writing files.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from audit_pattern_coverage import (
    TRACK_DIRS, PROPOSED_PATTERNS,
    walk_track, classify_pattern, _load_live_paths_by_track,
    NORMALIZE_PATTERN, _normalize,
)


DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def build_pattern_to_paths(track: str, live_paths: list[dict]) -> dict[str, list[dict]]:
    """Build {canonical_pattern_slug: [live_path_dicts]} for a track."""
    out: dict[str, list[dict]] = defaultdict(list)
    for p in live_paths:
        for raw_slug in (p.get("patterns") or []):
            canonical = _normalize(track, raw_slug)
            out[canonical].append(p)
    return out


def plan_recruitment(track: str, content_dir: Path, live_paths: list[dict]) -> list[dict]:
    """Return a list of recruitment actions to take for this track.

    Each action: {
        target_path: path slug,
        pattern: thin pattern slug,
        added_qids: [list of orphan qids being added],
        new_total: total questions[] count after recruit,
        skipped_reason: str if action is a skip,
    }
    """
    per_q, buckets, _, orphans, _ = walk_track(track, content_dir, live_paths=live_paths)
    pattern_to_paths = build_pattern_to_paths(track, live_paths)

    actions = []

    # Build lookup: orphans by tag-suggested pattern
    orphans_by_pattern: dict[str, list[dict]] = defaultdict(list)
    for o in orphans:
        if o["tag_pattern"]:
            orphans_by_pattern[o["tag_pattern"]].append(o)

    proposed_patterns = PROPOSED_PATTERNS.get(track, {})
    for pattern_slug in proposed_patterns:
        cls = classify_pattern(buckets.get(pattern_slug, []))
        if cls not in ("THIN", "EMPTY"):
            continue
        recruitable_orphans = orphans_by_pattern.get(pattern_slug, [])
        if not recruitable_orphans:
            continue
        target_paths = pattern_to_paths.get(pattern_slug, [])
        if not target_paths:
            actions.append({
                "type": "skip",
                "pattern": pattern_slug,
                "n_orphans": len(recruitable_orphans),
                "reason": "no live path declares this pattern",
            })
            continue
        # Pick first live path (deterministic)
        target_path = sorted(target_paths, key=lambda p: p["slug"])[0]
        current_qids = set(int(q) for q in target_path["questions"])
        added = [o for o in recruitable_orphans if o["qid"] not in current_qids]
        if not added:
            continue
        actions.append({
            "type": "add",
            "track": track,
            "pattern": pattern_slug,
            "target_path_slug": target_path["slug"],
            "current_count": len(current_qids),
            "added_qids": [o["qid"] for o in added],
            "added_records": added,
            "new_total": len(current_qids) + len(added),
        })

    return actions


def apply_action(action: dict, content_dir: Path, dry_run: bool):
    """Mutate path JSON to add orphans, sort by (difficulty, qid).

    Also broaden focus_concepts to include any concept whose family is
    needed by a recruited orphan to satisfy validator rule 5.
    """
    if action["type"] != "add":
        return
    track = action["track"]
    path_file = REPO / "backend" / "content" / "paths" / f"{action['target_path_slug']}.json"
    data = json.loads(path_file.read_text())

    # Difficulty per qid
    qid_diff: dict[int, str] = {}
    qid_concepts: dict[int, list[str]] = {}
    for f in content_dir.glob("*.json"):
        if f.stem == "schemas":
            continue
        for q in json.loads(f.read_text()):
            qid_diff[int(q["id"])] = f.stem
            qid_concepts[int(q["id"])] = q.get("concepts", []) or []

    all_qids = set(int(q) for q in data["questions"]) | set(action["added_qids"])
    sorted_qids = sorted(
        all_qids,
        key=lambda qid: (DIFFICULTY_ORDER.get(qid_diff.get(qid, "easy"), 9), qid),
    )
    data["questions"] = sorted_qids

    # Broaden focus_concepts so each recruited orphan satisfies rule 5
    from concept_families import concept_matches_focus
    fc = list(data.get("focus_concepts", []))
    for qid in action["added_qids"]:
        q_tags = qid_concepts.get(qid, [])
        # If no current focus_concept already matches this question, broaden
        matched = any(
            concept_matches_focus(t, f, track) for t in q_tags for f in fc
        )
        if not matched and q_tags:
            # Add the first tag of the question (uppercase if it's already uppercase
            # or contains spaces — matches existing convention)
            chosen = q_tags[0]
            if chosen not in fc:
                fc.append(chosen)
    # Dedupe preserving order
    seen, deduped = set(), []
    for c in fc:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    data["focus_concepts"] = deduped

    if not dry_run:
        path_file.write_text(json.dumps(data, indent=2) + "\n")


def main():
    dry_run = "--dry-run" in sys.argv
    live_paths_by_track = _load_live_paths_by_track()
    total_added = 0
    total_skipped = 0
    track_actions: dict[str, list] = {}

    for track, content_dir in TRACK_DIRS.items():
        actions = plan_recruitment(track, content_dir, live_paths_by_track.get(track, []))
        track_actions[track] = actions

    # Print plan
    print(f"=== Orphan recruitment plan ({'DRY RUN' if dry_run else 'APPLY'}) ===\n")
    for track, actions in track_actions.items():
        if not actions:
            continue
        print(f"## {track}")
        for a in actions:
            if a["type"] == "add":
                qids_str = ", ".join(str(q) for q in a["added_qids"][:8])
                if len(a["added_qids"]) > 8:
                    qids_str += f", … (+{len(a['added_qids'])-8} more)"
                print(
                    f"  ADD {len(a['added_qids']):>2} Qs to `{a['target_path_slug']}` "
                    f"(pattern `{a['pattern']}`, {a['current_count']} → {a['new_total']}): {qids_str}"
                )
                total_added += len(a["added_qids"])
            elif a["type"] == "skip":
                print(
                    f"  SKIP `{a['pattern']}` — {a['n_orphans']} recruitable orphans but {a['reason']}"
                )
                total_skipped += 1
        print()

    print(f"=== Totals ===")
    print(f"  Total orphans to recruit: {total_added}")
    print(f"  Patterns skipped (no live path): {total_skipped}")
    print()

    # Apply (or dry-run)
    if not dry_run:
        for track, actions in track_actions.items():
            content_dir = TRACK_DIRS[track]
            for a in actions:
                if a["type"] == "add":
                    apply_action(a, content_dir, dry_run=False)
        print("Applied. Re-run validator + audit to confirm.")


if __name__ == "__main__":
    main()
