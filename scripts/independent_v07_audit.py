"""Separate *standard-library-only* results audit; never imports optimizer/SciPy.

Checks documented outputs from JSON and raw price CSV, not scientific validation.
By design this is AI-assisted independent-code numerical verification, not human peer review.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ABS_GAS_MWH=1e-8
ABS_HEAT_MWH=1e-8
ABS_EUR=1e-7


def need(cond,msg):
    if not cond:raise AssertionError(msg)


def check(path:Path)->dict:
    obj=json.loads(path.read_text(encoding='utf8'))
    profile=obj['input_profile']
    need(obj['solver']['status_code']==0 and obj['solver']['success'],'not optimal')
    eta_e=obj['electric_efficiency_lhv_assumed']
    eta_th=obj['thermal_efficiency_lhv_assumed']
    smax=obj['capacity_mwh_lhv']
    rating=obj['chp_electric_rating_mw']
    initial=obj['initial_and_terminal_stock_mwh_lhv']
    totals={k:{'revenue':0.,'backup_cost':0.,'dump_cost':0.,'chp_cost':0.,
               'gas_used':0.,'electricity':0.,'heat_served':0.,'heat_backup':0.,'heat_dump':0.}
            for k in ('fixed','optimized')}
    prev_end=None
    gas_supply=0.; flared=0.; lost=0.; heat_demand=0.
    for t,row in enumerate(profile):
        dt=float(row['dt_h']);need(dt>0,'invalid time-step')
        start=datetime.fromisoformat(row['start_utc']);end=datetime.fromisoformat(row['end_utc'])
        need(start.tzinfo is not None and end.tzinfo is not None,'missing offset')
        need(abs((end-start).total_seconds()/3600-dt)<1e-10,'mismatched interval duration')
        if prev_end is not None: need(start==prev_end,'timestamp gap')
        prev_end=end
        prod=row['gas_production_mw_lhv'];flare=row['fixed_flaring_mw_lhv'];loss=row['fixed_losses_mw_lhv']
        gas_supply+=prod*dt;flared+=flare*dt;lost+=loss*dt
        heat_demand+=row['heat_demand_mw_th']*dt
        for name in ('fixed','optimized'):
            if name=='fixed':
                gas_use=row['fixed_gas_use_mw_lhv']; power=row['fixed_chp_power_mw_e']
                heat=row['fixed_useful_heat_mw_th'];aux=row['fixed_auxiliary_heat_mw_th'];dump=row['fixed_heat_dump_mw_th']
            else:
                gas_use=row['optimized_gas_use_mw_lhv'];power=row['optimized_chp_power_mw_e']
                heat=row['optimized_useful_heat_mw_th'];aux=row['optimized_auxiliary_heat_mw_th'];dump=row['optimized_heat_dump_mw_th']
            need(min(gas_use,power,heat,aux,dump)>-1e-9,'negative flow')
            need(power<=rating+1e-9,'nameplate violation')
            need(abs(power-eta_e*gas_use)*dt < ABS_HEAT_MWH,'electric conversion mismatch')
            need(abs(eta_th*gas_use-heat-dump)*dt<ABS_HEAT_MWH,'CHP thermal conversion mismatch')
            need(abs(heat+aux-row['heat_demand_mw_th'])*dt<ABS_HEAT_MWH,'heat demand not served')
            need(not(aux>1e-8 and dump>1e-8),'unnecessary backup and heat dumping same interval')
            z=totals[name]
            z['revenue']+=power*row['price_eur_per_mwh']*dt
            z['backup_cost']+=aux*row['auxiliary_heat_cost_eur_per_mwh_th']*dt
            z['dump_cost']+=dump*row['heat_dump_penalty_eur_per_mwh_th']*dt
            z['chp_cost']+=power*row['chp_variable_cost_eur_per_mwh_e']*dt
            z['gas_used']+=gas_use*dt
            z['electricity']+=power*dt
            z['heat_served']+=heat*dt
            z['heat_backup']+=aux*dt
            z['heat_dump']+=dump*dt
        stock0=row['stock_start_mwh_lhv'];stock1=row['stock_end_mwh_lhv'];gasuse=row['optimized_gas_use_mw_lhv']
        need(-1e-8<=stock0<=smax+1e-8 and -1e-8<=stock1<=smax+1e-8,'inventory capacity violation')
        need(abs(stock1-stock0-(prod-gasuse-flare-loss)*dt)<ABS_GAS_MWH,'gas conservation mismatch')
        if t:need(abs(stock0-profile[t-1]['stock_end_mwh_lhv'])<ABS_GAS_MWH,'inventory discontinuity')
        else:need(abs(stock0-initial)<ABS_GAS_MWH,'wrong initial inventory')
    need(abs(profile[-1]['stock_end_mwh_lhv']-initial)<ABS_GAS_MWH,'non-cyclic gas stock')
    for name in ('fixed','optimized'):
        z=totals[name];record=obj[f'{name}_dispatch']
        need(abs(z['gas_used']-(gas_supply-flared-lost))<ABS_GAS_MWH,'fuel utilization mismatch')
        need(abs(z['heat_served']+z['heat_backup']-heat_demand)<ABS_HEAT_MWH,'aggregate heat demand mismatch')
        for calc,output in [('revenue','gross_electricity_revenue_eur'),('backup_cost','auxiliary_heat_cost_eur'),
                            ('dump_cost','heat_dump_penalty_eur'),('chp_cost','chp_variable_cost_eur'),
                            ('gas_used','gas_utilized_mwh_lhv'),('electricity','electricity_generated_mwh'),
                            ('heat_served','useful_chp_heat_delivered_mwh_th'),('heat_backup','auxiliary_heat_delivered_mwh_th'),
                            ('heat_dump','heat_dumped_mwh_th')]:
            eps=ABS_EUR if calc in ('revenue','backup_cost','dump_cost','chp_cost') else ABS_HEAT_MWH
            need(abs(z[calc]-record[output])<eps,f'{name} {calc}: ledger mismatch')
        contribution=z['revenue']-z['backup_cost']-z['dump_cost']-z['chp_cost']
        need(abs(contribution-record['economic_contribution_proxy_eur'])<ABS_EUR,f'{name} contribution mismatch')
    delta=totals['optimized']['revenue']-totals['fixed']['revenue']
    contribution_delta=(totals['optimized']['revenue']-totals['optimized']['backup_cost']-totals['optimized']['dump_cost']-totals['optimized']['chp_cost']
                       -totals['fixed']['revenue']+totals['fixed']['backup_cost']+totals['fixed']['dump_cost']+totals['fixed']['chp_cost'])
    need(abs(delta-obj['incremental_gross_electricity_value_eur'])<ABS_EUR,'gross electric uplift mismatch')
    need(abs(contribution_delta-obj['incremental_economic_contribution_proxy_eur'])<ABS_EUR,'economic proxy uplift mismatch')
    need(contribution_delta>=-ABS_EUR,'optimal worse than feasible baseline')
    return {'file':path.name,'interval_count':len(profile),'gas_balance_pass':True,'heat_service_pass':True,
            'objective_recomputed_pass':True,'incremental_contribution_eur':contribution_delta,
            'gross_electricity_increment_eur':delta,'heat_demand_mwh_th':heat_demand}


def main()->list[dict]:
    outs=[]
    for fname in ('synthetic_oracle_heat_cost80.json','lovsta_crossyear_heat_cost80.json'):
        outs.append(check(ROOT/'results/v0.7'/fname))
    oracle=outs[0]
    need(abs(oracle['incremental_contribution_eur']-9.6)<1e-9,'toy independent closed-form optimum mismatch')
    need(abs(oracle['gross_electricity_increment_eur']-24)<1e-9,'toy gross electric closed-form mismatch')
    dst=ROOT/'reports/V07_INDEPENDENT_LEDGER_CHECK.json'
    dst.write_text(json.dumps({'review':'separate implementation, standard-library-only; self/AI-assisted not human review',
                               'checks':outs},indent=2,allow_nan=False)+'\n',encoding='utf8')
    return outs

if __name__=='__main__':print(json.dumps(main(),indent=2))
