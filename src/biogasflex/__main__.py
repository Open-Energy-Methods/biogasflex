"""BiogasFlex command-line entry points."""
import argparse
import json
from pathlib import Path
from .baseline import run as baseline_run
from .dispatch import run_dispatch, run_sweep
from .heat_dispatch import run_heat_dispatch
from .svk import fetch_local_day

parser = argparse.ArgumentParser(description='BiogasFlex 0.9.2: audited baseline, heat-aware dispatch and conditional service security')
sub = parser.add_subparsers(dest='command', required=True)
p = sub.add_parser('fetch-svk', help='Retrieve a licensed day of historical SE3 prices')
p.add_argument('--output', type=Path, default=Path('data/external/svk_se3_20200101.csv'))
p = sub.add_parser('baseline', help='Legacy fixed-operation baseline')
p.add_argument('--config', type=Path, default=Path('config/baseline.json'))
p.add_argument('--prices', type=Path, default=Path('data/synthetic/prices_4h.csv'))
p.add_argument('--output', type=Path, default=Path('results/v0.5/latest.json'))
p.add_argument('--mode', choices=['synthetic','observed'], default='synthetic')
for command in ('dispatch','sweep'):
    p=sub.add_parser(command,help='v0.6 verified storage dispatch' if command=='dispatch' else 'Predeclared storage capacity sweep')
    p.add_argument('--config',type=Path,default=Path('config/v06_lovsta_counterfactual.json'))
    p.add_argument('--prices',type=Path,default=Path('data/observed/svk_se3_20200101_CC-BY-4.0.csv'))
    p.add_argument('--output',type=Path,default=Path('results/v0.6/'+command+'.json'))
    if command == 'dispatch':
        p.add_argument('--capacity-mwh-lhv',type=float,default=None)
p=sub.add_parser('heat-dispatch',help='v0.7 heat-service-constrained CHP dispatch')
p.add_argument('--config',type=Path,default=Path('config/v07_lovsta_heat_proxy.json'))
p.add_argument('--prices',type=Path,default=Path('data/observed/svk_se3_20200101_CC-BY-4.0.csv'))
p.add_argument('--output',type=Path,default=Path('results/v0.7/heat_dispatch.json'))
p.add_argument('--capacity-mwh-lhv',type=float,default=None)
p=sub.add_parser('emergency-service',help='v0.8 explicitly hypothetical gas-inflow outage and critical energy service')
p.add_argument('--config',type=Path,default=Path('config/v08_hypothetical_emergency.json'))
p.add_argument('--output',type=Path,default=Path('results/v0.8/emergency_manual.json'))
args=parser.parse_args()
if args.command == 'fetch-svk':
    result=fetch_local_day(local_date='2020-01-01',bidding_zone='SE3',output=args.output)
elif args.command == 'baseline':
    result=baseline_run(args.config,args.prices,args.output,args.mode)
elif args.command == 'heat-dispatch':
    result=run_heat_dispatch(args.config,args.prices,args.output,capacity_mwh_lhv=args.capacity_mwh_lhv)
elif args.command == 'emergency-service':
    from .resilience import optimize_emergency_service
    result=optimize_emergency_service(json.loads(args.config.read_text(encoding='utf8')))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
elif args.command == 'dispatch':
    result=run_dispatch(args.config,args.prices,args.output,capacity_mwh_lhv=args.capacity_mwh_lhv)
else:
    result=run_sweep(args.config,args.prices,args.output)
print(json.dumps(result if args.command in ('fetch-svk','baseline') else ({
    'case_id':result['case_id'], 'output_path':str(args.output),
    'status':'hypothetical_optimal',
    'energy_totals':result['energy_totals'],
    'solver':result['solver']} if args.command=='emergency-service' else {
    'case_id':result['case_id'], 'output_path':str(args.output),
    'status':'optimal' if args.command in ('dispatch','heat-dispatch') else 'all_sweep_cases_optimal',
    'incremental_gross_revenue_eur':result.get('gross_incremental_revenue_eur'),
    'incremental_economic_contribution_proxy_eur':result.get('incremental_economic_contribution_proxy_eur'),
    'sweep':result.get('cases'),
    'solver':result.get('solver')}),indent=2))
