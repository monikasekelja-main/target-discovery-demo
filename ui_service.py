"""Read-only projection of existing runs. Never creates a DB or invokes a workflow."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from contracts import DecisionBrief, content_fingerprint
from workflow import PACKAGE, BASE_INPUTS, IMPLEMENTATION_FILES, EXPERIMENT_IDS, checked_id
from agent_layer import load_report


def connect(workspace):
    path=Path(workspace).expanduser().resolve()/'workflow.sqlite3'
    if not path.is_file():raise ValueError('No saved workflow database in this directory.')
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def list_runs(workspace):
    with closing(connect(workspace)) as db:
        return [dict(r) for r in db.execute('SELECT run_id,updated_at FROM runs ORDER BY updated_at DESC')]


def load_run(workspace,run_id,root=PACKAGE):
    checked_id(run_id)
    with closing(connect(workspace)) as db:
        db.execute('BEGIN')
        row=db.execute('SELECT state FROM runs WHERE run_id=?',(run_id,)).fetchone()
        if row is None:raise ValueError('Saved run not found.')
        state=json.loads(row['state'])
        briefs=[json.loads(r['brief']) for r in db.execute('SELECT brief FROM assessments WHERE run_id=? ORDER BY rowid',(run_id,))]
        reviews=[json.loads(r['review']) for r in db.execute('SELECT review FROM reviews WHERE run_id=? ORDER BY rowid',(run_id,))]
        events=[{'event_id':r['event_id'],'kind':r['kind'],'created_at':r['created_at'],'payload':json.loads(r['payload'])}
                for r in db.execute('SELECT * FROM events WHERE run_id=? ORDER BY event_id',(run_id,))]
        policy_snapshots=[dict(r) for r in db.execute('SELECT sha256,source_text FROM snapshots WHERE run_id=? AND relative_path=?',(run_id,'runtime/policy.json'))]
    for brief in briefs:DecisionBrief.model_validate(brief)
    allowed=set(BASE_INPUTS)|{f'runtime/experiments/{eid}.json' for eid in EXPERIMENT_IDS}
    changes=[]
    for relative,snapshot in state['snapshots'].items():
        if relative not in allowed:raise ValueError('Unexpected recorded source path.')
        if hashlib.sha256(snapshot['text'].encode()).hexdigest()!=snapshot['sha256']:
            raise ValueError('Recorded source integrity check failed.')
        try:actual=hashlib.sha256((Path(root)/relative).read_text().encode()).hexdigest()
        except OSError:actual=None
        if actual!=snapshot['sha256']:changes.append(relative)
    for name in IMPLEMENTATION_FILES:
        actual=hashlib.sha256((PACKAGE/name).read_text().encode()).hexdigest()
        if state['implementation_sha256'].get('implementation/'+name)!=actual:changes.append(name)
    return {'state':state,'assessments':briefs,'reviews':reviews,'events':events,
            'inputs_current':not changes,'changed_inputs':changes,'policy_snapshots':policy_snapshots}


def review_status(run,brief):
    if brief is None:return 'Not yet assessed',False,None
    historical=brief['assessment_id']!=run['state']['current_assessment_id']
    reviews=[r for r in run['reviews'] if r['assessment_id']==brief['assessment_id']]
    review=reviews[-1] if reviews else None
    bound=bool(review and review['reviewed_content_sha256']==content_fingerprint(DecisionBrief.model_validate(brief)))
    if historical:return 'Historical assessment',False,review
    if not run['inputs_current']:return 'Stale — refresh needed',False,review
    if review and not bound:return 'Review binding mismatch',False,review
    if not review:return 'Pending human review',False,None
    return {'APPROVE':'Approved local-demo action','DEFER':'Deferred','AMEND':'Amended'}.get(review['decision'],review['decision']),bound and review['decision']=='APPROVE',review


def list_reports(workspace,run_id):
    checked_id(run_id)
    parent=Path(workspace).resolve()/'agent-reports'/run_id
    if not parent.is_dir():return []
    results=[]
    for path in parent.glob('*/report.json'):
        if path.is_symlink() or not path.resolve().is_relative_to(parent.resolve()):continue
        try:
            checked_id(path.parent.name)
            data=json.loads(path.read_text())
            if data['binding']['run_id']!=run_id:continue
            results.append({'attempt_id':path.parent.name,'assessment_id':data['binding']['assessment_id'],
                            'mode':data.get('mode','unknown'),'created_at':data.get('created_at','')})
        except (ValueError,KeyError,OSError,TypeError):continue
    return sorted(results,key=lambda r:r['created_at'],reverse=True)


def get_report(workspace,run_id,attempt_id):
    return load_report(workspace,run_id,attempt_id)


ACTIONS={'EXPERIMENT_TO_RESOLVE_UNCERTAINTY':'Propose a functional experiment',
         'ADVANCE_TO_REPLICATION':'Propose independent replication',
         'DEPRIORITIZE_TESTED_HYPOTHESIS':'Deprioritize this tested hypothesis',
         'INCONCLUSIVE':'Resolve the remaining uncertainty'}
FINDINGS={'EXPERIMENT_TO_RESOLVE_UNCERTAINTY':'Functional benefit not yet measured',
          'ADVANCE_TO_REPLICATION':'Supported within this experiment',
          'DEPRIORITIZE_TESTED_HYPOTHESIS':'Useful effect excluded in this setting',
          'INCONCLUSIVE':'Functional conclusion unresolved'}


def interval_rows(brief):
    return [{'method':name,**values} for name,values in brief['functional_effects'].items()]


def recorded_policy(run,brief):
    wanted=brief['versions']['input_content_sha256']['runtime/policy.json']
    for saved in run['policy_snapshots']:
        if saved['sha256']==wanted:
            if hashlib.sha256(saved['source_text'].encode()).hexdigest()!=wanted:
                raise ValueError('Historical policy snapshot is corrupt.')
            return json.loads(saved['source_text'])
    raise ValueError('Policy snapshot for this assessment is unavailable; no threshold fabricated.')
