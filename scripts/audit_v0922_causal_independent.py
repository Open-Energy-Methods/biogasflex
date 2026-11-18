"""Independent standard-library v0.9.22 audit. Imports NO BiogasFlex code.

This verifies externally reported source chronology, first-stage SHA locks,
separate hourly gas/heat assumption reconstruction, every executed 15-min
gas/electric/thermal/stock/ramp ledger and matched-inventory comparison.
It cannot prove internal nonanticipativity merely from a final JSON: that
property additionally requires adversarial frozen-prefix regression tests.
Neither script authenticates a site meter or market gate forecast vintage.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path

SRC_SHA = "6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"
PROTOCOL = "BIOGASFLEX_V0922_HOURLY_CAUSAL_OBSERVATION_15MIN_CHp_REPLAY_RESEARCH_V1"
DT = .25
CAP = 1.5
ETA_E, ETA_H = .4, .2
INITIAL_STOCK = .75
INITIAL_POWER = .4
RAMP, RATE_MIN, RATE_MAX = .8, .5, 2.
START_COST, STOP_COST = 5., 1.
AUX_COST, DUMP_COST, VAR_COST = 6., 1., .75
TOL = 6e-5


def check(condition, message):
    if not condition:
        raise AssertionError("INDEPENDENT_V0922: " + message)


def close(a, b, desc, tol=TOL):
    check(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= tol,
          f"{desc}: {a!r} != {b!r}")


def clip(x, low, high):
    return max(low, min(high, x))


def projected_hour(source, target, hour):
    stats = source["training_metrics"]
    pe = target["price_baseline_error_eur_mwh"][hour]
    le = target["regional_load_error_relative"][hour]
    mp = stats["price_lag_7day_baseline_mean_error_eur_mwh"]
    ml = stats["published_TSO_load_forecast_mean_relative_error"]
    sp = math.sqrt(max(0., stats["price_lag_7day_baseline_RMSE_eur_mwh"]**2 - mp**2))
    sl = math.sqrt(max(0., stats["published_TSO_load_forecast_RMSE_relative"]**2 - ml**2))
    zp = clip((pe-mp)/sp, -2.5, 2.5)
    zl = clip((le-ml)/sl, -2.5, 2.5)
    return (round(clip(1.0*(1+.08*zp-.06*zl), .78, 1.22), 8),
            round(clip(.15*(1+.10*zl+.03*zp), .105, .195), 8))


def audit(source, report):
    check(source["source"]["sha256"] == SRC_SHA, "Wrong source SHA")
    check(source["source"]["electricity_price_original_forecast_column_available"] is False,
          "Historical price prediction source falsely attested")
    check(source["source"]["gas_production_or_heat_load_site_measurement_present"] is False,
          "Plant telemetry falsely attested")
    check(report["protocol"] == PROTOCOL, "Wrong study protocol")
    check(report["source_sha256"] == SRC_SHA, "Report original source digest mismatch")
    check(report["gas_and_heat_couplings_empirically_calibrated"] is False,
          "Assumed heat/gas falsely called calibrated")
    check(report["original_price_forecast_vintages_verified"] is False,
          "Original price forecast vintage falsely attested")
    check(report["real_traded_awards_enforced"] is False,
          "Accepted awards falsely claimed")
    all_days = source["complete_days"]
    by_day = {d["date_utc"]: d for d in all_days}
    check(len(all_days) == len(by_day), "Duplicated source UTC dates")
    targets = [d for d in all_days
               if d["partition"] == "HOLDOUT_FROM_2019_10_01"]
    check(len(targets) == report["available_complete_heldout_days"],
          "Holdout total changed")
    eligible, excluded = [], []
    for day in targets:
        previous = (date.fromisoformat(day["date_utc"]) -
                    timedelta(days=7)).isoformat()
        if previous in by_day:
            eligible.append(day["date_utc"])
        else:
            excluded.append(day["date_utc"])
    check(report["eligible_days_with_exact_complete_7day_lag"] == len(eligible),
          "Eligibility denominator forged")
    check([d["date_utc"] for d in report["excluded_due_to_missing_prior_complete_day"]]
          == excluded, "Source exclusion set changed")
    rows = report["rows"]
    check(len(rows) == report["days_evaluated"], "Row count inconsistent")
    check([r["heldout_day_utc"] for r in rows] == eligible[:len(rows)],
          "Future date lookahead, skipped day or cherry-picked target")
    check(report["all_eligible_days_evaluated"] == (len(rows) == len(eligible)),
          "Complete-backtest flag wrong")
    paired = []
    failures, unmatched = 0, 0
    for case in rows:
        d = case["heldout_day_utc"]
        target = by_day[d]
        lag_date = (date.fromisoformat(d) - timedelta(days=7)).isoformat()
        lag = by_day[lag_date]
        check(case["nominal_and_joint_solved_before_heldout_reveal"] is True,
              "Pre-reveal ordering not declared")
        feasibility = {}
        matched = {}
        cash = {}
        for label in ("nominal", "joint"):
            entry = case["comparisons"][label]
            states, starts, stops = (entry["first_stage_on"],
                                   entry["first_stage_starts"],
                                   entry["first_stage_stops"])
            check(len(states) == len(starts) == len(stops) == 24,
                  "Commitment horizon invalid")
            check(all(v in (0, 1) for v in states+starts+stops),
                  "Nonbinary first-stage decision")
            checksum = sha256(json.dumps([states, starts, stops],
                              separators=(",", ":")).encode("utf8")).hexdigest()
            check(checksum == entry["first_stage_sha256_pre_reveal"] ==
                  case["pre_reveal_policy_hashes"][label],
                  "First-stage policy SHA failed")
            past_on = 1
            for t in range(24):
                check(starts[t] == int(states[t] > past_on) and
                      stops[t] == int(states[t] < past_on),
                      "First-stage transitions inconsistent")
                past_on = states[t]
            replay = entry["causal_hourly_observation_replay"]
            check(len(replay["hourly_observation_log"]) <= 6,
                  "Impossible number of hourly observation events")
            for h, log in enumerate(replay["hourly_observation_log"]):
                g, heat = projected_hour(source, target, 8+h)
                check(log["hour_index"] == h and
                      log["revealed_source_hour_utc"] == 8+h,
                      "Invalid source observation chronology")
                close(log["synthetic_gas_rate_observed_at_hour_start_mw_lhv"],
                      g, "Current-hour gas")
                close(log["synthetic_heat_load_observed_at_hour_start_mw_th"],
                      heat, "Current-hour heat")
                check(log["realized_price_never_used_for_control"] is True and
                      log["future_gas_heat_from_frozen_nominal_only"] is True,
                      "Future-information claim missing")
            produced = replay["completed_15min_rows"]
            check(len(produced) <= 24 and len(produced) % 4 == 0,
                  "Only full source hours may be accepted")
            stock = INITIAL_STOCK
            previous_power = INITIAL_POWER
            old = 1
            earning = 0.
            for t, row in enumerate(produced):
                h = 8 + t//4
                gas, heat = projected_hour(source, target, h)
                check(row["quarter_index"] == t and row["hour_index"] == t//4,
                      "Quarter-hour output chronology forged")
                check((row["on"], row["start"], row["stop"]) ==
                      (states[t], starts[t], stops[t]), "Frozen binary modified")
                close(row["gas_in_mw_lhv"], gas, "Projected gas")
                close(row["heat_demand_mw_th"], heat, "Projected heat")
                close(row["forecast_price_eur_mwh_used"],
                      lag["delivery_price_eur_mwh"][h], "Prior-week price baseline")
                close(row["realized_price_eur_mwh_EX_POST_ONLY"],
                      target["delivery_price_eur_mwh"][h], "Ex-post price")
                u = row["gas_use_mw_lhv"]
                check((-TOL <= u <= RATE_MAX+TOL) and
                      (RATE_MIN-TOL <= u if states[t] else u <= TOL),
                      "Generator rating or minimum output")
                stock += DT*(gas-u)
                close(stock, row["stock_end_mwh_lhv"], "Stock conservation")
                check(-TOL <= stock <= CAP+TOL, "Fuel buffer limit")
                useful, aux, dump = (row["useful_chp_heat_mw_th"],
                                     row["backup_heat_mw_th"],
                                     row["dumped_heat_mw_th"])
                close(useful+aux, heat, "Heat service")
                close(useful+dump, ETA_H*u, "Heat allocation")
                check(-TOL <= aux <= .20+TOL and -TOL <= dump <= .40+TOL
                      and useful >= -TOL, "Heat backup or dump limit")
                power = ETA_E*u
                if old == states[t] == 1:
                    width = DT/2 if t == 0 else DT
                    check(abs(power-previous_power) <= RAMP*width+TOL,
                          "Midpoint ramp violation")
                previous_power, old = power, states[t]
                earning += DT*(power*(
                    target["delivery_price_eur_mwh"][h]-VAR_COST)
                    -AUX_COST*aux-DUMP_COST*dump)
            feasibility[label] = replay["feasible"]
            if replay["feasible"]:
                check(len(produced) == 24, "Success claimed with incomplete service")
                expected_switch = START_COST*sum(starts) + STOP_COST*sum(stops)
                close(replay["switching_cost_eur"], expected_switch, "Switch cost")
                close(replay["operating_contribution_before_switching_eur"],
                      earning, "Ex-post operating cashflow")
                close(replay["economic_contribution_eur"],
                      earning - expected_switch, "Ex-post total cashflow")
                close(replay["terminal_stock_mwh_lhv"], stock, "Terminal stock")
                matched[label] = abs(stock - INITIAL_STOCK) <= 5e-5
                check(replay["terminal_inventory_matches_initial_for_comparison"]
                      == matched[label], "Matched terminal indicator forged")
                cash[label] = replay["economic_contribution_eur"]
                if matched[label] and entry["same_binary_hindsight_feasible"]:
                    check(cash[label] <=
                          entry["same_binary_full_future_recourse_upper_bound_eur"]+2e-4,
                          "Causal outcome above equal-commitment hindsight bound")
            else:
                check(replay["economic_contribution_eur"] is None,
                      "Incomplete service falsely counted as earnings")
                check("failure_reason" in replay, "Missing explicit failure")
                matched[label] = False
        if not all(feasibility.values()):
            failures += 1
        if any(feasibility[k] and not matched[k] for k in ("nominal", "joint")):
            unmatched += 1
        if all(matched.values()):
            paired.append(cash["joint"]-cash["nominal"])
    check(failures == report["one_or_more_causal_replays_infeasible_count"],
          "Infeasibility count mismatch")
    check(unmatched == report["one_or_more_replays_terminal_inventory_unmatched_count"],
          "Non-matched service count mismatch")
    check(len(paired) == report["both_policies_feasible_and_terminal_matched_count"],
          "Matched-service paired count mismatch")
    observed = report["joint_minus_nominal_causal_contribution_eur_paired"]
    check(len(observed) == len(paired), "Paired differences count mismatch")
    for computed, stated in zip(paired, observed):
        close(computed, stated, "Matched-service economic difference")
    if paired:
        close(math.fsum(paired)/len(paired),
              report["paired_average_difference_eur_descriptive_not_confidence_interval"],
              "Paired descriptive mean")
    else:
        check(report["paired_average_difference_eur_descriptive_not_confidence_interval"]
              is None, "Fabricated mean with no matched-service pairs")
    return {
        "status": "PASS_INDEPENDENT_V0922_CHRONOLOGY_ENERGY_CASH_FIRST_STAGE_SHA",
        "audited_days": len(rows),
        "all_eligible_heldout_days_replayed": len(rows) == len(eligible),
        "matched_service_paired_cases": len(paired),
        "infeasible_causal_replays_days": failures,
        "terminal_inventory_unmatched_days": unmatched,
        "real_site_validation": False,
        "historical_as_of_gate_vintage_verified": False,
        "no_lookahead_proven_from_output_alone": False,
        "separate_prefix_invariance_regression_tests_required": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--study", type=Path, required=True)
    p.add_argument("--output", type=Path, required=False)
    args = p.parse_args()
    result = audit(json.loads(args.source.read_text(encoding="utf8")),
                   json.loads(args.study.read_text(encoding="utf8")))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
