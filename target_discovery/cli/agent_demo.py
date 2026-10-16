from target_discovery.paths import PROJECT_ROOT
"""Additive analyst/challenger CLI. Reference runs and approvals remain unchanged."""
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ required; use Python 3.12 in a virtual environment. See docs/agent_layer.md.')
import argparse
import json
from pathlib import Path
from target_discovery.agents.agent_layer import run_agents, load_report, render_report
from target_discovery.agents.agent_provider import OpenAIProvider
from target_discovery.agents.agent_offline import OfflineProvider


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, default=PROJECT_ROOT/'demo-runs')
    p.add_argument('--json', action='store_true')
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('run', 'show'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--run-id', required=True)
        cmd.add_argument('--attempt-id', required=True)
        if name == 'run':
            cmd.add_argument('--provider', choices=('offline', 'openai'), required=True)
            cmd.add_argument('--model', help='Explicit Structured Outputs compatible model ID; required for openai')
    args = p.parse_args(argv)
    try:
        if args.command == 'run':
            if args.provider == 'offline' and args.model:
                raise ValueError('--model is only valid with --provider openai.')
            provider = OfflineProvider() if args.provider == 'offline' else OpenAIProvider(args.model)
            result, directory = run_agents(args.workspace, args.run_id, args.attempt_id, provider)
            if not args.json:
                print('Saved report: '+str(directory/'report.md'))
        else:
            result = load_report(args.workspace, args.run_id, args.attempt_id)
        print(json.dumps(result, indent=2) if args.json else render_report(result))
        return 0 if result.get('effective_status', result['status']) == 'ADVISORY_READY_FOR_REVIEW' else 3
    except (ValueError, OSError) as exc:
        print('Error: '+str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
