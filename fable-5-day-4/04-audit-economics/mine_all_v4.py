#!/usr/bin/env python3
"""Per-card billed-token totals for the v4 collections, mined from local session
logs. Matches every clean v4 run (sets 01/02/03) to its session by prompt prefix
+ model + start time, then sums usage per card:
  card 33 = set01-v4 (420 runs)   card 32 = set02-v4 + set03-v4 (360 runs)
"""
import csv, glob, json, os
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
PROJ = os.path.join(HOME, ".claude", "projects", "SESSION-PROJECT-SLUG")
OUT = r"<WORKDIR>\Temp\output\fable5-n10"
LOCAL = timezone(timedelta(hours=2))  # CEDT

PK = {  # prompt-prefix keys
    "QA": "Explain in exactly 3 bullet points why nested subagents cost more",
    "QM": "Do knowledge/craft/human-signals.md and knowledge/craft/word_choice.md disagree",
    "QH": "How many positive integers n < 1000 satisfy",
    "Q1": "What tool does CLAUDE.md say to use for exporting infographics",
    "Q2": "Per knowledge/platforms/substack/paywall-patterns.md",
    "Q3": "What are the three buckets in Section 5.1",
    "Q4": "What does tools/README.md say is the cheapest data-fetching tool",
    "Q5": "How many lenses does knowledge/lenses/INDEX.md list",
    "AUD": "Audit knowledge/craft/human-signals.md, knowledge/craft/word_choice.md,",
}
CLI_MODEL = {"fable": "claude-fable-5", "opus": "claude-opus-4-8"}
# $/MTok: in, out, cache_w_5m, cache_w_1h, cache_read
PRICES = {"claude-fable-5": (10, 50, 12.5, 20, 1), "claude-opus-4-8": (5, 25, 6.25, 10, 0.5),
          "claude-haiku-4-5": (1, 5, 1.25, 2, 0.1)}

def load_runs():
    runs = []
    for r in csv.DictReader(open(os.path.join(OUT, "set01-v4.csv"), encoding="utf-8")):
        if r["rc"] != "0" or r["round"] == "0": continue
        pk = "QA" if r["tier"] in ("easy", "control") else ("QM" if r["tier"] == "realistic" else "QH")
        runs.append(("33", pk, r["model"],
                     datetime.fromisoformat(r["ts"]) - timedelta(seconds=float(r["seconds"]))))
    for r in csv.DictReader(open(os.path.join(OUT, "set02-v4.csv"), encoding="utf-8")):
        if r["rc"] != "0" or r["round"] == "0": continue
        pk = "AUD" if r["exp"] == "audit" else r["q"]
        runs.append(("32", pk, r["model"],
                     datetime.fromisoformat(r["ts"]) - timedelta(seconds=float(r["seconds"]))))
    for r in csv.DictReader(open(os.path.join(OUT, "set03-v4.csv"), encoding="utf-8")):
        if r["rc"] != "0" or r["round"] == "0": continue
        pk = "QA" if r["prompt_id"] == "easy" else "QH"
        runs.append(("32", pk, r["model"],
                     datetime.fromisoformat(r["ts"]) - timedelta(seconds=float(r["t_total"]))))
    return runs

def first_user_key(path, max_records=6):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= max_records: return None
                try: rec = json.loads(line)
                except json.JSONDecodeError: continue
                if rec.get("type") == "user":
                    c = rec.get("message", {}).get("content", "")
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    if not isinstance(c, str): return None
                    for k, pre in PK.items():
                        if c.startswith(pre): return k
                    return None
    except OSError: pass
    return None

def parse_session(path):
    seen, no_id, first_ts = {}, [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        try: rec = json.loads(line)
        except json.JSONDecodeError: continue
        ts = rec.get("timestamp", "")
        if ts and (first_ts is None or ts < first_ts): first_ts = ts
        if rec.get("type") != "assistant": continue
        msg = rec.get("message", {})
        u = msg.get("usage", {})
        tok = [u.get(k, 0) or 0 for k in ("input_tokens", "output_tokens",
                                          "cache_read_input_tokens", "cache_creation_input_tokens")]
        if sum(tok) == 0: continue
        cc = u.get("cache_creation") or {}
        t = {"model": msg.get("model", ""), "in": tok[0], "out": tok[1], "cr": tok[2], "cw": tok[3],
             "cw5": cc.get("ephemeral_5m_input_tokens"), "cw1": cc.get("ephemeral_1h_input_tokens")}
        mid = msg.get("id", "")
        (seen.__setitem__(mid, t) if mid else no_id.append(t))
    return list(seen.values()) + no_id, first_ts

def main():
    files = glob.glob(os.path.join(PROJ, "*.jsonl"))
    print(f"scanning {len(files)} files...")
    sessions = []
    for fp in files:
        k = first_user_key(fp)
        if not k: continue
        turns, fts = parse_session(fp)
        if not turns or not fts: continue
        start = datetime.fromisoformat(fts.replace("Z", "+00:00")).astimezone(LOCAL).replace(tzinfo=None)
        main_model = next((t["model"] for t in turns if not t["model"].startswith("claude-haiku") and t["model"]), "")
        sessions.append({"key": k, "model": main_model, "start": start, "turns": turns, "used": False})
    print(f"candidate sessions: {len(sessions)}")

    runs = load_runs()
    print(f"clean v4 runs: {len(runs)} (33: {sum(1 for r in runs if r[0]=='33')}, 32: {sum(1 for r in runs if r[0]=='32')})")
    agg = {"33": {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0, "n": 0},
           "32": {"in": 0, "out": 0, "cw": 0, "cr": 0, "cost": 0.0, "n": 0}}
    unmatched = 0
    for card, pk, model, start in sorted(runs, key=lambda r: r[3]):
        best, best_d = None, None
        for s in sessions:
            if s["used"] or s["key"] != pk or not s["model"].startswith(CLI_MODEL[model]): continue
            d = abs((s["start"] - start).total_seconds())
            if best is None or d < best_d: best, best_d = s, d
        if best is None or best_d > 120:
            unmatched += 1
            continue
        best["used"] = True
        a = agg[card]; a["n"] += 1
        for t in best["turns"]:
            p = next((v for k2, v in PRICES.items() if t["model"].startswith(k2)), None)
            if p is None: continue
            w = (t["cw5"] or 0) * p[2] + (t["cw1"] or 0) * p[3] if (t["cw5"] is not None or t["cw1"] is not None) else t["cw"] * p[3]
            a["cost"] += (t["in"] * p[0] + t["out"] * p[1] + w + t["cr"] * p[4]) / 1e6
            a["in"] += t["in"]; a["out"] += t["out"]; a["cw"] += t["cw"]; a["cr"] += t["cr"]
    print(f"unmatched runs: {unmatched}")
    for card in ("33", "32"):
        a = agg[card]
        total = a["in"] + a["out"] + a["cw"] + a["cr"]
        print(f"card {card}: n={a['n']}  in={a['in']:,}  out={a['out']:,}  cache_w={a['cw']:,}  "
              f"cache_r={a['cr']:,}  TOTAL={total:,} ({total/1e6:.2f}M)  cost=${a['cost']:.2f}")

if __name__ == "__main__":
    main()
