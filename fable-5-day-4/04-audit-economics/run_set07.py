#!/usr/bin/env python3
"""Set 07: cost per real finding. Same heavy 3-file audit as Set 02, but run with
--output-format json so every run yields billed usage (input/output/cache tokens)
and the CLI's total_cost_usd. n=10 per model, 3 matched lanes.

We compute cost two ways for the receipts:
  1. CLI-reported total_cost_usd
  2. usage x public API prices (Fable $10/$50, Opus $5/$25 per MTok; cache w x1.25, r x0.1)
Findings are counted post-hoc from the saved result text.

Outputs: Temp/output/fable5-n10/set07.csv + answers/s07-*.json (full receipts, private)
CSV: ts,run_id,lane,model,round,rc,seconds,in_tok,out_tok,cache_w,cache_r,cost_usd,chars
"""
import csv, json, os, random, shutil, subprocess, sys, threading, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_set02 import QAUDIT  # identical prompt -> comparable to Set 02 findings data

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-n10")
ANS = os.path.join(OUT, "answers")
os.makedirs(ANS, exist_ok=True)

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
ROUNDS = 10
LANES = 3
TIMEOUT = 700
MODEL_IDS = {"fable": "claude-fable-5", "opus": "opus"}

def round_range():
    if "--rounds" in sys.argv:
        a, b = sys.argv[sys.argv.index("--rounds") + 1].split("-")
        return int(a), int(b)
    return 1, ROUNDS

def build_runs():
    lo, hi = round_range()
    runs = [(model, r) for r in range(lo, hi + 1) for model in ("opus", "fable")]
    random.Random(47).shuffle(runs)
    return runs

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

def claude_cmd(model):
    base = [CLAUDE, "-p", QAUDIT, "--model", MODEL_IDS[model],
            "--disallowedTools", DENY, "--output-format", "json"]
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c"] + base
    return base

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
SUF = f"-{TAG}" if TAG else ""
lock = threading.Lock()
csv_path = os.path.join(OUT, f"set07{SUF}.csv")
prog_path = os.path.join(OUT, f"set07{SUF}_progress.log")
done_count = [0]

def log_row(row):
    with lock:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        done_count[0] += 1
        with open(prog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} done={done_count[0]} "
                    f"{row[3]} r{row[4]} rc={row[5]} {row[6]}s out_tok={row[8]} cost={row[11]}\n")

def run_one(lane, model, rnd):
    run_id = f"s07{SUF}-{model}-r{rnd:02d}"
    t0 = time.monotonic()
    try:
        p = subprocess.run(claude_cmd(model), cwd=REPO, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
        rc, raw = p.returncode, (p.stdout or "")
    except subprocess.TimeoutExpired:
        rc, raw = -9, "[timeout]"
    secs = round(time.monotonic() - t0, 3)
    in_tok = out_tok = cw = cr = cost = chars = -1
    if rc == 0:
        try:
            j = json.loads(raw)
            u = j.get("usage", {})
            in_tok = u.get("input_tokens", -1)
            out_tok = u.get("output_tokens", -1)
            cw = u.get("cache_creation_input_tokens", -1)
            cr = u.get("cache_read_input_tokens", -1)
            cost = j.get("total_cost_usd", -1)
            chars = len(j.get("result", ""))
        except (json.JSONDecodeError, AttributeError):
            rc = -8  # json parse failure, raw saved for inspection
    with open(os.path.join(ANS, run_id + ".json"), "w", encoding="utf-8") as f:
        f.write(raw)
    log_row([datetime.now().isoformat(timespec="seconds"), run_id, lane,
             model, rnd, rc, secs, in_tok, out_tok, cw, cr, cost, chars])

def lane_worker(lane, jobs):
    time.sleep(lane * 4)
    for (model, rnd) in jobs:
        run_one(lane, model, rnd)

def main():
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["ts", "run_id", "lane", "model", "round", "rc",
                                    "seconds", "in_tok", "out_tok", "cache_w", "cache_r",
                                    "cost_usd", "chars"])
    if "--smoke" in sys.argv:
        run_one(0, "fable", 0)
        print("SET07 SMOKE DONE — check CSV + answers/s07-fable-r00.json")
        return
    if "--validate" in sys.argv:
        # 2-run pricing cross-check: mined-cost math vs CLI total_cost_usd
        run_one(0, "opus", 0)
        run_one(0, "fable", 0)
        print("SET07 VALIDATE DONE — compare cost_usd vs mine_usage.py math")
        return
    runs = build_runs()
    lanes = [runs[i::LANES] for i in range(LANES)]
    threads = [threading.Thread(target=lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"SET07 DONE: {len(runs)} runs in {round((time.monotonic()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
