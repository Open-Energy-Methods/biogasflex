"""Explicitly hypothetical CHP on/off MILP with finite-horizon commitment.

v0.9.8 extends the separate experimental v0.9.6 binary CHP model with
clock-hour dwell constraints and explicit pre-horizon residual obligations. Thermal service and gas conservation
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

MODEL = "receding_horizon_commitment_milp_v098"
TIME_TOL_H = 1e-9
REQUIRED = {
    "model", "ramp_up_mw_e_per_hour", "ramp_down_mw_e_per_hour",
    "minimum_on_power_mw_e", "initial_on", "initial_power_mw_e",
    "startup_cost_eur", "shutdown_cost_eur",
    "minimum_up_hours", "minimum_down_hours", "initial_remaining_dwell_hours",
    "terminal_gas_inventory_mwh_lhv", "initial_power_observation_age_hours",
}


def _parameters(config: dict, electric_rating: float) -> dict:
    """Validate explicit nonnegative hourly and initial operating assumptions."""
    raw = config.get("experimental_v098")
    if not isinstance(raw, dict) or set(raw) != REQUIRED or raw.get("model") != MODEL:
        raise ValueError("Explicit complete experimental_v098 hourly commitment configuration required")
    out = {"model": MODEL}
    for key in REQUIRED - {"initial_on", "model"}:
        out[key] = _number(raw[key], key)
    if type(raw["initial_on"]) is not bool:
        raise ValueError("initial_on must be an explicit boolean")
    out["initial_on"] = raw["initial_on"]
    for key in ("minimum_up_hours", "minimum_down_hours"):
        if out[key] <= 0:
            raise ValueError(f"{key} must be strictly positive elapsed hours")
    prior_min = out["minimum_up_hours"] if out["initial_on"] else out["minimum_down_hours"]
    if out["initial_remaining_dwell_hours"] > prior_min + TIME_TOL_H:
        raise ValueError("Prior remaining dwell cannot exceed the chosen minimum operating duration")
    if not 0 < out["minimum_on_power_mw_e"] <= electric_rating + TOL:
        raise ValueError("Minimum-on power must be positive and within nameplate rating")
    if out["initial_on"]:
        if not out["minimum_on_power_mw_e"]-TOL <= out["initial_power_mw_e"] <= electric_rating+TOL:
            raise ValueError("Initial ON power outside minimum-on/nameplate bounds")
    elif out["initial_power_mw_e"] != 0:
        raise ValueError("Initially OFF CHP must have zero initial electrical output")
    return out


def _hours(durations: Sequence[float]) -> list[float]:
    """Hours since first interval start, including the terminal boundary."""
    return [math.fsum(durations[:i]) for i in range(len(durations)+1)]


def _dwell_window(t: int, minimum_hours: float,
                  offsets: Sequence[float]) -> range | None:
    """Whole slots intersecting an elapsed-hour dwell from slot-start t.

    Switching occurs at interval boundaries; midpoint power is constant per
    slot for commitment purposes. An intersected partial final slot is
    therefore locked in its entirety. An end-crossing event is prohibited.
    """
    deadline = offsets[t] + minimum_hours
    if deadline > offsets[-1] + TIME_TOL_H:
        return None
    end = t
    while end < len(offsets)-1 and offsets[end] < deadline-TIME_TOL_H:
        end += 1
    return range(t, end)

def _transition_audit(states, starts, stops, power, durations, limits) -> float:
    n = len(states)
    offsets = _hours(durations)
    prior = int(limits["initial_on"])
    prev_p = limits["initial_power_mw_e"]
    violation = 0.0
    residual = limits["initial_remaining_dwell_hours"]
    for t in range(n):
        y, z, v, p = states[t], starts[t], stops[t], power[t]
        if y not in (0,1) or z not in (0,1) or v not in (0,1):
            raise DispatchError("Operating/transition flags are not binary")
        if z != int(y==1 and prior==0) or v != int(y==0 and prior==1):
            raise DispatchError("On/off transition event does not match operating state")
        if offsets[t] < residual-TIME_TOL_H and y != int(limits["initial_on"]):
            raise DispatchError("Pre-horizon minimum dwell obligation violated")
        if ((not y and abs(p)>TOL) or
                (y and not limits["minimum_on_power_mw_e"]-TOL <= p <=
                 limits["rated_power_mw_e"]+TOL)):
            raise DispatchError("Binary CHP power/nameplate/minimum-on limit violated")
        elapsed = (limits["initial_power_observation_age_hours"]+0.5*durations[0]
                   if t==0 else 0.5*(durations[t-1]+durations[t]))
        if prior==y==1:
            violation=max(violation,
                          p-prev_p-limits["ramp_up_mw_e_per_hour"]*elapsed,
                          prev_p-p-limits["ramp_down_mw_e_per_hour"]*elapsed)
        if z or v:
            key = "minimum_up_hours" if z else "minimum_down_hours"
            window = _dwell_window(t, limits[key], offsets)
            if window is None:
                raise DispatchError("New commitment event cannot finish mandatory hours in horizon")
            if any(states[k] != y for k in window):
                raise DispatchError("Elapsed-hour minimum operating dwell violated")
        prior, prev_p = y, p
    return max(0.0, violation)

def optimize_commitment_milp(config: dict, intervals: Sequence[Interval]) -> dict[str, Any]:
    """Finite-horizon commitment with *elapsed hours* and declared history.

    Initial residual dwell is enforced from the first slot boundary.
    New starts/stops must complete all operating hours within this horizon.
    """
    inp = prepare_heat_inputs(config, intervals)
    gas = inp.gas
    lim = _parameters(config, gas.rating_mw_e)
    lim["rated_power_mw_e"] = gas.rating_mw_e
    n = len(gas.price_intervals)
    terminal = lim["terminal_gas_inventory_mwh_lhv"]
    if terminal > gas.storage_capacity_mwh_lhv + TOL:
        raise ValueError("Terminal inventory target exceeds gas vessel storage capacity")
    dt = [interval.hours for interval in gas.price_intervals]
    offsets = _hours(dt)
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
        elapsed=(lim["initial_power_observation_age_hours"]+0.5*dt[0]
                 if t==0 else 0.5*(dt[t-1]+dt[t]))
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
    row({s0+n-1:1},terminal,terminal)

    # Enforce the pre-horizon residual obligation from the start boundary.
    residual = lim["initial_remaining_dwell_hours"]
    if residual:
        forced = int(lim["initial_on"])
        for t in range(n):
            if offsets[t] < residual-TIME_TOL_H:
                row({y0+t:1},forced,forced)

    # New events use elapsed-hour dwell, not number of intervals. A new event
    # requiring time past the horizon is disallowed, not silently relaxed.
    for t in range(n):
        for var,active,key in (
            (z0+t,1,"minimum_up_hours"),(v0+t,0,"minimum_down_hours")
        ):
            window = _dwell_window(t,lim[key],offsets)
            if window is None:
                row({var:1},hi=0)
            elif active:
                for k in window:
                    row({var:1,y0+k:-1},hi=0)
            else:
                for k in window:
                    row({var:1,y0+k:1},hi=1)

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
    # v0.7's independent ledger assumes cyclic stock equal to initial
    # inventory. For rolling horizons, the initial inventory changes but
    # the ORIGINAL fixed final target does not. Re-label only the terminal
    # residual against the explicit target; preserve physical interval and
    # whole-horizon balances calculated using true stock[0].
    ledger["legacy_initial_inventory_cycle_residual_mwh"]=ledger["terminal_inventory_residual_mwh"]
    ledger["terminal_inventory_target_mwh_lhv"]=terminal
    ledger["terminal_inventory_residual_mwh"]=stock[-1]-terminal
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
    if abs(gas.initial_storage_mwh_lhv-terminal)<=TOL:
        try:
            feasible_ref=(_transition_audit(ref_on,ref_starts,ref_stops,ref_power,dt,lim)<=TOL)
        except DispatchError:
            feasible_ref=False
    ref_total=(fixed_ledger["economic_contribution_proxy_eur"]
               -lim["startup_cost_eur"]*sum(ref_starts)
               -lim["shutdown_cost_eur"]*sum(ref_stops))
    if feasible_ref and value<ref_total-COST_TOL:
        raise DispatchError("Optimal MILP below a feasible fixed comparator")
    # A *real* LP relaxation of THIS SAME model and explicit terminal
    # stock target. It remains an upper bound even when rolling replans
    # change the initial inventory while preserving a fixed final target.
    relaxed = milp(c,integrality=np.zeros(nv,dtype=int),bounds=Bounds(lb,ub),
                   constraints=LinearConstraint(A.tocsr(),np.array(lower),np.array(upper)))
    if relaxed.status!=0 or not relaxed.success or relaxed.fun is None:
        raise DispatchError("Continuous relaxation failed; cannot certify MILP value")
    relaxed_bound=-float(relaxed.fun)
    if value>relaxed_bound+COST_TOL:
        raise DispatchError("Committed value exceeds matched-boundary LP relaxation")
    return {
        "version":"0.9.8","case_id":gas.case_id,"model_type":MODEL,
        "boundary":("Price-only synthetic rolling commitment, explicit gas terminal "
                    "target, elapsed-hour prior dwell and fixed heat/gas profile; "
                    "no calibrated CHP transients, dynamic plant measurements, "
                    "real forecast algorithm or validated real-market operation."),
        "solver":{"backend":"SciPy/HiGHS milp","success":True,
                  "status":int(sol.status),"mip_gap":float(sol.mip_gap or 0.0)},
        "limits":lim,"on":states,"starts":starts,"stops":stops,
        "initial_stock_mwh_lhv":gas.initial_storage_mwh_lhv,
        "terminal_target_mwh_lhv":terminal,
        "clock_hours_from_horizon_start":offsets,
        "carry_in_remaining_dwell_hours":residual,
        "carry_in_remaining_after_horizon_hours":max(0.0,residual-offsets[-1]),
        "dwell_boundary_policy":"whole overlapping slots; new events must complete within horizon",
        "start_count":sum(starts),"stop_count":sum(stops),
        "optimized_dispatch":ledger,
        "startup_cost_eur":startup_cost,"shutdown_cost_eur":shutdown_cost,
        "net_contribution_eur":value,
        "fixed_reference_feasible":feasible_ref,
        "fixed_reference_net_contribution_eur":ref_total,
        "increment_over_feasible_fixed_eur":value-ref_total if feasible_ref else None,
        "same_boundary_LP_relaxation_upper_bound_eur":relaxed_bound,
        "max_steady_on_ramp_violation_mw_e":ramp_violation,
        "hourly":[
            {"start_utc":row.start_utc.isoformat(),"dt_h":row.hours,
             "price_eur_mwh":row.price_eur_per_mwh,"on":states[t],
             "startup":starts[t],"shutdown":stops[t],
             "gas_use_mw_lhv":use[t],"stock_end_mwh_lhv":stock[t+1],
             "elapsed_start_h":offsets[t],"elapsed_end_h":offsets[t+1],
             "power_mw_e":power[t],"useful_heat_mw_th":heat[t],
             "aux_heat_mw_th":backup[t],"dump_heat_mw_th":dump[t]}
            for t,row in enumerate(gas.price_intervals)
        ],
    }


def _slice_config(config: dict, first: int, total: int) -> dict:
    """Return a self-contained suffix without changing original profiles.

    No future physical-input prediction errors are modeled: gas/heat
    assumptions are the same as those used to compute all alternatives.
    """
    result=dict(config)
    keys=(
        "gas_production_mw_lhv","fixed_flaring_mw_lhv","fixed_losses_mw_lhv",
        "heat_demand_mw_th","aux_heat_capacity_mw_th",
        "heat_dump_capacity_mw_th","aux_heat_cost_eur_per_mwh_th",
        "heat_dump_penalty_eur_per_mwh_th","chp_variable_cost_eur_per_mwh_e",
    )
    for key in keys:
        value=result.get(key)
        if isinstance(value,(list,tuple)):
            if len(value)!=total:
                raise ValueError(f"{key} must match the entire realized time grid")
            result[key]=list(value[first:])
    return result


def _check_forecast_snapshots(actual: Sequence[Interval],
                              forecasts: Sequence[Sequence[Interval]]) -> None:
    if not actual or len(forecasts)!=len(actual):
        raise ValueError("Exactly one forecast snapshot per realized interval is required")
    for t,snapshot in enumerate(forecasts):
        if len(snapshot)!=len(actual)-t:
            raise ValueError(f"Forecast snapshot {t} must cover ALL remaining intervals")
        for predicted,observed in zip(snapshot,actual[t:]):
            if (predicted.start_utc!=observed.start_utc
                or predicted.zone!=observed.zone
                or predicted.hours!=observed.hours
                or not math.isfinite(predicted.price_eur_per_mwh)):
                raise ValueError("Forecast and realized prices require identical UTC grids, duration and zone")


def evaluate_rolling_prices(config: dict,
                            realized_intervals: Sequence[Interval],
                            forecast_snapshots: Sequence[Sequence[Interval]]) -> dict[str, Any]:
    """Forecast-plan/execute-one/replan for a synthetic *fixed gas/heat* case.

    Forecast snapshots must be supplied ex ante as a full triangular
    matrix of predicted remaining-horizon prices. No actual forecasting,
    physical recourse, gas/heat forecast errors or stochastic process.
    All reoptimizations keep the ORIGINAL terminal inventory target.
    """
    _check_forecast_snapshots(realized_intervals,forecast_snapshots)
    inp=prepare_heat_inputs(config,realized_intervals)
    n=len(realized_intervals)
    basis=dict(config)
    initial=basis.get("experimental_v098")
    if not isinstance(initial,dict):
        raise ValueError("Explicit experimental_v098 assumptions required")
    _parameters(basis,inp.gas.rating_mw_e)
    original_target=_number(initial["terminal_gas_inventory_mwh_lhv"],"terminal_gas_inventory_mwh_lhv")
    if abs(original_target-inp.gas.initial_storage_mwh_lhv)>TOL:
        raise ValueError("Rolling comparison requires initial and final original gas inventory to match")

    perfect=optimize_commitment_milp(basis,realized_intervals)
    current_stock=inp.gas.initial_storage_mwh_lhv
    current_on=initial["initial_on"]
    current_power=initial["initial_power_mw_e"]
    current_remaining=initial["initial_remaining_dwell_hours"]
    duration=[interval.hours for interval in realized_intervals]
    executed=[]
    prefix_stock=[current_stock]
    for t,snapshot in enumerate(forecast_snapshots):
        prepared=_slice_config(basis,t,n)
        prepared["initial_gas_inventory_mwh_lhv"]=current_stock
        prepared["experimental_v098"]={
            **initial,"initial_on":current_on,
            "initial_power_mw_e":current_power,
            "initial_remaining_dwell_hours":current_remaining,
            "terminal_gas_inventory_mwh_lhv":original_target,
            "initial_power_observation_age_hours":0.0 if t==0 else duration[t-1]/2,
        }
        plan=optimize_commitment_milp(prepared,snapshot)
        chosen=plan["hourly"][0]
        spent=duration[t]
        prior_stock=current_stock
        previous_on=current_on
        current_stock=chosen["stock_end_mwh_lhv"]
        current_on=bool(chosen["on"])
        current_power=chosen["power_mw_e"] if current_on else 0.0
        if chosen["startup"] or chosen["shutdown"]:
            dwell=initial["minimum_up_hours"] if current_on else initial["minimum_down_hours"]
            current_remaining=max(0.0,dwell-spent)
        else:
            current_remaining=max(0.0,current_remaining-spent)

        actual_revenue=(chosen["power_mw_e"]*realized_intervals[t].price_eur_per_mwh*spent)
        actual_variable=(chosen["power_mw_e"]*inp.variable_chp_cost_eur_mwh_e[t]*spent)
        actual_aux=(chosen["aux_heat_mw_th"]*inp.backup_cost_eur_mwh_th[t]*spent)
        actual_dump=(chosen["dump_heat_mw_th"]*inp.dump_penalty_eur_mwh_th[t]*spent)
        startup=initial["startup_cost_eur"]*chosen["startup"]
        shutdown=initial["shutdown_cost_eur"]*chosen["shutdown"]
        value=actual_revenue-actual_variable-actual_aux-actual_dump-startup-shutdown
        executed.append({
            **chosen,
            "step":t,
            "forecast_price_eur_mwh":snapshot[0].price_eur_per_mwh,
            "realized_price_eur_mwh":realized_intervals[t].price_eur_per_mwh,
            "stock_start_mwh_lhv":prior_stock,
            "previous_on":bool(previous_on),
            "forecast_plan_value_eur":plan["net_contribution_eur"],
            "forecast_plan_continuous_relaxation_bound_eur":
                plan["same_boundary_LP_relaxation_upper_bound_eur"],
            "realized_step_contribution_eur":value,
            "remaining_initial_dwell_next_step_h":current_remaining,
        })
        prefix_stock.append(current_stock)

    if abs(current_stock-original_target)>1e-6:
        raise DispatchError("Rolling execution violates original terminal gas inventory")
    # Independently reconstruct the COMPLETE realized physical and economic
    # ledger from the actually executed controls, not from forecast plans.
    use=[row["gas_use_mw_lhv"] for row in executed]
    useful=[row["useful_heat_mw_th"] for row in executed]
    auxiliary=[row["aux_heat_mw_th"] for row in executed]
    dump=[row["dump_heat_mw_th"] for row in executed]
    actual_ledger=_ledger(inp,use,prefix_stock,useful,auxiliary,dump)
    _audit_ledger(inp,actual_ledger)
    start_cost=initial["startup_cost_eur"]*sum(row["startup"] for row in executed)
    stop_cost=initial["shutdown_cost_eur"]*sum(row["shutdown"] for row in executed)
    actual_value=actual_ledger["economic_contribution_proxy_eur"]-start_cost-stop_cost
    if abs(actual_value-math.fsum(row["realized_step_contribution_eur"] for row in executed))>COST_TOL:
        raise DispatchError("Rolling realization does not match independently rebuilt ledger")
    states=[int(row["on"]) for row in executed]
    starts=[int(row["startup"]) for row in executed]
    stops=[int(row["shutdown"]) for row in executed]
    power=[row["power_mw_e"] for row in executed]
    operating=_parameters(basis,inp.gas.rating_mw_e)
    operating["rated_power_mw_e"]=inp.gas.rating_mw_e
    violation=_transition_audit(states,starts,stops,power,duration,operating)
    if violation>TOL:
        raise DispatchError("Rolling commitments violated their original dwell or steady-on ramps")
    hindsight=perfect["net_contribution_eur"]
    regret=hindsight-actual_value
    if regret < -COST_TOL:
        raise DispatchError("Realized rolling control beats optimal full-horizon hindsight")
    return {
        "version":"0.9.8","model_type":MODEL,
        "case_id":inp.gas.case_id,
        "scope":("Synthetic price-only rolling forecasts with one-interval execution "
                 "and full remaining-horizon replanning; exact gas and heat assumptions, "
                 "no plant physics, actual forecasts or economic performance validated."),
        "steps_executed":n,
        "rolling_realized_contribution_eur":actual_value,
        "perfect_foresight_net_contribution_eur":hindsight,
        "perfect_foresight_regret_eur":max(0.0,regret),
        "rolling_fixed_reference_feasible":perfect["fixed_reference_feasible"],
        "realized_original_fixed_reference_net_eur":
            perfect["fixed_reference_net_contribution_eur"] if perfect["fixed_reference_feasible"] else None,
        "rolling_gain_over_feasible_fixed_eur":
            actual_value-perfect["fixed_reference_net_contribution_eur"]
            if perfect["fixed_reference_feasible"] else None,
        "original_initial_and_terminal_gas_inventory_mwh_lhv":original_target,
        "terminal_inventory_mwh_lhv":current_stock,
        "total_realized_start_cost_eur":start_cost,
        "total_realized_stop_cost_eur":stop_cost,
        "max_steady_on_ramp_violation_mw_e":violation,
        "realized_physical_and_contribution_ledger":actual_ledger,
        "hourly_executed":executed,
        "solver":"SciPy/HiGHS MILP independently reconstructed actual ledger",
    }
