"""Build blindsolve_report.md (per-track id->key->haiku->match sequences + mismatch
analysis) from blindsolve.jsonl. Deterministic; safe to re-run."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "blindsolve.jsonl"
OUT = HERE / "blindsolve_report.md"
TRACKS = ['data-engineering', 'data-modeling', 'pyspark', 'ml-fundamentals', 'experimentation', 'statistics']
TNAME = {'data-engineering': 'DATA ENGINEERING', 'data-modeling': 'DATA MODELING', 'pyspark': 'PYSPARK',
         'ml-fundamentals': 'ML FUNDAMENTALS', 'experimentation': 'EXPERIMENTATION',
         'statistics': 'STATISTICS (conceptual)'}


def main() -> None:
    recs = {}
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["id"]] = r
    recs = list(recs.values())

    lines = ["# Blind-solve report — haiku pass-1, sonnet pass-2 on mismatches",
             "# Models: pass1=claude-haiku-4-5 (blind: stem+options only), pass2=claude-sonnet-4-5 (explanation-consistency, mismatches only)",
             "# Format: <id> key=<stored> haiku=<blind> <MATCH|MISS> [sonnet=<verdict> leads=<letter>]",
             ""]
    # summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| track | n | haiku match | miss | stored-key dist (A/B/C/D) |")
    lines.append("|---|---|---|---|---|")
    tot = tm = 0
    allmiss = defaultdict(list)
    for t in TRACKS:
        rs = [r for r in recs if r['track'] == t]
        n = len(rs); m = sum(1 for r in rs if r['match'])
        kd = Counter(r['key'] for r in rs)
        dist = "/".join(f"{round(100*kd.get(k,0)/n)}" for k in 'ABCD') if n else "-"
        lines.append(f"| {TNAME[t]} | {n} | {round(100*m/n) if n else 0}% | {n-m} | {dist} |")
        tot += n; tm += m
    lines.append(f"| **TOTAL** | **{tot}** | **{round(100*tm/tot)}%** | **{tot-tm}** | |")
    lines.append("")

    # per-track sequences
    for t in TRACKS:
        rs = [r for r in recs if r['track'] == t]
        rs.sort(key=lambda r: (r['difficulty'] != 'easy', r['difficulty'] != 'medium', r.get('order', 0), r['id']))
        n = len(rs); m = sum(1 for r in rs if r['match'])
        lines.append(f"## {TNAME[t]}  (n={n}, match {round(100*m/n) if n else 0}%, {n-m} miss)")
        lines.append("")
        cur = None
        for r in rs:
            if r['difficulty'] != cur:
                cur = r['difficulty']; lines.append(f"### {cur}")
            line = f"{r['id']} key={r['key']} haiku={r['haiku']} {'MATCH' if r['match'] else 'MISS'}"
            if not r['match']:
                line += f"   sonnet={r.get('sonnet')} leads={r.get('sonnet_leads_to')}"
                allmiss[t].append(r)
            lines.append(line)
        lines.append("")

    # mismatch analysis
    lines.append("## Mismatch analysis (haiku != stored key)")
    lines.append("- sonnet=consistent  => explanation defends the stored key (haiku blind-missed; key OK)")
    lines.append("- sonnet=INCONSISTENT => sonnet's read of the explanation does NOT land on the stored key (review)")
    lines.append("")
    for t in TRACKS:
        ms = allmiss[t]
        if not ms:
            continue
        incon = [r for r in ms if r.get('sonnet') != 'consistent']
        lines.append(f"**{TNAME[t]}**: {len(ms)} miss — {len(ms)-len(incon)} sonnet-consistent, {len(incon)} sonnet-INCONSISTENT")
        for r in incon:
            lines.append(f"  - !! {r['id']} key={r['key']} haiku={r['haiku']} sonnet_leads={r.get('sonnet_leads_to')}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}  ({tot} questions, {tm} match, {tot-tm} miss)")


if __name__ == "__main__":
    main()
