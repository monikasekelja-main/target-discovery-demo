"""Rationale advice: mocked model transport only; never paid API calls."""
import copy
import json
import unittest
from unittest.mock import patch
from agent_provider import ProviderError
from review_service import prepare_handoff, digest
from rationale_advisor import RationaleAdvice, PROMPT
import verify_reviews
from workflow import WorkflowError


class FakeAdvisor:
    mode='live_llm'
    model='test-only'
    def __init__(self,outcome='NEEDS_REVISION',after_call=None):self.calls=[];self.outcome=outcome;self.after_call=after_call
    def complete(self,role,instructions,payload,schema):
        self.calls.append((role,instructions,payload,schema))
        if self.after_call:self.after_call()
        findings=[] if self.outcome!='NEEDS_REVISION' else [{'draft_quote':payload['draft']['rationale'],
            'assessment_field':'rationale','issue':'This does not explain the scientific decision.',
            'guidance':'Which finding supports your choice?'}]
        return {'outcome':self.outcome,'summary':'Mocked advice for control-flow tests only.',
                'findings':findings,'questions':['Which finding supports your choice?'] if findings else []}, {'resolved_model':'test-only','response_id':'test'}


class AdvisorTests(unittest.TestCase):
    setUp=verify_reviews.ReviewTests.setUp
    tearDown=verify_reviews.ReviewTests.tearDown
    preview=verify_reviews.ReviewTests.preview
    def check(self,p=None,text='this was not acceptable because of the cherries',provider=None,**kw):
        p=p or self.preview();provider=provider or FakeAdvisor()
        result=self.app.check_rationale(p,'APPROVE','Private reviewer',text,provider=provider,model='test-only',**kw)
        return p,result
    def save(self,p,check,text='this was not acceptable because of the cherries',**kw):
        return self.app.submit_review(p,'APPROVE','Private reviewer',text,acknowledged=True,
            check_id=check['request']['check_id'],advice_acknowledged=True,**kw)
    def test_missing_check_cannot_finalize(self):
        with self.assertRaisesRegex(WorkflowError,'Check this draft'):
            self.app.submit_review(self.preview(),'APPROVE','Human','Reason',acknowledged=True)
    def test_cherries_flagged_locally_without_claiming_ai(self):
        p=self.preview();check=self.app.check_rationale(p,'APPROVE','Private reviewer','this was not acceptable because of the cherries',mode='local_checks')
        self.assertEqual(check['result']['feedback']['outcome'],'NEEDS_REVISION')
        self.assertEqual(check['result']['mode'],'local_checks')
        with self.assertRaisesRegex(WorkflowError,'override'):self.save(p,check)
        self.assertFalse(self.workflow.show('case')['approval_effective'])
    def test_agent_advice_no_approval_and_identity_stays_local(self):
        provider=FakeAdvisor();before=len(self.app.store.reviews('case'));p,check=self.check(provider=provider)
        self.assertEqual(before,len(self.app.store.reviews('case')));self.assertEqual(len(provider.calls),1)
        role,instructions,payload,schema=provider.calls[0]
        self.assertEqual(payload['assessment'],p['brief']);self.assertNotIn('reviewer',payload['draft'])
        self.assertNotIn('Private reviewer',json.dumps(payload));self.assertIn('untrusted DATA',instructions)
        self.assertFalse(self.workflow.show('case')['approval_effective'])
        with self.assertRaises(WorkflowError):prepare_handoff(self.workspace,'case','case-A002',self.root)
    def test_feedback_override_requires_reason_and_is_separate(self):
        p,c=self.check();before=self.workflow.show('case')['assessment']
        for kw in ({},{'override':True},{'override':True,'override_reason':'yes'}):
            with self.assertRaises(WorkflowError):self.save(p,c,**kw)
        receipt=self.save(p,c,override=True,override_reason='This synthetic test intentionally exercises human override provenance.')
        self.assertTrue(receipt['rationale_advice']['overridden'])
        self.assertEqual(receipt['rationale_advice']['result_sha256'],c['result_sha256'])
        self.assertEqual(before,self.workflow.show('case')['assessment'])
        self.assertEqual(receipt,self.save(p,c,override=True,override_reason='This synthetic test intentionally exercises human override provenance.'))
    def test_successful_ai_check_still_needs_human_ack(self):
        text='Both methods meet the threshold; approve replication while retaining same-donor and modality limits.'
        p,c=self.check(text=text,provider=FakeAdvisor('NO_CONCERNS_IDENTIFIED'))
        self.assertFalse(self.workflow.show('case')['approval_effective'])
        with self.assertRaisesRegex(WorkflowError,'acknowledgement'):
            self.app.submit_review(p,'APPROVE','Private reviewer',text,check_id=c['request']['check_id'],advice_acknowledged=True)
        receipt=self.save(p,c,text=text);self.assertFalse(receipt['rationale_advice']['overridden'])
    def test_draft_changes_require_recheck(self):
        p,c=self.check(provider=FakeAdvisor('NO_CONCERNS_IDENTIFIED'))
        cases=[{'rationale':'Changed rationale about replication.'},{'decision':'DEFER'},{'next_action':'New next action'},
               {'reviewer':'Different reviewer'},{'historical_ack':True}]
        for changes in cases:
            kw={'preview':p,'decision':'APPROVE','reviewer':'Private reviewer','rationale':'this was not acceptable because of the cherries',
                'acknowledged':True,'check_id':c['request']['check_id'],'advice_acknowledged':True}
            kw.update(changes)
            with self.assertRaisesRegex(WorkflowError,'changed since'):self.app.submit_review(**kw)
    def test_another_preview_cannot_reuse_check(self):
        p,c=self.check(provider=FakeAdvisor('NO_CONCERNS_IDENTIFIED'))
        with self.assertRaisesRegex(WorkflowError,'changed since'):self.save(self.preview(),c)
    def test_failed_provider_never_silently_falls_back(self):
        provider=FakeAdvisor()
        with patch.object(provider,'complete',side_effect=ProviderError('Provider failed')):
            p,c=self.check(provider=provider)
        self.assertEqual(c['result']['status'],'FAILED');self.assertIsNone(c['result']['feedback'])
        with self.assertRaisesRegex(WorkflowError,'override'):self.save(p,c)
        self.save(p,c,override=True,override_reason='I have independently reviewed the evidence despite unavailable automated advice.')
    def test_bad_quote_and_schema_are_not_accepted(self):
        provider=FakeAdvisor()
        bad={'outcome':'NEEDS_REVISION','summary':'Bad quote','questions':[],
             'findings':[{'draft_quote':'invented text','assessment_field':'none','issue':'issue','guidance':'guidance'}]}
        with patch.object(provider,'complete',return_value=(bad,{})):
            p,c=self.check(provider=provider)
        self.assertEqual(c['result']['status'],'FAILED');self.assertIsNone(c['result']['feedback'])
        with self.assertRaises(ValueError):RationaleAdvice.model_validate({**bad,'outcome':'NO_CONCERNS_IDENTIFIED'})
    def test_concurrent_review_during_call_marks_advice_stale(self):
        provider=FakeAdvisor(after_call=lambda:self.workflow.review('case','case-A002','DEFER','Other reviewer','Needs review.'))
        p,c=self.check(provider=provider);self.assertEqual(c['result']['status'],'STALE')
        with self.assertRaises(WorkflowError):self.save(p,c,override=True,override_reason='An override cannot bypass stale assessment or review binding.')
    def test_checked_rationale_is_preserved_and_old_review_not_modified(self):
        prior=self.app.store.reviews('case');p,c=self.check()
        self.save(p,c,override=True,override_reason='Synthetic test overrides the feedback for audit verification only.')
        self.assertEqual(prior,self.app.store.reviews('case')[:-1])
        row=self.app.store.db.execute('SELECT request FROM rationale_checks WHERE check_id=?',(c['request']['check_id'],)).fetchone()
        self.assertEqual(json.loads(row[0])['draft']['rationale'],'this was not acceptable because of the cherries')
    def test_handoff_rejects_altered_advice(self):
        p,c=self.check(provider=FakeAdvisor('NO_CONCERNS_IDENTIFIED'));self.save(p,c)
        h=prepare_handoff(self.workspace,'case','case-A002',root=self.root)
        changed=copy.deepcopy(c['result']);changed['feedback']['summary']='Altered after approval'
        self.app.store.db.execute('UPDATE rationale_results SET result=?,result_sha256=? WHERE check_id=?',
            (json.dumps(changed),digest(changed),c['request']['check_id']))
        with self.assertRaisesRegex(WorkflowError,'advice changed'):self.app.submit_handoff(h,acknowledged=True)
    def test_local_checks_never_return_semantic_clearance(self):
        p=self.preview();text='The functional assay supports replication.'
        c=self.app.check_rationale(p,'APPROVE','Private reviewer',text,mode='local_checks')
        self.assertEqual(c['result']['feedback']['outcome'],'UNABLE_TO_ASSESS')
        with self.assertRaisesRegex(WorkflowError,'override'):self.save(p,c,text=text)

if __name__=='__main__':unittest.main()
