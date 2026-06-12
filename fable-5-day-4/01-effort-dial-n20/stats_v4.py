#!/usr/bin/env python3
"""All card-cell stats (med/min/max) for the v4 builds. Usage: stats_v4.py [tag]"""
import csv, os, sys, statistics as st

TAG = ('-' + sys.argv[1]) if len(sys.argv) > 1 else ''
OUT = r"<WORKDIR>\Temp\output\fable5-n10"

def load(name):
    return [r for r in csv.DictReader(open(os.path.join(OUT, f"{name}{TAG}.csv"), encoding="utf-8"))
            if r["rc"] == "0" and r.get("round") != "0"]

def mmm(name, v, fmt="{:.1f}"):
    print(f"  {name:28} med={fmt.format(st.median(v))}  min={fmt.format(min(v))}  max={fmt.format(max(v))}  n={len(v)}")

s1 = load("set01")
print("== CARD 33 (set01) ==")
for tier, model in [("easy", "fable"), ("realistic", "fable"), ("realistic", "opus"), ("hard", "fable")]:
    for eff in ["low", "medium", "high", "xhigh", "max"]:
        v = [float(r["seconds"]) for r in s1 if r["tier"] == tier and r["model"] == model and r["effort"] == eff]
        if v: mmm(f"{tier}/{model}/{eff}", v)

s2 = load("set02")
print("\n== CARD 32 sec03 (set02) ==")
rounds = sorted({int(r["round"]) for r in s2})
ratios, arat = [], []
for rnd in rounds:
    o = sum(float(r["seconds"]) for r in s2 if r["exp"] == "speed" and r["model"] == "opus" and int(r["round"]) == rnd)
    f = sum(float(r["seconds"]) for r in s2 if r["exp"] == "speed" and r["model"] == "fable" and int(r["round"]) == rnd)
    if o and f: ratios.append(f / o)
    oa = [float(r["seconds"]) for r in s2 if r["exp"] == "audit" and r["model"] == "opus" and int(r["round"]) == rnd]
    fa = [float(r["seconds"]) for r in s2 if r["exp"] == "audit" and r["model"] == "fable" and int(r["round"]) == rnd]
    if oa and fa: arat.append(fa[0] / oa[0])
mmm("speed round-ratio", ratios, "{:.2f}")
mmm("audit round-ratio", arat, "{:.2f}")
for m in ("opus", "fable"):
    mmm(f"audit secs {m}", [float(r["seconds"]) for r in s2 if r["exp"] == "audit" and r["model"] == m], "{:.0f}")
    chars = [int(r["chars"]) for r in s2 if r["exp"] == "audit" and r["model"] == m]
    print(f"    audit chars {m}: med={st.median(chars):.0f}")
print("  pin-check (Q1):")
for m in ("opus", "fable"):
    d = [float(r["seconds"]) for r in s2 if r["exp"] == "speed" and r["model"] == m and r["q"] == "Q1"]
    h = [float(r["seconds"]) for r in s2 if r["exp"] == "pin" and r["model"] == m]
    print(f"    {m}: default med={st.median(d):.1f} vs high med={st.median(h):.1f}")

s3 = load("set03")
print("\n== CARD 32 sec01+02 (set03) ==")
for m in ("opus", "fable"):
    mmm(f"pause easy {m}", [float(r["t_first_any"]) for r in s3 if r["prompt_id"] == "easy" and r["model"] == m], "{:.2f}")
for m in ("opus", "fable"):
    mmm(f"reason tokens {m}", [float(r["output_tokens"]) for r in s3 if r["prompt_id"] == "reason" and r["model"] == m], "{:.0f}")
    mmm(f"reason total {m}", [float(r["t_total"]) for r in s3 if r["prompt_id"] == "reason" and r["model"] == m])
