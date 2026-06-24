#!/usr/bin/env python3
"""Planted cross-file bug — diligence test, IN-CONTEXT variant for fugu-ultra.

Single call per run: all three style-guide files pasted in, asked to find
cross-file contradictions. Removes retrieval (model gets every file for free)
-> a fair-to-stronger diligence test than the agentic baselines: if fugu misses
the planted contradiction with all files in hand, that's a clean miss.
Reported as a distinct harness from the claude -p agentic baselines, not a
drop-in apples-to-apples number.

Routes through a US SOCKS5 exit (geo-block workaround).
Usage: SOCKS_HOST=<host> python fugu_audit_incontext.py --n 10 --concurrency 5

WITHHELD (honesty bar): the three style-guide files belong to a private content
repo and are NOT published. This script reads them from <WORKDIR> at run time;
the planted contradiction is real but its exact wording is the answer key, which
this repo withholds. The grader tokens below are placeholders (FILE_A/B,
KEY_TOKEN_*) so the script is auditable without leaking the private content.
"""
import json, os, socket, sys, time, csv, re, argparse, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[2]
def env(k):
    for line in (ROOT/".env").read_text().splitlines():
        line=line.strip()
        if line.startswith(k+"="): return line.split("=",1)[1].strip()
    sys.exit(f"{k} missing")
KEY=env("SAKANA_API_KEY"); U,P=env("SOCKS_USER"),env("SOCKS_PASS")
HOST=os.environ.get("SOCKS_HOST")
if not HOST: sys.exit("set SOCKS_HOST=<your US SOCKS5 host>")
import socks
socks.set_default_proxy(socks.SOCKS5,HOST,1080,rdns=True,username=U,password=P)
socket.socket=socks.socksocket
API="https://api.sakana.ai/v1/chat/completions"
OUTDIR=ROOT/"Temp"/"data"/"fugu_audit_incontext"; OUTDIR.mkdir(parents=True,exist_ok=True)

# Three real style-guide files in the private content repo (withheld). Paths are
# placeholders here; the live script points them at the actual files under <WORKDIR>.
FILES=["<WORKDIR>/knowledge/craft/FILE_A.md",
       "<WORKDIR>/knowledge/craft/FILE_B.md",
       "<WORKDIR>/knowledge/craft/FILE_C.md"]
blocks=[]
for f in FILES:
    blocks.append(f"===== FILE: {f} =====\n"+(ROOT/f).read_text(encoding="utf-8",errors="replace"))
CORPUS="\n\n".join(blocks)
# The audit instruction is generic; it is the only model-facing prompt and is
# published verbatim in prompt.txt. The corpus (private files) is appended at run time.
PROMPT=("Audit my craft style-guide files below for cross-file contradictions — places where two "
  "files give conflicting or inconsistent guidance that only shows up if you read them against each "
  "other. For each contradiction, quote the load-bearing line from each file (with the file name) and "
  "say which side should win.\n\n"+CORPUS)

# Grader (genericized). The real grader keys on the two load-bearing numbers of the
# planted contradiction and that the answer frames the right conflict. Those tokens
# are the answer key -> withheld; placeholders shown for auditability.
KEY_TOKEN_LOW  = r"<KEY_TOKEN_LOW>"   # the lower threshold one file gates a tactic at
KEY_TOKEN_HIGH = r"<KEY_TOKEN_HIGH>"  # the higher threshold the other file says it fails at
KEY_TOPIC      = r"<KEY_TOPIC>"       # the tactic the two files disagree about
def grade(t):
    loose  = bool(re.search(f"{KEY_TOKEN_LOW}|{KEY_TOKEN_HIGH}", t, re.I))
    has_lo = bool(re.search(KEY_TOKEN_LOW, t, re.I))
    has_hi = bool(re.search(KEY_TOKEN_HIGH, t, re.I))
    strict = has_lo and has_hi and bool(re.search(KEY_TOPIC, t, re.I))
    return loose, strict

def run_one(idx):
    payload={"model":"fugu-ultra","max_tokens":16000,"temperature":0.3,
             "messages":[{"role":"user","content":PROMPT}]}
    t0=time.time()
    for attempt in range(3):
        try:
            req=urllib.request.Request(API,data=json.dumps(payload).encode(),method="POST")
            req.add_header("Authorization",f"Bearer {KEY}"); req.add_header("Content-Type","application/json")
            with urllib.request.urlopen(req,timeout=600) as r: resp=json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            body=e.read().decode(errors="replace")
            if attempt<2 and e.code in (429,500,502,503,504): time.sleep(6); continue
            return {"idx":idx,"rc":e.code,"loose":None,"strict":None,"completion_tokens":None,
                    "total_tokens":None,"orchestration_in":None,"sec":round(time.time()-t0,1)}
        except Exception:
            if attempt<2: time.sleep(6); continue
            return {"idx":idx,"rc":-1,"loose":None,"strict":None,"completion_tokens":None,
                    "total_tokens":None,"orchestration_in":None,"sec":round(time.time()-t0,1)}
    dt=time.time()-t0
    ch=(resp.get("choices") or [{}])[0]; content=ch.get("message",{}).get("content") or ""
    u=resp.get("usage",{}) or {}
    loose,strict=grade(content)
    (OUTDIR/f"run_{idx:02d}.json").write_text(json.dumps(
        {"idx":idx,"loose":loose,"strict":strict,"completion_tokens":u.get("completion_tokens"),
         "total_tokens":u.get("total_tokens"),
         "orchestration_in":(u.get("prompt_tokens_details",{}) or {}).get("orchestration_input_tokens"),
         "sec":round(dt,1),"final":content},indent=2),encoding="utf-8")
    return {"idx":idx,"rc":0,"loose":loose,"strict":strict,"completion_tokens":u.get("completion_tokens"),
            "total_tokens":u.get("total_tokens"),
            "orchestration_in":(u.get("prompt_tokens_details",{}) or {}).get("orchestration_input_tokens"),
            "sec":round(dt,1)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--n",type=int,default=10); ap.add_argument("--start",type=int,default=1)
    ap.add_argument("--concurrency",type=int,default=5)
    a=ap.parse_args()
    idxs=list(range(a.start,a.start+a.n))
    print(f"in-context audit runs {idxs[0]}..{idxs[-1]} concurrency {a.concurrency}; corpus ~{len(CORPUS)} chars")
    rows=[]
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs={ex.submit(run_one,i):i for i in idxs}
        done=0
        for f in as_completed(futs):
            r=f.result(); rows.append(r); done+=1
            print(f"[{done}/{len(idxs)}] run{r['idx']:02d} rc={r['rc']} loose={r['loose']} strict={r['strict']} "
                  f"comp={r['completion_tokens']} tot={r['total_tokens']} {r['sec']}s")
    rows.sort(key=lambda r:r["idx"])
    csvp=Path(__file__).resolve().parents[1]/"planted_bug_incontext.csv"
    cols=["idx","rc","loose","strict","completion_tokens","total_tokens","orchestration_in","sec"]
    with open(csvp,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for r in rows: w.writerow(r)
    ok=[r for r in rows if r["rc"]==0]
    loose=sum(1 for r in ok if r["loose"]); strict=sum(1 for r in ok if r["strict"])
    print(f"\nLOOSE: {loose}/{len(ok)}   STRICT (both-sides): {strict}/{len(ok)}   wrote {csvp}")

if __name__=="__main__": main()
