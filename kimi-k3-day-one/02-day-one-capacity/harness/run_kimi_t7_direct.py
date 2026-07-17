#!/usr/bin/env python3
"""Run T7 (doc-staleness audit) against Kimi K3 via Moonshot's OWN Anthropic-compatible
endpoint (https://api.moonshot.ai/anthropic) -- NO custom proxy.

Why: the OpenRouter path (kimi_proxy.py) kills T7 every time. That shim commits a 200
header then streams upstream chunks verbatim and only retries 429/5xx, so a single
degenerate 200 anywhere in the chain aborts the run (terminal_reason=api_error). T7 is
the longest tool chain in the battery, so it eats that risk on every attempt.

Driving Claude Code straight at Moonshot removes our shim from the path entirely and
lets Claude Code's OWN native 429 backoff handle the engine_overloaded_error the
Moonshot pool is currently returning (~50% of requests as of 2026-07-17 08:30).

METHODOLOGY NOTE: this measures T7 on a DIFFERENT TRANSPORT than K3's other cells
(T1-T6, T8 ran OpenRouter-via-proxy). The agentic scaffold (Claude Code, same tools,
same task prompt, same target repo) is identical, which is what the benchmark measures.
Flag the transport difference in any writeup.
"""
import json, subprocess, time, os
from pathlib import Path

ROOT = Path(r"<WORKDIR>")
TASKS = ROOT / "experiments/three-harness-202607/tasks"
RAW = ROOT / "Temp/data/three-harness/raw"
CSV = ROOT / "Temp/data/three-harness/metrics_kimi.csv"
T7_TARGET = ROOT / "Temp/three-harness/T7_repo"
# identical read-only manifest to the other T7 arms
DENY = "Bash,PowerShell,Agent,Task,Edit,Write,NotebookEdit,WebFetch,WebSearch,KillShell,BashOutput"
T7_TIMEOUT = 7200  # 2h ceiling
# kimi_proxy2 (empty-200 fix) -> OpenRouter. Moonshot's own /anthropic route was tried
# first and could not serve a single trivial `claude -p` in 5 min (engine_overloaded on
# Claude-Code-sized requests), while OpenRouter demonstrably has K3 throughput today
# (T6 landed there: 44 turns / 24 min). So: OpenRouter + the fixed shim.
BASE_URL = "http://localhost:8790"
MODEL = "claude-opus-4-8"  # proxy rewrites -> moonshotai/kimi-k3


def key():
    return "dummy"  # proxy injects the real OpenRouter key


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
            return {"input": u.get("input_tokens", 0),
                    "cache_read": u.get("cache_read_input_tokens", 0),
                    "output": u.get("output_tokens", 0),
                    "wall": o.get("duration_ms", 0) / 1000.0,
                    "terminal": o.get("terminal_reason"),
                    "is_error": o.get("is_error"),
                    "result": (o.get("result") or "")[:200]}
    return None


def main():
    prompt = (TASKS / "T7.md").read_text(encoding="utf-8")
    rawpath = RAW / "T7_kimi_direct.jsonl"
    env = dict(os.environ)
    env["ANTHROPIC_BASE_URL"] = BASE_URL
    env["ANTHROPIC_AUTH_TOKEN"] = key()
    env.pop("ANTHROPIC_API_KEY", None)  # must not take precedence over the Moonshot token
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--effort", "high",
           "--output-format", "stream-json", "--include-partial-messages", "--verbose",
           "--disallowedTools", DENY]
    print(f"[{time.strftime('%H:%M:%S')}] T7 DIRECT via {BASE_URL} model={MODEL} "
          f"(timeout={T7_TIMEOUT}s, no proxy)...", flush=True)
    t0 = time.time()
    exit_code = "0"
    try:
        with open(rawpath, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, cwd=str(T7_TARGET), env=env, stdout=f,
                               stderr=subprocess.STDOUT, timeout=T7_TIMEOUT)
        exit_code = "0" if p.returncode == 0 else str(p.returncode)
    except subprocess.TimeoutExpired:
        exit_code = "timeout"
    wall = time.time() - t0
    txt = extract_text(rawpath)
    (RAW / "T7_kimi_direct.txt").write_text(txt, encoding="utf-8")
    u = final_usage(rawpath) or {"input": 0, "cache_read": 0, "output": 0, "wall": wall}
    # K3 real OpenRouter-listed rates; cache reads billed (the runner bug fixed here)
    cost = u["input"] * 3.0 / 1e6 + u["output"] * 15.0 / 1e6 + u.get("cache_read", 0) * 0.30 / 1e6
    lines = [ln for ln in CSV.read_text(encoding="utf-8").splitlines() if not ln.startswith("T7_direct,")]
    lines.append(f"T7_direct,kimi,Kimi K3 (direct),high,{round(u.get('wall', wall), 1)},{u['input']},"
                 f"{u['cache_read']},{u['output']},{round(cost, 4)},{exit_code},{len(txt)}")
    CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> T7 DIRECT: wall={round(wall,1)}s out={u['output']} cost=${round(cost,4)} "
          f"exit={exit_code} chars={len(txt)}", flush=True)
    print(f"     terminal_reason={u.get('terminal')} is_error={u.get('is_error')}", flush=True)
    if u.get("result"):
        print(f"     result={u['result']}", flush=True)
    print("T7 DIRECT DONE.", flush=True)


if __name__ == "__main__":
    main()
