#!/usr/bin/env python3
"""Re-run ONLY the K3 T6 (implement-to-spec) write cell — T4 already passed, so we do
NOT touch it. Same hardened proxy (8789), write mode. Reuses run_kimi_write helpers."""
import json, subprocess, time, os
from pathlib import Path

ROOT = Path(r"<WORKDIR>")
TASKS = ROOT / "experiments/three-harness-202607/tasks"
RAW = ROOT / "Temp/data/three-harness/raw"
CSV = ROOT / "Temp/data/three-harness/metrics_kimi.csv"
PROXY = "http://localhost:8789"
DENY = "Bash,PowerShell,Agent,Task,WebFetch,WebSearch,KillShell,BashOutput"
CWD = ROOT / "Temp/three-harness/T6_kimi"
TIMEOUT = 1500  # short implement task; T3/T8 completed, this should too


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
            return {"input": u.get("input_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0),
                    "output": u.get("output_tokens", 0), "wall": o.get("duration_ms", 0) / 1000.0}
    return None


def main():
    task = "T6"
    prompt = (TASKS / f"{task}.md").read_text(encoding="utf-8")
    rawpath = RAW / f"{task}_kimi.jsonl"
    env = dict(os.environ)
    env["ANTHROPIC_BASE_URL"] = PROXY
    env["ANTHROPIC_AUTH_TOKEN"] = "dummy"
    cmd = ["claude", "-p", prompt, "--model", "claude-opus-4-8", "--effort", "high",
           "--output-format", "stream-json", "--include-partial-messages", "--verbose",
           "--permission-mode", "acceptEdits", "--disallowedTools", DENY]
    print(f"[{time.strftime('%H:%M:%S')}] T6 write-mode re-run (timeout={TIMEOUT}s)...", flush=True)
    t0 = time.time(); exit_code = "0"
    try:
        with open(rawpath, "w", encoding="utf-8") as f:
            p = subprocess.run(cmd, cwd=str(CWD), env=env, stdout=f, stderr=subprocess.STDOUT, timeout=TIMEOUT)
        exit_code = "0" if p.returncode == 0 else str(p.returncode)
    except subprocess.TimeoutExpired:
        exit_code = "timeout"
    wall = time.time() - t0
    txt = extract_text(rawpath); (RAW / f"{task}_kimi.txt").write_text(txt, encoding="utf-8")
    u = final_usage(rawpath) or {"input": 0, "cache_read": 0, "output": 0, "wall": wall}
    cost = u["input"] * 3.0 / 1e6 + u["output"] * 15.0 / 1e6
    lines = [ln for ln in CSV.read_text(encoding="utf-8").splitlines() if not ln.startswith(f"{task},")]
    lines.append(f"{task},kimi,Kimi K3,high,{round(u.get('wall', wall), 1)},{u['input']},{u['cache_read']},"
                 f"{u['output']},{round(cost, 4)},{exit_code},{len(txt)}")
    CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    created = (CWD / "src/utils/certificateId.ts").exists()
    print(f"  -> T6: wall={round(wall,1)}s out={u['output']} cost=${round(cost,4)} exit={exit_code} "
          f"chars={len(txt)} certificateId.ts_created={created}", flush=True)
    print("T6 RE-RUN DONE.", flush=True)


if __name__ == "__main__":
    main()
