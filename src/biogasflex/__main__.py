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
from .experimental_v099 import run_manifest
from .market_v0910 import run_manifest as run_market_boundary_manifest
from .annual_chp_evidence import audit_annual_chp
from .chp_parameter_evidence import run_register
from .bounded_sensitivity_v0914b import run_manifest as run_bounded_sensitivity
from .telemetry_acquisition_v0915 import audit_telemetry
from .public_chp_sources_v0916 import run as run_public_chp_sources
from .kitakyushu_real_v0917 import run as run_kitakyushu_real_v0917
from .market_provenance_v0913 import run_market_source_audit, require_operational_validation
from .svk import fetch_local_day

parser = argparse.ArgumentParser(description='BiogasFlex 0.9.17: source-provenance auditable research CHP and strict market bid-time validation gate')
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
p=sub.add_parser('rolling-forecast',help='v0.9.8.1 EXPERIMENTAL synthetic price-only forecast/execute/replan with fixed terminal gas stock')
p.add_argument('--config',type=Path,default=Path('examples/v098_toy_config.json'))
p.add_argument('--realized-prices',type=Path,default=Path('examples/v098_toy_realized_prices.csv'))
p.add_argument('--forecast-snapshots',type=Path,default=Path('examples/v098_toy_forecast_snapshots.json'))
p.add_argument('--output',type=Path,default=None,help='Opt-in full JSON report; otherwise summary only')
p=sub.add_parser('historical-replay',help='v0.9.9 observed 2020 SE3 prices + naive causal price replay against entirely hypothetical CHP')
p.add_argument('--manifest',type=Path,default=Path('examples/v099_historical_backtest.json'))
p.add_argument('--output',type=Path,default=None,help='Opt in to write full scientific provenance and per-step replay JSON')
p=sub.add_parser('market-boundary',help='v0.9.10 EXPERIMENTAL pre/post day-ahead timing, exogenous award and exact matched synthetic CHP delivery')
p.add_argument('--manifest',type=Path,default=Path('examples/v0910_market_hourly.json'))
p.add_argument('--output',type=Path,default=None,help='Opt-in full data report; no output file created by default')
p=sub.add_parser('contract-dispatch',
    help='v0.9.11 EXPERIMENTAL hard accepted MWh equality inside CHP MILP and constrained LP relaxation')
p.add_argument('--manifest',type=Path,default=Path('examples/v0911_contract_hourly.json'))
p.add_argument('--output',type=Path,default=None,help='Opt-in full audit; no files written by default')
p.add_argument('--require-operational-validation',action='store_true',
               help='Fail closed without true historical bid-time and same-plant high-frequency telemetry')
p=sub.add_parser('market-provenance',help='v0.9.13: offline verify Svk 2020 ex-post prices and bid-time evidence limitations')
p.add_argument('--manifest',type=Path,default=Path('examples/v0913_market_provenance.json'))
p.add_argument('--output',type=Path,default=None,help='Opt-in full source/market provenance report')
p=sub.add_parser('annual-chp-evidence',help='v0.9.12: audit published 2012-2022 annual landfill-CHP records; no dispatch calibration')
p.add_argument('--csv',type=Path,default=Path('data/observed/ciula_2023_landfill_chp_annual.csv'))
p.add_argument('--output',type=Path,default=None,help='Optional full source audit JSON; otherwise summary on stdout')
p=sub.add_parser('chp-evidence-register',help='v0.9.14-A: independently source-scoped CHP manufacturer parameter audit (no equipment calibration)')
p.add_argument('--register',type=Path,default=Path('data/evidence/v0914_chp_parameter_register.json'))
p.add_argument('--output',type=Path,default=None,help='Optional JSON evidence report, no file by default')
p=sub.add_parser('bounded-sensitivity',
                 help='v0.9.14-B: EXPLICITLY SYNTHETIC 81-case factorial contract feasibility, OAT, and conditional box proofs')
p.add_argument('--manifest',type=Path,default=Path('examples/v0914b_hypothetical_sensitivity.json'))
p.add_argument('--output',type=Path,default=None,help='Optional full deterministic case table, no files written by default')
p=sub.add_parser('telemetry-qa',
    help='v0.9.15: fail-closed dry normalized gas/heat/electric 15-min raw-data QA; NOT calibrated CHP model')
p.add_argument('--manifest',type=Path,default=Path('examples/v0915_synthetic_acquisition_manifest.json'))
p.add_argument('--csv',type=Path,default=None,help='Optional private/authorized raw input CSV path outside repository')
p.add_argument('--output',type=Path,default=None,help='Optional full QA report, never write raw telemetry')
p=sub.add_parser('public-chp-sources',
    help='v0.9.16: curated two-source, real external CHP dataset provenance; --fetch opts in to licensed online downloads')
p.add_argument('--source',choices=['all','rise_lulea_2023_biogas_sofc','kitakyushu_japan_2001_2022_citygas_chp'],default='all')
p.add_argument('--fetch',action='store_true',help='Opt-in online original file MD5/SHA256 and XLSX/ZIP profile audit')
p.add_argument('--report',type=Path,default=None,help='Write provenance report outside git checkout')
p=sub.add_parser('real-chp-analysis',
    help='v0.9.17 measured Kitakyushu city-gas engine hourly 2005 3-channel source analysis, opt-in --fetch')
p.add_argument('--fetch',action='store_true',help='Download and integrity-check 3 original CC-BY archives before numerical source analysis')
p.add_argument('--report',type=Path,default=None,help='Write real-source research report outside git source checkout')
args=parser.parse_args()
if args.command == 'real-chp-analysis':
    result=run_kitakyushu_real_v0917(args.fetch,args.report)
elif args.command == 'public-chp-sources':
    result=run_public_chp_sources(args.source,args.fetch,args.report)
elif args.command == 'telemetry-qa':
    result=audit_telemetry(args.manifest,args.csv)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
elif args.command == 'bounded-sensitivity':
    result=run_bounded_sensitivity(args.manifest)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
elif args.command == 'chp-evidence-register':
    result=run_register(args.register)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'market-provenance':
    result=run_market_source_audit(args.manifest)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'annual-chp-evidence':
    result=audit_annual_chp(args.csv)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
elif args.command == 'fetch-svk':
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
elif args.command == 'contract-dispatch':
    if args.require_operational_validation:
        evidence=run_market_source_audit(Path('examples/v0913_market_provenance.json'))
        require_operational_validation(evidence)
    result=run_market_boundary_manifest(
        args.manifest,include_solver_details=args.output is not None,
        hard_contract=True)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'market-boundary':
    result=run_market_boundary_manifest(args.manifest,include_solver_details=args.output is not None)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'historical-replay':
    path=args.manifest.resolve()
    root=Path(__file__).resolve().parents[2]
    result=run_manifest(root,path,include_hourly=args.output is not None)
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
elif args.command == 'dispatch':
    result=run_dispatch(args.config,args.prices,args.output,capacity_mwh_lhv=args.capacity_mwh_lhv)
else:
    result=run_sweep(args.config,args.prices,args.output)
if args.command == 'real-chp-analysis':
    print(json.dumps(result,indent=2,allow_nan=False,ensure_ascii=False))
elif args.command == 'public-chp-sources':
    print(json.dumps(result,indent=2,allow_nan=False,ensure_ascii=False))
elif args.command == 'telemetry-qa':
    print(json.dumps({
        'version':'0.9.15',
        'status':result['status'],
        'source_class':result['source_class'],
        'intervals_checked':result['interval_count'],
        'measurement_channels':result['measurement_channels'],
        'raw_sha256':result['raw_sha256'],
        'data_quality_screen_passed':result['raw_data_quality_screen_passed'],
        'physical_validation_performed':result['real_plant_model_validation_performed'],
        'calibration_certificates_verified':result['calibration_certificates_cryptographically_verified'],
        'high_rate_event_data_available':result['high_rate_startup_ramp_evidence_available'],
        'output_path':str(args.output) if args.output is not None else None,
        'claim_limit':'Source/balance screen only; no equipment calibration or actual model validation',
    },indent=2,allow_nan=False))
elif args.command == 'bounded-sensitivity':
    print(json.dumps({
        'version':'0.9.14-B',
        'status':result['status'],
        'factorial_scenarios':result['summary']['factorial_case_count'],
        'feasible_grid_scenarios':result['summary']['factorial_feasible_count'],
        'infeasible_grid_scenarios':result['summary']['factorial_infeasible_count'],
        'one_at_a_time_scenarios':result['summary']['oat_case_count'],
        'continuous_box_certificates':len(result['continuous_box_certificates']),
        'calibrated_plant':result['calibration_claim'],
        'physical_market_participation_eligible':result['operational_market_eligibility_claim'],
        'output_path':str(args.output) if args.output is not None else None,
        'scope':'Fixed synthetic two-slot CHP terminal-generation model only; not an observed physical probability',
    },indent=2,allow_nan=False))
elif args.command == 'chp-evidence-register':
    print(json.dumps({
        'version':'0.9.14',
        'status':result['status'],
        'evidence_level':'SOURCE_SCOPED_CATALOGUE_AND_ANNUAL_PAPER',
        'sources_checked':result['sources_checked_against_curated_source_catalogue'],
        'parameters_reviewed':result['parameters_reviewed'],
        'unidentified_dynamic_parameters':result['unidentified_count'],
        'physical_dispatch_calibrated':result['physical_validation_of_v0911_contracts'],
        'auto_import_into_dispatch':result['auto_import_into_dispatch'],
        'output_path':str(args.output) if args.output is not None else None,
        'claim_limit':'Manufacturer catalogue examples do not identify Polish site or validate dispatch dynamics',
    },indent=2,allow_nan=False))
elif args.command == 'market-provenance':
    print(json.dumps({
        "version":"0.9.13",
        "status":result["status"],
        "observed_price_intervals":result["market_archive"]["observed_intervals"],
        "source_snapshot_sha256":result["market_archive"]["source_csv_sha256"],
        "external_annual_chp_years":result["published_independent_annual_chp"]["years"],
        "operational_contract_dispatch_eligible":result["operational_contract_dispatch_eligible"],
        "blocking_reasons":result["operational_blockers"],
        "output_path":str(args.output) if args.output is not None else None,
    },indent=2,allow_nan=False))
elif args.command == 'annual-chp-evidence':
    print(json.dumps({
        'version':'0.9.12',
        'status':result['status'],
        'doi':result['doi'],
        'evidence_level':result['evidence_level'],
        'annual_records':len(result['annual_observations']),
        'source_discrepancies':len(result['documented_source_discrepancies']),
        '2018_2022_annual_row_mean_gas_m3':
            result['periods']['2018-2022']['arithmetic_annual_means']['landfill_gas_recovered_m3'],
        '2018_2022_as_published_mean_gas_m3':
            result['published_reported_averages_unchanged']['2018-2022']['landfill_gas_recovered_m3'],
        'input_csv_sha256':result['input_csv_sha256'],
        'output_path':str(args.output) if args.output is not None else None,
        'claim_limit':'Annual landfill CHP records only; no hourly dispatch calibration or observed revenues',
    },indent=2,allow_nan=False))
elif args.command == 'contract-dispatch':
    post=result["postclearing"]
    print(json.dumps({
        "version":"0.9.11",
        "phase":post["phase"],
        "accepted_mwh":post["total_accepted_mwh"],
        "gross_contract_cashflow_PROXY_not_profit_eur":
            post["gross_contract_cashflow_proxy_eur"],
        "hard_award_equalities_inside_milp":post["hard_award_equality_count"],
        "maximum_award_energy_residual_mwh":
            post["maximum_contract_vs_simulated_delivery_mwh"],
        "constrained_LP_upper_bound_eur":
            post["matched_contract_LP_relaxation_upper_bound_eur"],
        "output_path":str(args.output) if args.output is not None else None,
        "claim_limit":"Fictional awards and CHP, no real trade, forecast, imbalance settlements or metered electricity",
    },indent=2,allow_nan=False))
elif args.command == 'market-boundary':
    print(json.dumps({
        "status":result["postclearing"]["phase"],
        "version":"0.9.10",
        "output_path":str(args.output) if args.output is not None else None,
        "preclear_phase":result["preclearing"]["phase"],
        "auction_gate_close_utc":result["preclearing"]["gate_close_utc"],
        "publication_time_utc":result["postclearing"]["prices_published_utc"],
        "accepted_mwh":result["postclearing"]["total_accepted_mwh"],
        "gross_contract_cashflow_PROXY_not_settlement_eur":
            result["postclearing"]["gross_contract_cashflow_proxy_eur"],
        "maximum_contract_delivery_residual_mwh":
            result["postclearing"]["maximum_contract_vs_simulated_delivery_mwh"],
        "scientific_scope":"ALL MARKET ORDERS, FORECASTS, AWARDS AND CHP INPUTS FICTIONAL; no live settlement or profits",
    },indent=2,allow_nan=False))
elif args.command == 'historical-replay':
    print(json.dumps({
        'status':result['status'],
        'version':result['version'],
        'observed_heldout_days':result['observed_heldout_days'],
        'forecast_methods':result['forecast_methods'],
        'output_path':str(args.output) if args.output is not None else None,
        'studies':[{
            'case_id':s['case_id'],
            'method':s['method'],
            'one_step_mae_eur_mwh':s['one_step_mae_eur_mwh'],
            'rolling_realized_contribution_eur':s['rolling_realized_contribution_eur'],
            'perfect_hindsight_regret_eur':s['perfect_hindsight_regret_eur'],
        } for s in result['studies']],
        'claim_limit':'Observed prices, synthetic CHP; hypothetical sequential-reveal experiment, not operational day-ahead price forecasting or validated revenue',
    },indent=2,allow_nan=False))
elif args.command in ('operating-surrogate','forecast-regret','unit-commitment','hourly-commitment','rolling-forecast'):
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
