#!/usr/bin/env python3
"""Complete the in-context diligence matrix: Opus 4.8 + Fable 5 (Anthropic API) and
GLM-5.2 (OpenRouter), n=10 each, SAME 3-file corpus + prompt as fugu/GPT-5.5, all at
effort=high. Makes the diligence panel apples-to-apples (one harness: in-context, single-shot).

WITHHELD (honesty bar): the three style-guide files are private and not published;
the planted-contradiction answer key is withheld -> grader tokens are placeholders.
The generic audit instruction is published in prompt.txt.

NOTE on Fable 5: the Anthropic endpoint for claude-fable-5 was export-restricted at
run time (HTTP 404 on every call from this setup), so Fable's in-context column could
NOT be re-run here. Fable's diligence number in the set README is its earlier RECORDED
agentic figure, on a different (claude -p) harness — flagged as not directly comparable.
"""
import json, sys, time, csv, re, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[2]
def env(k):
    for l in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        if l.startswith(k+'='): return l.split('=',1)[1].strip()
ANTH=env('ANTHROPIC_API_KEY'); ORK=env('OPENROUTER_API_KEY')
OUT=Path(__file__).resolve().parents[1]
RAW=ROOT/'Temp'/'data'/'matrix_raw'; RAW.mkdir(parents=True,exist_ok=True)

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
def grade(t):
    loose=bool(re.search(f'{KEY_TOKEN_LOW}|{KEY_TOKEN_HIGH}',t,re.I))
    hlo=bool(re.search(KEY_TOKEN_LOW,t,re.I)); hhi=bool(re.search(KEY_TOKEN_HIGH,t,re.I))
    strict=hlo and hhi and bool(re.search(KEY_TOPIC,t,re.I))
    return loose,strict

def post(url, body, headers, timeout=600):
    req=urllib.request.Request(url,data=json.dumps(body).encode(),method='POST')
    for k,v in headers.items(): req.add_header(k,v)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            b=e.read().decode(errors='replace')
            if attempt<2 and e.code in (429,500,502,503,504,529): time.sleep(8); continue
            raise RuntimeError(f'HTTP {e.code}: {b[:200]}')
        except Exception:
            if attempt<2: time.sleep(8); continue
            raise

def run_anthropic(model, i):
    body={'model':model,'max_tokens':20000,'thinking':{'type':'adaptive'},
          'output_config':{'effort':'high'},'messages':[{'role':'user','content':DPROMPT}]}
    h={'x-api-key':ANTH,'anthropic-version':'2023-06-01','content-type':'application/json'}
    t0=time.time()
    try:
        r=post('https://api.anthropic.com/v1/messages',body,h)
        txt=''.join(b.get('text','') for b in r.get('content',[]) if b.get('type')=='text')
        u=r.get('usage',{}); loose,strict=grade(txt)
        (RAW/f'{model}_{i:02d}.json').write_text(json.dumps({'i':i,'loose':loose,'strict':strict,'usage':u,'final':txt},indent=2),encoding='utf-8')
        return {'model':model,'idx':i,'rc':0,'loose':loose,'strict':strict,
                'in':u.get('input_tokens'),'out':u.get('output_tokens'),'stop':r.get('stop_reason'),'sec':round(time.time()-t0,1)}
    except Exception as e:
        return {'model':model,'idx':i,'rc':1,'loose':None,'strict':None,'in':None,'out':None,'stop':str(e)[:80],'sec':round(time.time()-t0,1)}

def run_openrouter(model, i):
    body={'model':model,'max_tokens':20000,'reasoning':{'enabled':True},
          'messages':[{'role':'user','content':DPROMPT}]}
    h={'Authorization':'Bearer '+ORK,'content-type':'application/json'}
    t0=time.time()
    try:
        r=post('https://openrouter.ai/api/v1/chat/completions',body,h)
        ch=r['choices'][0]; txt=ch['message'].get('content') or ''; u=r.get('usage',{})
        loose,strict=grade(txt)
        (RAW/f'glm_{i:02d}.json').write_text(json.dumps({'i':i,'loose':loose,'strict':strict,'usage':u,'final':txt},indent=2),encoding='utf-8')
        return {'model':model,'idx':i,'rc':0,'loose':loose,'strict':strict,
                'in':u.get('prompt_tokens'),'out':u.get('completion_tokens'),'stop':ch.get('finish_reason'),'sec':round(time.time()-t0,1)}
    except Exception as e:
        return {'model':model,'idx':i,'rc':1,'loose':None,'strict':None,'in':None,'out':None,'stop':str(e)[:80],'sec':round(time.time()-t0,1)}

# Fable 5 left in the job list to document the export-restriction (it 404s; see CSV note).
JOBS=[('anthropic','claude-opus-4-8','opus'),('anthropic','claude-fable-5','fable'),('openrouter','z-ai/glm-5.2','glm')]
def main():
    for kind,model,slug in JOBS:
        print(f'\n=== {slug} ({model}) in-context n=10, effort=high ===')
        fn = run_anthropic if kind=='anthropic' else run_openrouter
        rows=[]
        with ThreadPoolExecutor(max_workers=4) as ex:
            for f in as_completed([ex.submit(fn,model,i) for i in range(1,11)]):
                r=f.result(); rows.append(r)
                print(f"  {slug}{r['idx']:02d} rc={r['rc']} loose={r['loose']} strict={r['strict']} in={r['in']} out={r['out']} {r['sec']}s {r['stop']}")
        with open(OUT/f'{slug}_planted_incontext.csv','w',newline='',encoding='utf-8') as fh:
            w=csv.DictWriter(fh,fieldnames=['model','idx','rc','loose','strict','in','out','stop','sec']); w.writeheader()
            for r in sorted(rows,key=lambda x:x['idx']): w.writerow(r)
        ok=[r for r in rows if r['rc']==0]
        L=sum(1 for r in ok if r['loose']); S=sum(1 for r in ok if r['strict'])
        print(f"  -> {slug}: LOOSE {L}/{len(ok)}  STRICT {S}/{len(ok)}")
    print('\nDONE matrix')

if __name__=='__main__': main()
