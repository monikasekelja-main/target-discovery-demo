"""Scripted plumbing provider. NOT an LLM or an agent quality evaluation."""
import json
from target_discovery.agents.agent_layer import evidence_status

class OfflineProvider:
    mode = 'scripted_offline_test'
    model = 'none'

    def complete(self, role, instructions, payload, schema):
        sources = payload['sources']
        computed = json.loads(sources['COMPUTED'])
        cite = lambda key: {'source_id': key, 'quote': sources[key][:160]}
        if role == 'analyst':
            initial = not computed['functional_effects']
            result = {
                'hypothesis_under_test': 'Does partial DEMO-R1 expression reduction produce a useful functional effect while preserving cells in the specified stimulated context?',
                'current_evidence': {
                    'status': evidence_status(computed['eligible_action']),
                    'summary': ('Functional benefit remains unmeasured.' if initial else
                        'Prerequisites failed; functional estimates are diagnostic only.' if computed['failed_gates'] else
                        'This experiment supports the scoped useful effect; independent replication and specificity remain unresolved.' if computed['eligible_action']=='ADVANCE_TO_REPLICATION' else
                        'Both methods exclude the predefined useful effect in this tested setting.' if computed['eligible_action']=='DEPRIORITIZE_TESTED_HYPOTHESIS' else
                        'Imprecision or method disagreement leaves the useful functional effect unresolved.'),
                    'citations': [cite('COMPUTED')]},
                'claims': [
                    {'claim_id': 'C1', 'kind': 'support', 'statement': 'The locus evidence motivates investigation; it does not settle gene assignment.', 'citations': [cite('E01')]},
                    {'claim_id': 'C2', 'kind': 'limitation', 'statement': 'Frozen signature outputs are not measured functional benefit.', 'citations': [cite('PREDICTION')]},
                    {'claim_id': 'C3', 'kind': 'challenge', 'statement': 'Retain the historical cell-loss concern and inspect functional-study controls.', 'citations': [cite('E09')]},
                    {'claim_id': 'C4', 'kind': 'limitation', 'statement': 'Fixed calculated eligibility constrains the next decision; assay failures cannot establish benefit.', 'citations': [cite('COMPUTED')]}],
                'proposed_action': computed['eligible_action'],
                'experiment_option_id': 'OPT-FUNCTION' if initial else None,
                'next_step': ('Discuss the functional concept with biology: it addresses the endpoint more directly than broad omics, at greater effort than record review; feasibility remains assumed.' if initial else 'Ask biology to review the fixed calculation and select the appropriate replication, scoped deprioritization or unresolved/QC follow-up.'),
                'uncertainties': ['Gene assignment and genetic direction remain unresolved.', 'Antibody blockade equivalence and systemic safety remain unassessed.'],
                'retrieval': {'evidence_ids': ['E03', 'E09'], 'question': 'Reinspect genetic direction and cell-loss limitations.'} if payload['retrieval_allowed'] else None}
        else:
            result = {'checks': {k: 'PASS' for k in ('hypothesis_and_finding', 'cell_loss_and_qc', 'replication_independence', 'modality_equivalence')}, 'verdict': 'READY_FOR_HUMAN_REVIEW', 'findings': [{
                'severity': 'caution', 'claim_id': None,
                'issue': 'Scripted harness has not performed independent scientific evaluation.',
                'required_change': 'A human must inspect sources and claims; live-model evaluation is still required.',
                'citations': [cite('COMPUTED')]}], 'retrieval': None,
                'rationale': 'SCRIPTED TEST ONLY: exercises report plumbing; no scientific correctness verdict.'}
        return result, {'mode': self.mode, 'usage': None, 'response_id': None}
