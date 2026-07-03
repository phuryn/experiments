#!/usr/bin/env python3
"""Aggregate runs.csv -> summary.json + medians tables (stdout)."""
import csv, json, os, statistics as st

OUT = os.path.dirname(os.path.abspath(__file__))
EFFORTS = ["low", "medium", "high", "xhigh", "max"]

rows = list(csv.DictReader(open(os.path.join(OUT, "runs.csv"), newline="", encoding="utf-8")))
clean = [r for r in rows if r["rc"] == "0"]
dirty = [r for r in rows if r["rc"] != "0"]

def p95(xs):
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = 0.95 * (len(xs) - 1)
    f = int(k)
    return round(xs[f] + (xs[f + 1] - xs[f]) * (k - f), 1) if f + 1 < len(xs) else xs[-1]

summary = {}
cells = sorted({(r["task"], r["model"]) for r in rows})
for task, model in cells:
    for eff in EFFORTS:
        cell = [r for r in clean if (r["task"], r["model"], r["effort"]) == (task, model, eff)]
        allc = [r for r in rows if (r["task"], r["model"], r["effort"]) == (task, model, eff)]
        if not allc:
            continue
        secs = [float(r["seconds"]) for r in cell]
        toks = [int(r["output_tokens"]) for r in cell if r["output_tokens"]]
        key = f"{task}/{model}/{eff}"
        s = {"n": len(allc), "n_clean": len(cell),
             "median_seconds": round(st.median(secs), 1) if secs else None,
             "p95_seconds": p95(secs) if secs else None,
             "worst_seconds": round(max(secs), 1) if secs else None,
             "median_output_tokens": int(st.median(toks)) if toks else None,
             "median_input_tokens": int(st.median([int(r["input_tokens"]) for r in cell if r["input_tokens"]])) if cell else None,
             "median_chars": int(st.median([int(r["chars"]) for r in cell])) if cell else None}
        if task == "audit":
            scores = [int(r["correct_or_score"]) for r in cell]
            s["mean_bug_score"] = round(sum(scores) / len(scores), 2) if scores else None
            s["score_distribution"] = {str(v): scores.count(v) for v in sorted(set(scores))} if scores else {}
        elif task.startswith("needle"):
            strict = [int(r["correct_or_score"]) for r in cell]
            loose = [int(r.get("loose_score") or 0) for r in cell]
            s["strict_catch"] = f"{sum(strict)}/{len(strict)}" if strict else None
            s["strict_rate"] = round(sum(strict) / len(strict), 2) if strict else None
            s["loose_catch"] = f"{sum(loose)}/{len(loose)}" if loose else None
        elif task == "easy":
            g = [int(r["correct_or_score"]) for r in cell if r["correct_or_score"] != ""]
            s["exactly_3_bullets_rate"] = round(sum(g) / len(g), 2) if g else None
        summary[key] = s

summary["_meta"] = {
    "build": "Claude Code CLI 2.1.198, 2026-07-03 (day-4 reference: 2.1.173, June 12)",
    "total_rows": len(rows), "clean_rows": len(clean), "failed_rows": len(dirty),
    "failed_detail": [{"task": r["task"], "model": r["model"], "effort": r["effort"],
                       "round": r["round"], "rc": r["rc"]} for r in dirty],
    "notes": "seconds = wall clock incl. CLI startup (day-4 parity). output_tokens from CLI result JSON usage; includes thinking (no separate reasoning-token field exposed). CLAUDE_EFFORT env stripped; explicit --effort flags on every run.",
}
with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=1)

def table(task, model, field):
    vals = []
    for eff in EFFORTS:
        s = summary.get(f"{task}/{model}/{eff}", {})
        v = s.get(field)
        vals.append(str(v) if v is not None else "-")
    return " / ".join(vals)

print("=== medians low/medium/high/xhigh/max ===")
for task, model in cells:
    print(f"{task}/{model}: sec {table(task, model, 'median_seconds')} | out_tok {table(task, model, 'median_output_tokens')}")
print("\naudit mean bug score:", table("audit", "fable", "mean_bug_score"))
print("easy 3-bullet rate:", table("easy", "fable", "exactly_3_bullets_rate"))
if any(t == "needle" for t, _ in cells):
    print("needle strict fable:", table("needle", "fable", "strict_catch"), "| loose:", table("needle", "fable", "loose_catch"))
    print("needle strict opus: ", table("needle", "opus", "strict_catch"), "| loose:", table("needle", "opus", "loose_catch"))
print(f"\nrows {len(rows)} clean {len(clean)} failed {len(dirty)}")
