"""Standard-library-only v0.8 published-output audit, independent of optimization code.

Recomputes conservation, dispatch output, heat service and contribution from saved
interval-level records, including a physically separate emergency-service ledger.
No SciPy/HiGHS/model import. This does NOT constitute outside human peer review.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
TOL=2e-6
class AuditError(ValueError): pass


def close(x,y,tol=TOL):
    if not (math.isfinite(float(x)) and math.isfinite(float(y)) and abs(float(x)-float(y))<=tol):
        raise AuditError(f'Mismatched quantities: {x} vs {y}')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_market_case(data:dict, row:dict, registry_hash:str, source_price_sha:str)->None:
    if data.get('case_id')!=row['case_id'] or data.get('v08_provenance',{}).get('registry_sha256')!=registry_hash:
        raise AuditError('Case identity or frozen-registry hash mismatch')
    if data.get('v08_provenance',{}).get('price_source_sha256')!=source_price_sha:
        raise AuditError('Source price hash mismatch')
    if not data.get('solver',{}).get('success') or data['solver'].get('status_code')!=0:
        raise AuditError('Solver not optimal')
    if len(data.get('input_profile',[]))!=24 or data.get('duration_hours')!=24:
        raise AuditError('Incomplete market-price window')
    eta_e=data['electric_efficiency_lhv_assumed']
    eta_h=data['thermal_efficiency_lhv_assumed']
    cap=data['capacity_mwh_lhv']
    close(eta_e,float(row['electric_efficiency_lhv']))
    close(cap,float(row['gas_storage_mwh_lhv']))
    close(data['chp_electric_rating_mw'],float(row['rated_mw_e']))
    values={}
    for mode in ('fixed','optimized'):
        pfx=f'{mode}_'
        es=0.;fuel=0.;heat=0.;direct=0.;backup=0.;dump=0.;backup_cost=0.;dump_cost=0.;chp_cost=0.;gross=0.
        previous=data['initial_and_terminal_stock_mwh_lhv']
        for x in data['input_profile']:
            dt=float(x['dt_h']);close(dt,1)
            u=float(x[pfx+'gas_use_mw_lhv'])
            elec=float(x[pfx+'chp_power_mw_e'])
            useful=float(x[pfx+'useful_heat_mw_th'])
            aux=float(x[pfx+'auxiliary_heat_mw_th'])
            rej=float(x[pfx+'heat_dump_mw_th'])
            if min(u,elec,useful,aux,rej)< -TOL:raise AuditError('Negative energy/service flow')
            close(elec,eta_e*u);close(eta_h*u,useful+rej)
            close(useful+aux,x['heat_demand_mw_th'])
            close(elec<=data['chp_electric_rating_mw']+TOL,True,0.0)
            if mode=='optimized':
                close(previous,x['stock_start_mwh_lhv'])
                expected_end=previous+(x['gas_production_mw_lhv']-x['fixed_flaring_mw_lhv']-x['fixed_losses_mw_lhv']-u)*dt
                close(expected_end,x['stock_end_mwh_lhv'])
                previous=float(x['stock_end_mwh_lhv'])
                if previous < -TOL or previous>cap+TOL:raise AuditError('Storage violates capacity')
            es+=elec*dt;fuel+=u*dt;heat+=eta_h*u*dt;direct+=useful*dt;backup+=aux*dt;dump+=rej*dt
            gross+=elec*x['price_eur_per_mwh']*dt
            backup_cost+=aux*x['auxiliary_heat_cost_eur_per_mwh_th']*dt
            dump_cost+=rej*x['heat_dump_penalty_eur_per_mwh_th']*dt
            chp_cost+=elec*x['chp_variable_cost_eur_per_mwh_e']*dt
        if mode=='optimized':close(previous,data['initial_and_terminal_stock_mwh_lhv'])
        d=data[mode+'_dispatch']
        for key,value in [('gas_utilized_mwh_lhv',fuel),('electricity_generated_mwh',es),
                          ('potential_heat_generated_mwh',heat),('useful_chp_heat_delivered_mwh_th',direct),
                          ('auxiliary_heat_delivered_mwh_th',backup),('heat_dumped_mwh_th',dump),
                          ('gross_electricity_revenue_eur',gross),('auxiliary_heat_cost_eur',backup_cost),
                          ('heat_dump_penalty_eur',dump_cost),('chp_variable_cost_eur',chp_cost),
                          ('economic_contribution_proxy_eur',gross-backup_cost-dump_cost-chp_cost)]:close(d[key],value)
        values[mode]={'gross':gross,'contribution':gross-backup_cost-dump_cost-chp_cost,
                      'fuel':fuel,'backup_cost':backup_cost,'dump_cost':dump_cost,'chp_cost':chp_cost}
    f,o=values['fixed'],values['optimized']
    close(f['fuel'],o['fuel'])
    for key,value in [('incremental_economic_contribution_proxy_eur',o['contribution']-f['contribution']),
                      ('incremental_gross_electricity_value_eur',o['gross']-f['gross']),
                      ('change_in_auxiliary_heat_cost_eur',o['backup_cost']-f['backup_cost'])]:close(data[key],value)
    close(float(row['scenario_contribution_increment_eur']),o['contribution']-f['contribution'])
    close(float(row['gross_electric_increment_eur']),o['gross']-f['gross'])
    if o['contribution'] < f['contribution']-TOL:
        raise AuditError('Optimized contribution worse than fixed comparator')


def audit_emergency_case(data:dict, row:dict, registry_hash:str)->None:
    if data.get('registry_sha256')!=registry_hash or not data.get('solver',{}).get('success'):
        raise AuditError('Emergency result registry or solver mismatch')
    case=data['assumptions'];t=data['energy_totals'];hourly=data['hourly']
    if case['case_id']!=row['case_id'] or len(hourly)!=case['duration_hours']:
        raise AuditError('Emergency case identity or horizon mismatch')
    total_use=total_e=total_h=total_ed=total_hd=total_eun=total_hun=total_dump=0.0
    stock=case['initial_stock_mwh_lhv']
    for step in hourly:
        u=step['gas_use_mw_lhv'];e=step['electric_served_mw'];h=step['heat_served_mw_th']
        eu=step['electric_unserved_mw'];hu=step['heat_unserved_mw_th'];dump=step['heat_dump_mw_th']
        close(stock,step['stock_start_mwh_lhv'])
        close(stock+case['gas_inflow_mw_lhv']-u,step['stock_end_mwh_lhv'])
        close(u*case['electric_efficiency_lhv'],e)
        close(u*case['thermal_efficiency_lhv'],h+dump)
        close(e+eu,case['critical_electric_load_mw'])
        close(h+hu,case['critical_heat_load_mw'])
        if min(u,e,h,eu,hu,dump)<-TOL:raise AuditError('Negative critical-service flow')
        if stock>case['gas_storage_capacity_mwh_lhv']+TOL:raise AuditError('Excess emergency stock')
        if not (case['island_capable'] and case['chp_available']) and u>TOL:
            raise AuditError('Service incorrectly delivered without island-capable available CHP')
        if e>case['chp_electric_rating_mw']+TOL:raise AuditError('Exceeded CHP rating')
        stock=step['stock_end_mwh_lhv']
        total_use+=u;total_e+=e;total_h+=h;total_ed+=e+eu;total_hd+=h+hu;total_eun+=eu;total_hun+=hu;total_dump+=dump
    for k,v in [('gas_utilized_mwh_lhv',total_use),('electric_served_mwh',total_e),('heat_served_mwh_th',total_h),
                ('electric_demand_mwh',total_ed),('heat_demand_mwh_th',total_hd),
                ('electric_unserved_mwh',total_eun),('heat_unserved_mwh_th',total_hun),
                ('dumped_heat_mwh_th',total_dump),('terminal_inventory_mwh_lhv',stock)]:close(t[k],v)
    close(t['electric_service_fraction'],total_e/total_ed)
    close(t['heat_service_fraction'],total_h/total_hd)
    close(case['initial_stock_mwh_lhv']+case['gas_inflow_mw_lhv']*len(hourly),total_use+stock)
    close(row['electric_critical_served_mwh'],total_e)
    close(row['heat_critical_served_mwh_th'],total_h)


def audit(root:Path=ROOT,*,verbose:bool=True)->dict:
    registry_file=root/'scenarios/registry.json'
    reg=json.loads(registry_file.read_text(encoding='utf8'));reg_hash=sha(registry_file)
    result=root/'results/v0.8';summary=json.loads((result/'v08_study_summary.json').read_text(encoding='utf8'))
    if summary['registry_sha256']!=reg_hash:raise AuditError('Study registry was changed after result generation')
    with (result/'predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=reg['scenario_count_expected'] or len({r['case_id'] for r in rows})!=len(rows):
        raise AuditError('Incomplete or duplicate scenario cases')
    expected={}
    for win in reg['market_windows']:
        for storage,demand,cost,eff,rating in itertools.product(reg['gas_storage_mwh_lhv'],
            reg['heat_demand_factors_of_2022_annual_mean_production'],reg['assumed_backup_cost_eur_mwh_th'],
            reg['electrical_efficiency_lhv'],reg['rating_variants']):
            k=(win['id'],str(storage),str(demand),str(cost),str(eff),rating['id'])
            expected[k]=None
    found=set()
    market_count=0
    for row in rows:
        k=(row['market_window'],row['gas_storage_mwh_lhv'],row['heat_demand_multiplier'],row['aux_cost_eur_mwh_th'],
           row['electric_efficiency_lhv'],row['rating_variant'])
        if k not in expected or k in found:raise AuditError('Scenario outside registry or duplicate')
        found.add(k)
        p=next(x for x in reg['market_windows'] if x['id']==row['market_window'])
        recorded=summary['source_price_checksums'][p['id']]
        price_sha=sha(root/p['file'])
        if price_sha!=recorded['sha256']:raise AuditError('Observed data checksum mismatch')
        payload=json.loads((result/'cases'/f"{row['case_id']}.json").read_text(encoding='utf8'))
        # Cross-check the price/duration/time observations against the CC BY 4.0
        # input snapshot, not only against the internally reported result ledger.
        with (root/p['file']).open(newline='',encoding='utf8') as sf:
            observed=list(csv.DictReader(sf))
        if len(observed)!=len(payload['input_profile']):
            raise AuditError('Price snapshot and saved profile have differing length')
        for source,interval in zip(observed,payload['input_profile']):
            if source['start_time_utc']!=interval['start_utc'] or source['bidding_zone']!=payload['price_zone']:
                raise AuditError('Saved price timestamp or market zone does not match source snapshot')
            close(source['price'],interval['price_eur_per_mwh'],1e-9)
        audit_market_case(payload,row,reg_hash,price_sha)
        market_count+=1
    if found!=set(expected):raise AuditError('Registry matrix not fully covered')
    with (result/'hypothetical_critical_service_results.csv').open(newline='',encoding='utf8') as f:
        outrows=list(csv.DictReader(f))
    if len(outrows)!=len(reg['resilience_cases']):raise AuditError('Unexpected emergency-case count')
    out_ids={x['id'] for x in reg['resilience_cases']}
    if {x['case_id'] for x in outrows}!=out_ids:raise AuditError('Emergency-case registry incomplete')
    for row in outrows:
        payload=json.loads((result/'resilience'/f"{row['case_id']}.json").read_text(encoding='utf8'))
        audit_emergency_case(payload,row,reg_hash)
    if summary['market_scenario_count']!=market_count:raise AuditError('Summary count mismatch')
    check={'audit_status':'PASS','market_cases_verified':market_count,'emergency_cases_verified':len(outrows),
           'registry_sha256':reg_hash,
           'qualification':'Standard-library output-ledger audit performed in same project; not independent human review or plant validation.'}
    if verbose:print(json.dumps(check,indent=2))
    return check

if __name__=='__main__':audit()
