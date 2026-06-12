#!/usr/bin/env python3
"""Set 08: depth-10 no-resistance probe, both nesting modes, n=10 each, haiku,
trivial payloads. Pass/fail only — no timing claims.
  cli: depth/level.sh chain to MAX=10 (each level a claude -p that spawns the next)
  rec: gen_spec10 chain — each level WRITES the next level's orchestrator, to L10
Usage: python run_set08.py [smoke|cli|rec|all]
"""
import os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"  # plain "bash" resolves to WSL, which can't read C:/ paths
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "output", "fable5-n10"))
CSV = os.path.join(OUT, "set08.csv")
LEVEL_SH = os.path.join(HERE, "depth", "level.sh").replace("\\", "/")
SPEC_T = os.path.join(HERE, "recwf", "gen_spec10_template.md")

def log_row(variant, run, secs, ok, detail):
    new = not os.path.exists(CSV)
    with open(CSV, "a", encoding="utf-8") as f:
        if new: f.write("variant,run,seconds,pass,detail\n")
        f.write(f"{variant},{run},{secs},{'PASS' if ok else 'FAIL'},{detail}\n")
    print(f"{variant} r{run:02d}: {'PASS' if ok else 'FAIL'} {secs}s {detail}", flush=True)

def run_cli(r):
    d = os.path.join(OUT, "depth10", f"c{r:02d}")
    os.makedirs(d, exist_ok=True)
    du = d.replace("\\", "/")
    t0 = time.time()
    with open(os.path.join(d, "root_output.txt"), "w", encoding="utf-8") as fo:
        subprocess.run([GIT_BASH, LEVEL_SH, "1", "10", du], stdout=fo,
                       stderr=subprocess.STDOUT, timeout=1800)
    secs = round(time.time() - t0)
    floor = os.path.join(d, "level_10.txt")
    floor_ok = os.path.exists(floor) and "floor reached" in open(floor, encoding="utf-8", errors="replace").read()
    tl = os.path.join(d, "timeline.log")
    done = len(re.findall(r"done", open(tl, encoding="utf-8", errors="replace").read())) if os.path.exists(tl) else 0
    log_row("cli", r, secs, floor_ok and done >= 9, f"floor={floor_ok} done_levels={done}")

def run_rec(r):
    d = os.path.join(OUT, "recwf10", f"r{r:02d}")
    os.makedirs(d, exist_ok=True)
    du = d.replace("\\", "/")
    spec = open(SPEC_T, encoding="utf-8").read().replace("@DIR@", du)
    open(os.path.join(d, "gen_spec.md"), "w", encoding="utf-8").write(spec)
    t0 = time.time()
    with open(os.path.join(d, "seed_output.txt"), "w", encoding="utf-8") as fo:
        subprocess.run(["claude", "-p", f"Read {du}/gen_spec.md and execute the procedure with LEVEL=1",
                        "--model", "haiku", "--allowedTools", "Bash,Write,Read",
                        "--permission-mode", "acceptEdits"],
                       stdout=fo, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                       timeout=2400, shell=(os.name == "nt"))
    # the seed session may detach the chain and return early — poll the log for the leaf
    gl = os.path.join(d, "gen-depth.log")
    deadline = time.time() + 900
    while time.time() < deadline:
        txt = open(gl, encoding="utf-8", errors="replace").read() if os.path.exists(gl) else ""
        if "leaf, spec floor reached" in txt:
            break
        time.sleep(10)
    secs = round(time.time() - t0)
    alive = len(re.findall(r"alive at", txt))
    leaf = "leaf, spec floor reached" in txt
    genned = len([f for f in os.listdir(d) if re.match(r"gen_L\d+\.sh$", f)])
    log_row("rec", r, secs, leaf and alive >= 10, f"alive={alive} leaf={leaf} genned={genned}")

def pool(fn, runs):
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(fn, runs))

mode = sys.argv[1] if len(sys.argv) > 1 else "all"
if mode == "smoke":
    run_cli(0); run_rec(0)
elif mode == "cli":
    pool(run_cli, range(1, 11))
elif mode == "rec":
    pool(run_rec, range(1, 11))
elif mode == "all":
    run_cli(0); run_rec(0)
    print("smoke done, starting full runs", flush=True)
    pool(run_cli, range(1, 11))
    pool(run_rec, range(1, 11))
print("SET08 DONE", flush=True)
