"""Batch-level answer-key balance check (defeats the dilution trap).

The group validators in validate_content.py measure a WHOLE (track, difficulty,
surface) group and only ERROR above a lenient ceiling (40% position / 55%
length). A freshly-authored batch can be 100% biased and still pass, because the
pre-existing questions dilute it under the ceiling. This helper checks the
distribution of *just the questions you authored* against the stricter AUTHORING
TARGET (<=40% position, <=45% unique-longest), so the bias is caught at the batch
level before it is laundered into a group.

Run it on the ids you just authored/edited:
    cd backend
    ../.venv/bin/python scripts/check_batch_balance.py 73077 73078 73079 ...
Exit code 1 (and a FAIL summary) if the batch exceeds a target; 0 if clean.
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

POS_TARGET = 0.40   # authoring target (stricter than the 40% group ERROR is identical here)
LEN_TARGET = 0.45   # authoring target (group ERROR is 55%; this is the real bar)

_LOADERS = {
    "data-engineering": "data_engineering_questions",
    "data-modeling": "data_modeling_questions",
    "pyspark": "pyspark_questions",
    "ml-fundamentals": "ml_fundamentals_questions",
    "experimentation": "experimentation_questions",
    "statistics": "statistics_questions",
}


def _all_mcq() -> dict[int, dict]:
    import importlib
    out: dict[int, dict] = {}
    for mod in _LOADERS.values():
        try:
            M = importlib.import_module(mod)
        except Exception:
            continue
        for q in getattr(M, "_ALL_QUESTIONS", []):
            if isinstance(q.get("correct_option"), int) and isinstance(q.get("options"), list) and len(q["options"]) >= 2:
                out[int(q["id"])] = q
    return out


def main() -> None:
    ids: list[int] = []
    for a in sys.argv[1:]:
        ids += [int(x) for x in a.replace(",", " ").split()]
    if not ids:
        sys.exit("usage: check_batch_balance.py <id> [<id> ...]  (space- or comma-separated)")
    idx = _all_mcq()
    batch = [idx[i] for i in ids if i in idx]
    missing = [i for i in ids if i not in idx]
    if missing:
        print(f"NOTE: {len(missing)} id(s) not found as MCQ (or numerical subtype): {missing}", file=sys.stderr)
    if not batch:
        sys.exit("no MCQ questions resolved from the given ids")

    n = len(batch)
    pos = Counter(q["correct_option"] for q in batch)
    modal_pos, modal_n = pos.most_common(1)[0]
    pos_share = modal_n / n

    def unique_longest(q):
        L = [len(str(o)) for o in q["options"]]
        return L[q["correct_option"]] == max(L) and L.count(max(L)) == 1
    longest = sum(1 for q in batch if unique_longest(q))
    len_share = longest / n

    labels = "ABCDEFGH"
    print(f"BATCH (n={n}): position {dict(sorted({labels[k]: v for k, v in pos.items()}.items()))}  "
          f"modal {labels[modal_pos]}={pos_share:.0%}  |  unique-longest {longest}/{n}={len_share:.0%}")

    fails = []
    if pos_share > POS_TARGET:
        fails.append(f"POSITION: modal {labels[modal_pos]} = {pos_share:.0%} > {POS_TARGET:.0%} target")
    if len_share > LEN_TARGET:
        fails.append(f"LENGTH: unique-longest = {len_share:.0%} > {LEN_TARGET:.0%} target "
                     f"(trim the over-detailed correct options)")
    if fails:
        print("FAIL — batch is biased (a green group validator would NOT catch this; dilution trap):")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    print("OK — batch within authoring targets.")


if __name__ == "__main__":
    main()
