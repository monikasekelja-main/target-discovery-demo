"""Bounded advisory roles, layered over immutable reference assessments.

The baseline database is read only. An exclusive per-attempt directory records
inputs, outputs, requests and errors. No agent result is an approval or mutation.
"""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

from pydantic import ValidationError
from target_discovery.agents.agent_contracts import AnalystOutput, ChallengerOutput
from target_discovery.agents.agent_prompts import VERSION, ANALYST, CHALLENGER
from target_discovery.agents.agent_provider import ProviderError
from target_discovery.workflow.contracts import content_fingerprint, DecisionBrief
from target_discovery.workflow.local_tools import LocalTools
from target_discovery.workflow.workflow import PACKAGE, BASE_INPUTS, IMPLEMENTATION_FILES, checked_id

AGENT_FILES = ('target_discovery/paths.py','target_discovery/agents/agent_contracts.py', 'target_discovery/agents/agent_prompts.py', 'target_discovery/agents/agent_provider.py',
               'target_discovery/agents/agent_layer.py', 'target_discovery/cli/agent_demo.py', 'target_discovery/agents/agent_offline.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_text().encode()).hexdigest()


def read_state(workspace, run_id, root=PACKAGE):
    checked_id(run_id)
    database = Path(workspace).resolve() / 'workflow.sqlite3'
    if not database.is_file():
        raise ValueError('No reference database. Run demo.py start and resume first.')
    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
        db.execute('BEGIN')
        row = db.execute('SELECT state FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown reference run.')
        state = json.loads(row[0])
        aid = state['current_assessment_id']
        if not aid:
            raise ValueError('No complete reference assessment. Resolve metadata/blockers first.')
        brief = json.loads(db.execute('SELECT brief FROM assessments WHERE run_id=? AND assessment_id=?',
                                      (run_id, aid)).fetchone()[0])
    allowed = set(BASE_INPUTS)
    if state['selected_experiment']:
        allowed.add(f"runtime/experiments/{state['selected_experiment']}.json")
    if set(state['snapshots']) != allowed:
        raise ValueError('Unexpected snapshot scope; alternative outcomes are forbidden.')
    for relative, source in state['snapshots'].items():
        if hashlib.sha256(source['text'].encode()).hexdigest() != source['sha256']:
            raise ValueError('Snapshot integrity failure.')
        if file_hash(Path(root)/relative) != source['sha256']:
            raise ValueError('Stale reference inputs. Refresh and reassess using demo.py.')
    expected = {'implementation/'+p: file_hash(PACKAGE/p) for p in IMPLEMENTATION_FILES}
    if expected != state['implementation_sha256']:
        raise ValueError('Stale reference implementation. Refresh and reassess using demo.py.')
    DecisionBrief.model_validate(brief)
    return state, brief


def binding(state, brief):
    return {'run_id': state['run_id'], 'revision': state['revision'],
            'assessment_id': brief['assessment_id'], 'assessment_sha256': content_fingerprint(DecisionBrief.model_validate(brief)),
            'input_hashes': {p: x['sha256'] for p, x in state['snapshots'].items()},
            'reference_implementation': state['implementation_sha256'],
            'agent_implementation': {p: file_hash(PACKAGE/p) for p in AGENT_FILES},
            'prompt_version': VERSION}


def source_catalog(state, brief):
    # No compiled narrative, expected answer, other outcome or example is exposed.
    sources = {r['evidence_id']: r for r in state['evidence']['records']}
    sources['MANIFEST'] = state['manifest']
    sources['PREDICTION'] = state['prediction']
    sources['OPTIONS'] = state['options']
    sources['POLICY'] = json.loads(state['snapshots']['runtime/policy.json']['text'])
    sources['RUBRIC'] = json.loads(state['snapshots']['runtime/confidence_rubric.json']['text'])
    sources['COMPUTED'] = {k: brief[k] for k in ('functional_effects', 'functional_effect_units',
                                              'prerequisites_passed', 'failed_gates')}
    # This is the fixed eligibility constraint, NOT an agent performance label.
    sources['COMPUTED']['eligible_action'] = brief['scientific_recommendation']
    if state['selected_experiment']:
        sources[state['selected_experiment']] = json.loads(
            state['snapshots'][f"runtime/experiments/{state['selected_experiment']}.json"]['text'])
    return {key: canonical(value) for key, value in sources.items()}


def evidence_status(action):
    return {'EXPERIMENT_TO_RESOLVE_UNCERTAINTY': 'UNTESTED',
            'ADVANCE_TO_REPLICATION': 'SUPPORTED_IN_THIS_EXPERIMENT',
            'DEPRIORITIZE_TESTED_HYPOTHESIS': 'USEFUL_EFFECT_EXCLUDED',
            'INCONCLUSIVE': 'UNRESOLVED'}[action]


def validate_citations(output, sources):
    groups = list(output.get('claims', output.get('findings', [])))
    if 'current_evidence' in output:
        groups.append(output['current_evidence'])
    for group in groups:
        for citation in group['citations']:
            source = sources.get(citation['source_id'])
            if source is None or citation['quote'] not in source:
                raise ValueError('Unknown source or non-verbatim quote; advisory output rejected.')


def validate_semantics(role, output, sources, brief, analyst=None, final=False):
    model = AnalystOutput if role == 'analyst' else ChallengerOutput
    parsed = model.model_validate(output).model_dump(mode='json')
    validate_citations(parsed, sources)
    if final and parsed['retrieval'] is not None:
        raise ValueError('Retrieval budget exhausted; further requests are rejected.')
    if parsed['retrieval']:
        ids = parsed['retrieval']['evidence_ids']
        if len(ids) != len(set(ids)) or any(not eid.startswith('E') or eid not in sources for eid in ids):
            raise ValueError('Retrieval must reference unique captured evidence IDs.')
    if role == 'analyst':
        if not parsed['hypothesis_under_test'].strip().endswith('?'):
            raise ValueError('Hypothesis under test must be a question, not an asserted finding.')
        expected = evidence_status(brief['scientific_recommendation'])
        if parsed['current_evidence']['status'] != expected:
            raise ValueError('Current evidence status conflicts with fixed experimental eligibility.')
        ids = [c['claim_id'] for c in parsed['claims']]
        if len(ids) != len(set(ids)):
            raise ValueError('Claim IDs must be unique.')
        options = {o['option_id'] for o in json.loads(sources['OPTIONS'])['options']}
        if brief['functional_effects']:
            if parsed['experiment_option_id'] is not None:
                raise ValueError('Post-result recommendations must not reuse an initial-study option.')
        elif parsed['experiment_option_id'] not in options:
            raise ValueError('Initial recommendation must select an available experiment concept.')
    else:
        ids = {c['claim_id'] for c in analyst['claims']}
        if any(f['claim_id'] is not None and f['claim_id'] not in ids for f in parsed['findings']):
            raise ValueError('Challenger references a nonexistent analyst claim.')
        blocking = any(f['severity'] == 'blocking' for f in parsed['findings'])
        if 'FAIL' in parsed['checks'].values() and not blocking:
            raise ValueError('A failed consistency check requires a blocking finding.')
        if parsed['verdict'] == 'READY_FOR_HUMAN_REVIEW' and (blocking or parsed['retrieval']):
            raise ValueError('Challenger readiness contradicts blocking findings or pending retrieval.')
        if parsed['verdict'] == 'REVISE' and not (blocking or parsed['retrieval']):
            raise ValueError('Revision needs a blocking finding or concrete retrieval question.')
    return parsed


def write_json(path, data):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    temporary.replace(path)


def run_agents(workspace, run_id, attempt_id, provider, root=PACKAGE):
    checked_id(attempt_id)
    state, brief = read_state(workspace, run_id, root)
    bound = binding(state, brief)
    sources = source_catalog(state, brief)
    if len(canonical(sources).encode()) > 200_000:
        raise ValueError('Source packet exceeds the demo input budget.')
    directory = Path(workspace).resolve()/'agent-reports'/run_id/attempt_id
    directory.mkdir(parents=True, exist_ok=False)  # Never repeat a paid attempt implicitly.
    report = {'schema_version': 'agent-report-v2', 'synthetic_biology': True,
              'mode': provider.mode, 'requested_model': provider.model, 'binding': bound,
              'created_at': datetime.now(timezone.utc).isoformat(),
              'status': 'RUNNING', 'human_review_required': True, 'approval_effective': False,
              'reference_database_mutated': False, 'calls': [], 'retrievals': [],
              'analyst': None, 'challenger': None,
              'limitations': ['Citation checks establish source membership and exact quotation, not entailment.',
                             'Shared-model challenger is not independent biological validation.',
                             'Fixed numerical eligibility is supplied, so agreement is not a discovery-accuracy metric.',
                             'Report is advisory and is not incorporated into the reference assessment or approval.']}
    write_json(directory/'input.json', {'sources': sources, 'binding': bound})
    write_json(directory/'report.json', report)

    def call(role, *, analyst=None, critique=None, retrieved=None, final=False):
        if len(report['calls']) >= 5:
            raise ValueError('Maximum five model calls reached.')
        payload = {'sources': sources, 'analyst_proposal': analyst, 'challenger_feedback': critique,
                   'focused_retrieval': retrieved, 'retrieval_allowed': not final,
                   'authority': 'advisory_only_human_review_required'}
        schema_model = AnalystOutput if role == 'analyst' else ChallengerOutput
        instructions = ANALYST if role == 'analyst' else CHALLENGER
        entry = {'role': role, 'request': payload, 'instructions': instructions,
                 'schema': schema_model.model_json_schema(), 'status': 'REQUESTED'}
        report['calls'].append(entry)
        write_json(directory/'report.json', report)
        raw, metadata = provider.complete(role, instructions, copy.deepcopy(payload), entry['schema'])
        entry.update(raw_output=raw, provider=metadata, status='RECEIVED')
        write_json(directory/'report.json', report)
        accepted = validate_semantics(role, raw, sources, brief, analyst, final)
        entry.update(status='VALIDATED', output=accepted)
        write_json(directory/'report.json', report)
        return accepted

    def retrieve(role, proposal):
        request = proposal['retrieval']
        if not request:
            return None
        if any(r['role'] == role for r in report['retrievals']):
            raise ValueError('At most one retrieval per role.')
        args = {'contract_version': 'tools-v1', 'request_id': f'{attempt_id}-{role}',
                'idempotency_key': f'{run_id}-{attempt_id}-{role}',
                'target_id': state['target_id'],
                'evidence_snapshot_id': state['evidence']['evidence_snapshot_id'],
                'query': request['question'], 'evidence_ids': request['evidence_ids'],
                'include_unresolved_candidates': True}
        tools = LocalTools(lambda p: json.loads(state['snapshots'][p]['text']))
        result = tools.call('search_evidence', args)
        report['retrievals'].append({'role': role, 'tool': 'search_evidence', 'request': args, 'response': result})
        write_json(directory/'report.json', report)
        if result['status'] != 'OK':
            raise ValueError('Focused retrieval failed; no fabricated evidence or retry.')
        return result

    try:
        analyst = call('analyst')
        if analyst['retrieval']:
            analyst = call('analyst', analyst=analyst, retrieved=retrieve('analyst', analyst), final=True)
        report['analyst'] = analyst
        challenger = call('challenger', analyst=analyst)
        report['challenger'] = challenger
        if challenger['verdict'] == 'REVISE':
            retrieved = retrieve('challenger', challenger)
            analyst = call('analyst', analyst=analyst, critique=challenger, retrieved=retrieved, final=True)
            report['analyst'] = analyst
            challenger = call('challenger', analyst=analyst, final=True)
            report['challenger'] = challenger
        ready = challenger['verdict'] == 'READY_FOR_HUMAN_REVIEW'
        consistent = analyst['proposed_action'] == brief['scientific_recommendation']
        report['numerical_policy_consistent'] = consistent
        report['status'] = 'ADVISORY_READY_FOR_REVIEW' if ready and consistent else 'NEEDS_EXPERT_REVIEW'
        if not consistent:
            report['policy_conflict'] = {'fixed_eligible_action': brief['scientific_recommendation'],
                                         'agent_proposal': analyst['proposed_action']}
        current_state, current_brief = read_state(workspace, run_id, root)
        if binding(current_state, current_brief) != bound:
            report['status'] = 'STALE'
    except (ValueError, TypeError, KeyError, OSError) as exc:
        report['status'] = 'FAILED'
        # Validation error details can echo full untrusted model inputs; retain raw in trace, not stderr.
        report['error'] = ('Structured output validation failed.' if isinstance(exc, ValidationError)
                           else str(exc) if isinstance(exc, (ValueError, ProviderError)) else 'Execution failed.')
    finally:
        write_json(directory/'report.json', report)
        (directory/'report.md').write_text(render_report(report))
    return report, directory


def load_report(workspace, run_id, attempt_id, root=PACKAGE):
    checked_id(run_id); checked_id(attempt_id)
    path = Path(workspace)/'agent-reports'/run_id/attempt_id/'report.json'
    report = json.loads(path.read_text())
    try:
        state, brief = read_state(workspace, run_id, root)
        current = binding(state, brief) == report['binding']
    except (ValueError, OSError):
        current = False
    report['binding_current'] = current
    report['effective_status'] = report['status'] if current else 'STALE'
    return report


def render_report(report):
    lines = ['# Evidence analyst and challenger — synthetic demo', '',
             f"Mode: **{report['mode']}** · Status: **{report.get('effective_status', report['status'])}**", '',
             f"Bound to {report['binding']['assessment_id']} · Human review required · No approval granted.", '',
             'This is an advisory companion. It does not modify the reference decision brief.', '']
    if report.get('error'):
        lines += ['Error: '+report['error'], '']
    analyst = report.get('analyst')
    if analyst:
        lines += ['## Analyst', '', '### Hypothesis under test', '',
                  analyst.get('hypothesis_under_test', analyst.get('hypothesis', '')), '']
        if 'current_evidence' in analyst:
            current = analyst['current_evidence']
            lines += ['### Current evidence assessment', '', '**'+current['status']+'**', '', current['summary'], '']
            lines += ['- '+c['source_id']+': '+c['quote'] for c in current['citations']]
        else:
            lines += ['Legacy report: no separate evidence-assessment field; opening is not an established finding.', '']
        lines += ['', 'Proposal: '+analyst['proposed_action'],
                  '', analyst['next_step'], '']
        for c in analyst['claims']:
            lines += [f"- {c['claim_id']} ({c['kind']}): {c['statement']}"]
            for citation in c['citations']:
                lines += [f"  - {citation['source_id']}: {citation['quote']}"]
        lines += ['', 'Uncertainties:', '']+['- '+u for u in analyst['uncertainties']]+['']
    challenger = report.get('challenger')
    if challenger:
        lines += ['## Challenger', '', challenger['verdict'], '', challenger['rationale'], '']
        if 'checks' in challenger:
            lines += ['Consistency checks (PASS means no identified overclaim, not established biology):', '']
            lines += ['- '+k+': '+v for k,v in challenger['checks'].items()]
            lines += ['']
        for f in challenger['findings']:
            lines += [f"- {f['severity']}: {f['issue']} Required: {f['required_change']}"]
    if report.get('policy_conflict'):
        lines += ['', '**Numerical-policy conflict: needs expert review.**', canonical(report['policy_conflict'])]
    lines += ['', '## Limits', '']+['- '+x for x in report['limitations']]
    return '\n'.join(lines)+'\n'
