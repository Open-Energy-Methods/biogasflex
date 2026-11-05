"""BiogasFlex v0.7: heat-service-constrained gas-buffer CHP dispatch.

A continuous perfect-foresight *LP*, not an operationally calibrated CHP model.
Gas rates MW_LHV, inventory MWh_LHV; power MW_e; heat MW_th; prices EUR/MWh.
Fixed supply, flaring and losses; immediate heat service (no thermal storage).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Sequence

from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from .baseline import Interval, load_config, parse_prices
from .dispatch import (Inputs, DispatchError, prepare_inputs, _recalculate,
                       _assert_physical, CONSERVATION_ABS_TOL_MWH,
                       RATING_ABS_TOL_MW, OBJECTIVE_ABS_TOL_EUR)

HEAT_ABS_TOL_MWH = 1e-8
COST_ABS_TOL_EUR = 1e-7


@dataclass(frozen=True)
class HeatInputs:
    gas: Inputs
    demand_mw_th: tuple[float, ...]
    backup_cap_mw_th: tuple[float, ...]
    dump_cap_mw_th: tuple[float, ...]
    backup_cost_eur_mwh_th: tuple[float, ...]
    dump_penalty_eur_mwh_th: tuple[float, ...]
    variable_chp_cost_eur_mwh_e: tuple[float, ...]


def _nonnegative_series(config: dict, key: str, n: int, *, required: bool = False,
                        default: float = 0.0) -> tuple[float, ...]:
    if required and key not in config:
        raise ValueError(f'Heat-service scenario must specify {key}')
    raw = config.get(key, default)
    if isinstance(raw, bool):
        raise ValueError(f'{key} cannot be a boolean')
    if isinstance(raw, (int, float)):
        vals = (float(raw),) * n
    elif isinstance(raw, (list, tuple)) and len(raw) == n:
        if any(isinstance(v, bool) for v in raw):
            raise ValueError(f'{key} cannot include boolean values')
        vals = tuple(float(v) for v in raw)
    else:
        raise ValueError(f'{key} must be a scalar or {n}-entry series')
    if any(not math.isfinite(v) or v < 0 for v in vals):
        raise ValueError(f'{key} must contain finite nonnegative values')
    return vals


def prepare_heat_inputs(config: dict, intervals: Sequence[Interval], *,
                        capacity_mwh_lhv: float | None = None) -> HeatInputs:
    if config.get('heat_service_model') != 'instantaneous_heat_service_no_thermal_store_v07':
        raise ValueError('Explicit v0.7 heat_service_model configuration is required')
    gas = prepare_inputs(config, intervals, capacity=capacity_mwh_lhv)
    n = len(intervals)
    return HeatInputs(
        gas=gas,
        demand_mw_th=_nonnegative_series(config, 'heat_demand_mw_th', n, required=True),
        backup_cap_mw_th=_nonnegative_series(config, 'aux_heat_capacity_mw_th', n, required=True),
        dump_cap_mw_th=_nonnegative_series(config, 'heat_dump_capacity_mw_th', n, required=True),
        backup_cost_eur_mwh_th=_nonnegative_series(config, 'aux_heat_cost_eur_per_mwh_th', n, required=True),
        dump_penalty_eur_mwh_th=_nonnegative_series(config, 'heat_dump_penalty_eur_per_mwh_th', n),
        variable_chp_cost_eur_mwh_e=_nonnegative_series(config, 'chp_variable_cost_eur_per_mwh_e', n),
    )


def _ledger(inp: HeatInputs, gas_use: Sequence[float], stock: Sequence[float],
            heat_delivered: Sequence[float], backup: Sequence[float],
            dumped: Sequence[float]) -> dict[str, Any]:
    """Recompute the scientific ledger independently from the LP's objective or equality rows."""
    gas = inp.gas
    n = len(gas.price_intervals)
    dt = [row.hours for row in gas.price_intervals]
    base = _recalculate(gas, gas_use, stock)
    heat_gen = [gas.eta_th * u for u in gas_use]
    potential = math.fsum(h * d for h, d in zip(heat_gen, dt))
    served = math.fsum(h * d for h, d in zip(heat_delivered, dt))
    aux = math.fsum(h * d for h, d in zip(backup, dt))
    curtailed = math.fsum(h * d for h, d in zip(dumped, dt))
    demand = math.fsum(h * d for h, d in zip(inp.demand_mw_th, dt))
    r_heat = [heat_gen[t] - heat_delivered[t] - dumped[t] for t in range(n)]
    r_demand = [inp.demand_mw_th[t] - heat_delivered[t] - backup[t] for t in range(n)]
    backup_cost = math.fsum(backup[t] * inp.backup_cost_eur_mwh_th[t] * dt[t] for t in range(n))
    dump_cost = math.fsum(dumped[t] * inp.dump_penalty_eur_mwh_th[t] * dt[t] for t in range(n))
    chp_cost = math.fsum(gas.eta_e * gas_use[t] * inp.variable_chp_cost_eur_mwh_e[t] * dt[t] for t in range(n))
    electricity = base['gross_electricity_revenue_eur']
    contribution = electricity - backup_cost - dump_cost - chp_cost
    base.update({
        'heat_demand_mwh_th': demand,
        'potential_heat_generated_mwh': potential,
        'useful_chp_heat_delivered_mwh_th': served,
        'auxiliary_heat_delivered_mwh_th': aux,
        'heat_dumped_mwh_th': curtailed,
        'max_heat_conversion_residual_mwh': max(abs(v * d) for v, d in zip(r_heat, dt)),
        'max_heat_service_residual_mwh': max(abs(v * d) for v, d in zip(r_demand, dt)),
        'full_horizon_heat_conversion_residual_mwh': potential - served - curtailed,
        'full_horizon_heat_service_residual_mwh': demand - served - aux,
        'max_backup_above_capacity_mw_th': max(0.0, max(backup[t] - inp.backup_cap_mw_th[t] for t in range(n))),
        'max_dump_above_capacity_mw_th': max(0.0, max(dumped[t] - inp.dump_cap_mw_th[t] for t in range(n))),
        'minimum_heat_service_flow_mw_th': min(list(heat_delivered) + list(backup) + list(dumped)),
        'auxiliary_heat_cost_eur': backup_cost,
        'heat_dump_penalty_eur': dump_cost,
        'chp_variable_cost_eur': chp_cost,
        'incremental_cost_proxy_total_eur': backup_cost + dump_cost + chp_cost,
        'economic_contribution_proxy_eur': contribution,
    })
    return base


def _audit_ledger(inp: HeatInputs, ledger: dict[str, Any]) -> None:
    _assert_physical(inp.gas, ledger)
    for key in ('max_heat_conversion_residual_mwh', 'max_heat_service_residual_mwh',
                'full_horizon_heat_conversion_residual_mwh', 'full_horizon_heat_service_residual_mwh'):
        if abs(ledger[key]) > HEAT_ABS_TOL_MWH:
            raise DispatchError(f'Heat conservation/service error: {key}={ledger[key]}')
    for key in ('max_backup_above_capacity_mw_th', 'max_dump_above_capacity_mw_th'):
        if ledger[key] > RATING_ABS_TOL_MW:
            raise DispatchError(f'Heat-resource capacity exceeded: {key}={ledger[key]}')
    if ledger['minimum_heat_service_flow_mw_th'] < -RATING_ABS_TOL_MW:
        raise DispatchError('Negative delivered/backup/dumped heat')


def _fixed_scenario(inp: HeatInputs) -> tuple[dict[str, Any], dict[str, list[float]]]:
    gas = inp.gas
    n = len(gas.price_intervals)
    u = [gas.production_mw_lhv[t] - gas.fixed_flaring_mw_lhv[t] - gas.fixed_losses_mw_lhv[t] for t in range(n)]
    if any(v * gas.eta_e > gas.rating_mw_e + RATING_ABS_TOL_MW for v in u):
        raise DispatchError('Fixed CHP baseline infeasible at electrical rating')
    potential = [gas.eta_th * v for v in u]
    useful = [min(potential[t], inp.demand_mw_th[t]) for t in range(n)]
    backup = [inp.demand_mw_th[t] - useful[t] for t in range(n)]
    dumped = [potential[t] - useful[t] for t in range(n)]
    stock = [gas.initial_storage_mwh_lhv] * (n + 1)
    ledger = _ledger(inp, u, stock, useful, backup, dumped)
    _audit_ledger(inp, ledger)
    return ledger, {'gas_use': u, 'inventory': stock, 'useful': useful,
                    'backup': backup, 'dump': dumped}


def optimize_heat_dispatch(config: dict, intervals: Sequence[Interval], *,
                           capacity_mwh_lhv: float | None = None) -> dict[str, Any]:
    """Maximize spot-equivalent contribution net of *assumed scenario* costs.

    LP decision variables per interval: gas utilization, end-of-interval gas stock,
    CHP useful heat, auxiliary heat, dumped heat. Gas and heat equalities exact.
    Requires a feasible fixed baseline, same time-resolved heat demand in both cases.
    """
    inp = prepare_heat_inputs(config, intervals, capacity_mwh_lhv=capacity_mwh_lhv)
    gas = inp.gas
    n = len(gas.price_intervals)
    dt = [r.hours for r in gas.price_intervals]
    # Stable group layout: u[n], s[n], q_useful[n], q_backup[n], q_dump[n].
    uid, sid, hid, aid, did = 0, n, 2*n, 3*n, 4*n
    numvar = 5*n
    c = [0.0] * numvar
    bounds = [(0.0, None)] * numvar
    for t, row in enumerate(gas.price_intervals):
        c[uid+t] = -gas.eta_e * (row.price_eur_per_mwh - inp.variable_chp_cost_eur_mwh_e[t]) * dt[t]
        c[aid+t] = inp.backup_cost_eur_mwh_th[t] * dt[t]
        c[did+t] = inp.dump_penalty_eur_mwh_th[t] * dt[t]
        bounds[uid+t] = (0.0, gas.rating_mw_e / gas.eta_e)
        bounds[sid+t] = (0.0, gas.storage_capacity_mwh_lhv)
        bounds[hid+t] = (0.0, inp.demand_mw_th[t])
        bounds[aid+t] = (0.0, inp.backup_cap_mw_th[t])
        bounds[did+t] = (0.0, inp.dump_cap_mw_th[t])
    # n gas balances + n instantaneous heat-potential balances + n heat-service balances + 1 cyclic inventory.
    a = lil_matrix((3*n+1,numvar),dtype=float)
    b = [0.0]*(3*n+1)
    for t in range(n):
        a[t,uid+t] = dt[t]
        a[t,sid+t] = 1.0
        if t: a[t,sid+t-1] = -1.0
        b[t] = (gas.production_mw_lhv[t] - gas.fixed_flaring_mw_lhv[t]
                - gas.fixed_losses_mw_lhv[t])*dt[t] + (gas.initial_storage_mwh_lhv if t==0 else 0.0)
        a[n+t,uid+t] = gas.eta_th
        a[n+t,hid+t] = -1.0
        a[n+t,did+t] = -1.0
        a[2*n+t,hid+t] = 1.0
        a[2*n+t,aid+t] = 1.0
        b[2*n+t] = inp.demand_mw_th[t]
    a[3*n,sid+n-1] = 1.0
    b[3*n] = gas.initial_storage_mwh_lhv
    fixed, fixed_vars = _fixed_scenario(inp)
    sol = linprog(c,A_eq=a.tocsr(),b_eq=b,bounds=bounds,method='highs')
    if sol.status != 0 or not sol.success or sol.x is None or sol.fun is None:
        raise DispatchError(f'Heat-LP did not find an optimum: status={sol.status}; {sol.message}')
    u=[float(v) for v in sol.x[uid:uid+n]]
    s=[gas.initial_storage_mwh_lhv]+[float(v) for v in sol.x[sid:sid+n]]
    # Use CHP heat for contemporaneous demand before calling on backup or dumping.
    # This resolves otherwise-degenerate zero-cost choices (backup and dumping in
    # the same interval), without changing gas dispatch or primary optimum.
    # Maximal direct heat allocation weakly decreases both auxiliary heat and dump
    # so it cannot break either upper capacity bound.
    useful=[min(gas.eta_th*u[t],inp.demand_mw_th[t]) for t in range(n)]
    backup=[inp.demand_mw_th[t]-useful[t] for t in range(n)]
    dumped=[gas.eta_th*u[t]-useful[t] for t in range(n)]
    optim=_ledger(inp,u,s,useful,backup,dumped)
    _audit_ledger(inp, optim)
    if abs(-float(sol.fun) - optim['economic_contribution_proxy_eur'])>COST_ABS_TOL_EUR:
        raise DispatchError('Heat LP objective and independent contribution ledger disagree')
    gas_difference=optim['gas_utilized_mwh_lhv']-fixed['gas_utilized_mwh_lhv']
    if abs(gas_difference)>CONSERVATION_ABS_TOL_MWH:
        raise DispatchError('Compared scenarios consume different gas energy')
    if abs(optim['heat_demand_mwh_th']-fixed['heat_demand_mwh_th'])>HEAT_ABS_TOL_MWH:
        raise DispatchError('Compared scenarios do not serve identical heat demand')
    delta_gross=optim['gross_electricity_revenue_eur']-fixed['gross_electricity_revenue_eur']
    delta_proxy=optim['economic_contribution_proxy_eur']-fixed['economic_contribution_proxy_eur']
    if delta_proxy < -OBJECTIVE_ABS_TOL_EUR:
        raise DispatchError('Optimized contribution below feasible fixed comparator')
    return {
        'version':'0.7.0', 'case_id':gas.case_id,
        'model_type':'continuous heat-service-constrained LP solved by SciPy/HiGHS',
        'solver': {'library':'scipy.optimize.linprog','backend':'HiGHS','status_code':int(sol.status),
                   'success':bool(sol.success),'termination':str(sol.message),'iterations':int(sol.nit)},
        'claim_boundary':'Hypothetical perfect-foresight spot-equivalent CHP dispatch contribution with fixed simultaneous heat demand and assumed backup/heat-sink capacities and cost coefficients; not calibrated Lövsta heat use, actual exports, plant profitability or operational validation.',
        'price_zone':gas.zone,'gas_basis':'MWh_LHV','currency':'EUR',
        'capacity_mwh_lhv':gas.storage_capacity_mwh_lhv,
        'initial_and_terminal_stock_mwh_lhv':gas.initial_storage_mwh_lhv,
        'chp_electric_rating_mw':gas.rating_mw_e,
        'electric_efficiency_lhv_assumed':gas.eta_e,
        'thermal_efficiency_lhv_assumed':gas.eta_th,
        'interval_count':n,'duration_hours':math.fsum(dt),
        'thermal_service': {
            'requirement':'Demand is met in each interval by CHP useful heat plus auxiliary heat',
            'heat_storage_included':False,
            'auxiliary_heat_cost_note':'Marginal scenario cost, not observed plant OPEX',
            'heat_dump_cost_note':'Synthetic penalty; physical heat-rejection availability not verified',
            'heat_demand_total_mwh_th':fixed['heat_demand_mwh_th']},
        'fixed_dispatch':fixed,'optimized_dispatch':optim,
        'incremental_gross_electricity_value_eur':delta_gross,
        'incremental_economic_contribution_proxy_eur':delta_proxy,
        'change_in_auxiliary_heat_cost_eur': optim['auxiliary_heat_cost_eur']-fixed['auxiliary_heat_cost_eur'],
        'change_in_heat_dump_penalty_eur': optim['heat_dump_penalty_eur']-fixed['heat_dump_penalty_eur'],
        'change_in_chp_variable_cost_eur': optim['chp_variable_cost_eur']-fixed['chp_variable_cost_eur'],
        'input_profile': [
            {'start_utc':r.start_utc.isoformat(),
             'end_utc':(r.start_utc+timedelta(hours=r.hours)).isoformat(),
             'dt_h':r.hours,'price_eur_per_mwh':r.price_eur_per_mwh,
             'heat_demand_mw_th':inp.demand_mw_th[t],
             'gas_production_mw_lhv':gas.production_mw_lhv[t],
             'fixed_flaring_mw_lhv':gas.fixed_flaring_mw_lhv[t],
             'fixed_losses_mw_lhv':gas.fixed_losses_mw_lhv[t],
             'fixed_chp_power_mw_e':gas.eta_e*fixed_vars['gas_use'][t],
             'fixed_gas_use_mw_lhv':fixed_vars['gas_use'][t],
             'fixed_useful_heat_mw_th':fixed_vars['useful'][t],
             'fixed_auxiliary_heat_mw_th':fixed_vars['backup'][t],
             'fixed_heat_dump_mw_th':fixed_vars['dump'][t],
             'optimized_chp_power_mw_e':gas.eta_e*u[t],
             'optimized_gas_use_mw_lhv':u[t],
             'optimized_heat_potential_mw_th':gas.eta_th*u[t],
             'optimized_useful_heat_mw_th':useful[t],
             'optimized_auxiliary_heat_mw_th':backup[t],
             'optimized_heat_dump_mw_th':dumped[t],
             'stock_start_mwh_lhv':s[t],
             'stock_end_mwh_lhv':s[t+1],
             'auxiliary_heat_cost_eur_per_mwh_th':inp.backup_cost_eur_mwh_th[t],
             'heat_dump_penalty_eur_per_mwh_th':inp.dump_penalty_eur_mwh_th[t],
             'chp_variable_cost_eur_per_mwh_e':inp.variable_chp_cost_eur_mwh_e[t]}
            for t,r in enumerate(gas.price_intervals)],
        'tolerance_contract': {
            'max_absolute_gas_balance_mwh':CONSERVATION_ABS_TOL_MWH,
            'max_absolute_heat_balance_mwh':HEAT_ABS_TOL_MWH,
            'max_absolute_rating_error_mw':RATING_ABS_TOL_MW,
            'max_absolute_objective_recalculation_eur':COST_ABS_TOL_EUR,
        },
    }


def _sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_heat_case(config_path:Path,price_path:Path)->tuple[dict,list[Interval]]:
    config=load_config(config_path)
    if 'price_window_end_utc' not in config:
        raise ValueError('Explicit terminal price-window end required')
    rows=parse_prices(price_path,config['price_zone'],end_utc=config['price_window_end_utc'],
                      required_hours=config.get('expected_duration_hours'))
    return config, rows


def run_heat_dispatch(config_path:Path,price_path:Path,output_path:Path,*,
                      capacity_mwh_lhv:float|None=None)->dict[str,Any]:
    cfg,intervals=load_heat_case(config_path,price_path)
    result=optimize_heat_dispatch(cfg,intervals,capacity_mwh_lhv=capacity_mwh_lhv)
    result['provenance']={'config_path':str(config_path),'config_sha256':_sha256(config_path),
                          'price_path':str(price_path),'price_sha256':_sha256(price_path)}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
    return result
