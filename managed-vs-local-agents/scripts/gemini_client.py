"""Shared Gemini client for the Managed Agents experiment.
Loads GEMINI_API_KEY from repo .env. Provides:
  - generate_content(model, prompt, ...)        -> raw generateContent
  - run_interaction(task, agent=..., poll=True) -> Managed Agents loop (Arm A)
  - register_agent(spec)                         -> POST /v1beta/agents (custom agent)
No third-party deps (urllib only).
"""
import json, os, time, urllib.request, urllib.error

BASE = "https://generativelanguage.googleapis.com/v1beta"
API_REVISION = "2026-05-20"


def _load_key(name="GEMINI_API_KEY"):
    # find .env walking up from this file
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        p = os.path.join(here, ".env")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
        here = os.path.dirname(here)
    raise RuntimeError(f"{name} not found in .env")


KEY = _load_key()


def _headers(extra=None):
    h = {"x-goog-api-key": KEY, "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def _post(path, body, headers=None, timeout=300):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers=_headers(headers), method="POST"
    )
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return {"ok": True, "status": r.status, "json": json.load(r), "elapsed": time.time() - t0}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1500], "elapsed": time.time() - t0}
    except Exception as e:
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}", "elapsed": time.time() - t0}


def _get(path, timeout=120):
    req = urllib.request.Request(BASE + path, headers=_headers({"Api-Revision": API_REVISION}))
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return {"ok": True, "status": r.status, "json": json.load(r), "elapsed": time.time() - t0}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": e.read().decode()[:1500], "elapsed": time.time() - t0}
    except Exception as e:
        return {"ok": False, "status": None, "error": f"{type(e).__name__}: {e}", "elapsed": time.time() - t0}


def generate_content(model, prompt, system=None, tools=None, timeout=120):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools
    return _post(f"/models/{model}:generateContent", body, timeout=timeout)


def run_interaction(task, agent="antigravity-preview-05-2026", environment=None, previous=None, poll=True, timeout=300):
    body = {"agent": agent, "input": [{"type": "text", "text": task}]}
    body["environment"] = environment or {"type": "remote"}
    if previous:
        body["previous_interaction_id"] = previous
    res = _post("/interactions", body, headers={"Api-Revision": API_REVISION}, timeout=timeout)
    if not res["ok"] or not poll:
        return res
    j = res["json"]
    # If the response is already terminal, return it. Otherwise poll by id.
    status = j.get("status") or j.get("state")
    iid = j.get("id") or j.get("name")
    if (j.get("output_text") is not None) or (status in ("COMPLETED", "SUCCEEDED", "DONE", "completed")):
        return res
    if iid and poll:
        # poll the interaction resource
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(3)
            g = _get(f"/interactions/{iid.split('/')[-1]}")
            if g["ok"]:
                gj = g["json"]
                st = gj.get("status") or gj.get("state")
                if (gj.get("output_text") is not None) or (st in ("COMPLETED", "SUCCEEDED", "DONE", "completed", "FAILED", "ERROR")):
                    g["elapsed"] = res["elapsed"] + (time.time() - (deadline - timeout))
                    return g
            else:
                # polling not supported / different shape; return original
                return res
    return res


def register_agent(spec, timeout=120):
    return _post("/agents", spec, headers={"Api-Revision": API_REVISION}, timeout=timeout)


if __name__ == "__main__":
    print("key prefix:", KEY[:3] + "...")
    print("quick generate:", generate_content("gemini-2.5-flash", "Say PONG").get("json", {}).get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "ERR")[:20] if True else "")
