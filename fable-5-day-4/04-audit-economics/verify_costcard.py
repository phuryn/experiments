#!/usr/bin/env python3
"""Re-verify every number going on the 36-finding-cost card.
$/audit (v4 + pooled), findings counts (v4), hit rates (pooled 30/model)."""
import csv, glob, os, re, statistics as st

OUT = r"<WORKDIR>\Temp\output\fable5-n10"
ANS = os.path.join(OUT, "answers")

# ---- 1. $/audit from audit_usage.csv ----
rows = list(csv.DictReader(open(os.path.join(OUT, "audit_usage.csv"), encoding="utf-8")))
for model in ("opus", "fable"):
    allc = sorted(float(r["cost_usd"]) for r in rows if r["model"] == model)
    v4 = sorted(float(r["cost_usd"]) for r in rows if r["model"] == model and "v4" in r["src"])
    print(f"{model}: n={len(allc)} total=${sum(allc):.2f} med=${st.median(allc):.3f} | "
          f"v4 n={len(v4)} min=${v4[0]:.3f} med=${st.median(v4):.3f} max=${v4[-1]:.3f}")
grand = sum(float(r["cost_usd"]) for r in rows)
print(f"grand total: ${grand:.2f}")

# ---- 2. findings counts (v4 = r01-r20 in set02-v4) + hit rates (all 30) ----
# v4 audit answers: which rounds belong to v4? set02-v4.csv rounds 1-20, set02.csv rounds 1-10.
# Answer files: s02-audit-<model>-AUD-r<NN>.txt — v4 retry overwrote? Check run_id space.
v4_ids = set()
for r in csv.DictReader(open(os.path.join(OUT, "set02-v4.csv"), encoding="utf-8")):
    if r["exp"] == "audit" and r["rc"] == "0" and r["round"] != "0":
        v4_ids.add(r["run_id"])
print(f"v4 clean audit run_ids: {len(v4_ids)} e.g. {sorted(v4_ids)[:2]}")

def count_findings(text):
    """Count distinct numbered findings in an audit answer."""
    nums = re.findall(r"(?m)^\s*(?:\*\*)?(\d{1,2})[.)]", text)
    if not nums:
        nums = re.findall(r"(?m)^\s*[-*]\s", text)
        return len(nums) if nums else None
    seq = [int(n) for n in nums]
    best, cur, prev = 0, 0, 0
    for n in seq:
        cur = cur + 1 if n == prev + 1 else 1
        prev = n
        best = max(best, cur)
    return best if best >= 2 else None

# map v4 run_id -> answer file (v4 files tagged differently?)
files = glob.glob(os.path.join(ANS, "*audit*"))
print(f"audit answer files: {len(files)}")
tags = sorted({os.path.basename(f) for f in files})
print("sample names:", tags[:3], "...", tags[-3:])
