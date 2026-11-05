"""BiogasFlex v0.8: strictly hypothetical, short emergency critical-service model.

No actual plant islanding, black start, battery, controls, emergency gas inventory,
backup heat, or regional critical-load coverage is established. This is NOT a
continuation of the cyclic, grid-connected economic dispatch calculation.

A simple continuous LP maximizes two explicitly weighted energy-service measures
conditional on island-capable CHP and an initially charged gas store. It is not a
physical islanding feasibility model. Electricity and useful heat are co-products.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

TOL = 1e-8


def _positive_finite(value, name: str, *, can_be_zero: bool=False) -> float:
    if isinstance(value, bool) or not isinstance(value,(float,int)):
        raise ValueError(f'{name} must be a numeric value, not bool or string')
    v=float(value)
    if not math.isfinite(v) or v<0 or (v==0 and not can_be_zero):
        raise ValueError(f'{name} must be finite and {"nonnegative" if can_be_zero else "positive"}')
    return v


def _validate(case: dict) -> dict:
    required = ('case_id','duration_hours','gas_inflow_mw_lhv','electric_efficiency_lhv',
                'thermal_efficiency_lhv','chp_electric_rating_mw','gas_storage_capacity_mwh_lhv',
                'initial_stock_mwh_lhv','critical_electric_load_mw','critical_heat_load_mw',
                'island_capable','chp_available','grid_available','auxiliary_heat_available')
    for k in required:
        if k not in case: raise ValueError(f'Missing emergency case field: {k}')
    if not isinstance(case['case_id'],str) or not case['case_id']:
        raise ValueError('case_id must be nonempty text')
    if isinstance(case['duration_hours'],bool) or not isinstance(case['duration_hours'],int) or not 1<=case['duration_hours']<=168:
        raise ValueError('duration_hours must be an integer 1..168')
    for flag in ('island_capable','chp_available','grid_available','auxiliary_heat_available'):
        if not isinstance(case[flag],bool): raise ValueError(f'{flag} must be boolean')
    if case['grid_available'] or case['auxiliary_heat_available']:
        raise ValueError('This emergency LP requires zero grid and zero external auxiliary heat')
    vals = {k:_positive_finite(case[k],k,can_be_zero=(k not in ('chp_electric_rating_mw', 'electric_efficiency_lhv')))
            for k in ('gas_inflow_mw_lhv','electric_efficiency_lhv','thermal_efficiency_lhv',
                      'chp_electric_rating_mw','gas_storage_capacity_mwh_lhv','initial_stock_mwh_lhv',
                      'critical_electric_load_mw','critical_heat_load_mw')}
    # v0.9 boundary fix: the defined experiment is a TOTAL gas-supply interruption.
    # Earlier code accepted positive inflow while continuing to label the result
    # as a total outage; reject that out-of-scope input explicitly.
    if vals['gas_inflow_mw_lhv'] != 0.0:
        raise ValueError('Declared total gas-inflow interruption requires gas_inflow_mw_lhv == 0')
    if vals['electric_efficiency_lhv']>1 or vals['electric_efficiency_lhv']+vals['thermal_efficiency_lhv']>1+1e-12:
        raise ValueError('Unphysical electrical/thermal conversion efficiencies')
    if vals['initial_stock_mwh_lhv']>vals['gas_storage_capacity_mwh_lhv']+TOL:
        raise ValueError('Initial gas inventory exceeds storage capacity')
    if not (vals['critical_electric_load_mw']>0 and vals['critical_heat_load_mw']>0):
        raise ValueError('Both critical services must have positive demand')
    return vals


def optimize_emergency_service(case: dict) -> dict[str,Any]:
    """LP for grid-down service. The inventory is NOT cyclic during an emergency.

    LP variables in each 1-hour interval: gas-use (MW_LHV), end stock (MWh_LHV),
    useful electric (MW_e), unmet electric (MW_e), useful CHP heat (MW_th),
    unmet heat (MW_th), dumped heat (MW_th).
    Minimize electric/heat unserved weighted energies (synthetic weights 10:1).
    Gas-use is zero if island-capable conversion/CHP availability is not assumed.
    """
    v=_validate(case)
    n=case['duration_hours']
    eta_e,eta_h=v['electric_efficiency_lhv'],v['thermal_efficiency_lhv']
    input_rate=v['gas_inflow_mw_lhv']
    stock0=v['initial_stock_mwh_lhv']
    sc=v['gas_storage_capacity_mwh_lhv']
    de=v['critical_electric_load_mw']
    dh=v['critical_heat_load_mw']
    gate=case['island_capable'] and case['chp_available']
    # Seven variable blocks, one per hour.
    uid,sid,eid,meid,hid,mhid,did=[i*n for i in range(7)]
    count=7*n
    c=[0.0]*count
    bounds=[(0.0,None)]*count
    for t in range(n):
        c[meid+t]=10.0
        c[mhid+t]=1.0
        bounds[uid+t]=(0.0, min(v['chp_electric_rating_mw']/eta_e,de/eta_e) if gate else 0.0)
        bounds[sid+t]=(0.0,sc)
        bounds[eid+t]=(0.0,de)
        bounds[meid+t]=(0.0,de)
        bounds[hid+t]=(0.0,dh)
        bounds[mhid+t]=(0.0,dh)
        bounds[did+t]=(0.0,None)
    # Conservation, electricity co-product, electric service, thermal co-product, heat service.
    a=lil_matrix((5*n,count),dtype=float)
    b=[0.0]*(5*n)
    for t in range(n):
        a[t,uid+t]=1.0
        a[t,sid+t]=1.0
        if t:a[t,sid+t-1]=-1.0
        b[t]=input_rate+(stock0 if t==0 else 0.0)
        a[n+t,uid+t]=eta_e; a[n+t,eid+t]=-1.0
        a[2*n+t,eid+t]=1.0; a[2*n+t,meid+t]=1.0
        b[2*n+t]=de
        a[3*n+t,uid+t]=eta_h; a[3*n+t,hid+t]=-1.0; a[3*n+t,did+t]=-1.0
        a[4*n+t,hid+t]=1.0; a[4*n+t,mhid+t]=1.0
        b[4*n+t]=dh
    sol=linprog(c,A_eq=a.tocsr(),b_eq=b,bounds=bounds,method='highs')
    if sol.status!=0 or sol.x is None or not sol.success:
        raise ValueError(f'Emergency service LP infeasible: {sol.status}: {sol.message}')
    vectors=[[float(q) for q in sol.x[g:g+n]] for g in (uid,sid,eid,meid,hid,mhid,did)]
    uses,ends,e_serv,e_unmet,h_serv,h_unmet,h_dump=vectors
    s=[stock0]+ends
    gas_res=[s[t]+input_rate-uses[t]-s[t+1] for t in range(n)]
    e_res=[eta_e*uses[t]-e_serv[t] for t in range(n)]
    h_res=[eta_h*uses[t]-h_serv[t]-h_dump[t] for t in range(n)]
    elec_res=[e_serv[t]+e_unmet[t]-de for t in range(n)]
    heat_res=[h_serv[t]+h_unmet[t]-dh for t in range(n)]
    errors={'gas_inventory_mwh_lhv':max(map(abs,gas_res)),'electric_cogeneration_mwh':max(map(abs,e_res)),
            'heat_cogeneration_mwh':max(map(abs,h_res)),
            'electric_service_mwh':max(map(abs,elec_res)), 'heat_service_mwh':max(map(abs,heat_res))}
    if any(err>TOL for err in errors.values()):raise RuntimeError(f'Emergency physical ledger violated: {errors}')
    if ends[-1]<-TOL:raise RuntimeError('Negative terminal gas inventory')
    totals={
        'gas_inflow_mwh_lhv':input_rate*n,'gas_utilized_mwh_lhv':math.fsum(uses),
        'initial_inventory_mwh_lhv':stock0,'terminal_inventory_mwh_lhv':s[-1],
        'electric_demand_mwh':de*n,'electric_served_mwh':math.fsum(e_serv),'electric_unserved_mwh':math.fsum(e_unmet),
        'heat_demand_mwh_th':dh*n,'heat_served_mwh_th':math.fsum(h_serv),'heat_unserved_mwh_th':math.fsum(h_unmet),
        'dumped_heat_mwh_th':math.fsum(h_dump),
        'electric_service_fraction':math.fsum(e_serv)/(de*n), 'heat_service_fraction':math.fsum(h_serv)/(dh*n)}
    if abs(stock0+input_rate*n-totals['gas_utilized_mwh_lhv']-s[-1])>TOL:
        raise RuntimeError('Integrated emergency gas mass balance failed')
    return {
        'version':'0.8.0','case_id':case['case_id'],
        'boundary':'Hypothetical 3-hour gas-inflow outage; grid power unavailable; island-capable CHP and available equipment ASSUMED where enabled, not demonstrated. Gas buffer precharged exogenously; no cyclic stock. Service accounting, not regional resilience or validated black start.',
        'assumptions':dict(case),'solver':{'backend':'HiGHS','success':True,'status_code':0,'termination':str(sol.message)},
        'energy_totals':totals,'max_abs_residuals':errors,
        'hourly':[{'hour_index':t,'gas_use_mw_lhv':uses[t],'stock_start_mwh_lhv':s[t],
                   'stock_end_mwh_lhv':s[t+1],
                   'critical_electric_load_mw':de,'electric_served_mw':e_serv[t],
                   'electric_unserved_mw':e_unmet[t],
                   'critical_heat_load_mw_th':dh,'heat_served_mw_th':h_serv[t],
                   'heat_unserved_mw_th':h_unmet[t], 'heat_dump_mw_th':h_dump[t]}
                  for t in range(n)]
    }
