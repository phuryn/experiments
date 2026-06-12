#!/usr/bin/env python3
"""Part 2: findings counts (v4, n=20/model) + hit rates (pooled, 30/model)."""
import glob, os, re, statistics as st

ANS = r"<WORKDIR>\Temp\output\fable5-n10\answers"

def count_findings(text):
    """Longest run of consecutively numbered headings/items = findings count."""
    nums = [int(n) for n in re.findall(r"(?m)^\s*(?:#{1,4}\s*)?(?:\*\*)?(\d{1,2})[.)—:]", text)]
    best = cur = prev = 0
    for n in nums:
        cur = cur + 1 if n == prev + 1 else 1
        prev = n
        best = max(best, cur)
    return best if best >= 2 else None

for model in ("opus", "fable"):
    counts = []
    for fp in sorted(glob.glob(os.path.join(ANS, f"s02-v4-audit-{model}-*.txt"))):
        c = count_findings(open(fp, encoding="utf-8", errors="replace").read())
        counts.append(c)
    ok = [c for c in counts if c]
    print(f"{model} v4 findings: parseable n={len(ok)}/20  med={st.median(ok)}  "
          f"min={min(ok)} max={max(ok)}  raw={counts}")

print()
for model in ("opus", "fable"):
    files = sorted(glob.glob(os.path.join(ANS, f"s02-audit-{model}-*.txt")) +
                   glob.glob(os.path.join(ANS, f"s02-v4-audit-{model}-*.txt")))
    h50 = hnn = hex_ = 0
    for fp in files:
        t = open(fp, encoding="utf-8", errors="replace").read()
        if "50K" in t and "75K" in t: h50 += 1
        if "nobody is naming" in t.lower(): hnn += 1
        if "exclamation" in t.lower(): hex_ += 1
    print(f"{model}: n={len(files)}  50K-vs-75K={h50}  nobody-is-naming={hnn}  exclamation={hex_}")
