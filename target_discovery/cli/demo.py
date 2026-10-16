"""Command-line reference workflow. All biology and service responses are synthetic."""
from __future__ import annotations
from target_discovery.paths import PROJECT_ROOT

import argparse
import json
import sqlite3
from pathlib import Path
import sys

from target_discovery.workflow.workflow import SCENARIOS, Workflow, WorkflowError


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,default=PROJECT_ROOT/'demo-runs',help='SQLite state and exports (default: demo-runs/)')
    p.add_argument('--json',action='store_true',help='Emit structured output')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['start','resume','show','review','amend','import-result','refresh','handoff','replay','export']:
        cmd=sub.add_parser(name)
        cmd.add_argument('--run-id',required=True)
        if name=='start':cmd.add_argument('--scenario',choices=SCENARIOS,default='standard')
        if name=='refresh':cmd.add_argument('--scenario',choices=SCENARIOS)
        if name in ['review','amend','handoff']:cmd.add_argument('--assessment',required=True)
        if name in ['review','amend']:
            cmd.add_argument('--reviewer',required=True)
            cmd.add_argument('--rationale',required=True)
        if name=='review':
            cmd.add_argument('--decision',choices=['approve','defer'],required=True)
            cmd.add_argument('--simulated',action='store_true',help='Mark this review as a scripted simulation, not operator review')
        if name=='amend':cmd.add_argument('--next-action',required=True)
        if name=='import-result':cmd.add_argument('--experiment',required=True)
        if name=='export':cmd.add_argument('--output',type=Path)
    return p


def human_output(value):
    if 'events' in value:
        lines=[f"Recorded run {value['run_id']} — {value['replay_mode']}"]
        for e in value['events']:
            p=e['payload'];detail=p.get('proposed_action') or p.get('status') or p.get('step') or p.get('assessment_id') or ''
            if e['kind']=='TOOL_RESULT':detail=f"{p['tool']} → {p['response']['status']} (attempt {p['attempt']})"
            lines.append(f"{e['event_id']:03}  {e['kind']}  {detail}")
        return '\n'.join(lines)
    if 'export_directory' in value:return f"Exported synthetic run to {value['export_directory']}"
    lines=['SYNTHETIC DEMO — fixed code, frozen model responses, no agents',
        f"Run {value['run_id']} · revision {value['revision']} · {value['phase']}",
        f"Workflow: {value['workflow_status']} · review: {value['review_status']} · approval effective: {value['approval_effective']}"]
    if not value['inputs_current']:lines.append('Inputs changed: previous approval is stale. Refresh and review again.')
    brief=value['assessment']
    if brief:
        lines.extend([f"Assessment: {brief['assessment_id']}",f"Proposal: {brief['scientific_recommendation']}",brief['rationale']])
        for method,s in brief['functional_effects'].items():
            lines.append(f"  {method}: {s['mean']:.1f}% reduction (95% CI {s['lower_95']:.1f} to {s['upper_95']:.1f}); n={s['n_donors']}")
        if brief['failed_gates']:lines.append(f"  {len(brief['failed_gates'])} failed gates; estimates are diagnostic only. See JSON/export for reasons.")
        lines.append(f"Next action: {brief['next_action']}")
    if value['block_reason']:lines.append('Blocked: '+json.dumps(value['block_reason'],ensure_ascii=False))
    if value['specialist_response']:
        r=value['specialist_response'];lines+=['Simulated specialist: '+r['status'],r['reason'],'Owner: '+r['next_owner_role']]
    lines.append('Next: '+value['next_command'])
    return '\n'.join(lines)


def main(argv=None):
    args=parser().parse_args(argv)
    app=None
    try:
        app=Workflow(args.workspace)
        if args.command=='start':result=app.start(args.run_id,args.scenario)
        elif args.command=='resume':result=app.resume(args.run_id)
        elif args.command=='show':result=app.show(args.run_id)
        elif args.command=='review':result=app.review(args.run_id,args.assessment,args.decision.upper(),args.reviewer,args.rationale,args.simulated)
        elif args.command=='amend':result=app.amend(args.run_id,args.assessment,args.reviewer,args.rationale,args.next_action)
        elif args.command=='import-result':result=app.import_result(args.run_id,args.experiment)
        elif args.command=='refresh':result=app.refresh(args.run_id,args.scenario)
        elif args.command=='handoff':result=app.handoff(args.run_id,args.assessment)
        elif args.command=='replay':result=app.replay(args.run_id)
        else:result=app.export(args.run_id,args.output)
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False) if args.json else human_output(result))
        return 3 if result.get('phase')=='BLOCKED' else 0
    except (WorkflowError,ValueError,OSError,sqlite3.Error) as exc:
        if args.json:print(json.dumps({'error':str(exc),'type':type(exc).__name__}),file=sys.stderr)
        else:print('Error: '+str(exc),file=sys.stderr)
        return 2
    finally:
        if app:app.close()


if __name__=='__main__':raise SystemExit(main())
