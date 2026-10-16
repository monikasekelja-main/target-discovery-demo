"""Explicit preview-and-submit controls for local human review and handoff."""
from pathlib import Path
import sqlite3
import os
import streamlit as st
from target_discovery.ui.ui_service import PACKAGE, list_reports, review_status, FINDINGS
from target_discovery.review.review_service import prepare_review, prepare_handoff, ReviewWorkflow, review_receipt, handoff_receipt, advice_binding, load_rationale_check
from target_discovery.review.rationale_advisor import draft_fields


def human_review_summary(run,brief):
    label,effective,review=review_status(run,brief)
    if not review:
        st.info('Human decision: pending review')
        return
    current=label in ('Approved local-demo action','Deferred','Amended')
    with st.container(border=True):
        st.subheader('Human decision: '+{'DEFER':'Deferred','APPROVE':'Approved for local simulation','AMEND':'Amended'}[review['decision']])
        if not current:
            st.warning(label+' — this saved decision is not current authorization.')
        elif review['decision']=='DEFER':
            st.warning('Progression is on hold. This review does not authorize a specialist handoff.')
        elif effective:
            st.success('Human approval recorded for this assessment, within local simulation only.')
        else:
            st.info('The amended assessment requires a new human review.')
        st.markdown('**Reviewer:** '+review['reviewer_role'])
        st.markdown('**Reason for the decision**')
        st.write(review['rationale'])
        st.caption('Saved review '+review['review_id']+' · Assessment '+review['assessment_id'])
        st.caption('The evidence assessment describes the experimental findings. The human decision determines whether to proceed; deferring does not change those findings.')


def available(workspace,run,brief):
    if Path(workspace).resolve().is_relative_to(PACKAGE/'recorded_examples'):
        st.info('Bundled examples are read-only. Select your saved workspace to record a local review.');return False
    if not brief or brief['assessment_id']!=run['state']['current_assessment_id']:
        st.info('Select the current complete assessment to prepare an action.');return False
    if not run['inputs_current'] or run['state']['phase']=='BLOCKED':
        st.warning('Review and handoff are disabled until stale or blocked inputs are resolved.');return False
    return True


def preview_details(preview):
    st.caption('Exact canonical assessment: '+preview['assessment_id'])
    st.code(preview['assessment_sha256'],language=None,wrap_lines=True)
    st.write(preview['brief']['next_action'])
    with st.expander('Canonical assessment being reviewed',expanded=False):st.json(preview['brief'])


def review_controls(workspace,run,brief):
    st.divider();st.subheader('Record human review · local simulation')
    st.caption('Approval applies to this canonical assessment only. Agent readiness and PASS checks never grant approval.')
    if not available(workspace,run,brief):return
    rid=run['state']['run_id']
    prior=run['state']['review']
    if prior:
        receipt=review_receipt(workspace,rid,prior['review_id'])
        with st.expander('Current human review and consultation provenance'):
            st.json(prior)
            if receipt:
                st.json(receipt)
                if not receipt.get('rationale_advice'):st.caption('This saved review predates rationale checking. Its reasoning was not checked by this feature.')
                else:
                    st.write('Saved rationale feedback and override provenance')
                    st.json(load_rationale_check(workspace,receipt['rationale_advice']['check_id']))
            else:st.caption('Legacy review: report consultation was not recorded. Viewing a report does not attach it to this approval.')
    choices=['No agent report consulted']+[r['attempt_id'] for r in list_reports(workspace,rid) if r['assessment_id']==brief['assessment_id']]
    choice=st.selectbox('Report consulted for this new review',choices,key='review_report')
    key='review_preview:'+str(Path(workspace).resolve())+':'+rid+':'+brief['assessment_id']
    if st.button('Prepare human review',key='prepare_review'):
        try:
            st.session_state[key]=prepare_review(workspace,rid,brief['assessment_id'],None if choice==choices[0] else choice)
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error(str(exc))
    preview=st.session_state.get(key)
    if not preview:return
    preview_details(preview)
    consulted=preview['consultation']
    if consulted:
        st.write('Previewed report: '+consulted['attempt_id']+' · '+consulted['mode']+' · '+consulted['effective_status'])
        st.caption('Separate report digest');st.code(consulted['report_sha256'],language=None,wrap_lines=True)
    else:st.info('This review explicitly records that no agent report was consulted.')
    stale=bool(consulted and consulted['effective_status']=='STALE')
    if stale:st.warning('Historical report only. Its binding is stale; it cannot be recorded as current advice.')
    st.caption('Changing the report selection requires preparing a new preview. Submission uses the preview shown above.')
    suffix=preview['submission_id']
    st.markdown('**1. Draft your decision**')
    reviewer=st.text_input('Reviewer name or role',key='reviewer_'+suffix)
    decision=st.selectbox('Human decision',['DEFER','APPROVE','AMEND'],key='decision_'+suffix)
    rationale=st.text_area('Review rationale',key='rationale_'+suffix)
    next_action=st.text_area('Revised next action (required only for AMEND)',key='next_action_'+suffix,
        help='Creates a new canonical draft requiring a separate review. Scientific calculations remain unchanged.')
    historical=st.checkbox('I acknowledge that this report is historical advice',key='historical_'+suffix) if stale else False
    try:draft=draft_fields(decision,reviewer,rationale,next_action,historical)
    except ValueError:draft=None
    st.markdown('**2. Check your reasoning**')
    mode_label=st.selectbox('Rationale check mode',['AI advisory check','Local checks only — no AI'],key='advice_mode_'+suffix)
    mode='live_llm' if mode_label=='AI advisory check' else 'local_checks'
    model=''
    if mode=='live_llm':
        model=st.text_input('Advisor model',value=os.environ.get('TARGET_REVIEW_MODEL','gpt-6-astra'),key='advisor_model_'+suffix)
        st.caption('One paid API call when you click. Sends this canonical assessment, decision, rationale and amendment text to OpenAI. Reviewer identity stays local. No automatic retry.')
        if not os.environ.get('OPENAI_API_KEY'):
            st.warning('AI checking needs OPENAI_API_KEY in the Streamlit server environment. Restart the server after setting it; do not paste keys here. Local checks are available but cannot assess meaning.')
    else:
        st.info('Local text checks only. They can flag missing evidence references but cannot evaluate meaning or scientific consistency. Saving requires an explicit override of the missing AI review.')
    advice_key='rationale_advice_'+suffix
    if st.button('Check rationale with AI (one paid call)' if mode=='live_llm' else 'Run local checks (no model)',
                 key='check_rationale',disabled=draft is None):
        app=None
        try:
            app=ReviewWorkflow(workspace)
            with st.spinner('Checking draft rationale…'):
                checked=app.check_rationale(preview,decision,reviewer,rationale,next_action=next_action,
                    historical_ack=historical,mode=mode,model=model)
            st.session_state[advice_key]=checked['request']['check_id']
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:
            st.session_state.pop(advice_key,None);st.error('Rationale check not available: '+str(exc))
        finally:
            if app:app.close()
    checked=None
    if st.session_state.get(advice_key):
        try:checked=load_rationale_check(workspace,st.session_state[advice_key])
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error(str(exc))
    current=bool(checked and draft and checked['request']['input_sha256']==advice_binding(preview,draft))
    if checked and not current:st.warning('Draft changed since the check. Check the current decision and rationale again before saving.')
    needs_override=True
    if current:
        result=checked['result'];feedback=result['feedback']
        st.caption('AI advisory feedback' if result['mode']=='live_llm' else 'Local check feedback — not AI reasoning')
        if result['status']!='COMPLETED':st.error(result['error'] or 'Check did not complete; no accepted advice.')
        if feedback:
            if feedback['outcome']=='NO_CONCERNS_IDENTIFIED':st.success('No concerns identified by this check. This is not approval or proof of correctness.')
            elif feedback['outcome']=='NEEDS_REVISION':st.warning('Revise your rationale or explain an explicit override before saving.')
            else:st.warning('The check could not establish whether this rationale is adequate.')
            st.write(feedback['summary'])
            for finding in feedback['findings']:
                with st.container(border=True):
                    st.caption('Draft text');st.text(finding['draft_quote'])
                    st.write(finding['issue']);st.write(finding['guidance'])
            for question in feedback['questions']:st.write('Question: '+question)
        needs_override=not (result['status']=='COMPLETED' and result['mode']=='live_llm' and feedback and feedback['outcome']=='NO_CONCERNS_IDENTIFIED')
        if result['status']=='STALE':current=False
        with st.expander('Exact advisory check and draft binding'):st.json(checked)
    st.markdown('**3. Record your final human decision**')
    if not current:st.info('Complete a check of this exact draft before recording a decision.')
    # A new check ID gets fresh acknowledgements; prior confirmations never carry forward.
    final_key=suffix+'_'+(checked['request']['check_id'] if current else 'unchecked')
    with st.form('human_review_final_'+final_key):
        advice_ack=st.checkbox('I have read the feedback and understand its limitations')
        override=st.checkbox('I explicitly override the concerns or unavailable AI review') if needs_override else False
        override_reason=st.text_area('Why proceed despite the concerns or missing AI review?') if needs_override else ''
        acknowledged=st.checkbox('I reviewed this exact assessment and explicitly record this decision for local simulation only')
        submitted=st.form_submit_button('Record human decision',disabled=not current)
    if submitted:
        app=None
        try:
            app=ReviewWorkflow(workspace)
            result=app.submit_review(preview,decision,reviewer,rationale,acknowledged=acknowledged,
                historical_ack=historical,next_action=next_action,check_id=checked['request']['check_id'],
                advice_acknowledged=advice_ack,override=override,override_reason=override_reason)
            del st.session_state[key]
            if decision=='AMEND':st.session_state['select_amended_assessment']=result['current_assessment_id']
            st.session_state['action_notice']='Recorded '+result['review_id']+'. '+('Amended draft requires a new review.' if decision=='AMEND' else 'Local simulation only.')
            st.rerun()
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error('Review not recorded: '+str(exc))
        finally:
            if app:app.close()


def handoff_summary(brief,review,request):
    with st.container(border=True):
        st.subheader('Request to antibody specialists')
        st.write(request)
        st.caption('Local simulation: confirming saves a handoff and a simulated response. No specialist is contacted and no experiment is ordered.')
        st.markdown('**Scientific next step being supported**')
        st.write(brief['next_action'])
        st.markdown('**Evidence supporting this request**')
        st.write(FINDINGS[brief['scientific_recommendation']])
        st.write(brief['rationale'])
        st.write('Assay prerequisites: '+('passed' if brief['prerequisites_passed'] else 'not passed'))
        st.markdown('**Uncertainties the specialists must consider**')
        for uncertainty in brief['remaining_uncertainties']:st.write('• '+uncertainty)
    with st.container(border=True):
        st.subheader('Human decision supporting this handoff')
        st.write('Decision: '+{'APPROVE':'Approved for local simulation','DEFER':'Deferred','AMEND':'Amended'}[review['decision']])
        st.write('Reviewer: '+review['reviewer_role'])
        st.markdown('**Reason for the decision**');st.write(review['rationale'])
        st.caption('Assessment '+brief['assessment_id']+' · Review '+review['review_id'])


def handoff_controls(workspace,run,brief):
    saved=run['state'].get('handoff')
    if saved and brief and saved['assessment']['assessment_id']==brief['assessment_id']:
        with st.expander('Saved handoff consultation provenance'):
            receipt=handoff_receipt(workspace,run['state']['run_id'],saved['handoff_id'])
            if receipt:st.json(receipt)
            else:st.caption('Legacy handoff: no separate consultation provenance was recorded.')
        st.info('This assessment already has a saved handoff. Review its receipt and simulated response above; no further creation step is needed.')
        return
    st.divider();st.subheader('Prepare specialist handoff · local simulation')
    st.caption('Creates a saved antibody handoff and a simulated response. No external message, experiment order or API call is sent.')
    if not available(workspace,run,brief):return
    status,effective,review=review_status(run,brief)
    eligible=effective and brief['scientific_recommendation']=='ADVANCE_TO_REPLICATION' and brief['prerequisites_passed']
    if not eligible:st.info('Requires explicit current human approval of a supportive result with passed assay prerequisites.')
    key='handoff_preview:'+str(Path(workspace).resolve())+':'+run['state']['run_id']+':'+brief['assessment_id']
    if st.button('Preview local handoff',disabled=not eligible,key='prepare_handoff'):
        try:st.session_state[key]=prepare_handoff(workspace,run['state']['run_id'],brief['assessment_id'])
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error(str(exc))
    preview=st.session_state.get(key)
    if not preview:return
    st.subheader('Review the proposed handoff')
    handoff_summary(preview['brief'],preview['expected_review'],
        'Assess whether receptor blockade can reproduce the expression-reduction phenotype; identify the missing evidence.')
    receipt=preview['review_receipt']
    consultation=receipt.get('consultation') if receipt else None
    st.markdown('**Advice considered in the human review**')
    if consultation:
        st.write('Saved report: '+consultation['attempt_id'])
        st.write('Report status at review: '+consultation['effective_status'].replace('_',' ').lower())
    else:st.write('No agent report consultation recorded for this approval.')
    if receipt and receipt.get('rationale_advice'):
        advice=receipt['rationale_advice']
        st.write('Rationale check: '+(advice.get('outcome') or advice['status']).replace('_',' ').lower())
        st.caption('AI advisory check' if advice['mode']=='live_llm' else 'Local text checks only')
        if advice['overridden']:
            st.write('Reviewer override: '+advice['override_reason'])
    else:st.caption('No rationale-check record attached to this approval.')
    with st.expander('Technical details · exact records and verification'):
        st.code(preview['assessment_sha256'],language=None,wrap_lines=True)
        st.json(preview['brief'])
        st.json(preview['expected_review'])
        if preview['review_receipt']:st.json(preview['review_receipt'])
        else:st.caption('Legacy approval: no consultation receipt was recorded. No report will be attached retroactively.')
    with st.form('local_handoff_'+preview['submission_id']):
        st.markdown('**Confirm this request**')
        st.write('Confirm that the request, evidence limitations and human decision above match what you want to hand over.')
        acknowledged=st.checkbox('I explicitly authorize this local simulated handoff using the previewed approval')
        submitted=st.form_submit_button('Create local simulated handoff',disabled=not eligible)
    if submitted:
        app=None
        try:
            app=ReviewWorkflow(workspace);saved=app.submit_handoff(preview,acknowledged=acknowledged)
            del st.session_state[key];st.session_state['action_notice']='Handoff created successfully — '+saved['handoff_id']+'. Your saved receipt and simulated specialist response are below. No message or order was sent.';st.rerun()
        except (ValueError,OSError,KeyError,sqlite3.Error) as exc:st.error('Handoff not created: '+str(exc))
        finally:
            if app:app.close()
