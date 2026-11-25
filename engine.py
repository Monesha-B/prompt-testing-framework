import csv
import io
import json
import re
import time
import urllib.request
from dataclasses import dataclass, asdict
from statistics import mean

@dataclass(frozen=True)
class Case:
    id: str
    question: str
    required: tuple
    forbidden: tuple = ()

CONTEXT = 'Fictional Northstar store policy: returns within 30 days; shipping is free on orders of $50 or more; support is available Monday through Friday; refunds take 5 business days. If information is missing, say you do not know.'
BASELINE = 'Answer the customer question using the policy.'
CANDIDATE = 'Answer concisely using only the policy. Include exact numbers and conditions. If unknown, say you do not know.'
CASES = [Case('returns','What is the return window?',('30 days',)), Case('shipping','When is shipping free?',('$50', 'free')), Case('support','When is support available?',('monday','friday')), Case('refund','How long do refunds take?',('5 business days',)), Case('unknown','What is the warranty period?',('do not know',),('1 year',)), Case('boundary','Is a $50 order eligible for free shipping?',('yes','free'))]
FIXTURES = {'baseline':['30 days','Shipping is free.','Monday through Friday','5 business days','1 year','Yes, free shipping.'], 'candidate':['30 days','Shipping is free on orders of $50 or more.','Monday through Friday','5 business days','I do not know.','No, only orders above $50.']}

def evaluate(answer, case):
    normalized = ' '.join(answer.casefold().split())
    checks = [bool(re.search(r'(?<!\w)'+re.escape(x.casefold())+r'(?!\w)', normalized)) for x in case.required]
    checks += [not bool(re.search(r'(?<!\w)'+re.escape(x.casefold())+r'(?!\w)', normalized)) for x in case.forbidden]
    return sum(checks)/len(checks), all(checks)

def gemini(prompt, key, model):
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', model):
        raise ValueError('Invalid model')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    body = {'contents':[{'parts':[{'text':prompt}]}], 'generationConfig':{'temperature':0,'maxOutputTokens':512}}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type':'application/json','x-goog-api-key':key})
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.load(response)
    elapsed = (time.perf_counter()-start)*1000
    answer = ''.join(p.get('text','') for p in data['candidates'][0]['content']['parts'] if not p.get('thought'))
    if not answer.strip(): raise ValueError('Empty response')
    usage = data.get('usageMetadata',{})
    return answer, elapsed, usage.get('promptTokenCount'), usage.get('candidatesTokenCount'), usage.get('totalTokenCount')

def run(baseline=BASELINE, candidate=CANDIDATE, cases=CASES, provider=None):
    rows=[]
    for case in cases:
        for version, instruction in [('baseline',baseline),('candidate',candidate)]:
            prompt=f'{instruction}\nPolicy: {CONTEXT}\nQuestion: {case.question}'
            row={'case':case.id,'question':case.question,'version':version,'mode':'live' if provider else 'fictional','answer':'','score':None,'passed':None,'latency_ms':None,'input_tokens':None,'output_tokens':None,'total_tokens':None,'error':None}
            try:
                if provider:
                    answer, latency, it, ot, total = provider(prompt)
                else:
                    i=CASES.index(case); answer=FIXTURES[version][i]; latency=120+i*15+(25 if version=='candidate' else 0); it=len(prompt.split()); ot=len(answer.split()); total=it+ot
                score, passed=evaluate(answer,case)
                row.update(answer=answer,score=score,passed=passed,latency_ms=round(latency,2),input_tokens=it,output_tokens=ot,total_tokens=total)
            except Exception:
                row['error']='Generation failed; check model, quota or connection.'
            rows.append(row)
    return rows

def compare(rows):
    pairs={}
    for row in rows: pairs.setdefault(row['case'],{})[row['version']]=row
    result=[]
    for case,p in pairs.items():
        a,b=p['baseline'],p['candidate']
        delta=None if a['score'] is None or b['score'] is None else b['score']-a['score']
        result.append({'case':case,'baseline_score':a['score'],'candidate_score':b['score'],'delta':delta,'status':'Unavailable' if delta is None else 'Regression' if delta<0 else 'Improvement' if delta>0 else 'Unchanged'})
    return result

def summary(rows,version):
    selected=[r for r in rows if r['version']==version]; valid=[r for r in selected if r['score'] is not None]
    def avg(k):
        values=[r[k] for r in valid if r[k] is not None]; return mean(values) if values else None
    return {'quality':avg('score'),'pass_rate':avg('passed'),'latency_ms':avg('latency_ms'),'total_tokens':avg('total_tokens'),'errors':len(selected)-len(valid)}

def csv_report(rows):
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=list(rows[0]) if rows else ['case']); writer.writeheader()
    # Protect spreadsheet consumers from formula injection.
    for row in rows:
        writer.writerow({k: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()})
    return out.getvalue()

def json_report(rows):
    return json.dumps({'results':rows,'comparison':compare(rows),'summary':{v:summary(rows,v) for v in ('baseline','candidate')}},indent=2)
