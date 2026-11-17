"""v0.9.22 research: information-causal hourly-observation CHP replay.

Reuses v0.9.21 publisher-verified SE3 paired historical errors and the
EXPLICITLY UNCALIBRATED synthetic gas/heat relationships. The historic
source is hourly: each source-hour is held constant over four mathematical
15-minute plant intervals. The controller never observes a future hour's
synthetic gas/heat, and NEVER sees realized electricity price in its LP.
An observed current-hour synthetic rate is assumed available at the hour
start; this is an illustrative sensing assumption, not measured telemetry.

No original as-of-gate forecast vintages, actual market bids, calibrated
biogas plant, 15-minute meter readings or physical reliability are claimed.
The first-stage commitments are frozen before target errors are revealed.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path
from statistics import mean

import numpy as np
from scipy.optimize import linprog

from . import joint_v0921 as j

PROTOCOL = "BIOGASFLEX_V0922_HOURLY_CAUSAL_OBSERVATION_15MIN_CHp_REPLAY_RESEARCH_V1"
TERMINAL_SOFT_PENALTY_EUR_PER_MWH = 50.0


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("v0.9.22 causal replay: " + reason)


def _validate_inputs(nominal: dict, actual: dict, states: list[int]) -> None:
    require(len(states) == j.N and all(x in (0, 1) for x in states),
            "First-stage binary sequence invalid")
    for sc in (nominal, actual):
        for key in ("price_eur_mwh", "synthetic_gas_production_mw_lhv",
                    "synthetic_site_heat_demand_mw_th"):
            vals = sc[key]
            require(len(vals) == j.N and all(math.isfinite(v) for v in vals),
                    "Missing or nonfinite scenario values: " + key)
    require(all(0 <= v <= j.HEAT_BACKUP_CAP for v in actual["synthetic_site_heat_demand_mw_th"]),
            "Unmodelled heat demand exceeds declared backup bound")


def _solve_remaining(hour: int, prior_stock: float, prior_power: float,
                     prior_on: int, states: list[int], nominal: dict,
                     measured_gas: float, measured_heat: float) -> dict:
    """Forecast-only LP, with only the *current* source-hour gas/heat revealed.

    All future hours use the frozen nominal profile; no target future
    measurement and no contemporaneous/future realized price is passed in.
    Terminal stock is a SOFT target, separately reported, not a guarantee.
    """
    first = hour * 4
    count = j.N - first
    u, stock, useful, aux, dump = [k * count for k in range(5)]
    dplus, dminus = 5 * count, 5 * count + 1
    nv = 5 * count + 2
    cost = np.zeros(nv)
    cost[dplus] = cost[dminus] = TERMINAL_SOFT_PENALTY_EUR_PER_MWH
    bounds = [(0., None)] * nv
    equations, rhs, inequalities, upper = [], [], [], []

    def vector(values: dict[int, float]) -> np.ndarray:
        result = np.zeros(nv)
        for ix, val in values.items():
            result[ix] = val
        return result

    for k in range(count):
        t = first + k
        on = states[t]
        current_hour = t // 4 == hour
        g = measured_gas if current_hour else nominal["synthetic_gas_production_mw_lhv"][t]
        h = measured_heat if current_hour else nominal["synthetic_site_heat_demand_mw_th"][t]
        bounds[u+k] = (.5, 2.) if on else (0., 0.)
        bounds[stock+k] = (0., j.STOCK_CAP)
        bounds[useful+k] = (0., h)
        bounds[aux+k] = (0., j.HEAT_BACKUP_CAP)
        bounds[dump+k] = (0., j.HEAT_DUMP_CAP)
        cost[u+k] = -j.ETA_E * (nominal["price_eur_mwh"][t] - j.VAR_COST) * j.DT
        cost[aux+k] = j.AUX_COST * j.DT
        cost[dump+k] = j.DUMP_COST * j.DT

        balance = {u+k: j.DT, stock+k: 1.}
        if k:
            balance[stock+k-1] = -1.
        equations.append(vector(balance))
        rhs.append(g * j.DT + (prior_stock if k == 0 else 0.))
        equations.append(vector({u+k: j.ETA_H, useful+k: -1., dump+k: -1.}))
        rhs.append(0.)
        equations.append(vector({useful+k: 1., aux+k: 1.}))
        rhs.append(h)

        previous = prior_on if k == 0 else states[t-1]
        if on == previous == 1:
            step = j.DT / 2 if t == 0 else j.DT
            for sign in (-1., 1.):
                constraint = {u+k: sign * j.ETA_E}
                limit = j.RAMP * step
                if k == 0:
                    limit += sign * prior_power
                else:
                    constraint[u+k-1] = -sign * j.ETA_E
                inequalities.append(vector(constraint))
                upper.append(limit)

    equations.append(vector({stock+count-1: 1., dplus: -1., dminus: 1.}))
    rhs.append(j.STOCK_INITIAL)
    solution = linprog(
        cost, A_eq=np.asarray(equations), b_eq=rhs,
        A_ub=np.asarray(inequalities) if inequalities else None,
        b_ub=upper if upper else None, bounds=bounds, method="highs")
    if not solution.success:
        return {"feasible": False, "reason": str(solution.message), "steps": None}
    x = solution.x
    steps = []
    for k in range(4):
        steps.append({
            "gas_use_mw_lhv": float(x[u+k]),
            "stock_end_mwh_lhv": float(x[stock+k]),
            "useful_chp_heat_mw_th": float(x[useful+k]),
            "backup_heat_mw_th": float(x[aux+k]),
            "dumped_heat_mw_th": float(x[dump+k]),
        })
    return {"feasible": True, "steps": steps,
            "forecast_terminal_stock_mwh_lhv": float(x[stock+count-1]),
            "forecast_soft_terminal_deviation_mwh_lhv":
                float(x[dplus]+x[dminus])}


def replay_causal(nominal: dict, actual: dict, states: list[int],
                  *, starts: list[int] | None = None,
                  stops: list[int] | None = None) -> dict:
    """Run hourly sense/replan/execute, with fixed ex-ante CHP commitment.

    The realized path is used only (a) for the CURRENT hourly observation
    and (b) for ex-post cashflow; _solve_remaining receives neither the
    full realized path nor the realized source-day electricity prices.
    """
    _validate_inputs(nominal, actual, states)
    require((starts is None) == (stops is None), "Incomplete switch-cost record")
    if starts is None:
        starts, stops = [], []
        old = j.INITIAL_ON
        for on in states:
            starts.append(int(on > old))
            stops.append(int(on < old))
            old = on
    require(len(starts) == len(stops) == j.N, "Invalid switch array length")
    old = j.INITIAL_ON
    for t, on in enumerate(states):
        require(starts[t] == int(on > old) and stops[t] == int(on < old),
                "Switch costs/first-stage commitment inconsistent")
        old = on

    stock = j.STOCK_INITIAL
    previous_power = j.INITIAL_POWER
    previous_on = j.INITIAL_ON
    records, observations = [], []
    for hour in range(j.HOURS):
        t0 = 4 * hour
        # Exactly one hourly observation event. These synthetic plant
        # variables are NOT field measurements and are presumed revealed
        # at hour start solely for the hypothetical controller experiment.
        g = actual["synthetic_gas_production_mw_lhv"][t0]
        heat = actual["synthetic_site_heat_demand_mw_th"][t0]
        decision = _solve_remaining(hour, stock, previous_power, previous_on,
                                    states, nominal, g, heat)
        observations.append({
            "hour_index": hour,
            "revealed_source_hour_utc": 8 + hour,
            "synthetic_gas_rate_observed_at_hour_start_mw_lhv": g,
            "synthetic_heat_load_observed_at_hour_start_mw_th": heat,
            "future_gas_heat_from_frozen_nominal_only": True,
            "realized_price_never_used_for_control": True,
            "forecast_lp_feasible": decision["feasible"],
        })
        if not decision["feasible"]:
            return {
                "feasible": False, "failed_hour": hour,
                "failure_reason": decision["reason"],
                "completed_15min_rows": records,
                "hourly_observation_log": observations,
                "economic_contribution_eur": None,
                "no_unserved_heat_claim": True,
                "actual_terminal_stock_requirement_enforced": False,
            }
        for slot, scheduled in enumerate(decision["steps"]):
            t = t0 + slot
            u = scheduled["gas_use_mw_lhv"]
            stock = stock + j.DT * (g - u)
            require(abs(stock-scheduled["stock_end_mwh_lhv"]) < 2e-5,
                    "Implemented stock disagrees with predicted state")
            row = {
                "quarter_index": t, "hour_index": hour,
                "on": states[t], "start": starts[t], "stop": stops[t],
                "gas_use_mw_lhv": u, "stock_end_mwh_lhv": stock,
                "useful_chp_heat_mw_th": scheduled["useful_chp_heat_mw_th"],
                "backup_heat_mw_th": scheduled["backup_heat_mw_th"],
                "dumped_heat_mw_th": scheduled["dumped_heat_mw_th"],
                "gas_in_mw_lhv": g, "heat_demand_mw_th": heat,
                "realized_price_eur_mwh_EX_POST_ONLY": actual["price_eur_mwh"][t],
                "forecast_price_eur_mwh_used": nominal["price_eur_mwh"][t],
            }
            records.append(row)
            previous_power = u * j.ETA_E
            previous_on = states[t]
    require(len(records) == j.N, "Incomplete simulated six-hour service")
    cash = math.fsum(j.DT * (
        j.ETA_E * r["gas_use_mw_lhv"]
        * (r["realized_price_eur_mwh_EX_POST_ONLY"] - j.VAR_COST)
        - j.AUX_COST * r["backup_heat_mw_th"]
        - j.DUMP_COST * r["dumped_heat_mw_th"]) for r in records)
    switching = j.START_COST * sum(starts) + j.STOP_COST * sum(stops)
    return {
        "feasible": True,
        "economic_contribution_eur": cash-switching,
        "operating_contribution_before_switching_eur": cash,
        "switching_cost_eur": switching,
        "completed_15min_rows": records,
        "hourly_observation_log": observations,
        "terminal_stock_mwh_lhv": stock,
        "terminal_deviation_from_soft_target_mwh_lhv": stock-j.STOCK_INITIAL,
        "terminal_inventory_matches_initial_for_comparison":
            abs(stock-j.STOCK_INITIAL) <= 5e-5,
        "actual_terminal_stock_requirement_enforced": False,
        "perfect_future_information_used_for_dispatch": False,
        "gas_heat_observation_assumed_at_start_of_each_source_hour": True,
    }


def _historical_baseline(day: dict, known_by_day: dict[str, dict]) -> list[float] | None:
    """Get prices from an actual PRIOR calendar day, never target-day p-e."""
    previous = (date.fromisoformat(day["date_utc"]) - timedelta(days=7)).isoformat()
    prior = known_by_day.get(previous)
    if prior is None or prior["date_utc"] >= day["date_utc"]:
        return None
    return prior["delivery_price_eur_mwh"]


def run(source: dict, *, max_days: int | None = None) -> dict:
    train, heldout = j._source_validate(source)
    require(max_days is None or max_days > 0, "max_days must be positive")
    scales = j._standardizers(source)
    historical = {d["date_utc"]: d for d in source["complete_days"]}
    results, excluded = [], []
    eligible = []
    for ordinal, day in enumerate(heldout):
        lag = _historical_baseline(day, historical)
        if lag is None:
            excluded.append({"date_utc": day["date_utc"],
                             "reason": "Exact complete UTC prior-7-day source block absent"})
        else:
            eligible.append((ordinal, day, lag))
    require(eligible, "No heldout dates have an independently prior-day price baseline")
    selected = eligible if max_days is None else eligible[:max_days]
    for ordinal, day, lag in selected:
        nominal = {
            "block_key": "PERSISTENCE_PRICE_UNCALIBRATED_NOMINAL",
            "price_eur_mwh": [float(lag[h]) for h in range(j.HOUR_START, j.HOUR_START+j.HOURS)
                              for _ in range(4)],
            "synthetic_gas_production_mw_lhv": [j.GAS_BASE]*j.N,
            "synthetic_site_heat_demand_mw_th": [j.HEAT_BASE]*j.N,
        }
        training = [j._scenario(train[i], lag, scales,
                                key=f"TRAIN_BLOCK_{i:03d}") for i in j.TRAIN_ORDINALS]
        # Both full first-stage MILPs are solved before revealing this day's
        # paired empirical residuals and derived uncalibrated plant signals.
        nominal_policy = j._milp_bundle([nominal])
        joint_policy = j._milp_bundle(training)
        locks = {
            "nominal": nominal_policy["first_stage_sha256"],
            "joint": joint_policy["first_stage_sha256"],
        }
        actual = j._scenario(day, lag, scales, key="POST_LOCK_HELDOUT")
        comparisons = {}
        for name, policy in (("nominal", nominal_policy), ("joint", joint_policy)):
            states = policy["binary_first_stage_on"]
            simulated = replay_causal(
                nominal, actual, states,
                starts=policy["starts"], stops=policy["stops"])
            # Non-operational clairvoyant bound with the SAME locked binaries;
            # not a free-binary global oracle and not a causal controller.
            hindsight = j._fixed_recourse(actual, states)
            switch = j.START_COST * sum(policy["starts"]) + j.STOP_COST * sum(policy["stops"])
            comparisons[name] = {
                "first_stage_sha256_pre_reveal": locks[name],
                "first_stage_on": states,
                "first_stage_starts": policy["starts"],
                "first_stage_stops": policy["stops"],
                "causal_hourly_observation_replay": simulated,
                "same_binary_full_future_recourse_upper_bound_eur":
                    hindsight["contribution_eur"] - switch if hindsight["feasible"] else None,
                "same_binary_hindsight_feasible": hindsight["feasible"],
            }
            # The hindsight LP imposes exact cyclic terminal stock, whereas
            # causal planning only PENALIZES terminal deviation. A bound
            # comparison is valid only on matched-inventory outcomes.
            if (simulated["feasible"] and hindsight["feasible"] and
                    simulated["terminal_inventory_matches_initial_for_comparison"]):
                require(simulated["economic_contribution_eur"] <=
                        comparisons[name]["same_binary_full_future_recourse_upper_bound_eur"] + 2e-4,
                        "Causal replay exceeds fixed-binary perfect-future information upper bound")
        results.append({
            "heldout_day_utc": day["date_utc"],
            "heldout_ordinal": ordinal,
            "nominal_and_joint_solved_before_heldout_reveal": True,
            "pre_reveal_policy_hashes": locks,
            "comparisons": comparisons,
        })
    paired = [
        row["comparisons"]["joint"]["causal_hourly_observation_replay"]["economic_contribution_eur"]
        - row["comparisons"]["nominal"]["causal_hourly_observation_replay"]["economic_contribution_eur"]
        for row in results
        if all(
            row["comparisons"][strategy]["causal_hourly_observation_replay"]["feasible"]
            and row["comparisons"][strategy]["causal_hourly_observation_replay"]
                ["terminal_inventory_matches_initial_for_comparison"]
            for strategy in ("nominal", "joint"))
    ]
    unmatched_count = sum(
        any(row["comparisons"][strategy]["causal_hourly_observation_replay"]["feasible"]
            and not row["comparisons"][strategy]["causal_hourly_observation_replay"]
                ["terminal_inventory_matches_initial_for_comparison"]
            for strategy in ("nominal", "joint")) for row in results)
    fail_count = sum(any(not row["comparisons"][strategy]
                             ["causal_hourly_observation_replay"]["feasible"]
                         for strategy in ("nominal", "joint")) for row in results)
    return {
        "protocol": PROTOCOL,
        "status": "RESEARCH_REPLAY_NO_SITE_CALIBRATION_NO_GATE_VINTAGE_CERTIFICATION",
        "source_sha256": j.SOURCE_SHA256,
        "available_complete_heldout_days": len(heldout),
        "eligible_days_with_exact_complete_7day_lag": len(eligible),
        "excluded_due_to_missing_prior_complete_day": excluded,
        "days_evaluated": len(results),
        "all_eligible_days_evaluated": max_days is None or len(selected) == len(eligible),
        "study_is_subset_smoke_not_population_evidence": len(selected) != len(eligible),
        "both_policies_feasible_and_terminal_matched_count": len(paired),
        "one_or_more_causal_replays_infeasible_count": fail_count,
        "one_or_more_replays_terminal_inventory_unmatched_count": unmatched_count,
        "paired_economic_comparison_only_if_both_causal_replays_feasible_and_terminal_stock_matched": True,
        "joint_minus_nominal_causal_contribution_eur_paired": paired,
        "paired_average_difference_eur_descriptive_not_confidence_interval":
            mean(paired) if paired else None,
        "failure_is_never_imputed_as_zero_cashflow": True,
        "source_hourly_not_quarter_hourly": True,
        "gas_and_heat_couplings_empirically_calibrated": False,
        "original_price_forecast_vintages_verified": False,
        "price_persistence_historical_only": True,
        "real_traded_awards_enforced": False,
        "dynamic_engine_and_buffer_pressure_calibrated": False,
        "forecast_assumption": "7day-lagged prices; nominal future gas/heat; current hour synthetic gas/heat assumed observable at hour start",
        "rows": results,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True,
                   help="Original SHA-verified v0.9.21 SE3 source report, outside checkout")
    p.add_argument("--output", type=Path, required=True,
                   help="Write reproducible report OUTSIDE git checkout")
    p.add_argument("--max-days", type=int, default=None,
                   help="First N chronologically eligible days (smoke only; default all)")
    opts = p.parse_args()
    source = json.loads(opts.source.read_text(encoding="utf8"))
    outcome = run(source, max_days=opts.max_days)
    j.write_out(outcome, opts.output)
    print(json.dumps({k: v for k, v in outcome.items() if k not in (
        "rows", "joint_minus_nominal_causal_contribution_eur_paired",
        "excluded_due_to_missing_prior_complete_day")}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
