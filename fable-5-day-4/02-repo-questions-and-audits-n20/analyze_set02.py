#!/usr/bin/env python3
"""Set 02 analysis: speed ratios, audit cell, pin-check, correctness heuristics."""
import csv, os, sys, statistics as st
TAG = ('-' + sys.argv[1]) if len(sys.argv) > 1 else ''

OUT = r"<WORKDIR>\Temp\output\fable5-n10"
rows = list(csv.DictReader(open(os.path.join(OUT, f"set02{TAG}.csv"), encoding="utf-8")))
ok = [r for r in rows if r["rc"] == "0"]
fails = [r for r in rows if r["rc"] != "0"]
print(f"total={len(rows)} ok={len(ok)} fails={len(fails)}")
for f in fails:
    print("  FAIL:", f["run_id"], "rc=", f["rc"])

def sel(exp, model, q=None):
    return [float(r["seconds"]) for r in ok
            if r["exp"] == exp and r["model"] == model and (q is None or r["q"] == q)]

QS = ["Q1", "Q2", "Q3", "Q4", "Q5"]

print("\nspeed: per-question mean s (sd), n=10 each")
print(f"  {'Q':4} {'opus':>16} {'fable':>16}")
for q in QS:
    o, f = sel("speed", "opus", q), sel("speed", "fable", q)
    print(f"  {q:4} {st.mean(o):7.1f} ({st.stdev(o):4.1f}) {st.mean(f):8.1f} ({st.stdev(f):4.1f})")

print("\nspeed: per-round totals (5 questions) and ratio")
ratios = []
for rnd in range(1, 11):
    o = sum(float(r["seconds"]) for r in ok if r["exp"] == "speed" and r["model"] == "opus" and int(r["round"]) == rnd)
    f = sum(float(r["seconds"]) for r in ok if r["exp"] == "speed" and r["model"] == "fable" and int(r["round"]) == rnd)
    if o and f:
        ratios.append(f / o)
        print(f"  r{rnd:02d}: opus {o:6.1f}s  fable {f:6.1f}s  ratio {f/o:.2f}")
print(f"  mean ratio {st.mean(ratios):.2f} (sd {st.stdev(ratios):.2f})")

oa, fa = sel("speed", "opus"), sel("speed", "fable")
print(f"\nper-answer: opus {st.mean(oa):.1f}s (sd {st.stdev(oa):.1f}, max {max(oa):.1f}) | "
      f"fable {st.mean(fa):.1f}s (sd {st.stdev(fa):.1f}, max {max(fa):.1f})")

print("\naudit (multi-file judgment, n=10 per model): seconds + answer chars")
for model in ("opus", "fable"):
    secs = sel("audit", model)
    chars = [int(r["chars"]) for r in ok if r["exp"] == "audit" and r["model"] == model]
    print(f"  {model:5} {st.mean(secs):6.1f}s (sd {st.stdev(secs):5.1f})  chars {st.mean(chars):7.0f} (sd {st.stdev(chars):5.0f})")

print("\npin-check: Q1 at default vs explicit --effort high, n=10 each")
for model in ("opus", "fable"):
    d, h = sel("speed", model, "Q1"), sel("pin", model, "Q1")
    print(f"  {model:5} default {st.mean(d):5.1f}s (sd {st.stdev(d):4.1f})  high {st.mean(h):5.1f}s (sd {st.stdev(h):4.1f})")

CHECKS = {
    "Q1": lambda t: "screenshot" in t.lower(),
    "Q2": lambda t: "how" in t.lower(),
    "Q3": lambda t: all(w in t.lower() for w in ("constraint", "calibration", "scaffold")),
    "Q4": lambda t: "webfetch" in t.lower(),
    "Q5": lambda t: "17" in t,
}
print("\ncorrectness heuristics (speed answers):")
bad = []
for q, check in CHECKS.items():
    for model in ("opus", "fable"):
        n_ok = 0
        for r in ok:
            if r["exp"] == "speed" and r["q"] == q and r["model"] == model:
                txt = open(os.path.join(OUT, "answers", r["run_id"] + ".txt"), encoding="utf-8").read()
                if check(txt):
                    n_ok += 1
                else:
                    bad.append(r["run_id"])
        print(f"  {q}/{model}: {n_ok}/10")
if bad:
    print("review manually:", *bad, sep="\n  ")
