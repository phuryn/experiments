"""Run the same comparison battery (T1-T3) on Anthropic:
  - managed = Anthropic Managed Agents (hosted loop, claude-haiku-4-5 + toolset)
  - single  = one Messages call (claude-haiku-4-5 + code execution tool)
Captures latency + token cost. Writes data/anthropic_runs.jsonl + outputs/phase-anthropic.md.
"""
import json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc
import anthropic
from runner import TASKS  # reuse T1-T3 prompts + graders

BETA = ["managed-agents-2026-04-01"]
MODEL = "claude-haiku-4-5"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "outputs")
client = anthropic.Anthropic(api_key=gc._load_key("ANTHROPIC_API_KEY"))

# haiku pricing estimate ($/1M): in 1.00, out 5.00, cache-write 1.25x in, cache-read 0.10x in
P_IN, P_OUT = 1.00, 5.00

def cost_from_usage(u):
    if u is None:
        return 0, 0, 0.0
    inp = getattr(u, "input_tokens", 0) or 0
    out = getattr(u, "output_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cc_obj = getattr(u, "cache_creation", None)
    cc = 0
    if cc_obj is not None:
        cc = (getattr(cc_obj, "ephemeral_5m_input_tokens", 0) or 0) + (getattr(cc_obj, "ephemeral_1h_input_tokens", 0) or 0)
    cost = (inp * P_IN + out * P_OUT + cc * P_IN * 1.25 + cr * P_IN * 0.10) / 1e6
    return inp + cc + cr, out, cost

# ---- shared managed env + agent (created once) ----
def setup_managed():
    env = client.beta.environments.create(name="exp-cmp-env", config={"type": "cloud", "networking": {"type": "unrestricted"}}, betas=BETA)
    agent = client.beta.agents.create(
        name="exp-cmp-agent", model=MODEL,
        system="You are precise. Use tools/code when needed. Output only the final answer.",
        tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}], betas=BETA)
    return env.id, agent.id, agent.version

def run_managed(task_text, env_id, agent_id, agent_ver):
    t0 = time.time()
    session = client.beta.sessions.create(agent={"type": "agent", "id": agent_id, "version": agent_ver}, environment_id=env_id, betas=BETA)
    client.beta.sessions.events.send(session_id=session.id, events=[{"type": "user.message", "content": [{"type": "text", "text": task_text}]}], betas=BETA)
    texts, used_tool = [], False
    with client.beta.sessions.events.stream(session_id=session.id, betas=BETA) as stream:
        for ev in stream:
            et = getattr(ev, "type", "")
            if et == "agent.tool_use":
                used_tool = True
            content = getattr(ev, "content", None)
            if content and et == "agent.message":
                for b in content:
                    if getattr(b, "type", None) == "text":
                        texts.append(b.text)
            if et == "session.status_terminated":
                break
            if et == "session.status_idle":
                sr = getattr(ev, "stop_reason", None)
                if not sr or getattr(sr, "type", None) != "requires_action":
                    break
    elapsed = time.time() - t0
    sess = client.beta.sessions.retrieve(session_id=session.id, betas=BETA)
    intok, outtok, cost = cost_from_usage(getattr(sess, "usage", None))
    return {"text": " ".join(texts), "latency": round(elapsed, 2), "in_tok": intok, "out_tok": outtok, "cost": cost, "used_tool": used_tool, "ok": True}

def run_single(task_text):
    t0 = time.time()
    # try code execution via beta messages; fall back to plain if the beta tool is unavailable
    try:
        resp = client.beta.messages.create(model=MODEL, max_tokens=1024,
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
            betas=["code-execution-2025-08-25"],
            messages=[{"role": "user", "content": task_text}])
        tool = True
    except Exception:
        resp = client.messages.create(model=MODEL, max_tokens=1024, messages=[{"role": "user", "content": task_text}])
        tool = False
    elapsed = time.time() - t0
    text = " ".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    u = resp.usage
    inp = getattr(u, "input_tokens", 0); out = getattr(u, "output_tokens", 0)
    cost = (inp * P_IN + out * P_OUT) / 1e6
    return {"text": text, "latency": round(elapsed, 2), "in_tok": inp, "out_tok": out, "cost": cost, "used_tool": tool, "ok": True}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--tasks", default="T1,T2,T3")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    task_ids = args.tasks.split(",")

    print("setting up managed env+agent...")
    env_id, agent_id, agent_ver = setup_managed()
    print("  env", env_id, "agent", agent_id)

    jobs = []
    for tid in task_ids:
        for arm in ("managed", "single"):
            for i in range(args.n):
                jobs.append((tid, arm, i))
    print(f"running {len(jobs)} jobs (T{task_ids} x [managed,single] x {args.n})")

    rows = []
    fh = open(os.path.join(DATA, "anthropic_runs.jsonl"), "w", encoding="utf-8")

    def do(job):
        tid, arm, i = job
        task = TASKS[tid]
        try:
            r = run_managed(task["prompt"], env_id, agent_id, agent_ver) if arm == "managed" else run_single(task["prompt"])
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
            print(f"  [{done}/{len(jobs)}] {row['task']}/{row['arm']}#{row['run']} pass={row['passed']} {row['latency']}s ${row['cost']:.5f}")
    fh.close()
    try:
        client.beta.agents.archive(agent_id, betas=BETA)
    except Exception:
        pass
    write_report(rows, args.n)

def write_report(rows, n):
    from collections import defaultdict
    import statistics as st
    cells = defaultdict(list)
    for r in rows:
        cells[(r["task"], r["arm"])].append(r)
    def med(xs): return round(st.median(xs), 2) if xs else 0
    L = ["# Anthropic: managed vs single-call (claude-haiku-4-5)", "",
         f"Same T1-T3 battery. N={n}/cell. Cost = token estimate (haiku $1/$5 per 1M + cache); managed hosted-compute overhead not in tokens, so managed cost is a floor.", "",
         "| Task | Arm | N | Pass% | Median latency | Avg cost | % used tool |",
         "|------|-----|---|-------|----------------|----------|-------------|"]
    for k in sorted(cells):
        rs = cells[k]; npass = sum(1 for r in rs if r["passed"])
        L.append(f"| {k[0]} | {k[1]} | {len(rs)} | {round(100*npass/len(rs))}% | {med([r['latency'] for r in rs if r.get('latency')])}s | ${st.mean([r['cost'] or 0 for r in rs]):.5f} | {round(100*sum(1 for r in rs if r.get('used_tool'))/len(rs))}% |")
    # managed vs single multipliers
    L += ["", "## Managed vs single (Anthropic, same model)", "", "| Task | managed $ | single $ | cost x | managed lat | single lat | lat x |", "|------|-----------|----------|--------|-------------|------------|-------|"]
    for tid in sorted({k[0] for k in cells}):
        if (tid, "managed") in cells and (tid, "single") in cells:
            m = cells[(tid, "managed")]; s = cells[(tid, "single")]
            mc = st.mean([r["cost"] or 0 for r in m]); sc = st.mean([r["cost"] or 0 for r in s]) or 1e-9
            ml = med([r["latency"] for r in m]); sl = med([r["latency"] for r in s]) or 1e-9
            L.append(f"| {tid} | ${mc:.5f} | ${sc:.5f} | {mc/sc:.1f}x | {ml}s | {sl}s | {ml/sl:.1f}x |")
    total = sum(r.get("cost") or 0 for r in rows)
    L += ["", f"**Total estimated cost this run: ${total:.4f}**"]
    open(os.path.join(OUT, "phase-anthropic.md"), "w", encoding="utf-8").write("\n".join(L))
    print("-> outputs/phase-anthropic.md")

if __name__ == "__main__":
    main()
