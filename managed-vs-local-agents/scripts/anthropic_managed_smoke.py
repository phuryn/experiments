"""Smoke: one Anthropic Managed Agents run end-to-end.
Learns the usage shape + confirms output extraction + measures time/cost before scaling.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_client as gc
import anthropic

BETA = ["managed-agents-2026-04-01"]
MODEL = "claude-haiku-4-5"  # flash-tier-comparable for a fair cross-vendor cost view
client = anthropic.Anthropic(api_key=gc._load_key("ANTHROPIC_API_KEY"))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

def main():
    log = {}
    t0 = time.time()
    env = client.beta.environments.create(name="exp-env", config={"type": "cloud", "networking": {"type": "unrestricted"}}, betas=BETA)
    log["environment_id"] = env.id
    print("env:", env.id)

    agent = client.beta.agents.create(
        name="exp-mgr-smoke", model=MODEL,
        system="You are precise. Use tools/code when needed. Output only the final answer.",
        tools=[{"type": "agent_toolset_20260401", "default_config": {"enabled": True}}],
        betas=BETA,
    )
    log["agent_id"] = agent.id
    print("agent:", agent.id, "v", agent.version)

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": agent.id, "version": agent.version},
        environment_id=env.id, betas=BETA,
    )
    print("session:", session.id)

    task = "Calculate the sum of all prime numbers strictly below 1000. Output ONLY the final integer."
    client.beta.sessions.events.send(session_id=session.id,
        events=[{"type": "user.message", "content": [{"type": "text", "text": task}]}], betas=BETA)

    out_text = []
    event_types = []
    t_run = time.time()
    try:
        with client.beta.sessions.events.stream(session_id=session.id, betas=BETA) as stream:
            for event in stream:
                et = getattr(event, "type", "?")
                event_types.append(et)
                # collect any text content
                content = getattr(event, "content", None)
                if content:
                    for b in content:
                        if getattr(b, "type", None) == "text":
                            out_text.append(b.text)
                if et in ("session.status_terminated",):
                    break
                if et == "session.status_idle":
                    # idle w/o requires_action => done
                    sr = getattr(event, "stop_reason", None)
                    if not sr or getattr(sr, "type", None) != "requires_action":
                        break
    except Exception as e:
        log["stream_error"] = f"{type(e).__name__}: {e}"
        print("stream error:", e)

    elapsed = time.time() - t0
    sess = client.beta.sessions.retrieve(session_id=session.id, betas=BETA)
    usage = getattr(sess, "usage", None)
    status = getattr(sess, "status", None)

    log.update({
        "model": MODEL, "elapsed_total_s": round(elapsed, 2), "run_s": round(time.time() - t_run, 2),
        "status": str(status), "event_types": event_types,
        "output_text": " ".join(out_text)[:500],
        "usage_repr": str(usage)[:800],
    })
    json.dump(log, open(os.path.join(DATA, "anthropic_managed_smoke.json"), "w"), indent=2, default=str)
    print("\n=== SMOKE RESULT ===")
    print("status:", status)
    print("event types:", event_types)
    print("output:", (" ".join(out_text))[:200])
    print("usage:", str(usage)[:600])
    print("elapsed:", round(elapsed, 1), "s")
    # cleanup
    try:
        client.beta.agents.archive(agent.id, betas=BETA)
    except Exception:
        pass

if __name__ == "__main__":
    main()
