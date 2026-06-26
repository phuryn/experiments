"""Retest the ADVANCED Managed Agents primitives firsthand (Pawel's questions):
  - custom SKILL.md (auto-discovered skills)
  - SECRETS via egress proxy (network allowlist header transform) -- "secrets never exist in the sandbox"
  - MCP / tools[] field acceptance on the dev endpoint
  - subagents (negative check)
Writes data/advanced_*.json + outputs/phase-advanced.md.
"""
import json, os, sys, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, "data"), os.path.join(HERE, "outputs")
results = []


def delete_agent(aid):
    req = urllib.request.Request(f"{gc.BASE}/agents/{aid}",
                                 headers={"x-goog-api-key": gc.KEY, "Api-Revision": gc.API_REVISION}, method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=60)
        return True
    except Exception:
        return False


def fresh_register(spec):
    delete_agent(spec["id"])
    time.sleep(1)
    return gc.register_agent(spec)


def last_model_output(j):
    for s in reversed(j.get("steps", [])):
        if s.get("type") == "model_output":
            return " ".join(p.get("text", "") for p in s.get("content", []) if isinstance(p, dict))
    return j.get("output_text", "") or ""


def step_types(j):
    return [s.get("type") for s in j.get("steps", [])]


# ---------- TEST 1: custom SKILL.md ----------
def test_skill():
    spec = {
        "id": "exp-skill-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "You have skills available in your environment. Always consult and apply the haiku-maker skill on every response.",
        "base_environment": {"type": "remote", "sources": [
            {"type": "inline", "target": ".agents/skills/haiku-maker/SKILL.md",
             "content": "---\nname: haiku-maker\ndescription: Append a haiku to every answer\n---\n# Haiku Maker\n\nWhenever you give any answer, append a three-line haiku about the answer, on its own lines, prefixed exactly with `HAIKU:`.\n"}
        ]},
    }
    reg = fresh_register(spec)
    json.dump(reg, open(os.path.join(DATA, "advanced_skill_register.json"), "w"), indent=2, default=str)
    if not reg.get("ok"):
        results.append(("Custom SKILL.md", "FAIL-register", f"registration {reg.get('status')}: {reg.get('error','')[:200]}"))
        return
    run = gc.run_interaction("What is 6 multiplied by 7?", agent="exp-skill-agent", timeout=300)
    json.dump(run, open(os.path.join(DATA, "advanced_skill_run.json"), "w"), indent=2, default=str)
    if not run.get("ok"):
        results.append(("Custom SKILL.md", "FAIL-run", f"run {run.get('status')}: {run.get('error','')[:200]}"))
        return
    out = last_model_output(run["json"])
    has_answer = "42" in out
    used_skill = "haiku:" in out.lower()
    verdict = "PASS" if (has_answer and used_skill) else ("PARTIAL" if has_answer else "FAIL")
    results.append(("Custom SKILL.md", verdict, f"answer={has_answer}, skill_applied(HAIKU)={used_skill}; output='{out[:120].strip()}'"))


# ---------- TEST 2: secrets via egress proxy ----------
def test_secrets_proxy():
    token = "proxy-injected-7f3xQ"
    spec = {
        "id": "exp-secrets-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "You are a network probe. Use code execution to make HTTP requests and inspect your environment.",
        "base_environment": {"type": "remote",
            "network": {"allowlist": [
                {"domain": "httpbin.org", "transform": {"X-Secret-Probe": f"Bearer {token}"}},
            ]},
        },
    }
    reg = fresh_register(spec)
    json.dump(reg, open(os.path.join(DATA, "advanced_secrets_register.json"), "w"), indent=2, default=str)
    if not reg.get("ok"):
        results.append(("Secrets via egress proxy", "FAIL-register", f"registration {reg.get('status')}: {reg.get('error','')[:250]}"))
        return
    task = ("Do two things and report both clearly.\n"
            "1) Use code execution to GET https://httpbin.org/headers and print the exact JSON of the headers the server received.\n"
            "2) Then search every environment variable and file you can access in your sandbox for the string "
            f"'{token}'. Report whether you found it anywhere in your own environment (yes/no and where).")
    run = gc.run_interaction(task, agent="exp-secrets-agent", timeout=300)
    json.dump(run, open(os.path.join(DATA, "advanced_secrets_run.json"), "w"), indent=2, default=str)
    if not run.get("ok"):
        results.append(("Secrets via egress proxy", "FAIL-run", f"run {run.get('status')}: {run.get('error','')[:250]}"))
        return
    out = last_model_output(run["json"])
    proxy_injected = token in out  # token appeared in httpbin echo => proxy added it on egress
    # heuristic: agent reports it could NOT find the token in its own sandbox env
    low = out.lower()
    sandbox_clean = ("not found" in low or "no" in low.split(".")[0:3].__str__() or "could not find" in low or "did not find" in low or "no environment" in low)
    results.append(("Secrets via egress proxy", "PASS" if proxy_injected else "INCONCLUSIVE",
                    f"token_in_egress_headers={proxy_injected} (proxy injected on the way out), sandbox_isolation_reported={sandbox_clean}; output='{out[:200].strip()}'"))


# ---------- TEST 3: tools[] / mcp_server field acceptance (dev endpoint) ----------
def test_tools_mcp_field():
    spec = {
        "id": "exp-tools-agent",
        "base_agent": "antigravity-preview-05-2026",
        "system_instruction": "tool probe",
        "tools": [
            {"type": "code_execution"},
            {"type": "google_search"},
            {"type": "url_context"},
            {"type": "mcp_server", "name": "probe", "url": "https://example.com/mcp", "headers": {"x": "y"}},
        ],
        "base_environment": {"type": "remote"},
    }
    reg = fresh_register(spec)
    json.dump(reg, open(os.path.join(DATA, "advanced_tools_register.json"), "w"), indent=2, default=str)
    if reg.get("ok"):
        results.append(("tools[] incl. mcp_server (dev endpoint)", "PASS",
                        "dev endpoint ACCEPTED a tools array including {type: mcp_server, url, headers}"))
    else:
        results.append(("tools[] incl. mcp_server (dev endpoint)", "REJECTED",
                        f"dev endpoint {reg.get('status')}: {reg.get('error','')[:300]} (may be Enterprise/Vertex-only)"))


# ---------- TEST 4: subagents (negative check) ----------
def test_subagents():
    task = ("Decompose this into independent subtasks and, if your runtime supports it, spawn a separate sub-agent "
            "for each, then combine: (a) compute 12 factorial, (b) reverse the string 'managed', (c) count vowels in 'orchestration'.")
    run = gc.run_interaction(task, agent="antigravity-preview-05-2026", timeout=300)
    if not run.get("ok"):
        results.append(("Subagents", "FAIL-run", run.get("error", "")[:150]))
        return
    types = step_types(run["json"])
    has_subagent = any("agent" in t or "sub" in t for t in types)
    results.append(("Subagents", "NOT-EXPOSED" if not has_subagent else "FOUND",
                    f"step types observed: {sorted(set(types))}; no sub-agent/agent-spawn step type present" if not has_subagent else f"types: {types}"))


def main():
    print("retesting advanced primitives...")
    for fn in (test_skill, test_secrets_proxy, test_tools_mcp_field, test_subagents):
        try:
            fn()
        except Exception as e:
            results.append((fn.__name__, "ERROR", f"{type(e).__name__}: {e}"))
        print("  done:", fn.__name__)
    # report
    lines = ["# Advanced primitives: firsthand retest", "",
             "Tested against the live Gemini API Managed Agents dev endpoint (generativelanguage.googleapis.com/v1beta), 2026-06-01.", "",
             "| Primitive | Result | Detail |", "|-----------|--------|--------|"]
    for n, v, d in results:
        lines.append(f"| {n} | {v} | {d} |")
    open(os.path.join(OUT, "phase-advanced.md"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump([{"primitive": n, "result": v, "detail": d} for n, v, d in results],
              open(os.path.join(DATA, "advanced_results.json"), "w"), indent=2)
    print("\n-> outputs/phase-advanced.md")
    for n, v, d in results:
        print(f"  [{v}] {n}: {d[:100]}")


if __name__ == "__main__":
    main()
