import copy
import hashlib
import os
import unittest
from unittest.mock import patch,Mock
from streamlit.testing.v1 import AppTest
from target_discovery.paths import PROJECT_ROOT
from target_discovery.predictive.replay import load_examples,replay,review_nomination
from target_discovery.predictive.live_chat import context,ask,INSTRUCTIONS

class LiveProposalTests(unittest.TestCase):
    def setUp(self):
        self.study,scenarios=load_examples();self.n=replay(self.study,scenarios[0],'after_prediction');self.ctx=context(self.study,self.n)
        self.good={'answer':'The study is illustrative. Human review is needed.','limitations':'No model experiment has been executed.','citations':[{'source_id':'boundary','excerpt':'The patient study has not been run.'}]}
    def provider(self):
        p=Mock();p.complete.return_value=(copy.deepcopy(self.good),{'resolved_model':'test-model'});return p
    def test_one_call_and_exact_context_no_mutation(self):
        p=self.provider();before=copy.deepcopy(self.ctx)
        r=ask(self.ctx,'Why this experiment?','test-model',provider=p)
        p.complete.assert_called_once();self.assertEqual(self.ctx,before);self.assertEqual(r['binding'],self.ctx['binding'])
        payload=p.complete.call_args.args[2]
        self.assertEqual(payload['sources'],self.ctx['sources']);self.assertNotIn('demo-A002',str(payload))
        self.assertIn('untrusted',INSTRUCTIONS)
    def test_bad_citations_structure_and_failure_never_retry(self):
        for field,value in [('source_id','unread'),('excerpt','invented quote')]:
            p=self.provider();p.complete.return_value[0]['citations'][0][field]=value
            with self.assertRaises(ValueError):ask(self.ctx,'Explain','test-model',provider=p)
            p.complete.assert_called_once()
        p=self.provider();p.complete.side_effect=ValueError('Provider failure')
        with self.assertRaises(ValueError):ask(self.ctx,'Explain','test-model',provider=p)
        p.complete.assert_called_once()
    def test_quote_budget_is_cumulative_and_errors_explain_rejection(self):
        p=self.provider()
        p.complete.return_value[0]['citations']=[{'source_id':'boundary','excerpt':self.ctx['sources']['boundary']}] * 2
        with self.assertRaisesRegex(ValueError,'more than 25 quoted words'):
            ask(self.ctx,'Explain','test-model',provider=p)
        p.complete.assert_called_once()
        p=self.provider();p.complete.return_value[0]['citations'][0]['excerpt']='Not in the source'
        with self.assertRaisesRegex(ValueError,'did not exactly match'):
            ask(self.ctx,'Explain','test-model',provider=p)
    def test_invalid_input_does_not_call_and_history_is_bounded(self):
        p=self.provider()
        for question in ['', 'x'*4001]:
            with self.assertRaises(ValueError):ask(self.ctx,question,'test',provider=p)
        p.complete.assert_not_called()
        prior=[{'binding':self.ctx['binding'],'question':str(i),'answer':self.good} for i in range(7)]
        prior.append({'binding':'other','question':'wrong context','answer':self.good})
        ask(self.ctx,'Follow up','test',prior,p)
        history=p.complete.call_args.args[2]['recent_chat'];self.assertEqual([h['question'] for h in history],['4','5','6'])
    def test_review_and_feedback_change_chat_binding(self):
        r=review_nomination(self.n,'DEFER','Resolve the remaining uncertainty.')
        self.assertNotEqual(context(self.study,self.n,r)['binding'],self.ctx['binding'])
        study,sc=load_examples();new=replay(study,sc[0],'after_prediction',True)
        self.assertNotEqual(context(study,new,r)['binding'],self.ctx['binding'])
        self.assertIn('No matching',context(study,new,r)['sources']['review'])
    def test_ui_defaults_offline_and_missing_key_disables_send(self):
        with patch.dict(os.environ,{},clear=True),patch('target_discovery.predictive.live_chat.OpenAIProvider') as provider:
            at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
            self.assertEqual(at.radio(key='proposal_answer_mode').value,'Offline examples')
            at.radio(key='proposal_answer_mode').set_value('Live assistant (API)').run()
            self.assertTrue(next(b for b in at.button if b.label=='Send to live assistant').disabled)
            provider.assert_not_called();self.assertFalse(at.exception)
    def test_ui_live_submission_clear_and_context_switch_without_writes(self):
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['demo-runs','recorded_examples','predictive_examples'] for p in (PROJECT_ROOT/folder).rglob('*') if p.is_file()}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('socket.socket.connect',side_effect=AssertionError('No network')),patch('target_discovery.predictive.live_chat.OpenAIProvider',return_value=self.provider()) as factory:
            at=AppTest.from_file(str(PROJECT_ROOT/'streamlit_app.py'),default_timeout=20).run()
            at.radio(key='proposal_answer_mode').set_value('Live assistant (API)').run()
            factory.assert_not_called()
            next(t for t in at.text_area if t.label=='Your question about this proposal').set_value('What is uncertain?')
            next(b for b in at.button if b.label=='Send to live assistant').click().run()
            self.assertEqual(factory.call_count,1);self.assertFalse(at.exception)
            self.assertTrue(any('study is illustrative' in x.value for x in at.markdown))
            at.radio(key='predictive_step').set_value('3 · Review the experiment').run()
            self.assertEqual(factory.call_count,1)
            at.selectbox(key='predictive_scenario').set_value('annotation').run()
            self.assertFalse(any('study is illustrative' in x.value for x in at.markdown))
            self.assertEqual(factory.call_count,1)
        self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['demo-runs','recorded_examples','predictive_examples'] for p in (PROJECT_ROOT/folder).rglob('*') if p.is_file()})
