#!/usr/bin/env python3
"""three-harness-202607 orchestrator.

Runs each task through each model IN ITS NATIVE HARNESS, one round per cell, effort=high.
Captures wall-clock, the detailed token split, exit code, and the model's final report text.

  python runner.py --tasks T1..T8 --models claude,codex,grok [--only T1:grok,...] [--dry-run]
                   [--serial] [--force]

Per (task,model) cell:
  * launch the right CLI (templates below), cwd = the cell's target from manifest.json
  * wall-clock via time.monotonic around the subprocess
  * tokens parsed per-arm (see parse_* ); text -> Temp/data/three-harness/raw/<TASK>_<MODEL>.txt
  * one row appended to Temp/data/three-harness/metrics.csv
  * T1/T2 graded deterministically here; T3/T5/T7/T8 blind-judged later; T4/T6 via grade_T4/6.py
Idempotent: skips (task,model) already in metrics.csv unless --force. The 3 arms may run
concurrently (one subprocess per arm); --serial forces fully sequential.

NOTE (published copy): reference artifact. The private answer keys, seeded rig, and manifest
targets are withheld; this file is published verbatim except for machine-identifying paths,
which are replaced with <HOME>. It will not run as-is without the private rig.
"""
import argparse, csv, json, os, re, subprocess, sys, threading, time

HERE = os.path.abspath(os.path.dirname(__file__))
REPO = os.path.abspath(HERE + "/../..")                      # content repo root
MANIFEST = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
RAW_DIR = os.path.join(REPO, "Temp", "data", "three-harness", "raw")
CSV_PATH = os.path.join(REPO, "Temp", "data", "three-harness", "metrics.csv")
SCRATCH = os.path.join(REPO, "Temp", "three-harness", "_scratch")
CODEX = "<HOME>/.vscode/extensions/openai.chatgpt-26.5707.31123-win32-x64/bin/windows-x86_64/codex.exe"
GROK_ACP = os.path.join(HERE, "grok_acp.py")

CSV_COLS = ["task","model","engine_label","effort","wall_s","input_tok","cached_tok",
            "output_tok","reasoning_tok","total_tok","cost_est_usd","exit","notes","grade"]
CLAUDE_DENY_READ = "Bash,PowerShell,Agent,Task,Edit,Write,NotebookEdit,WebFetch,WebSearch,KillShell,BashOutput"
CLAUDE_DENY_WRITE = "Bash,PowerShell,Agent,Task,WebFetch,WebSearch,KillShell,BashOutput"
ENGINE = {"claude": "Opus 4.8", "codex": "GPT-5.5"}
GROK_MODEL = "grok-build"      # overridable via --grok-model (threaded into grok_acp.py)
# "codex56" is a SECOND codex arm (same binary/harness, different model slug), kept as a
# distinct model name so its rows/raw files/grades never clobber the gpt-5.5 "codex" arm.
CODEX56_MODEL = "gpt-5.6-sol"  # overridable via --codex-model (proven working slug on ChatGPT auth)
CODEX56_LABELS = {"gpt-5.6-sol": "GPT-5.6 Sol", "gpt-5.6-terra": "GPT-5.6 Terra",
                  "gpt-5.6-luna": "GPT-5.6 Luna"}
# Per-arm task-timeout overrides that must NOT touch the manifest (precedent: the 5.5
# codex T7 DNF'd at 900 s and was rerun at 1800 s — the new arm starts at 1800 s).
ARM_TIMEOUT_OVERRIDES = {("codex56", "T7"): 1800}

def grok_engine_label():
    """Engine label for the grok arm, read AT RUN TIME from the grok CLI's live model
    cache (system_prompt_label, e.g. 'Grok 4.3' / 'Grok 4.5'), so a different machine or
    model slug records what that engine actually self-labels. Falls back to the model's
    display name, then to the slug."""
    cache = os.path.expanduser("~/.grok/models_cache.json")
    try:
        d = json.load(open(cache, encoding="utf-8"))
        info = d["models"][GROK_MODEL]["info"]
        return info.get("system_prompt_label") or info.get("name") or GROK_MODEL
    except Exception:
        return GROK_MODEL

def engine_label(model):
    if model == "grok":
        return grok_engine_label()
    if model == "codex56":
        return CODEX56_LABELS.get(CODEX56_MODEL, CODEX56_MODEL)
    return ENGINE[model]

_csv_lock = threading.Lock()
_print_lock = threading.Lock()

def log(msg):
    with _print_lock:
        print(msg, flush=True)

# ---------------------------------------------------------------- helpers
def task_by_id(tid):
    for t in MANIFEST["tasks"]:
        if t["id"] == tid:
            return t
    raise KeyError(tid)

def resolve_target(task, model):
    key = "codex" if model == "codex56" else model   # codex56 reuses the codex targets
    tgt = task["targets"][key]
    p = tgt if os.path.isabs(tgt) else os.path.join(REPO, tgt)
    return os.path.abspath(p)

def prompt_text(task):
    with open(os.path.join(HERE, task["prompt_file"]), encoding="utf-8") as f:
        return f.read().strip()

def done_cells():
    if not os.path.exists(CSV_PATH):
        return set()
    out = set()
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.add((r["task"], r["model"]))
    return out

def append_row(row):
    with _csv_lock:
        newfile = not os.path.exists(CSV_PATH)
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLS)
            if newfile:
                w.writeheader()
            w.writerow({k: row.get(k, "") for k in CSV_COLS})

def kill_tree(proc):
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            proc.kill()
    except Exception:
        pass

def run_capture(cmd, cwd, timeout, env=None):
    """Run cmd, return (stdout, exit_code_or_'timeout', wall_s). Kills the tree on timeout."""
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace",
                            env=env or os.environ.copy())
    try:
        out, _ = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=15)
        except Exception:
            out = ""
        rc = "timeout"
    return out or "", rc, time.monotonic() - t0

# ---------------------------------------------------------------- grading (T1/T2)
def grade_math(text, expected):
    lines = [l for l in text.splitlines() if l.strip()]
    for line in reversed(lines[-4:]):                       # last few non-empty lines
        nums = [int(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*", line)]
        if expected in nums:
            return "correct"
    return "wrong"

# ---------------------------------------------------------------- claude arm
def parse_claude(stdout):
    text_pieces, result_text = [], ""
    usage = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "stream_event":
            d = (ev.get("event", {}) or {}).get("delta", {}) or {}
            if d.get("type") == "text_delta":
                text_pieces.append(d.get("text", ""))
        elif t == "result":
            usage = ev.get("usage", {}) or {}
            result_text = ev.get("result", "") or ""
    text = "".join(text_pieces) or result_text
    return text, usage

def run_claude(task, mode, cwd, timeout):
    prompt = prompt_text(task)
    deny = CLAUDE_DENY_WRITE if mode == "write" else CLAUDE_DENY_READ
    cmd = ["claude", "-p", prompt, "--model", "claude-opus-4-8", "--effort", "high",
           "--output-format", "stream-json", "--include-partial-messages", "--verbose",
           "--disallowedTools", deny]
    if mode == "write":
        cmd += ["--permission-mode", "acceptEdits"]
    out, rc, wall = run_capture(cmd, cwd, timeout)
    text, u = parse_claude(out)
    inp = u.get("input_tokens", 0) or 0
    cw = u.get("cache_creation_input_tokens", 0) or 0
    cr = u.get("cache_read_input_tokens", 0) or 0
    outp = u.get("output_tokens", 0) or 0
    total = inp + cw + cr + outp
    cost = (inp*5.0 + cw*6.25 + cr*0.5 + outp*25.0) / 1e6
    return {"text": text, "wall_s": wall, "exit": rc,
            "input_tok": inp, "cached_tok": cr, "output_tok": outp, "reasoning_tok": "",
            "total_tok": total, "cost_est_usd": round(cost, 4), "notes": f"cache_write={cw}"}

# ---------------------------------------------------------------- codex arm
def parse_codex(stdout):
    inp = cached = outp = reason = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "turn.completed":
            u = ev.get("usage", {}) or ev.get("turn", {}).get("usage", {}) or {}
            inp += u.get("input_tokens", 0) or 0
            cached += u.get("cached_input_tokens", 0) or 0
            outp += u.get("output_tokens", 0) or 0
            reason += u.get("reasoning_output_tokens", 0) or 0
    return inp, cached, outp, reason

def run_codex(task, mode, cwd, timeout, slug="gpt-5.5", tag="codex", extra_notes=""):
    prompt = prompt_text(task)
    sandbox = "workspace-write" if mode == "write" else "read-only"
    raw_out = os.path.join(RAW_DIR, f"{task['id']}_{tag}.txt")     # -o MUST be absolute
    cmd = [CODEX, "exec", "--json", "-o", raw_out, "--skip-git-repo-check",
           "-s", sandbox, "-c", "model_reasoning_effort=high", "-m", slug, prompt]
    out, rc, wall = run_capture(cmd, cwd, timeout)
    inp, cached, outp, reason = parse_codex(out)
    total = inp + outp
    non_cached = max(inp - cached, 0)
    # GPT-5.5 list rates; GPT-5.6 Sol publishes the SAME rates (in 5 / cached 0.5 / out 30
    # per 1M — openai pricing page + aipricing.guru, checked 2026-07-10).
    cost = (non_cached*5.0 + cached*0.5 + outp*30.0) / 1e6
    # codex wrote its final message to raw_out via -o; text captured there already
    text = ""
    if os.path.exists(raw_out):
        text = open(raw_out, encoding="utf-8", errors="replace").read()
    return {"text": text, "wall_s": wall, "exit": rc, "_wrote_raw": True,
            "input_tok": inp, "cached_tok": cached, "output_tok": outp, "reasoning_tok": reason,
            "total_tok": total, "cost_est_usd": round(cost, 4), "notes": extra_notes}

def run_codex56(task, mode, cwd, timeout):
    return run_codex(task, mode, cwd, timeout, slug=CODEX56_MODEL, tag="codex56",
                     extra_notes=f"auth=chatgpt-account;slug={CODEX56_MODEL}")

# ---------------------------------------------------------------- grok arm (ACP subprocess)
# WARNING (token accounting): the grok CLI's ACP `_meta` token fields report FINAL CONTEXT
# SIZE (a context-fill gauge that the CLI resets to 0 on /compact), NOT a cumulative sum of
# billed tokens over the turns. Claude Code and Codex report cumulative sums. Do NOT compare
# the numbers this arm records against the claude/codex arms raw — they are different meters.
# See the experiment README "The token-accounting defect".
def run_grok(task, mode, cwd, timeout):
    prompt_file = os.path.join(HERE, task["prompt_file"])
    raw_out = os.path.join(RAW_DIR, f"{task['id']}_grok.txt")
    cmd = [sys.executable, GROK_ACP, "--cwd", cwd, "--prompt-file", prompt_file,
           "--mode", mode, "--effort", "high", "--model", GROK_MODEL,
           "--timeout", str(timeout), "--out", raw_out]
    out, rc, wall = run_capture(cmd, cwd, timeout + 60)   # +60 for ACP startup/teardown
    meta = {}
    # grok_acp prints a JSON blob on stdout (meta + server_methods)
    try:
        blob = out[out.index("{"):out.rindex("}")+1]
        meta = json.loads(blob).get("meta", {})
    except Exception:
        pass
    inp = meta.get("inputTokens") or 0
    cr = meta.get("cachedReadTokens") or 0
    outp = meta.get("outputTokens") or 0
    reason = meta.get("reasoningTokens") or 0
    total = meta.get("totalTokens") or (inp + outp)
    text = open(raw_out, encoding="utf-8", errors="replace").read() if os.path.exists(raw_out) else ""
    note = f"cost=unpriced;slug={GROK_MODEL}"
    if not meta:
        note += ";no_meta(check_stdout)"
    return {"text": text, "wall_s": wall, "exit": rc, "_wrote_raw": True,
            "input_tok": inp, "cached_tok": cr, "output_tok": outp, "reasoning_tok": reason,
            "total_tok": total, "cost_est_usd": "", "notes": note}

ARM = {"claude": run_claude, "codex": run_codex, "grok": run_grok, "codex56": run_codex56}

# ---------------------------------------------------------------- one cell
def run_cell(tid, model, smoke_note=""):
    task = task_by_id(tid)
    mode = task["mode"]
    harness_mode = "write" if mode == "write" else "read"    # reason/review/read -> read posture
    cwd = resolve_target(task, model)
    if not os.path.isabs(cwd):
        cwd = os.path.abspath(cwd)
    if os.path.sep + "_scratch" + os.path.sep in cwd or cwd.endswith("_scratch"):
        os.makedirs(cwd, exist_ok=True)                      # no-repo tasks: empty scratch dir
    if not os.path.isdir(cwd):
        os.makedirs(cwd, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    timeout_s = ARM_TIMEOUT_OVERRIDES.get((model, tid), task["timeout_s"])
    override_note = f"T{tid[1:]}_timeout={timeout_s}s(arm-override)" if timeout_s != task["timeout_s"] else ""
    log(f"  [{tid}/{model}] start (mode={mode}, cwd={os.path.relpath(cwd, REPO)}, timeout={timeout_s}s)")
    res = ARM[model](task, harness_mode, cwd, timeout_s)
    # write raw text if the arm didn't already
    if not res.get("_wrote_raw"):
        with open(os.path.join(RAW_DIR, f"{tid}_{model}.txt"), "w", encoding="utf-8") as f:
            f.write(res.get("text", ""))
    grade = ""
    if tid in ("T1", "T2"):
        key = json.load(open(os.path.join(HERE, "keys", f"{tid}.json"), encoding="utf-8"))
        grade = grade_math(res.get("text", ""), key["answer"])
    notes = "; ".join(x for x in [res.get("notes", ""), override_note, smoke_note] if x)
    row = {"task": tid, "model": model, "engine_label": engine_label(model), "effort": "high",
           "wall_s": round(res["wall_s"], 1), "input_tok": res["input_tok"],
           "cached_tok": res["cached_tok"], "output_tok": res["output_tok"],
           "reasoning_tok": res["reasoning_tok"], "total_tok": res["total_tok"],
           "cost_est_usd": res["cost_est_usd"], "exit": res["exit"], "notes": notes, "grade": grade}
    append_row(row)
    log(f"  [{tid}/{model}] done wall={row['wall_s']}s in={row['input_tok']} cr={row['cached_tok']} "
        f"out={row['output_tok']} rsn={row['reasoning_tok']} tot={row['total_tok']} "
        f"${row['cost_est_usd']} exit={row['exit']} grade={grade}")
    return row

# ---------------------------------------------------------------- planning
def expand_tasks(spec):
    spec = spec.strip()
    if ".." in spec:
        a, b = spec.split("..")
        return [f"T{i}" for i in range(int(a[1:]), int(b[1:]) + 1)]
    return [s.strip() for s in spec.split(",") if s.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="T1..T8")
    ap.add_argument("--models", default="claude,codex,grok")
    ap.add_argument("--only", default="", help="comma list of TASK:MODEL cells to restrict to")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--serial", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tag rows notes=smoke")
    ap.add_argument("--grok-model", default="grok-build",
                    help="grok model slug for the grok arm (default grok-build); "
                         "engine_label is read from ~/.grok/models_cache.json at run time")
    ap.add_argument("--codex-model", default="gpt-5.6-sol",
                    help="model slug for the codex56 arm (default gpt-5.6-sol); the base "
                         "'codex' arm stays pinned to gpt-5.5")
    args = ap.parse_args()
    global GROK_MODEL, CODEX56_MODEL
    GROK_MODEL = args.grok_model
    CODEX56_MODEL = args.codex_model

    tasks = expand_tasks(args.tasks)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    only = set()
    if args.only:
        for c in args.only.split(","):
            t, m = c.split(":")
            only.add((t.strip(), m.strip()))
    done = set() if args.force else done_cells()

    plan = []   # (task, model)
    for t in tasks:
        for m in models:
            if only and (t, m) not in only:
                continue
            if (t, m) in done:
                log(f"  skip {t}/{m} (already in metrics.csv; --force to rerun)")
                continue
            plan.append((t, m))

    log(f"PLAN: {len(plan)} cells -> " + ", ".join(f"{t}/{m}" for t, m in plan))
    if args.dry_run:
        for t, m in plan:
            task = task_by_id(t)
            tgt = task["targets"]["codex" if m == "codex56" else m]
            to = ARM_TIMEOUT_OVERRIDES.get((m, t), task["timeout_s"])
            log(f"  DRY {t}/{m}  mode={task['mode']}  cwd={tgt}  timeout={to}s")
        return

    smoke_note = "smoke" if args.smoke else ""
    if args.serial:
        for t, m in plan:
            run_cell(t, m, smoke_note)
    else:
        # one thread per model arm; tasks sequential within an arm, arms concurrent
        by_model = {m: [t for (t, mm) in plan if mm == m] for m in models}
        threads = []
        for m, tlist in by_model.items():
            if not tlist:
                continue
            def worker(model=m, tl=tlist):
                for t in tl:
                    run_cell(t, model, smoke_note)
            th = threading.Thread(target=worker)
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
    log("DONE. metrics -> " + os.path.relpath(CSV_PATH, REPO))

if __name__ == "__main__":
    main()
