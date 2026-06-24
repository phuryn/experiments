#!/usr/bin/env python3
"""fugu-ultra reliability by effort (Result: reliability.csv) + visible output tokens.

Raw OpenAI-compatible API, routed through a US SOCKS5 exit (geo-block workaround).
fugu-ultra has NO off switch: reasoning_effort in {high,xhigh,max}; 'default' = omit it.

Two checkable problems (same as the GLM-5.2 / Opus rig):
  P1 (hard):  automorphic count, n^2 ends in same last 3 digits as n  -> ans 3 (1,376,625)
  P2 (med):   count 1..1000 divisible by neither 3 nor 7               -> ans 572

Env (.env, key names only — values never appear here):
  SAKANA_API_KEY        Sakana API key
  SOCKS_USER, SOCKS_PASS  credentials for the US SOCKS5 exit
  SOCKS_HOST (env var)  US SOCKS5 hostname (default left unset — supply your own)

Writes:
  fugu-ultra-vs-frontier/reliability.csv          (per-call rows; in this folder)
  <WORKDIR>/Temp/data/fugu_reliability_raw/*.json (full responses, gitignored)
"""
import json, os, socket, sys, time, csv, urllib.request, urllib.error, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[2]
def env(k):
    for line in (ROOT/".env").read_text().splitlines():
        line=line.strip()
        if line.startswith(k+"="): return line.split("=",1)[1].strip()
    sys.exit(f"{k} missing")

KEY = env("SAKANA_API_KEY")
U, P = env("SOCKS_USER"), env("SOCKS_PASS")
HOST = os.environ.get("SOCKS_HOST")  # supply a US SOCKS5 exit hostname
if not HOST:
    sys.exit("set SOCKS_HOST=<your US SOCKS5 host> (geo-block workaround)")
import socks
socks.set_default_proxy(socks.SOCKS5, HOST, 1080, rdns=True, username=U, password=P)
socket.socket = socks.socksocket
API = "https://api.sakana.ai/v1/chat/completions"

OUTDIR = ROOT/"Temp"/"data"/"fugu_reliability_raw"; OUTDIR.mkdir(parents=True, exist_ok=True)
CSV = Path(__file__).resolve().parents[1]/"reliability.csv"

PROBLEMS = {
  "P1": "How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits as n (treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number and the list of such n.",
  "P2": "How many integers n with 1 <= n <= 1000 are divisible by neither 3 nor 7? Work it out carefully, then give the final count.",
}
def grade(pid, t):
    if pid=="P1": return ("376" in t) and ("625" in t)
    if pid=="P2": return bool(re.search(r"\b572\b", t))
    return None

EFFORTS = ["default","high","xhigh","max"]
N = 8

def call(pid, eff, i):
    payload = {"model":"fugu-ultra","messages":[{"role":"user","content":PROBLEMS[pid]}],
               "max_tokens":4000,"temperature":0.3}
    if eff!="default": payload["reasoning_effort"]=eff
    for attempt in range(2):
        t0=time.time()
        try:
            req=urllib.request.Request(API,data=json.dumps(payload).encode(),method="POST")
            req.add_header("Authorization",f"Bearer {KEY}"); req.add_header("Content-Type","application/json")
            with urllib.request.urlopen(req,timeout=600) as r: resp=json.loads(r.read())
            dt=time.time()-t0
            ch=(resp.get("choices") or [{}])[0]; content=ch.get("message",{}).get("content") or ""
            u=resp.get("usage",{}) or {}
            pd=u.get("prompt_tokens_details",{}) or {}; cd=u.get("completion_tokens_details",{}) or {}
            (OUTDIR/f"{pid}_{eff}_{i}.json").write_text(json.dumps(resp,indent=2))
            return {"problem":pid,"effort":eff,"i":i,"rc":0,
                    "correct":grade(pid,content),
                    "completion_tokens":u.get("completion_tokens"),
                    "total_tokens":u.get("total_tokens"),
                    "orchestration_in":pd.get("orchestration_input_tokens"),
                    "orchestration_out":cd.get("orchestration_output_tokens"),
                    "reasoning_tokens":cd.get("reasoning_tokens"),
                    "finish":ch.get("finish_reason"),"sec":round(dt,1),
                    "answer_tail":content.strip().replace("\n"," ")[-160:]}
        except urllib.error.HTTPError as e:
            body=e.read().decode(errors="replace")
            if attempt==0 and e.code in (429,500,502,503,504): time.sleep(5); continue
            return {"problem":pid,"effort":eff,"i":i,"rc":e.code,"correct":None,
                    "completion_tokens":None,"total_tokens":None,"orchestration_in":None,
                    "orchestration_out":None,"reasoning_tokens":None,"finish":f"HTTP{e.code}",
                    "sec":round(time.time()-t0,1),"answer_tail":body[:160]}
        except Exception as e:
            if attempt==0: time.sleep(5); continue
            return {"problem":pid,"effort":eff,"i":i,"rc":-1,"correct":None,
                    "completion_tokens":None,"total_tokens":None,"orchestration_in":None,
                    "orchestration_out":None,"reasoning_tokens":None,"finish":"ERR",
                    "sec":round(time.time()-t0,1),"answer_tail":str(e)[:160]}

jobs=[(pid,eff,i) for pid in PROBLEMS for eff in EFFORTS for i in range(1,N+1)]
print(f"running {len(jobs)} calls (concurrency 6) ...")
rows=[]
with ThreadPoolExecutor(max_workers=6) as ex:
    futs={ex.submit(call,*j):j for j in jobs}
    done=0
    for f in as_completed(futs):
        r=f.result(); rows.append(r); done+=1
        print(f"[{done}/{len(jobs)}] {r['problem']} {r['effort']:7} #{r['i']} "
              f"correct={r['correct']} comp={r['completion_tokens']} tot={r['total_tokens']} "
              f"{r['sec']}s {r['finish']}")

cols=["problem","effort","i","rc","correct","completion_tokens","total_tokens",
      "orchestration_in","orchestration_out","reasoning_tokens","finish","sec","answer_tail"]
rows.sort(key=lambda r:(r["problem"],EFFORTS.index(r["effort"]),r["i"]))
with open(CSV,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)
print(f"\nwrote {CSV}")
