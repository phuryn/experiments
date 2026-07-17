#!/usr/bin/env python3
"""Run Kimi K3 (via glm_claude_proxy on :8788 -> OpenRouter) through the Claude Code
harness on the three-harness read/reason tasks. Sequential (rate-limit friendly).
Captures raw stream-json, extracts assistant text, parses real token usage, writes
a kimi metrics CSV. Cost recomputed at OpenRouter K3 rates ($3/M in, $15/M out)."""
import json, subprocess, time, os
from pathlib import Path

ROOT = Path(r"<WORKDIR>")
TASKS = ROOT / "experiments/three-harness-202607/tasks"
RAW = ROOT / "Temp/data/three-harness/raw"
RAW.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "Temp/data/three-harness/metrics_kimi.csv"
PROXY = "http://localhost:8788"

# claude-arm read invocation disallowed tools (from manifest)
DENY = "Bash,PowerShell,Agent,Task,Edit,Write,NotebookEdit,WebFetch,WebSearch,KillShell,BashOutput"

# task -> (target cwd, timeout_s). claude-arm targets from manifest.
CELLS = {
    "T2": (ROOT / "Temp/three-harness/_scratch/T2_kimi", 300),
    "T3": (ROOT / "Temp/<APP>/buggy", 1500),
    "T5": (ROOT / "Temp/<APP>/baseline", 600),
    "T7": (ROOT / "Temp/three-harness/T7_repo", 900),
    "T8": (ROOT / "Temp/three-harness/T8_repo", 600),
}

def extract_text(rawpath):
    txts = []
    for line in rawpath.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ev = o.get("event", {})
        if ev.get("type") == "content_block_delta":
            d = ev.get("delta", {})
            if d.get("type") == "text_delta":
                txts.append(d.get("text", ""))
        if o.get("type") == "assistant":
            for c in o.get("message", {}).get("content", []):
                if c.get("type") == "text":
                    txts.append(c.get("text", ""))
    return "".join(txts)

def final_usage(rawpath):
    for line in reversed(rawpath.read_text(encoding="utf-8", errors="replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "result":
            u = o.get("usage", {})
            return {
                "input": u.get("input_tokens", 0),
                "cache_read": u.get("cache_read_input_tokens", 0),
                "output": u.get("output_tokens", 0),
                "wall": o.get("duration_ms", 0) / 1000.0,
            }
    return None

def run_cell(task, cwd, timeout):
    prompt = (TASKS / f"{task}.md").read_text(encoding="utf-8")
    rawpath = RAW / f"{task}_kimi.jsonl"
    cwd.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["ANTHROPIC_BASE_URL"] = PROXY
    env["ANTHROPIC_AUTH_TOKEN"] = "dummy"
    cmd = ["claude", "-p", prompt, "--model", "claude-opus-4-8", "--effort", "high",
           "--output-format", "stream-json", "--include-partial-messages", "--verbose",
           "--disallowedTools", DENY]
    t0 = time.time()
    exit_code = "0"
    for attempt in (1, 2):  # one retry on failure (429 pool limits)
        try:
            with open(rawpath, "w", encoding="utf-8") as f:
                p = subprocess.run(cmd, cwd=str(cwd), env=env, stdout=f,
                                   stderr=subprocess.STDOUT, timeout=timeout)
            if p.returncode == 0:
                exit_code = "0"
                break
            exit_code = str(p.returncode)
        except subprocess.TimeoutExpired:
            exit_code = "timeout"
            break
        if attempt == 1:
            time.sleep(20)  # backoff before retry
    wall = time.time() - t0
    txt = extract_text(rawpath)
    (RAW / f"{task}_kimi.txt").write_text(txt, encoding="utf-8")
    u = final_usage(rawpath) or {"input": 0, "cache_read": 0, "output": 0, "wall": wall}
    cost = u["input"] * 3.0 / 1e6 + u["output"] * 15.0 / 1e6
    return {"task": task, "wall_s": round(u.get("wall", wall), 1), "input": u["input"],
            "cache_read": u["cache_read"], "output": u["output"],
            "cost_k3": round(cost, 4), "exit": exit_code, "text_chars": len(txt)}

def main():
    rows = []
    hdr = "task,model,engine_label,effort,wall_s,input_tok,cache_read_tok,output_tok,cost_k3_usd,exit,text_chars\n"
    CSV.write_text(hdr, encoding="utf-8")
    for task, (cwd, to) in CELLS.items():
        print(f"[{time.strftime('%H:%M:%S')}] running {task} (cwd={cwd.name}, timeout={to}s)...", flush=True)
        r = run_cell(task, cwd, to)
        rows.append(r)
        with open(CSV, "a", encoding="utf-8") as f:
            f.write(f"{r['task']},kimi,Kimi K3,high,{r['wall_s']},{r['input']},{r['cache_read']},"
                    f"{r['output']},{r['cost_k3']},{r['exit']},{r['text_chars']}\n")
        print(f"  -> {task}: wall={r['wall_s']}s out={r['output']} cost=${r['cost_k3']} "
              f"exit={r['exit']} chars={r['text_chars']}", flush=True)
    print("DONE. metrics_kimi.csv written.", flush=True)
    for r in rows:
        print(r, flush=True)

if __name__ == "__main__":
    main()
