"""Explore: code-defined Google Managed Agents accessing local source files (.py/.md),
and retest the egress-proxy secrets mechanism with a bounded task.
Writes outputs/phase-explore-google.md + data/explore_*.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc
from probe_advanced import fresh_register, last_model_output, step_types

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "outputs")
results = []

SPEC_MD = """# Calculator spec

Implement two functions in solution.py:
- add(a, b) -> returns a + b
- mul(a, b) -> returns a * b

Both must be correct for all integers.
"""

# solution.py has a DELIBERATE BUG: mul actually adds.
SOLUTION_PY = """def add(a, b):
    return a + b

def mul(a, b):
    # BUG: should multiply
    return a + b

if __name__ == "__main__":
    print("add(2,3)=", add(2, 3))
    print("mul(2,3)=", mul(2, 3))
"""


def test_local_files():
    """Code-define an agent with .py + .md mounted as source; agent reads, runs, reviews them."""
    spec = {
        "id": "exp-codefiles-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "You are a code reviewer. You work with the files mounted in your environment.",
        "base_environment": {"type": "remote", "sources": [
            {"type": "inline", "target": "/workspace/spec.md", "content": SPEC_MD},
            {"type": "inline", "target": "/workspace/solution.py", "content": SOLUTION_PY},
        ]},
    }
    reg = fresh_register(spec)
    json.dump(reg, open(os.path.join(DATA, "explore_codefiles_register.json"), "w"), indent=2, default=str)
    if not reg.get("ok"):
        results.append(("Google: agent reads/runs local .py + .md", "FAIL-register",
                        f"{reg.get('status')}: {reg.get('error','')[:250]}"))
        return
    task = ("Two files were placed in your environment: spec.md and solution.py (look in /workspace and the current directory). "
            "Read both. Then actually run solution.py to test it against spec.md. "
            "Report: (1) the contents you found, (2) whether the code meets the spec, (3) any bug and the exact one-line fix.")
    run = gc.run_interaction(task, agent="exp-codefiles-agent", timeout=300)
    json.dump(run, open(os.path.join(DATA, "explore_codefiles_run.json"), "w"), indent=2, default=str)
    if not run.get("ok"):
        results.append(("Google: agent reads/runs local .py + .md", "FAIL-run", f"{run.get('status')}: {run.get('error','')[:250]}"))
        return
    out = last_model_output(run["json"])
    types = step_types(run["json"])
    read_files = ("add" in out and "mul" in out)
    found_bug = ("mul" in out.lower() and ("bug" in out.lower() or "should" in out.lower() or "a * b" in out or "a*b" in out.replace(" ", "")))
    ran_code = any(t == "code_execution_call" for t in types)
    verdict = "PASS" if (read_files and found_bug) else ("PARTIAL" if read_files else "FAIL")
    results.append(("Google: agent reads/runs local .py + .md", verdict,
                    f"read_files={read_files}, found_mul_bug={found_bug}, ran_code={ran_code}; steps={sorted(set(types))}; out='{out[:160].strip()}'"))


def test_secrets_retest():
    """Egress proxy injects a header the sandbox never sees. Bounded task."""
    token = "egress7f3xQ"
    spec = {
        "id": "exp-secrets2-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "You are a network probe. Be fast: at most one HTTP request, then stop.",
        "base_environment": {"type": "remote", "network": {"allowlist": [
            {"domain": "httpbin.org", "transform": {"X-Secret-Probe": f"Bearer {token}"}}]}},
    }
    reg = fresh_register(spec)
    json.dump(reg, open(os.path.join(DATA, "explore_secrets_register.json"), "w"), indent=2, default=str)
    reg_ok = reg.get("ok")
    if not reg_ok:
        results.append(("Google: egress-proxy secret injection", "FAIL-register",
                        f"{reg.get('status')}: {reg.get('error','')[:250]}"))
        return
    task = ("Make EXACTLY ONE request with code execution: GET https://httpbin.org/headers . "
            "Print the JSON response verbatim. Do not retry. Then stop.")
    run = gc.run_interaction(task, agent="exp-secrets2-agent", timeout=240)
    json.dump(run, open(os.path.join(DATA, "explore_secrets_run.json"), "w"), indent=2, default=str)
    if not run.get("ok"):
        results.append(("Google: egress-proxy secret injection", "INCONCLUSIVE",
                        f"registration ACCEPTED network.allowlist+transform; run did not return ({run.get('status')}: {run.get('error','')[:120]}). Mechanism documented (secrets injected at egress proxy, never in sandbox)."))
        return
    out = last_model_output(run["json"])
    injected = token in out
    results.append(("Google: egress-proxy secret injection",
                    "PASS" if injected else "INCONCLUSIVE",
                    f"network.allowlist+transform accepted at registration; egress header X-Secret-Probe present in httpbin echo={injected}; out='{out[:200].strip()}'"))


def main():
    for fn in (test_local_files, test_secrets_retest):
        try:
            fn()
        except Exception as e:
            results.append((fn.__name__, "ERROR", f"{type(e).__name__}: {e}"))
        print("done:", fn.__name__)
    lines = ["# Explore: Google code-defined agents + local files + secrets", "",
             "Live, dev endpoint, 2026-06-01.", "", "| Path | Result | Detail |", "|------|--------|--------|"]
    for n, v, d in results:
        lines.append(f"| {n} | {v} | {d} |")
    open(os.path.join(OUT, "phase-explore-google.md"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump([{"path": n, "result": v, "detail": d} for n, v, d in results],
              open(os.path.join(DATA, "explore_google_results.json"), "w"), indent=2)
    for n, v, d in results:
        print(f"  [{v}] {n}: {d[:110]}")


if __name__ == "__main__":
    main()
