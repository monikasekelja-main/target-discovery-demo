from pathlib import Path
import hashlib
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from target_discovery.ui.ui_service import list_runs,load_run,review_status,get_report
from target_discovery.workflow.contracts import DecisionBrief,content_fingerprint
from target_discovery.review.followup_service import history
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for base in ['demo-runs','recorded_examples'] for p in Path(base).rglob('*') if p.is_file()}
with patch('target_discovery.agents.agent_provider.OpenAIProvider.complete',side_effect=AssertionError('API call')),patch('target_discovery.evidence.evidence_search.fetch',side_effect=AssertionError('Retrieval')),patch('socket.socket.connect',side_effect=AssertionError('Network')):
 at=AppTest.from_file(str(Path('streamlit_app.py').resolve()),default_timeout=20).run();assert not at.exception
 at.radio(key='experience').set_value('Guided demo').run();assert not at.exception
 for step in range(4):
  assert not at.error
  at.button(key='guide_next').click().run();assert not at.exception
 at.radio(key='experience').set_value('Explore the workbench').run();assert not at.exception
 for workspace in ['My saved runs','Bundled initial & supportive','Bundled reviewed handoff']:
  at.selectbox(key='workspace_choice').set_value(workspace).run();assert not at.exception
  for rid in at.selectbox(key='run_id').options:
   at.selectbox(key='run_id').set_value(rid).run();assert not at.exception
   for view in ['Evidence & prediction','Challenge & review','Specialist handoff','Decision']:
    at.radio(key='view').set_value(view).run();assert not at.exception
r=load_run(Path('demo-runs'),'demo');b=next(x for x in r['assessments'] if x['assessment_id']=='demo-A002')
assert r['inputs_current'];label,effective,review=review_status(r,b);assert effective
assert review['actor_mode']=='simulated_human'
h=r['state']['handoff'];assert h['assessment']==b and h['review']==review
assert r['state']['specialist_response']['status']=='NEEDS_INFORMATION'
assert len(history(Path('demo-runs'),'demo'))==2
report=get_report(Path('demo-runs'),'demo','offline-public-01')
assert report['mode']=='scripted_offline_test' and report['effective_status']=='ADVISORY_READY_FOR_REVIEW'
assert report['binding']['assessment_sha256']==content_fingerprint(DecisionBrief.model_validate(b))
assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for base in ['demo-runs','recorded_examples'] for p in Path(base).rglob('*') if p.is_file()}
print('PASS: four guided steps plus nine saved runs across three workspaces, four views each; approval, follow-up, report and handoff bindings; no calls or saved-record mutations.')
