"""CLEAN managed-vs-local comparison (fixes the confounds Pawel flagged).

Axis: MANAGED (provider runs the full agent loop in their sandbox, one session/call)
      vs LOCAL (I run the loop on this machine: base API per step + LOCAL code execution).
Both are real multi-step tool-use loops. Tool execution local = free CPU.
Caching reported as-measured (managed auto-caches its context; local context is lean) -> transparent.

Providers: Google (gemini-3.5-flash), Anthropic (claude-haiku-4-5), OpenAI (gpt-5-mini).
Same T1-T3 tasks + graders. Writes data/clean_runs.jsonl + outputs/comparison-clean.md
"""
import argparse, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc
from runner import TASKS
import anthropic
from openai import OpenAI

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "outputs")
A_BETA = ["managed-agents-2026-04-01"]
GEM_MODEL, ANT_MODEL, OAI_MODEL = "gemini-3.5-flash", "claude-haiku-4-5", "gpt-5-mini"
PRICE = {"gem": (0.30, 2.50), "ant": (1.00, 5.00), "oai": (0.25, 2.00)}  # ($/1M in,out) estimates
aclient = anthropic.Anthropic(api_key=gc._load_key("ANTHROPIC_API_KEY"))
OAI_KEY = gc._load_key("OPENAI_API_KEY")
oclient = OpenAI(api_key=OAI_KEY)
# Pawel's real Agent Builder workflow (gpt-5-mini + code_interpreter, medium reasoning),
# published + invoked headlessly by ID via POST /v1/workflows/{id}/run.
OAI_WORKFLOW_ID = "wf_68f0aace15ec8190ac50ebb281f7af700abfb51ee810a303"

# ---------------- local tool executor ----------------
def run_python(code):
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code); path = f.name
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=20)
        os.unlink(path)
        return (r.stdout + (("\nSTDERR:\n" + r.stderr) if r.stderr else ""))[:4000]
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

PY_TOOL_DESC = "Execute a Python program and return its stdout. Use it to compute the answer."

# ---------------- LOCAL loops (native tool use, code runs HERE) ----------------
def local_anthropic(task):
    t0 = time.time(); intok = outtok = 0; steps = 0; used = False
    system = [{"type": "text", "text": "You are precise. Use the run_python tool to compute when helpful. Output only the final answer."}]
    tools = [{"name": "run_python", "description": PY_TOOL_DESC, "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}]
    msgs = [{"role": "user", "content": task}]
    text = ""
    for _ in range(6):
        steps += 1
        r = aclient.messages.create(model=ANT_MODEL, max_tokens=1024, system=system, tools=tools, messages=msgs)
        intok += r.usage.input_tokens; outtok += r.usage.output_tokens
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason == "tool_use":
            used = True; results = []
            for b in r.content:
                if b.type == "tool_use":
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": run_python(b.input.get("code", ""))})
            msgs.append({"role": "user", "content": results})
        else:
            text = " ".join(b.text for b in r.content if b.type == "text"); break
    pin, pout = PRICE["ant"]
    return {"text": text, "in_tok": intok, "out_tok": outtok, "cost": (intok * pin + outtok * pout) / 1e6, "latency": round(time.time() - t0, 2), "steps": steps, "used_tool": used}

def local_google(task):
    t0 = time.time(); intok = outtok = 0; steps = 0; used = False
    tools = [{"function_declarations": [{"name": "run_python", "description": PY_TOOL_DESC, "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}]}]
    contents = [{"role": "user", "parts": [{"text": task + "\nUse run_python to compute. Output only the final answer."}]}]
    text = ""
    for _ in range(6):
        steps += 1
        body = {"contents": contents, "tools": tools}
        res = gc._post(f"/models/{GEM_MODEL}:generateContent", body, timeout=120)
        if not res["ok"]:
            return {"text": "", "in_tok": intok, "out_tok": outtok, "cost": 0, "latency": round(time.time() - t0, 2), "steps": steps, "used_tool": used, "error": res.get("error", "")[:200]}
        j = res["json"]; um = j.get("usageMetadata", {})
        intok += um.get("promptTokenCount", 0); outtok += um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0)
        cand = (j.get("candidates") or [{}])[0]; parts = cand.get("content", {}).get("parts", [])
        contents.append({"role": "model", "parts": parts})
        fcs = [p["functionCall"] for p in parts if "functionCall" in p]
        if fcs:
            used = True; fr_parts = []
            for fc in fcs:
                out = run_python(fc.get("args", {}).get("code", ""))
                fr_parts.append({"functionResponse": {"name": fc["name"], "response": {"output": out}}})
            contents.append({"role": "user", "parts": fr_parts})
        else:
            text = " ".join(p.get("text", "") for p in parts if "text" in p); break
    pin, pout = PRICE["gem"]
    return {"text": text, "in_tok": intok, "out_tok": outtok, "cost": (intok * pin + outtok * pout) / 1e6, "latency": round(time.time() - t0, 2), "steps": steps, "used_tool": used}

def local_openai(task):
    t0 = time.time(); intok = outtok = 0; steps = 0; used = False
    tools = [{"type": "function", "function": {"name": "run_python", "description": PY_TOOL_DESC, "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}}]
    msgs = [{"role": "system", "content": "You are precise. Use run_python to compute. Output only the final answer."}, {"role": "user", "content": task}]
    text = ""
    for _ in range(6):
        steps += 1
        r = oclient.chat.completions.create(model=OAI_MODEL, messages=msgs, tools=tools)
        u = r.usage; intok += u.prompt_tokens; outtok += u.completion_tokens
        m = r.choices[0].message
        msgs.append({"role": "assistant", "content": m.content or "", "tool_calls": [tc.model_dump() for tc in (m.tool_calls or [])]})
        if m.tool_calls:
            used = True
            for tc in m.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                out = run_python(args.get("code", ""))
                msgs.append({"role": "tool", "tool_call_id": tc.id, "content": out})
        else:
            text = m.content or ""; break
    pin, pout = PRICE["oai"]
    return {"text": text, "in_tok": intok, "out_tok": outtok, "cost": (intok * pin + outtok * pout) / 1e6, "latency": round(time.time() - t0, 2), "steps": steps, "used_tool": used}

# ---------------- MANAGED loops (provider runs it) ----------------
def managed_google(task):
    t0 = time.time()
    res = gc.run_interaction(task, timeout=300)
    if not res.get("ok"):
        return {"text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": round(time.time() - t0, 2), "used_tool": False, "error": res.get("error", "")[:150]}
    j = res["json"]; u = j.get("usage", {})
    text = ""
    for s in reversed(j.get("steps", [])):
        if s.get("type") == "model_output":
            text = " ".join(p.get("text", "") for p in s.get("content", []) if isinstance(p, dict)); break
    ti = u.get("total_input_tokens", 0); to = u.get("total_output_tokens", 0) + u.get("total_thought_tokens", 0) + u.get("total_tool_use_tokens", 0)
    pin, pout = PRICE["gem"]
    return {"text": text, "in_tok": ti, "out_tok": to, "cost": (ti * pin + to * pout) / 1e6, "latency": round(res.get("elapsed", 0), 2), "used_tool": any(s.get("type") == "code_execution_call" for s in j.get("steps", []))}

_ANT_MA = {}
def managed_anthropic(task):
    if "env" not in _ANT_MA:
        env = aclient.beta.environments.create(name="clean-env", config={"type": "cloud", "networking": {"type": "unrestricted"}}, betas=A_BETA)
        ag = aclient.beta.agents.create(name="clean-agent", model=ANT_MODEL, system="You are precise. Use tools/code when needed. Output only the final answer.", tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}], betas=A_BETA)
        _ANT_MA["env"] = env.id; _ANT_MA["agent"] = ag.id; _ANT_MA["ver"] = ag.version
    t0 = time.time()
    s = aclient.beta.sessions.create(agent={"type": "agent", "id": _ANT_MA["agent"], "version": _ANT_MA["ver"]}, environment_id=_ANT_MA["env"], betas=A_BETA)
    aclient.beta.sessions.events.send(session_id=s.id, events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}], betas=A_BETA)
    texts = []; used = False
    with aclient.beta.sessions.events.stream(session_id=s.id, betas=A_BETA) as st:
        for ev in st:
            et = getattr(ev, "type", "")
            if et == "agent.tool_use": used = True
            if et == "agent.message":
                for b in (getattr(ev, "content", None) or []):
                    if getattr(b, "type", None) == "text": texts.append(b.text)
            if et == "session.status_terminated": break
            if et == "session.status_idle":
                sr = getattr(ev, "stop_reason", None)
                if not sr or getattr(sr, "type", None) != "requires_action": break
    elapsed = time.time() - t0
    sess = aclient.beta.sessions.retrieve(session_id=s.id, betas=A_BETA); u = getattr(sess, "usage", None)
    inp = getattr(u, "input_tokens", 0) or 0; out = getattr(u, "output_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    ccobj = getattr(u, "cache_creation", None)
    cc = ((getattr(ccobj, "ephemeral_5m_input_tokens", 0) or 0) + (getattr(ccobj, "ephemeral_1h_input_tokens", 0) or 0)) if ccobj else 0
    pin, pout = PRICE["ant"]
    cost = (inp * pin + out * pout + cc * pin * 1.25 + cr * pin * 0.10) / 1e6
    return {"text": " ".join(texts), "in_tok": inp + cc + cr, "out_tok": out, "cost": cost, "latency": round(elapsed, 2), "used_tool": used}

def _oai_walk(o, found):
    """Pull usage + output_text + code-tool signal out of a streamed workflow event."""
    if isinstance(o, dict):
        if isinstance(o.get("usage"), dict) and o["usage"].get("total_tokens"):
            found["usage"] = o["usage"]
        if o.get("type") == "output_text" and isinstance(o.get("text"), str):
            found.setdefault("texts", []).append(o["text"])
        # ACTUAL tool call (an output item), not the tool definition in the config event
        if "code_interpreter_call" in str(o.get("type", "")):
            found["used"] = True
        for v in o.values():
            _oai_walk(v, found)
    elif isinstance(o, list):
        for v in o:
            _oai_walk(v, found)

def managed_openai(task):
    """REAL hosted Agent Builder workflow: OpenAI runs the loop server-side, invoked by ID.
    Stream the run to recover usage + output (the non-streaming result.output is unmapped/null)."""
    t0 = time.time()
    body = {"input_data": {"input": [{"role": "user", "content": [{"type": "input_text", "text": task}]}],
                           "input_as_text": task}, "stream": True}
    req = urllib.request.Request("https://api.openai.com/v1/workflows/" + OAI_WORKFLOW_ID + "/run",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + OAI_KEY, "Content-Type": "application/json",
                                          "OpenAI-Beta": "workflows=v1", "Accept": "text/event-stream"})
    found = {}
    try:
        r = urllib.request.urlopen(req, timeout=300)
        for raw in r:
            s = raw.decode("utf-8", "replace").strip()
            if not s.startswith("data:"):
                continue
            try:
                d = json.loads(s[5:].strip())
            except Exception:
                continue
            _oai_walk(d, found)
    except urllib.error.HTTPError as e:
        return {"text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": round(time.time() - t0, 2),
                "used_tool": False, "error": ("HTTP %s: %s" % (e.code, e.read().decode()[:150]))}
    elapsed = time.time() - t0
    u = found.get("usage", {})
    inp = u.get("input_tokens", 0); out = u.get("output_tokens", 0)
    texts = found.get("texts", [])
    text = max(texts, key=len) if texts else ""
    used = found.get("used", False)
    pin, pout = PRICE["oai"]
    cost = (inp * pin + out * pout) / 1e6 + (0.03 if used else 0)
    return {"text": text, "in_tok": inp, "out_tok": out, "cost": cost, "latency": round(elapsed, 2), "used_tool": used}

ARMS = {
    ("google", "managed"): managed_google, ("google", "local"): local_google,
    ("anthropic", "managed"): managed_anthropic, ("anthropic", "local"): local_anthropic,
    ("openai", "managed"): managed_openai, ("openai", "local"): local_openai,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--tasks", default="T1,T2,T3")
    ap.add_argument("--providers", default="google,anthropic,openai")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    task_ids = args.tasks.split(","); provs = args.providers.split(",")
    # warm anthropic managed setup once (avoid race in threads)
    if "anthropic" in provs:
        managed_anthropic.__wrapped__ if False else None
        try:
            managed_anthropic("warmup: output OK")
        except Exception as e:
            print("anthropic warmup err:", e)
    jobs = [(p, arm, tid, i) for p in provs for arm in ("managed", "local") for tid in task_ids for i in range(args.n)]
    print(f"running {len(jobs)} jobs")
    rows = []; fh = open(os.path.join(DATA, "clean_runs.jsonl"), "w", encoding="utf-8")
    def do(job):
        p, arm, tid, i = job; task = TASKS[tid]
        try:
            r = ARMS[(p, arm)](task["prompt"])
        except Exception as e:
            r = {"text": "", "in_tok": 0, "out_tok": 0, "cost": 0, "latency": 0, "error": f"{type(e).__name__}: {e}"}
        passed = bool(task["grader"](r.get("text")))
        return {"provider": p, "arm": arm, "task": tid, "run": i, "passed": passed, **{k: r.get(k) for k in ("in_tok", "out_tok", "cost", "latency", "steps", "used_tool", "error")}, "text": (r.get("text") or "")[:200]}
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(do, j): j for j in jobs}; done = 0
        for fut in as_completed(futs):
            row = fut.result(); rows.append(row); fh.write(json.dumps(row, default=str) + "\n"); fh.flush(); done += 1
            print(f"  [{done}/{len(jobs)}] {row['provider']}/{row['arm']}/{row['task']}#{row['run']} pass={row['passed']} {row['latency']}s ${row['cost']:.5f} {(row.get('error') or '')[:50]}")
    fh.close()
    write_report(rows, args.n)

def write_report(rows, n):
    from collections import defaultdict
    import statistics as st
    cells = defaultdict(list)
    for r in rows: cells[(r["provider"], r["arm"])].append(r)
    def med(xs): return round(st.median(xs), 2) if xs else 0
    L = ["# CLEAN comparison: managed loop vs true local loop", "",
         f"Same T1-T3 tasks. N={n}/cell. MANAGED = provider runs the loop in its sandbox. LOCAL = I run the loop here (base API per step + local Python execution, free CPU). Cost = token estimate at tier rates (+ OpenAI code_interpreter $0.03/container; Anthropic-managed cache pricing). Caching reported as-used: managed auto-caches its large agent context; local context is lean.", "",
         "| Provider | Arm | N | Pass% | Median latency | Avg cost | % tool |",
         "|---|---|---|---|---|---|---|"]
    for k in sorted(cells):
        rs = cells[k]; np_ = sum(1 for r in rs if r["passed"])
        L.append(f"| {k[0]} | {k[1]} | {len(rs)} | {round(100*np_/len(rs))}% | {med([r['latency'] for r in rs if r.get('latency')])}s | ${st.mean([r['cost'] or 0 for r in rs]):.5f} | {round(100*sum(1 for r in rs if r.get('used_tool'))/max(len(rs),1))}% |")
    L += ["", "## Managed vs local (per provider)", "", "| Provider | managed $ | local $ | cost x | managed lat | local lat | lat x |", "|---|---|---|---|---|---|---|"]
    for p in sorted({k[0] for k in cells}):
        if (p, "managed") in cells and (p, "local") in cells:
            m = cells[(p, "managed")]; l = cells[(p, "local")]
            mc = st.mean([r["cost"] or 0 for r in m]); lc = st.mean([r["cost"] or 0 for r in l]) or 1e-9
            ml = med([r["latency"] for r in m]); ll = med([r["latency"] for r in l]) or 1e-9
            L.append(f"| {p} | ${mc:.5f} | ${lc:.5f} | {mc/lc:.1f}x | {ml}s | {ll}s | {ml/ll:.1f}x |")
    total = sum(r.get("cost") or 0 for r in rows)
    L += ["", f"**Total estimated cost: ${total:.4f}**"]
    open(os.path.join(OUT, "comparison-clean.md"), "w", encoding="utf-8").write("\n".join(L))
    print("-> outputs/comparison-clean.md")

if __name__ == "__main__":
    main()
