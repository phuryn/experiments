#!/usr/bin/env python3
"""Minimal ACP-stdio driver for the grok-build leg of the three-harness battery.

WHY THIS EXISTS
---------------
Grok's headless mode (`grok -p ... --output-format json|streaming-json`) returns NO
per-turn token split. The richest total it exposes is a running `contextTokensUsed`
(== `_meta.totalTokens` in the session's updates.jsonl) — a single cumulative number,
not the input/output/cached/reasoning breakdown the benchmark needs.

The full split is only available over grok's ACP (Agent Client Protocol) stdio channel:
`grok agent --reasoning-effort <e> -m <model> stdio`. There, the JSON-RPC response to
`session/prompt` carries `_meta` = {totalTokens, inputTokens, outputTokens,
cachedReadTokens, reasoningTokens, modelId}. This driver speaks that protocol as the
*client*: it answers grok's server->client fs/terminal/permission requests, streams the
agent's text, and returns the final `_meta` split + wall-clock.

IMPORTANT — WHAT `_meta` ACTUALLY MEASURES
------------------------------------------
The ACP `_meta` token fields report the session's FINAL CONTEXT SIZE (a context-fill
gauge that the CLI resets to 0 on /compact), NOT a cumulative sum of billed tokens over
the turns. Claude Code and Codex report cumulative sums. Comparing the numbers this driver
records against those arms raw understates grok's real token/dollar usage by a large factor
(~26x on the battery measured here). The published experiment README reconstructs the real
figures from the per-turn context staircase. Treat this field as a context-fill snapshot.

Protocol + field shapes cribbed verbatim from the grok-build VS Code extension:
  grok-build-vscode/src/acp.ts          (spawn args, handshake, handlers)
  grok-build-vscode/src/acp-dispatch.ts (parseAcpLine, extractPromptMeta, routeSessionUpdate)

READ-ONLY ENFORCEMENT (mode="read")
-----------------------------------
Over ACP, grok's file reads and shell commands are delegated back to THIS client as
`fs/read_text_file`, `fs/write_text_file`, and `terminal/*` requests. There is no
server-side grok sandbox to lean on, so the client is the sandbox:
  * fs/read_text_file  -> always served (reads are safe)
  * fs/write_text_file -> BLOCKED in read mode (JSON-RPC error); served in write mode
  * terminal/create    -> in read mode, only READ-ONLY commands run (mutating ones are
                          refused); in write mode, commands run scoped to cwd.
This mirrors the extension's own plan-gate (block-at-handler) approach and gives grok a
read-only posture analogous to Codex's read-only sandbox. (Claude, by contrast, is fully
shell-denied — a deliberate cross-harness asymmetry documented in the README.)
"""
import json, os, subprocess, sys, threading, time, shutil, argparse, re

# ---- read-only command guard (mirrors plan-gate.ts intent) ----------------------------
# GOAL: let grok do read-only navigation/search exactly like Codex's read-only sandbox
# (find / grep / cat / ls / head / pipes / `2>/dev/null` all fine) while making it
# impossible to WRITE, delete, execute code, hit the network, or `git diff` the seeded
# commits (the last is the June parity rule — a shell that can `git diff` would trivially
# reveal T3's committed seeds, so git is denied to grok just as all shells are to Claude).
#
# The guard is deny-by-property, not an allowlist (an allowlist over-blocked a legit
# `find ... -exec grep ... 2>/dev/null || echo` in probe 3). A command is read-only unless
# it: writes/appends to a file, backgrounds, substitutes a subshell, edits in place, or
# names any mutating / code-executing / network / git tool.
_HARD_MUTATING = re.compile(
    r"(?<![\w-])("
    r"rm|rmdir|del|erase|unlink|rd|mv|move|ren|rename|cp|copy|xcopy|robocopy|mkdir|md|"
    r"touch|ni|new-item|ri|remove-item|set-content|add-content|out-file|clear-content|tee|"
    r"chmod|chown|icacls|attrib|dd|truncate|split|shred|"
    r"git|svn|hg|"
    r"npm|npx|pnpm|yarn|bun|pip|pip3|pipx|poetry|cargo|go|make|cmake|gradle|mvn|dotnet|"
    r"node|deno|python|python3|py|ruby|perl|php|sh|bash|zsh|fish|powershell|pwsh|cmd|osascript|"
    r"curl|wget|iwr|invoke-webrequest|invoke-restmethod|irm|nc|netcat|ssh|scp|sftp|rsync|ftp|"
    r"apt|apt-get|brew|choco|winget|reg|fsutil|mklink|ln|systemctl|service|kill|taskkill"
    r")(?![\w-])", re.I)
# stderr redirects that write nothing real — stripped before the file-write check
_SAFE_REDIRECT = re.compile(r"(2>\s*/dev/null|2>\s*nul|2>&1|1>&2|&>\s*/dev/null|>\s*/dev/null)", re.I)
_INPLACE_EDIT = re.compile(r"(?<![\w-])(sed|perl|gsed)(?![\w-])[^|;&]*\s-i\b", re.I)

def _is_read_only(cmd: str) -> bool:
    if not cmd or not cmd.strip():
        return False
    stripped = _SAFE_REDIRECT.sub("", cmd)
    if ">" in stripped or "<(" in stripped:      # any real file-write redirect / process sub
        return False
    if "`" in cmd or "$(" in cmd:                # command substitution can hide a write
        return False
    if _INPLACE_EDIT.search(cmd):                # sed -i / perl -i
        return False
    # lone `&` backgrounding (after removing `&&` and stderr-dup `>&`, `&>`): block
    bg = re.sub(r"&&|\d?>&\d?|&>", "", cmd)
    if "&" in bg:
        return False
    if _HARD_MUTATING.search(cmd):
        return False
    return True


class GrokAcpRunner:
    def __init__(self, cwd, effort="high", model="grok-build", mode="read",
                 log=lambda m: None, always_approve=True):
        self.cwd = os.path.abspath(cwd)
        self.effort = effort
        self.model = model
        self.mode = mode           # "read" | "write"
        self.log = log
        self.always_approve = always_approve
        self.proc = None
        self.next_id = 1
        self.pending = {}          # id -> {"event": Event, "result": ..., "error": ...}
        self.session_id = None
        self.text_chunks = []
        self.meta = {}
        self.server_methods = {}   # method -> count (diagnostics)
        self.terminals = {}        # terminalId -> {"proc","out","done","code"}
        self._term_seq = 0
        self._writelock = threading.Lock()
        self._blocked = []         # list of (kind, target) blocked in read mode

    # ---- process + IO -----------------------------------------------------------------
    def _find_grok(self):
        exe = shutil.which("grok")
        if exe:
            return exe
        for cand in (os.path.expanduser(r"~/.grok/bin/grok.exe"),
                     os.path.expanduser(r"~/.grok/bin/grok")):
            if os.path.exists(cand):
                return cand
        return "grok"

    def start(self):
        grok = self._find_grok()
        # `--reasoning-effort` is an agent-level flag and MUST precede the `stdio`
        # subcommand (acp.ts buildGrokAgentArgs). grok-build ignores effort
        # (supports_reasoning_effort:false) but we send it for parity/intent.
        args = [grok, "agent", "--reasoning-effort", self.effort, "-m", self.model]
        if self.always_approve:
            args.append("--always-approve")
        args.append("stdio")
        self.log(f"spawn: {' '.join(args)} (cwd={self.cwd})")
        self.proc = subprocess.Popen(
            args, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._stderr_reader, daemon=True).start()

    def _stderr_reader(self):
        for line in self.proc.stderr:
            if line.strip():
                self.log(f"[stderr] {line.rstrip()}")

    def _reader(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self.log(f"[non-json] {line[:200]}")
                continue
            self._on_message(msg)

    def _send(self, obj):
        with self._writelock:
            if not self.proc or self.proc.poll() is not None:
                return False
            try:
                self.proc.stdin.write(json.dumps(obj) + "\n")
                self.proc.stdin.flush()
                return True
            except Exception as e:
                self.log(f"[send-fail] {e}")
                return False

    # ---- JSON-RPC request (client -> server), blocking --------------------------------
    def request(self, method, params, timeout=1800):
        rid = self.next_id
        self.next_id += 1
        ev = threading.Event()
        self.pending[rid] = {"event": ev, "result": None, "error": None}
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        if not ev.wait(timeout):
            raise TimeoutError(f"ACP request timed out: {method}")
        entry = self.pending.pop(rid)
        if entry["error"] is not None:
            raise RuntimeError(f"{method} error: {entry['error']}")
        return entry["result"]

    def _respond(self, rid, result=None, error=None):
        if error is not None:
            self._send({"jsonrpc": "2.0", "id": rid, "error": error})
        else:
            self._send({"jsonrpc": "2.0", "id": rid, "result": result or {}})

    # ---- message router ---------------------------------------------------------------
    def _on_message(self, msg):
        # response to one of our requests
        if msg.get("id") is not None and msg.get("method") is None:
            entry = self.pending.get(msg["id"])
            if entry:
                entry["result"] = msg.get("result")
                entry["error"] = msg.get("error")
                entry["event"].set()
            return
        method = msg.get("method")
        if method == "session/update":
            self._on_session_update(msg.get("params", {}).get("update", {}))
            return
        if method and method.endswith("session/update"):  # _x.ai/session/update
            return
        if method:  # server -> client request (has id) or notification
            self.server_methods[method] = self.server_methods.get(method, 0) + 1
            self._on_server_request(msg.get("id"), method, msg.get("params") or {})

    def _on_session_update(self, u):
        su = u.get("sessionUpdate")
        if su == "agent_message_chunk":
            c = u.get("content") or {}
            if c.get("type") == "text":
                self.text_chunks.append(c.get("text", ""))
        # thoughts/tool calls ignored for text capture

    # ---- server -> client requests ----------------------------------------------------
    def _on_server_request(self, rid, method, params):
        try:
            if method == "fs/read_text_file":
                content = self._fs_read(params)
                if rid is not None:
                    self._respond(rid, {"content": content})
                return
            if method == "fs/write_text_file":
                if self.mode == "read":
                    self._blocked.append(("write", params.get("path")))
                    if rid is not None:
                        self._respond(rid, error={"code": -32000, "message": "read-only: writes disabled"})
                    return
                self._fs_write(params)
                if rid is not None:
                    self._respond(rid, {})
                return
            if method == "terminal/create":
                self._term_create(rid, params)
                return
            if method == "terminal/output":
                if rid is not None:
                    self._respond(rid, self._term_output(params.get("terminalId")))
                return
            if method == "terminal/wait_for_exit":
                if rid is not None:
                    self._respond(rid, self._term_wait(params.get("terminalId")))
                return
            if method in ("terminal/kill", "terminal/release"):
                self._term_kill(params.get("terminalId"))
                if rid is not None:
                    self._respond(rid, {})
                return
            if method == "session/request_permission":
                # auto-approve: pick an allow option (mutations are still blocked at fs/terminal handlers)
                opts = params.get("options", [])
                allow = next((o for o in opts if re.search(r"allow", o.get("kind", ""), re.I)), None)
                if rid is not None:
                    if allow:
                        self._respond(rid, {"outcome": {"outcome": "selected", "optionId": allow["optionId"]}})
                    else:
                        self._respond(rid, {"outcome": {"outcome": "cancelled"}})
                return
            if method.endswith("exit_plan_mode"):
                if rid is not None:
                    self._respond(rid, {"outcome": "approved"})
                return
            if method.endswith("ask_user_question"):
                # can't answer interactively in headless -> cancel so the agent proceeds
                if rid is not None:
                    self._respond(rid, {"outcome": "cancelled"})
                return
            # unknown -> ack so the agent doesn't hang
            if rid is not None:
                self._respond(rid, {})
        except Exception as e:
            self.log(f"[srv-handler-err] {method}: {e}")
            if rid is not None:
                self._respond(rid, error={"code": -32603, "message": str(e)})

    # ---- fs handlers ------------------------------------------------------------------
    def _resolve(self, p):
        p = os.path.normpath(p)
        if not os.path.isabs(p):
            p = os.path.join(self.cwd, p)
        return p

    def _fs_read(self, params):
        path = self._resolve(params.get("path", ""))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        line = params.get("line")
        limit = params.get("limit")
        if line is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (line - 1) if line else 0
            end = (start + limit) if limit else len(lines)
            content = "".join(lines[start:end])
        return content

    def _fs_write(self, params):
        path = self._resolve(params.get("path", ""))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(params.get("content", ""))

    # ---- terminal handlers ------------------------------------------------------------
    def _term_create(self, rid, params):
        command = params.get("command", "")
        # ACP may pass args separately; join into one shell string.
        args = params.get("args")
        if args:
            command = command + " " + " ".join(args)
        if self.mode == "read" and not _is_read_only(command):
            self._blocked.append(("terminal", command))
            if rid is not None:
                self._respond(rid, error={"code": -32000, "message": f"read-only: refused mutating command"})
            return
        cwd = params.get("cwd") or self.cwd
        self._term_seq += 1
        tid = f"term-{self._term_seq}"
        try:
            p = subprocess.Popen(command, cwd=cwd, shell=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                 errors="replace")
        except Exception as e:
            if rid is not None:
                self._respond(rid, error={"code": -32000, "message": f"spawn failed: {e}"})
            return
        rec = {"proc": p, "out": [], "code": None}
        self.terminals[tid] = rec

        def _pump():
            try:
                for ln in p.stdout:
                    rec["out"].append(ln)
            except Exception:
                pass
            rec["code"] = p.wait()
        threading.Thread(target=_pump, daemon=True).start()
        if rid is not None:
            self._respond(rid, {"terminalId": tid})

    def _term_output(self, tid):
        rec = self.terminals.get(tid)
        if not rec:
            return {"output": "", "exitStatus": None, "truncated": False}
        out = "".join(rec["out"])
        status = {"exitCode": rec["code"]} if rec["code"] is not None else None
        return {"output": out, "exitStatus": status, "truncated": False}

    def _term_wait(self, tid):
        rec = self.terminals.get(tid)
        if not rec:
            return {"exitCode": -1}
        rec["proc"].wait()
        return {"exitCode": rec["code"] if rec["code"] is not None else rec["proc"].returncode}

    def _term_kill(self, tid):
        rec = self.terminals.get(tid)
        if rec and rec["proc"].poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(rec["proc"].pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    rec["proc"].kill()
            except Exception:
                pass

    # ---- top-level run ----------------------------------------------------------------
    def run(self, prompt, prompt_timeout=1800):
        t0 = time.monotonic()
        self.start()
        self.request("initialize", {
            "protocolVersion": 1,
            "clientCapabilities": {
                "fs": {"readTextFile": True, "writeTextFile": True},
                "terminal": True,
            },
        }, timeout=120)
        sess = self.request("session/new", {"cwd": self.cwd, "mcpServers": []}, timeout=120)
        self.session_id = sess.get("sessionId")
        # grok-build is the default agent-model; -m already set it. Skip set_model.
        result = self.request("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": prompt}],
        }, timeout=prompt_timeout)
        meta = (result or {}).get("_meta", {}) or {}
        self.meta = {
            "totalTokens": meta.get("totalTokens"),
            "inputTokens": meta.get("inputTokens"),
            "outputTokens": meta.get("outputTokens"),
            "cachedReadTokens": meta.get("cachedReadTokens"),
            "reasoningTokens": meta.get("reasoningTokens"),
            "modelId": meta.get("modelId"),
            "stopReason": (result or {}).get("stopReason"),
        }
        wall = time.monotonic() - t0
        text = "".join(self.text_chunks)
        return {
            "text": text, "meta": self.meta, "wall_s": wall,
            "session_id": self.session_id, "server_methods": self.server_methods,
            "blocked": self._blocked, "raw_result": result,
        }

    def close(self):
        try:
            if self.proc and self.proc.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.proc.terminate()
        except Exception:
            pass


def run_grok_acp(cwd, prompt, mode="read", effort="high", model="grok-build",
                 prompt_timeout=1800, log=None):
    """Convenience wrapper used by runner.py. Returns the run dict."""
    logfn = log or (lambda m: None)
    r = GrokAcpRunner(cwd=cwd, effort=effort, model=model, mode=mode, log=logfn)
    try:
        return r.run(prompt, prompt_timeout=prompt_timeout)
    finally:
        r.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--mode", default="read", choices=["read", "write"])
    ap.add_argument("--effort", default="high")
    ap.add_argument("--model", default="grok-build")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    logfn = (lambda m: print(f"[acp] {m}", file=sys.stderr)) if args.verbose else (lambda m: None)
    res = run_grok_acp(args.cwd, prompt, mode=args.mode, effort=args.effort,
                       model=args.model, prompt_timeout=args.timeout, log=logfn)
    out = {
        "wall_s": round(res["wall_s"], 2), "meta": res["meta"],
        "server_methods": res["server_methods"], "blocked": res["blocked"],
        "text_len": len(res["text"]), "session_id": res["session_id"],
    }
    print(json.dumps(out, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(res["text"])


if __name__ == "__main__":
    main()
