#!/usr/bin/env python3
"""kimi_proxy.py — Anthropic-API shim so `claude -p` drives an OpenRouter model,
HARDENED with retry-on-429/5xx backoff for launch-day throttled providers (Kimi K3).
Based on tools/glm_claude_proxy.py; adds a retry loop on the upstream request so a
throttled tool call eventually lands instead of failing the whole cell. Temp copy —
shared tool left untouched."""
import json, argparse, urllib.request, urllib.error, subprocess, time, random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
LOG = ROOT / "Temp/output/kimi_proxy.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
OR_ROOT = "https://openrouter.ai/api"
TARGET_MODEL = "moonshotai/kimi-k3"
REASONING_EFFORT = None
MAX_RETRIES = 10          # retries on 429/5xx before giving up
BACKOFF_BASE = 2.0        # seconds
BACKOFF_CAP = 25.0


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
        if raw:
            try:
                body = json.loads(raw)
                if "model" in body:
                    body["model"] = TARGET_MODEL
                if REASONING_EFFORT and "messages" in body and "count_tokens" not in self.path:
                    body.pop("thinking", None)
                    body["reasoning"] = {"effort": REASONING_EFFORT}
                raw = json.dumps(body).encode()
            except Exception:
                log(f"{method} {self.path} (non-JSON body, passthrough)")

        # Retry the upstream request on 429/5xx with exponential backoff + jitter.
        up = None
        last_err = None
        for attempt in range(MAX_RETRIES + 1):
            req = urllib.request.Request(OR_ROOT + self.path, data=raw or None, method=method)
            req.add_header("Authorization", f"Bearer {KEY}")
            for h in ("Content-Type", "anthropic-version", "anthropic-beta"):
                if self.headers.get(h):
                    req.add_header(h, self.headers[h])
            try:
                up = urllib.request.urlopen(req, timeout=600)
                break
            except urllib.error.HTTPError as e:
                code = e.code
                last_err = e
                if code in (429, 500, 502, 503, 529) and attempt < MAX_RETRIES:
                    wait = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt)) + random.uniform(0, 1.5)
                    log(f"  upstream {code} (attempt {attempt+1}/{MAX_RETRIES}) -> retry in {wait:.1f}s")
                    time.sleep(wait)
                    continue
                err = e.read()
                log(f"  upstream {code} FINAL: {err[:200].decode(errors='replace')}")
                self.send_response(code)
                self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(err)
                return
            except urllib.error.URLError as e:
                last_err = e
                if attempt < MAX_RETRIES:
                    wait = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt)) + random.uniform(0, 1.5)
                    log(f"  urlerror {e} (attempt {attempt+1}) -> retry in {wait:.1f}s")
                    time.sleep(wait)
                    continue
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": str(e)}}).encode())
                return
        if up is None:
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
    ap.add_argument("--port", type=int, default=8789)
    ap.add_argument("--model", default="moonshotai/kimi-k3")
    ap.add_argument("--reasoning-effort", default=None)
    args = ap.parse_args()
    global TARGET_MODEL, REASONING_EFFORT
    TARGET_MODEL = args.model
    REASONING_EFFORT = args.reasoning_effort
    log(f"=== kimi_proxy start: port={args.port} target={TARGET_MODEL} reasoning={REASONING_EFFORT} "
        f"max_retries={MAX_RETRIES} ===")
    print(f"kimi_proxy on http://localhost:{args.port} -> {TARGET_MODEL} (retry-hardened; log: {LOG})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
