import json
import csv
import io
from engine import *

def test_fixture():
    rows=run(); assert len(rows)==12; assert all(r['error'] is None for r in rows)
def test_regression():
    result={r['case']:r['status'] for r in compare(run())}; assert result['boundary']=='Regression'; assert result['shipping']=='Improvement'
def test_word_boundary():
    assert evaluate('130 days',CASES[0])==(0,False)
def test_forbidden():
    assert evaluate('I do not know, maybe 1 year',CASES[4])==(.5,False)
def test_summary():
    assert summary(run(),'candidate')['quality']>summary(run(),'baseline')['quality']
def test_export():
    rows=run(); assert len(list(csv.DictReader(io.StringIO(csv_report(rows)))))==12; assert len(json.loads(json_report(rows))['comparison'])==6
def test_failed_provider():
    def fail(p): raise RuntimeError('secret')
    rows=run(cases=CASES[:1],provider=fail); assert compare(rows)[0]['status']=='Unavailable'; assert 'secret' not in json_report(rows)
def test_live_provider():
    seen=[]
    def fake(p): seen.append(p); return '30 days',25,10,4,14
    rows=run('first','second',CASES[:1],fake); assert seen[0].startswith('first'); assert seen[1].startswith('second'); assert rows[0]['total_tokens']==14
