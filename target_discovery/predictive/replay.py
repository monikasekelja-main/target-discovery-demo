"""Pure offline replay. Numbers and records are invented; no service is called."""
import hashlib
import json
from pathlib import Path
from statistics import mean
from .contracts import Study, Scenario, Nomination, Event, Review
from target_discovery.paths import PROJECT_ROOT

ENGINE_VERSION = 'predictive-replay-v2'
REQUIRED_GATES = {'Scoped scientific rationale','Assay readiness','Decision value','Resources allocated'}

def load_examples(root: Path = PROJECT_ROOT):
    study = Study.model_validate_json((root/'predictive_examples/study.json').read_text())
    scenarios = [Scenario.model_validate(x) for x in json.loads((root/'predictive_examples/scenarios.json').read_text())]
    if len({s.id for s in scenarios}) != len(scenarios):
        raise ValueError('Scenario identifiers must be unique')
    return study, scenarios

def compare(observation, heldout_ids):
    shifts = list(observation.donor_shifts.values())
    reference = max(observation.simple_baseline,observation.control_shift)
    valid = len(shifts)>=2 and set(observation.donor_shifts)==set(heldout_ids)
    average = mean(shifts) if shifts else 0
    loo = [mean(shifts[:i]+shifts[i+1:]) for i in range(len(shifts))] if len(shifts)>1 else []
    # Illustrative ranking rule, not a calibrated scientific acceptance threshold.
    eligible = valid and observation.identity_preserved and all(v>reference for v in shifts)
    return {'evidence_id':observation.evidence_id,'cell_state':observation.cell_state,
        'donor_shifts':observation.donor_shifts,'mean_shift':round(average,3),
        'baseline':observation.simple_baseline,'control':observation.control_shift,
        'donors_above_comparators':sum(v>reference for v in shifts),'donors':len(shifts),
        'leave_one_out_min':round(min(loo),3) if loo else None,
        'identity_preserved':observation.identity_preserved,'eligible':eligible}

def replay(study: Study, scenario: Scenario, route: str, incorporate_feedback=False) -> Nomination:
    if route not in ('after_prediction','parallel'): raise ValueError('Unknown route')
    events=[]
    def event(check,finding,action,owner):
        events.append(Event(check=check,finding=finding,action=action,owner=owner))
    event('Evidence boundary','All study results and supporting records are invented','Replay only; no patient study or model executed.','Workflow owner')
    split_valid = (len(study.adaptation.evaluation_donors)>=2 and
        not set(study.adaptation.development_donors)&set(study.adaptation.evaluation_donors) and
        set(study.adaptation.development_donors+study.adaptation.evaluation_donors)<=set(study.dataset.donor_ids))
    blocked = not split_valid or scenario.data_status!='ready' or scenario.model_status=='unsupported' or scenario.timeout
    comparisons=[] if blocked else [compare(o,study.adaptation.evaluation_donors) for o in scenario.observations]
    candidates=sorted((c for c in comparisons if c['eligible']),key=lambda c:c['mean_shift'],reverse=True)
    status='blocked' if blocked else 'exploratory' if scenario.model_status=='unvalidated' else 'unresolved'
    if not blocked and scenario.model_status=='supported' and candidates and not scenario.conflict:
        status='supported_for_review'
    if not split_valid: event('Donor split','Invalid or overlapping split','Resolve the split before comparison.','Analysis lead')
    event('Context', 'Missing subtype annotation' if scenario.data_status!='ready' else 'Context eligibility assumed in this illustrative scenario',
        'Pause dependent prediction; request source and mapping review.' if scenario.data_status!='ready' else 'Retain source, mapping version and reviewer before real execution.','Data steward')
    event('Model suitability',scenario.model_status,'Exploration only unless intended-use evidence and operation compatibility are established.','Predictive-model specialist')
    if scenario.timeout:
        event('Service status','Simulated timeout; no completed job found','Check status before resubmission; one retry with the same input/key.','Platform service owner')
        event('Bounded retry','Simulated retry exhausted; no result','Stop and escalate, not a negative biological result.','Platform service owner')
    for c in comparisons:
        event('Donor and baseline comparison',f"{c['evidence_id']}: {c['donors_above_comparators']}/{c['donors']} donors above both comparators; leave-one-out minimum {c['leave_one_out_min']}",
            'Eligible for illustrative ranking.' if c['eligible'] else 'Retain uncertainty; inspect subgroup, controls and sensitivity.','Analysis lead')
    if scenario.conflict:
        event('Contradictory evidence','SIM-F01: no functional effect despite target reduction; SIM-P01: positive representation shift','Preserve both; biological contexts and endpoints differ.','Biology reviewer')
    event('Contextual follow-up',scenario.challenge,scenario.request,scenario.request_owner)
    names=[p.name for p in scenario.prerequisites]
    complete=set(names)==REQUIRED_GATES and len(names)==len(REQUIRED_GATES)
    missing=[p.name for p in scenario.prerequisites if not p.met]
    if not complete: missing.append('Complete, unique prerequisite record')
    scientific_route=status=='supported_for_review' if route=='after_prediction' else scenario.independent_rationale.met
    eligible=scientific_route and not missing
    if missing: reason='Resolve before either route can be approved: '+', '.join(missing)+'.'
    elif not scientific_route: reason='No supported predictive nomination; resolve the follow-up first.' if route=='after_prediction' else 'Independent scientific rationale is missing; parallel biology is not justified.'
    else: reason='Ready for scoped human review on predictive support.' if route=='after_prediction' else 'Independent fictional evidence supports a cultured-CD4 test; this does not infer a patient-cell nomination.'
    intervention='Test expression reduction; the model operation is a representation perturbation, not calibrated knockdown' if status=='supported_for_review' else None
    state=candidates[0]['cell_state'] if status=='supported_for_review' else None
    proposed=None
    if scientific_route:
        proposed=('Scope reduction testing in a CD4 culture matched as closely as feasible to the nominated state.' if route=='after_prediction' else 'Scope a cultured-CD4 reduction test on SIM-E01, independently of unresolved patient-cell prediction.')
    specialist={'request_id':scenario.id+'-SIM-H01','status':'NEEDS_INFORMATION','evidence_status':'scripted_offline_example',
        'question':'Could antibody blockade test the expression-reduction hypothesis?',
        'response':'Expression reduction does not demonstrate blockade equivalence. Establish native surface binding and target engagement in the proposed culture before interpreting a blockade arm.',
        'owner':'Antibody specialist with biology assay lead','effort':'A scoped feasibility review; specialists must estimate experimental effort.',
        'before':'Scope CD4 reduction testing; antibody feasibility remains an open question.',
        'after':'First scope native-target binding and engagement controls; retain reduction testing and defer a blockade-effect claim.',
        'scientific_limit':'No blockade equivalence or target validation established.'}
    if incorporate_feedback and proposed: proposed += ' '+specialist['after']
    followup=scenario.request if split_valid else 'Analysis lead: correct overlapping or invalid donor splits before any predictive comparison.'
    next_action=proposed if eligible else ('Resolve prerequisites: '+', '.join(missing) if missing else followup)
    next_owner='Biology reviewer and project owner' if eligible or missing else (scenario.request_owner if split_valid else 'Analysis lead')
    event('Route to biology',reason,next_action,next_owner)
    payload=dict(study_id=study.study_id,scenario_id=scenario.id,evidence_status=study.evidence_status,status=status,
        target=study.target,intervention=intervention,cell_state=state,comparisons=comparisons,
        prerequisites=scenario.prerequisites,independent_rationale=scenario.independent_rationale,
        proposed_test=proposed,next_action=next_action,next_owner=next_owner,challenge=scenario.challenge,request=followup,
        specialist=specialist,feedback_incorporated=bool(incorporate_feedback and proposed),reason=scenario.summary,
        limitations=study.boundaries,events=events,route=route,route_eligible=eligible,route_reason=reason,binding='pending')
    nomination=Nomination(**payload)
    binding=hashlib.sha256(json.dumps({'engine':ENGINE_VERSION,'study':study.model_dump(),'scenario':scenario.model_dump(),'nomination':nomination.model_dump()},sort_keys=True).encode()).hexdigest()
    return nomination.model_copy(update={'binding':binding})

def review_nomination(nomination, decision, rationale):
    if decision=='APPROVE_SCOPED_TEST' and not nomination.route_eligible:
        raise ValueError('This route is not eligible for approval. Resolve prerequisites or consider a justified parallel route.')
    if len(rationale.strip())<12: raise ValueError('Please explain the scope and reason in at least 12 characters. This is a completeness check, not a semantic review.')
    return Review(binding=nomination.binding,decision=decision,rationale=rationale.strip())

def current_review(nomination, review):
    return review if review is not None and review.binding==nomination.binding else None

def require_real_execution(*args,**kwargs):
    raise RuntimeError('Real execution is unavailable: DEMO-R1 is fictional and this study has not been run.')
