"""Read-only UI contract and navigation tests; no live model execution."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from workflow import Workflow,PACKAGE
from agent_layer import run_agents
from agent_offline import OfflineProvider
from ui_service import list_runs,load_run,review_status,recorded_policy,get_report
from ui_charts import functional_chart,prediction_chart

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.workspace=self.base/'runs'
        self.env=patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace)});self.env.start()
        self.app=Workflow(self.workspace)
        self.app.start('case');self.app.resume('case')
    def tearDown(self):self.app.close();self.env.stop();self.temp.cleanup()
    def outcome(self,eid='X101'):
        self.app.review('case','case-A001','APPROVE','test','Synthetic test',True)
        self.app.import_result('case',eid)
    def launch(self):
        with patch.dict(os.environ,{'TARGET_DEMO_WORKSPACE':str(self.workspace)}):
            return AppTest.from_file(str(PACKAGE/'streamlit_app.py'),default_timeout=15).run()
    def test_missing_database_does_not_create_files(self):
        path=self.base/'absent'
        with self.assertRaises(ValueError):list_runs(path)
        self.assertFalse(path.exists())
    def test_reading_preserves_database_bytes(self):
        db=self.workspace/'workflow.sqlite3';before=db.read_bytes()
        run=load_run(self.workspace,'case')
        self.assertFalse(review_status(run,run['assessments'][-1])[1])
        self.assertEqual(before,db.read_bytes())
    def test_readonly_connection_rejects_writes(self):
        from ui_service import connect
        import sqlite3
        db=connect(self.workspace)
        try:
            with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM runs')
        finally:db.close()
    def test_current_and_historical_review_differ(self):
        self.outcome();run=load_run(self.workspace,'case')
        self.assertEqual(review_status(run,run['assessments'][0])[0],'Historical assessment')
        self.assertFalse(review_status(run,run['assessments'][0])[1])
        self.assertEqual(review_status(run,run['assessments'][-1])[0],'Pending human review')
    def test_stale_inputs_disable_effective_approval(self):
        self.app.review('case','case-A001','APPROVE','test','test',True)
        root=self.base/'changed';shutil.copytree(PACKAGE/'runtime',root/'runtime')
        p=root/'runtime/policy.json';p.write_text(p.read_text()+'\n')
        run=load_run(self.workspace,'case',root)
        self.assertFalse(run['inputs_current'])
        self.assertFalse(review_status(run,run['assessments'][-1])[1])
    def test_charts_use_saved_intervals_and_distinct_units(self):
        self.outcome();run=load_run(self.workspace,'case');b=run['assessments'][-1]
        fig=functional_chart(b,20)
        self.assertEqual(fig.data[0].x[0],b['functional_effects']['KD-A']['mean'])
        self.assertIn('Relative reduction',fig.layout.xaxis.title.text)
        self.assertIn('standardized units',prediction_chart(run['state']['prediction']).layout.yaxis.title.text)
    def test_historical_policy_is_bound_to_selected_assessment(self):
        run=load_run(self.workspace,'case');brief=run['assessments'][0]
        expected=recorded_policy(run,brief)['minimum_useful_reduction_pct']
        run['state']['snapshots']['runtime/policy.json']['text']='{}'
        self.assertEqual(recorded_policy(run,brief)['minimum_useful_reduction_pct'],expected)
    def test_initial_ui_no_measurement_or_mutation(self):
        db=self.workspace/'workflow.sqlite3';before=db.read_bytes()
        at=self.launch();self.assertFalse(at.exception)
        self.assertTrue(any('not yet measured' in x.value for x in at.info))
        self.assertEqual(before,db.read_bytes())
        self.assertEqual(len(at.button),0)
    def test_all_views_and_sources_make_no_provider_calls(self):
        run_agents(self.workspace,'case','offline',OfflineProvider())
        before={str(p.relative_to(self.workspace)):p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        with patch('agent_provider.OpenAIProvider.complete',side_effect=AssertionError('Unexpected API call')):
            at=self.launch()
            for view in ['Evidence & prediction','Challenge & review','Specialist handoff','Decision']:
                at.radio(key='view').set_value(view).run();self.assertFalse(at.exception)
        after={str(p.relative_to(self.workspace)):p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_cell_loss_shows_diagnostic_warning(self):
        self.outcome('X104');at=self.launch();self.assertFalse(at.exception)
        self.assertTrue(any('Diagnostic estimates only' in e.value for e in at.error))
    def test_saved_handoff_rendered_as_simulation(self):
        self.outcome();self.app.review('case','case-A002','APPROVE','test','test',True);self.app.handoff('case','case-A002')
        at=self.launch();at.radio(key='view').set_value('Specialist handoff').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('Simulated specialist response' in e.value for e in at.warning))
    def test_missing_report_does_not_generate_one(self):
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('No saved agent report' in e.value for e in at.info))
        self.assertFalse((self.workspace/'agent-reports').exists())
    def test_deferred_review_is_readable_above_saved_report(self):
        self.outcome()
        run_agents(self.workspace,'case','offline',OfflineProvider())
        reason='Wait for independent donor replication before progressing.'
        self.app.review('case','case-A002','DEFER','Review owner',reason)
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        self.assertFalse(at.exception)
        self.assertTrue(any(x.value=='Human decision: Deferred' for x in at.subheader))
        self.assertTrue(any(x.value==reason for x in at.markdown))
        self.assertTrue(any('Progression is on hold' in x.value for x in at.warning))
        self.assertTrue(any('Human review: Deferred' in x.value for x in at.info))
        self.assertFalse(any('Report ready for human review' in x.value for x in at.success))
        at.selectbox(key='assessment_id').set_value('case-A001').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('Historical assessment — this saved decision is not current authorization' in x.value for x in at.warning))
    def test_challenger_pass_labels_bound_claims(self):
        report,_=run_agents(self.workspace,'case','offline',OfflineProvider())
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        self.assertFalse(at.exception)
        text='\n'.join(x.value for x in at.markdown)
        self.assertIn('Same-donor methods not claimed as independent replication',text)
        self.assertIn('Expression reduction not claimed equivalent to receptor blockade',text)
        self.assertTrue(any('not proof of replication' in x.value for x in at.caption))
        self.assertTrue(any('Scripted offline test — not model reasoning' in x.value for x in at.info))
        for citation in report['analyst']['current_evidence']['citations']:
            self.assertTrue(any(citation['quote'].strip()==x.value for x in at.text))
    def test_saved_live_origin_label_without_provider_execution(self):
        # Mock only the report projection; do not relabel a saved scripted artifact.
        report,_=run_agents(self.workspace,'case','offline',OfflineProvider())
        projected=copy.deepcopy(report);projected['mode']='live_llm'
        with patch('ui_service.get_report',return_value=projected), patch('agent_provider.OpenAIProvider.complete',side_effect=AssertionError('Unexpected API call')):
            at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('Captured live LLM output — no call is running' in x.value for x in at.info))
    def test_legacy_and_stale_report_remain_readable(self):
        report,directory=run_agents(self.workspace,'case','old',OfflineProvider())
        a=report['analyst'];a['hypothesis']=a.pop('hypothesis_under_test');a.pop('current_evidence')
        report['binding']['prompt_version']='older-version'
        (directory/'report.json').write_text(json.dumps(report))
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('Legacy report' in e.value for e in at.warning))
        self.assertTrue(any('Historical / stale report' in e.value for e in at.warning))
    def test_metadata_only_run_is_inspectable(self):
        self.app.start('pending')
        at=self.launch();at.selectbox(key='run_id').set_value('pending').run()
        self.assertFalse(at.exception)
        self.assertTrue(any('No complete assessment' in e.value for e in at.info))

    def check_local_ui(self,at):
        next(x for x in at.selectbox if x.label=='Rationale check mode').set_value('Local checks only — no AI').run()
        at.button(key='check_rationale').click().run()
        self.assertFalse(at.exception)

    def accept_ui_advice(self,at):
        next(x for x in at.checkbox if x.label=='I have read the feedback and understand its limitations').check()
        next(x for x in at.checkbox if x.label=='I explicitly override the concerns or unavailable AI review').check()
        next(x for x in at.text_area if x.label=='Why proceed despite the concerns or missing AI review?').set_value('This synthetic UI test explicitly bypasses semantic checking to verify local control flow.')
        next(x for x in at.checkbox if x.label.startswith('I reviewed this exact assessment')).check()

    def test_explicit_ui_review_and_handoff(self):
        self.outcome();at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        at.button(key='prepare_review').click().run();self.assertFalse(at.exception)
        at.text_input[0].set_value('UI test reviewer')
        next(x for x in at.selectbox if x.label=='Human decision').set_value('APPROVE')
        at.text_area[0].set_value('Approve only this synthetic local action.')
        self.check_local_ui(at)
        next(x for x in at.button if x.label=='Record human decision').click().run()
        self.assertTrue(any('acknowledgement' in x.value for x in at.error))
        self.assertFalse(self.app.show('case')['approval_effective'])
        self.accept_ui_advice(at)
        next(x for x in at.button if x.label=='Record human decision').click().run()
        self.assertFalse(at.exception);self.assertTrue(self.app.show('case')['approval_effective'])
        at.radio(key='view').set_value('Specialist handoff').run()
        at.button(key='prepare_handoff').click().run()
        at.checkbox[0].check()
        next(x for x in at.button if x.label=='Create local simulated handoff').click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any('Simulated specialist response' in e.value for e in at.warning))

    def test_ui_submission_retains_preview_digest_across_rerun(self):
        self.outcome();at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        at.button(key='prepare_review').click().run()
        at.text_input[0].set_value('UI reviewer')
        next(x for x in at.selectbox if x.label=='Human decision').set_value('APPROVE')
        at.text_area[0].set_value('Old preview about assay replication');self.check_local_ui(at)
        self.app.review('case','case-A002','DEFER','Concurrent reviewer','Changed decision')
        self.accept_ui_advice(at)
        next(x for x in at.button if x.label=='Record human decision').click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any('review changed' in x.value for x in at.error))
        self.assertEqual(self.app.show('case')['review']['decision'],'DEFER')

    def test_handoff_button_disabled_without_human_approval(self):
        self.outcome();run_agents(self.workspace,'case','ready',OfflineProvider())
        at=self.launch();at.radio(key='view').set_value('Specialist handoff').run()
        self.assertTrue(at.button(key='prepare_handoff').disabled)

    def test_ui_amend_creates_unapproved_version(self):
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        at.button(key='prepare_review').click().run()
        at.text_input[0].set_value('UI reviewer')
        next(x for x in at.selectbox if x.label=='Human decision').set_value('AMEND')
        at.text_area[0].set_value('Clarify next step');at.text_area[1].set_value('Discuss assay design with biology.')
        self.check_local_ui(at);self.accept_ui_advice(at)
        next(x for x in at.button if x.label=='Record human decision').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(self.app.show('case')['assessment']['assessment_id'],'case-A002')
        self.assertEqual(at.selectbox(key='assessment_id').value,'case-A002')
        self.assertFalse(self.app.show('case')['approval_effective'])

    def test_cherries_feedback_and_edited_rationale_invalidate_ui_check(self):
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        at.button(key='prepare_review').click().run()
        self.assertTrue(next(x for x in at.button if x.label=='Record human decision').disabled)
        at.text_input[0].set_value('UI reviewer');at.text_area[0].set_value('this was not acceptable because of the cherries')
        self.check_local_ui(at)
        self.assertTrue(any('Revise your rationale' in x.value for x in at.warning))
        self.assertTrue(any('not identify an assessment finding' in x.value for x in at.markdown))
        self.assertFalse(self.app.show('case')['approval_effective'])
        at.text_area[0].set_value('The donor replication evidence needs more review.').run()
        self.assertTrue(any('Draft changed since the check' in x.value for x in at.warning))
        self.assertTrue(next(x for x in at.button if x.label=='Record human decision').disabled)

    def test_mocked_ai_feedback_never_saves_automatically(self):
        from verify_advisor import FakeAdvisor
        provider=FakeAdvisor('NO_CONCERNS_IDENTIFIED')
        at=self.launch();at.radio(key='view').set_value('Challenge & review').run()
        at.button(key='prepare_review').click().run()
        at.text_input[0].set_value('UI reviewer');at.text_area[0].set_value('Replicate the functional effect in independent donors.').run()
        with patch('agent_provider.OpenAIProvider',return_value=provider):
            at.button(key='check_rationale').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(len(provider.calls),1)
        self.assertTrue(any('No concerns identified' in x.value for x in at.success))
        self.assertFalse(self.app.show('case')['approval_effective'])

    def test_programme_context_scope_and_boundaries(self):
        from ui_programme_context import context_for
        brief=load_run(self.workspace,'case')['assessments'][-1]
        original=copy.deepcopy(brief)
        context=context_for(brief)
        self.assertEqual(context['version'],'programme-context-v1')
        self.assertEqual(len(context['references']),2)
        self.assertIsNone(context_for({**brief,'target_id':'OTHER'}))
        self.assertEqual(brief,original)
        at=self.launch();self.assertFalse(at.exception)
        self.assertTrue(any(x.value=='Plaque psoriasis | DEMO-R1' for x in at.subheader))
        self.assertTrue(any('Synthetic target; mechanism untested' in x.value for x in at.caption))
        self.assertTrue(any(x.label=='Programme hypothesis and scope' and not x.proto.expanded for x in at.expander))
        for label in ['Published disease background','Synthetic target-specific evidence and frozen predictions','Untested mechanistic and differentiation hypotheses']:
            self.assertTrue(any(label in x.value for x in at.markdown))
        with patch('ui_service.load_run',return_value={**load_run(self.workspace,'case'),
                'assessments':[{**brief,'context_id':'MISMATCH'}]}):
            at=self.launch()
            self.assertTrue(any('Programme assay context does not match' in x.value for x in at.warning))

    def test_programme_context_keeps_each_saved_decision_and_records(self):
        from ui_service import ACTIONS
        for rid,eid in [('supportive','X101'),('contrary','X102'),('imprecise','X103'),('cell-loss','X104')]:
            self.app.start(rid);self.app.resume(rid)
            self.app.review(rid,rid+'-A001','APPROVE','test','Synthetic test',True)
            self.app.import_result(rid,eid)
        before={str(p):p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        with patch('agent_provider.OpenAIProvider.complete',side_effect=AssertionError('API call')), \
             patch('evidence_search.fetch',side_effect=AssertionError('External retrieval')):
            at=self.launch()
            for rid in ['case','supportive','contrary','imprecise','cell-loss']:
                at.selectbox(key='run_id').set_value(rid).run()
                self.assertFalse(at.exception)
                run=load_run(self.workspace,rid);brief=run['assessments'][-1]
                self.assertTrue(any(x.value==ACTIONS[brief['scientific_recommendation']] for x in at.subheader))
                if brief['functional_effects']:
                    chart=json.loads(at.get('plotly_chart')[0].proto.spec)
                    expected=functional_chart(brief,recorded_policy(run,brief)['minimum_useful_reduction_pct']).to_plotly_json()
                    self.assertEqual(chart['layout']['shapes'],expected['layout']['shapes'])
                    self.assertEqual(chart['data'][0]['x'],expected['data'][0]['x'])
        after={str(p):p.read_bytes() for p in self.workspace.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

if __name__=='__main__':unittest.main()
