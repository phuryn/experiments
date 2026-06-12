#!/usr/bin/env python3
"""Set 01 re-run at n=10: effort dial (easy / realistic / hard tiers + xyz control).

Design: 3 matched lanes (threads). Full run list = every cell x 10 rounds,
shuffled with a fixed seed, dealt round-robin so each lane carries a balanced
mix of models/efforts/tiers -> contention is symmetric, ratios stay clean.

Output (all local, gitignored):
  Temp/output/fable5-n10/set01.csv            content-free receipts (one row per run)
  Temp/output/fable5-n10/answers/<id>.txt     answer bodies (private side, never published)
  Temp/output/fable5-n10/set01_progress.log   heartbeat
CSV: ts,run_id,lane,tier,model,effort,round,rc,seconds,chars
"""
import csv, os, random, shutil, subprocess, sys, threading, time
from datetime import datetime

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-n10")
ANS = os.path.join(OUT, "answers")
os.makedirs(ANS, exist_ok=True)

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
ROUNDS = 10
LANES = 3
TIMEOUT = 420

QA = "Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks."
QM = ("Do knowledge/craft/human-signals.md and knowledge/craft/word_choice.md disagree about em dashes? "
      "Quote the load-bearing line from each, then reconcile any tension in under 120 words.")
QH = ("How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits as n "
      "(treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number and the list of such n.")

EFFORTS = ["low", "medium", "high", "xhigh", "max"]
# 'fable' alias is rejected by CLI 2.1.168 on this surface; full ID works (smoke-tested)
MODEL_IDS = {"fable": "claude-fable-5", "opus": "opus"}

def round_range():
    # --rounds 11-20 appends a second batch with distinct round numbers/run IDs
    if "--rounds" in sys.argv:
        a, b = sys.argv[sys.argv.index("--rounds") + 1].split("-")
        return int(a), int(b)
    return 1, ROUNDS

def build_runs():
    runs = []
    lo, hi = round_range()
    for r in range(lo, hi + 1):
        for eff in EFFORTS:
            runs.append(("easy", "fable", eff, r, QA))
            runs.append(("realistic", "fable", eff, r, QM))
            runs.append(("realistic", "opus", eff, r, QM))
            runs.append(("hard", "fable", eff, r, QH))
        runs.append(("control", "fable", "xyz", r, QA))
    random.Random(42).shuffle(runs)
    return runs

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

def claude_cmd(prompt, model, effort):
    base = [CLAUDE, "-p", prompt, "--model", MODEL_IDS[model], "--effort", effort,
            "--disallowedTools", DENY]
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c"] + base
    return base

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
SUF = f"-{TAG}" if TAG else ""
lock = threading.Lock()
csv_path = os.path.join(OUT, f"set01{SUF}.csv")
prog_path = os.path.join(OUT, f"set01{SUF}_progress.log")
done_count = [0]

def log_row(row):
    with lock:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        done_count[0] += 1
        with open(prog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} done={done_count[0]} {row[3]}/{row[4]}/{row[5]} r{row[6]} rc={row[7]} {row[8]}s\n")

def run_one(lane, idx, tier, model, effort, rnd, prompt):
    run_id = f"s01{SUF}-{tier}-{model}-{effort}-r{rnd:02d}"
    t0 = time.monotonic()
    try:
        p = subprocess.run(claude_cmd(prompt, model, effort), cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT)
        rc, out = p.returncode, (p.stdout or "") + ("\n[stderr]\n" + p.stderr if p.stderr else "")
    except subprocess.TimeoutExpired:
        rc, out = -9, "[timeout]"
    secs = round(time.monotonic() - t0, 3)
    with open(os.path.join(ANS, run_id + ".txt"), "w", encoding="utf-8") as f:
        f.write(out)
    log_row([datetime.now().isoformat(timespec="seconds"), run_id, lane,
             tier, model, effort, rnd, rc, secs, len(p.stdout) if rc != -9 else -1])

def lane_worker(lane, jobs):
    time.sleep(lane * 4)  # stagger startup
    for i, (tier, model, effort, rnd, prompt) in enumerate(jobs):
        run_one(lane, i, tier, model, effort, rnd, prompt)

def main():
    smoke = "--smoke" in sys.argv
    runs = build_runs()
    if smoke:
        runs = [("easy", "fable", "low", 0, QA), ("control", "fable", "xyz", 0, QA)]
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["ts", "run_id", "lane", "tier", "model", "effort", "round", "rc", "seconds", "chars"])
    lanes = [runs[i::LANES] for i in range(LANES)] if not smoke else [runs]
    threads = [threading.Thread(target=lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"SET01 {'SMOKE ' if smoke else ''}DONE: {len(runs)} runs in {round((time.monotonic()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
