#!/usr/bin/env python3
"""Mine billed token usage for the Set 02 audit runs from local Claude Code
session logs (~/.claude/projects/<editor-slug>/*.jsonl) — the claude-usage
approach: dedup assistant records by message.id (last record wins), sum usage,
price per message.model at public API rates.

Audit sessions are identified by their FIRST user message == the Set 02 audit
prompt. Matched back to set02 / set02-v4 CSV rows by model + start time.

Output: Temp/output/fable5-n10/audit_usage.csv + stdout summary.
"""
import csv, glob, json, os, statistics as st
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
PROJ = os.path.join(HOME, ".claude", "projects", "SESSION-PROJECT-SLUG")
OUT = r"<WORKDIR>\Temp\output\fable5-n10"
PROMPT_PREFIX = "Audit knowledge/craft/human-signals.md, knowledge/craft/word_choice.md,"
LOCAL_UTC_OFFSET = 2  # CEDT, June 2026

# $/MTok: (input, output, cache_write_5m, cache_write_1h, cache_read)
PRICES = {
    "claude-fable-5":  (10.0, 50.0, 12.50, 20.0, 1.00),
    "claude-opus-4-8": (5.0,  25.0,  6.25, 10.0, 0.50),
    "claude-haiku-4-5": (1.0,  5.0,  1.25,  2.0, 0.10),
}
def price_for(model):
    for k, v in PRICES.items():
        if model.startswith(k):
            return v
    return None  # unknown model -> flag, don't silently misprice

def first_user_is_audit(path, max_records=6):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_records:
                    return False
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") == "user":
                    c = rec.get("message", {}).get("content", "")
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    return isinstance(c, str) and c.startswith(PROMPT_PREFIX)
    except OSError:
        pass
    return False

def parse_session(path):
    seen = {}
    no_id = []
    first_ts = last_ts = None
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("timestamp", "")
        if ts:
            first_ts = ts if first_ts is None or ts < first_ts else first_ts
            last_ts = ts if last_ts is None or ts > last_ts else last_ts
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message", {})
        u = msg.get("usage", {})
        tok = [u.get(k, 0) or 0 for k in ("input_tokens", "output_tokens",
                                          "cache_read_input_tokens", "cache_creation_input_tokens")]
        if sum(tok) == 0:
            continue
        cc = u.get("cache_creation") or {}
        turn = {"model": msg.get("model", ""), "in": tok[0], "out": tok[1],
                "cr": tok[2], "cw": tok[3],
                "cw_5m": cc.get("ephemeral_5m_input_tokens", None),
                "cw_1h": cc.get("ephemeral_1h_input_tokens", None)}
        mid = msg.get("id", "")
        if mid:
            seen[mid] = turn
        else:
            no_id.append(turn)
    return list(seen.values()) + no_id, first_ts, last_ts

def session_cost(turns):
    cost, unknown = 0.0, set()
    agg = {"in": 0, "out": 0, "cw": 0, "cr": 0}
    main_model = ""
    for t in turns:
        p = price_for(t["model"])
        if p is None:
            unknown.add(t["model"])
            continue
        pin, pout, pw5, pw1, prd = p
        if t["cw_5m"] is not None or t["cw_1h"] is not None:
            w_cost = (t["cw_5m"] or 0) * pw5 + (t["cw_1h"] or 0) * pw1
        else:
            w_cost = t["cw"] * pw5  # assume 5m writes if no detail present
        cost += (t["in"] * pin + t["out"] * pout + w_cost + t["cr"] * prd) / 1e6
        for k in agg:
            agg[k] += t[k]
        if not t["model"].startswith("claude-haiku") and t["model"]:
            main_model = t["model"]
    return cost, agg, main_model, unknown

def load_csv_rows():
    rows = []
    for name in ("set02.csv", "set02-v4.csv"):
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r["exp"] == "audit" and r["rc"] == "0":
                end = datetime.fromisoformat(r["ts"])
                start = end - timedelta(seconds=float(r["seconds"]))
                rows.append({"run_id": r["run_id"], "model": r["model"],
                             "start": start, "secs": float(r["seconds"]),
                             "chars": int(r["chars"]), "src": name})
    return rows

def main():
    files = glob.glob(os.path.join(PROJ, "*.jsonl"))
    print(f"scanning {len(files)} session files...")
    sessions = []
    for fp in files:
        if not first_user_is_audit(fp):
            continue
        turns, fts, lts = parse_session(fp)
        if not turns:
            continue
        cost, agg, model, unknown = session_cost(turns)
        start_local = (datetime.fromisoformat(fts.replace("Z", "+00:00"))
                       .astimezone(timezone(timedelta(hours=LOCAL_UTC_OFFSET)))
                       .replace(tzinfo=None))
        sessions.append({"file": os.path.basename(fp), "start": start_local,
                         "model": model, "cost": cost, "turns": len(turns),
                         "unknown": unknown, **agg})
    print(f"audit sessions found: {len(sessions)}")

    cli_model = {"fable": "claude-fable-5", "opus": "claude-opus-4-8"}
    runs = load_csv_rows()
    print(f"clean audit CSV rows: {len(runs)}")
    # greedy match: same model, closest start-time
    for s in sessions:
        s["match"] = None
    for run in sorted(runs, key=lambda r: r["start"]):
        best, best_d = None, None
        for s in sessions:
            if s["match"] or not s["model"].startswith(cli_model[run["model"]]):
                continue
            d = abs((s["start"] - run["start"]).total_seconds())
            if best is None or d < best_d:
                best, best_d = s, d
        if best is not None and best_d <= 120:
            best["match"] = run["run_id"]
            run["session"] = best

    out_path = os.path.join(OUT, "audit_usage.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_id", "src", "model", "start", "secs", "chars",
                    "in_tok", "out_tok", "cache_w", "cache_r", "cost_usd", "api_turns", "session_file"])
        for run in runs:
            s = run.get("session")
            if s:
                w.writerow([run["run_id"], run["src"], run["model"], run["start"].isoformat(),
                            run["secs"], run["chars"], s["in"], s["out"], s["cw"], s["cr"],
                            round(s["cost"], 4), s["turns"], s["file"]])
            else:
                w.writerow([run["run_id"], run["src"], run["model"], run["start"].isoformat(),
                            run["secs"], run["chars"], "", "", "", "", "", "", "UNMATCHED"])
    print(f"wrote {out_path}")

    matched = [r for r in runs if r.get("session")]
    print(f"matched {len(matched)}/{len(runs)} runs")
    orphans = [s for s in sessions if not s["match"]]
    if orphans:
        print(f"orphan audit sessions (no CSV row matched): {len(orphans)}")
        for s in orphans[:5]:
            print("  ", s["file"], s["start"], s["model"], f"${s['cost']:.3f}")
    unknown = set().union(*(s["unknown"] for s in sessions)) if sessions else set()
    if unknown:
        print("UNKNOWN MODELS (unpriced!):", unknown)

    for src in ("set02.csv", "set02-v4.csv"):
        for m in ("opus", "fable"):
            costs = [r["session"]["cost"] for r in matched if r["model"] == m and r["src"] == src]
            outs = [r["session"]["out"] for r in matched if r["model"] == m and r["src"] == src]
            if costs:
                print(f"{src} {m:5}: n={len(costs)}  cost med=${st.median(costs):.3f} "
                      f"[{min(costs):.3f}-{max(costs):.3f}]  out_tok med={st.median(outs):.0f}")

if __name__ == "__main__":
    main()
