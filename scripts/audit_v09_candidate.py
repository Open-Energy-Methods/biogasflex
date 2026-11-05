"""BiogasFlex 0.9 offline scientific-consistency and provenance audit.

Independent of the optimizer and SciPy: recomputes each scenario's *inputs*
from frozen registry/config, audits independent v0.8 output-ledger checks, ties
all reported prices to a pinned CC BY 4.0 snapshot, checks both fixed and
optimized dispatch, tests emergency assumptions, and reconstructs summaries.

This is an internal AI-assisted audit, NOT third-party peer review, experimental
validation, or a mathematical proof of global solver optimality.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inherited_v08_audit',ROOT/'scripts/independent_v08_audit.py')
v08=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=v08
spec.loader.exec_module(v08)

class AuditFailure(ValueError): pass

def eq(a,b,label,atol=1e-8):
    if isinstance(a,bool) or isinstance(b,bool):
        if type(a)!=type(b) or a!=b: raise AuditFailure(f'{label}: boolean mismatch')
        return
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        if not (math.isfinite(float(a)) and math.isfinite(float(b)) and abs(a-b)<=atol):
            raise AuditFailure(f'{label}: expected {b!r}, found {a!r}')
    elif a!=b:
        raise AuditFailure(f'{label}: expected {b!r}, found {a!r}')

def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def input_pins(root:Path)->dict:
    pins=json.loads((root/'docs/V09_FROZEN_INPUT_HASHES.json').read_text(encoding='utf8'))['inputs']
    for relative,expected in pins.items():
        dest=root/relative
        if not dest.is_file() or sha(dest)!=expected:raise AuditFailure(f'Frozen-source checksum mismatch: {relative}')
    return pins

def scenario_grid(reg:dict,base:dict):
    for idx,(w,s,d,c,e,v) in enumerate(itertools.product(
        reg['market_windows'],reg['gas_storage_mwh_lhv'],
        reg['heat_demand_factors_of_2022_annual_mean_production'],
        reg['assumed_backup_cost_eur_mwh_th'],reg['electrical_efficiency_lhv'],
        reg['rating_variants'])):
        rating=v['value'] if v['rule']=='fixed_mw' else v['value']*base['gas_input_mw_lhv']*e
        yield {'case_id':f'V08-S{idx:03d}', 'win':w,'s':s,'d':d,'c':c,'e':e,'v':v,'rating':rating}

def check_market_contract(payload:dict, row:dict, entry:dict, base:dict,price_records:list[dict])->None:
    w,s,d,c,e,v,rating=(entry[k] for k in ('win','s','d','c','e','v','rating'))
    expect={'case_id':entry['case_id'],'market_window':w['id'],'civil_date':w['civil_date'],
            'gas_storage_mwh_lhv':s,'heat_demand_multiplier':d,
            'aux_cost_eur_mwh_th':c,'electric_efficiency_lhv':e,
            'rating_variant':v['id'],'rated_mw_e':rating}
    for k,val in expect.items():
        if k not in row:raise AuditFailure(f'Missing market row field: {k}')
        eq(float(row[k]) if isinstance(val,(float,int)) else row[k],val,'CSV '+entry['case_id']+'/'+k)
    for k,val in [('case_id',entry['case_id']),('price_zone',base['price_zone']),
            ('capacity_mwh_lhv',s),('chp_electric_rating_mw',rating),
            ('electric_efficiency_lhv_assumed',e),
            ('thermal_efficiency_lhv_assumed',base['thermal_efficiency_lhv']),
            ('initial_and_terminal_stock_mwh_lhv',base['initial_gas_inventory_mwh_lhv']),
            ('gas_basis','MWh_LHV'),('currency','EUR')]:
        eq(payload.get(k),val,entry['case_id']+'/'+k)
    eq(payload['v08_provenance'].get('source_market_window'),w['civil_date'],'market metadata date')
    eq(payload['v08_provenance'].get('rating_variant'),v['id'],'market rating variant')
    eq(payload['v08_provenance'].get('core_solver_version'),'0.7.0 (unchanged heat optimizer)','core version')
    profile=payload['input_profile']
    if len(profile)!=24 or len(price_records)!=24:raise AuditFailure('Market-window length must be exactly 24 hourly values')
    zone=ZoneInfo('Europe/Stockholm')
    start_times=[]
    for i,(x,observed) in enumerate(zip(profile,price_records)):
        pfx=f'{entry["case_id"]}/interval{i}'
        start=datetime.fromisoformat(x['start_utc'])
        if start.tzinfo is None or start.utcoffset().total_seconds()!=0:
            raise AuditFailure(f'{pfx}: timestamp not explicitly UTC')
        if start.astimezone(zone).date().isoformat()!=w['civil_date']:
            raise AuditFailure(f'{pfx}: price outside the selected local civil day')
        start_times.append(start)
        eq(x['start_utc'],observed['start_time_utc'],f'{pfx} UTC source')
        eq(float(x['price_eur_per_mwh']),float(observed['price']),f'{pfx} source price',1e-10)
        eq(x['dt_h'],1.0,f'{pfx} interval duration')
        for key,value in (
            ('gas_production_mw_lhv',base['gas_input_mw_lhv']),
            ('fixed_flaring_mw_lhv',base['fixed_flaring_mw_lhv']),
            ('fixed_losses_mw_lhv',base['fixed_losses_mw_lhv']),
            ('heat_demand_mw_th',base['heat_demand_mw_th']*d),
            ('auxiliary_heat_cost_eur_per_mwh_th',c),
            ('heat_dump_penalty_eur_per_mwh_th',base['heat_dump_penalty_eur_per_mwh_th']),
            ('chp_variable_cost_eur_per_mwh_e',base['chp_variable_cost_eur_per_mwh_e'])):
            eq(x.get(key),value,pfx+'/'+key)
        supply=x['gas_production_mw_lhv']-x['fixed_flaring_mw_lhv']-x['fixed_losses_mw_lhv']
        eq(x['fixed_gas_use_mw_lhv'],supply,pfx+'/fixed comparator gas conservation')
        eq(x['fixed_chp_power_mw_e'],e*supply,pfx+'/fixed comparator power')
        eq(x['fixed_useful_heat_mw_th'],min(base['thermal_efficiency_lhv']*supply,x['heat_demand_mw_th']),pfx+'/fixed useful heat')
        eq(x['fixed_auxiliary_heat_mw_th'],max(0,x['heat_demand_mw_th']-base['thermal_efficiency_lhv']*supply),pfx+'/fixed backup')
        eq(x['fixed_heat_dump_mw_th'],max(0,base['thermal_efficiency_lhv']*supply-x['heat_demand_mw_th']),pfx+'/fixed dumping')
        eq(x['optimized_useful_heat_mw_th'],min(base['thermal_efficiency_lhv']*x['optimized_gas_use_mw_lhv'],x['heat_demand_mw_th']),pfx+'/optimal direct heat')
        if x['optimized_auxiliary_heat_mw_th']>base['aux_heat_capacity_mw_th']+1e-8:
            raise AuditFailure(f'{pfx}: auxiliary heat capacity violated')
        if x['optimized_heat_dump_mw_th']>base['heat_dump_capacity_mw_th']+1e-8:
            raise AuditFailure(f'{pfx}: dumping capacity violated')
    if any((b-a).total_seconds()!=3600 for a,b in zip(start_times,start_times[1:])):
        raise AuditFailure(f'{entry["case_id"]}: gap/overlap in provider observations')
    eq(profile[-1]['end_utc'],w['end_utc'],'terminal market boundary')
    eq(row['solver_status'],0,'market row solver status') if isinstance(row['solver_status'],(float,int)) else eq(int(row['solver_status']),0,'market row solver status')
    gross=[x['price_eur_per_mwh'] for x in profile]
    eq(float(row['mean_price_eur_mwh_e']),math.fsum(gross)/24,entry['case_id']+'/mean price')
    eq(float(row['price_range_eur_mwh_e']),max(gross)-min(gross),entry['case_id']+'/price range')
    for k,ledger_key in [('fixed_value_eur','fixed_dispatch'),('optimized_value_eur','optimized_dispatch')]:
        eq(float(row[k]),payload[ledger_key]['economic_contribution_proxy_eur'],entry['case_id']+'/'+k)

def check_emergency_contract(payload:dict,row:dict,condition:dict,definition:dict)->None:
    expected={'case_id':condition['id'],'duration_hours':definition['time_h'],
      'gas_inflow_mw_lhv':definition['gas_inflow_during_disruption_mw_lhv'],
      'electric_efficiency_lhv':definition['electric_efficiency_lhv'],
      'thermal_efficiency_lhv':definition['thermal_efficiency_lhv'],
      'chp_electric_rating_mw':definition['chp_electric_rating_mw'],
      'gas_storage_capacity_mwh_lhv':condition['stock_mwh_lhv'],
      'initial_stock_mwh_lhv':condition['stock_mwh_lhv'],
      'critical_electric_load_mw':definition['critical_electric_load_mw'],
      'critical_heat_load_mw':definition['critical_heat_load_mw'],
      'island_capable':condition['island_capable'],
      'chp_available':condition['chp_available'],
      'grid_available':False,'auxiliary_heat_available':False}
    for k,v in expected.items():
        eq(payload['assumptions'].get(k),v,'emergency '+condition['id']+'/'+k)
    eq(expected['gas_inflow_mw_lhv'],0.0,'outage requires zero gas input')
    eq(row['gas_stock_precharged_mwh_lhv'],condition['stock_mwh_lhv'],'reported precharged stock') if isinstance(row['gas_stock_precharged_mwh_lhv'],(float,int)) else eq(float(row['gas_stock_precharged_mwh_lhv']),condition['stock_mwh_lhv'],'reported precharged stock')
    for k,v in [('island_capable_assumed',condition['island_capable']),('chp_available_assumed',condition['chp_available'])]:
        eq(str(row[k]).lower(),str(v).lower(),'resilience CSV '+k)
    if not (condition['island_capable'] and condition['chp_available']):
        eq(payload['energy_totals']['electric_served_mwh'],0.0,'unavailable emergency electricity')
        eq(payload['energy_totals']['heat_served_mwh_th'],0.0,'unavailable emergency heat')
    # Energy maxima: critical loads and fuel supply bound conditional service, no plant capability inferred.
    max_e=min(expected['initial_stock_mwh_lhv']*expected['electric_efficiency_lhv'],
              expected['critical_electric_load_mw']*expected['duration_hours'])
    if payload['energy_totals']['electric_served_mwh']>max_e+1e-7:
        raise AuditFailure('Emergency electric service exceeds gas/critical-load bound')
    max_h=min(expected['initial_stock_mwh_lhv']*expected['thermal_efficiency_lhv'],
              expected['critical_heat_load_mw']*expected['duration_hours'])
    if payload['energy_totals']['heat_served_mwh_th']>max_h+1e-7:
        raise AuditFailure('Emergency heat service exceeds gas/critical-load bound')
    eq(float(row['fraction_electric_served']),payload['energy_totals']['electric_service_fraction'],'emergency electric fraction')
    eq(float(row['fraction_heat_served']),payload['energy_totals']['heat_service_fraction'],'emergency heat fraction')

def audit(root:Path=ROOT,*,write:bool=False,verbose:bool=True)->dict:
    pins=input_pins(root)
    original=v08.audit(root,verbose=False)
    reg=json.loads((root/'scenarios/registry.json').read_text(encoding='utf8'))
    base=json.loads((root/'config/v07_lovsta_heat_proxy.json').read_text(encoding='utf8'))
    with (root/'results/v0.8/predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
        rows=list(csv.DictReader(f))
    case_by_id={row['case_id']:row for row in rows}
    if len(case_by_id)!=216 or len(rows)!=216:raise AuditFailure('Lost or duplicate preregistered cases')
    sources={}
    for w in reg['market_windows']:
        with (root/w['file']).open(newline='',encoding='utf8') as f:
            sources[w['id']]=list(csv.DictReader(f))
    outputs=[]
    for entry in scenario_grid(reg,base):
        if entry['case_id'] not in case_by_id:raise AuditFailure('Registry scenario case ID missing')
        row=case_by_id[entry['case_id']]
        payload=json.loads((root/'results/v0.8/cases'/f'{entry["case_id"]}.json').read_text(encoding='utf8'))
        check_market_contract(payload,row,entry,base,sources[entry['win']['id']])
        outputs.append(float(row['scenario_contribution_increment_eur']))
    with (root/'results/v0.8/hypothetical_critical_service_results.csv').open(newline='',encoding='utf8') as f:
        emergency_rows=list(csv.DictReader(f))
    e_by_id={x['case_id']:x for x in emergency_rows}
    for e in reg['resilience_cases']:
        if e['id'] not in e_by_id:raise AuditFailure('Emergency case missing from results')
        payload=json.loads((root/'results/v0.8/resilience'/f'{e["id"]}.json').read_text(encoding='utf8'))
        check_emergency_contract(payload,e_by_id[e['id']],e,reg['resilience_definition'])
    summary=json.loads((root/'results/v0.8/v08_study_summary.json').read_text(encoding='utf8'))
    stats=summary['scenario_statistics']
    eq(stats['minimum_increment_eur'],min(outputs),'study minimum')
    eq(stats['median_increment_eur'],statistics.median(outputs),'study median')
    eq(stats['maximum_increment_eur'],max(outputs),'study maximum')
    eq(stats['positive_scenarios_1e-7'],sum(x>1e-7 for x in outputs),'positive count')
    eq(stats['near_zero_scenarios_1e-7'],sum(abs(x)<=1e-7 for x in outputs),'near-zero count')
    eq(stats['negative_scenarios_1e-7'],sum(x < -1e-7 for x in outputs),'negative count')
    answer={'audit':'PASS','version':'0.9.0','audited_core_results':'0.8.0',
            'frozen_inputs_verified':len(pins),
            'source_registry_scenarios_reconstructed':len(outputs),
            'market_cases_independently_recalculated':original['market_cases_verified'],
            'emergency_cases_verified':original['emergency_cases_verified'],
            'positive_cases':sum(x>1e-7 for x in outputs),
            'near_zero_cases':sum(abs(x)<=1e-7 for x in outputs),
            'min_increment_eur':min(outputs), 'median_increment_eur':statistics.median(outputs),
            'max_increment_eur':max(outputs),
            'limits':'Internal audit only. Perfect foresight, hypothetical dispatch and outage capability; no observed plant operation, independent human review, probabilities, CAPEX/NPV or actual exports.',
            'python_stdlib_only':True}
    if write:
        dest=root/'results/v0.9/v09_audit_summary.json';dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(answer,indent=2,allow_nan=False)+'\n',encoding='utf8')
    if verbose:print(json.dumps(answer,indent=2))
    return answer

if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('--write-summary',action='store_true')
    options=args.parse_args()
    try:audit(write=options.write_summary)
    except (AuditFailure,v08.AuditError,ValueError,KeyError,FileNotFoundError) as e:
        print(f'V0.9 AUDIT FAILED: {e}',file=sys.stderr);raise SystemExit(2)
