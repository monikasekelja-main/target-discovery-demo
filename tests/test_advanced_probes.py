"""Offline tests of advanced probe construction and CLI, not live reasoning."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from target_discovery.workflow.workflow import Workflow
from target_discovery.agents.agent_contracts import AnalystOutput
from target_discovery.agents.agent_layer import validate_citations
from target_discovery.agents.agent_offline import OfflineProvider
import target_discovery.agents.challenger_probe as probe

class AdvancedProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.workspace=Path(self.temp.name)
        app=Workflow(self.workspace)
        for name,eid in [('support','X101'),('discord','X107'),('imprecise','X103')]:
            app.start(name);app.resume(name)
            app.review(name,name+'-A001','APPROVE','test','Synthetic test preparation.',True)
            app.import_result(name,eid)
        app.close()
    def tearDown(self):self.temp.cleanup()
    def cases(self):return probe.build_advanced_cases(self.workspace,'support','discord','imprecise')
    def test_four_semantic_mutations_preserve_facts_and_valid_citations(self):
        cases=self.cases();self.assertEqual(len(cases),4)
        for name,expected,state,brief,sources,proposal in cases:
            AnalystOutput.model_validate(proposal);validate_citations(proposal,sources)
            baseline=probe.make_proposal(sources)
            self.assertEqual(proposal['claims'][:-1],baseline['claims'])
            self.assertEqual(proposal['current_evidence'],baseline['current_evidence'])
            self.assertEqual(proposal['proposed_action'],baseline['proposed_action'])
            self.assertEqual(proposal['claims'][-1]['claim_id'],'C7')
            self.assertEqual(expected,'MATERIAL_INFERENCE')
    def test_wrong_outcome_is_rejected_before_provider(self):
        with self.assertRaises(ValueError):probe.build_advanced_cases(self.workspace,'support','imprecise','discord')
    def test_missing_run_arguments_rejected(self):
        with self.assertRaises(ValueError):probe.build_advanced_cases(self.workspace,'support',None,None)
    def test_grader_requires_targeted_blocking_finding(self):
        case=self.cases()[0]
        result,_=OfflineProvider().complete('challenger','',{'sources':case[4]}, {})
        self.assertFalse(probe.evaluate_response(result,'MATERIAL_INFERENCE'))
        result['verdict']='REVISE';result['checks']['hypothesis_and_finding']='FAIL'
        result['findings'][0].update(severity='blocking',claim_id='C1')
        self.assertFalse(probe.evaluate_response(result,'MATERIAL_INFERENCE'))
        result['findings'][0]['claim_id']='C7'
        self.assertTrue(probe.evaluate_response(result,'MATERIAL_INFERENCE'))
    def test_cli_dispatch_four_calls_no_expected_labels_in_payload(self):
        calls=[]
        class FakeProvider(OfflineProvider):
            mode='scripted_offline_test'
            def __init__(self,model):self.model=model
            def complete(self,role,instructions,payload,schema):
                calls.append(payload)
                self_check=set(payload)
                if {'case_id','expected_check','suite'} & self_check:raise AssertionError('Answer leakage')
                result,meta=super().complete(role,instructions,payload,schema)
                result['verdict']='REVISE';result['checks']['hypothesis_and_finding']='FAIL'
                result['findings'][0].update(severity='blocking',claim_id='C7')
                return result,meta
        args=['target_discovery.agents.challenger_probe.py','--workspace',str(self.workspace),'--suite','advanced',
              '--supportive-run','support','--disagreement-run','discord','--imprecise-run','imprecise',
              '--attempt-id','mock','--model','mock']
        with patch('sys.argv',args),patch.object(probe,'OpenAIProvider',FakeProvider),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(probe.main(),0)
        self.assertEqual(len(calls),4)
        summary=json.loads((self.workspace/'challenger-probes/mock/summary.json').read_text())
        self.assertEqual(summary['suite'],'advanced')
        self.assertTrue(all(x['automatic_check_passed'] for x in summary['results']))

if __name__=='__main__':unittest.main()
