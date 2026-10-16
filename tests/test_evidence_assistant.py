"""Read-only boundaries and grounded-source tests; model doubles are NOT semantic evaluation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from target_discovery.workflow.workflow import Workflow,PACKAGE
from target_discovery.evidence.evidence_context import context,read_assessment,read_evidence,read_report
from target_discovery.evidence.evidence_assistant import Job,validate_answer
from target_discovery.evidence.evidence_figures import figure_data,render
from target_discovery.evidence.evidence_search import Literature,clean_query


def step(action,**kwargs):
    return {'action':action,'query':'','start_year':None,'end_year':None,'screenings':[],'source_id':'','evidence_ids':[],'template':'none','answer':None,**kwargs}

def answer(ctx):
    return {'saved_assessment':ctx['brief']['rationale'],'external_context':'No external research performed.',
        'uncertainty_and_next_steps':ctx['brief']['next_action'],
        'citations':[{'source_id':'assessment','excerpt':ctx['brief']['scientific_recommendation'],
                      'claim':'Saved proposed action','applicability_limits':'Synthetic only'}]}

class Fake:
    def __init__(self,steps):self.steps=iter(steps);self.calls=0
    def complete(self,*args):self.calls+=1;return next(self.steps),{'mode':'test double'}

class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.workspace=Path(self.temp.name)/'runs'
        self.w=Workflow(self.workspace);self.w.start('case');self.w.resume('case')
    def tearDown(self):self.w.close();self.temp.cleanup()
    def outcome(self,eid='X101'):
        self.w.review('case','case-A001','APPROVE','tester','Fixture setup',True);self.w.import_result('case',eid)
    def ctx(self,aid=None):return context(self.workspace,'case',aid or self.w.store.load('case')['current_assessment_id'])
    def bytes(self):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.workspace.rglob('*') if p.is_file()}
    def test_initial_has_no_invented_effect_plot(self):
        ctx=self.ctx();self.assertEqual(ctx['brief']['functional_effects'],{})
        for template in ('effect_intervals','qc_comparison'):
            with self.assertRaises(ValueError):figure_data(ctx,{'template':template,'data_reference':'selected_assessment'})
    def test_historical_assessment_does_not_read_new_outcome(self):
        self.outcome();ctx=self.ctx('case-A001')
        self.assertFalse(ctx['current']);self.assertFalse(any(k.startswith('runtime/experiments/') for k in ctx['snapshots']))
    def test_supportive_plot_values_preserved(self):
        self.outcome();ctx=self.ctx();data=figure_data(ctx,{'template':'effect_intervals','data_reference':'selected_assessment'})
        self.assertEqual(data['threshold'],20)
        for row in data['rows']:
            self.assertEqual({k:v for k,v in row.items() if k!='method'},ctx['brief']['functional_effects'][row['method']])
        self.assertEqual(ctx['brief']['scientific_recommendation'],'ADVANCE_TO_REPLICATION')
    def test_cell_loss_qc_reads_exact_counts(self):
        self.outcome('X104');ctx=self.ctx()
        self.assertFalse(ctx['brief']['prerequisites_passed'])
        data=figure_data(ctx,{'template':'qc_comparison','data_reference':'selected_assessment'})
        donor=ctx['snapshots']['runtime/experiments/X104.json']['assays']['KD-A'][0]
        self.assertEqual(data['rows'][0]['perturbed_live_cells'],donor['kd_live_cells'])
        self.assertEqual(data['rows'][0]['control_live_cells'],donor['ntc_live_cells'])
    def test_imprecision_and_contrary_distinct(self):
        self.outcome('X103');self.assertEqual(self.ctx()['brief']['scientific_recommendation'],'INCONCLUSIVE')
        self.w.start('negative');self.w.resume('negative');self.w.review('negative','negative-A001','APPROVE','test','Setup',True);self.w.import_result('negative','X102')
        self.assertEqual(context(self.workspace,'negative','negative-A002')['brief']['scientific_recommendation'],'DEPRIORITIZE_TESTED_HYPOTHESIS')
    def test_unresolved_and_contradictory_evidence_preserved(self):
        result=read_evidence(self.ctx(),[])
        self.assertEqual(len(result['records']),16)
        self.assertIn('E15',json.dumps(result));self.assertIn('E13',json.dumps(result))
    def test_plot_spec_cannot_supply_arrays_or_paths(self):
        self.outcome()
        for spec in ({'template':'paired_donor','data_reference':'selected_assessment'},
                     {'template':'effect_intervals','data_reference':'/tmp/arbitrary'},
                     {'template':'effect_intervals','data_reference':'selected_assessment','values':[99]}):
            with self.assertRaises(ValueError):figure_data(self.ctx(),spec)
    def test_figure_exports_and_readonly(self):
        self.outcome();before=self.bytes()
        for template in ('effect_intervals','qc_comparison'):
            result=render(self.ctx(),{'template':template,'data_reference':'selected_assessment'})
            self.assertTrue(result['exports']['png'].startswith(b'\x89PNG'))
            self.assertTrue(result['exports']['pdf'].startswith(b'%PDF'))
            self.assertIn(b'<svg',result['exports']['svg']);self.assertIn('SYNTHETIC',result['caption'])
        self.assertEqual(before,self.bytes())
    def test_no_model_call_on_browsing_or_rerun(self):
        before=self.bytes()
        with patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace)}),patch('target_discovery.evidence.evidence_assistant.OpenAIProvider',side_effect=AssertionError('No call')):
            at=AppTest.from_file(str(PACKAGE/'streamlit_app.py')).run()
            at.radio(key='view').set_value('Ask the evidence assistant').run();at.run()
            self.assertFalse(at.exception)
        self.assertEqual(before,self.bytes())
    def test_agent_bounded_readonly_and_unknown_tool_rejected(self):
        ctx=self.ctx();before=self.bytes()
        job=Job(ctx,'Explain','test',provider=Fake([step('read_evidence'),step('answer',answer=answer(ctx))]));job.run()
        self.assertEqual(job.state['status'],'completed');self.assertEqual(before,self.bytes())
        job=Job(ctx,'Edit','test',provider=Fake([step('execute_python')]));job.run()
        self.assertEqual(job.state['status'],'failed');self.assertEqual(before,self.bytes())
    def test_six_tool_limit(self):
        provider=Fake([step('read_evidence')]*7);job=Job(self.ctx(),'Loop','test',provider=provider);job.run()
        self.assertEqual(job.state['status'],'failed')
        self.assertEqual(sum(a['status']=='completed' for a in job.state['activity']),6)
    def test_cancel_during_request_stops_following_calls(self):
        ctx=self.ctx();job=Job(ctx,'Explain','test')
        class Canceller:
            def complete(self,*args):job.cancel.set();return step('read_evidence'),{}
        job.provider=Canceller();job.run()
        self.assertEqual(job.state['status'],'cancelled');self.assertEqual(len(job.state['activity']),1)
    def test_fabricated_or_unread_citations_rejected(self):
        ctx=self.ctx();a=answer(ctx);sources={'assessment':{'content':json.dumps(read_assessment(ctx))}}
        a['citations'][0]['source_id']='PMID:invented'
        with self.assertRaises(ValueError):validate_answer(a,sources)
        a=answer(ctx);a['citations'][0]['excerpt']='Invented verified efficacy'
        with self.assertRaises(ValueError):validate_answer(a,sources)
    def test_external_contradiction_stays_candidate(self):
        ctx=self.ctx();a=answer(ctx);a['external_context']='Candidate context contradicts the proposed interpretation.'
        a['citations'].append({'source_id':'PMID:123','excerpt':'No effect observed','claim':'Contradictory external context','applicability_limits':'Different system'})
        literature=Literature();literature.read={'PMID:123':{'content':'No effect observed','access':'abstract only'}}
        screening={'source_id':'PMID:123','decision':'relevant','reason':'Direct contradictory context','excerpt':'No effect observed'}
        before=self.bytes();job=Job(ctx,'Compare','test',provider=Fake([step('answer',answer=a,screenings=[screening])]),literature=literature);job.run()
        self.assertEqual(job.state['status'],'completed');self.assertEqual(before,self.bytes())
    def test_fictional_target_query_rejected(self):
        for query in ('DEMO-R1 papers','DEMO_R1 biology','demo r1 validation'):
            with self.assertRaises(ValueError):clean_query(query)
    def test_submitted_question_is_not_repeated_by_rerun(self):
        ctx=self.ctx();provider=Fake([step('answer',answer=answer(ctx))])
        from target_discovery.evidence.evidence_assistant import Job as RealJob
        def instant(*args,**kwargs):
            job=RealJob(*args,provider=provider,**kwargs)
            job.start=job.run
            return job
        before=self.bytes()
        with patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace),'OPENAI_API_KEY':'test-only'}),patch('target_discovery.ui.ui_evidence_assistant.PACKAGE',Path(self.temp.name)),patch('target_discovery.ui.ui_evidence_assistant.Job',side_effect=instant):
            at=AppTest.from_file(str(PACKAGE/'streamlit_app.py')).run()
            at.radio(key='view').set_value('Ask the evidence assistant').run()
            next(x for x in at.text_area if x.label=='Your question').set_value('Explain this assessment')
            next(x for x in at.button if x.label=='Ask evidence assistant').click().run()
            at.run();at.run()
            self.assertFalse(at.exception)
            self.assertEqual(provider.calls,1)
            self.assertTrue(any(x.value=='**What the saved assessment establishes**' for x in at.markdown))
            at.radio(key='view').set_value('Decision').run()
        self.assertEqual(before,self.bytes())
    def test_retrieval_failure_not_silently_replaced(self):
        with patch('target_discovery.evidence.evidence_search.eutils',side_effect=OSError()),patch('target_discovery.evidence.evidence_search.fetch',side_effect=OSError()):
            with self.assertRaisesRegex(ValueError,'No sources were read'):Literature().search('cytokine viability')
    def test_pubmed_read_requires_discovery_and_labels_abstract(self):
        lit=Literature()
        with self.assertRaises(ValueError):lit.publication('PMID:123')
        lit.register([{'source_id':'PMID:123','pmid':'123','title':'Test','url':'https://pubmed.ncbi.nlm.nih.gov/123/'}],'query','PubMed')
        xml=b'<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><Abstract><AbstractText>Measured live cells.</AbstractText></Abstract><PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'
        with patch('target_discovery.evidence.evidence_search.eutils',return_value=xml):result=lit.publication('PMID:123')
        self.assertEqual(result['access'],'abstract only');self.assertEqual(result['content'],'Measured live cells.')
    def test_pubmed_broadens_once_and_preserves_date_filter(self):
        replies=[{'esearchresult':{'idlist':[]}}, {'esearchresult':{'idlist':['123']}},
                 {'result':{'123':{'title':'A method','pubdate':'2024','authors':[],'articleids':[]}}}]
        with patch('target_discovery.evidence.evidence_search.eutils',side_effect=[json.dumps(r).encode() for r in replies]) as call:
            result=Literature().search('cytokine secretion | live cell | flow cytometry',2021,2026)
        self.assertEqual(call.call_count,3)
        self.assertEqual(call.call_args_list[0].kwargs['term'],'(cytokine secretion) AND (live cell) AND (flow cytometry)')
        self.assertEqual(call.call_args_list[1].kwargs['term'],'(cytokine secretion) AND (live cell)')
        for c in call.call_args_list[:2]:
            self.assertEqual(c.kwargs['mindate'],'2021');self.assertEqual(c.kwargs['maxdate'],'2026');self.assertEqual(c.kwargs['datetype'],'pdat')
        self.assertIn('broadened once',result['notice']);self.assertEqual(len(result['search_trace']),2)
        self.assertEqual(result['results'][0]['date_filter']['mindate'],'2021')
    def test_crossref_keeps_dates_after_two_empty_queries(self):
        from urllib.parse import urlsplit,parse_qs
        empty=json.dumps({'esearchresult':{'idlist':[]}}).encode()
        with patch('target_discovery.evidence.evidence_search.eutils',return_value=empty) as pubmed,patch('target_discovery.evidence.evidence_search.fetch',return_value=b'{"message":{"items":[]}}') as fetch:
            result=Literature().search('cytokine secretion | viability',2021,2026)
        self.assertEqual(pubmed.call_count,2)
        args=parse_qs(urlsplit(fetch.call_args.args[0]).query)
        self.assertEqual(args['filter'],['from-pub-date:2021-01-01,until-pub-date:2026-12-31'])
        self.assertIn('does not establish absence',result['notice'])
        self.assertEqual(len(result['search_trace']),3)
    def test_bad_search_arguments_make_no_network_requests(self):
        with patch('target_discovery.evidence.evidence_search.eutils') as call:
            for query,start,end in [('2021 2022 cytokine secretion',None,None),
                    ('one two three four five six seven',None,None),('cytokine',2026,2021),
                    ('cytokine',2021,None),('cytokine | ',None,None)]:
                with self.assertRaises(ValueError):Literature().search(query,start,end)
            call.assert_not_called()

if __name__=='__main__':unittest.main()
