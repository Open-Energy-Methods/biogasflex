"""BiogasFlex command-line entry points."""
import argparse
import json
import math
from pathlib import Path
from .baseline import Interval, run as baseline_run
from .dispatch import run_dispatch, run_sweep
from .heat_dispatch import run_heat_dispatch, load_heat_case
from .experimental_v095 import optimize_operating_surrogate, evaluate_fixed_forecast_schedule
from .experimental_v096 import optimize_commitment_milp
from .experimental_v097 import optimize_commitment_milp as optimize_hourly_commitment
from .experimental_v098 import evaluate_rolling_prices
from .svk import fetch_local_day

parser = argparse.ArgumentParser(description='BiogasFlex 0.9.8: audited baseline, heat-aware dispatch and conditional service security')
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
p=sub.add_parser('operating-surrogate', help='v0.9.5 EXPERIMENTAL continuously-on CHP ramp/minimum-power LP')
p.add_argument('--config',type=Path,default=Path('examples/v095_toy_config.json'))
p.add_argument('--prices',type=Path,default=Path('examples/v095_toy_realized_prices.csv'))
p.add_argument('--output',type=Path,default=None)
p=sub.add_parser('forecast-regret',help='v0.9.5 EXPERIMENTAL fixed synthetic forecast schedule versus realized prices')
p.add_argument('--config',type=Path,default=Path('examples/v095_toy_config.json'))
p.add_argument('--forecast-prices',type=Path,default=Path('examples/v095_toy_forecast_prices.csv'))
p.add_argument('--realized-prices',type=Path,default=Path('examples/v095_toy_realized_prices.csv'))
p.add_argument('--output',type=Path,default=None)
p=sub.add_parser('unit-commitment',help='v0.9.6 EXPERIMENTAL binary CHP on/off/start/stop MILP (not equipment-calibrated)')
p.add_argument('--config',type=Path,default=Path('examples/v096_commitment_toy.json'))
p.add_argument('--prices',type=Path,default=Path('examples/v096_commitment_toy_prices.csv'))
p.add_argument('--output',type=Path,default=None,help='Opt-in output of full JSON report; no file written by default')
p=sub.add_parser('hourly-commitment',help='v0.9.7 EXPERIMENTAL clock-hour CHP on/off dwell with declared carry-in')
p.add_argument('--config',type=Path,default=Path('examples/v097_fractional_hour_config.json'))
p.add_argument('--prices',type=Path,default=Path('examples/v097_fractional_hour_prices.csv'))
p.add_argument('--output',type=Path,default=None,help='Optional full experimental JSON; stdout summary by default')
p=sub.add_parser('rolling-forecast',help='v0.9.8 EXPERIMENTAL synthetic price-only forecast/execute/replan with fixed terminal gas stock')
p.add_argument('--config',type=Path,default=Path('examples/v098_toy_config.json'))
p.add_argument('--realized-prices',type=Path,default=Path('examples/v098_toy_realized_prices.csv'))
p.add_argument('--forecast-snapshots',type=Path,default=Path('examples/v098_toy_forecast_snapshots.json'))
p.add_argument('--output',type=Path,default=None,help='Opt-in full JSON report; otherwise summary only')
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
elif args.command == 'operating-surrogate':
    cfg, intervals=load_heat_case(args.config,args.prices)
    result=optimize_operating_surrogate(cfg,intervals)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'forecast-regret':
    cfg, forecast=load_heat_case(args.config,args.forecast_prices)
    _, realized=load_heat_case(args.config,args.realized_prices)
    result=evaluate_fixed_forecast_schedule(cfg,forecast,realized)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'unit-commitment':
    cfg, intervals=load_heat_case(args.config,args.prices)
    result=optimize_commitment_milp(cfg,intervals)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'hourly-commitment':
    cfg, intervals=load_heat_case(args.config,args.prices)
    result=optimize_hourly_commitment(cfg,intervals)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'rolling-forecast':
    cfg, realized=load_heat_case(args.config,args.realized_prices)
    forecast_file=json.loads(args.forecast_snapshots.read_text(encoding='utf-8'))
    forecasts=forecast_file.get('forecasts_eur_per_mwh') if isinstance(forecast_file,dict) else None
    if not isinstance(forecasts,list) or len(forecasts)!=len(realized):
        raise ValueError('One remaining-horizon forecast list per realized interval required')
    snapshots=[]
    for t,suffix in enumerate(forecasts):
        if not isinstance(suffix,list) or len(suffix)!=len(realized)-t:
            raise ValueError(f'Forecast snapshot {t} must span all remaining intervals')
        if any(type(p) not in (int,float) or not math.isfinite(p) for p in suffix):
            raise ValueError('Forecast prices must be finite numbers and not booleans')
        snapshots.append([Interval(row.start_utc,float(p),row.hours,row.zone)
                          for row,p in zip(realized[t:],suffix)])
    result=evaluate_rolling_prices(cfg,realized,snapshots)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'dispatch':
    result=run_dispatch(args.config,args.prices,args.output,capacity_mwh_lhv=args.capacity_mwh_lhv)
else:
    result=run_sweep(args.config,args.prices,args.output)
if args.command in ('operating-surrogate','forecast-regret','unit-commitment','hourly-commitment','rolling-forecast'):
    print(json.dumps({
        'status':'EXPERIMENTAL_NOT_PLANT_VALIDATED',
        'model_type':result['model_type'],
        'case_id':result.get('case_id',cfg['case_id']),
        'output_path':str(args.output) if args.output is not None else None,
        'incremental_contribution_eur':result.get('incremental_contribution_eur'),
        'net_contribution_eur':result.get('net_contribution_eur'),
        'steps_executed':result.get('steps_executed'),
        'rolling_realized_contribution_eur':result.get('rolling_realized_contribution_eur'),
        'perfect_foresight_net_contribution_eur':result.get('perfect_foresight_net_contribution_eur'),
        'start_count':result.get('start_count'),
        'stop_count':result.get('stop_count'),
        'fixed_reference_feasible':result.get('fixed_reference_feasible'),
        'carry_in_remaining_dwell_hours':result.get('carry_in_remaining_dwell_hours'),
        'carry_in_remaining_after_horizon_hours':result.get('carry_in_remaining_after_horizon_hours'),
        'perfect_foresight_regret_eur':result.get('perfect_foresight_regret_eur'),
        'realized_increment_over_fixed_eur':result.get('realized_increment_over_fixed_eur')
    },indent=2))
else:
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
