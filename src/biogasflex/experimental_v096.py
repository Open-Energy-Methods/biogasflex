"""Explicitly hypothetical CHP on/off MILP with finite-horizon commitment.

v0.9.6 extends the earlier *separate* experimental v0.9.5 LP with binary
operating, startup and shutdown decisions. Thermal service and gas conservation
remain exact; this is NOT equipment-calibrated unit commitment. Switching is
treated as instantaneous at the midpoint for ramp-exemption purposes.
No vessel dynamics, start fuel, heat storage, electrical export or grid checks.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from .baseline import Interval
from .dispatch import CONSERVATION_ABS_TOL_MWH, DispatchError
from .heat_dispatch import _audit_ledger, _fixed_scenario, _ledger, prepare_heat_inputs
from .experimental_v095 import COST_TOL, TOL, _number

MODEL = "finite_horizon_on_off_milp_v096"
REQUIRED = {
    "model", "ramp_up_mw_e_per_hour", "ramp_down_mw_e_per_hour",
    "minimum_on_power_mw_e", "initial_on", "initial_power_mw_e",
    "startup_cost_eur", "shutdown_cost_eur",
    "minimum_up_intervals", "minimum_down_intervals",
}


def _parameters(config: dict, electric_rating: float) -> dict:
    raw = config.get("experimental_v096")
    if not isinstance(raw, dict) or set(raw) != REQUIRED or raw.get("model") != MODEL:
        raise ValueError("Explicit complete experimental_v096 MILP parameters required")
    result = {"model": MODEL}
    for k in REQUIRED - {"initial_on", "model", "minimum_up_intervals", "minimum_down_intervals"}:
        result[k] = _number(raw[k], k)
    if type(raw["initial_on"]) is not bool:
        raise ValueError("initial_on must be an explicit boolean")
    result["initial_on"] = raw["initial_on"]
    for k in ("minimum_up_intervals", "minimum_down_intervals"):
        v = raw[k]
        if type(v) is not int or v < 1:
            raise ValueError(f"{k} must be an integer >= 1")
        result[k] = v
    if result["minimum_on_power_mw_e"] <= 0:
        raise ValueError("minimum_on_power_mw_e must be positive for an on/off experiment")
    if result["minimum_on_power_mw_e"] > electric_rating + TOL:
        raise ValueError("Minimum-on power exceeds nameplate power")
    if result["initial_on"]:
        if not result["minimum_on_power_mw_e"]-TOL <= result["initial_power_mw_e"] <= electric_rating+TOL:
            raise ValueError("Initial ON output must lie within nameplate and minimum-on band")
    elif result["initial_power_mw_e"] != 0:
        raise ValueError("Initially OFF CHP must have zero initial electrical power")
    return result


def _transition_audit(states, starts, stops, power, durations, limits) -> float:
    n = len(states)
    prev_y = int(limits["initial_on"])
    prev_p = limits["initial_power_mw_e"]
    excess = 0.0
    for t in range(n):
        y, z, v, p = states[t], starts[t], stops[t], power[t]
        if (z != int(y == 1 and prev_y == 0) or
                v != int(y == 0 and prev_y == 1)):
            raise DispatchError("Startup/shutdown transition binaries disagree with on/off state")
        if (y == 0 and abs(p) > TOL) or (y == 1 and
            not (limits["minimum_on_power_mw_e"]-TOL <= p <= limits["rated_power_mw_e"]+TOL)):
            raise DispatchError("CHP power violates binary on/off minimum/nameplate")
        elapsed = 0.5*(durations[t] if t == 0 else durations[t-1]+durations[t])
        if prev_y == y == 1:
            excess = max(excess,
                         p-prev_p-limits["ramp_up_mw_e_per_hour"]*elapsed,
                         prev_p-p-limits["ramp_down_mw_e_per_hour"]*elapsed)
        prev_y, prev_p = y, p
    for t in range(n):
        if starts[t]:
            if t+limits["minimum_up_intervals"]>n or not all(states[t:t+limits["minimum_up_intervals"]]):
                raise DispatchError("Minimum-up interval rule violated")
        if stops[t]:
            if t+limits["minimum_down_intervals"]>n or any(states[t:t+limits["minimum_down_intervals"]]):
                raise DispatchError("Minimum-down interval rule violated")
    return max(0.0, excess)


def optimize_commitment_milp(config: dict, intervals: Sequence[Interval]) -> dict[str, Any]:
    """Optimize a conditional finite-horizon gas/heat on-off MILP.

    Interpret declared initial_on as a boundary state with *no remaining
    pre-horizon minimum up/down obligation*. Start/stop events at horizon
    end must satisfy their full declared dwell time within this horizon,
    and a future end-of-horizon state is not imposed.
    """
    inp = prepare_heat_inputs(config, intervals)
    gas = inp.gas
    lim = _parameters(config, gas.rating_mw_e)
    lim["rated_power_mw_e"] = gas.rating_mw_e
    n = len(gas.price_intervals)
    dt = [interval.hours for interval in gas.price_intervals]
    # Blocks: [gas_use, stock_end, heat_use, backup, dumped, on, start, stop].
    u0,s0,h0,a0,w0,y0,z0,v0=(j*n for j in range(8))
    nv = 8*n
    c = np.zeros(nv,dtype=float)
    lb = np.zeros(nv,dtype=float)
    ub = np.full(nv,np.inf,dtype=float)
    integrality=np.zeros(nv,dtype=int)
    for t,interval in enumerate(gas.price_intervals):
        c[u0+t] = -gas.eta_e*(interval.price_eur_per_mwh-inp.variable_chp_cost_eur_mwh_e[t])*dt[t]
        c[a0+t] = inp.backup_cost_eur_mwh_th[t]*dt[t]
        c[w0+t] = inp.dump_penalty_eur_mwh_th[t]*dt[t]
        c[z0+t] = lim["startup_cost_eur"]
        c[v0+t] = lim["shutdown_cost_eur"]
        ub[u0+t] = gas.rating_mw_e/gas.eta_e
        ub[s0+t] = gas.storage_capacity_mwh_lhv
        ub[h0+t] = inp.demand_mw_th[t]
        ub[a0+t] = inp.backup_cap_mw_th[t]
        ub[w0+t] = inp.dump_cap_mw_th[t]
        for ix in (y0+t,z0+t,v0+t):
            ub[ix]=1
            integrality[ix]=1

    rows: list[dict[int,float]]=[]
    lower: list[float]=[]
    upper: list[float]=[]
    def row(coeff: dict[int,float], lo=-np.inf, hi=np.inf):
        rows.append({k:float(v) for k,v in coeff.items() if v != 0})
        lower.append(float(lo))
        upper.append(float(hi))
    for t in range(n):
        supply=(gas.production_mw_lhv[t]-gas.fixed_flaring_mw_lhv[t]-gas.fixed_losses_mw_lhv[t])*dt[t]
        balance={u0+t:dt[t],s0+t:1}
        if t: balance[s0+t-1]=-1
        row(balance, supply+(gas.initial_storage_mwh_lhv if t==0 else 0),
            supply+(gas.initial_storage_mwh_lhv if t==0 else 0))
        row({u0+t:gas.eta_th,h0+t:-1,w0+t:-1},0,0)
        row({h0+t:1,a0+t:1},inp.demand_mw_th[t],inp.demand_mw_th[t])
        # The binary switch ties power to the on-band with no positive
        # generation in an off interval.
        row({u0+t:gas.eta_e,y0+t:-gas.rating_mw_e},hi=0)
        row({u0+t:gas.eta_e,y0+t:-lim["minimum_on_power_mw_e"]},lo=0)
        # Exact start/stop transition, including t=0 from declared state.
        prev=int(lim["initial_on"]) if t==0 else None
        change={z0+t:1,v0+t:-1,y0+t:-1}
        if t: change[y0+t-1]=1
        row(change, -(prev if t==0 else 0), -(prev if t==0 else 0))
        row({z0+t:1,v0+t:1},hi=1)
        row({z0+t:1,y0+t:-1},hi=0)
        row({v0+t:1,y0+t:1},hi=1)
        if t==0:
            row({z0+t:1},hi=1-prev)
            row({v0+t:1},hi=prev)
        else:
            row({z0+t:1,y0+t-1:1},hi=1)
            row({v0+t:1,y0+t-1:-1},hi=0)

        # Steady-on midpoint ramps; on/off transitions deliberately
        # exempted (they are NOT realistic startup/shutdown trajectories).
        elapsed=0.5*(dt[t] if t==0 else dt[t-1]+dt[t])
        big_m=gas.rating_mw_e
        for sign, rlim in ((1,lim["ramp_up_mw_e_per_hour"]),(-1,lim["ramp_down_mw_e_per_hour"])):
            coeff={u0+t:sign*gas.eta_e,y0+t:big_m}
            if t:
                coeff[u0+t-1]=-sign*gas.eta_e
                coeff[y0+t-1]=big_m
                rhs=rlim*elapsed+2*big_m
            else:
                rhs=rlim*elapsed+big_m*(2-prev)+sign*lim["initial_power_mw_e"]
            row(coeff,hi=rhs)
    row({s0+n-1:1},gas.initial_storage_mwh_lhv,gas.initial_storage_mwh_lhv)

    # Enforce complete minimum-on/minimum-off dwell within this horizon.
    for t in range(n):
        up=lim["minimum_up_intervals"]
        down=lim["minimum_down_intervals"]
        if t+up>n: row({z0+t:1},hi=0)
        else:
            for k in range(t,t+up): row({z0+t:1,y0+k:-1},hi=0)
        if t+down>n: row({v0+t:1},hi=0)
        else:
            for k in range(t,t+down): row({v0+t:1,y0+k:1},hi=1)

    A=lil_matrix((len(rows),nv),dtype=float)
    for i,values in enumerate(rows):
        for j,v in values.items(): A[i,j]=v
    sol=milp(c,integrality=integrality,bounds=Bounds(lb,ub),
             constraints=LinearConstraint(A.tocsr(),np.array(lower),np.array(upper)),
             options={"mip_rel_gap":0.0})
    if sol.status!=0 or not sol.success or sol.x is None or sol.fun is None:
        raise DispatchError(f"Experimental on/off MILP infeasible or not optimal: {sol.status}: {sol.message}")
    x=sol.x
    states=[int(round(x[y0+t])) for t in range(n)]
    starts=[int(round(x[z0+t])) for t in range(n)]
    stops=[int(round(x[v0+t])) for t in range(n)]
    if any(abs(x[i]-round(x[i]))>TOL for t in range(n) for i in (y0+t,z0+t,v0+t)):
        raise DispatchError("Noninteger on/off/start/stop solution")
    use=[float(x[u0+t]) for t in range(n)]
    stock=[gas.initial_storage_mwh_lhv]+[float(x[s0+t]) for t in range(n)]
    heat=[min(max(0.0,gas.eta_th*u),inp.demand_mw_th[t]) for t,u in enumerate(use)]
    backup=[inp.demand_mw_th[t]-heat[t] for t in range(n)]
    dump=[gas.eta_th*use[t]-heat[t] for t in range(n)]
    ledger=_ledger(inp,use,stock,heat,backup,dump)
    _audit_ledger(inp,ledger)
    power=[gas.eta_e*u for u in use]
    ramp_violation=_transition_audit(states,starts,stops,power,dt,lim)
    if ramp_violation>TOL:
        raise DispatchError(f"Within-on-mode ramp violation: {ramp_violation}")
    startup_cost=lim["startup_cost_eur"]*sum(starts)
    shutdown_cost=lim["shutdown_cost_eur"]*sum(stops)
    value=ledger["economic_contribution_proxy_eur"]-startup_cost-shutdown_cost
    if abs(value+sol.fun)>COST_TOL:
        raise DispatchError("MILP primary objective differs from independent physical/economic ledger")

    # The inherited fixed-use ledger is a descriptive arithmetic reference;
    # it may be INFEASIBLE for a binary commitment model. Never label its
    # difference a feasible dispatch uplift unless specifically audited.
    fixed_ledger,_=_fixed_scenario(inp)
    ref_power=[
        gas.eta_e*(gas.production_mw_lhv[t]-gas.fixed_flaring_mw_lhv[t]-gas.fixed_losses_mw_lhv[t])
        for t in range(n)
    ]
    ref_on=[int(p>TOL) for p in ref_power]
    previous=int(lim["initial_on"])
    ref_starts=[];ref_stops=[]
    for y in ref_on:
        ref_starts.append(int(y==1 and previous==0))
        ref_stops.append(int(y==0 and previous==1))
        previous=y
    feasible_ref=False
    try:
        feasible_ref=(_transition_audit(ref_on,ref_starts,ref_stops,ref_power,dt,lim)<=TOL)
    except DispatchError:
        feasible_ref=False
    ref_total=(fixed_ledger["economic_contribution_proxy_eur"]
               -lim["startup_cost_eur"]*sum(ref_starts)
               -lim["shutdown_cost_eur"]*sum(ref_stops))
    if feasible_ref and value<ref_total-COST_TOL:
        raise DispatchError("Optimal MILP below a feasible fixed comparator")
    # LP upper bound ignores startup/shutdown penalties but preserves
    # the exact original heat, gas, nameplate constraints.
    from .heat_dispatch import optimize_heat_dispatch
    unconstrained=optimize_heat_dispatch(config,intervals)["optimized_dispatch"]["economic_contribution_proxy_eur"]
    if value>unconstrained+COST_TOL:
        raise DispatchError("MILP economic value exceeds original unconstrained LP upper bound")
    return {
        "version":"0.9.6","case_id":gas.case_id,"model_type":MODEL,
        "boundary":("Experimental finite-horizon on/off MILP with fixed gas inflow, "
                    "midpoint ramps only between ON intervals and unmodelled "
                    "startup dynamics, physical gas pressure and grid operation."),
        "solver":{"backend":"SciPy/HiGHS milp","success":True,
                  "status":int(sol.status),"mip_gap":float(sol.mip_gap or 0.0)},
        "limits":lim,"on":states,"starts":starts,"stops":stops,
        "start_count":sum(starts),"stop_count":sum(stops),
        "optimized_dispatch":ledger,
        "startup_cost_eur":startup_cost,"shutdown_cost_eur":shutdown_cost,
        "net_contribution_eur":value,
        "fixed_reference_feasible":feasible_ref,
        "fixed_reference_net_contribution_eur":ref_total,
        "increment_over_feasible_fixed_eur":value-ref_total if feasible_ref else None,
        "unconstrained_LP_upper_bound_eur":unconstrained,
        "max_steady_on_ramp_violation_mw_e":ramp_violation,
        "hourly":[
            {"start_utc":row.start_utc.isoformat(),"dt_h":row.hours,
             "price_eur_mwh":row.price_eur_per_mwh,"on":states[t],
             "startup":starts[t],"shutdown":stops[t],
             "gas_use_mw_lhv":use[t],"stock_end_mwh_lhv":stock[t+1],
             "power_mw_e":power[t],"useful_heat_mw_th":heat[t],
             "aux_heat_mw_th":backup[t],"dump_heat_mw_th":dump[t]}
            for t,row in enumerate(gas.price_intervals)
        ],
    }
