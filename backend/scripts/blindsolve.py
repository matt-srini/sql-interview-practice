"""Resumable blind-solve driver (haiku pass-1, gated sonnet pass-2 on mismatches).

Reuses audit_blind_answer.py's exact prompts/parsing but writes each result to a
JSONL immediately, so a kill/interrupt never loses progress (re-run resumes).

Usage:
    cd backend
    ../.venv/bin/python scripts/blindsolve.py            # all 6 MCQ tracks
    ../.venv/bin/python scripts/blindsolve.py --track pyspark
Output: scripts/blindsolve.jsonl  (one record per question)
Then build the human report with scripts/blindsolve_build_report.py
"""
from __future__ import annotations
import argparse, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_blind_answer as H  # noqa: E402 (loads .env + anthropic on import)
import anthropic  # noqa: E402

OUT = Path(__file__).resolve().parent / "blindsolve.jsonl"
HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-5"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=None, choices=list(H.TRACKS.keys()))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=key)

    tracks = [args.track] if args.track else H.TRACK_ORDER
    questions = H.load_questions(tracks, H.DIFFICULTY_ORDER)

    done: set = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                pass
    todo = [q for q in questions if q.get("id") not in done]
    print(f"[blindsolve] {len(questions)} MCQs, {len(done)} already done, {len(todo)} to solve",
          file=sys.stderr, flush=True)

    lock = threading.Lock()

    def write(rec: dict) -> None:
        with lock:
            with OUT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def solve(q: dict) -> str:
        keyed = H.idx_to_letter(q["correct_option"])
        p1 = H.run_pass1(q, client, HAIKU)
        haiku = p1["pass1_answer"]
        match = (haiku == keyed)
        rec = {
            "id": q.get("id"), "track": q["_track"], "difficulty": q["_difficulty"],
            "order": q.get("order", 0), "key": keyed, "haiku": haiku, "match": match,
            "sonnet": None, "sonnet_leads_to": None,
        }
        if not match:
            p2 = H.run_pass2(q, client, SONNET)
            rec["sonnet_leads_to"] = p2.get("pass2_explanation_leads_to")
            rec["sonnet"] = "consistent" if p2.get("pass2_consistent") else "INCONSISTENT"
        write(rec)
        return f"{q.get('id')} {keyed}/{haiku}"

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(solve, q): q for q in todo}
        n = 0
        for f in as_completed(futs):
            n += 1
            try:
                f.result()
            except Exception:
                q = futs[f]
                write({"id": q.get("id"), "track": q["_track"], "difficulty": q["_difficulty"],
                       "order": q.get("order", 0), "key": H.idx_to_letter(q["correct_option"]),
                       "haiku": "ERROR", "match": False, "sonnet": None, "sonnet_leads_to": None})
            if n % 25 == 0:
                print(f"[blindsolve] {n}/{len(todo)}", file=sys.stderr, flush=True)
    print(f"[blindsolve] done — {OUT}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
