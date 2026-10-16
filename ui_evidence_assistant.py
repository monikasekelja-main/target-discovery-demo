"""Separate chat state, explicit paid submission, background cancellation and exports."""
import hashlib
import io
import json
import os
from pathlib import Path
import uuid
import zipfile
import streamlit as st
from evidence_context import context
from evidence_assistant import Job
from ui_service import PACKAGE

PROMPTS=[
    'Why this recommendation, and what evidence could change it?',
    'Plot the functional results and explain the cell-loss limitation.',
    'Find recent methods for distinguishing selective cell depletion from reduced cytokine production.',
    'What evidence would an antibody team need next?']


def conversation_key(ctx):
    return hashlib.sha256(json.dumps(ctx['binding'],sort_keys=True).encode()).hexdigest()


def cancel_on_navigation(view,run_id,assessment_id,workspace):
    active=st.session_state.get('evidence_active')
    if active:
        b=active['job'].ctx['binding']
        if (view!='Ask the evidence assistant' or b['run_id']!=run_id or b['assessment_id']!=assessment_id
                or b['workspace']!=str(Path(workspace).resolve())):
            active['job'].cancel.set()


def archive(active,result):
    # Chat state lives outside every scientific workspace and never opens its DB writable.
    root=PACKAGE/'.assistant-state'/active['context_key'];root.mkdir(parents=True,exist_ok=True)
    record={'question':active['job'].question,'binding':active['job'].ctx['binding'],
            'status':result['status'],'answer':result['answer'],'sources':result['sources'],
            'activity':result['activity'],'calls':result['calls'],'error':result['error'],
            'figures':[f['provenance'] for f in result['figures']]}
    path=root/(active['id']+'.json')
    if not path.exists():
        for index,figure in enumerate(result['figures']):
            (root/(active['id']+f'-{index}.zip')).write_bytes(figure['bundle'])
        temporary=path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record,indent=2));temporary.replace(path)
    return record


def display_record(record,key):
    with st.chat_message('user'):st.write(record['question'])
    with st.chat_message('assistant'):
        answer=record.get('answer')
        if answer:
            st.markdown('**What the saved assessment establishes**');st.write(answer['saved_assessment'])
            st.markdown('**External evidence and methodological context**')
            st.caption('External candidate evidence — not incorporated into assessment '+record['binding']['assessment_id']+'.')
            st.write(answer['external_context'])
            st.markdown('**Remaining uncertainty and proposed next steps**')
            st.caption('Experimental suggestions are proposals for specialist discussion, not validated protocols. Specialists determine feasibility, controls and priorities; citations establish only the claims identified below.')
            st.write(answer['uncertainty_and_next_steps'])
            with st.expander('Sources and supporting excerpts'):
                for c in answer['citations']:
                    source=record['sources'][c['source_id']]
                    st.markdown('**'+str(source.get('title') or c['source_id'])+'**')
                    st.write('Access: '+source['access']);st.write('Supports: '+c['claim']);st.text(c['excerpt'])
                    if source.get('provider'):st.caption('Retrieved via '+source['provider'])
                    st.write('Limitations: '+c['applicability_limits'])
                    if source.get('url'):st.link_button('Open source',source['url'])
                    if source.get('authors'):st.write('Authors: '+', '.join(source['authors']))
                    if source.get('query'):st.caption('Query: '+source['query']+' · Retrieved: '+source['retrieved_at'])
                    if source.get('year'):st.caption('Publication date: '+str(source['year']))
                    if source.get('study_type'):st.caption('Provider study type: '+', '.join(source['study_type']))
                    if source.get('applicability_limits'):st.caption(source['applicability_limits'])
        elif record['status']=='cancelled':st.info('Cancelled. No answer accepted; an already-started API request may still incur cost.')
        else:st.error(record.get('error') or 'No accepted answer.')
        root=PACKAGE/'.assistant-state'/key
        for index,figure in enumerate(record.get('figures',[])):
            archive_path=root/(record['_id']+f'-{index}.zip')
            if not archive_path.is_file():continue
            bundle=archive_path.read_bytes()
            with zipfile.ZipFile(io.BytesIO(bundle)) as z:
                st.image(z.read('figure.png'));st.caption(figure['caption'])
            st.download_button('Download PNG + SVG + PDF, caption and provenance',bundle,
                file_name=figure['binding']['assessment_id']+'-figure.zip',mime='application/zip',key=record['_id']+f'-figure-{index}')
        with st.expander('Tool activity and assessment binding'):
            for item in record['activity']:
                st.write(item['tool']+' · '+item['status'])
                if item.get('error'):st.warning(item['error'])
                if item.get('query'):st.caption(item['query'])
                if item.get('notice'):st.caption(item['notice'])
                if item.get('reason'):st.write(item.get('source_id','')+': '+item['reason'])
                for search in item.get('search_trace',[]):
                    st.write(search['provider']+' query: '+search['query'])
                    st.caption('Publication-date filter: '+str(search['date_filter'] or 'unrestricted')+' · Returned: '+str(search['returned']))
            st.caption('Assessment SHA-256: '+record['binding']['assessment_sha256'])
            st.caption('Model requests: '+str(len(record['calls'])))
        st.download_button('Download answer and source record',json.dumps({k:v for k,v in record.items() if k!='_id'},indent=2),
            file_name='evidence-answer.json',mime='application/json',key=record['_id']+'-answer')


@st.fragment(run_every='1s')
def running_panel():
    active=st.session_state.get('evidence_active')
    if not active:return
    result=active['job'].snapshot()
    if result['status'] in ('completed','failed','cancelled'):
        archive(active,result);st.session_state.pop('evidence_active',None);st.rerun();return
    st.info('Evidence assistant is working. '+str(sum(x['status']=='completed' for x in result['activity']))+' tool calls completed (maximum six).')
    if active['job'].cancel.is_set():st.caption('Cancellation requested. Waiting for the current request to return; no further calls will start.')
    if st.button('Cancel question',key='cancel_evidence_question'):active['job'].cancel.set()
    with st.expander('Live tool activity',expanded=True):
        for a in result['activity']:st.write(a['tool']+' · '+a['status'])


def assistant_view(workspace,run,brief):
    st.subheader('Ask the evidence assistant')
    if not brief:st.info('Select a complete assessment first.');return
    ctx=context(workspace,run['state']['run_id'],brief['assessment_id']);key=conversation_key(ctx)
    st.info('Target: '+brief['target_id']+' (fictional) · Run: '+run['state']['run_id']+' · Assessment: '+brief['assessment_id'])
    st.sidebar.caption('Evidence assistant context: '+brief['target_id']+' (fictional) · '+run['state']['run_id']+' · '+brief['assessment_id'])
    st.caption('Read-only advice. Chat, external sources and figures do not change evidence, assessments, approvals or handoffs.')
    if not ctx['current']:st.warning('Historical or stale assessment: answers describe this exact saved version, not current authorization.')
    st.caption('Publication search: PubMed, with labelled Crossref fallback. Abstracts only. Official web context requires BRAVE_SEARCH_API_KEY.')
    st.markdown('[NCBI disclaimer and copyright](https://www.ncbi.nlm.nih.gov/About/disclaimer.html) · [Crossref metadata terms](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)')
    root=PACKAGE/'.assistant-state'/key
    records=[]
    if root.exists():
        for p in sorted(root.glob('*.json'),key=lambda p:p.stat().st_mtime):
            record=json.loads(p.read_text());record['_id']=p.stem;records.append(record);display_record(record,key)
    active=st.session_state.get('evidence_active')
    if active:
        if active['context_key']!=key:active['job'].cancel.set()
        running_panel();return
    choice=st.selectbox('Suggested question',['Write my own question']+PROMPTS,key='assistant_suggestion_'+key)
    with st.form('assistant_question_'+key):
        question=st.text_area('Your question',value='' if choice=='Write my own question' else choice,max_chars=4000,key='assistant_question_text_'+key+'_'+str(PROMPTS.index(choice) if choice in PROMPTS else -1))
        model=st.text_input('Evidence assistant model',value=os.environ.get('TARGET_REVIEW_MODEL','gpt-6-astra'))
        st.caption('Submitting may make up to seven paid model requests and six bounded tool calls. Sends the selected scientific context and recent chat to OpenAI; search queries go to the retrieval provider. No automatic retries.')
        submitted=st.form_submit_button('Ask evidence assistant',disabled=not bool(os.environ.get('OPENAI_API_KEY')))
    if not os.environ.get('OPENAI_API_KEY'):st.warning('OPENAI_API_KEY is missing from this server environment.')
    if submitted:
        if not question.strip():st.error('Enter a question.');return
        prior=[{'question':r['question'],'answer':r['answer']} for r in records if r.get('answer')][-3:]
        job=Job(ctx,question,model,prior)
        st.session_state['evidence_active']={'id':uuid.uuid4().hex,'context_key':key,'job':job}
        job.start();st.rerun()
