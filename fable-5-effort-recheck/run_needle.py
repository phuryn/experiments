#!/usr/bin/env python3
"""Needle tier: the proven planted cross-file bug (one-liner follower-ceiling
clash), effort-swept. 2 models x 5 efforts x n=10 = 100 runs, 3 matched lanes.

Prompt is VERBATIM the day-4 QAUDIT that produced the Fable 20/30 / Opus 2/30
baselines (fable-5-day-4/02.../run_set02.py). Grading per needle_expected.json
(loose keyword grader + strict both-sides proxy from the recorded scheme).

Appends to runs.csv (13th column loose_score added by migrate step in main()).
Stop rule: 5 consecutive rc!=0 aborts.
"""
import csv, json, os, random, re, shutil, subprocess, sys, threading, time
from datetime import datetime

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-return-0703")
ANS = os.path.join(OUT, "answers")
os.makedirs(ANS, exist_ok=True)

DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
ROUNDS = 10
LANES = 6
TIMEOUT = 900
EFFORTS = ["low", "medium", "high", "xhigh", "max"]

QAUDIT = ("Audit knowledge/craft/human-signals.md, knowledge/craft/word_choice.md, and "
          "knowledge/craft/draft-gate.md for contradictions. Find places where they disagree, "
          "quote both sides of each contradiction, and recommend a fix for each. Be thorough.")

LOOSE = re.compile(r"50K|75K|one-liner ceiling|<50")
STRICT_A = re.compile(r"50K")
STRICT_B = re.compile(r"75K|one-liner ceiling")

CLAUDE = shutil.which("claude")
if not CLAUDE:
    sys.exit("claude CLI not found on PATH")

CHILD_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_EFFORT"}

def claude_cmd(model, effort):
    base = [CLAUDE, "-p", QAUDIT, "--effort", effort,
            "--output-format", "json", "--disallowedTools", DENY]
    if model == "opus":
        base[1:1] = ["--model", "claude-opus-4-8"]
    if CLAUDE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c"] + base
    return base

lock = threading.Lock()
csv_path = os.path.join(OUT, "runs.csv")
prog_path = os.path.join(OUT, "progress.log")
done_count = [0]
consec_fail = [0]
stop = threading.Event()

def migrate_csv():
    """Add loose_score column to existing runs.csv (empty for non-needle rows)."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if rows and rows[0][-1] != "loose_score":
        rows[0].append("loose_score")
        for r in rows[1:]:
            r.append("")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

def log_row(row):
    with lock:
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        done_count[0] += 1
        with open(prog_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} done(needle)={done_count[0]} "
                    f"needle/{row[2]}/{row[3]} r{row[4]} rc={row[11]} {row[5]}s "
                    f"out_tok={row[6]} strict={row[10]} loose={row[12]}\n")

def run_one(model, effort, rnd):
    run_id = f"needle-{model}-{effort}-r{rnd:02d}"
    t0 = time.monotonic()
    try:
        p = subprocess.run(claude_cmd(model, effort), cwd=REPO,
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

    strict = 1 if (rc == 0 and STRICT_A.search(text) and STRICT_B.search(text)) else 0
    loose = 1 if (rc == 0 and LOOSE.search(text)) else 0
    with open(os.path.join(ANS, run_id + ".json"), "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "rc": rc, "wall_seconds": secs,
                   "stderr": stderr[-2000:], "cli_json": meta if meta is not None else raw[-4000:]},
                  f, indent=1)
    with lock:
        if rc != 0:
            consec_fail[0] += 1
            if consec_fail[0] >= 5:
                stop.set()
        else:
            consec_fail[0] = 0
    log_row([datetime.now().isoformat(timespec="seconds"), "needle", model, effort,
             rnd, secs, out_tok, "", in_tok, len(text), strict, rc, loose])

CELLS = [(m, e) for m in ("fable", "opus") for e in EFFORTS]

def cell_state():
    """(model, effort) -> {'clean': [strict...], 'rounds_used': set()} from runs.csv."""
    state = {c: {"clean": [], "rounds_used": set()} for c in CELLS}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["task"] != "needle":
                continue
            c = (row["model"], row["effort"])
            if c not in state:
                continue
            state[c]["rounds_used"].add(int(row["round"]))
            if row["rc"] == "0":
                state[c]["clean"].append(int(row["correct_or_score"]))
    return state

def queue_to(targets):
    """Runs needed to bring each cell's CLEAN count to its target, with fresh round numbers."""
    state = cell_state()
    runs = []
    for c, target in targets.items():
        need = target - len(state[c]["clean"])
        rnd, added = 1, 0
        while added < need:
            if rnd not in state[c]["rounds_used"]:
                runs.append((c[0], c[1], rnd))
                added += 1
            rnd += 1
    random.Random(99).shuffle(runs)
    return runs

def lane_worker(lane, jobs):
    time.sleep(lane * 4)
    for job in jobs:
        if stop.is_set():
            return
        run_one(*job)

def run_phase(runs, label):
    lanes = [runs[i::LANES] for i in range(LANES)]
    threads = [threading.Thread(target=lane_worker, args=(i, jobs)) for i, jobs in enumerate(lanes)]
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"phase {label}: {len(runs)} runs dispatched")

def main():
    migrate_csv()
    t0 = time.monotonic()
    # FLAT n=5 per cell, every cell, no extensions (Pawel final call 2026-07-03), 6 lanes
    run_phase(queue_to({c: 5 for c in CELLS}), "A(n=5,flat)")
    verdict = "ABORTED (5 consecutive failures)" if stop.is_set() else "DONE"
    print(f"NEEDLE {verdict}: {done_count[0]} new runs in {round((time.monotonic()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
