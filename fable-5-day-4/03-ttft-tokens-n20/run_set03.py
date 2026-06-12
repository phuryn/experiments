#!/usr/bin/env python3
"""Set 03 re-run at n=10: TTFT + exact token counts, Opus vs Fable, stream-json.
Serial on purpose: first-token timing is the most startup-sensitive measurement,
so no concurrent load. Order shuffled per round (fixed seed).
CSV: ts,run_id,round,prompt_id,model,rc,t_first_any,t_first_text,t_total,output_tokens,input_tokens,chars
Result text goes to answers/ (private side); the CSV stays content-free.
"""
import csv, json, os, random, shutil, subprocess, sys, time
from datetime import datetime

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-n10")
ANS = os.path.join(OUT, "answers")
os.makedirs(ANS, exist_ok=True)

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
ROUNDS = 10
MODEL_IDS = {"fable": "claude-fable-5", "opus": "opus"}
PROMPTS = {
    "easy": "Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks.",
    "reason": ("How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits "
               "as n (treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number "
               "and the list of such n."),
}

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
SUF = f"-{TAG}" if TAG else ""
csv_path = os.path.join(OUT, f"set03{SUF}.csv")
if not os.path.exists(csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["ts", "run_id", "round", "prompt_id", "model", "rc",
                                "t_first_any", "t_first_text", "t_total",
                                "output_tokens", "input_tokens", "chars"])

def run_one(rnd, pid, prompt, model):
    run_id = f"s03{SUF}-{pid}-{model}-r{rnd:02d}"
    cmd = [CLAUDE, "-p", prompt, "--model", MODEL_IDS[model],
           "--output-format", "stream-json", "--include-partial-messages",
           "--verbose", "--disallowedTools", DENY]
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c"] + cmd
    t0 = time.monotonic()
    t_first_any = t_first_text = None
    out_tokens = in_tokens = chars = -1
    result_text = ""
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True,
                            encoding="utf-8", errors="replace")
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
            result_text = ev.get("result", "") or ""
            chars = len(result_text)
    proc.wait()
    t_total = time.monotonic() - t0
    with open(os.path.join(ANS, run_id + ".txt"), "w", encoding="utf-8") as f:
        f.write(result_text)
    fa = round(t_first_any, 3) if t_first_any is not None else -1
    ft = round(t_first_text, 3) if t_first_text is not None else -1
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), run_id, rnd, pid, model,
                                proc.returncode, fa, ft, round(t_total, 3), out_tokens, in_tokens, chars])
    print(f"{run_id} rc={proc.returncode} first_any={fa} total={round(t_total,1)}", flush=True)

def round_range():
    if "--rounds" in sys.argv:
        a, b = sys.argv[sys.argv.index("--rounds") + 1].split("-")
        return int(a), int(b)
    return 1, ROUNDS

jobs = []
_lo, _hi = round_range()
for rnd in range(_lo, _hi + 1):
    cell = [(pid, model) for pid in PROMPTS for model in ("opus", "fable")]
    random.Random(100 + rnd).shuffle(cell)
    jobs += [(rnd, pid, model) for pid, model in cell]

t0 = time.monotonic()
for rnd, pid, model in jobs:
    run_one(rnd, pid, PROMPTS[pid], model)
print(f"SET03 DONE: {len(jobs)} runs in {round((time.monotonic()-t0)/60,1)} min")
