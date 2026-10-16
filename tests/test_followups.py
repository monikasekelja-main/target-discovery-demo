"""Follow-up persistence, stale-session and human authority regression checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os
from streamlit.testing.v1 import AppTest
from target_discovery.workflow.workflow import Workflow, PACKAGE
from target_discovery.review.followup_service import FollowupWorkflow, prepare_followup, history
from target_discovery.ui.ui_service import load_run

class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.workspace=Path(self.temp.name)/'runs'
        self.app=Workflow(self.workspace);self.app.start('case');self.app.resume('case')
        self.app.review('case','case-A001','DEFER','Owner','Resolve evidence gaps first')
        self.service=FollowupWorkflow(self.workspace)
    def tearDown(self):self.service.close();self.app.close();self.temp.cleanup()
    def preview(self):return prepare_followup(self.workspace,'case','case-A001')
    def save(self,p=None,**kwargs):return self.service.save_followup(p or self.preview(),'Plan independent replication','Assay team','Independent donor results available',**kwargs)
    def test_versions_retry_and_decision_preservation(self):
        before=load_run(self.workspace,'case');p=self.preview();a=self.save(p)
        self.assertEqual(self.save(p),a)
        b=self.save(status='In progress',progress_note='Protocol drafting')
        self.assertEqual(b['previous_followup_id'],a['followup_id'])
        self.assertEqual(len(history(self.workspace,'case')),2)
        after=load_run(self.workspace,'case')
        for key in ('state','assessments','reviews'):self.assertEqual(before[key],after[key])
    def test_concurrent_plan_and_review_rejected(self):
        stale=self.preview();self.save()
        with self.assertRaisesRegex(ValueError,'another session'):self.save(stale)
        stale=self.preview();self.app.review('case','case-A001','APPROVE','Owner','Proceed',True)
        with self.assertRaisesRegex(ValueError,'review changed'):self.save(stale)
    def test_missing_fields_and_ready_note(self):
        with self.assertRaises(ValueError):self.service.save_followup(self.preview(),'','Owner','Condition')
        with self.assertRaises(ValueError):self.save(status='Ready for re-review')
        self.save(status='Ready for re-review',progress_note='Protocol and result reference recorded for reviewer')
        self.assertEqual(self.app.show('case')['review']['decision'],'DEFER')
    def test_readonly_history_creates_nothing(self):
        before=(self.workspace/'workflow.sqlite3').read_bytes()
        self.assertEqual(history(self.workspace,'case'),[])
        self.assertEqual(before,(self.workspace/'workflow.sqlite3').read_bytes())
    def test_new_assessment_keeps_history_requires_review(self):
        self.save();self.app.amend('case','case-A001','Owner','Reconsider next step','Resolve evidence gaps')
        run=load_run(self.workspace,'case')
        self.assertIsNone(run['state']['review'])
        self.assertEqual(history(self.workspace,'case')[0]['assessment_id'],'case-A001')
        with self.assertRaises(ValueError):prepare_followup(self.workspace,'case',run['state']['current_assessment_id'])
    def test_ui_save_update_reload(self):
        with patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace)}):
            at=AppTest.from_file(str(PACKAGE/'streamlit_app.py')).run()
            at.button(key='prepare_followup').click().run()
            next(x for x in at.text_area if x.label=='Required work').set_value('Plan replication')
            next(x for x in at.text_input if x.label=='Follow-up owner').set_value('Assay team')
            next(x for x in at.text_area if x.label=='Condition for re-review').set_value('Independent results')
            next(x for x in at.button if x.label=='Save follow-up plan').click().run()
            self.assertFalse(at.exception)
            self.assertTrue(any(x.value=='Plan replication' for x in at.markdown))
            at.button(key='prepare_followup').click().run()
            next(x for x in at.selectbox if x.label=='Follow-up status').set_value('Ready for re-review')
            next(x for x in at.text_area if x.label=='Progress / evidence note').set_value('Results available for assessment')
            next(x for x in at.button if x.label=='Save follow-up plan').click().run()
            at=AppTest.from_file(str(PACKAGE/'streamlit_app.py')).run()
            self.assertFalse(at.exception)
            self.assertTrue(any('decision remains deferred' in x.value for x in at.info))
            self.assertEqual(len(history(self.workspace,'case')),2)
    def test_ready_followup_opens_fresh_review_without_saving_decision(self):
        self.save(status='Ready for re-review',progress_note='Plan available for review')
        before=load_run(self.workspace,'case')
        with patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace)}):
            at=AppTest.from_file(str(PACKAGE/'streamlit_app.py')).run()
            at.button(key='start_re_review').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.radio(key='view').value,'Challenge & review')
            self.assertTrue(any(x.label=='Review rationale' for x in at.text_area))
            self.assertTrue(any(x.label=='Record human decision' and x.disabled for x in at.button))
            self.assertTrue(any(x.value=='Plan available for review' for x in at.markdown))
            at.button(key='start_re_review').click().run()
            self.assertFalse(at.exception)
        self.assertEqual(load_run(self.workspace,'case')['reviews'],before['reviews'])
        self.assertEqual(load_run(self.workspace,'case')['state'],before['state'])

if __name__=='__main__':unittest.main()
