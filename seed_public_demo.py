"""Create a fresh synthetic public replay without network access or model calls.

Refuses to overwrite an existing workspace. Reviews are simulated; follow-up
notes are authored scenario text, not evidence that additional work occurred.
"""
from pathlib import Path
import argparse
from unittest.mock import patch
from workflow import Workflow
from followup_service import FollowupWorkflow, prepare_followup
from agent_layer import run_agents
from agent_offline import OfflineProvider

CASES={'demo':'X101','test-initial':None,'test-contrary':'X102',
       'test-cell-loss':'X104','test-disagreement':'X107','test-imprecise':'X103'}
ROLE='Demo biology reviewer (scripted)'
INITIAL='Scripted example: approve the scoped synthetic experiment under the provisional criteria.'
APPROVAL=('Scripted example: approve new-donor/batch replication and target-specificity work only. '
          'The two methods clear the provisional useful-effect criterion but share the same eight donors. '
          'Independent replication, specificity, antibody blockade equivalence and systemic safety remain unestablished. '
          'This is not target validation or programme approval.')


def create_run(workspace,run_id,experiment,followups=False):
    app=Workflow(workspace)
    try:
        app.start(run_id);app.resume(run_id)
        if experiment:
            app.review(run_id,run_id+'-A001','APPROVE',ROLE,INITIAL,True)
            app.import_result(run_id,experiment)
        if experiment=='X101':
            if followups:
                app.review(run_id,run_id+'-A002','DEFER',ROLE,
                           'Scripted example: clarify the scope of the proposed next work before approving it.',True)
                service=FollowupWorkflow(workspace)
                try:
                    for status,note in [('Planned','Scripted plan; no additional experiments performed.'),
                                        ('Ready for re-review','Scripted clarification: approval is sought only for replication and specificity work. No new experimental results are claimed.')]:
                        service.save_followup(prepare_followup(workspace,run_id,run_id+'-A002'),
                            'Clarify the proposed replication and target-specificity scope.',
                            'Demo assay team (scripted)',
                            'Scoped next-action clarification available for review.',status,note)
                finally:service.close()
            app.review(run_id,run_id+'-A002','APPROVE',ROLE,APPROVAL,True)
            app.handoff(run_id,run_id+'-A002')
        app.export(run_id)
    finally:app.close()
    run_agents(workspace,run_id,'offline-public-01',OfflineProvider())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('public-replay-new'))
    parser.add_argument('--bundled-reference',action='store_true',help='Create reference workspaces as well as the six main cases')
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new directory. Existing records are never overwritten.')
    with patch('socket.socket.connect',side_effect=AssertionError('Network is forbidden during public replay creation')):
        workspace=args.output/'demo-runs'
        for rid,experiment in CASES.items():create_run(workspace,rid,experiment,followups=rid=='demo')
        if args.bundled_reference:
            root=args.output/'recorded_examples'
            create_run(root/'state','recorded-supportive','X101')
            create_run(root/'agents/state','recorded-initial',None)
            create_run(root/'agents/state','recorded-supportive','X101')
            import shutil
            shutil.copytree(root/'state/exports/recorded-supportive',root/'supportive')
    print('Created fresh synthetic cases with simulated reviews and offline reports. No model or network calls.')

if __name__=='__main__':main()
