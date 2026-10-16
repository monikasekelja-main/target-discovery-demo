"""Exact-version, read-only assistant context. Never opens a writable workflow store."""
from contextlib import closing
from pathlib import Path
import hashlib
import json
from contracts import DecisionBrief, content_fingerprint
from ui_service import connect, load_run, list_reports, get_report


def context(workspace,run_id,assessment_id):
    run=load_run(workspace,run_id)
    brief=next(b for b in run['assessments'] if b['assessment_id']==assessment_id)
    snapshots={}
    with closing(connect(workspace)) as db:
        for path,sha in brief['versions']['input_content_sha256'].items():
            if not path.startswith('runtime/'):continue
            row=db.execute('SELECT source_text FROM snapshots WHERE run_id=? AND relative_path=? AND sha256=? LIMIT 1',(run_id,path,sha)).fetchone()
            if not row or hashlib.sha256(row[0].encode()).hexdigest()!=sha:
                raise ValueError('Missing or altered assessment snapshot: '+path)
            snapshots[path]=json.loads(row[0])
    digest=content_fingerprint(DecisionBrief.model_validate(brief))
    identity={'workspace':str(Path(workspace).resolve()),'run_id':run_id,'assessment_id':assessment_id,'assessment_sha256':digest}
    return {'binding':identity,'brief':brief,'snapshots':snapshots,
            'current':run['inputs_current'] and assessment_id==run['state']['current_assessment_id'],
            'reports':[r for r in list_reports(workspace,run_id) if r['assessment_id']==assessment_id]}


def read_assessment(ctx):
    return {'brief':ctx['brief'],'current':ctx['current'],'policy':ctx['snapshots']['runtime/policy.json'],
            'registered_measurements':{k:v for k,v in ctx['snapshots'].items() if k.startswith('runtime/experiments/')},
            'binding':ctx['binding'],'available_reports':ctx['reports'],
            'figure_templates':['effect_intervals','qc_comparison'],
            'data_reference':'selected_assessment','notice':'DEMO-R1 and all target-specific data are fictional. No clinical efficacy or systemic safety is established.'}


def read_evidence(ctx,ids):
    records=ctx['snapshots']['runtime/initial_evidence.json']['records']
    selected=[r for r in records if not ids or r['id'] in ids]
    if ids and set(ids)-{r['id'] for r in selected}:raise ValueError('Unknown evidence ID.')
    return {'records':selected,'limitations':ctx['brief']['excluded_or_limited_evidence'],
            'contradictory_ids':ctx['brief']['challenging_evidence_ids'],'notice':'Synthetic source records, not publications. Preserve unresolved entities and evidence families.'}


def read_report(ctx,attempt):
    if attempt not in [r['attempt_id'] for r in ctx['reports']]:raise ValueError('Choose a saved report for this assessment.')
    report=get_report(ctx['binding']['workspace'],ctx['binding']['run_id'],attempt)
    return {'mode':report.get('mode'),'effective_status':report.get('effective_status',report['status']),
            'analyst':report.get('analyst'),'challenger':report.get('challenger'),'binding':report['binding'],
            'notice':'Advisory interpretation only. Scripted or stale reports are not current scientific evidence.'}
