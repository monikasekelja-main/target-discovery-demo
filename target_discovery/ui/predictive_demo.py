"""Four-step, offline patient-study rehearsal; independent of saved assay records."""
import json
import streamlit as st
from target_discovery.predictive.explainer import QUESTIONS, offline_answer, trace
from target_discovery.predictive.replay import load_examples, replay, review_nomination, current_review

STEPS = ('1 · Define the study','2 · Test the prediction','3 · Review the experiment','4 · Agree the next action')
LABELS = {'supported_for_review':'Supportive — in this illustrative scenario', 'unresolved':'Unresolved', 'exploratory':'Exploratory only', 'blocked':'Prediction blocked'}

def navigation_changed():
    st.session_state['predictive_navigation'] = st.session_state.get('predictive_navigation',0)+1

def go(index):
    st.session_state['predictive_step'] = STEPS[index]
    navigation_changed()

def reset_scroll_on_navigation():
    token=st.session_state.get('predictive_navigation',0)
    if token != st.session_state.get('predictive_navigation_rendered',-1):
        st.session_state['predictive_navigation_rendered']=token
        # Fixed local script only; no user or scientific content is interpolated.
        st.html('''<script>
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const main = document.querySelector('[data-testid="stMain"]');
            if (main) main.scrollTo({top: 0, behavior: 'instant'});
            window.scrollTo({top: 0, behavior: 'instant'});
        }));
        </script>''',unsafe_allow_javascript=True)


def feedback_changed():
    st.session_state['predictive_feedback_applied'] = st.session_state['predictive_feedback']

def render():
    st.caption('PATIENT-STUDY DEMO')
    st.title('From patient cells to a justified experiment')
    st.caption('Plaque psoriasis → in-silico perturbation → intervention and cell state → biological test')
    st.info('Illustrative example — this patient study has not been run. DEMO-R1 and all results are fictional; no model or API is called.')
    try:
        study, scenarios = load_examples()
    except (ValueError, OSError) as exc:
        st.error(f'Cannot load the illustrative study: {exc}'); return
    with st.expander('Explore a different scenario or route'):
        scenario_id = st.selectbox('Offline scenario',[s.id for s in scenarios],format_func=lambda v:next(s.label for s in scenarios if s.id==v),key='predictive_scenario')
        route = st.radio('When should biology start?', ['after_prediction','parallel'],
            format_func=lambda v:'After supportive predictive review' if v=='after_prediction' else 'In parallel, on an independent scientific rationale',key='predictive_route')
        st.caption('Scenario checks are scripted assumptions. The real study remains unexecuted. Changing scenario or route requires a new rehearsal review.')
    scenario = next(s for s in scenarios if s.id == scenario_id)
    nomination = replay(study,scenario,route,st.session_state.get('predictive_feedback_applied',False))
    st.caption(f"Scenario: {scenario.label} · Route: {'after predictive review' if route=='after_prediction' else 'independent parallel biology'}")
    review = current_review(nomination,st.session_state.get('predictive_review'))
    step = STEPS.index(st.radio('Study journey',STEPS,horizontal=True,key='predictive_step',label_visibility='collapsed',on_change=navigation_changed))
    if step == 0:
        st.subheader('Which psoriasis-related cells should we test?')
        st.write('We want to learn whether reducing DEMO-R1 could change inflammatory activity in a particular group of CD4 T cells.')
        st.caption('A cell state is a particular condition or activity pattern of a cell. Here, the state of interest is Th17-like CD4 cells.')
        left,right = st.columns(2)
        with left:
            st.markdown('**Start with patient cells**')
            st.write('Use single-cell RNA data from psoriasis skin to identify relevant cells across patients.')
            st.markdown('**Ask a focused question**')
            st.write('Which cells are worth testing, and what should the biological experiment measure?')
        with right:
            st.markdown('**Check the data first**')
            st.write('Confirm cell labels and data quality, then set aside patients for an independent evaluation.')
            st.markdown('**Use a suitable comparison**')
            st.write('Compare related CD4 cell states, with biology reviewing what a useful change would mean.')
        with st.expander('Study requirements and scientific context'):
            st.write(study.question)
            st.write(study.dataset.reference)
            st.write('Before a real run: agree data access, donor coverage, annotation, the real gene identifier and model compatibility. No dataset or model has been selected here.')
            st.caption('Published disease background, synthetic target evidence and untested mechanism/differentiation hypotheses remain distinct.')
    elif step == 1:
        if nomination.cell_state:
            st.subheader('The Th17-like state shows the most consistent signal' if nomination.cell_state=='Th17-like CD4 state' else 'One cell state is worth prioritising for testing')
            st.write('In this invented example, the result is stronger than both comparisons in every evaluation donor. That supports proposing a biological test.')
        elif nomination.status=='blocked':
            st.subheader('We need to resolve a problem before predicting')
            st.warning(nomination.request)
        else:
            st.subheader('The prediction is not yet strong enough to nominate a test')
            st.write(nomination.challenge)
        if nomination.comparisons:
            st.table([{'Cell state':c['cell_state'],'Donors exceeding both comparisons':f"{c['donors_above_comparators']} of {c['donors']}", 'Donor check':'Consistent' if c['eligible'] else 'Needs review'} for c in nomination.comparisons])
            st.caption('These are invented comparisons of model representations, not measured changes in cytokines or health. Other context and model checks still apply.')
            with st.expander('Inspect scores, donor sensitivity and evaluation plan'):
                st.caption('Positive = movement toward the illustrative within-lineage reference. Arbitrary representation units; no calibrated biological threshold.')
                st.table([{'State':c['cell_state'],'Mean shift':c['mean_shift'],'Simple baseline':c['baseline'],'Control':c['control'],'Lowest leave-one-out mean':c['leave_one_out_min']} for c in nomination.comparisons])
                st.write('Leaving out one donor at a time checks whether one person drives the average. The lowest resulting mean is shown above.')
                st.table([{'Record':c['evidence_id'],'State':c['cell_state'],**c['donor_shifts'],'Identity preserved':c['identity_preserved']} for c in nomination.comparisons])
                st.write('Illustrative rule: every held-out donor must exceed both comparators and cell identity must be preserved. Rank eligible states by mean shift. Context, model suitability and unresolved contradictions can still prevent nomination.')
                st.write(study.adaptation.plan+' '+study.adaptation.split)
                st.write('Compare adaptation with the unadapted model. Improved disease representation does not establish causal perturbation accuracy. Evaluate intended perturbation use separately, holding out interventions if claiming transfer to unseen interventions.')
        with st.expander('See what the workflow checked'):
            st.table([{'Check':e.check,'Finding':e.finding,'Next action':e.action,'Owner':e.owner} for e in nomination.events])
    elif step == 2:
        st.subheader('Biology decides whether a small experiment is justified')
        st.markdown(f'**Predictive support: {LABELS[nomination.status]}**')
        if nomination.cell_state:
            st.write('**Proposed test:** reduce target expression and measure how the cells respond.')
            st.write(f'**Nominated state:** {nomination.cell_state}.')
        else:
            st.warning('No predictive nomination available. '+nomination.request)
        if route=='parallel':
            st.markdown('**Separate biological proposal — not inferred from patient-state prediction**')
            st.write(scenario.independent_rationale.basis)
        if nomination.proposed_test:
            st.write('**Plan for review:** '+nomination.proposed_test.replace('Scope reduction testing','Plan a test that reduces target expression').replace('Scope a cultured-CD4 reduction test','Plan a test that reduces target expression in cultured CD4 cells'))
        with st.expander('Check the prerequisites for approval'):
            st.table([{'Prerequisite':g.name,'Ready':g.met,'Evidence (invented)':g.basis,'Owner':g.owner} for g in nomination.prerequisites])
        if not nomination.route_eligible: st.warning(nomination.route_reason)
        else: st.caption('The required checks are met in this scenario. Human approval is still needed.')
        st.markdown('**How this workflow is controlled**')
        st.write('**Orchestrator** routes the next permitted action → **Verifier** checks evidence and prerequisites → **Human reviewer** decides whether to proceed.')
        st.caption('Offline demonstration: fixed code performs the checks; analyst/challenger commentary is scripted. Checks do not establish scientific truth.')
        with st.expander('Follow one example trace for this scenario'):
            for role,detail in trace(nomination): st.write('**'+role+':** '+detail)
            st.caption('Derived from the current replay, not a log of live model calls. The verifier can block progression; only humans approve experiments and resources.')
        with st.expander('Inspect the scripted analyst and challenger commentary'):
            st.caption('Deterministic offline commentary, not a saved live-model report or independent review. Bound to this study, scenario and route.')
            st.markdown('**Analyst:** '+nomination.reason+' '+nomination.route_reason)
            st.markdown('**Challenger:** '+nomination.challenge)
            st.markdown('**Follow-up request:** '+nomination.request)
            st.write('**Owner:** '+scenario.request_owner)
            st.caption('The fixed evaluator, not this scripted commentary, determines eligibility. No request is sent.')
            st.write('Model perturbation changes a representation; it is not calibrated transcript knockdown, protein inhibition or receptor blockade. The biological test must establish the relevant effect.')
            st.code(nomination.binding,language=None)
        with st.expander('Rehearse a human decision (session only)'):
            st.warning('Offline rehearsal only: the rationale is NOT checked for scientific meaning. Recording it is not an endorsement. No work, spending or saved assessment is authorized.')
            with st.expander('Example of rationale guidance (scripted)'):
                st.write('**Weak rationale:** “This was not acceptable because of the cherries.”')
                st.write('**Example guidance:** Explain the scoped experiment, the evidence supporting this route and the limitation it will address. Irrelevant text does not justify a decision.')
                st.caption('Fixed teaching example, not an assessment of your text. The original workbench’s optional AI rationale check is not invoked here.')
            with st.form('predictive_review_form'):
                decision = st.selectbox('Rehearsal decision',['DEFER','APPROVE_SCOPED_TEST'],key='predictive_decision')
                rationale = st.text_area('Explain the scope and reason',key='predictive_rationale',placeholder='Specify the proposed test, what it can resolve and the limitations that remain.')
                submit = st.form_submit_button('Record rehearsal decision')
            if submit:
                try:
                    st.session_state['predictive_review'] = review_nomination(nomination,decision,rationale)
                    st.rerun()
                except ValueError as exc: st.error(str(exc))
        if review:
            if review.decision=='APPROVE_SCOPED_TEST': st.success('Rehearsal decision: approve the scoped test proposal')
            else: st.warning('Rehearsal decision: defer')
            st.write(review.rationale)
        else: st.caption('Human decision: not recorded for this scenario and route. No approval is assumed.')
    else:
        if review and review.decision=='DEFER':
            st.subheader('Next: resolve the reviewer’s concern')
        elif not nomination.route_eligible:
            st.subheader('Next: resolve the outstanding requirement')
        elif review:
            st.subheader('Next: plan the agreed biological test')
        else:
            st.subheader('Next: biology reviews the proposed experiment')
        st.markdown('**Route: '+('after predictive review' if route=='after_prediction' else 'biology in parallel')+'**')
        if not nomination.route_eligible: st.write(nomination.route_reason)
        if review and review.decision=='APPROVE_SCOPED_TEST':
            st.success('Session rehearsal: scoped proposal approved. No experiment or handoff has been submitted.')
        elif review:
            st.warning('Session rehearsal: deferred. Resolve the reviewer’s concern before any commitment.')
        else:
            st.warning('Awaiting scoped human review. The following is a proposal, not an approved experiment.')
        st.markdown('**Immediate next action**')
        if review and review.decision=='DEFER': st.write('Resolve the reviewer’s concern: '+review.rationale)
        elif nomination.route_eligible and not review: st.write('Ask biology and the project owner to review the evidence, experiment and resources before making a commitment.')
        else: st.write(nomination.next_action.replace('Scope reduction testing','Plan a test that reduces target expression').replace('Scope a cultured-CD4 reduction test','Plan a test that reduces target expression in cultured CD4 cells'))
        st.caption('Owner: Biology reviewer' if review and review.decision=='DEFER' else 'Owner: '+nomination.next_owner)
        if nomination.route_eligible:
            with st.expander('Proposed experiment and measurements'):
                st.write(nomination.proposed_test)
                st.write('RNA knockdown and CRISPRi; 72 hours is illustrative and must be agreed with biology. Establish how the culture relates to the patient state; a parallel proposal does not assume that match.')
                st.write('Measure target reduction, IL-17A-positive live-cell fraction, absolute cell/subset recovery and survival. Assess activation/stress and cytokine output per survivor to distinguish reduced production from selective loss.')
                st.caption(study.biological_test.criteria)
            with st.expander('Specialist feedback: how the next experiment changes'):
                h=nomination.specialist
                st.caption('SCRIPTED OFFLINE EXCHANGE · '+h['request_id']+' · linked to this proposal; no message sent')
                st.write('**Antibody request:** '+h['question'])
                st.write('**Simulated reply — needs information:** '+h['response'])
                st.write('**Before:** '+h['before'])
                st.write('**Revised next step:** '+h['after'])
                st.caption('Owner: '+h['owner']+'. Effort: '+h['effort'])
                st.checkbox('Include specialist recommendation in proposal',key='predictive_feedback',value=st.session_state.get('predictive_feedback_applied',False),on_change=feedback_changed)
                st.caption('Changing this scope invalidates the prior rehearsal approval. Return to step 3 for review of the revised proposal.')
                st.write('**Small molecule:** can we modulate the target and measure engagement? **Oligonucleotide:** can knockdown reach the relevant cells with appropriate isoform coverage and tolerability?')
        else:
            st.info('The assay and specialist exchange remain deferred on this route. Resolve the displayed action or select an independently justified parallel route.')
        with st.expander('How future results would change the decision'):
            st.write('A supportive assay prompts independent replication and specificity work. A precise negative with successful perturbation can lower priority. Failed QC or imprecision remains unresolved. Preserve prediction/experiment disagreement and review intervention and cell-state match.')
            st.write('The existing assay replay is available through “Optional assay example” above. Its invented 32%/29% results are a separate example, not outputs of this proposed study.')
    with st.expander('Ask about this proposal'):
        st.caption('OFFLINE EXAMPLE ANSWERS · predefined questions, no live AI or external retrieval')
        st.caption(f'Current context: {nomination.study_id} · {scenario.label} · {route.replace("_", " ")}')
        question=st.selectbox('Choose a question',QUESTIONS,key='proposal_question')
        answer=offline_answer(nomination,question,review)
        st.write(answer['answer'])
        with st.expander('Answer sources and boundaries'):
            st.write('Based on: '+', '.join(answer['sources']))
            st.caption('Read-only explanation of this proposal. No access to the separate assay case; no approval, editing, execution or messaging capability. Selection changes no scientific records.')
            st.code(answer['binding'],language=None)
    with st.expander('Study detail and evidence boundaries'):

        for boundary in study.boundaries: st.write('• '+boundary)
        st.write('**Reproducible plan:** '+study.adaptation.split)
        st.write('**Model and baseline:** '+study.model.baseline)
        st.caption('Published background is available in the workbench’s programme context. It does not validate the fictional target.')
        st.download_button('Download illustrative nomination',json.dumps(nomination.model_dump(),indent=2),file_name='illustrative-nomination.json',mime='application/json')
        with st.expander('Technical study record'):
            st.json(study.model_dump())
    back,position,next_col = st.columns([1,3,1])
    back.button('Back',key='predictive_back',disabled=step==0,on_click=go,args=(max(0,step-1),),width='stretch')
    position.caption(f'Step {step+1} of 4')
    next_col.button('Start again' if step==3 else 'Next',key='predictive_next',on_click=go,args=((step+1)%4,),width='stretch')

    reset_scroll_on_navigation()
