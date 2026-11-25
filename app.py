import os
import streamlit as st
import pandas as pd
from engine import BASELINE,CANDIDATE,CASES,CONTEXT,run,gemini,compare,summary,csv_report,json_report
st.set_page_config(page_title='Prompt Testing Framework',page_icon='🧪',layout='wide')
st.title('Prompt Testing Framework')
st.caption('AI reliability lab / Prompt evaluation and regression testing')
with st.sidebar:
    st.header('Configuration')
    mode=st.radio('Execution mode',['Offline fictional demo','Live Gemini'])
    model=st.text_input('Gemini model','gemini-2.5-flash',disabled=mode.startswith('Offline'))
    key=os.getenv('GEMINI_API_KEY','')
    if not key:
        try: key=st.secrets.get('GEMINI_API_KEY','')
        except Exception: pass
    if mode=='Live Gemini':
        st.caption('Live mode uses the configured server-side key. Requests consume API quota.')
        st.caption('API configuration: '+('Available' if key else 'Not configured'))
    selected=st.multiselect('Test cases',[c.id for c in CASES],default=[c.id for c in CASES] if mode.startswith('Offline') else [CASES[0].id,CASES[1].id])
    st.caption(f'{2*len(selected)} generations per run')
offline=mode.startswith('Offline')
if offline: st.info('Fictional fixture responses, simulated latency and approximate word-based token counts. Editing prompts does not change fixture responses. Use live mode for actual prompt experiments.')
else: st.warning('Live requests use Gemini and may be rate limited. Only fictional policy questions are sent with your prompt instructions. Do not enter sensitive information.')
with st.expander('Fictional policy and evaluation cases'):
    st.write(CONTEXT)
    st.dataframe([{'Case':c.id,'Question':c.question,'Required phrases':', '.join(c.required),'Forbidden phrases':', '.join(c.forbidden)} for c in CASES],hide_index=True,width="stretch")
a,b=st.columns(2)
with a: baseline=st.text_area('Baseline prompt',BASELINE,height=140,disabled=offline)
with b: candidate=st.text_area('Candidate prompt',CANDIDATE,height=140,disabled=offline)
if st.button('Run comparison',type='primary',disabled=not selected or not baseline.strip() or not candidate.strip() or (not offline and not key)):
    with st.spinner('Running test cases…'):
        rows=run(baseline,candidate,[c for c in CASES if c.id in selected],None if offline else lambda p:gemini(p,key,model))
        st.session_state['results']=rows
        st.session_state['run_mode']=mode
if 'results' in st.session_state:
    rows=st.session_state['results']; comparison=compare(rows)
    st.subheader('Evaluation overview')
    st.caption('Last run: '+st.session_state['run_mode']+' · Quality is required/forbidden phrase compliance, not semantic judgment.')
    s={v:summary(rows,v) for v in ('baseline','candidate')}
    cols=st.columns(4)
    def fmt(x,percent=False): return 'N/A' if x is None else f'{x:.0%}' if percent else f'{x:.1f}'
    for col,(label,k,percent) in zip(cols,[('Quality','quality',True),('Pass rate','pass_rate',True),('Mean latency (ms)','latency_ms',False),('Mean total tokens','total_tokens',False)]):
        with col:
            st.metric(label,fmt(s['candidate'][k],percent),help='Candidate result'); st.caption('Baseline: '+fmt(s['baseline'][k],percent))
    if any(r['error'] for r in rows): st.warning('Some generations failed. Failed calls are excluded from averages and marked unavailable in comparisons.')
    st.subheader('Regression analysis')
    st.write(f"{sum(r['status']=='Regression' for r in comparison)} regressions · {sum(r['status']=='Improvement' for r in comparison)} improvements")
    frame=pd.DataFrame(comparison); st.dataframe(frame,hide_index=True,width="stretch")
    st.bar_chart(frame.set_index('case')[['baseline_score','candidate_score']])
    st.subheader('Individual test results')
    st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
    a,b=st.columns(2)
    a.download_button('Download CSV',csv_report(rows),'prompt-results.csv','text/csv')
    b.download_button('Download JSON',json_report(rows),'prompt-results.json','application/json')
else: st.write('Choose your test cases and run a comparison to view results.')
