#!/usr/bin/env python3
"""Set 02 re-run at n=10: speed head-to-head (5 short repo questions, default effort),
heavy multi-file audit (n=1 -> n=10 per model), plus effort-default pin-check
(Q1 at explicit --effort high vs the default rows, both models).

Same lane design as set 01: 3 matched lanes, fixed-seed shuffle, content-free CSV.
Outputs: Temp/output/fable5-n10/set02.csv + answers/ (private, gitignored).
CSV: ts,run_id,lane,exp,model,effort,q,round,rc,seconds,chars
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
TIMEOUT = 600
MODEL_IDS = {"fable": "claude-fable-5", "opus": "opus"}

QS = {
    "Q1": "What tool does CLAUDE.md say to use for exporting infographics, and why not headless playwright? One sentence.",
    "Q2": "Per knowledge/platforms/substack/paywall-patterns.md, where should the paywall cut land? One sentence.",
    "Q3": "What are the three buckets in Section 5.1 of Articles/Fable-5-Guide/draft.md? Three words.",
    "Q4": "What does tools/README.md say is the cheapest data-fetching tool? One sentence.",
    "Q5": "How many lenses does knowledge/lenses/INDEX.md list? One number.",
}
QAUDIT = ("Audit knowledge/craft/human-signals.md, knowledge/craft/word_choice.md, and "
          "knowledge/craft/draft-gate.md for contradictions. Find places where they disagree, "
          "quote both sides of each contradiction, and recommend a fix for each. Be thorough.")

def round_range():
    if "--rounds" in sys.argv:
        a, b = sys.argv[sys.argv.index("--rounds") + 1].split("-")
        return int(a), int(b)
    return 1, ROUNDS

def build_runs():
    runs = []
    lo, hi = round_range()
    for r in range(lo, hi + 1):
        for model in ("opus", "fable"):
            for q, prompt in QS.items():
                runs.append(("speed", model, "", q, r, prompt))
            runs.append(("audit", model, "", "AUD", r, QAUDIT))
            runs.append(("pin", model, "high", "Q1", r, QS["Q1"]))
    random.Random(43).shuffle(runs)
    return runs

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

def claude_cmd(prompt, model, effort):
    base = [CLAUDE, "-p", prompt, "--model", MODEL_IDS[model], "--disallowedTools", DENY]
    if effort:
        base += ["--effort", effort]
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c"] + base
    return base

TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
SUF = f"-{TAG}" if TAG else ""
lock = threading.Lock()
csv_path = os.path.join(OUT, f"set02{SUF}.csv")
prog_path = os.path.join(OUT, f"set02{SUF}_progress.log")
done_count = [0]

def log_row(row):
    with lock:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        done_count[0] += 1
        with open(prog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} done={done_count[0]} "
                    f"{row[3]}/{row[4]}/{row[6]} r{row[7]} rc={row[8]} {row[9]}s\n")

def run_one(lane, exp, model, effort, q, rnd, prompt):
    run_id = f"s02{SUF}-{exp}-{model}-{q}-r{rnd:02d}"
    t0 = time.monotonic()
    try:
        p = subprocess.run(claude_cmd(prompt, model, effort), cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT)
        rc, out, chars = p.returncode, (p.stdout or "") + ("\n[stderr]\n" + p.stderr if p.stderr else ""), len(p.stdout or "")
    except subprocess.TimeoutExpired:
        rc, out, chars = -9, "[timeout]", -1
    secs = round(time.monotonic() - t0, 3)
    with open(os.path.join(ANS, run_id + ".txt"), "w", encoding="utf-8") as f:
        f.write(out)
    log_row([datetime.now().isoformat(timespec="seconds"), run_id, lane,
             exp, model, effort or "default", q, rnd, rc, secs, chars])

def lane_worker(lane, jobs):
    time.sleep(lane * 4)
    for (exp, model, effort, q, rnd, prompt) in jobs:
        run_one(lane, exp, model, effort, q, rnd, prompt)

def main():
    runs = build_runs()
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["ts", "run_id", "lane", "exp", "model", "effort", "q", "round", "rc", "seconds", "chars"])
    lanes = [runs[i::LANES] for i in range(LANES)]
    threads = [threading.Thread(target=lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"SET02 DONE: {len(runs)} runs in {round((time.monotonic()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
