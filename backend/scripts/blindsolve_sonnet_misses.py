"""Sonnet BLIND re-solve of the haiku misses (blind = stem+options only, no explanation).

Upgrades the evidence from "the explanation is self-consistent" to "an independent
strong model also lands on the stored key reasoning from scratch." Resumable.

Reads scripts/blindsolve.jsonl (match==False -> the misses), blind-solves each with
claude-sonnet-4-5 via the same pass-1 path, writes scripts/blindsolve_sonnet_misses.jsonl.
"""
from __future__ import annotations
import json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_blind_answer as H  # noqa: E402
import anthropic  # noqa: E402

HERE = Path(__file__).resolve().parent
SRC = HERE / "blindsolve.jsonl"
OUT = HERE / "blindsolve_sonnet_misses.jsonl"
SONNET = "claude-sonnet-4-5"


def main() -> None:
    miss_ids = set()
    for l in SRC.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            if not r["match"]:
                miss_ids.add(r["id"])

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    qs = [q for q in H.load_questions(H.TRACK_ORDER, H.DIFFICULTY_ORDER) if q.get("id") in miss_ids]

    done = set()
    if OUT.exists():
        for l in OUT.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(l)
                if r["sonnet_blind"] != "ERROR":
                    done.add(r["id"])
            except Exception:
                pass
    todo = [q for q in qs if q.get("id") not in done]
    print(f"[sonnet-misses] {len(miss_ids)} misses, {len(done)} done, {len(todo)} to solve", file=sys.stderr, flush=True)

    lock = threading.Lock()

    def write(rec):
        with lock:
            with OUT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def solve(q):
        keyed = H.idx_to_letter(q["correct_option"])
        try:
            p1 = H.run_pass1(q, client, SONNET)
            pick = p1["pass1_answer"]
        except Exception:
            pick = "ERROR"
        write({"id": q.get("id"), "track": q["_track"], "difficulty": q["_difficulty"],
               "key": keyed, "sonnet_blind": pick, "match": pick == keyed})

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(as_completed({ex.submit(solve, q): q for q in todo}))
    print(f"[sonnet-misses] done — {OUT}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
