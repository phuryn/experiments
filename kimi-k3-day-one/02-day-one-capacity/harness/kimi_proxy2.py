#!/usr/bin/env python3
"""kimi_proxy2.py — kimi_proxy.py + the EMPTY-200 FIX.

THE BUG THIS FIXES (diagnosed 2026-07-17):
  kimi_proxy.py does `self.send_response(200)` and THEN streams upstream chunks
  verbatim. It only retries 429/5xx. So when OpenRouter returns a 200 with an
  empty/degenerate body, the shim has already committed a 200 to `claude`, forwards
  nothing, and the CLI aborts the whole run with:
     "API Error: API returned an empty or malformed response (HTTP 200)"
     terminal_reason=api_error
  T7 (the longest tool chain in the battery) hit this on every attempt: 8 turns, then
  28 turns, then dead -- while K3 itself was auditing correctly.

THE FIX:
  PEEK the first chunk from upstream BEFORE committing the 200 header. An empty first
  read is now treated as a retryable condition (same backoff as 429) instead of being
  forwarded as a corpse. Once a non-empty first chunk is in hand, commit the 200 and
  stream normally -- so real streaming semantics are preserved untouched.

  This is infrastructure resilience only. It cannot change what the model computes; it
  is the same category of fix as the 429 retry that is already here. It does not touch
  the prompt, the tools, the task, or the model.
"""
import json, argparse, urllib.request, urllib.error, subprocess, time, random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
LOG = ROOT / "Temp/output/kimi_proxy2.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
OR_ROOT = "https://openrouter.ai/api"
TARGET_MODEL = "moonshotai/kimi-k3"
REASONING_EFFORT = None
MAX_RETRIES = 10
BACKOFF_BASE = 2.0
BACKOFF_CAP = 25.0
KEY_VAR = "OPENROUTER_API_KEY"


def key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(KEY_VAR + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"no {KEY_VAR}")


KEY = key()


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def backoff(attempt):
    return min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt)) + random.uniform(0, 1.5)


def stream_error(first: bytes):
    """THE REAL BUG (diagnosed 2026-07-17 08:40 via first-chunk capture).

    OpenRouter does NOT always signal throttling with an HTTP 429. Under load it returns
    HTTP *200* with the rate-limit error embedded in the SSE body:

        event: ping
        data: {"type":"ping"}
        event: error
        data: {"type":"error","error":{"type":"rate_limit_error",
               "message":"Provider returned error","error_type":"rate_limit_exceeded"}}

    kimi_proxy.py only ever retried on HTTP status (429/5xx), so a 200-wrapped rate limit
    was forwarded verbatim; `claude` then saw a stream with nothing but an error event and
    aborted the whole cell with "empty or malformed response (HTTP 200)". This is why T7 --
    the longest tool chain, hence the most requests, hence the most exposure -- died every
    single run while shorter cells survived. The throttle was always the cause; the shim
    just could not see it.

    Returns a short reason string when the first chunk carries an error event (=> retry
    it exactly like a 429), else None. A healthy response never opens with an error event.
    """
    try:
        s = first.decode("utf-8", "replace")
    except Exception:
        return None
    if '"type":"error"' not in s.replace(" ", ""):
        return None
    low = s.lower()
    for marker in ("rate_limit", "engine_overloaded", "overloaded",
                   "too many requests", "quota", "capacity"):
        if marker in low:
            return marker
    return "error_event"


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

        for attempt in range(MAX_RETRIES + 1):
            req = urllib.request.Request(OR_ROOT + self.path, data=raw or None, method=method)
            req.add_header("Authorization", f"Bearer {KEY}")
            for h in ("Content-Type", "anthropic-version", "anthropic-beta"):
                if self.headers.get(h):
                    req.add_header(h, self.headers[h])
            try:
                up = urllib.request.urlopen(req, timeout=600)
            except urllib.error.HTTPError as e:
                code = e.code
                if code in (429, 500, 502, 503, 529) and attempt < MAX_RETRIES:
                    w = backoff(attempt)
                    log(f"  upstream {code} (attempt {attempt+1}/{MAX_RETRIES}) -> retry in {w:.1f}s")
                    time.sleep(w)
                    continue
                err = e.read()
                log(f"  upstream {code} FINAL: {err[:200].decode(errors='replace')}")
                self.send_response(code)
                self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(err)
                return
            except urllib.error.URLError as e:
                if attempt < MAX_RETRIES:
                    w = backoff(attempt)
                    log(f"  urlerror {e} (attempt {attempt+1}) -> retry in {w:.1f}s")
                    time.sleep(w)
                    continue
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": str(e)}}).encode())
                return

            # ---- THE FIX: peek before committing the 200 ----
            try:
                first = up.read(1024)
            except Exception as e:
                first = b""
                log(f"  first-chunk read error: {e}")

            if not first:
                if attempt < MAX_RETRIES:
                    w = backoff(attempt)
                    log(f"  upstream 200 EMPTY BODY (attempt {attempt+1}/{MAX_RETRIES}) -> retry in {w:.1f}s")
                    time.sleep(w)
                    continue
                log("  upstream 200 EMPTY BODY FINAL -> 502 to client")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": {"type": "api_error",
                               "message": "upstream returned empty body after retries"}}).encode())
                return

            # ---- THE REAL FIX: a 200 whose body opens with an error event is a
            # disguised rate limit. Retry it exactly like a 429. ----
            why = stream_error(first)
            if why:
                if attempt < MAX_RETRIES:
                    w = backoff(attempt)
                    log(f"  upstream 200-wrapped {why} (attempt {attempt+1}/{MAX_RETRIES}) -> retry in {w:.1f}s")
                    time.sleep(w)
                    continue
                log(f"  upstream 200-wrapped {why} FINAL -> 429 to client")
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(first)
                return

            # good response — commit and stream the rest verbatim
            self.send_response(200)
            self.send_header("Content-Type", up.headers.get("Content-Type", "application/json"))
            self.end_headers()
            try:
                self.wfile.write(first)
                self.wfile.flush()
                while True:
                    chunk = up.read(1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception as e:
                log(f"  stream error: {e}")
            return

    def do_POST(self):
        self._forward("POST")

    def do_GET(self):
        self._forward("GET")

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--model", default="moonshotai/kimi-k3")
    ap.add_argument("--reasoning-effort", default=None)
    args = ap.parse_args()
    global TARGET_MODEL, REASONING_EFFORT
    TARGET_MODEL = args.model
    REASONING_EFFORT = args.reasoning_effort
    log(f"=== kimi_proxy2 (empty-200 fix) start: port={args.port} target={TARGET_MODEL} "
        f"reasoning={REASONING_EFFORT} max_retries={MAX_RETRIES} ===")
    print(f"kimi_proxy2 on http://localhost:{args.port} -> {TARGET_MODEL} (empty-200 retry; log: {LOG})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
