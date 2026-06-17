#!/usr/bin/env python3
"""Build the raw per-(model, run, bug) catch matrix for the tile-grid infographic.

Caps every model to the SAME N runs (first --cap, sorted by run tag) so the grid is
rectangular (the visual requires equal tiles per cell). Routes each caught ID to its
correct axis (live seed / real / superseded) regardless of which grader array it landed
in, since blind judges occasionally misfile R*/C* IDs.

Usage: python build_raw_matrix.py [--grades PATH] [--cap 10] [--out PATH]
"""
import json, argparse, os
from collections import defaultdict

BASE = "Temp/audit-repo"
AK = json.load(open(f"{BASE}/answer_key.json", encoding="utf-8"))
RB = json.load(open(f"{BASE}/real_bugs.json", encoding="utf-8"))
seeds = AK if isinstance(AK, list) else AK.get("seeds", AK)
real = RB if isinstance(RB, list) else RB.get("bugs", RB)

live = [s for s in seeds if s.get("tier") == "live"]
sup = [s for s in seeds if s.get("tier") == "superseded"]
LIVE_IDS = {s["id"] for s in live}
SUP_IDS = {s["id"] for s in sup}
REAL_IDS = {b["id"] for b in real}
ALL_IDS = LIVE_IDS | SUP_IDS | REAL_IDS
MODELS = ["OPUS", "GLM", "CODEX"]

CAUGHT_KEYS = ("live_seeds_caught", "real_bugs_caught",
               "superseded_caught_with_history", "superseded_flagged_as_live")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", default="Temp/data/audit_runs/grades_full.json")
    ap.add_argument("--cap", type=int, default=10)
    ap.add_argument("--out", default="Temp/data/audit_runs/raw_matrix.json")
    args = ap.parse_args()

    grades = [g for g in json.load(open(args.grades, encoding="utf-8")) if not g.get("error")]
    by = defaultdict(list)
    for g in grades:
        by[g["runId"].split("_")[0].upper()].append(g)
    for m in by:
        by[m].sort(key=lambda g: g["runId"])
        by[m] = by[m][:args.cap]   # equal N: first `cap` runs per model

    out = {"models": MODELS, "cap": args.cap, "runs": {}, "run_tags": {},
           "bugs_live_order": [s["id"] for s in live],
           "bugs_real_order": [b["id"] for b in real],
           "bugs_super_order": [s["id"] for s in sup],
           "matrix": {}}
    for m in MODELS:
        runs = by.get(m, [])
        out["runs"][m] = len(runs)
        out["run_tags"][m] = [g["runId"].split("_")[1] for g in runs]
        caught_per_run = []
        for g in runs:
            c = set()
            for k in CAUGHT_KEYS:
                for x in (g.get(k) or []):
                    c.add(x)
            caught_per_run.append(c)
        out["matrix"][m] = {bid: [1 if bid in cs else 0 for cs in caught_per_run] for bid in ALL_IDS}

    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=1)
    print(f"-> {args.out}  (cap={args.cap})")
    print("runs:", out["runs"])
    for m in MODELS:
        n = out["runs"][m]
        if not n:
            continue
        lh = sum(sum(out["matrix"][m][i]) for i in LIVE_IDS)
        rh = sum(sum(out["matrix"][m][i]) for i in REAL_IDS)
        print(f"  {m}: live {lh}/{len(LIVE_IDS)*n} ({100*lh/(len(LIVE_IDS)*n):.0f}%)  "
              f"real {rh}/{len(REAL_IDS)*n} ({100*rh/(len(REAL_IDS)*n):.0f}%)")


if __name__ == "__main__":
    main()
