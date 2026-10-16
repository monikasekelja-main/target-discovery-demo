"""Fixed offline explanations of the current proposal, never a model/chat provider."""
from .replay import current_review

QUESTIONS = (
    'Why is this the proposed next step?',
    'What did the orchestrator and verifier do?',
    'What still needs human judgement?',
    'What changes if biology starts in parallel?',
    'Can this assistant approve or change anything?',
)

def trace(nomination):
    return [
        ('Input', 'Current illustrative study, scenario, evidence records and selected route.'),
        ('Orchestrator', nomination.request),
        ('Verifier', f'Fixed checks return {nomination.status.replace("_", " ")}; route prerequisites '+('pass.' if nomination.route_eligible else 'do not pass.')),
        ('Outcome', nomination.route_reason+' Next owner: '+nomination.next_owner),
    ]

def offline_answer(nomination, question, review=None):
    if question not in QUESTIONS:
        raise ValueError('Only the listed offline example questions are supported.')
    review=current_review(nomination,review)
    review_text=('No human decision is recorded for this exact proposal.' if review is None else
        'The session rehearsal is deferred; resolve the reviewer’s concern before commitment.' if review.decision=='DEFER' else
        'A session-only scoped approval is recorded; it does not authorize an actual experiment.')
    if question==QUESTIONS[0]:
        if nomination.cell_state:
            c=next(c for c in nomination.comparisons if c['cell_state']==nomination.cell_state)
            text=f"The illustrative comparison nominates {nomination.cell_state}: {c['donors_above_comparators']} of {c['donors']} evaluation donors exceed both comparators. This is a model-representation comparison, not a demonstrated biological benefit. "
        else:
            text='No supported predictive nomination is available. '+nomination.challenge+' '
        text+=nomination.route_reason+' '+review_text
        if review and review.decision=='DEFER': text+=' Reviewer concern: '+review.rationale
        elif nomination.proposed_test: text+=' Proposal for review: '+nomination.proposed_test
        else:text+=' Required follow-up: '+nomination.request
        sources=['Current comparisons','Route prerequisites','Current session review binding']
    elif question==QUESTIONS[1]:
        text='The orchestrator routes the next permitted action: '+nomination.request+' The deterministic verifier checks context/model eligibility, donor comparisons and route prerequisites. '+nomination.route_reason+' This replay does not run an LLM orchestrator or an independent scientific verifier; the challenger commentary is scripted.'
        sources=['Current workflow events','Current prerequisites']
    elif question==QUESTIONS[2]:
        text=nomination.challenge+' Biology must judge the experiment, patient-to-culture match and unresolved mechanism; the project owner agrees resources. '+review_text+' Neither the fixed verifier nor this explanation validates the target.'
        sources=['Current challenger commentary','Evidence boundaries','Current session review binding']
    elif question==QUESTIONS[3]:
        text='Parallel biology needs independent scientific rationale plus assay readiness, decision value and resources. It does not turn an unavailable patient-cell prediction into a nomination. '+nomination.independent_rationale.basis+' Shared prerequisites: '+', '.join(g.name+(' — met' if g.met else ' — missing') for g in nomination.prerequisites)+'. The displayed route remains '+nomination.route+'; selecting this question does not change it or grant approval.'
        sources=[nomination.independent_rationale.evidence_id]+[g.evidence_id for g in nomination.prerequisites]
    else:
        text='No. This panel only formats answers to five predefined questions from the current proposal. It cannot call models, search the web, execute code, edit evidence, record reviews, send handoffs or approve experiments. It does not read the original assay assessment. Free-text live chat is not enabled here.'
        sources=['Offline explainer capability boundary']
    return {'question':question,'answer':text,'sources':sources,'binding':nomination.binding,
            'study_id':nomination.study_id,'scenario_id':nomination.scenario_id,'route':nomination.route,
            'mode':'scripted_offline_example'}
