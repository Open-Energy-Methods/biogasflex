"""Deterministic synthetic CHP dispatch stress suite for BiogasFlex v0.9.3.

Compare the inherited SciPy/HiGHS heat-dispatch LP against a solver-free,
exact two-interval piecewise-linear oracle. Check mathematically required
metamorphic relationships, not empirical model accuracy. No input/output
research files are changed, and the benchmark grid is NOT an observed sample.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from biogasflex.baseline import Interval
from biogasflex.heat_dispatch import optimize_heat_dispatch
from oracle_v093_two_interval import verify_two_interval

SEED = 20261105
CASES = 96
EUR_TOL = 2e-6


def synthetic_case(rng: random.Random, index: int):
    """Return an explicitly hypothetical two-interval dispatch experiment."""
    dt0, dt1 = rng.choice(((1.0, 1.0), (0.5, 1.5), (0.25, 1.75)))
    prices = (float(rng.randint(-100, 180)), float(rng.randint(-100, 180)))
    capacity = rng.choice((0.0, 0.05, 0.2, 0.45, 0.8))
    gas_source = rng.choice(((0.6, 0.6), (0.5, 0.8), (0.35, 0.7)))
    flaring = rng.choice((0.0, 0.02))
    heat_demand = rng.choice(((0.27, 0.27), (0.15, 0.35), (0.55, 0.10)))
    eta_h = rng.choice((0.0, 0.3, 0.45, 0.5))
    initial = capacity * rng.choice((0.0, 0.25, 0.5))
    config = {
        "case_id": f"v093_synthetic_{index:03d}",
        "price_zone": "SE3",
        "electric_rating_mw": 0.55,
        "gas_input_mw_lhv": 0.6,
        "gas_production_mw_lhv": list(gas_source),
        "fixed_flaring_mw_lhv": flaring,
        "fixed_losses_mw_lhv": 0.01,
        "electric_efficiency_lhv": 0.4,
        "thermal_efficiency_lhv": eta_h,
        "gas_storage_capacity_mwh_lhv": capacity,
        "initial_gas_inventory_mwh_lhv": initial,
        "heat_service_model": "instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th": list(heat_demand),
        "aux_heat_capacity_mw_th": 0.7,
        "heat_dump_capacity_mw_th": 0.9,
        "aux_heat_cost_eur_per_mwh_th": rng.choice((0.0, 5.0, 20.0, 80.0, 200.0)),
        "heat_dump_penalty_eur_per_mwh_th": rng.choice((0.0, 2.0, 20.0)),
        "chp_variable_cost_eur_per_mwh_e": list(
            rng.choice(((0.0, 0.0), (0.0, 8.0), (5.0, 15.0)))
        ),
    }
    return config, ((prices[0], dt0), (prices[1], dt1))


def _intervals(pairs):
    start = datetime(2020, 1, 1, 0, tzinfo=timezone.utc)
    result = []
    for price, duration in pairs:
        result.append(Interval(start, price, duration, "SE3"))
        start += timedelta(hours=duration)
    return result


def _equal(actual, expected, label, tol=EUR_TOL):
    if not (math.isfinite(actual) and math.isfinite(expected)
            and abs(actual-expected) <= tol):
        raise AssertionError(f"{label}: actual={actual!r}, expected={expected!r}")


def compare_solvers(config, pairs):
    analytical = verify_two_interval(config, pairs)
    solved = optimize_heat_dispatch(config, _intervals(pairs))
    _equal(solved["optimized_dispatch"]["economic_contribution_proxy_eur"],
           analytical["optimized_contribution_eur"], "optimal contribution")
    _equal(solved["fixed_dispatch"]["economic_contribution_proxy_eur"],
           analytical["fixed_contribution_eur"], "fixed comparator contribution")
    _equal(solved["incremental_economic_contribution_proxy_eur"],
           analytical["incremental_contribution_eur"], "incremental contribution")
    return analytical, solved


def run(*, count=CASES, seed=SEED):
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("count must be a positive integer")
    rng = random.Random(seed)
    max_diff = 0.0
    translations = 0
    marginal_cost_shifts = 0
    storage_monotonic_chains = 0
    zero_buffer_cases = 0
    for i in range(count):
        config, pairs = synthetic_case(rng, i)
        oracle, solved = compare_solvers(config, pairs)
        value = solved["optimized_dispatch"]["economic_contribution_proxy_eur"]
        max_diff = max(max_diff, abs(value-oracle["optimized_contribution_eur"]))
        if config["gas_storage_capacity_mwh_lhv"] == 0:
            zero_buffer_cases += 1
            _equal(oracle["incremental_contribution_eur"], 0.0,
                   "zero buffer cannot retime fuel")
        if i % 4 == 0:
            shift = rng.choice((-130.0, 75.0, 210.0))
            moved = tuple((price+shift, hours) for price, hours in pairs)
            _, shifted = compare_solvers(config, moved)
            _equal(shifted["incremental_economic_contribution_proxy_eur"],
                   solved["incremental_economic_contribution_proxy_eur"],
                   "uniform spot-price shift should cancel in incremental value")
            gas_energy = math.fsum(
                (config["gas_production_mw_lhv"][t]
                 - config["fixed_flaring_mw_lhv"]
                 - config["fixed_losses_mw_lhv"]) * pairs[t][1]
                for t in range(2)
            )
            _equal(
                shifted["optimized_dispatch"]["economic_contribution_proxy_eur"]-value,
                shift * config["electric_efficiency_lhv"] * gas_energy,
                "absolute price-translation energy identity",
            )
            translations += 1
        if i % 4 == 1:
            raised = dict(config)
            costs = config["chp_variable_cost_eur_per_mwh_e"]
            raised["chp_variable_cost_eur_per_mwh_e"] = [c + 17.0 for c in costs]
            _, changed = compare_solvers(raised, pairs)
            _equal(changed["incremental_economic_contribution_proxy_eur"],
                   solved["incremental_economic_contribution_proxy_eur"],
                   "uniform CHP variable cost should cancel in incremental value")
            marginal_cost_shifts += 1
        if i % 8 == 0:
            original = dict(config)
            original["initial_gas_inventory_mwh_lhv"] = 0.0
            values = []
            for storage in (0.0, 0.1, 0.3, 0.8):
                cfg = dict(original, gas_storage_capacity_mwh_lhv=storage)
                optimum, numerical = compare_solvers(cfg, pairs)
                values.append(numerical["optimized_dispatch"]["economic_contribution_proxy_eur"])
            if any(b < a-EUR_TOL for a,b in zip(values, values[1:])):
                raise AssertionError("More gas buffer lowered the feasible optimum")
            storage_monotonic_chains += 1
    return {
        "status": "PASS",
        "version": "0.9.3",
        "seed": seed,
        "synthetic_oracle_comparisons": count,
        "price_translation_checks": translations,
        "variable_cost_shift_checks": marginal_cost_shifts,
        "capacity_monotonicity_chains": storage_monotonic_chains,
        "zero_buffer_tests": zero_buffer_cases,
        "max_abs_optimized_objective_disagreement_eur": max_diff,
        "test_scope": "synthetic two-interval constraints; no observed plant or probabilistic inference",
        "oracle_independence": "standard-library analytical breakpoint enumeration, no solver import",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=CASES)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    try:
        print(json.dumps(run(count=args.count, seed=args.seed), indent=2, allow_nan=False))
    except (ValueError, AssertionError, RuntimeError) as exc:
        parser.exit(1, f"v0.9.3 SYNTHETIC STRESS FAILED: {exc}\n")
