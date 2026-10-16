"""Audit regression: evidence-derived nominations, shared gates and scoped feedback."""
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from target_discovery.paths import PROJECT_ROOT
from target_discovery.predictive.replay import *

class DecisionAuditTests(unittest.TestCase):
    def setUp(self):
        self.study,scenarios=load_examples();self.scenarios={s.id:s for s in scenarios}
    def replay(self,key='supportive',route='after_prediction',feedback=False):
        return replay(self.study,self.scenarios[key],route,feedback)
    def test_evidence_changes_nomination_without_scenario_label_change(self):
        scenario=self.scenarios['supportive']
        n=replay(self.study,scenario,'after_prediction')
        self.assertEqual(n.cell_state,'Th17-like CD4 state')
        self.assertEqual(n.comparisons[0]['donors_above_comparators'],4)
        self.assertAlmostEqual(n.comparisons[0]['mean_shift'],.312)
        observations=[o.model_copy(update={'donor_shifts':{d:0.0 for d in o.donor_shifts}}) for o in scenario.observations]
        changed=scenario.model_copy(update={'observations':observations})
        n=replay(self.study,changed,'after_prediction')
        self.assertEqual(n.status,'unresolved');self.assertIsNone(n.cell_state);self.assertFalse(n.route_eligible)
    def test_blocked_and_unresolved_cases_never_have_predictive_nomination(self):
        for case in ['annotation','timeout','unsupported','inconclusive','donor','conflict','exploratory']:
            for route in ['after_prediction','parallel']:
                n=self.replay(case,route)
                self.assertIsNone(n.cell_state);self.assertIsNone(n.intervention)
                if route=='parallel':
                    self.assertTrue(n.route_eligible)
                    self.assertIn('independently',n.proposed_test)
                else:self.assertFalse(n.route_eligible)
    def test_each_shared_prerequisite_blocks_both_routes_even_with_supportive_prediction(self):
        original=self.scenarios['supportive']
        for index in range(len(original.prerequisites)):
            gates=[g.model_copy(update={'met':False}) if i==index else g for i,g in enumerate(original.prerequisites)]
            for route in ['after_prediction','parallel']:
                n=replay(self.study,original.model_copy(update={'prerequisites':gates}),route)
                self.assertEqual(n.status,'supported_for_review');self.assertFalse(n.route_eligible)
                with self.assertRaises(ValueError):review_nomination(n,'APPROVE_SCOPED_TEST','A scoped test would be useful.')
        n=replay(self.study,original.model_copy(update={'prerequisites':[]}), 'after_prediction')
        self.assertFalse(n.route_eligible)
    def test_independent_rationale_required_only_for_parallel(self):
        original=self.scenarios['supportive']
        altered=original.model_copy(update={'independent_rationale':original.independent_rationale.model_copy(update={'met':False})})
        self.assertFalse(replay(self.study,altered,'parallel').route_eligible)
        self.assertTrue(replay(self.study,altered,'after_prediction').route_eligible)
    def test_donor_sensitivity_and_conflicting_observations_are_retained(self):
        n=self.replay('donor');self.assertLess(n.comparisons[0]['leave_one_out_min'],0)
        self.assertIn('subgroup',n.request)
        n=self.replay('conflict');self.assertTrue(n.comparisons[0]['eligible']);self.assertEqual(n.status,'unresolved')
        self.assertTrue(any('SIM-F01' in e.finding and 'SIM-P01' in e.finding for e in n.events))
    def test_split_leakage_and_identity_loss_cannot_nominate(self):
        s=self.study.model_copy(update={'adaptation':self.study.adaptation.model_copy(update={'evaluation_donors':self.study.adaptation.development_donors})})
        self.assertEqual(replay(s,self.scenarios['supportive'],'after_prediction').status,'blocked')
        original=self.scenarios['supportive'];altered=original.model_copy(update={'observations':[o.model_copy(update={'identity_preserved':False}) for o in original.observations]})
        self.assertIsNone(replay(self.study,altered,'after_prediction').cell_state)
    def test_specialist_change_invalidates_approval(self):
        n=self.replay();review=review_nomination(n,'APPROVE_SCOPED_TEST','Scope the reduction assay; transfer remains uncertain.')
        revised=self.replay(feedback=True)
        self.assertNotEqual(n.binding,revised.binding);self.assertIsNone(current_review(revised,review))
        self.assertIn('native-target binding',revised.proposed_test)
        self.assertEqual(revised.specialist['status'],'NEEDS_INFORMATION')
    def test_ui_feedback_persists_across_steps_and_deferral_is_never_green(self):
        with patch('socket.socket.connect',side_effect=AssertionError('Network prohibited')):
            at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
            at.radio(key='predictive_step').set_value('4 · Agree the next action').run()
            at.checkbox(key='predictive_feedback').check().run()
            at.radio(key='predictive_step').set_value('3 · Review the experiment').run()
            self.assertTrue(any('native-target binding' in t.value for t in at.markdown))
            at.run();self.assertTrue(any('native-target binding' in t.value for t in at.markdown))
            at.selectbox(key='predictive_decision').set_value('DEFER')
            at.text_area(key='predictive_rationale').set_value('Obtain binding and engagement feasibility first.')
            next(b for b in at.button if b.label=='Record rehearsal decision').click().run()
            self.assertFalse(at.success);self.assertTrue(any('defer' in w.value for w in at.warning))
            self.assertFalse(at.exception)
    def test_ui_missing_context_has_no_nominated_state_and_has_actual_next_owner(self):
        at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
        at.selectbox(key='predictive_scenario').set_value('annotation').run()
        at.radio(key='predictive_step').set_value('3 · Review the experiment').run()
        self.assertFalse(any('**Nominated state:**' in t.value for t in at.markdown))
        at.radio(key='predictive_step').set_value('4 · Agree the next action').run()
        self.assertTrue(any('Data steward:' in t.value for t in at.markdown))
        self.assertFalse(at.checkbox);self.assertFalse(at.exception)
    def test_plain_language_summary_pending_review_and_navigation(self):
        at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
        self.assertTrue(any('Which psoriasis-related cells' in h.value for h in at.subheader))
        at.button(key='predictive_next').click().run()
        self.assertTrue(any('most consistent signal' in h.value for h in at.subheader))
        self.assertTrue(any('scores, donor sensitivity' in e.label for e in at.expander))
        at.radio(key='predictive_step').set_value('4 · Agree the next action').run()
        self.assertTrue(any('biology reviews the proposed experiment' in h.value for h in at.subheader))
        self.assertTrue(any('Ask biology and the project owner' in m.value for m in at.markdown))
        at.button(key='predictive_next').click().run()
        self.assertEqual(at.radio(key='predictive_step').value,'1 · Define the study')
        self.assertFalse(at.exception)
