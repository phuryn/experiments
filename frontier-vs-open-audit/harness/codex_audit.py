#!/usr/bin/env python3
"""Codex (GPT-5.5) bug-audit of the seeded audit-repo repo — 3rd arm vs Opus 4.8 / GLM-5.2.

Same audit prompt and same repo as audit_runs.py, driven by the OpenAI Codex CLI in its NATIVE
agentic harness (codex exec, read-only sandbox). Codex bills to the ChatGPT sub, but it reports token
usage, so we compute an API-EQUIVALENT cost at GPT-5.5 public list rates ($5/M in, $30/M out, $0.50/M
cached input) — making the cost axis fully 3-way and comparable to Opus/GLM.

`--json` streams events (we sum usage from turn.completed); `-o <file>` writes the final findings text.

Usage:
  python codex_audit.py --n 3 --concurrency 2 --repo Temp/audit_repo \
      --out-dir Temp/data/audit_runs --effort high [--model gpt-5.5]
"""
import subprocess, sys, time, io, os, re, json, argparse, csv, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

PROMPT = (
    "You are doing a pre-release code audit of this repository. Find real defects — focus on "
    "security (authentication, authorization, RBAC, RLS policies, tokens / API keys), "
    "correctness and business logic, and performance. Navigate the code yourself; the risky "
    "surfaces are the auth/access-control layer, the data-access layer, and anything that grows "
    "unbounded.\n\n"
    "Report EVERY issue you find as a numbered list. For each item give: `file:line`, a one-line "
    "description of the bug, its category (security / logic / performance), and severity. Quote the "
    "offending code. Be thorough and specific. Do not fix anything — report only."
)
_lock = threading.Lock()

# GPT-5.5 public list rates ($/1M). output_tokens already INCLUDES reasoning tokens (OpenAI convention),
# so reasoning is logged for transparency but NOT added again to the output cost.
P_IN, P_CACHED, P_OUT = 5.0, 0.5, 30.0


def find_codex():
    env = os.environ.get("CODEX_BIN")
    if env and os.path.exists(env):
        return env
    import glob
    hits = sorted(glob.glob(os.path.expanduser(
        "~/.vscode/extensions/openai.chatgpt-*/bin/*/codex.exe")), reverse=True)
    if hits:
        return hits[0]
    raise SystemExit("codex binary not found")


def run_one(tag, codex_bin, model, repo, out_dir, effort):
    msg_file = os.path.join(out_dir, f"CODEX_{tag}.txt")   # -o writes the final findings message here
    cmd = [codex_bin, "exec", "--json", "-o", msg_file, "--skip-git-repo-check", "-s", "read-only"]
    if effort:
        cmd += ["-c", f"model_reasoning_effort={effort}"]
    if model:
        cmd += ["-m", model]
    cmd.append(PROMPT)
    t0 = time.monotonic()
    in_tok = cached = out_tok = reason = 0
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", input="", cwd=repo)
        rc = proc.returncode
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "turn.completed":
                u = ev.get("usage", {}) or {}
                in_tok += u.get("input_tokens", 0) or 0
                cached += u.get("cached_input_tokens", 0) or 0
                out_tok += u.get("output_tokens", 0) or 0
                reason += u.get("reasoning_output_tokens", 0) or 0
    except Exception as exc:
        rc = -99
        with open(msg_file, "w", encoding="utf-8") as f:
            f.write(f"[runner error: {exc}]")
    secs = time.monotonic() - t0
    out = ""
    if os.path.exists(msg_file):
        with open(msg_file, encoding="utf-8", errors="replace") as f:
            out = f.read()
        if rc != 0 and not out.strip():
            out = f"[codex exit {rc}]"
            with open(msg_file, "w", encoding="utf-8") as f:
                f.write(out)
    # API-equivalent cost: cached input billed at the discounted rate; output already incl reasoning.
    cost = ((in_tok - cached) * P_IN + cached * P_CACHED + out_tok * P_OUT) / 1e6
    n_items = len(re.findall(r"(?m)^\s*\**\s*\d+[.)]", out))
    row = {"label": "CODEX", "tag": tag, "secs": round(secs), "in_tok": in_tok, "cached": cached,
           "out_tok": out_tok, "reason_tok": reason, "cost_usd": round(cost, 4),
           "chars": len(out), "n_items": n_items, "rc": rc}
    with _lock:
        print(f"CODEX {tag:>5}  {row['secs']:>4}s  in={in_tok:>7} cache={cached:>6} out={out_tok:>6} "
              f"${cost:6.3f}  items~{n_items:>3}  rc={rc}", flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out-dir", default="Temp/data/audit_runs")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="high",
                    help="codex model_reasoning_effort (high = ceiling). minimal/low/medium/high.")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    # MUST be absolute: codex runs with cwd=repo (read-only sandbox), so a relative `-o`
    # path resolves against the repo dir and the write silently fails (no report captured).
    args.out_dir = os.path.abspath(args.out_dir)
    os.makedirs(args.out_dir, exist_ok=True)
    codex_bin = find_codex()
    tags = [f"r{i:02d}" for i in range(args.start, args.start + args.n)]
    print(f"CODEX: n={args.n} conc={args.concurrency} model={args.model or '(default gpt-5.5)'} "
          f"effort={args.effort} prices=${P_IN}/${P_OUT}(cache ${P_CACHED}) repo={repo}\n", flush=True)
    t0 = time.monotonic()
    rows = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(run_one, t, codex_bin, args.model, repo, args.out_dir, args.effort): t for t in tags}
        for fut in as_completed(futs):
            rows.append(fut.result())
    rows.sort(key=lambda r: r["tag"])
    summ = args.summary or os.path.join(args.out_dir, "summary_CODEX.csv")
    with open(summ, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    ok = [r for r in rows if r["rc"] == 0]
    mean_cost = sum(r["cost_usd"] for r in ok) / max(1, len(ok))
    mean_items = sum(r["n_items"] for r in ok) / max(1, len(ok))
    print(f"\nCODEX: {len(ok)}/{len(rows)} clean · mean ${mean_cost:.3f}/run · "
          f"mean ~{mean_items:.0f} items/run · {(time.monotonic()-t0)/60:.1f} min · -> {summ}", flush=True)


if __name__ == "__main__":
    main()
