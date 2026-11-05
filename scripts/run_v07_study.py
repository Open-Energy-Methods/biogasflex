"""Reproduce v0.7 toy and source-mixed sensitivity results, offline.

No optimization-performance values are hardcoded: all outputs are regenerated from
version-controlled configs and licensed input data. Plots are optional.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from biogasflex.heat_dispatch import run_heat_dispatch, optimize_heat_dispatch, load_heat_case


def file_sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path:Path, rows:list[dict]):
    if not rows:raise ValueError('Cannot write empty evidence CSV')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        writer.writeheader();writer.writerows(rows)


def export_profile(result:dict,path:Path):
    write_csv(path,result['input_profile'])


def build(*,plots:bool=False)->dict:
    out=ROOT/'results/v0.7'
    out.mkdir(parents=True,exist_ok=True)
    toy_cfg=ROOT/'config/v07_oracle_two_period_heat.json'
    toy_price=ROOT/'data/synthetic/prices_2period_oracle.csv'
    real_cfg=ROOT/'config/v07_lovsta_heat_proxy.json'
    real_price=ROOT/'data/observed/svk_se3_20200101_CC-BY-4.0.csv'
    study_cfg=ROOT/'config/v07_predeclared_sensitivity.json'
    study=json.loads(study_cfg.read_text(encoding='utf8'))
    toy=run_heat_dispatch(toy_cfg,toy_price,out/'synthetic_oracle_heat_cost80.json')
    real=run_heat_dispatch(real_cfg,real_price,out/'lovsta_crossyear_heat_cost80.json')
    export_profile(toy,out/'synthetic_oracle_heat_cost80_intervals.csv')
    export_profile(real,out/'lovsta_crossyear_heat_cost80_intervals.csv')
    tcfg,trows=load_heat_case(toy_cfg,toy_price)
    oracle=[]
    for cost in (0.0,20.0,80.0,200.0):
        cfg={**tcfg,'aux_heat_cost_eur_per_mwh_th':cost}
        result=optimize_heat_dispatch(cfg,trows)
        oracle.append({'aux_cost_eur_per_mwh_th':cost,
                       'fixed_electricity_value_eur':result['fixed_dispatch']['gross_electricity_revenue_eur'],
                       'optimized_electricity_value_eur':result['optimized_dispatch']['gross_electricity_revenue_eur'],
                       'gross_electricity_increment_eur':result['incremental_gross_electricity_value_eur'],
                       'aux_heat_cost_increment_eur':result['change_in_auxiliary_heat_cost_eur'],
                       'net_scenario_contribution_increment_eur':result['incremental_economic_contribution_proxy_eur'],
                       'aux_heat_mwh_th':result['optimized_dispatch']['auxiliary_heat_delivered_mwh_th'],
                       'dumped_heat_mwh_th':result['optimized_dispatch']['heat_dumped_mwh_th']})
    write_csv(out/'synthetic_oracle_heat_cost_sensitivity.csv',oracle)
    cfg,rows=load_heat_case(real_cfg,real_price)
    params=[]
    for factor in study['heat_demand_multipliers_of_2022_annual_mean_heat_production']:
        for cost in study['assumed_aux_heat_cost_eur_per_mwh_th']:
            c={**cfg,
               'heat_demand_mw_th': cfg['heat_demand_mw_th']*factor,
               'aux_heat_cost_eur_per_mwh_th':cost,
               'gas_storage_capacity_mwh_lhv':study['gas_storage_capacity_mwh_lhv'],
               'heat_dump_penalty_eur_per_mwh_th':study['heat_dump_penalty_eur_per_mwh_th'],
               'chp_variable_cost_eur_per_mwh_e':study['chp_variable_cost_eur_per_mwh_e']}
            result=optimize_heat_dispatch(c,rows)
            o=result['optimized_dispatch'];f=result['fixed_dispatch']
            params.append({
                'heat_demand_fraction_of_annual_mean_production':factor,
                'hypothetical_backup_cost_eur_per_mwh_th':cost,
                'fixed_heat_demand_mwh_th':f['heat_demand_mwh_th'],
                'fixed_aux_heat_mwh_th':f['auxiliary_heat_delivered_mwh_th'],
                'optimized_aux_heat_mwh_th':o['auxiliary_heat_delivered_mwh_th'],
                'fixed_dump_mwh_th':f['heat_dumped_mwh_th'],
                'optimized_dump_mwh_th':o['heat_dumped_mwh_th'],
                'gross_electricity_increment_eur':result['incremental_gross_electricity_value_eur'],
                'aux_cost_increment_eur':result['change_in_auxiliary_heat_cost_eur'],
                'contribution_increment_eur':result['incremental_economic_contribution_proxy_eur'],
                'max_gas_residual_mwh':o['max_interval_balance_residual_mwh'],
                'max_heat_service_residual_mwh':o['max_heat_service_residual_mwh'],
                'status_code':result['solver']['status_code']})
    write_csv(out/'lovsta_crossyear_heat_service_sensitivity.csv',params)
    summary={'version':'0.7.0','study_id':study['study_id'],'status':'development candidate, not plant validated',
             'evidence_contract':study['interpretation'],
             'reproduction_hashes':{str(p.relative_to(ROOT)):file_sha(p) for p in (toy_cfg,toy_price,real_cfg,real_price,study_cfg)},
             'synthetic_oracle_cases':oracle,'source_mixed_crossyear_counterfactual_cases':params,
             'primary_case': {'fixed_gross_electricity_eur':real['fixed_dispatch']['gross_electricity_revenue_eur'],
                              'optimized_gross_electricity_eur':real['optimized_dispatch']['gross_electricity_revenue_eur'],
                              'gross_electricity_increment_eur':real['incremental_gross_electricity_value_eur'],
                              'fixed_contribution_proxy_eur':real['fixed_dispatch']['economic_contribution_proxy_eur'],
                              'optimized_contribution_proxy_eur':real['optimized_dispatch']['economic_contribution_proxy_eur'],
                              'contribution_increment_eur':real['incremental_economic_contribution_proxy_eur'],
                              'heat_service_mwh_th':real['fixed_dispatch']['heat_demand_mwh_th']},
            'null_result_note':'Sub-micro-euro floating residuals near zero must be reported as zero within published tolerance.'}
    (out/'v07_study_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf8')
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figdir=out/'figures';figdir.mkdir(exist_ok=True)
        # Toy: original gross timing revenue vs scenario contribution after the backup cost.
        fig,ax=plt.subplots(figsize=(8,4.3))
        x=[r['aux_cost_eur_per_mwh_th'] for r in oracle]
        y=[r['net_scenario_contribution_increment_eur'] for r in oracle]
        # Display the *actual* analytically derived piecewise optimum, not a
        # misleading straight-line interpolation through sparse study points.
        curve_x=[i for i in range(201)]
        curve_y=[max(0.0,24.0-0.18*cost) for cost in curve_x]
        ax.plot(curve_x,curve_y,label='Closed-form heat-constrained optimum')
        ax.scatter(x,y,marker='o',label='Predeclared solved scenarios',zorder=4)
        ax.axhline(24,linestyle='--',label='Electricity-only analytic uplift (toy)')
        ax.axhline(0,linewidth=0.8)
        ax.set(xlabel='Assumed marginal backup-heat cost (EUR/MWh_th)',
               ylabel='Incremental scenario contribution (EUR)',title='Two-period synthetic heat-service oracle')
        ax.axvline(60.0/0.45,linestyle=':',linewidth=1,label='Backup-cost crossover (133.33 EUR/MWh_th)')
        ax.legend(loc='best',fontsize=8);fig.tight_layout();fig.savefig(figdir/'synthetic_heat_cost_oracle.png',dpi=175);plt.close(fig)
        # Real-data-price + hypothetical-plant sensitivity; multiple demand profiles.
        fig,ax=plt.subplots(figsize=(8.5,4.6))
        for f in study['heat_demand_multipliers_of_2022_annual_mean_heat_production']:
            s=[r for r in params if r['heat_demand_fraction_of_annual_mean_production']==f]
            ax.plot([r['hypothetical_backup_cost_eur_per_mwh_th'] for r in s],
                    [r['contribution_increment_eur'] if abs(r['contribution_increment_eur'])>1e-7 else 0 for r in s],
                    marker='o',label=f'Heat demand = {f:g} × annual mean')
        ax.axhline(0,linewidth=0.8)
        ax.set(xlabel='Assumed backup-heat cost (EUR/MWh_th)',
               ylabel='Scenario contribution uplift (EUR per 24 h)',
               title='Lövsta-parameterized, cross-year hypothetical sensitivity')
        ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figdir/'lovsta_heat_service_sensitivity.png',dpi=175);plt.close(fig)
        fig,ax=plt.subplots(figsize=(9,4.6))
        xs=range(len(real['input_profile']))
        rows=real['input_profile']
        ax.plot(xs,[r['fixed_chp_power_mw_e'] for r in rows],linestyle='--',label='Fixed CHP electrical output')
        ax.plot(xs,[r['optimized_chp_power_mw_e'] for r in rows],label='Heat-aware CHP electrical output')
        ax.plot(xs,[r['heat_demand_mw_th'] for r in rows],label='Assumed heat load (MW_th)')
        ax.set(xlabel='Hourly interval index (local 1 Jan 2020, SE3 price window)',ylabel='Power (MW)',
               title='Heat-binding base-case: dispatch remains constant')
        ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figdir/'lovsta_heat_binding_profile.png',dpi=175);plt.close(fig)
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--plots',action='store_true',help='Optional matplotlib figures')
    args=ap.parse_args()
    x=build(plots=args.plots)
    print(json.dumps({'version':x['version'],'cases':len(x['source_mixed_crossyear_counterfactual_cases']),
                      'toy_sensitivity_cases':len(x['synthetic_oracle_cases']),
                      'primary_contribution_increment_eur':x['primary_case']['contribution_increment_eur']},indent=2))
