"""Analyze runs_<tag>.jsonl -> outputs/results.md (the writeup).
Computes per-cell stats, Arm A vs B cost/latency multipliers, T4 portability,
failure taxonomy with examples, and headline numbers for the post.

Usage: python analyze.py --tag full
"""
import argparse, json, os, statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "outputs")


def load(tag):
    rows = []
    with open(os.path.join(DATA, f"runs_{tag}.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def med(xs):
    return round(st.median(xs), 2) if xs else 0


def mean(xs):
    return st.mean(xs) if xs else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="full")
    args = ap.parse_args()
    rows = load(args.tag)

    cells = defaultdict(list)
    for r in rows:
        cells[(r["task"], r["arm"])].append(r)

    def cell_stats(rs):
        passed = sum(1 for r in rs if r["passed"])
        return {
            "n": len(rs), "pass": passed, "passpct": round(100 * passed / max(len(rs), 1)),
            "lat_med": med([r["latency"] for r in rs if r.get("latency")]),
            "cost_mean": mean([r["cost"] or 0 for r in rs]),
            "steps_med": med([r["n_steps"] for r in rs if r.get("n_steps")]) if any(r.get("n_steps") for r in rs) else None,
            "code_exec_pct": round(100 * sum(1 for r in rs if r.get("had_code_exec")) / max(len(rs), 1)) if any("had_code_exec" in r for r in rs) else None,
        }

    L = []
    L.append("# Results: Testing Google's Managed Agents (Gemini API)")
    L.append("")
    L.append(f"Run 2026-06-01. {len(rows)} total executions. Graders are deterministic (objective answers), not model-judged. Cost is estimated from token counts (directional).")
    L.append("")

    # --- main reliability table ---
    L.append("## 1. Reliability, cost, latency by task and arm")
    L.append("")
    L.append("Arm A = Google Managed Agents (they run the loop). Arm B = self-orchestrated gemini-3.5-flash (I run the loop). Same model class.")
    L.append("")
    L.append("| Task | Arm | N | Pass% | Median latency | Avg cost (est) | Median steps (A) | % used code-exec (A) |")
    L.append("|------|-----|---|-------|----------------|----------------|------------------|----------------------|")
    for (task, arm) in sorted(cells.keys()):
        s = cell_stats(cells[(task, arm)])
        L.append(f"| {task} | {arm} | {s['n']} | {s['passpct']}% | {s['lat_med']}s | ${s['cost_mean']:.5f} | {s['steps_med'] if s['steps_med'] is not None else '-'} | {str(s['code_exec_pct'])+'%' if s['code_exec_pct'] is not None else '-'} |")
    L.append("")

    # --- A vs B multipliers (T1-T3) ---
    L.append("## 2. The harness tradeoff: managed vs self-orchestrated (same model)")
    L.append("")
    cost_ratios, lat_ratios = [], []
    L.append("| Task | A cost | B cost | cost x | A latency | B latency | latency x | A pass% | B pass% |")
    L.append("|------|--------|--------|--------|-----------|-----------|-----------|---------|---------|")
    for task in ["T1", "T2", "T3"]:
        if (task, "A") in cells and (task, "B") in cells:
            a, b = cell_stats(cells[(task, "A")]), cell_stats(cells[(task, "B")])
            cr = a["cost_mean"] / b["cost_mean"] if b["cost_mean"] else 0
            lr = a["lat_med"] / b["lat_med"] if b["lat_med"] else 0
            cost_ratios.append(cr); lat_ratios.append(lr)
            L.append(f"| {task} | ${a['cost_mean']:.5f} | ${b['cost_mean']:.5f} | {cr:.1f}x | {a['lat_med']}s | {b['lat_med']}s | {lr:.1f}x | {a['passpct']}% | {b['passpct']}% |")
    if cost_ratios:
        L.append("")
        L.append(f"**Headline: the managed runtime costs ~{mean(cost_ratios):.0f}x more and runs ~{mean(lat_ratios):.0f}x slower than self-orchestrating the same model class, on these tasks.**")
    L.append("")

    # --- T4 portability ---
    L.append("## 3. Portability: does one AGENTS.md cross runtimes? (T4)")
    L.append("")
    L.append("One markdown control surface (format rule: `RESULT: <answer> | CONFIDENCE: <0-1>`, no markdown). Fed each runtime its native way.")
    L.append("")
    L.append("| Arm | Runtime | N | Answer correct% | Format-compliant% | Both% |")
    L.append("|-----|---------|---|-----------------|-------------------|-------|")
    arm_runtime = {"A": "Google Managed Agent (AGENTS.md inline)", "B": "Gemini direct (system prompt)", "C": "Claude (system prompt)"}
    for arm in ["A", "B", "C"]:
        rs = cells.get(("T4", arm))
        if not rs:
            continue
        n = len(rs)
        ans = sum(1 for r in rs if r.get("grade", {}) and r["grade"].get("answer"))
        fmt = sum(1 for r in rs if r.get("grade", {}) and r["grade"].get("format"))
        both = sum(1 for r in rs if r["passed"])
        L.append(f"| {arm} | {arm_runtime[arm]} | {n} | {round(100*ans/n)}% | {round(100*fmt/n)}% | {round(100*both/n)}% |")
    L.append("")

    # --- failure taxonomy ---
    L.append("## 4. Failure taxonomy")
    L.append("")
    tax = defaultdict(list)
    for r in rows:
        if r.get("failure_mode"):
            tax[r["failure_mode"]].append(r)
    if not tax:
        L.append("No failures recorded.")
    for f, rs in sorted(tax.items(), key=lambda x: -len(x[1])):
        ex = rs[0]
        L.append(f"- **{f}** ({len(rs)}): e.g. {ex['task']}/{ex['arm']} -> \"{(ex.get('text') or '')[:120].strip()}\"")
    L.append("")

    # --- totals ---
    total_cost = sum((r.get("cost") or 0) for r in rows)
    a_runs = [r for r in rows if r["arm"] == "A"]
    L.append("## 5. Totals")
    L.append("")
    L.append(f"- Total executions: {len(rows)}")
    L.append(f"- Total estimated cost: ${total_cost:.4f}")
    if a_runs:
        L.append(f"- Arm A median steps/run: {med([r['n_steps'] for r in a_runs if r.get('n_steps')])}")
        L.append(f"- Arm A runs that executed code in the sandbox: {round(100*sum(1 for r in a_runs if r.get('had_code_exec'))/len(a_runs))}%")
    L.append("")
    L.append("## 6. Soundbite stats (for the post)")
    L.append("")
    if cost_ratios:
        L.append(f"- Same model, two harnesses: managed ~{mean(cost_ratios):.0f}x the cost, ~{mean(lat_ratios):.0f}x the wall-clock.")
    # portability soundbite
    t4 = {arm: cell_stats(cells[("T4", arm)]) for arm in ["A", "B", "C"] if ("T4", arm) in cells}
    if t4:
        L.append(f"- One AGENTS.md, three runtimes, format-compliance: " + ", ".join(f"{arm} {t4[arm]['passpct']}%" for arm in t4))
    open(os.path.join(OUT, "results.md"), "w", encoding="utf-8").write("\n".join(L))
    print("wrote outputs/results.md")
    # also echo headline
    if cost_ratios:
        print(f"HEADLINE: managed ~{mean(cost_ratios):.0f}x cost, ~{mean(lat_ratios):.0f}x latency")
    for arm in ["A", "B", "C"]:
        if ("T4", arm) in cells:
            s = cell_stats(cells[("T4", arm)])
            print(f"T4 {arm}: both-compliant {s['passpct']}%")


if __name__ == "__main__":
    main()
