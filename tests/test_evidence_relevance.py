"""Relevance routing checks with explicit model doubles, not a scientific benchmark."""
from unittest.mock import patch
from tests.test_evidence_assistant import AssistantTests,Fake,step,answer
from target_discovery.evidence.evidence_assistant import Job
from target_discovery.evidence.evidence_search import Literature
from target_discovery.evidence.evidence_relevance import Relevance
import unittest

class RelevanceTests(unittest.TestCase):
    def test_unread_or_rejected_sources_cannot_be_accepted(self):
        lit=Literature();lit.discovered={'P':{'title':'Population development'}};r=Relevance()
        r.apply([{'source_id':'P','decision':'reject','reason':'No secretion or survival method','excerpt':''}],lit)
        with self.assertRaises(ValueError):r.require_candidate('P')
        with self.assertRaises(ValueError):r.apply([{'source_id':'P','decision':'relevant','reason':'A method','excerpt':'invented'}],lit)
        lit.read['P']={'content':'Population development'}
        self.assertEqual(r.sources(lit),{})
    def test_fallback_requires_distinct_searches_with_same_dates(self):
        r=Relevance();r.searches.append(r.check_search('cytokine secretion | viable cell',2021,2026))
        with self.assertRaises(ValueError):r.require_second_search()
        with self.assertRaises(ValueError):r.check_search('CYTOKINE secretion | viable   cell',2021,2026)
        with self.assertRaises(ValueError):r.check_search('microengraving',2020,2026)
        r.searches.append(r.check_search('microengraving | cytokine secretion',2021,2026));r.require_second_search()

class RoutingTests(AssistantTests):
    # Only new routing tests here; inherited suite is loaded separately by the runner.
    def test_irrelevant_hit_then_focused_search_and_accepted_method(self):
        ctx=self.ctx();lit=Literature();queries=[]
        def search(query,start,end):
            queries.append(query)
            sid='P1' if len(queries)==1 else 'P2'
            title='Eosinophil development' if sid=='P1' else 'Viable cytokine producer recovery'
            lit.discovered[sid]={'source_id':sid,'title':title}
            return {'results':[lit.discovered[sid]]}
        def publication(sid):
            self.assertEqual(sid,'P2')
            lit.read[sid]={'content':'Viable producers were recovered','access':'abstract only'}
            return lit.read[sid]
        reject={'source_id':'P1','decision':'reject','reason':'Population profiling does not measure producer survival or secretion.','excerpt':''}
        candidate={'source_id':'P2','decision':'candidate','reason':'Title suggests live producer recovery.','excerpt':''}
        relevant={'source_id':'P2','decision':'relevant','reason':'Abstract describes viable producer recovery; IL-17A transfer unverified.','excerpt':'Viable producers were recovered'}
        a=answer(ctx);a['external_context']='Candidate recovery method, transfer unverified.'
        a['citations'].append({'source_id':'P2','excerpt':'Viable producers were recovered','claim':'Producer recovery method','applicability_limits':'Different cell system'})
        provider=Fake([step('search_literature',query='cytokine secretion | viable cell',start_year=2021,end_year=2026),
                       step('search_literature',query='microengraving | cytokine secretion',start_year=2021,end_year=2026,screenings=[reject]),
                       step('read_publication',source_id='P2',screenings=[candidate]),step('answer',answer=a,screenings=[relevant])])
        before=self.bytes()
        with patch.object(lit,'search',side_effect=search),patch.object(lit,'publication',side_effect=publication),patch.object(lit,'web') as web:
            job=Job(ctx,'Find methods','test',provider=provider,literature=lit);job.run();web.assert_not_called()
        self.assertEqual(job.state['status'],'completed');self.assertEqual(len(queries),2)
        self.assertNotIn('P1',job.state['sources']);self.assertEqual(before,self.bytes())
    def test_early_web_fallback_is_blocked(self):
        ctx=self.ctx();lit=Literature()
        with patch.object(lit,'web') as web:
            job=Job(ctx,'Find methods','test',provider=Fake([step('search_web',query='methods'),step('answer',answer=answer(ctx))]),literature=lit)
            job.run();web.assert_not_called()
        self.assertTrue(any('second distinct' in a.get('error','') for a in job.state['activity']))

# Avoid re-running the inherited contract suite in this module.
def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(RelevanceTests)
    for name in ('test_irrelevant_hit_then_focused_search_and_accepted_method','test_early_web_fallback_is_blocked'):
        suite.addTest(RoutingTests(name))
    return suite
