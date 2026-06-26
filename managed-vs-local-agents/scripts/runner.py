"""Managed Agents experiment runner.

Arms:
  A = Google Managed Agents (antigravity, /v1beta/interactions) -- Google runs the loop
  B = self-orchestrated gemini-3.5-flash (generateContent + code_execution) -- I run the loop
  C = Claude (Anthropic Messages API) -- cross-vendor portability (T4 only)

Tasks T1-T4 each have an automated grader. Per-run rows -> data/runs_<tag>.jsonl.
Summary -> outputs/phase-run_<tag>.md.

Usage:
  python runner.py --tasks T1,T2,T3 --arms A,B --n 10 --concurrency 4 --tag full
  python runner.py --tasks T4 --arms A,B,C --n 10 --tag portability
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # experiments/managed-agents
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "outputs")

# --- pricing (USD per 1M tokens; ESTIMATES, labelled as such in report) ---
PRICE = {
    "gemini-in": 0.30, "gemini-out": 2.50,          # gemini flash-class estimate
    "claude-in": 1.00, "claude-out": 5.00,          # claude haiku-class estimate
}

# --- AGENTS.md used for the portability test (T4). One markdown control surface. ---
AGENTS_MD = """# Agent Operating Rules

You are a calculation assistant.

- Always respond in EXACTLY this format, on a single line:
  RESULT: <answer> | CONFIDENCE: <number between 0 and 1>
- <answer> is the final numeric answer only. No words.
- Never use markdown, code blocks, asterisks, or any extra commentary.
"""

# ---------------- graders ----------------
def _norm(s):
    return re.sub(r"[,\s$]", "", (s or "").lower())

def grade_T1(out):  # sum of primes below 1000 = 76127
    return "76127" in _norm(out)

def grade_T2(out):  # mean of squares 1..50 = 858.5
    return "858.5" in _norm(out)

def grade_T3(out):  # bat&ball -> ball = 0.05 ; trap answer = 0.10
    n = _norm(out)
    has_correct = ("0.05" in n) or (".05" in n) or ("5cents" in n)
    has_trap = ("0.10" in n) or ("0.1cents" in n) or ("10cents" in n) or (n.strip() in ("0.1", ".1"))
    return has_correct and not (has_trap and not has_correct)

def grade_T4(out):  # format compliance: RESULT: 391 | CONFIDENCE: x , no markdown
    ans_ok = bool(re.search(r"result:\s*391\b", (out or "").lower()))
    fmt_ok = bool(re.search(r"result:.*\|\s*confidence:\s*0?\.?\d", (out or "").lower(), re.S))
    no_md = not any(c in (out or "") for c in ("```", "**", "###"))
    return {"answer": ans_ok, "format": fmt_ok and no_md, "both": ans_ok and fmt_ok and no_md}

TASKS = {
    "T1": {
        "name": "prime-sum (deterministic compute)",
        "prompt": "Calculate the sum of all prime numbers strictly below 1000. Output ONLY the final integer, nothing else.",
        "grader": grade_T1, "kind": "bool",
    },
    "T2": {
        "name": "squares-mean (multi-step)",
        "prompt": "Generate the squares of the integers 1 through 50 (i.e. 1, 4, 9, ... 2500). Then compute the arithmetic mean of those 50 squared values. Output ONLY the mean as a number.",
        "grader": grade_T2, "kind": "bool",
    },
    "T3": {
        "name": "bat-and-ball (reasoning trap)",
        "prompt": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? Output ONLY the dollar amount.",
        "grader": grade_T3, "kind": "bool",
    },
    "T4": {
        "name": "AGENTS.md format compliance (portability)",
        "prompt": "What is 17 multiplied by 23?",
        "grader": grade_T4, "kind": "dict",
        "agents_md": AGENTS_MD,
    },
}

# ---------------- arms ----------------
def cost_gemini(usage):
    ti = usage.get("total_input_tokens", usage.get("promptTokenCount", 0)) or 0
    to = usage.get("total_output_tokens", usage.get("candidatesTokenCount", 0)) or 0
    tt = usage.get("total_thought_tokens", usage.get("thoughtsTokenCount", 0)) or 0
    tu = usage.get("total_tool_use_tokens", 0) or 0
    out_all = to + tt + tu
    return ti, out_all, (ti * PRICE["gemini-in"] + out_all * PRICE["gemini-out"]) / 1e6

def run_A(task):
    """Managed Agents. For T4, register a custom agent with AGENTS.md first."""
    agent = "antigravity-preview-05-2026"
    if task.get("agents_md"):
        agent = task["_custom_agent_id"]  # set by caller
    res = gc.run_interaction(task["prompt"], agent=agent, timeout=300)
    out = {"arm": "A", "ok": res.get("ok"), "status": res.get("status"), "latency": round(res.get("elapsed", 0), 2)}
    if not res.get("ok"):
        out["error"] = res.get("error", "")[:300]; out["text"] = ""; out["in_tok"] = out["out_tok"] = 0; out["cost"] = 0
        return out
    j = res["json"]
    text = ""
    steps = j.get("steps", [])
    for s in reversed(steps):
        if s.get("type") == "model_output":
            c = s.get("content", [])
            text = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
            break
    if not text and j.get("output_text"):
        text = j["output_text"]
    ti, to, cost = cost_gemini(j.get("usage", {}))
    out.update({"text": text, "in_tok": ti, "out_tok": to, "cost": cost,
                "n_steps": len(steps),
                "step_types": [s.get("type") for s in steps],
                "had_code_exec": any(s.get("type") == "code_execution_call" for s in steps),
                "interaction_status": j.get("status")})
    return out

def run_B(task):
    """Self-orchestrated gemini-3.5-flash with code execution tool (single call, I control harness)."""
    system = task.get("agents_md")  # for T4 the AGENTS.md goes in as system instruction
    tools = None if task.get("agents_md") else [{"code_execution": {}}]
    res = gc.generate_content("gemini-3.5-flash", task["prompt"], system=system, tools=tools, timeout=120)
    out = {"arm": "B", "ok": res.get("ok"), "status": res.get("status"), "latency": round(res.get("elapsed", 0), 2)}
    if not res.get("ok"):
        # retry once without code tool (some tasks/models reject it)
        res2 = gc.generate_content("gemini-3.5-flash", task["prompt"], system=system, timeout=120)
        if res2.get("ok"):
            res = res2
        else:
            out["error"] = res.get("error", "")[:300]; out["text"] = ""; out["in_tok"] = out["out_tok"] = 0; out["cost"] = 0
            return out
    j = res["json"]
    text = ""
    try:
        parts = j["candidates"][0]["content"]["parts"]
        text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p)
    except Exception:
        text = ""
    ti, to, cost = cost_gemini(j.get("usageMetadata", {}))
    out.update({"text": text, "in_tok": ti, "out_tok": to, "cost": cost})
    return out

def run_C(task):
    """Claude (Anthropic) for cross-vendor portability. T4 only."""
    key = gc._load_key("ANTHROPIC_API_KEY")
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 256,
        "system": task.get("agents_md", ""),
        "messages": [{"role": "user", "content": task["prompt"]}],
    }
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    out = {"arm": "C", "latency": 0}
    try:
        r = urllib.request.urlopen(req, timeout=120); j = json.load(r)
        out["ok"] = True; out["status"] = 200; out["latency"] = round(time.time() - t0, 2)
        text = " ".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        u = j.get("usage", {})
        ti, to = u.get("input_tokens", 0), u.get("output_tokens", 0)
        out.update({"text": text, "in_tok": ti, "out_tok": to,
                    "cost": (ti * PRICE["claude-in"] + to * PRICE["claude-out"]) / 1e6})
    except urllib.error.HTTPError as e:
        out.update({"ok": False, "status": e.code, "error": e.read().decode()[:300], "text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": round(time.time() - t0, 2)})
    except Exception as e:
        out.update({"ok": False, "status": None, "error": f"{type(e).__name__}: {e}", "text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": round(time.time() - t0, 2)})
    return out

ARMS = {"A": run_A, "B": run_B, "C": run_C}

def classify_failure(task_id, row, passed):
    if not row.get("ok"):
        return f"api_error_{row.get('status')}"
    if passed:
        return None
    t = (row.get("text") or "").lower()
    if not t.strip():
        return "empty_output"
    if task_id == "T3" and ("0.10" in t or "10 cents" in t):
        return "reasoning_trap"
    if task_id == "T4":
        g = TASKS["T4"]["grader"](row.get("text"))
        if not g["answer"]:
            return "wrong_answer"
        if not g["format"]:
            return "format_violation"  # didn't follow AGENTS.md
    return "wrong_answer"

def ensure_custom_agent():
    """Register a custom Managed Agent carrying AGENTS.md. Returns agent_id or None."""
    spec = {
        "id": "exp-portability-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "Follow the operating rules in your AGENTS.md exactly.",
        "base_environment": {
            "type": "remote",
            "sources": [{"type": "inline", "target": ".agents/AGENTS.md", "content": AGENTS_MD}],
        },
    }
    res = gc.register_agent(spec)
    json.dump(res, open(os.path.join(DATA, "custom_agent_register.json"), "w"), indent=2, default=str)
    if res.get("ok"):
        j = res["json"]
        return j.get("id") or j.get("name", "").split("/")[-1] or "exp-portability-agent"
    # tolerate "already exists" so re-runs still use the agent
    err = (res.get("error") or "").lower()
    if res.get("status") in (409,) or "exist" in err or "already" in err:
        return "exp-portability-agent"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="T1,T2,T3")
    ap.add_argument("--arms", default="A,B")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    task_ids = [t.strip() for t in args.tasks.split(",")]
    arms = [a.strip() for a in args.arms.split(",")]
    custom_agent_id = None
    if "T4" in task_ids and "A" in arms:
        print("registering custom agent (AGENTS.md)...")
        custom_agent_id = ensure_custom_agent()
        print("  custom agent id:", custom_agent_id)

    jobs = []
    for tid in task_ids:
        task = dict(TASKS[tid]); task["_id"] = tid
        if tid == "T4":
            task["_custom_agent_id"] = custom_agent_id or "antigravity-preview-05-2026"
        for arm in arms:
            if tid != "T4" and arm == "C":
                continue  # Arm C only for portability
            if tid == "T4" and arm == "A" and not custom_agent_id:
                continue  # registration failed; skip Arm A for T4
            for i in range(args.n):
                jobs.append((tid, arm, i, task))

    print(f"running {len(jobs)} jobs ({task_ids} x {arms} x n={args.n}), concurrency={args.concurrency}")
    rows = []
    runfile = os.path.join(DATA, f"runs_{args.tag}.jsonl")
    fh = open(runfile, "w", encoding="utf-8")

    def do(job):
        tid, arm, i, task = job
        t0 = time.time()
        try:
            r = ARMS[arm](task)
        except Exception as e:
            r = {"arm": arm, "ok": False, "error": f"runner_exc: {type(e).__name__}: {e}", "text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": round(time.time() - t0, 2)}
        grade = task["grader"](r.get("text"))
        passed = grade["both"] if isinstance(grade, dict) else bool(grade)
        row = {"task": tid, "task_name": task["name"], "arm": arm, "run": i,
               "passed": passed, "grade": grade if isinstance(grade, dict) else None,
               "failure_mode": classify_failure(tid, r, passed),
               **{k: r.get(k) for k in ("ok", "status", "latency", "in_tok", "out_tok", "cost", "n_steps", "had_code_exec", "step_types", "interaction_status", "error")},
               "text": (r.get("text") or "")[:600]}
        return row

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(do, j): j for j in jobs}
        done = 0
        for fut in as_completed(futs):
            row = fut.result()
            rows.append(row)
            fh.write(json.dumps(row, default=str) + "\n"); fh.flush()
            done += 1
            print(f"  [{done}/{len(jobs)}] {row['task']}/{row['arm']}#{row['run']} pass={row['passed']} {row['latency']}s ${row['cost']:.5f} {row.get('failure_mode') or ''}")
    fh.close()
    write_summary(rows, args.tag, task_ids, arms, args.n)
    print("DONE. rows:", len(rows), "-> ", runfile)

def write_summary(rows, tag, task_ids, arms, n):
    from collections import defaultdict
    agg = defaultdict(lambda: {"n": 0, "pass": 0, "lat": [], "cost": 0.0, "fails": defaultdict(int)})
    for r in rows:
        k = (r["task"], r["arm"])
        a = agg[k]
        a["n"] += 1
        a["pass"] += 1 if r["passed"] else 0
        if r.get("latency"):
            a["lat"].append(r["latency"])
        a["cost"] += r.get("cost") or 0
        if r.get("failure_mode"):
            a["fails"][r["failure_mode"]] += 1
    lines = [f"# Run summary: {tag}", "",
             f"Tasks: {task_ids} | Arms: {arms} | N per cell: {n} | total runs: {len(rows)}",
             "_Cost is an ESTIMATE from token counts (gemini in/out $0.30/$2.50, claude $1/$5 per 1M). Treat as directional._", "",
             "| Task | Arm | N | Pass | Pass% | med latency | avg cost | top failure |",
             "|------|-----|---|------|-------|-------------|----------|-------------|"]
    def med(xs):
        xs = sorted(xs)
        return xs[len(xs)//2] if xs else 0
    for k in sorted(agg.keys()):
        a = agg[k]
        topf = max(a["fails"].items(), key=lambda x: x[1])[0] if a["fails"] else "-"
        lines.append(f"| {k[0]} | {k[1]} | {a['n']} | {a['pass']} | {100*a['pass']//max(a['n'],1)}% | {med(a['lat'])}s | ${a['cost']/max(a['n'],1):.5f} | {topf} |")
    # failure taxonomy
    lines += ["", "## Failure taxonomy (all cells)", ""]
    tax = defaultdict(int)
    for r in rows:
        if r.get("failure_mode"):
            tax[r["failure_mode"]] += 1
    for f, c in sorted(tax.items(), key=lambda x: -x[1]):
        lines.append(f"- {f}: {c}")
    total_cost = sum((r.get("cost") or 0) for r in rows)
    lines += ["", f"**Total estimated cost this run: ${total_cost:.4f}**"]
    open(os.path.join(OUT, f"phase-run_{tag}.md"), "w", encoding="utf-8").write("\n".join(lines))

if __name__ == "__main__":
    main()
