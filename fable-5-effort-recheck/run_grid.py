#!/usr/bin/env python3
"""Fable 5 return-build (2026-07-03) effort-dial benchmark, CLI 2.1.198.

Grid (n=8/cell, 160 runs):
  fable  x easy      x {low,medium,high,xhigh,max}
  fable  x realistic x 5 efforts
  fable  x audit     x 5 efforts   (planted-contradictions, graded 0-3)
  opus   x realistic x 5 efforts   (control, --model claude-opus-4-8)

Design mirrors day-4 run_set01.py: 3 matched lanes, fixed-seed shuffle,
round-robin deal, 4s lane stagger, wall-clock includes CLI startup,
write tools denied. Upgrades vs day-4: --output-format json (exact
output/input tokens from usage; no reasoning-token field exists, thinking
is folded into output_tokens), and the discriminating audit tier graded
mechanically against expected.json regexes (written before any run).

CLAUDE_EFFORT env var (found =xhigh on this box) is stripped from child
env; every run passes an explicit --effort flag. settings.json also has
effortLevel: xhigh persisted - irrelevant here since all flags are valid.

Stop rule: 5 consecutive rc!=0 runs aborts the grid.
"""
import csv, json, os, random, re, shutil, subprocess, sys, threading, time
from datetime import datetime

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-return-0703")
ANS = os.path.join(OUT, "answers")
os.makedirs(ANS, exist_ok=True)

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
ROUNDS = 8
LANES = 3
TIMEOUT = 420
EFFORTS = ["low", "medium", "high", "xhigh", "max"]

QA = "Explain in exactly 3 bullet points why nested subagents cost more than a flat fan-out of the same leaf tasks."
QM = ("Do knowledge/craft/human-signals.md and knowledge/craft/word_choice.md disagree about em dashes? "
     "Quote the load-bearing line from each, then reconcile any tension in under 120 words.")
QB = ("Read Temp/output/fable5-return-0703/audit/service-overview.md and "
     "Temp/output/fable5-return-0703/audit/deploy-runbook.md. "
     "List every factual contradiction between the two files. Be precise.")

EXPECTED = json.load(open(os.path.join(OUT, "expected.json"), encoding="utf-8"))
BUG_PATTERNS = [[re.compile(rx) for rx in c["match_all_regexes"]]
                for c in EXPECTED["contradictions"]]

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

CHILD_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_EFFORT"}

def claude_cmd(prompt, model, effort):
    base = [CLAUDE, "-p", prompt, "--effort", effort,
            "--output-format", "json", "--disallowedTools", DENY]
    if model == "opus":
        base[1:1] = ["--model", "claude-opus-4-8"]  # fable cells run the default model (verified = claude-fable-5)
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c"] + base
    return base

def grade(task, text):
    if task == "audit":
        return sum(1 for pats in BUG_PATTERNS if all(p.search(text) for p in pats))
    if task == "easy":  # exactly-3-bullets compliance
        bullets = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S", text))
        return 1 if bullets == 3 else 0
    return ""  # realistic: ungraded (day-4 parity)

def build_runs():
    runs = []
    for r in range(1, ROUNDS + 1):
        for eff in EFFORTS:
            runs.append(("easy", "fable", eff, r, QA))
            runs.append(("realistic", "fable", eff, r, QM))
            runs.append(("audit", "fable", eff, r, QB))
            runs.append(("realistic", "opus", eff, r, QM))
    random.Random(42).shuffle(runs)
    if "--resume" in sys.argv and os.path.exists(csv_path):
        done = set()
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["rc"] == "0":
                    done.add((row["task"], row["model"], row["effort"], int(row["round"])))
        runs = [x for x in runs if (x[0], x[1], x[2], x[3]) not in done]
        print(f"resume: {len(done)} clean rows found, {len(runs)} runs remaining")
    return runs

lock = threading.Lock()
csv_path = os.path.join(OUT, "runs.csv")
prog_path = os.path.join(OUT, "progress.log")
done_count = [0]
consec_fail = [0]
stop = threading.Event()

def log_row(row):
    with lock:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        done_count[0] += 1
        with open(prog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} done={done_count[0]} "
                    f"{row[1]}/{row[2]}/{row[3]} r{row[4]} rc={row[11]} {row[5]}s "
                    f"out_tok={row[6]} score={row[10]}\n")

def run_one(tier, model, effort, rnd, prompt):
    run_id = f"{tier}-{model}-{effort}-r{rnd:02d}"
    t0 = time.monotonic()
    try:
        p = subprocess.run(claude_cmd(prompt, model, effort), cwd=REPO,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT, env=CHILD_ENV)
        rc, raw = p.returncode, p.stdout or ""
        stderr = p.stderr or ""
    except subprocess.TimeoutExpired:
        rc, raw, stderr = -9, "", "[timeout]"
    secs = round(time.monotonic() - t0, 3)

    out_tok = in_tok = ""
    text = raw
    meta = None
    try:
        meta = json.loads(raw)
        u = meta.get("usage", {})
        out_tok = u.get("output_tokens", "")
        in_tok = u.get("input_tokens", "")
        text = meta.get("result", "") or ""
        if meta.get("is_error"):
            rc = rc if rc != 0 else 1
    except (json.JSONDecodeError, AttributeError):
        pass

    score = grade(tier, text) if rc == 0 else (0 if tier in ("audit", "easy") else "")
    with open(os.path.join(ANS, run_id + ".json"), "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "rc": rc, "wall_seconds": secs,
                   "stderr": stderr[-2000:], "cli_json": meta if meta is not None else raw[-4000:],
                   }, f, indent=1)

    with lock:
        if rc != 0:
            consec_fail[0] += 1
            if consec_fail[0] >= 5:
                stop.set()
        else:
            consec_fail[0] = 0
    log_row([datetime.now().isoformat(timespec="seconds"), tier, model, effort,
             rnd, secs, out_tok, "", in_tok, len(text), score, rc])

def lane_worker(lane, jobs):
    time.sleep(lane * 4)
    for job in jobs:
        if stop.is_set():
            return
        run_one(*job)

def main():
    runs = build_runs()
    if "--smoke" in sys.argv:
        runs = [("audit", "fable", "low", 0, QB)]
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["ts", "task", "model", "effort", "round", "seconds",
                                    "output_tokens", "reasoning_tokens", "input_tokens",
                                    "chars", "correct_or_score", "rc"])
    lanes = [runs[i::LANES] for i in range(LANES)] if "--smoke" not in sys.argv else [runs]
    threads = [threading.Thread(target=lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join()
    verdict = "ABORTED (5 consecutive failures)" if stop.is_set() else "DONE"
    print(f"GRID {verdict}: {done_count[0]}/{len(runs)} runs in {round((time.monotonic()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
