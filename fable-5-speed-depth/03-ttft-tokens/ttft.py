#!/usr/bin/env python3
"""TTFT + exact token counts: Opus vs Fable, stream-json with partial messages.
Emits CSV: TTFT,round,prompt_id,model,rc,t_first_text,t_total,output_tokens,input_tokens,chars
"""
import json, subprocess, sys, time

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
PROMPTS = {
    "easy": "Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks.",
    "reason": "How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits as n (treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number and the list of such n.",
}

def run_one(rnd, pid, prompt, model):
    cmd = ["claude", "-p", prompt, "--model", model,
           "--output-format", "stream-json", "--include-partial-messages",
           "--verbose", "--disallowedTools", DENY]
    t0 = time.monotonic()
    t_first_any = None   # first model activity (thinking or text)
    t_first_text = None  # first visible text (user-perceived latency)
    out_tokens = in_tokens = chars = -1
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for line in proc.stdout:
        now = time.monotonic()
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        et = ev.get("type")
        dtype = None
        if et == "stream_event":
            dtype = (ev.get("event", {}).get("delta", {}) or {}).get("type")
        if t_first_any is None and (dtype in ("text_delta", "thinking_delta") or et == "assistant"):
            t_first_any = now - t0
        if t_first_text is None and (dtype == "text_delta" or et == "assistant"):
            t_first_text = now - t0
        if et == "result":
            usage = ev.get("usage", {}) or {}
            out_tokens = usage.get("output_tokens", -1)
            in_tokens = usage.get("input_tokens", -1)
            chars = len(ev.get("result", "") or "")
    proc.wait()
    t_total = time.monotonic() - t0
    fa = f"{t_first_any:.3f}" if t_first_any is not None else "-1"
    ft = f"{t_first_text:.3f}" if t_first_text is not None else "-1"
    print(f"TTFT,{rnd},{pid},{model},{proc.returncode},{fa},{ft},{t_total:.3f},{out_tokens},{in_tokens},{chars}", flush=True)

for rnd in (1, 2, 3):
    for pid, prompt in PROMPTS.items():
        for model in ("opus", "fable"):
            run_one(rnd, pid, prompt, model)
print("########## TTFT DONE ##########", flush=True)
