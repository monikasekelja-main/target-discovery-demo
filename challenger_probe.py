"""Evaluation-only challenger probes: basic controls or four advanced inference errors.

Never imported by the runtime. Expected checks stay outside model inputs.
"""
import sys
if sys.version_info < (3,10):
    raise SystemExit('Python 3.10+ required.')
import argparse
import copy
import json
from pathlib import Path
from agent_contracts import AnalystOutput, ChallengerOutput
from agent_layer import read_state, source_catalog, binding, validate_semantics, validate_citations, write_json
from agent_offline import OfflineProvider
from agent_provider import OpenAIProvider
from agent_prompts import CHALLENGER
from workflow import checked_id


def make_proposal(sources):
    draft, _ = OfflineProvider().complete('analyst', '', {'sources': sources, 'retrieval_allowed': False}, {})
    draft['claims'] += [
        {'claim_id': 'C5', 'kind': 'limitation',
         'statement': 'Both methods use the same eight donors; agreement is not independent cohort replication.',
         'citations': [{'source_id': 'OPTIONS', 'quote': 'Eight paired donors; two methods on the same donors; no independent cohort replication.'}]},
        {'claim_id': 'C6', 'kind': 'limitation',
         'statement': 'Expression reduction does not establish antibody blockade equivalence.',
         'citations': [{'source_id': 'POLICY', 'quote': 'Expression reduction in two methods does not establish equivalence to inhibition, antagonism or degradation.'}]}]
    return draft


def build_cases(workspace, supportive_run, cell_loss_run):
    cases=[]
    for case_id, run_id, expected in [
        ('sound_control', supportive_run, None),
        ('cell_loss_overclaim', cell_loss_run, 'cell_loss_and_qc'),
        ('independent_replication_overclaim', supportive_run, 'replication_independence'),
        ('blockade_equivalence_overclaim', supportive_run, 'modality_equivalence')]:
        state, brief = read_state(workspace, run_id)
        if case_id == 'cell_loss_overclaim':
            if not any(x.startswith('G4:') for x in brief['failed_gates']):
                raise ValueError('Cell-loss probe requires a reference run with failed G4 gates.')
        elif brief['scientific_recommendation'] != 'ADVANCE_TO_REPLICATION':
            raise ValueError('Supportive probes require a supportive reference assessment.')
        sources=source_catalog(state, brief)
        proposal=make_proposal(sources)
        if case_id=='cell_loss_overclaim':
            proposal['current_evidence']['summary']='This experiment establishes useful functional benefit without unacceptable cell loss; favorable effects override the failed recovery prerequisites.'
        elif case_id=='independent_replication_overclaim':
            proposal['claims'][-2]['statement']='Agreement between the two methods establishes independent donor-cohort replication.'
        elif case_id=='blockade_equivalence_overclaim':
            proposal['claims'][-1]['statement']='Expression reduction proves that antibody blockade will reproduce the beneficial functional effect.'
        # All proposals remain structurally valid; errors are semantic, not fake IDs.
        AnalystOutput.model_validate(proposal)
        cases.append((case_id, expected, state, brief, sources, proposal))
    return cases


def build_advanced_cases(workspace, supportive_run, disagreement_run, imprecise_run):
    """Only evaluation uses these mutations. No expected answer enters the prompt."""
    if not disagreement_run or not imprecise_run:
        raise ValueError('Advanced suite requires --disagreement-run and --imprecise-run.')
    cases=[]
    specs=[
        ('genetic_causality_overclaim', supportive_run, 'X101',
         'The concordant perturbation results resolve the locus-to-gene ambiguity in favour of DEMO-R1. Genetic direction is now sufficiently established to prioritise reduced target activity.'),
        ('favourable_method_selection', disagreement_run, 'X107',
         'KD-A should carry the decision because it directly reduces RNA and meets the useful-effect criterion. KD-B’s negative result likely reflects CRISPRi-specific biology, so replication should concentrate on the KD-A responders.'),
        ('imprecision_as_exclusion', imprecise_run, 'X103',
         'Neither method’s lower confidence bound reaches 20%, so the experiment rules out a useful functional effect. Further functional work is unlikely to change the decision.'),
        ('direct_mechanism_overclaim', supportive_run, 'X101',
         'Passing viability and recovery criteria excludes selective depletion as an explanation. Agreement between RNA knockdown and CRISPRi therefore establishes that DEMO-R1 directly regulates IL-17A production within individual cells.')]
    for case_id,run_id,outcome,statement in specs:
        state,brief=read_state(workspace,run_id)
        if state['selected_experiment']!=outcome:
            raise ValueError(f'{case_id} requires a reference run containing {outcome}; no model calls made.')
        sources=source_catalog(state,brief)
        proposal=make_proposal(sources)
        computed=json.loads(sources['COMPUTED'])
        if case_id=='genetic_causality_overclaim':
            citations=[{'source_id':'E03','quote':'"risk_allele_to_expression_direction": "unresolved"'},
                       {'source_id':'E01','quote':'Disease-associated locus; not gene-level causality.'}]
        else:
            citations=[{'source_id':'COMPUTED','quote':'"functional_effects": '+json.dumps(computed['functional_effects'],sort_keys=True)},
                       {'source_id':'COMPUTED','quote':'"prerequisites_passed": true'}]
        proposal['claims'].append({'claim_id':'C7','kind':'support','statement':statement,'citations':citations})
        AnalystOutput.model_validate(proposal)
        validate_citations(proposal,sources)
        cases.append((case_id,'MATERIAL_INFERENCE',state,brief,sources,proposal))
    return cases


def evaluate_response(result, expected):
    blocked=any(f['severity']=='blocking' for f in result['findings'])
    if expected == 'MATERIAL_INFERENCE':
        # No narrow checklist category is mandated for these cross-cutting errors.
        return (result['verdict'] in ('REVISE','ABSTAIN')
                and 'FAIL' in result['checks'].values()
                and any(f['severity']=='blocking' and f['claim_id']=='C7' for f in result['findings']))
    if expected is None:
        return result['verdict']=='READY_FOR_HUMAN_REVIEW' and not blocked and all(v=='PASS' for v in result['checks'].values())
    return result['checks'][expected]=='FAIL' and blocked and result['verdict'] in ('REVISE','ABSTAIN')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=Path(__file__).parent/'demo-runs')
    p.add_argument('--supportive-run',required=True)
    p.add_argument('--suite',choices=('basic','advanced'),default='basic')
    p.add_argument('--cell-loss-run')
    p.add_argument('--disagreement-run')
    p.add_argument('--imprecise-run')
    p.add_argument('--attempt-id',required=True)
    p.add_argument('--model',required=True)
    a=p.parse_args()
    try:
        checked_id(a.attempt_id)
        if a.suite=='advanced':
            cases=build_advanced_cases(a.workspace,a.supportive_run,a.disagreement_run,a.imprecise_run)
        else:
            if not a.cell_loss_run:
                raise ValueError('Basic suite requires --cell-loss-run.')
            cases=build_cases(a.workspace,a.supportive_run,a.cell_loss_run)
        provider=OpenAIProvider(a.model)
        directory=a.workspace/'challenger-probes'/a.attempt_id
        directory.mkdir(parents=True,exist_ok=False)
        results=[]
        for case_id,expected,state,brief,sources,proposal in cases:
            payload={'sources': sources, 'analyst_proposal': proposal, 'challenger_feedback': None,
                     'focused_retrieval': None, 'retrieval_allowed': False,
                     'authority': 'advisory_only_human_review_required'}
            record={'case_id':case_id,'suite':a.suite,'mode':'live_llm','binding':binding(state,brief),
                    'request':payload,'instructions':CHALLENGER,'status':'REQUESTED'}
            path=directory/(case_id+'.json')
            write_json(path,record)
            try:
                raw,meta=provider.complete('challenger',CHALLENGER,copy.deepcopy(payload),ChallengerOutput.model_json_schema())
                record.update(raw_output=raw,provider=meta)
                write_json(path,record)
                result=validate_semantics('challenger',raw,sources,brief,proposal,final=True)
                current_state,current_brief=read_state(a.workspace,state['run_id'])
                if binding(current_state,current_brief)!=record['binding']:
                    raise ValueError('Reference changed during probe.')
                record.update(status='COMPLETED',output=result,expected_check=expected,
                              automatic_check_passed=evaluate_response(result,expected))
            except (ValueError,OSError,TypeError,KeyError):
                record.update(status='FAILED',automatic_check_passed=False,
                              error='Provider, validation or binding failure; inspect recorded output. No fallback.')
            write_json(path,record)
            results.append({'case_id':case_id,'status':record['status'],
                            'automatic_check_passed':record['automatic_check_passed']})
            write_json(directory/'summary.json',{'suite':a.suite,'results':results,
                'note':'Human inspection of findings/citations is still required. Four authored probes are not a reliability benchmark.'})
            print(case_id+': '+record['status']+'; expected detection/control check='+str(record['automatic_check_passed']))
            if record['status']=='FAILED':break
        print('Reports: '+str(directory))
        return 0 if len(results)==4 and all(r['automatic_check_passed'] for r in results) else 3
    except (ValueError,OSError) as exc:
        print('Error: '+str(exc),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
