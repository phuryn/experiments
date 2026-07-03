#!/usr/bin/env python3
"""One-shot needle-skill probe: Opus 4.8, --effort xhigh, security-audit-static
method preamble + verbatim needle audit task. n=1 by design (anecdote arm).
Appends task='needle-skill' row to runs.csv with the needle grader."""
import csv, json, os, re, shutil, subprocess, time
from datetime import datetime

REPO = r"<WORKDIR>"
OUT = os.path.join(REPO, "Temp", "output", "fable5-return-0703")
DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"
PROMPT = open(os.path.join(OUT, "needle_skill_prompt.txt"), encoding="utf-8").read()

LOOSE = re.compile(r"50K|75K|one-liner ceiling|<50")
STRICT_A = re.compile(r"50K")
STRICT_B = re.compile(r"75K|one-liner ceiling")

CLAUDE = shutil.which("claude")
cmd = [CLAUDE, "-p", "--model", "claude-opus-4-8", "--effort", "xhigh",
       "--output-format", "json", "--disallowedTools", DENY]  # prompt via stdin: it starts with '---' which argv parses as a flag
if CLAUDE.lower().endswith((".cmd", ".bat")):
    cmd = ["cmd", "/c"] + cmd
env = {k: v for k, v in os.environ.items() if k != "CLAUDE_EFFORT"}

t0 = time.monotonic()
try:
    p = subprocess.run(cmd, cwd=REPO, input=PROMPT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, env=env)
    rc, raw = p.returncode, p.stdout or ""
except subprocess.TimeoutExpired:
    rc, raw = -9, ""
secs = round(time.monotonic() - t0, 3)

out_tok = in_tok = ""
text = raw
meta = None
try:
    meta = json.loads(raw)
    u = meta.get("usage", {})
    out_tok, in_tok = u.get("output_tokens", ""), u.get("input_tokens", "")
    text = meta.get("result", "") or ""
except json.JSONDecodeError:
    pass

strict = 1 if (rc == 0 and STRICT_A.search(text) and STRICT_B.search(text)) else 0
loose = 1 if (rc == 0 and LOOSE.search(text)) else 0
with open(os.path.join(OUT, "answers", "needle-skill-opus-xhigh-r01.json"), "w", encoding="utf-8") as f:
    json.dump({"run_id": "needle-skill-opus-xhigh-r01", "rc": rc, "wall_seconds": secs,
               "cli_json": meta if meta is not None else raw[-4000:]}, f, indent=1)
with open(os.path.join(OUT, "runs.csv"), "a", newline="", encoding="utf-8") as f:
    csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), "needle-skill",
                            "opus", "xhigh", 1, secs, out_tok, "", in_tok, len(text),
                            strict, rc, loose])
print(f"needle-skill probe: rc={rc} {secs}s out_tok={out_tok} strict={strict} loose={loose}")
