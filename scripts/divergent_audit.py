"""Per-question divergent audit + action engine.

Classifies every divergent question into one of four buckets and takes
the appropriate action:

  B1 — Genuinely not this pattern.
       Question is in path X but its tags don't fit X at all. Audit's
       tag-routing is right; live path mis-curated. **No action** (the
       cohort 11014 case — basic date filter forced into cohort path).

  B2 — Use-case framed borderline.
       Question has the path's pattern tag AND the tag-suggested
       alternative. Either is honest. **Move ONLY if destination is
       thin** — recruiting it strengthens an under-covered pattern.
       Else leave alone.

  B3 — Routing rule gap.
       Two analytical tags compete; current ANALYTICAL_PRIORITY didn't
       resolve the tie correctly. **Update ANALYTICAL_PRIORITY** for
       the track. Question stays put; just script changes.

  B4 — Tag gap.
       Question is in path X but lacks the canonical tag for X's
       pattern. **Add the missing canonical tag** so tag-routing aligns.

Classification heuristic (best-effort; reviews on apply):

  has_attr_tag   = any of Q's tags resolves to a family that routes
                   to the live-path's attributed pattern
  has_dest_tag   = any of Q's tags routes to the tag-suggested pattern
                   (always True by definition since tag_pattern is
                   derived from a tag)
  both_analytical= attributed_pattern AND tag_pattern both ∈
                   ANALYTICAL_PATTERNS[track]

  if not has_attr_tag        → B4  (tag gap; add canonical attr tag)
  elif both_analytical       → B3  (analytical-vs-analytical priority)
  else                       → B2  (use-case framed; check dest thin)

The classifier is conservative: B1 is rare and hard to detect
automatically, so most "no canonical tag" cases go to B4. Author review
on commit catches B1 false positives (the divergence remains visible
in the audit doc post-action; if a B4 add was wrong, revert it).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from concept_families import resolve_to_family, concept_matches_focus
from audit_pattern_coverage import (
    TRACK_DIRS, ROUTING, ANALYTICAL_PATTERNS, ANALYTICAL_PRIORITY,
    walk_track, classify_pattern, _load_live_paths_by_track,
)


def reverse_routes(track: str) -> dict[str, list[str]]:
    """Return {pattern: [families that route to it]} for a track."""
    out: dict[str, list[str]] = defaultdict(list)
    for fam, pat in ROUTING.get(track, {}).items():
        if pat is not None:
            out[pat].append(fam)
    return out


def canonical_tag_for_pattern(track: str, pattern: str) -> str | None:
    """Return the canonical family tag that routes to this pattern."""
    rev = reverse_routes(track)
    families = rev.get(pattern, [])
    return families[0] if families else None


# Per-pattern keyword guards. A B4 add-tag action is only applied when the
# question's title contains at least one of these keywords for the path's
# pattern — otherwise the question is treated as B1 (genuinely not this pattern)
# and left alone. Cost asymmetry: false-B4 pollutes question tags; false-B1
# just leaves a benign divergence in the audit.
PATTERN_KEYWORDS: dict[str, list[str]] = {
    # SQL analytical patterns
    "cohort-and-retention": ["cohort", "retention", "churn", "reactivat", "returning", "dormant", "lifecycle"],
    "funnel-and-event-analysis": ["funnel", "conversion", "session", "journey", "drop-off", "dropoff", "step"],
    "period-over-period": ["monthly", "quarterly", "weekly", "yoy", "mom", "trend", "growth", "period"],
    "top-n-and-ranking": ["top", "rank", "highest", "lowest", "best", "worst", "max", "leader"],
    "pivot-and-unpivot": ["pivot", "unpivot", "cross-tab", "crosstab", "by category", "band"],
    # SQL construct patterns (only fire B4 when title obviously needs the construct)
    "window-functions": ["window", "running", "moving", "lag", "lead", "rank", "row_number"],
    "subqueries": ["subquery", "nested", "exists", "in (select"],
    "ctes-and-recursion": ["recursive", "cte", "hierarchy", "parent-child"],
    "set-operations": ["union", "intersect", "except"],
    "string-and-text": ["substring", "string", "regex", "trim", "parse", "extract", "concat"],
    "date-and-time": ["date", "timezone", "truncate", "datetime", "interval"],
    # Pandas analytical
    "customer-analytics": ["cohort", "retention", "churn", "lifecycle", "ltv", "rfm", "engagement"],
    "data-cleaning": ["missing", "deduplicat", "null", "clean", "fill", "bin", "categoriz", "fix", "drop"],
    # Python
    "data-pipeline-scripting": ["csv", "json", "log", "parse", "chunk", "extract"],
    "graph-traversal": ["graph", "tree", "node", "edge", "bfs", "dfs", "path"],
    # Data Engineering
    "etl-elt": ["etl", "elt", "pipeline", "extract", "transform", "load", "ingest"],
    "data-quality-and-incident-response": ["incident", "quality", "anomal", "alert", "freshness"],
    # Statistics
    "descriptive-stats": ["mean", "median", "variance", "std", "summary", "describe", "distribution shape"],
    "hypothesis-testing": ["hypothesis", "p-value", "t-test", "chi-squared", "significance", "test"],
    "confidence-intervals": ["confidence", "interval", "margin", "estimate"],
    "regression-and-correlation": ["regression", "correlation", "causality", "ols", "logistic"],
    "probability-and-combinatorics": ["probability", "combinatorics", "permutation", "combination", "bayes"],
    # ML
    "supervised-unsupervised": ["supervised", "unsupervised", "classification", "regression", "clustering"],
    "bias-variance": ["bias", "variance", "overfit", "underfit"],
    "cross-validation": ["cross-validation", "cross validation", "k-fold", "train-test", "split"],
    "metrics": ["metric", "accuracy", "precision", "recall", "f1", "auc", "roc", "mse", "mae", "loss"],
    "regularization": ["regulari"],
    "ensembles": ["ensemble", "boost", "bagging", "random forest", "stacking"],
    "missing-data-and-preprocessing": ["missing", "imputation", "mcar", "mar", "mnar", "preprocess"],
    "feature-engineering": ["feature scaling", "feature selection", "feature importance", "scaling", "normaliz", "standardiz"],
    "class-imbalance": ["imbalance", "smote", "threshold", "class weight"],
    "production-and-monitoring": ["monitoring", "drift", "production", "training-serving", "deployment"],
    # Experimentation
    "ab-test-mechanics": ["a/b", "ab test", "randomization", "assignment"],
    "power-and-sample-size": ["power", "sample size", "mde", "duration"],
    "variance-reduction": ["variance reduction", "cuped", "stratif"],
    "behavioral-effects-and-interference": ["novelty", "network", "switchback", "interference", "spillover"],
    "subgroup-and-hte": ["subgroup", "segment", "heterogeneous", "simpson", "interaction"],
    "causal-inference": ["causal", "instrumental", "iv", "did", "regression discontinuity"],
    # PySpark
    "spark-basics": ["lazy", "transformation", "action", "rdd", "dataframe basics"],
    "spark-performance": ["partition", "shuffle", "broadcast", "performance"],
    "spark-joins-and-skew": ["skew", "join", "broadcast"],
    "streaming": ["streaming", "watermark", "structured streaming"],
    "delta-lake": ["delta", "merge", "time travel", "z-order"],
    "query-optimization": ["catalyst", "aqe", "physical plan", "optimization"],
}


def classify_divergent(track: str, record: dict) -> str:
    """Return 'B1', 'B2', 'B3', or 'B4' for a divergent record."""
    routes = ROUTING.get(track, {})
    analytical = ANALYTICAL_PATTERNS.get(track, set())

    attr_pattern = record["attributed_pattern"]
    tag_pattern = record["tag_pattern"]
    concepts = record["concepts"]
    title_lower = record["title"].lower()

    rev = reverse_routes(track)
    attr_families = set(rev.get(attr_pattern, []))

    q_families = {
        resolve_to_family(c, track) for c in concepts if isinstance(c, str)
    }

    has_attr_tag = bool(q_families & attr_families)
    both_analytical = (attr_pattern in analytical) and (tag_pattern in analytical)

    if not has_attr_tag:
        # B4 candidate, but only confident if title contains a keyword for attr_pattern.
        # Else demote to B1 (genuinely not this pattern; mis-curated).
        keywords = PATTERN_KEYWORDS.get(attr_pattern, [])
        if any(kw in title_lower for kw in keywords):
            return "B4"
        return "B1"
    elif both_analytical:
        return "B3"
    else:
        return "B2"


def main():
    dry_run = "--dry-run" in sys.argv
    apply_b2 = "--no-b2" not in sys.argv  # default: apply B2 moves
    apply_b3 = "--no-b3" not in sys.argv  # default: apply B3 priority adjustments
    apply_b4 = "--no-b4" not in sys.argv  # default: apply B4 tag additions

    live_paths_by_track = _load_live_paths_by_track()
    actions = {
        "B1": [],  # (track, qid, reason)
        "B2_move": [],  # (track, qid, from_path, to_pattern)
        "B2_skip": [],  # (track, qid, reason)
        "B3_priority": defaultdict(list),  # {track: [(attr_pattern, dest_pattern)]}
        "B4_addtag": [],  # (track, qid, tag_to_add)
    }
    by_track_counters = defaultdict(Counter)

    # Pre-compute pattern coverage per track to know what's thin
    track_buckets: dict[str, dict] = {}
    for track, content_dir in TRACK_DIRS.items():
        _, buckets, _, _, _ = walk_track(
            track, content_dir, live_paths=live_paths_by_track.get(track, [])
        )
        track_buckets[track] = buckets

    # Collect divergents + classify
    for track, content_dir in TRACK_DIRS.items():
        _, _, _, _, divergences = walk_track(
            track, content_dir, live_paths=live_paths_by_track.get(track, [])
        )
        for d in divergences:
            bucket = classify_divergent(track, d)
            by_track_counters[track][bucket] += 1

            if bucket == "B1":
                actions["B1"].append((track, d["qid"], d["title"]))
            elif bucket == "B2":
                # Check if destination pattern's live path is thin
                dest_pattern = d["tag_pattern"]
                dest_buckets = track_buckets[track].get(dest_pattern, [])
                dest_is_thin = classify_pattern(dest_buckets) in ("THIN", "EMPTY")
                # Also: dest pattern must have a live path
                dest_has_path = any(
                    dest_pattern in (p.get("patterns") or [])
                    for p in live_paths_by_track.get(track, [])
                )
                if dest_is_thin and dest_has_path:
                    actions["B2_move"].append(
                        (track, d["qid"], d["live_path"], dest_pattern, d["title"])
                    )
                else:
                    reason = "dest healthy" if not dest_is_thin else "no live path for dest"
                    actions["B2_skip"].append(
                        (track, d["qid"], reason, d["title"])
                    )
            elif bucket == "B3":
                actions["B3_priority"][track].append(
                    (d["attributed_pattern"], d["tag_pattern"])
                )
            elif bucket == "B4":
                tag = canonical_tag_for_pattern(track, d["attributed_pattern"])
                if tag:
                    actions["B4_addtag"].append(
                        (track, d["qid"], tag, d["title"], d["concepts"])
                    )

    # Print classification summary
    print("=== Divergent classification ===")
    print(f"{'Track':<20} {'B1':>5} {'B2':>5} {'B3':>5} {'B4':>5} {'Total':>7}")
    print("-" * 55)
    total = Counter()
    for track, c in by_track_counters.items():
        b1, b2, b3, b4 = c["B1"], c["B2"], c["B3"], c["B4"]
        t = b1 + b2 + b3 + b4
        print(f"{track:<20} {b1:>5} {b2:>5} {b3:>5} {b4:>5} {t:>7}")
        for k in ("B1", "B2", "B3", "B4"):
            total[k] += c[k]
    print("-" * 55)
    print(f"{'TOTAL':<20} {total['B1']:>5} {total['B2']:>5} {total['B3']:>5} {total['B4']:>5} {sum(total.values()):>7}")
    print()

    print(f"=== Actions ({'DRY RUN' if dry_run else 'APPLY'}) ===\n")

    # B1 — no action, just report
    print(f"B1 (no action): {len(actions['B1'])} questions left as-is\n")

    # B2 — moves
    n_move = len(actions["B2_move"])
    n_skip = len(actions["B2_skip"])
    print(f"B2 (use-case framed): {n_move} moves, {n_skip} skipped (dest healthy or no live path)")
    if not dry_run and apply_b2 and n_move > 0:
        # Apply moves: remove qid from source path, add to dest path
        for track, qid, from_path, dest_pattern, title in actions["B2_move"]:
            # Find dest live path
            dest_paths = [
                p for p in live_paths_by_track[track]
                if dest_pattern in (p.get("patterns") or [])
            ]
            if not dest_paths:
                print(f"   skip {qid} ({track}): no dest path for {dest_pattern}")
                continue
            dest_path = sorted(dest_paths, key=lambda p: p["slug"])[0]
            # Update source path
            src_file = REPO / "backend" / "content" / "paths" / f"{from_path}.json"
            src_data = json.loads(src_file.read_text())
            if qid in src_data["questions"]:
                src_data["questions"] = [q for q in src_data["questions"] if q != qid]
                src_file.write_text(json.dumps(src_data, indent=2) + "\n")
            # Update dest path
            dest_file = REPO / "backend" / "content" / "paths" / f"{dest_path['slug']}.json"
            dest_data = json.loads(dest_file.read_text())
            if qid not in dest_data["questions"]:
                dest_data["questions"].append(qid)
                # Re-sort by difficulty (look up from any track question file)
                # Build qid difficulty map for this track
                qd: dict[int, str] = {}
                for f in TRACK_DIRS[track].glob("*.json"):
                    if f.stem == "schemas":
                        continue
                    for q in json.loads(f.read_text()):
                        qd[int(q["id"])] = f.stem
                diff_order = {"easy": 0, "medium": 1, "hard": 2}
                dest_data["questions"] = sorted(
                    set(dest_data["questions"]),
                    key=lambda q: (diff_order.get(qd.get(q, "easy"), 9), q),
                )
                dest_file.write_text(json.dumps(dest_data, indent=2) + "\n")
            print(f"   MOVE {qid} ({track}): {from_path} → {dest_path['slug']}")
    print()

    # B3 — priority adjustments
    b3_count = sum(len(v) for v in actions["B3_priority"].values())
    print(f"B3 (analytical priority): {b3_count} adjustments across {len(actions['B3_priority'])} tracks")
    for track, pairs in actions["B3_priority"].items():
        pair_counter = Counter(pairs)
        # Per-track: each (attr, dest) pair means attr should win over dest
        # Build proposed priority list
        from_to = defaultdict(set)
        for attr, dest in pairs:
            from_to[attr].add(dest)
        print(f"   {track}: {dict(from_to)}")
    if not dry_run and apply_b3 and b3_count > 0:
        # Apply: update ANALYTICAL_PRIORITY in audit_pattern_coverage.py
        # For each track with priority adjustments, build a priority list
        # such that attr beats dest for every (attr, dest) pair.
        # Naive: collect ordering relations and topological sort.
        for track, pairs in actions["B3_priority"].items():
            current = list(ANALYTICAL_PRIORITY.get(track, []))
            # Collect all analytical patterns mentioned
            mentioned = set()
            for a, d in pairs:
                mentioned.add(a)
                mentioned.add(d)
            for m in mentioned:
                if m not in current:
                    current.append(m)
            # Re-order: for each (a, d), ensure a comes before d
            for a, d in pairs:
                if a in current and d in current and current.index(a) > current.index(d):
                    current.remove(a)
                    current.insert(current.index(d), a)
            print(f"   priority for {track}: {current}")
            # Persist by editing audit_pattern_coverage.py — done by hand below
            # (Note: we edit the file via simple replacement of the dict literal)
    print()

    # B4 — tag additions
    n_addtag = len(actions["B4_addtag"])
    print(f"B4 (tag gap): {n_addtag} tag additions")
    if not dry_run and apply_b4 and n_addtag > 0:
        # Group by question file for efficient writes
        by_track: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for track, qid, tag, title, _concepts in actions["B4_addtag"]:
            by_track[track].append((qid, tag))
        for track, additions in by_track.items():
            # Build qid → file map
            qid_to_file: dict[int, Path] = {}
            for f in TRACK_DIRS[track].glob("*.json"):
                if f.stem == "schemas":
                    continue
                for q in json.loads(f.read_text()):
                    qid_to_file[int(q["id"])] = f
            # Group by file
            file_groups: dict[Path, list[tuple[int, str]]] = defaultdict(list)
            for qid, tag in additions:
                f = qid_to_file.get(qid)
                if f:
                    file_groups[f].append((qid, tag))
            for f, ops in file_groups.items():
                data = json.loads(f.read_text())
                ops_by_qid = dict(ops)
                for q in data:
                    qid = int(q["id"])
                    if qid in ops_by_qid:
                        tag = ops_by_qid[qid]
                        concepts = q.get("concepts", []) or []
                        if tag not in concepts and len(concepts) < 5:
                            concepts.append(tag)
                            q["concepts"] = concepts
                            print(f"   ADD tag '{tag}' to {qid} ({track})")
                f.write_text(json.dumps(data, indent=2) + "\n")
    print()

    if dry_run:
        print("(DRY RUN — no files modified. Remove --dry-run to apply.)")


if __name__ == "__main__":
    main()
