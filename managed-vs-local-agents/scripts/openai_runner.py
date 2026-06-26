"""Run the same T1-T3 battery on OpenAI:
  - hosted  = Responses API + code_interpreter (OpenAI runs code in its sandbox; closest analog to a managed agent loop)
  - single  = one plain Responses API call (no tools)
Model: gpt-5-mini (flash/haiku tier). Captures latency + token cost.
Note: code_interpreter also bills a per-container surcharge (~$0.03) NOT in tokens -> flagged.
Writes data/openai_runs.jsonl + outputs/phase-openai.md
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc
from runner import TASKS
from openai import OpenAI

MODEL = "gpt-5-mini"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "outputs")
client = OpenAI(api_key=gc._load_key("OPENAI_API_KEY"))

# gpt-5-mini pricing ESTIMATE ($/1M): in 0.25, out 2.00. code_interpreter ~ $0.03 per container session (separate).
P_IN, P_OUT = 0.25, 2.00
CI_SESSION = 0.03

def _usage_cost(u):
    inp = getattr(u, "input_tokens", 0) or 0
    out = getattr(u, "output_tokens", 0) or 0
    return inp, out, (inp * P_IN + out * P_OUT) / 1e6

def run_hosted(task_text):
    t0 = time.time()
    resp = client.responses.create(model=MODEL, input=task_text,
                                   tools=[{"type": "code_interpreter", "container": {"type": "auto"}}])
    elapsed = time.time() - t0
    text = getattr(resp, "output_text", "") or ""
    used_ci = any(getattr(o, "type", "") in ("code_interpreter_call",) for o in getattr(resp, "output", []) or [])
    inp, out, cost = _usage_cost(resp.usage)
    if used_ci:
        cost += CI_SESSION  # per-container surcharge
    return {"text": text, "latency": round(elapsed, 2), "in_tok": inp, "out_tok": out, "cost": cost, "used_tool": used_ci, "ok": True}

def run_single(task_text):
    t0 = time.time()
    resp = client.responses.create(model=MODEL, input=task_text)
    elapsed = time.time() - t0
    text = getattr(resp, "output_text", "") or ""
    inp, out, cost = _usage_cost(resp.usage)
    return {"text": text, "latency": round(elapsed, 2), "in_tok": inp, "out_tok": out, "cost": cost, "used_tool": False, "ok": True}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--tasks", default="T1,T2,T3")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    task_ids = args.tasks.split(",")
    jobs = [(tid, arm, i) for tid in task_ids for arm in ("hosted", "single") for i in range(args.n)]
    print(f"running {len(jobs)} jobs (T{task_ids} x [hosted,single] x {args.n}), model={MODEL}")
    rows = []
    fh = open(os.path.join(DATA, "openai_runs.jsonl"), "w", encoding="utf-8")

    def do(job):
        tid, arm, i = job
        task = TASKS[tid]
        try:
            r = run_hosted(task["prompt"]) if arm == "hosted" else run_single(task["prompt"])
        except Exception as e:
            r = {"text": "", "latency": 0, "in_tok": 0, "out_tok": 0, "cost": 0, "ok": False, "error": f"{type(e).__name__}: {e}"}
        g = task["grader"](r.get("text"))
        passed = g["both"] if isinstance(g, dict) else bool(g)
        return {"task": tid, "arm": arm, "run": i, "passed": passed, **{k: r.get(k) for k in ("ok", "latency", "in_tok", "out_tok", "cost", "used_tool", "error")}, "text": (r.get("text") or "")[:300]}

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(do, j): j for j in jobs}
        done = 0
        for fut in as_completed(futs):
            row = fut.result(); rows.append(row)
            fh.write(json.dumps(row, default=str) + "\n"); fh.flush()
            done += 1
            err = row.get("error") or ""
            print(f"  [{done}/{len(jobs)}] {row['task']}/{row['arm']}#{row['run']} pass={row['passed']} {row['latency']}s ${row['cost']:.5f} {err[:60]}")
    fh.close()
    write_report(rows, args.n)

def write_report(rows, n):
    from collections import defaultdict
    import statistics as st
    cells = defaultdict(list)
    for r in rows:
        cells[(r["task"], r["arm"])].append(r)
    def med(xs): return round(st.median(xs), 2) if xs else 0
    L = [f"# OpenAI: Responses+code_interpreter vs single ({MODEL})", "",
         f"Same T1-T3 battery. N={n}/cell. Cost = token estimate (gpt-5-mini ~$0.25/$2.00 per 1M) + ~$0.03 code_interpreter container surcharge when used.", "",
         "| Task | Arm | N | Pass% | Median latency | Avg cost | % used code_interpreter |",
         "|------|-----|---|-------|----------------|----------|-------------------------|"]
    for k in sorted(cells):
        rs = cells[k]; npass = sum(1 for r in rs if r["passed"])
        L.append(f"| {k[0]} | {k[1]} | {len(rs)} | {round(100*npass/len(rs))}% | {med([r['latency'] for r in rs if r.get('latency')])}s | ${st.mean([r['cost'] or 0 for r in rs]):.5f} | {round(100*sum(1 for r in rs if r.get('used_tool'))/len(rs))}% |")
    total = sum(r.get("cost") or 0 for r in rows)
    L += ["", f"**Total estimated cost this run: ${total:.4f}**"]
    open(os.path.join(OUT, "phase-openai.md"), "w", encoding="utf-8").write("\n".join(L))
    print("-> outputs/phase-openai.md")

if __name__ == "__main__":
    main()
