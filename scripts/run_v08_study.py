"""BiogasFlex v0.8: execute the frozen scenario registry, entirely offline.

The registry/market selections were specified before running this solver script.
Cases are observations PLUS clearly labelled hypothetical assumptions, not a
probability sample or real Lövsta hourly plant dataset.
"""
from __future__ import annotations

import argparse
import csv
from datetime import timedelta
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from biogasflex.baseline import load_config,parse_prices
from biogasflex.heat_dispatch import optimize_heat_dispatch
from biogasflex.resilience import optimize_emergency_service


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path:Path, obj:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def write_csv(path:Path, rows:list[dict])->None:
    if not rows: raise ValueError('No rows to write')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def load_window(window:dict):
    price=ROOT/window['file']
    rows=parse_prices(price,'SE3',end_utc=window['end_utc'],required_hours=window['required_hours'])
    assert len(rows)==24
    local=ZoneInfo('Europe/Stockholm')
    if {r.start_utc.astimezone(local).date().isoformat() for r in rows}!={window['civil_date']}:
        raise ValueError('Market price records do not cover exact selected local civil day')
    for a,b in zip(rows,rows[1:]):
        if abs((b.start_utc-a.start_utc).total_seconds()-3600)>1e-8:
            raise ValueError('Missing or duplicated market hour')
    return rows


def build(*,plots:bool=False)->dict:
    reg_path=ROOT/'scenarios/registry.json'
    registry=json.loads(reg_path.read_text(encoding='utf8'))
    reg_hash=sha(reg_path)
    base_cfg=load_config(ROOT/'config/v07_lovsta_heat_proxy.json')
    out=ROOT/'results/v0.8'
    case_dir=out/'cases';case_dir.mkdir(parents=True,exist_ok=True)
    cases=[]
    scenario_price_hashes={}
    case_idx=0
    for win in registry['market_windows']:
        p=ROOT/win['file']
        scenario_price_hashes[win['id']]={'relative_path':win['file'],'sha256':sha(p)}
        prices=load_window(win)
        for storage,demand,cost,eff,variant in itertools.product(
           registry['gas_storage_mwh_lhv'], registry['heat_demand_factors_of_2022_annual_mean_production'],
           registry['assumed_backup_cost_eur_mwh_th'],registry['electrical_efficiency_lhv'],registry['rating_variants']):
            case_id=f'V08-S{case_idx:03d}'
            case_idx+=1
            mean_elec=base_cfg['gas_input_mw_lhv']*eff
            rating=(variant['value'] if variant['rule']=='fixed_mw' else variant['value']*mean_elec)
            cfg=dict(base_cfg)
            cfg.update({'case_id':case_id,'price_window_end_utc':win['end_utc'],
                        'gas_storage_capacity_mwh_lhv':storage,
                        'heat_demand_mw_th':base_cfg['heat_demand_mw_th']*demand,
                        'aux_heat_cost_eur_per_mwh_th':cost,
                        'electric_efficiency_lhv':eff,'electric_rating_mw':rating,
                        'evidence_status':'v0.8 registry source-mixed counterfactual: observed 2020 SE3 prices, 2022 annual average generator reference, otherwise assumption variants'})
            r=optimize_heat_dispatch(cfg,prices)
            if r['solver']['status_code']!=0:raise RuntimeError('Unexpected nonoptimal scenario')
            r['v08_provenance']={'registry_sha256':reg_hash,'price_source_sha256':sha(p),
                'source_market_window':win['civil_date'],'rating_variant':variant['id'],
                'core_solver_version':'0.7.0 (unchanged heat optimizer)'}
            write_json(case_dir/f'{case_id}.json',r)
            cases.append({
                'case_id':case_id,'market_window':win['id'],'civil_date':win['civil_date'],
                'gas_storage_mwh_lhv':storage,'heat_demand_multiplier':demand,
                'aux_cost_eur_mwh_th':cost,'electric_efficiency_lhv':eff,
                'rating_variant':variant['id'],'rated_mw_e':rating,
                'mean_price_eur_mwh_e':math.fsum(i.price_eur_per_mwh for i in prices)/len(prices),
                'price_range_eur_mwh_e':max(i.price_eur_per_mwh for i in prices)-min(i.price_eur_per_mwh for i in prices),
                'fixed_value_eur':r['fixed_dispatch']['economic_contribution_proxy_eur'],
                'optimized_value_eur':r['optimized_dispatch']['economic_contribution_proxy_eur'],
                'gross_electric_increment_eur':r['incremental_gross_electricity_value_eur'],
                'backup_cost_increment_eur':r['change_in_auxiliary_heat_cost_eur'],
                'scenario_contribution_increment_eur':r['incremental_economic_contribution_proxy_eur'],
                'max_gas_residual_mwh':r['optimized_dispatch']['max_interval_balance_residual_mwh'],
                'max_heat_service_residual_mwh':r['optimized_dispatch']['max_heat_service_residual_mwh'],
                'solver_status':r['solver']['status_code']})
    if len(cases)!=registry['scenario_count_expected']:
        raise RuntimeError('Scenario-count mismatch with frozen registry')
    write_csv(out/'predeclared_scenario_matrix_results.csv',cases)
    # Separate security of critical energy services during a specified nonmarket outage.
    r_cfg=registry['resilience_definition']
    outage=[]
    for condition in registry['resilience_cases']:
        cfg={
            'case_id':condition['id'],'duration_hours':r_cfg['time_h'],
            'gas_inflow_mw_lhv':r_cfg['gas_inflow_during_disruption_mw_lhv'],
            'electric_efficiency_lhv':r_cfg['electric_efficiency_lhv'],
            'thermal_efficiency_lhv':r_cfg['thermal_efficiency_lhv'],
            'chp_electric_rating_mw':r_cfg['chp_electric_rating_mw'],
            'gas_storage_capacity_mwh_lhv':condition['stock_mwh_lhv'],
            'initial_stock_mwh_lhv':condition['stock_mwh_lhv'],
            'critical_electric_load_mw':r_cfg['critical_electric_load_mw'],
            'critical_heat_load_mw':r_cfg['critical_heat_load_mw'],
            'island_capable':condition['island_capable'],
            'chp_available':condition['chp_available'],
            'grid_available':False,'auxiliary_heat_available':False}
        res=optimize_emergency_service(cfg)
        res['registry_sha256']=reg_hash
        write_json(out/'resilience'/f"{condition['id']}.json",res)
        t=res['energy_totals']
        outage.append({'case_id':condition['id'],'gas_stock_precharged_mwh_lhv':condition['stock_mwh_lhv'],
            'island_capable_assumed':condition['island_capable'],'chp_available_assumed':condition['chp_available'],
            'electric_critical_demand_mwh':t['electric_demand_mwh'],
            'electric_critical_served_mwh':t['electric_served_mwh'],
            'electric_critical_unserved_mwh':t['electric_unserved_mwh'],
            'fraction_electric_served':t['electric_service_fraction'],
            'heat_critical_demand_mwh_th':t['heat_demand_mwh_th'],
            'heat_critical_served_mwh_th':t['heat_served_mwh_th'],
            'heat_critical_unserved_mwh_th':t['heat_unserved_mwh_th'],
            'fraction_heat_served':t['heat_service_fraction'],
            'terminal_gas_mwh_lhv':t['terminal_inventory_mwh_lhv']})
    write_csv(out/'hypothetical_critical_service_results.csv',outage)
    delta=[r['scenario_contribution_increment_eur'] for r in cases]
    summary={'version':'0.8.0','study_id':registry['study_id'],
        'registry_sha256':reg_hash,'evidence_boundary':registry['claim_boundary'],
        'source_price_checksums':scenario_price_hashes,'market_scenario_count':len(cases),
        'excluded_window':registry['rejected_window'],
        'scenario_statistics':{
            'minimum_increment_eur':min(delta),'median_increment_eur':__import__('statistics').median(delta),
            'maximum_increment_eur':max(delta),
            'near_zero_scenarios_1e-7':sum(1 for x in delta if abs(x)<=1e-7),
            'positive_scenarios_1e-7':sum(1 for x in delta if x>1e-7),
            'negative_scenarios_1e-7':sum(1 for x in delta if x< -1e-7),
            'sampling_warning':'min/median/max of finite deliberately selected parameter grid; NOT probability quantiles or statistical confidence intervals'
        },'source_mixed_cases':cases,'hypothetical_service_security_cases':outage}
    write_json(out/'v08_study_summary.json',summary)
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figdir=out/'figures';figdir.mkdir(exist_ok=True)
        fig,ax=plt.subplots(figsize=(9.5,4.7))
        for win in registry['market_windows']:
            vals=load_window(win)
            ax.plot(range(len(vals)),[x.price_eur_per_mwh for x in vals],label=f"{win['civil_date']} (observed SE3)")
        ax.set(xlabel='Hour of selected civil day (Sweden local time)',ylabel='Price (EUR/MWh_e)',
               title='Predeclared quarterly first-day windows: 2020 (July rejected due to gap)')
        ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figdir/'predeclared_price_windows.png',dpi=175);plt.close(fig)
        fig,ax=plt.subplots(figsize=(9,4.8))
        data=[]
        labels=[]
        for win in registry['market_windows']:
            data.append([r['scenario_contribution_increment_eur'] for r in cases if r['market_window']==win['id']])
            labels.append(win['civil_date'])
        ax.boxplot(data,tick_labels=labels,showmeans=True)
        ax.set(ylabel='Incremental scenario contribution (EUR / selected day)',
               xlabel='Observed SE3 price window; varying hypothetical CHP/heat/storage parameters',
               title='Conditional sensitivity across predeclared configurations (not a probability sample)')
        ax.axhline(0,linewidth=0.8);fig.tight_layout();fig.savefig(figdir/'scenario_value_sensitivity.png',dpi=175);plt.close(fig)
        fig,ax=plt.subplots(figsize=(9,4.7))
        a=[r['case_id'] for r in outage];x=list(range(len(a)))
        ax.bar([i-0.19 for i in x],[r['fraction_electric_served'] for r in outage],width=.38,label='Electric service fraction')
        ax.bar([i+0.19 for i in x],[r['fraction_heat_served'] for r in outage],width=.38,label='Heat service fraction')
        ax.set(ylabel='Fraction of hypothetical 3-hour critical demand met',
            title='Gas-interruption scenario: grid unavailable; islandable CHP only when assumed')
        ax.set_xticks(x,a,rotation=14,ha='right');ax.set_ylim(0,1.02)
        ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figdir/'hypothetical_critical_service.png',dpi=175);plt.close(fig)
    return summary

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--plots',action='store_true')
    x=build(plots=a.parse_args().plots)
    print(json.dumps({'study_id':x['study_id'],'market_cases':x['market_scenario_count'],
        'statistics':x['scenario_statistics'],'resilience_cases':len(x['hypothetical_service_security_cases'])},indent=2))
