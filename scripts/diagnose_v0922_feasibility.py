"""Independent v0.9.22 infeasibility taxonomy; no BiogasFlex imports.

For each failed replay, rebuild exactly the *current observed hour* as a
standalone 4-quarter LP. Determine whether it is feasible independently of
the assumed future-hour forecast. Conditional single-family constraint
relaxations are DIAGNOSTICS, never replacement plant physics or dispatch.

This analysis does not authenticate plant gas/heat measurements, quantify
probabilities, or assert a unique root cause when several relaxed LPs pass.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from math import isfinite
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

DT, CAP, ETA_H, ETA_E, BACKUP_CAP, DUMP_CAP = .25, 1.5, .2, .4, .2, .4
RAMP, INIT_STOCK, INIT_POWER = .8, .75, .4
LABEL = "INDEPENDENT_V0922_CAUSAL_FEASIBILITY_DIAGNOSTIC_V1"


def demand(ok, why):
    if not ok:
        raise ValueError("V0922 independent feasibility diagnosis: " + why)


def current_hour_lp(*, on: list[int], prior_on: int, prior_stock: float,
                    prior_power: float, gas: float, heat: float,
                    global_hour_index: int,
                    relax: str = "none") -> bool:
    """Feasibility only, with 20 variables, 12 energy equalities and ramps.

    Relaxations are one-at-a-time classification counterfactuals:
      stock_ceiling: 1.5 MWh bound lifted
      stock_floor: allow unphysical negative energy
      ramps: drop consecutive-ON ramp constraints
      commitment: let CHP fuel burn regardless of frozen binary state
      thermal: increase backup/dump beyond assumed ratings
    """
    demand(len(on) == 4 and all(x in (0, 1) for x in on), "Bad hour commitment")
    demand(prior_on in (0, 1), "Bad previous commitment")
    demand(all(isfinite(x) for x in (prior_stock, prior_power, gas, heat)),
           "Nonfinite physical state")
    demand(-6e-5 <= prior_stock <= CAP + 6e-5,
           f"Invalid carried buffer state: {prior_stock:.12f}")
    # Original independently audited full-day gas-ledger tolerance is 6e-5.
    # Roundoff at a physical zero or ceiling must not be mistaken for a
    # new infeasibility; normalize ONLY values inside this narrow tolerance.
    prior_stock = min(CAP, max(0., prior_stock))
    demand(0 <= gas and 0 <= heat, "Negative gas/heat input")

    n = 4
    u, s, h, a, w = (0, 4, 8, 12, 16)
    nv = 20
    bounds = []
    for t in range(n):
        if relax == "commitment":
            bounds.append((0., 2.))
        else:
            bounds.append((.5, 2.) if on[t] else (0., 0.))
    for t in range(n):
        lo = -50. if relax == "stock_floor" else 0.
        hi = 50. if relax == "stock_ceiling" else CAP
        bounds.append((lo, hi))
    bounds.extend([(0., heat)]*n)
    bounds.extend([(0., 5. if relax == "thermal" else BACKUP_CAP)]*n)
    bounds.extend([(0., 5. if relax == "thermal" else DUMP_CAP)]*n)

    equalities, right, inequalities, ceilings = [], [], [], []
    def v(items):
        row = np.zeros(nv)
        for k, value in items.items():
            row[k] = value
        return row

    for t in range(n):
        balance = {u+t: DT, s+t: 1.}
        if t:
            balance[s+t-1] = -1.
        equalities.append(v(balance))
        right.append(DT*gas + (prior_stock if not t else 0.))
        equalities.append(v({u+t: ETA_H, h+t: -1., w+t: -1.}))
        right.append(0.)
        equalities.append(v({h+t: 1., a+t: 1.}))
        right.append(heat)

        if relax != "ramps" and on[t] == (prior_on if t == 0 else on[t-1]) == 1:
            for sign in (-1., 1.):
                d = {u+t: sign * ETA_E}
                bound = RAMP * (DT/2 if t == 0 and global_hour_index == 0
                                else DT)
                # The half-interval exception is ONLY for initial t=0
                # in the 6-hour replay, not at each replanning hour.
                if t:
                    d[u+t-1] = -sign*ETA_E
                else:
                    bound += sign * prior_power
                inequalities.append(v(d))
                ceilings.append(bound)

    solution = linprog(
        np.zeros(nv), A_eq=np.asarray(equalities), b_eq=right,
        A_ub=np.asarray(inequalities) if inequalities else None,
        b_ub=ceilings if ceilings else None, bounds=bounds, method="highs")
    return bool(solution.success)


def classify(report: dict) -> dict:
    demand(report["protocol"] ==
           "BIOGASFLEX_V0922_HOURLY_CAUSAL_OBSERVATION_15MIN_CHp_REPLAY_RESEARCH_V1",
           "Unrecognized study protocol")
    demand(report["days_evaluated"] == len(report["rows"]),
           "Incomplete study rows")

    first_fail = Counter()
    current_feasibility = Counter()
    causes = Counter()
    same_commitment = 0
    failures = []
    fully_feasible_equal_inventory = 0
    unmatched = 0
    differences = []

    for day in report["rows"]:
        x, y = (day["comparisons"]["nominal"], day["comparisons"]["joint"])
        if x["first_stage_sha256_pre_reveal"] == y["first_stage_sha256_pre_reveal"]:
            same_commitment += 1
        r0 = x["causal_hourly_observation_replay"]
        r1 = y["causal_hourly_observation_replay"]
        if all(item["feasible"] and item["terminal_inventory_matches_initial_for_comparison"]
               for item in (r0, r1)):
            fully_feasible_equal_inventory += 1
            differences.append(r1["economic_contribution_eur"] -
                               r0["economic_contribution_eur"])
        if any(item["feasible"] and not item["terminal_inventory_matches_initial_for_comparison"]
               for item in (r0, r1)):
            unmatched += 1

        for policy_name, comparison in (("nominal", x), ("joint", y)):
            replay = comparison["causal_hourly_observation_replay"]
            if replay["feasible"]:
                continue
            failed_hour = replay["failed_hour"]
            first_fail[str(failed_hour)] += 1
            history = replay["completed_15min_rows"]
            demand(len(history) == failed_hour*4,
                   "Failure prefix must be complete observed hours")
            past = history[-1] if history else None
            stock = past["stock_end_mwh_lhv"] if past else INIT_STOCK
            power = ETA_E*past["gas_use_mw_lhv"] if past else INIT_POWER
            prev_on = past["on"] if past else 1
            obs = replay["hourly_observation_log"][-1]
            demand(obs["hour_index"] == failed_hour, "Wrong hourly observation")
            gas = obs["synthetic_gas_rate_observed_at_hour_start_mw_lhv"]
            heat = obs["synthetic_heat_load_observed_at_hour_start_mw_th"]
            states = comparison["first_stage_on"][failed_hour*4:failed_hour*4+4]
            input_ = dict(on=states, prior_on=prev_on,
                          prior_stock=stock, prior_power=power,
                          gas=gas, heat=heat, global_hour_index=failed_hour)
            # The first 15-min ramp uses half a time interval only at
            # actual global quarter index zero, not at hour index zero
            # whenever initial conditions happen to resemble their defaults.
            feasible_this_hour = current_hour_lp(**input_)
            if feasible_this_hour:
                category = "current_hour_feasible_but_remaining_forecast_plan_infeasible"
                causes[category] += 1
                relaxed = []
            else:
                category = "current_hour_constraints_infeasible"
                causes[category] += 1
                relaxed = [k for k in (
                    "stock_ceiling", "stock_floor", "ramps", "commitment", "thermal")
                    if current_hour_lp(**input_, relax=k)]
                for key in relaxed:
                    causes["single_family_relief_" + key] += 1
                if not relaxed:
                    causes["no_single_family_relief_sufficient"] += 1
            current_feasibility["current_hour_feasible" if feasible_this_hour
                                else "current_hour_infeasible"] += 1
            failures.append({
                "date_utc": day["heldout_day_utc"],
                "policy": policy_name,
                "failed_hour": failed_hour,
                "category": category,
                "single_family_relaxations_restoring_feasibility": relaxed,
                "at_failure_hour_start_stock_mwh": round(stock, 7),
                "frozen_on_pattern_current_hour": states,
                "current_hour_synthetic_gas_mw_lhv": gas,
                "current_hour_synthetic_heat_mw_th": heat,
            })

    demand(fully_feasible_equal_inventory ==
           report["both_policies_feasible_and_terminal_matched_count"],
           "Matched-case count not independently reproduced")
    demand(unmatched == report["one_or_more_replays_terminal_inventory_unmatched_count"],
           "Terminal mismatch count differs")
    demand(len(differences) == len(report["joint_minus_nominal_causal_contribution_eur_paired"]),
           "Missing paired differences")
    for i, diff in enumerate(differences):
        demand(abs(diff-report["joint_minus_nominal_causal_contribution_eur_paired"][i]) < 5e-5,
               "Paired-economic difference altered")
    return {
        "protocol": LABEL,
        "status": "PASS_SEPARATE_INFEASIBILITY_CLASSIFICATION_NOT_REAL_PLANT_VALIDATION",
        "heldout_days_checked": len(report["rows"]),
        "nominal_joint_first_stage_identical_count": same_commitment,
        "matched_feasible_economic_days": fully_feasible_equal_inventory,
        "terminal_inventory_unmatched_days": unmatched,
        "first_failed_hour_policy_count": dict(sorted(first_fail.items())),
        "current_hour_classification_policy_count": dict(current_feasibility),
        "one_at_a_time_counterfactual_relaxation_counts": dict(causes),
        "failed_policy_replays": failures,
        "causal_control_measurements_real": False,
        "site_gas_heat_uncertainty_calibrated": False,
        "unique_root_cause_established_by_one_at_a_time_relaxations": False,
        "no_model_feasibility_relaxation_applied_to_dispatch": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = classify(json.loads(args.study.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n",
                           encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="failed_policy_replays"},
                     indent=2, allow_nan=False))
    for row in result["failed_policy_replays"][:14]:
        print("CLASSIFIED_REPLAY_FAILURE", json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
