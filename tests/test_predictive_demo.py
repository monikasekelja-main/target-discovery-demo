"""Scientific boundaries, route gating, review binding and no-call UI replay."""
import hashlib
import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest
from target_discovery.paths import PROJECT_ROOT
from target_discovery.predictive.contracts import Study
from target_discovery.predictive.replay import load_examples,replay,review_nomination,current_review,require_real_execution
from target_discovery.ui.predictive_demo import STEPS

class PredictiveTests(unittest.TestCase):
    def setUp(self):
        self.study,scenarios=load_examples();self.scenarios={s.id:s for s in scenarios}
    def result(self,scenario='supportive',route='after_prediction'):
        return replay(self.study,self.scenarios[scenario],route)
    def test_scenario_outcomes_and_both_routes(self):
        expected={'supportive':'supported_for_review','inconclusive':'unresolved','annotation':'blocked','donor':'unresolved','conflict':'unresolved','timeout':'blocked','exploratory':'exploratory','unsupported':'blocked','resources':'supported_for_review'}
        for scenario,status in expected.items():
            with self.subTest(scenario=scenario):
                result=self.result(scenario)
                self.assertEqual(result.status,status)
                self.assertEqual(result.route_eligible,scenario=='supportive')
                self.assertEqual(self.result(scenario,'parallel').route_eligible,scenario!='resources')
                self.assertEqual(result.evidence_status,'illustrative_not_executed')
    def test_review_binding_invalidated_by_changed_scope_or_inputs(self):
        n=self.result();r=review_nomination(n,'APPROVE_SCOPED_TEST','Scope a biological test, retaining the limitations.')
        self.assertEqual(current_review(n,r),r)
        self.assertIsNone(current_review(self.result('supportive','parallel'),r))
        self.assertIsNone(current_review(self.result('donor'),r))
        changed=self.study.model_copy(update={'question':'Changed scientific question'})
        self.assertIsNone(current_review(replay(changed,self.scenarios['supportive'],'after_prediction'),r))
    def test_blocked_approval_and_blank_review_rejected(self):
        with self.assertRaises(ValueError):review_nomination(self.result('annotation'),'APPROVE_SCOPED_TEST','A long but unsupported approval rationale.')
        with self.assertRaises(ValueError):review_nomination(self.result(),'APPROVE_SCOPED_TEST','   ')
        self.assertEqual(review_nomination(self.result('timeout','parallel'),'APPROVE_SCOPED_TEST','Independent evidence and ready assay justify a scoped test.').decision,'APPROVE_SCOPED_TEST')
    def test_timeout_and_missing_metadata_do_not_invent_results(self):
        events=self.result('timeout').events
        self.assertEqual(sum(e.check=='Bounded retry' for e in events),1)
        self.assertIn('no result',next(e.finding for e in events if e.check=='Bounded retry'))
        self.assertFalse(any(e.check=='Robustness' for e in self.result('annotation').events))
        self.assertTrue(any(e.check=='Contradictory evidence' for e in self.result('conflict').events))
    def test_no_real_execution_or_silent_evidence_promotion(self):
        with self.assertRaises(RuntimeError):require_real_execution(self.study)
        data=self.study.model_dump();data['evidence_status']='executed'
        with self.assertRaises(ValidationError):Study.model_validate(data)
        self.assertIsNone(self.study.dataset.accession)
        self.assertFalse(self.study.dataset.approved_mapping)
    def hashes(self):
        return {str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('demo-runs','recorded_examples','runtime','predictive_examples') for p in (PROJECT_ROOT/folder).rglob('*') if p.is_file()}
    def test_all_scenarios_four_steps_and_routes_without_calls_or_writes(self):
        before=self.hashes()
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{},clear=False));os.environ.pop('TARGET_DEMO_WORKSPACE',None)
            for target in ['socket.socket.connect','target_discovery.agents.agent_provider.OpenAIProvider.complete','target_discovery.evidence.evidence_search.fetch']:
                stack.enter_context(patch(target,side_effect=AssertionError('External call prohibited')))
            at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
            self.assertEqual(at.radio(key='experience').value,'Patient-study demo')
            self.assertTrue(at.button(key='predictive_back').disabled)
            for scenario in self.scenarios:
                at.selectbox(key='predictive_scenario').set_value(scenario).run()
                for route in ['after_prediction','parallel']:
                    at.radio(key='predictive_route').set_value(route).run()
                    for step in STEPS:
                        at.radio(key='predictive_step').set_value(step).run()
                        self.assertFalse(at.exception);self.assertFalse(at.error)
                        self.assertTrue(any('has not been run' in x.value for x in at.info))
            at.button(key='predictive_next').click().run()
            self.assertEqual(at.radio(key='predictive_step').value,STEPS[0])
            at.button(key='predictive_next').click().run();at.button(key='predictive_back').click().run()
            self.assertEqual(at.radio(key='predictive_step').value,STEPS[0])
            at.radio(key='experience').set_value('Guided demo').run();self.assertFalse(at.exception)
            at.radio(key='experience').set_value('Patient-study demo').run();self.assertFalse(at.exception)
        self.assertEqual(before,self.hashes())
    def test_session_review_visible_then_invalidated_and_defer_respected(self):
        with patch.dict(os.environ,{},clear=False):
            os.environ.pop('TARGET_DEMO_WORKSPACE',None)
            at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
            at.radio(key='predictive_step').set_value(STEPS[2]).run()
            at.selectbox(key='predictive_decision').set_value('APPROVE_SCOPED_TEST')
            at.text_area(key='predictive_rationale').set_value('Scope the proposed CD4 assay; patient-to-culture transfer remains unresolved.')
            next(x for x in at.button if x.label=='Record rehearsal decision').click().run()
            self.assertFalse(at.exception);self.assertTrue(at.success)
            at.radio(key='predictive_step').set_value(STEPS[3]).run()
            self.assertTrue(any('scoped proposal approved' in x.value for x in at.success))
            at.selectbox(key='predictive_scenario').set_value('donor').run()
            self.assertFalse(at.success);self.assertTrue(any('Awaiting' in x.value for x in at.warning))
            at.radio(key='predictive_step').set_value(STEPS[2]).run()
            at.selectbox(key='predictive_decision').set_value('DEFER')
            at.text_area(key='predictive_rationale').set_value('Resolve the influential donor before predictive nomination.')
            next(x for x in at.button if x.label=='Record rehearsal decision').click().run()
            at.radio(key='predictive_step').set_value(STEPS[3]).run()
            self.assertFalse(at.success);self.assertTrue(any('deferred' in x.value for x in at.warning))

if __name__=='__main__':unittest.main()
