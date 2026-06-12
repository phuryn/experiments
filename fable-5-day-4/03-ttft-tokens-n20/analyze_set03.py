#!/usr/bin/env python3
"""Set 03 analysis: TTFT, totals, tokens per prompt/model + reasoning correctness."""
import csv, os, sys, statistics as st
TAG = ('-' + sys.argv[1]) if len(sys.argv) > 1 else ''

OUT = r"<WORKDIR>\Temp\output\fable5-n10"
rows = [r for r in csv.DictReader(open(os.path.join(OUT, f"set03{TAG}.csv"), encoding="utf-8")) if r["rc"] == "0"]
print(f"clean runs: {len(rows)}/40")

def cell(pid, model, field):
    return [float(r[field]) for r in rows if r["prompt_id"] == pid and r["model"] == model]

for pid in ("easy", "reason"):
    print(f"\n{pid}:")
    for model in ("opus", "fable"):
        fa = cell(pid, model, "t_first_any")
        tt = cell(pid, model, "t_total")
        ot = cell(pid, model, "output_tokens")
        print(f"  {model:5} first_any {st.mean(fa):5.2f}s (sd {st.stdev(fa):4.2f}, "
              f"[{min(fa):.1f}-{max(fa):.1f}])  total {st.mean(tt):5.1f}s (sd {st.stdev(tt):4.1f})  "
              f"out_tokens {st.mean(ot):6.0f} (sd {st.stdev(ot):4.0f})")

print("\nreasoning correctness (376+625):")
for model in ("opus", "fable"):
    n_ok = n = 0
    for r in rows:
        if r["prompt_id"] == "reason" and r["model"] == model:
            n += 1
            txt = open(os.path.join(OUT, "answers", r["run_id"] + ".txt"), encoding="utf-8").read()
            if "376" in txt and "625" in txt:
                n_ok += 1
    print(f"  {model}: {n_ok}/{n}")

print("\ncache check (input_tokens first vs rest):")
for model in ("opus", "fable"):
    it = [int(float(r["input_tokens"])) for r in rows if r["model"] == model]
    print(f"  {model}: first={it[0]}, median rest={sorted(it[1:])[len(it[1:])//2]}")
