#!/usr/bin/env python3
"""
sakana.py — call Sakana AI models (fugu-ultra) via their OpenAI-compatible API.

The client used for the fugu-ultra head-to-head vs the GLM-5.2 / Opus 4.8 /
GPT-5.5 / Fable 5 baselines in this set.

Endpoint: https://api.sakana.ai/v1  (OpenAI Chat Completions shape)
Key:      SAKANA_API_KEY in .env
Model:    fugu-ultra (default)

IMPORTANT — IP allowlist / geo-block. Sakana fronts the API with a GCP load
balancer that blanket-403s requests from datacenter egress IPs (incl. cloud
containers) and from non-US/JP IPs, *before auth*. Run this from a non-blocked
IP — a residential network or a US VPN/SOCKS5 exit. `python sakana.py check`
tells you which case you're in:
  - "EDGE-BLOCKED (403)"  -> this IP is blocked; switch network / use a US exit
  - "401 missing/invalid key" -> IP is fine, key/auth problem
  - "OK ... reply='pong'" -> good to go

A US exit is supplied with --proxy socks5://[user:pass@]host[:port]. Only this
Python process is routed through the proxy — no system VPN, no sudo.

Stdlib only (urllib) + PySocks (only when --proxy is used).

Usage:
  python sakana.py check                         # is this IP allowed? is the key good?
  python sakana.py check --proxy socks5://user:pass@<US-SOCKS-HOST>:1080
  python sakana.py models                        # list models (if endpoint exposes it)
  python sakana.py chat "prompt text"
  python sakana.py chat --file prompt.md --system "you are X" --out <WORKDIR>/Temp/data/fugu_run.json
  echo "prompt" | python sakana.py chat

Flags (chat):
  --model M         default fugu-ultra
  --system S        system prompt
  --file PATH       read user prompt from file (repeatable: concatenated)
  --temperature T   default 0.3
  --max-tokens N    default 4000
  --out PATH        save full JSON response
  --proxy URL       route this process via a SOCKS5 exit (US, for the geo-block)
"""
import sys, json, argparse, urllib.request, urllib.error, subprocess, time, socket
from pathlib import Path

API = "https://api.sakana.ai/v1"


def enable_proxy(proxy):
    """Route ALL sockets in this process through a SOCKS5 proxy.

    proxy: socks5://[user:pass@]host[:port]  (default port 1080).
    Used to give Sakana a US exit IP from a geo-blocked network. Only this
    Python process is affected — no system VPN, no sudo.
    """
    try:
        import socks  # PySocks
    except ImportError:
        sys.exit("error: --proxy needs PySocks. Run: python3 -m pip install --user PySocks")
    from urllib.parse import urlparse
    u = urlparse(proxy if "://" in proxy else "socks5://" + proxy)
    if u.scheme not in ("socks5", "socks5h"):
        sys.exit(f"error: --proxy must be socks5://... (got {u.scheme!r})")
    socks.set_default_proxy(socks.SOCKS5, u.hostname, u.port or 1080,
                            rdns=True, username=u.username, password=u.password)
    socket.socket = socks.socksocket
    sys.stderr.write(f"[routing via SOCKS5 {u.hostname}:{u.port or 1080}]\n")


def find_env_path():
    if Path(".env").exists():
        return Path(".env").resolve()
    try:
        root = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True).strip())
        if (root / ".env").exists():
            return root / ".env"
    except Exception:
        pass
    for p in Path(__file__).resolve().parents:
        if (p / ".env").exists():
            return p / ".env"
    return None


def load_key():
    path = find_env_path()
    if not path:
        sys.exit("error: .env not found")
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("SAKANA_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("error: SAKANA_API_KEY not in .env")


def _req(path, payload=None, method="GET", timeout=600):
    key = load_key()
    url = f"{API}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read())


def cmd_check(args):
    """Distinguish edge-block (403, wrong IP) from auth (401) from success."""
    # First, confirm the exit IP (proves the proxy/US-exit is actually in effect).
    try:
        info = json.loads(urllib.request.urlopen("https://ipinfo.io/json", timeout=20).read())
        print(f"exit IP: {info.get('ip')} ({info.get('country')}, {info.get('org','')[:40]})")
    except Exception as e:
        print(f"exit IP: (could not determine: {str(e)[:80]})")
    key = load_key()
    url = f"{API}/chat/completions"
    payload = {"model": args.model,
               "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
               "max_tokens": 16}  # fugu-ultra requires max_tokens >= 16
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        reply = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        print(f"OK — IP allowed, key valid. model={resp.get('model', args.model)} reply={reply!r}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 403 and "<title>403" in body:
            print("EDGE-BLOCKED (403): this IP is not allowed by Sakana's load balancer.")
            print("  -> switch to a non-datacenter, US/JP IP (residential or a US VPN) and retry.")
        elif e.code == 401:
            print(f"401 missing/invalid key (IP is fine): {body[:300]}")
        else:
            print(f"HTTP {e.code}: {body[:500]}")
    except urllib.error.URLError as e:
        print(f"network error: {e}")


def cmd_chat(args):
    parts = []
    if args.file:
        for f in args.file:
            parts.append(Path(f).read_text())
    if args.prompt:
        parts.append(args.prompt)
    if not parts and not sys.stdin.isatty():
        parts.append(sys.stdin.read())
    user = "\n\n".join(p for p in parts if p.strip())
    if not user.strip():
        sys.exit("error: no prompt (arg, --file, or stdin)")

    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": user})

    payload = {
        "model": args.model,
        "messages": messages,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }

    t0 = time.time()
    try:
        _, resp = _req("/chat/completions", payload, method="POST")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 403 and "<title>403" in body:
            sys.exit("HTTP 403 EDGE-BLOCKED: this IP isn't allowed. Run `python sakana.py check`.")
        sys.exit(f"HTTP {e.code}: {body}")
    dt = time.time() - t0

    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message", {})
    content = msg.get("content", "")
    usage = resp.get("usage", {}) or {}
    print(content)

    pt, ct = usage.get("prompt_tokens"), usage.get("completion_tokens")
    meta = (f"[model={resp.get('model', args.model)} prompt={pt} completion={ct} "
            f"{dt:.1f}s finish={choice.get('finish_reason')}]")
    sys.stderr.write("\n" + meta + "\n")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(resp, indent=2))
        sys.stderr.write(f"[saved {args.out}]\n")


def cmd_models(args):
    try:
        _, resp = _req("/models")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 403 and "<title>403" in body:
            sys.exit("HTTP 403 EDGE-BLOCKED: this IP isn't allowed. Run `python sakana.py check`.")
        sys.exit(f"HTTP {e.code}: {body}")
    rows = resp.get("data", resp)
    print(json.dumps(rows, indent=2)[:4000])


def main():
    ap = argparse.ArgumentParser(description="Sakana AI CLI (fugu-ultra)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    PROXY_HELP = ("route via SOCKS5, e.g. socks5://user:pass@<US-SOCKS-HOST>:1080 "
                  "(a US exit for the geo-block)")

    k = sub.add_parser("check", help="is this IP allowed + key valid?")
    k.add_argument("--model", default="fugu-ultra")
    k.add_argument("--proxy", help=PROXY_HELP)
    k.set_defaults(func=cmd_check)

    c = sub.add_parser("chat", help="chat completion")
    c.add_argument("prompt", nargs="?", help="user prompt (or use --file/stdin)")
    c.add_argument("--model", default="fugu-ultra")
    c.add_argument("--system")
    c.add_argument("--file", action="append")
    c.add_argument("--temperature", type=float, default=0.3)
    c.add_argument("--max-tokens", type=int, default=4000)
    c.add_argument("--out")
    c.add_argument("--proxy", help=PROXY_HELP)
    c.set_defaults(func=cmd_chat)

    m = sub.add_parser("models", help="list models (if exposed)")
    m.add_argument("--model", default="fugu-ultra")
    m.add_argument("--proxy", help=PROXY_HELP)
    m.set_defaults(func=cmd_models)

    args = ap.parse_args()
    if getattr(args, "proxy", None):
        enable_proxy(args.proxy)
    args.func(args)


if __name__ == "__main__":
    main()
