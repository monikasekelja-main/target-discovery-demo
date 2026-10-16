"""Fixed, inspectable reference rules for ONE synthetic hypothesis; not an agent.

Recommendations use computed measurements and policy, never experiment IDs,
evaluation labels, expected answers or hand-authored reference briefs.
"""
from contracts import DecisionBrief


def evidence_checks(records):
    groups={}
    findings=[]
    for record in records:
        eid=record['evidence_id'];raw=record['raw_record']
        groups.setdefault(record['evidence_family_id'],[]).append(eid)
        if record['entity_status']=='UNRESOLVED':
            findings.append({'evidence_id':eid,'issue':'unresolved_entity','effect':'Exclude from mapped target support.'})
        if raw.get('duplicate_of'):
            findings.append({'evidence_id':eid,'issue':'duplicate','effect':f"No independent support beyond {raw['duplicate_of']}."})
        if record['record_type']=='secondary_summary':
            findings.append({'evidence_id':eid,'issue':'unsupported_causal_summary',
                'effect':'Locus association does not establish the claimed gene causality or inhibition benefit.'})
        if record['record_type']=='incomplete_record':
            findings.append({'evidence_id':eid,'issue':'missing_context_and_endpoint',
                'effect':'Do not fill missing evidence context from the application study manifest.'})
        if record['context_id']=='CTX-CD4-REST':
            findings.append({'evidence_id':eid,'issue':'related_context_only',
                'effect':'Resting-cell evidence is not direct stimulated functional-effect evidence.'})
    return {'mode':'deterministic_reference_checks','evidence_families':groups,'findings':findings,
            'limitations':['Rules cover this curated case; they are not an LLM scientific challenger or general claim verifier.']}


def route_result(result):
    if any(g.startswith(('G0:','G1:','G2:','G3:')) for g in result['failed_gates']):
        return 'SCHEMA_OR_QC_REVIEW'
    if result['proposed_action']=='INCONCLUSIVE':
        return 'BIOLOGY_UNRESOLVED'
    return 'READY_FOR_BIOLOGY_REVIEW'


def compile_brief(*, assessment_id, evidence, manifest, prediction, policy, registry_version,
                  alias_version, input_hashes, implementation_version, result=None, experiment=None):
    available={r['evidence_id'] for r in evidence['records']}
    needed={'E01','E02','E03','E04','E06','E07','E09','E10','E11','E12','E13','E14','E15','E16'}
    if not needed <= available:
        raise ValueError('This reference compiler requires the complete curated evidence case; abstain on missing records')
    minimum=policy['minimum_useful_reduction_pct']
    state='READY_FOR_BIOLOGY_REVIEW' if result is None else route_result(result)
    action='EXPERIMENT_TO_RESOLVE_UNCERTAINTY' if result is None else result['proposed_action']
    grade=1
    if result is None:
        rationale=('Application context metadata is resolved. The eligible frozen signature response suggests a functional test; '
                   'it does not establish functional benefit. Gene assignment, genetic direction and the earlier cell-loss confound remain unresolved.')
        next_action='Propose OPT-FUNCTION after bounded evidence review; agree feasibility and assay policy with biology.'
    elif action=='ADVANCE_TO_REPLICATION':
        grade=2
        rationale=(f'Both methods meet the predefined {minimum:g}% useful functional-effect criterion with intact prerequisites. '
                   'The methods use the same donors; this is not independent cohort replication.')
        next_action='Propose new-donor/batch replication and target-specificity work; open a conditional specialist feasibility discussion.'
    elif action=='DEPRIORITIZE_TESTED_HYPOTHESIS':
        grade=0
        rationale=(f'Both methods exclude the predefined {minimum:g}% useful mean effect at achieved expression reduction in this assay/context. '
                   'Small nonzero effects and other target hypotheses remain possible.')
        next_action='Propose deprioritizing this scoped useful-benefit hypothesis; preserve the disease-locus evidence and limitations.'
    elif result['failed_gates']:
        rationale='A prerequisite failed. Effect estimates are diagnostic only and cannot justify the intended functional conclusion. '
        if any(g.startswith('G4:') for g in result['failed_gates']):
            rationale+='Cell loss or viability/recovery concerns confound benefit. '
        rationale+='Retain the exact failed gates for review.'
        next_action=('Review the failed context, input, assay-control or achieved-perturbation requirement with the data owner and biology.'
                     if state=='SCHEMA_OR_QC_REVIEW' else
                     'Investigate cell loss and on-target, off-target or delivery explanations with biology.')
    else:
        intervals=[s['functional_reduction_pct'] for s in result['statistics'].values()]
        discordant=any(s['lower_95']>=minimum for s in intervals) and any(s['upper_95']<minimum for s in intervals)
        rationale=('Methods disagree about a useful effect; averaging them would hide this contradiction.' if discordant else
                   'Effect intervals span useful and insufficient effects; the functional hypothesis remains unresolved.')
        next_action=('Resolve method disagreement and specificity with biology.' if discordant else
                     'Investigate donor variability and agree a prospective precision plan; do not select responders retrospectively.')
    exp_id=experiment['experiment_id'] if experiment else None
    excluded={'E06':'Historical resting-cell signature prediction; not a stimulated functional-effect prediction.',
        'E13':'Causal/inhibition-benefit overclaim is unsupported by the cited locus association.',
        'E14':'Duplicate of E01; no independent support.','E15':'Unresolved entity; do not map automatically.',
        'E16':'Cell context, endpoint and denominator remain unknown.',
        prediction['output_id']:'Frozen signature response; no measured predictive accuracy or functional-benefit claim.'}
    if result and not result['prerequisites_passed']:
        excluded[exp_id]='Prerequisite failure; estimates are diagnostic and cannot provide direct functional support.'
    supporting=['E01','E02','E03','E04']
    if result is None: supporting.append(prediction['output_id'])
    elif action=='ADVANCE_TO_REPLICATION': supporting.append(exp_id)
    challenging=['E07','E09','E10']
    if exp_id and action!='ADVANCE_TO_REPLICATION': challenging.append(exp_id)
    uncertainties=['Gene assignment and genetic direction remain unresolved.',
        'Systemic and tissue safety remain unassessed.',
        'Expression reduction is not established to be equivalent to receptor blockade.',
        'Relevant-cell delivery, isoform coverage and modality feasibility require specialist assessment.']
    if action=='ADVANCE_TO_REPLICATION': uncertainties.append('Independent replication and specificity remain unestablished.')
    brief={'synthetic':True,'assessment_id':assessment_id,'author_mode':'deterministic_reference',
        'hypothesis_id':'HYP-DEMO-R1-001','target_id':manifest['target_id'],'context_id':manifest['context']['context_id'],
        'hypothesis':f'Partial expression reduction produces at least {minimum:g}% relative reduction in the live-cell IL-17A-positive fraction while preserving cells in the specified stimulated context.',
        'intervention':policy['context']['intervention'],
        'versions':{'evidence_snapshot_id':evidence['evidence_snapshot_id']+('+'+experiment['evidence_version'] if experiment else ''),
            'metadata_snapshot_id':manifest['snapshot_id'],'model_output_ids':[prediction['output_id']],
            'model_versions':{prediction['model_id']:prediction['model_version'],'historical_E06':'synthetic-model-v1'},
            'policy_version':policy['policy_version'],'registry_version':registry_version,'alias_mapping_version':alias_version,
            'prompt_version':implementation_version,'contract_version':'tools-v1','input_content_sha256':input_hashes},
        'workflow_status':state,'scientific_recommendation':action,'rationale':rationale,
        'supporting_evidence_ids':supporting,'challenging_evidence_ids':challenging,'excluded_or_limited_evidence':excluded,
        'functional_effects':{} if result is None else {a:s['functional_reduction_pct'] for a,s in result['statistics'].items()},
        'functional_effect_units':'relative_percent_reduction','prerequisites_passed':None if result is None else result['prerequisites_passed'],
        'failed_gates':[] if result is None else result['failed_gates'],
        'confidence':{'rubric_version':'ordinal-rubric-v1','interpretation':'proposed_ordinal_support_not_probability',
            'causal':{'ordinal':1,'status':'ASSESSED','scope':'gene-to-disease causal hypothesis',
                     'rationale':'Suggestive locus evidence; gene assignment and genetic direction remain unresolved.',
                     'evidence_ids':['E01','E02','E03']},
            'intervention':{'ordinal':grade,'status':'ASSESSED','scope':f'{minimum:g}% useful functional effect of expression reduction in this tested context',
                'rationale':rationale,'evidence_ids':[exp_id] if exp_id else ['E07',prediction['output_id']]},
            'modality_feasibility':{'antibody':'conditional','small_molecule':'unknown','oligonucleotide':'conditional'},
            'systemic_safety':'unassessed'},
        'remaining_uncertainties':uncertainties,'next_action':next_action,
        'next_owner_role':'biology assay lead / data owner' if state=='SCHEMA_OR_QC_REVIEW' else 'biology reviewer',
        'human_review_required':True}
    citations=set(supporting+challenging+list(excluded))
    if not citations <= available | {prediction['output_id']} | ({exp_id} if exp_id else set()):
        raise ValueError('Compiler produced a citation outside the current evidence snapshot')
    return DecisionBrief.model_validate(brief)


def render_brief(brief):
    b=brief.model_dump(mode='json') if isinstance(brief,DecisionBrief) else brief
    lines=[f"# {b['assessment_id']} — synthetic target decision",'',
        '**All target-specific evidence is invented. This is a local demonstration.**','',
        f"Proposal: **{b['scientific_recommendation']}**",'',
        f"Workflow status: {b['workflow_status']} · Author: {b['author_mode']}",'',
        b['hypothesis'],'',b['rationale'],'',f"Next action: {b['next_action']}",'',
        f"Owner: {b['next_owner_role']} · Biology review required.",'',
        f"Support grades: causal {b['confidence']['causal']['ordinal']}/3; intervention {b['confidence']['intervention']['ordinal']}/3. Ordinal categories, not probabilities.",'']
    if b['functional_effects']:
        lines+=['| Method | Relative reduction | 95% interval | Donors |',
                '|---|---|---|---|']
        for method,s in b['functional_effects'].items():
            lines.append(f"| {method} | {s['mean']:.1f}% | {s['lower_95']:.1f}–{s['upper_95']:.1f}% | {s['n_donors']} |")
        lines+=['','Both methods use the same donors; not independent cohort replication.']
        if not b['prerequisites_passed']: lines+=['','**Prerequisites failed: these estimates are diagnostic only.**']
    if b['failed_gates']: lines+=['','Failed gates:','']+[f'- {x}' for x in b['failed_gates']]
    lines+=['','Remaining uncertainty:','']+[f'- {x}' for x in b['remaining_uncertainties']]
    lines+=['','Supporting source IDs: '+', '.join(b['supporting_evidence_ids']),
            'Challenging source IDs: '+', '.join(b['challenging_evidence_ids']),'',
            'Limited or excluded evidence:','']+[f'- {k}: {v}' for k,v in b['excluded_or_limited_evidence'].items()]
    lines+=['','Versions:','', '```json', __import__('json').dumps(b['versions'],indent=2), '```','']
    return '\n'.join(lines)
