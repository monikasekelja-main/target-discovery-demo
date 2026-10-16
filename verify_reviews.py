"""Transactional review/consultation/handoff tests, isolated from saved user runs."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from agent_layer import run_agents
from agent_offline import OfflineProvider
from contracts import DecisionBrief, content_fingerprint
from review_service import ReviewWorkflow, prepare_review, prepare_handoff, review_receipt
from workflow import Workflow, WorkflowError, PACKAGE
from workflow_store import dump


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.workspace=self.base/'runs'
        self.root=self.base/'fixtures';shutil.copytree(PACKAGE/'runtime',self.root/'runtime')
        self.workflow=Workflow(self.workspace,self.root)
        self.workflow.start('case');self.workflow.resume('case')
        self.workflow.review('case','case-A001','APPROVE','setup','Synthetic test setup',True)
        self.workflow.import_result('case','X101')
        self.app=ReviewWorkflow(self.workspace,self.root);self.checks={}
    def tearDown(self):self.app.close();self.workflow.close();self.temp.cleanup()
    def preview(self,attempt=None):
        aid=self.workflow.show('case')['assessment']['assessment_id']
        return prepare_review(self.workspace,'case',aid,attempt,root=self.root)
    def advice(self,p,decision='APPROVE',**kw):
        key=(p['submission_id'],decision,kw.get('next_action',''),kw.get('historical_ack',False))
        if key not in self.checks:
            check=self.app.check_rationale(p,decision,'Test human','Explicit local decision',mode='local_checks',**kw)
            self.checks[key]=check['request']['check_id']
        return self.checks[key]
    def submit(self,p=None,decision='APPROVE',**kw):
        p=p or self.preview();check_id=self.advice(p,decision,**kw)
        return self.app.submit_review(p,decision,'Test human','Explicit local decision',acknowledged=True,check_id=check_id,
            advice_acknowledged=True,override=True,override_reason='Temporary synthetic test deliberately exercises the local override.',**kw)
    def handoff_preview(self):
        return prepare_handoff(self.workspace,'case','case-A002',root=self.root)
    def report(self,attempt='offline'):
        return run_agents(self.workspace,'case',attempt,OfflineProvider(),root=self.root)
    def test_preview_does_not_write_and_agent_ready_is_not_approval(self):
        self.report();before=(self.workspace/'workflow.sqlite3').read_bytes()
        self.preview('offline')
        self.assertEqual(before,(self.workspace/'workflow.sqlite3').read_bytes())
        with self.assertRaises(WorkflowError):self.handoff_preview()
    def test_no_report_review_and_retry(self):
        p=self.preview();receipt=self.submit(p)
        self.assertIsNone(receipt['consultation']);self.assertEqual(receipt['consultation_choice'],'no_report')
        before=(self.workspace/'workflow.sqlite3').read_bytes()
        self.assertEqual(receipt,self.submit(p));self.assertEqual(before,(self.workspace/'workflow.sqlite3').read_bytes())
        with self.assertRaises(WorkflowError):self.submit(p,decision='DEFER')
    def test_report_digest_is_separate_and_changed_consultation_is_new_review(self):
        self.report();brief=self.workflow.show('case')['assessment'];canonical=content_fingerprint(DecisionBrief.model_validate(brief))
        first=self.submit();second=self.submit(self.preview('offline'))
        self.assertNotEqual(first['review_id'],second['review_id'])
        self.assertEqual(canonical,second['assessment_sha256'])
        self.assertNotEqual(canonical,second['consultation']['report_sha256'])
        self.assertEqual(brief,self.workflow.show('case')['assessment'])
        self.assertEqual(second,review_receipt(self.workspace,'case',second['review_id']))
    def test_same_id_content_change_rejected(self):
        p=self.preview();brief=copy.deepcopy(p['brief']);brief['next_action']+=' Changed.'
        self.app.store.db.execute('UPDATE assessments SET brief=? WHERE run_id=? AND assessment_id=?',(dump(brief),'case','case-A002'))
        with self.assertRaisesRegex(WorkflowError,'content changed'):self.submit(p)
    def test_input_change_rejected(self):
        p=self.preview();path=self.root/'runtime/policy.json';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(WorkflowError,'Inputs or implementation changed'):self.submit(p)
    def test_concurrent_review_rejected(self):
        p=self.preview();self.workflow.review('case','case-A002','DEFER','Other','Needs work')
        with self.assertRaisesRegex(WorkflowError,'review changed'):self.submit(p)
    def test_report_replacement_rejected_without_partial_review(self):
        _,directory=self.report();p=self.preview('offline');n=len(self.app.store.reviews('case'))
        path=directory/'report.json';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(WorkflowError,'report changed'):self.submit(p)
        self.assertEqual(n,len(self.app.store.reviews('case')))
    def test_historical_ack_and_wrong_assessment(self):
        report,directory=self.report();report['binding']['prompt_version']='historical';path=directory/'report.json';path.write_text(json.dumps(report))
        p=self.preview('offline')
        with self.assertRaisesRegex(WorkflowError,'historical'):self.submit(p)
        receipt=self.submit(p,historical_ack=True);self.assertTrue(receipt['historical_acknowledged'])
        report['binding']['assessment_id']='case-A001';path.write_text(json.dumps(report))
        with self.assertRaisesRegex(WorkflowError,'different assessment'):self.preview('offline')
    def test_explicit_ack_required(self):
        with self.assertRaisesRegex(WorkflowError,'acknowledgement'):
            self.app.submit_review(self.preview(),'APPROVE','Human','Reason')
    def test_defer_and_amend_do_not_approve(self):
        self.submit(decision='DEFER')
        with self.assertRaises(WorkflowError):self.handoff_preview()
        old=self.preview();receipt=self.submit(old,decision='AMEND',next_action='Discuss donor heterogeneity with biology.')
        state=self.workflow.show('case');self.assertEqual(state['assessment']['assessment_id'],'case-A003')
        self.assertFalse(state['approval_effective']);self.assertIsNone(state['review'])
        self.assertEqual(receipt['assessment_id'],'case-A002')
        self.assertEqual(receipt,self.submit(old,decision='AMEND',next_action='Discuss donor heterogeneity with biology.'))
        with self.assertRaises(WorkflowError):self.submit(old)
    def test_handoff_receipt_retry_and_review_invalidation(self):
        self.report();receipt=self.submit(self.preview('offline'));p=self.handoff_preview()
        h=self.app.submit_handoff(p,acknowledged=True)
        self.assertEqual(h['review']['review_id'],receipt['review_id'])
        state=self.app.store.load('case');self.assertEqual(state['specialist_response']['handoff_id'],h['handoff_id'])
        self.assertEqual(state['specialist_response']['reviewed_content_sha256'],p['assessment_sha256'])
        n=len(self.app.store.events('case'));self.app.submit_handoff(p,acknowledged=True)
        self.assertEqual(n,len(self.app.store.events('case')))
        row=self.app.store.db.execute('SELECT receipt FROM handoff_receipts').fetchone()
        self.assertEqual(json.loads(row[0])['review_receipt'],receipt)
        self.submit(decision='DEFER')
        with self.assertRaisesRegex(WorkflowError,'review changed'):self.app.submit_handoff(p,acknowledged=True)
        self.assertIsNone(self.app.store.load('case')['handoff'])
        self.assertEqual(self.app.store.db.execute('SELECT count(*) FROM handoff_receipts').fetchone()[0],1)
    def test_handoff_report_change_rejected(self):
        _,directory=self.report();self.submit(self.preview('offline'));p=self.handoff_preview()
        path=directory/'report.json';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(WorkflowError,'report changed'):self.app.submit_handoff(p,acknowledged=True)
        self.assertIsNone(self.app.store.load('case')['handoff'])
    def test_legacy_approval_is_not_backfilled(self):
        self.workflow.review('case','case-A002','APPROVE','Legacy','Approved locally')
        p=self.handoff_preview();self.assertIsNone(p['review_receipt'])
        self.app.submit_handoff(p,acknowledged=True)
        self.assertEqual(self.app.store.db.execute('SELECT count(*) FROM review_receipts').fetchone()[0],0)
    def test_failure_rolls_back_review_and_receipt(self):
        p=self.preview();self.advice(p);before=len(self.app.store.reviews('case'))
        with patch.object(self.app.store,'event',side_effect=RuntimeError('write failure')):
            with self.assertRaises(RuntimeError):self.submit(p)
        self.assertEqual(before,len(self.app.store.reviews('case')))
        self.assertIsNone(self.app.store.load('case')['review'])
    def test_non_supportive_and_cell_loss_handoffs_rejected(self):
        for eid in ('X102','X104'):
            rid=eid;self.workflow.start(rid);self.workflow.resume(rid)
            self.workflow.review(rid,rid+'-A001','APPROVE','setup','Synthetic test',True)
            self.workflow.import_result(rid,eid)
            p=prepare_review(self.workspace,rid,rid+'-A002',root=self.root)
            check=self.app.check_rationale(p,'APPROVE','Human','Local review',mode='local_checks')
            self.app.submit_review(p,'APPROVE','Human','Local review',acknowledged=True,check_id=check['request']['check_id'],
                advice_acknowledged=True,override=True,override_reason='Temporary synthetic test override for non-supportive result gating.')
            with self.assertRaisesRegex(WorkflowError,'supportive'):prepare_handoff(self.workspace,rid,rid+'-A002',root=self.root)

    def test_report_change_during_submission_rolls_back(self):
        _,directory=self.report();p=self.preview('offline');self.advice(p);original=self.app._check_report;calls=[]
        def concurrent_change(state,brief,receipt):
            calls.append(1)
            if len(calls)==2:
                path=directory/'report.json';path.write_text(path.read_text()+'\n')
            return original(state,brief,receipt)
        before=len(self.app.store.reviews('case'))
        with patch.object(self.app,'_check_report',side_effect=concurrent_change):
            with self.assertRaisesRegex(WorkflowError,'report changed'):self.submit(p)
        self.assertEqual(before,len(self.app.store.reviews('case')))
        self.assertIsNone(self.app.store.load('case')['review'])

    def test_handoff_input_change_and_missing_ack_rejected(self):
        self.submit();p=self.handoff_preview()
        with self.assertRaisesRegex(WorkflowError,'acknowledgement'):self.app.submit_handoff(p)
        path=self.root/'runtime/policy.json';path.write_text(path.read_text()+'\n')
        with self.assertRaisesRegex(WorkflowError,'Inputs or implementation changed'):
            self.app.submit_handoff(p,acknowledged=True)
        self.assertIsNone(self.app.store.load('case')['handoff'])

    def test_new_review_after_handoff_creates_new_handoff_identity(self):
        self.submit();first=self.app.submit_handoff(self.handoff_preview(),acknowledged=True)
        self.submit();second=self.app.submit_handoff(self.handoff_preview(),acknowledged=True)
        self.assertNotEqual(first['handoff_id'],second['handoff_id'])
        self.assertNotEqual(first['review']['review_id'],second['review']['review_id'])
        self.assertEqual(self.app.store.db.execute('SELECT count(*) FROM handoff_receipts').fetchone()[0],2)

    def test_bundled_examples_cannot_be_written(self):
        with self.assertRaisesRegex(WorkflowError,'read-only'):
            ReviewWorkflow(PACKAGE/'recorded_examples/state')

if __name__=='__main__':unittest.main()
