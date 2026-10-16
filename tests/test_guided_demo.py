"""Guided replay navigation, truthful state handling, and strict read-only checks."""
import copy
import hashlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from target_discovery.paths import PROJECT_ROOT
from target_discovery.ui.ui_service import load_run
from target_discovery.ui.guided_demo import STEPS

class GuidedDemoTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ);self.env.start();os.environ.pop('TARGET_DEMO_WORKSPACE',None)
        self.blocks=[patch('socket.socket.connect',side_effect=AssertionError('Network prohibited')),
                     patch('target_discovery.agents.agent_provider.OpenAIProvider.complete',side_effect=AssertionError('Model prohibited')),
                     patch('target_discovery.evidence.evidence_search.fetch',side_effect=AssertionError('Retrieval prohibited'))]
        for block in self.blocks:block.start()
    def tearDown(self):
        for block in reversed(self.blocks):block.stop()
        self.env.stop()
    def launch(self):
        at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
        return at.radio(key='experience').set_value('Guided demo').run()
    def hashes(self):
        return {str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in ('demo-runs','recorded_examples') for p in (PROJECT_ROOT/folder).rglob('*') if p.is_file()}
    def check(self,at):self.assertFalse(at.exception);self.assertFalse(at.error)
    def test_default_four_steps_no_writes_or_calls(self):
        before=self.hashes();at=self.launch();self.check(at)
        self.assertEqual(at.radio(key='experience').value,'Guided demo')
        self.assertFalse(at.selectbox);self.assertFalse(at.text_input);self.assertTrue(at.button(key='guide_back').disabled)
        for i in range(4):
            self.assertEqual(at.radio(key='guide_step').value,STEPS[i]);self.check(at)
            self.assertEqual([x.label for x in at.expander if x.label=='View supporting detail'],['View supporting detail'])
            self.assertFalse(any(x.label in ('Record human decision','Create locally simulated hand-off') for x in at.button))
            at.button(key='guide_next').click().run()
        self.assertEqual(at.radio(key='guide_step').value,STEPS[0])
        at.radio(key='guide_step').set_value(STEPS[2]).run();at.button(key='guide_back').click().run()
        self.assertEqual(at.radio(key='guide_step').value,STEPS[1])
        self.assertEqual(self.hashes(),before)
    def test_full_workbench_and_return_remain_available(self):
        at=self.launch();at.radio(key='experience').set_value('Explore the workbench').run();self.check(at)
        self.assertTrue(at.selectbox(key='run_id'))
        for view in ['Evidence & prediction','Challenge & review','Specialist handoff','Ask the evidence assistant','Decision']:
            at.radio(key='view').set_value(view).run();self.check(at)
        at.radio(key='experience').set_value('Guided demo').run();self.check(at)
        self.assertFalse(at.selectbox(key='run_id') if any(x.key=='run_id' for x in at.selectbox) else False)
        self.assertEqual(at.radio(key='guide_step').value,STEPS[0])
    def test_roles_and_saved_report_are_readonly_and_explicitly_scripted(self):
        before=self.hashes();at=self.launch()
        at.radio(key='guide_step').set_value(STEPS[2]).run();self.check(at)
        text=' '.join(x.value for x in at.markdown)
        for term in ('Who does what?', 'Analyst agent', 'Challenger agent', 'Deterministic code', 'Human reviewer'):
            self.assertIn(term,text)
        self.assertIn('Cannot change calculations or approve progression',text)
        self.assertIn('not validation or approval',text)
        self.assertTrue(any('not live reasoning or independent scientific review' in x.value for x in at.caption))
        self.assertEqual(sum(x.label=='Inspect the saved agent report' for x in at.expander),1)
        self.assertTrue(any('Scripted offline test' in x.value for x in at.info))
        self.assertFalse(any(x.label=='Record human decision' for x in at.button))
        self.assertEqual(before,self.hashes())

    def test_missing_case_never_created(self):
        before=self.hashes()
        with patch('target_discovery.ui.guided_demo.load_run',side_effect=ValueError('Saved run not found')):
            at=self.launch();self.assertFalse(at.exception);self.assertTrue(at.error);self.assertFalse(at.success)
        self.assertEqual(self.hashes(),before)
    def test_stale_case_and_changed_assessment_block_narrative(self):
        original=load_run(PROJECT_ROOT/'demo-runs','demo')
        for change in ('stale','new_assessment'):
            run=copy.deepcopy(original)
            if change=='stale':run['inputs_current']=False
            else:run['state']['current_assessment_id']='demo-A003'
            with patch('target_discovery.ui.guided_demo.load_run',return_value=run):
                at=self.launch();self.assertFalse(at.exception);self.assertTrue(at.warning)
                self.assertFalse(at.button);self.assertFalse(at.success)
    def test_deferred_review_never_shows_approval_or_current_handoff(self):
        run=copy.deepcopy(load_run(PROJECT_ROOT/'demo-runs','demo'))
        run['reviews'][-1]['decision']='DEFER';run['state']['review']['decision']='DEFER'
        with patch('target_discovery.ui.guided_demo.load_run',return_value=run):
            at=self.launch();at.radio(key='guide_step').set_value(STEPS[2]).run();self.check(at)
            self.assertTrue(any('Deferred' in x.value for x in at.warning));self.assertFalse(at.success)
            at.button(key='guide_next').click().run();self.check(at)
            self.assertTrue(any('No current, matching' in x.value for x in at.warning))
    def test_mismatched_specialist_response_not_presented_as_current(self):
        run=copy.deepcopy(load_run(PROJECT_ROOT/'demo-runs','demo'))
        run['state']['specialist_response']['handoff_id']='different-handoff'
        with patch('target_discovery.ui.guided_demo.load_run',return_value=run):
            at=self.launch();at.radio(key='guide_step').set_value(STEPS[3]).run();self.check(at)
            self.assertTrue(any('No current, matching' in x.value for x in at.warning))
            self.assertFalse(any('Simulated reply:' in x.value for x in at.warning))

if __name__=='__main__':unittest.main()
