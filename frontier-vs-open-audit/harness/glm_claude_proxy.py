#!/usr/bin/env python3
"""
glm_claude_proxy.py — minimal Anthropic-API shim so `claude -p` can drive GLM-5.2
(or any OpenRouter model) through the real Claude Code harness.

Why it's needed: OpenRouter serves an Anthropic-compatible /v1/messages, but only
under its own slug (z-ai/glm-5.2). Claude Code rejects that slug locally and only
emits claude-* names. This shim bridges that ONE mismatch:

  claude -p  --(model=claude-opus-4-8)-->  this proxy  --(model:=z-ai/glm-5.2)-->  OpenRouter

It does exactly one thing: rewrite the `model` field, then forward the request to
OpenRouter verbatim and stream the response back. No fabricated /v1/models lists,
no stubbed token counts — real requests, real responses.

Usage:
  python tools/glm_claude_proxy.py --port 8787 --model z-ai/glm-5.2
  ANTHROPIC_BASE_URL=http://localhost:8787 ANTHROPIC_AUTH_TOKEN=dummy claude -p "..."
"""
import json, argparse, urllib.request, urllib.error, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
LOG = ROOT / "Temp/output/glm_proxy.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
OR_ROOT = "https://openrouter.ai/api"   # CC's path (/v1/messages...) is appended verbatim
TARGET_MODEL = "z-ai/glm-5.2"
REASONING_EFFORT = None   # if set (low/medium/high), injected as reasoning={effort:...} on completions


def key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no OPENROUTER_API_KEY")


KEY = key()


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


class Handler(BaseHTTPRequestHandler):
    def _forward(self, method):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""
        # rewrite the model field on JSON bodies; otherwise pass bytes through
        if raw:
            try:
                body = json.loads(raw)
                if "model" in body:
                    log(f"{method} {self.path} model={body['model']} -> {TARGET_MODEL} "
                        f"stream={body.get('stream')}")
                    body["model"] = TARGET_MODEL
                # Pin GLM to a fixed reasoning tier on real completion requests (those carry
                # `messages`). Drop any Anthropic `thinking` block to avoid a conflicting signal —
                # OpenRouter's `reasoning.effort` is the single source of truth for the tier.
                if REASONING_EFFORT and "messages" in body and "count_tokens" not in self.path:
                    body.pop("thinking", None)
                    body["reasoning"] = {"effort": REASONING_EFFORT}
                    log(f"  injected reasoning.effort={REASONING_EFFORT}")
                raw = json.dumps(body).encode()
            except Exception:
                log(f"{method} {self.path} (non-JSON body, passthrough)")
        else:
            log(f"{method} {self.path}")

        req = urllib.request.Request(OR_ROOT + self.path, data=raw or None, method=method)
        req.add_header("Authorization", f"Bearer {KEY}")
        for h in ("Content-Type", "anthropic-version", "anthropic-beta"):
            if self.headers.get(h):
                req.add_header(h, self.headers[h])
        try:
            up = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            err = e.read()
            log(f"  upstream {e.code}: {err[:300].decode(errors='replace')}")
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.end_headers()
            self.wfile.write(err)
            return
        self.send_response(200)
        self.send_header("Content-Type", up.headers.get("Content-Type", "application/json"))
        self.end_headers()
        try:
            while True:
                chunk = up.read(1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as e:
            log(f"  stream error: {e}")

    def do_POST(self):
        self._forward("POST")

    def do_GET(self):
        self._forward("GET")

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--model", default="z-ai/glm-5.2")
    ap.add_argument("--reasoning-effort", default=None,
                    help="inject OpenRouter reasoning={effort:...} on completion requests "
                         "(low/medium/high) so the target runs at a fixed reasoning tier")
    args = ap.parse_args()
    global TARGET_MODEL, REASONING_EFFORT
    TARGET_MODEL = args.model
    REASONING_EFFORT = args.reasoning_effort
    log(f"=== proxy start: port={args.port} target={TARGET_MODEL} reasoning={REASONING_EFFORT} ===")
    print(f"proxy on http://localhost:{args.port} -> {TARGET_MODEL} (log: {LOG})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
