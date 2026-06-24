#!/usr/bin/env python3
"""Run GPT-5.5 through the SAME tests as fugu-ultra, for a comparable scorecard column.
OpenAI API (no proxy). Reliability (P1/P2) + in-context planted-bug diligence (n=10).

WITHHELD (honesty bar): the three style-guide files are private and not published;
the planted-contradiction answer key is withheld -> grader tokens are placeholders
(KEY_TOKEN_*). The generic audit instruction is published in prompt.txt.
"""
import json, os, sys, time, csv, re, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[2]
KEY=[l.split('=',1)[1].strip() for l in (ROOT/'.env').read_text(encoding='utf-8').splitlines() if l.startswith('OPENAI_API_KEY=')][0]
API='https://api.openai.com/v1/chat/completions'
MODEL='gpt-5.5'
OUT=Path(__file__).resolve().parents[1]
RAW=ROOT/'Temp'/'data'/'gpt55_raw'; RAW.mkdir(parents=True,exist_ok=True)

def call(messages, max_out, effort='high'):
    p={'model':MODEL,'messages':messages,'max_completion_tokens':max_out,'reasoning_effort':effort}
    for attempt in range(3):
        try:
            req=urllib.request.Request(API,data=json.dumps(p).encode(),method='POST')
            req.add_header('Authorization','Bearer '+KEY); req.add_header('Content-Type','application/json')
            with urllib.request.urlopen(req,timeout=600) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body=e.read().decode(errors='replace')
            if attempt<2 and e.code in (429,500,502,503,504): time.sleep(6); continue
            raise RuntimeError(f'HTTP {e.code}: {body[:200]}')
        except Exception:
            if attempt<2: time.sleep(6); continue
            raise

# ---------- Reliability ----------
PROBLEMS={
 'P1':"How many positive integers n < 1000 satisfy: n squared ends in exactly the same last three digits as n (treat n as zero-padded to 3 digits)? Work it out carefully, then answer with the number and the list of such n.",
 'P2':"How many integers n with 1 <= n <= 1000 are divisible by neither 3 nor 7? Work it out carefully, then give the final count.",
}
def grade_rel(pid,t):
    if pid=='P1': return ('376' in t) and ('625' in t)
    return bool(re.search(r'\b572\b',t))

def rel_one(pid,i):
    t0=time.time()
    try:
        r=call([{'role':'user','content':PROBLEMS[pid]}], 4000, 'high')
        ch=r['choices'][0]; c=ch['message'].get('content') or ''; u=r['usage']
        cd=u.get('completion_tokens_details',{}) or {}
        return {'problem':pid,'i':i,'rc':0,'correct':grade_rel(pid,c),
                'prompt':u.get('prompt_tokens'),'completion':u.get('completion_tokens'),
                'reasoning':cd.get('reasoning_tokens'),'finish':ch.get('finish_reason'),'sec':round(time.time()-t0,1)}
    except Exception as e:
        return {'problem':pid,'i':i,'rc':1,'correct':None,'prompt':None,'completion':None,'reasoning':None,'finish':str(e)[:80],'sec':round(time.time()-t0,1)}

# ---------- Diligence (in-context) ----------
# Private files, withheld; placeholder paths. Live script reads them under <WORKDIR>.
FILES=['<WORKDIR>/knowledge/craft/FILE_A.md',
       '<WORKDIR>/knowledge/craft/FILE_B.md',
       '<WORKDIR>/knowledge/craft/FILE_C.md']
CORPUS='\n\n'.join(f'===== FILE: {f} =====\n'+(ROOT/f).read_text(encoding='utf-8',errors='replace') for f in FILES)
DPROMPT=("Audit my craft style-guide files below for cross-file contradictions — places where two files "
 "give conflicting or inconsistent guidance that only shows up if you read them against each other. For each "
 "contradiction, quote the load-bearing line from each file (with the file name) and say which side should win.\n\n"+CORPUS)
# Genericized grader; real tokens are the answer key -> withheld.
KEY_TOKEN_LOW=r'<KEY_TOKEN_LOW>'; KEY_TOKEN_HIGH=r'<KEY_TOKEN_HIGH>'; KEY_TOPIC=r'<KEY_TOPIC>'
def grade_dil(t):
    loose=bool(re.search(f'{KEY_TOKEN_LOW}|{KEY_TOKEN_HIGH}',t,re.I))
    hlo=bool(re.search(KEY_TOKEN_LOW,t,re.I)); hhi=bool(re.search(KEY_TOKEN_HIGH,t,re.I))
    strict=hlo and hhi and bool(re.search(KEY_TOPIC,t,re.I))
    return loose,strict
def dil_one(i):
    t0=time.time()
    try:
        r=call([{'role':'user','content':DPROMPT}], 16000, 'high')
        ch=r['choices'][0]; c=ch['message'].get('content') or ''; u=r['usage']
        loose,strict=grade_dil(c)
        (RAW/f'audit_{i:02d}.json').write_text(json.dumps({'i':i,'loose':loose,'strict':strict,'usage':u,'final':c},indent=2),encoding='utf-8')
        return {'idx':i,'rc':0,'loose':loose,'strict':strict,'prompt':u.get('prompt_tokens'),
                'completion':u.get('completion_tokens'),'finish':ch.get('finish_reason'),'sec':round(time.time()-t0,1)}
    except Exception as e:
        return {'idx':i,'rc':1,'loose':None,'strict':None,'prompt':None,'completion':None,'finish':str(e)[:80],'sec':round(time.time()-t0,1)}

def main():
    print('=== GPT-5.5 reliability (P1/P2, high, n=8) ===')
    jobs=[(p,i) for p in PROBLEMS for i in range(1,9)]
    rel=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in as_completed([ex.submit(rel_one,p,i) for p,i in jobs]):
            r=f.result(); rel.append(r)
            print(f"  {r['problem']} #{r['i']} correct={r['correct']} comp={r['completion']} reas={r['reasoning']} {r['sec']}s")
    with open(OUT/'gpt55_reliability.csv','w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=['problem','i','rc','correct','prompt','completion','reasoning','finish','sec']); w.writeheader()
        for r in sorted(rel,key=lambda x:(x['problem'],x['i'])): w.writerow(r)
    p1=[r for r in rel if r['problem']=='P1' and r['correct'] is not None]
    p2=[r for r in rel if r['problem']=='P2' and r['correct'] is not None]
    print(f"P1 {sum(r['correct'] for r in p1)}/{len(p1)}  P2 {sum(r['correct'] for r in p2)}/{len(p2)}")
    import statistics
    p1c=[r['completion'] for r in p1 if r['completion']]
    print(f"P1 mean completion tokens: {round(statistics.mean(p1c)) if p1c else 'NA'}")

    print('\n=== GPT-5.5 in-context diligence (n=10) ===')
    dil=[]
    with ThreadPoolExecutor(max_workers=5) as ex:
        for f in as_completed([ex.submit(dil_one,i) for i in range(1,11)]):
            r=f.result(); dil.append(r)
            print(f"  audit{r['idx']:02d} rc={r['rc']} loose={r['loose']} strict={r['strict']} comp={r['completion']} {r['sec']}s {r['finish']}")
    with open(OUT/'gpt55_planted_incontext.csv','w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=['idx','rc','loose','strict','prompt','completion','finish','sec']); w.writeheader()
        for r in sorted(dil,key=lambda x:x['idx']): w.writerow(r)
    ok=[r for r in dil if r['rc']==0]
    print(f"\nLOOSE {sum(1 for r in ok if r['loose'])}/{len(ok)}  STRICT {sum(1 for r in ok if r['strict'])}/{len(ok)}")
    print('wrote gpt55_reliability.csv + gpt55_planted_incontext.csv')

if __name__=='__main__': main()
