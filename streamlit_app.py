"""Scientific workbench with explicit local review and handoff. Launch: python -m streamlit run streamlit_app.py"""
import json
import os
from pathlib import Path
import sqlite3
import streamlit as st
from ui_service import (PACKAGE,list_runs,load_run,review_status,list_reports,get_report,
                        ACTIONS,FINDINGS,recorded_policy)
from ui_charts import functional_chart,prediction_chart
from ui_programme_context import programme_context
from ui_reviews import review_controls,handoff_controls,human_review_summary,handoff_summary
from ui_followups import followup_controls
from ui_evidence_assistant import assistant_view,cancel_on_navigation

st.set_page_config(page_title='Target Hypothesis Workbench',page_icon='🧬',layout='wide')

# Presentation only: retain Streamlit's accessible controls and responsive columns.
st.html('''<style>
[data-testid="stMainBlockContainer"] {padding: 3.5rem 2rem 2rem;}
[data-testid="stMain"] [data-testid="stVerticalBlock"] {gap: .65rem;}
[data-testid="stMain"] h1 {font-size: 1.65rem; padding: 0 0 .25rem;}
[data-testid="stMain"] h3 {font-size: 1.2rem; padding: 0 0 .25rem;}
[data-testid="stMain"] hr {margin: .25rem 0;}
</style>''')


def text_list(items):
    for item in items:st.markdown('- '+str(item))


def decision(run,brief):
    if brief is None:
        st.info('No complete assessment yet. The saved workflow is waiting for its next step.')
        st.write('Current phase: '+run['state']['phase'])
        if run['state'].get('block_reason'):st.json(run['state']['block_reason'])
        return
    left,right=st.columns([1.7,1],gap='large')
    with left:
        programme_context(brief)
        st.caption('ASSAY QUESTION · '+brief['hypothesis'])
        st.markdown('**Current evidence: '+FINDINGS[brief['scientific_recommendation']]+'**')
        if brief['functional_effects']:
            if brief['prerequisites_passed']:
                st.success('Recorded assay prerequisites passed. This is not a systemic-safety finding.')
            else:
                st.error('Diagnostic estimates only — assay or cell-preservation prerequisites failed.')
            threshold=recorded_policy(run,brief)['minimum_useful_reduction_pct']
            st.plotly_chart(functional_chart(brief,threshold),width='stretch',config={'displayModeBar':False},key='functional')
            st.caption('Two methods in the same eight paired donors; not independent cohort replication. Intervals are 95% confidence intervals from the saved calculator.')
            st.write(brief['rationale'])
            if brief['failed_gates']:
                with st.expander(f"Inspect {len(brief['failed_gates'])} failed prerequisite checks"):
                    text_list(brief['failed_gates'])
            with st.expander('Exact saved estimates'):
                st.dataframe([{'Method':k,**v} for k,v in brief['functional_effects'].items()],hide_index=True,width='stretch')
        else:
            st.info('Functional effect not yet measured. Prediction is not experimental benefit.')
            st.write(brief['rationale'])
        previous=[b for b in run['assessments'] if b['assessment_id']<brief['assessment_id']]
        if previous:
            with st.expander('What changed from the previous assessment?'):
                old=previous[-1]
                st.write('Previous: '+ACTIONS[old['scientific_recommendation']])
                st.write('Now: '+ACTIONS[brief['scientific_recommendation']])
                st.write('Gene assignment, genetic direction, therapeutic modality equivalence and systemic safety remain unresolved.')
    with right:
        with st.container(border=True):
            st.caption('NEXT SCIENTIFIC ACTION · FIXED REFERENCE BRIEF')
            st.subheader(ACTIONS[brief['scientific_recommendation']])
            st.write(brief['next_action'])
            st.caption('Decision owner: '+brief['next_owner_role'])
            label,effective,review=review_status(run,brief)
            st.markdown('**Human review:** '+label)
            if review:
                st.caption('Review mode: '+review['actor_mode'])
                st.write(review['rationale'])
            st.caption('Read-only view. No review, import or handoff action is performed here.')
        st.markdown('**What remains uncertain**')
        text_list(brief['remaining_uncertainties'])
        with st.expander('Separate support dimensions'):
            for axis in ['causal','intervention']:
                support=brief['confidence'][axis]
                st.write(f"{axis.title()}: {support['ordinal']}/3 — ordinal support, not a probability")
                st.caption(support['rationale'])
            st.write('Modality feasibility');st.json(brief['confidence']['modality_feasibility'])
            st.write('Systemic safety: '+brief['confidence']['systemic_safety'])
    with st.expander('Canonical decision brief and version provenance'):
        st.json(brief)


def evidence(run):
    state=run['state'];records=state.get('evidence',{}).get('records',[])
    left,right=st.columns([1.4,1],gap='large')
    with left:
        st.subheader('Evidence ledger')
        st.caption('Source records are not independent studies. Original claims remain visible, including deliberately unsupported claims.')
        if not records:st.info('No evidence packet captured yet.')
        else:
            st.dataframe([{'ID':r['evidence_id'],'Family':r['evidence_family_id'],'Claim':r['claim'],
                           'Target mapping':r['entity_status']} for r in records],hide_index=True,width='stretch')
            eid=st.selectbox('Inspect a source',[r['evidence_id'] for r in records],key='evidence_id')
            record=next(r for r in records if r['evidence_id']==eid)
            with st.container(border=True):
                st.markdown('**Original claim — not automatically endorsed**')
                st.write(record['claim'])
                st.caption('Evidence family: '+record['evidence_family_id']+' · Mapping: '+record['entity_status'])
                st.json(record['source'])
                with st.expander('Complete original record and normalized fields'):st.json(record)
    with right:
        st.subheader('Metadata & model applicability')
        manifest=state.get('manifest')
        if manifest:
            st.success('Application cell context resolved in the saved run')
            context=manifest['context']
            st.write(' · '.join(str(context[k]) for k in ('species','cell_type','cell_state')))
            st.caption('Owner: '+manifest['owner_role'])
            st.caption('This manifest does not repair E16 or historical resting-cell evidence.')
            with st.expander('Manifest and dependency trace'):
                st.json(manifest)
                st.json([e for e in run['events'] if e['kind'] in ('DEPENDENCY_BLOCKED','METADATA_RESOLVED','CAPABILITY_SELECTION')])
        else:st.warning('Application metadata unresolved. No applicable prediction should be inferred.')
        prediction=state.get('prediction')
        if prediction:
            st.markdown('**Frozen synthetic signature response**')
            st.plotly_chart(prediction_chart(prediction),width='stretch',config={'displayModeBar':False},key='prediction')
            st.caption('These are signature units, not functional-effect percentages. No predictive model was trained or run.')
            st.caption(prediction['model_id']+' · '+prediction['model_version'])
            with st.expander('Prediction scope and limitations'):st.json(prediction)
        else:st.info('No successful prediction was captured.')


def challenge(workspace,run,brief):
    st.subheader('Saved analyst & challenger review')
    st.caption('Advisory interpretation is separate from the canonical decision and its human approval.')
    records=list_reports(workspace,run['state']['run_id'])
    matching=[r for r in records if brief and r['assessment_id']==brief['assessment_id']]
    if not matching:
        st.info('No saved agent report for this assessment. Nothing is generated automatically.')
        return
    attempt=st.selectbox('Saved attempt',[r['attempt_id'] for r in matching],key='attempt_id',
        format_func=lambda v:next(v+' · '+r['mode'] for r in matching if r['attempt_id']==v))
    report=get_report(workspace,run['state']['run_id'],attempt)
    mode={'live_llm':'Captured live LLM output — no call is running',
          'scripted_offline_test':'Scripted offline test — not model reasoning'}.get(report.get('mode'),report.get('mode','Unknown'))
    st.info(mode)
    status=report.get('effective_status',report['status'])
    if status=='STALE':st.warning('Historical / stale report: its binding no longer matches the current assessment, inputs or agent code.')
    elif status=='ADVISORY_READY_FOR_REVIEW':
        review_label,_,saved_review=review_status(run,brief)
        if saved_review:
            st.info('Saved advisory report · Human review: '+review_label+'. See the human decision above.')
        else:st.info('Advisory report available · Awaiting human decision')
    else:st.warning('Report status: '+status)
    if report.get('error'):st.error(report['error'])
    left,right=st.columns([1,1],gap='large')
    with left:
        st.markdown('### Analyst interpretation')
        analyst=report.get('analyst')
        if analyst:
            st.markdown('**Hypothesis under test**')
            st.write(analyst.get('hypothesis_under_test',analyst.get('hypothesis','')))
            finding=analyst.get('current_evidence')
            if finding:
                st.markdown('**Evidence assessment in this saved report**')
                st.write(finding['status'].replace('_',' ').capitalize());st.write(finding['summary'])
                st.caption('Scientific evidence finding; the saved human decision is shown above.')
                for citation in finding.get('citations',[]):
                    st.caption('Evidence source: '+citation['source_id'])
                    st.text(citation['quote'])
            else:st.warning('Legacy report: opening is a hypothesis, not an established finding. No separate evidence-assessment field was captured.')
            st.markdown('**Proposed next step**');st.write(analyst['next_step'])
            for claim in analyst['claims']:
                with st.expander(claim['claim_id']+' · '+claim['kind']):
                    st.write(claim['statement'])
                    for citation in claim['citations']:
                        st.caption(citation['source_id']);st.code(citation['quote'],language=None,wrap_lines=True)
            with st.expander('Remaining uncertainties'):text_list(analyst['uncertainties'])
        else:st.info('No validated analyst proposal saved.')
    with right:
        st.markdown('### Challenger findings')
        critic=report.get('challenger')
        if critic:
            st.write(critic['rationale'])
            if critic.get('checks'):
                st.caption('PASS means the saved challenger identified no overclaim in the stated boundary. It is not proof of replication, modality equivalence or established biology.')
                labels={
                    'hypothesis_and_finding':'Hypothesis kept separate from established findings',
                    'cell_loss_and_qc':'Cell-loss and assay-quality limits respected',
                    'replication_independence':'Same-donor methods not claimed as independent replication',
                    'modality_equivalence':'Expression reduction not claimed equivalent to receptor blockade',
                }
                for key,result in critic['checks'].items():
                    st.markdown('**'+result+'** · '+labels.get(key,key.replace('_',' ')))
            for finding in critic['findings']:
                with st.container(border=True):
                    st.markdown('**'+finding['severity'].upper()+'** · '+(finding.get('claim_id') or 'Opening / cross-cutting'))
                    st.write(finding['issue']);st.markdown('**Required change**');st.write(finding['required_change'])
                    with st.expander('Cited evidence'):
                        for citation in finding['citations']:
                            st.caption(citation['source_id']);st.code(citation['quote'],language=None,wrap_lines=True)
        else:st.info('No validated challenger response saved.')
    with st.expander('Actual call and revision history'):
        st.caption('Recorded outputs only. This view does not invent a revision when none occurred.')
        for index,call in enumerate(report.get('calls',[]),1):
            st.write(f"{index}. {call['role'].title()} — {call['status']}")
            st.json(call.get('output',call.get('raw_output',{})))
    with st.expander('Report binding and limits'):
        st.json(report['binding']);text_list(report.get('limitations',[]))


def handoff(run,brief):
    st.subheader('Specialist handoff · saved record')
    saved=run['state'].get('handoff')
    if not saved or not brief or saved['assessment']['assessment_id']!=brief['assessment_id']:
        st.info('No specialist handoff captured for this assessment. Prepare a local simulation below after explicit human approval.')
    else:
        status,effective,review=review_status(run,brief)
        st.success('Handoff created and saved — '+saved['handoff_id'])
        with st.container(border=True):
            st.subheader('Saved handoff receipt')
            st.write('Recipient: antibody specialists · local simulation')
            st.write('Assessment: '+saved['assessment']['assessment_id'])
            st.write('Authorized by: '+saved['review']['reviewer_role']+' · '+saved['review']['review_id'])
            created=next((e['created_at'] for e in run['events'] if e['kind']=='HANDOFF_CREATED' and e['payload'].get('handoff_id')==saved['handoff_id']),None)
            if created:st.write('Saved at: '+created)
            st.caption('The request is stored locally. No external message or experiment order was sent.')
        st.caption('Current canonical review: '+status)
        if not effective:st.warning('Historical or stale handoff — not current authorization.')
        response=run['state'].get('specialist_response')
        if response:
            st.subheader('What happens next')
            st.warning('Simulated specialist response: '+response['status'].replace('_',' ').lower())
            st.write(response['reason']);st.markdown('**Next action**');st.write(response['next_action'])
            st.markdown('**Owner:** '+response['next_owner_role'])
        with st.expander('Review the saved request and supporting decision'):
            handoff_summary(saved['assessment'],saved['review'],saved['requested_action'])
        with st.expander('Exact saved handoff packet'):st.json(saved)
    st.caption('No message or experiment order is sent. Platform questions below are illustrative, not specialist verdicts.')
    st.table([
        {'Platform':'Antibody','Question':'Can blockade reproduce the expression-reduction phenotype?','Specialist owns':'Binding, functional activity and developability'},
        {'Platform':'Small molecule','Question':'Is the required intervention tractable with suitable selectivity and exposure?','Specialist owns':'Chemistry, tractability and pharmacology'},
        {'Platform':'Oligonucleotide','Question':'Can expression reduction be delivered in relevant cells with appropriate isoform coverage?','Specialist owns':'Sequence, delivery and tolerability'}])


def main():
    st.caption('INVENTED TARGET & DATA  /  LOCAL SIMULATION  /  AI CHECKS ON REQUEST')
    st.title('Target Hypothesis Workbench')
    st.caption('PUBLIC SYNTHETIC REPLAY · Bundled reviews and follow-ups are scripted examples; bundled agent reports use the offline test provider.')
    if 'action_notice' in st.session_state:st.success(st.session_state.pop('action_notice'))
    presets={'My saved runs':PACKAGE/'demo-runs',
             'Bundled initial & supportive':PACKAGE/'recorded_examples/agents/state',
             'Bundled reviewed handoff':PACKAGE/'recorded_examples/state'}
    env=os.environ.get('TARGET_DEMO_WORKSPACE')
    if env:presets={'Selected workspace':Path(env),**presets}
    default=0 if env or (PACKAGE/'demo-runs/workflow.sqlite3').is_file() else 1
    with st.sidebar:
        st.markdown('### Explore saved evidence')
        choice=st.selectbox('Workspace',list(presets)+['Other local directory'],index=default,key='workspace_choice')
        workspace=Path(st.text_input('Directory containing workflow.sqlite3',key='workspace_path')).expanduser() if choice=='Other local directory' else presets[choice]
        st.caption('Browsing reads saved state. Only explicit review and handoff submissions write local records.')
    try:runs=list_runs(workspace)
    except (ValueError,OSError,sqlite3.Error):
        st.info('No readable saved database here. Choose a bundled workspace, or select the directory containing your existing workflow.sqlite3.');return
    if not runs:st.info('This database contains no saved runs.');return
    rid=st.sidebar.selectbox('Run',[r['run_id'] for r in runs],key='run_id')
    try:
        run=load_run(workspace,rid)
        ids=[b['assessment_id'] for b in reversed(run['assessments'])]
        amended=st.session_state.pop('select_amended_assessment',None)
        if amended in ids:st.session_state['assessment_id']=amended
        aid=st.sidebar.selectbox('Assessment',ids,key='assessment_id') if ids else None
        brief=next((b for b in run['assessments'] if b['assessment_id']==aid),None)
        status,effective,review=review_status(run,brief)
        st.caption('DEMO-R1 · '+(aid or 'Assessment pending')+' · '+status)
        if not run['inputs_current']:st.warning('Saved input or implementation versions differ from the installed package. Displaying historical evidence; approval is not current.')
        if brief and aid!=run['state']['current_assessment_id']:
            st.info('Historical assessment. Evidence & prediction shows the run’s latest captured context; the selected brief retains its original version references.')
        view=st.radio('View',['Decision','Evidence & prediction','Challenge & review','Specialist handoff','Ask the evidence assistant'],horizontal=True,label_visibility='collapsed',key='view')
        cancel_on_navigation(view,rid,aid,workspace)
        st.divider()
        if view=='Challenge & review' and brief:
            human_review_summary(run,brief)
            followup_controls(workspace,run,brief)
        if view=='Decision':
            decision(run,brief)
            if brief:
                human_review_summary(run,brief)
                followup_controls(workspace,run,brief)
        elif view=='Evidence & prediction':evidence(run)
        elif view=='Challenge & review':
            challenge(workspace,run,brief)
            review_controls(workspace,run,brief)
        elif view=='Ask the evidence assistant':assistant_view(workspace,run,brief)
        else:
            handoff(run,brief)
            handoff_controls(workspace,run,brief)
        with st.sidebar:
            st.divider();st.caption('Slice 2 · Explicit local review')
            st.caption('Review controls are under Challenge & review. Specialist handoff is a local simulation only.')
            if brief:
                st.download_button('Download saved brief',json.dumps(brief,indent=2),file_name=aid+'.json',mime='application/json')
        with st.expander('Saved workflow events'):
            st.dataframe([{'Event':e['event_id'],'Type':e['kind'],'Recorded at':e['created_at']} for e in run['events']],hide_index=True,width='stretch')
            st.caption('This is a saved event list, not a live execution trace.')
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as exc:
        st.error('Cannot safely display this saved record: '+str(exc))

main()
