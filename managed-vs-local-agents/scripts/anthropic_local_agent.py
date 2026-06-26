"""Anthropic LOCAL code-defined agent (no UI).

Demonstrates Pawel's claim path for Anthropic:
- agent defined in source code (this file + CLAUDE.md + a SKILL.md)
- skill loaded from .claude/skills/<name>/SKILL.md VIA CODE (not a UI upload)
- runs locally, accesses local .py/.md files through tools
- mirrors the Google Managed Agents test (same bugged solution.py vs spec.md)

Uses the Anthropic Messages API + a real tool-use loop. No nested CLI, no skipped permissions.
Writes data/anthropic_local_agent.json + outputs contribution.
"""
import json, os, subprocess, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc  # reuse _load_key

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(HERE, "anthropic-local")   # the local project the agent works in
DATA = os.path.join(HERE, "data")
MODEL = "claude-sonnet-4-6"
KEY = gc._load_key("ANTHROPIC_API_KEY")

TOOLS = [
    {"name": "read_file", "description": "Read a text file from the project folder.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "list_files", "description": "List files in the project folder.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_python", "description": "Run a python file in the project folder and return stdout/stderr.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]


def _safe(path):
    full = os.path.normpath(os.path.join(PROJ, path))
    if not full.startswith(os.path.normpath(PROJ)):
        raise ValueError("path escapes project")
    return full


def exec_tool(name, inp):
    try:
        if name == "read_file":
            return open(_safe(inp["path"]), encoding="utf-8").read()
        if name == "list_files":
            out = []
            for root, _, files in os.walk(PROJ):
                for f in files:
                    out.append(os.path.relpath(os.path.join(root, f), PROJ))
            return "\n".join(out)
        if name == "run_python":
            r = subprocess.run([sys.executable, _safe(inp["path"])], capture_output=True, text=True, timeout=30, cwd=PROJ)
            return f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        return f"unknown tool {name}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def call(messages, system):
    body = {"model": MODEL, "max_tokens": 1024, "system": system, "tools": TOOLS, "messages": messages}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, method="POST")
    r = urllib.request.urlopen(req, timeout=120)
    return json.load(r)


def main():
    # Load the agent definition FROM CODE: CLAUDE.md + the skill file (no UI upload).
    claude_md = open(os.path.join(PROJ, "CLAUDE.md"), encoding="utf-8").read()
    skill_md = open(os.path.join(PROJ, ".claude", "skills", "bug-finder", "SKILL.md"), encoding="utf-8").read()
    system = (claude_md + "\n\n# Loaded skill: bug-finder\n" + skill_md +
              "\n\nYou have tools: list_files, read_file, run_python. Use them on the local project files.")

    messages = [{"role": "user", "content": "Review solution.py against spec.md. Use the bug-finder skill and report in its exact format."}]
    trace = []
    final_text = ""
    for _ in range(8):
        resp = call(messages, system)
        trace.append({"stop_reason": resp.get("stop_reason"), "blocks": [b.get("type") for b in resp.get("content", [])]})
        messages.append({"role": "assistant", "content": resp["content"]})
        if resp.get("stop_reason") == "tool_use":
            tool_results = []
            for b in resp["content"]:
                if b.get("type") == "tool_use":
                    result = exec_tool(b["name"], b.get("input", {}))
                    tool_results.append({"type": "tool_result", "tool_use_id": b["id"], "content": result[:4000]})
            messages.append({"role": "user", "content": tool_results})
        else:
            final_text = " ".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text")
            break

    low = final_text.lower()
    found_bug = ("mul" in low and ("bug:" in low or "fix:" in low))
    used_skill_format = ("bug:" in low and "fix:" in low)
    verdict = "PASS" if (found_bug and used_skill_format) else ("PARTIAL" if found_bug else "FAIL")
    out = {"model": MODEL, "verdict": verdict, "found_bug": found_bug, "used_skill_format": used_skill_format,
           "tools_used": [t for tr in trace for t in tr["blocks"] if t == "tool_use"].__len__(),
           "trace": trace, "final_text": final_text}
    json.dump(out, open(os.path.join(DATA, "anthropic_local_agent.json"), "w"), indent=2)
    print(f"[{verdict}] anthropic local code-defined agent")
    print("tool-use rounds:", sum(1 for tr in trace if tr["stop_reason"] == "tool_use"))
    print("skill format (BUG:/FIX:) applied:", used_skill_format)
    print("---- final ----")
    print(final_text[:500])


if __name__ == "__main__":
    main()
