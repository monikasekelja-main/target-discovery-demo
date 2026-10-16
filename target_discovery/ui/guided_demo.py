"""Read-only, four-step projection of the saved public case; no workflow writes."""
import sqlite3
import streamlit as st
from target_discovery.ui.ui_service import PACKAGE, load_run, recorded_policy, review_status
from target_discovery.ui.ui_charts import functional_chart
from target_discovery.ui.ui_programme_context import programme_context

STEPS=('1 · Why investigate?', '2 · What did we learn?', '3 · What was decided?', '4 · What happens next?')


def go(step):
    st.session_state['guide_step']=STEPS[step]


def render(challenge_view):
    workspace=PACKAGE/'demo-runs'
    st.title('From target evidence to a justified next step')
    st.caption('Plaque psoriasis · Fictional target DEMO-R1 · About 3 minutes')
    st.caption('Saved synthetic case. Reviews and agent reports are scripted; the specialist reply is simulated. No API key needed.')
    try:
        run=load_run(workspace,'demo')
        brief=next((b for b in run['assessments'] if b['assessment_id']=='demo-A002'),None)
        if (brief is None or not run['inputs_current'] or run['state']['current_assessment_id']!='demo-A002'
                or run['state'].get('selected_experiment')!='X101'
                or brief['scientific_recommendation']!='ADVANCE_TO_REPLICATION' or brief['prerequisites_passed'] is not True):
            st.warning('This saved case has changed or is no longer current. Open Explore the workbench to inspect it. The guided story has not been substituted or regenerated.')
            return
        records={r['evidence_id']:r for r in run['state'].get('evidence',{}).get('records',[])}
        if 'E07' not in records:
            st.warning('The source record for this story is missing. Open Explore the workbench to inspect the saved case.');return
        step=STEPS.index(st.radio('Follow the case',STEPS,horizontal=True,key='guide_step',label_visibility='collapsed'))
        st.divider()
        if step==0:
            st.subheader('A promising signal had another explanation')
            left,right=st.columns([1.15,1],gap='large')
            with left:
                st.markdown('**The question**')
                st.write('Could reducing DEMO-R1 expression change an inflammatory T-cell state relevant to plaque psoriasis?')
                st.caption('An untested target hypothesis. Published disease biology motivates the question; it does not validate this fictional target.')
                st.markdown('**The earlier observation · E07**')
                st.write(records['E07']['claim'])
            with right:
                with st.container(border=True):
                    st.markdown('**Why a better test was needed**')
                    st.write('Less cytokine in the culture could reflect fewer surviving cells, rather than less production by surviving cells.')
                    st.write('The next experiment therefore assessed the IL-17A-positive fraction among live cells, alongside cell-preservation controls.')
            st.info('Takeaway: a promising signal is a reason to test the hypothesis—not to accept it.')
        elif step==1:
            st.subheader('Enough evidence to replicate—not to call the target validated')
            left,right=st.columns([1.3,1],gap='large')
            with left:
                st.plotly_chart(functional_chart(brief,recorded_policy(run,brief)['minimum_useful_reduction_pct']),
                    width='stretch',config={'displayModeBar':False},key='guide_effects')
                st.caption('Relative reduction in the live-cell IL-17A-positive fraction. Saved estimates with 95% confidence intervals.')
            with right:
                for name,values in brief['functional_effects'].items():
                    st.markdown(f"**{name}: {values['mean']:.0f}% reduction**")
                st.write('Both intervals clear the provisional useful-effect threshold; recorded assay and cell-preservation checks passed.')
                st.warning('Both methods used the same eight donors. This is not independent replication.')
                st.caption('Selective loss of cytokine-producing cells, target specificity and antibody-blockade equivalence remain unresolved. Culture viability is not systemic safety.')
            st.info('Next scientific step: '+brief['next_action'])
        elif step==2:
            st.subheader('A recorded decision with a clear scope')
            status,effective,review=review_status(run,brief)
            roles,decision=st.columns([1.1,1],gap='large')
            with roles:
                with st.container(border=True):
                    st.markdown('**Who does what?**')
                    st.markdown('**Analyst agent** — interprets evidence, cites sources and proposes a next step. Cannot change calculations or approve progression.')
                    st.markdown('**Challenger agent** — checks claims, conflicts and missing qualifications. “Ready for review” is not validation or approval.')
                    st.markdown('**Deterministic code** — calculates effects and applies predefined rules. Does not make scientific judgements beyond those rules.')
                    st.markdown('**Human reviewer** — approves, defers or amends the next action and records why. Approval does not remove uncertainty.')
                st.caption('Example of the intended check: agreement between two methods in the same eight donors must not be described as independent replication.')
            with decision:
                if review is None:st.info('No decision is recorded for this assessment. The scientific recommendation is not approval.')
                else:
                    if effective:st.success('Recorded decision: approve the scoped next action · local simulation')
                    else:st.warning('Recorded review status: '+status+' · no current approval')
                    st.caption('Reviewer: '+review['reviewer_role']+' · '+review['review_id'])
                    st.markdown('**Saved rationale**');st.write(review['rationale'])
                st.caption('These saved agent responses and reviews are scripted examples. They show workflow boundaries, not live reasoning or independent scientific review.')

        else:
            st.subheader('Give specialists a specific question they can act on')
            saved=run['state'].get('handoff');response=run['state'].get('specialist_response')
            status,effective,review=review_status(run,brief)
            current=bool(saved and response and effective and saved['assessment']==brief and saved['review']==review
                         and response['handoff_id']==saved['handoff_id'] and response['assessment_id']==brief['assessment_id']
                         and response['reviewed_content_sha256']==review['reviewed_content_sha256'])
            if not current:
                st.warning('No current, matching specialist handoff is available. Explore the workbench to inspect the records.');response=None
            if response:
                left,right=st.columns(2,gap='large')
                with left:
                    with st.container(border=True):
                        st.markdown('**Question for the antibody team**');st.write(saved['requested_action'])
                with right:
                    st.warning('Simulated reply: '+response['status'].replace('_',' ').lower())
                    st.write(response['reason'])
                    st.markdown('**Next action**');st.write(response['next_action'])
                    st.caption('Owner: '+response['next_owner_role'])
                st.info('The outcome is a justified next step with uncertainty visible—not target validation. Independent replication and specificity work remain necessary.')
            st.caption('Saved locally only. No email, Teams or Slack message was sent, and no experiment was ordered.')
        st.divider()
        back,progress,next_col=st.columns([1,2,1])
        back.button('← Back',key='guide_back',disabled=step==0,on_click=go,args=(max(0,step-1),),width='stretch')
        progress.caption(f'Step {step+1} of 4 · Read-only saved case')
        next_col.button('Next →' if step<3 else 'Start again',key='guide_next',on_click=go,args=((step+1)%4,),type='primary',width='stretch')
        if step==2:
            with st.expander('Inspect the saved agent report'):
                st.caption('Read-only saved output. This scripted report is not evidence that a live agent performed the checks above.')
                challenge_view(workspace,run,brief)
        with st.expander('View supporting detail'):
            st.caption('Saved run demo · Assessment demo-A002. Details do not change records.')
            if step==0:
                programme_context(brief)
                st.markdown('**Exact source record · E07**');st.json(records['E07'])
                st.caption('Frozen synthetic predictions are not measured functional benefit. No predictive model was trained or run.')
            elif step==1:
                st.dataframe([{'Method':k,**v} for k,v in brief['functional_effects'].items()],hide_index=True)
                for item in brief['remaining_uncertainties']:st.write('• '+item)
                st.caption('Saved policy');st.json(recorded_policy(run,brief))
            elif step==2:
                if review:st.json(review)
            else:
                if saved:st.json(saved)
                if response:st.json(response)
                st.write('Other specialist questions: oligonucleotide delivery, isoform coverage and tolerability; small-molecule tractability, selectivity and exposure. These are questions, not feasibility findings.')
        st.caption('For alternative scenarios, full evidence, review controls or the optional evidence assistant, choose Explore the workbench above.')
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as exc:
        st.error('The saved guided case cannot be displayed safely. Open Explore the workbench to inspect the records.')
        with st.expander('Diagnostic detail'):st.text(str(exc))
