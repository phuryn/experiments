#!/usr/bin/env python3
"""Set 01 analysis: per-cell mean/sd tables + hard-math correctness sweep."""
import csv, glob, os, sys, statistics as st
TAG = ('-' + sys.argv[1]) if len(sys.argv) > 1 else ''

OUT = r"<WORKDIR>\Temp\output\fable5-n10"

rows = list(csv.DictReader(open(os.path.join(OUT, f"set01{TAG}.csv"), encoding="utf-8")))
rows = [r for r in rows if r["round"] != "0"]  # drop smoke rows if any

EFFORTS = ["low", "medium", "high", "xhigh", "max"]

def cell(tier, model, effort):
    vals = [float(r["seconds"]) for r in rows
            if r["tier"] == tier and r["model"] == model and r["effort"] == effort and r["rc"] == "0"]
    fails = sum(1 for r in rows if r["tier"] == tier and r["model"] == model
                and r["effort"] == effort and r["rc"] != "0")
    return vals, fails

def table(tier, model):
    print(f"\n{tier} / {model}  (n per cell, mean s, sd, min-max, fails)")
    for eff in EFFORTS:
        vals, fails = cell(tier, model, eff)
        if not vals:
            print(f"  {eff:7} NO DATA fails={fails}")
            continue
        sd = st.stdev(vals) if len(vals) > 1 else 0.0
        print(f"  {eff:7} n={len(vals):2}  {st.mean(vals):6.1f}  sd {sd:5.1f}  "
              f"[{min(vals):5.1f}-{max(vals):6.1f}]  fails={fails}")

for tier, model in [("easy", "fable"), ("realistic", "fable"), ("realistic", "opus"), ("hard", "fable")]:
    table(tier, model)

vals, fails = cell("control", "fable", "xyz")
print(f"\ncontrol xyz: n={len(vals)} mean {st.mean(vals):.1f}s fails={fails}" if vals else f"\ncontrol xyz: no clean runs, fails={fails}")

# hard-math correctness: answer must contain 376 and 625 (the nontrivial idempotents)
print("\nhard-math correctness (376+625 present / total):")
for eff in EFFORTS:
    files = glob.glob(os.path.join(OUT, "answers", f"s01{TAG}-hard-fable-{eff}-r*.txt"))
    ok = sum(1 for fp in files
             if "376" in open(fp, encoding="utf-8").read() and "625" in open(fp, encoding="utf-8").read())
    print(f"  {eff:7} {ok}/{len(files)}")

# round-trip totals for drift visibility
print("\nmean seconds by round (all cells pooled):")
for rnd in sorted({int(r["round"]) for r in rows}):
    vals = [float(r["seconds"]) for r in rows if int(r["round"]) == rnd and r["rc"] == "0"]
    if vals:
        print(f"  r{rnd:02d}: {st.mean(vals):5.1f}s  n={len(vals)}")
