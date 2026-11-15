"""Predeclared hypothetical 2-hour CHP contract sensitivity and identifiability.

Only the frozen fictional v0.9.11 case is evaluated. The source-reviewed
v0.9.14-A manufacturer register is audited but NEVER copied into the MILP.
Discrete factorial summaries are design arithmetic, not probabilities.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

from .baseline import Interval
from .chp_parameter_evidence import run_register
from .dispatch import DispatchError
from .experimental_v098 import optimize_commitment_milp

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "examples/v0914b_hypothetical_sensitivity.json"
PROTOCOL = "BIOGASFLEX_V0914B_HYPOTHETICAL_FACTORIAL_V1"
EVIDENCE = "EXPLICITLY_HYPOTHETICAL_NOT_MANUFACTURER_SPECIFIED_OR_CALIBRATED"
ORDER = (
    "gas_storage_capacity_mwh_lhv",
    "experimental_v098.ramp_up_mw_e_per_hour",
    "experimental_v098.minimum_on_power_mw_e",
    "aux_heat_capacity_mw_th",
)
OAT_ORDER = (
    "electric_efficiency_lhv",
    "thermal_efficiency_lhv",
    "experimental_v098.ramp_down_mw_e_per_hour",
)
LEVELS = (
    (0.4, 0.5, 0.7),
    (0.3, 0.4, 0.8),
    (0.15, 0.2, 0.25),
    (0.03, 0.05, 0.10),
)
OAT_LEVELS = (
    (0.38, 0.4, 0.42),
    (0.15, 0.2, 0.25),
    (0.25, 0.4, 0.6),
)
REFERENCE = (0.5, 0.8, 0.15, 0.05)
PINS = {
    "reference_contract_manifest": (
        "examples/v0911_contract_hourly.json",
        "1ced01d0e97b0a76a0ac9f7442419fb577b20fb1056dcd6a7abda1e3441505c4",
        "contract_manifest_sha256",
    ),
    "reference_chp_config": (
        "examples/v0911_synthetic_chp.json",
        "637c95d5e5db7e88acade3e063d9582fffa291e2f4541ec3a2f6d5f5e2fa3b29",
        "chp_config_sha256",
    ),
    "source_evidence_register": (
        "data/evidence/v0914_chp_parameter_register.json",
        "03d1e141e33ca820878772d377234400eab7fab18825305e1dec2ae878b56823",
        "source_evidence_sha256",
    ),
}
TOL = 1e-8


class SensitivityError(ValueError):
    """Violation of the predeclared case or solver-independent verification."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SensitivityError(message)


def _finite_positive(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _set(config: dict, key: str, value: float) -> None:
    if key.startswith("experimental_v098."):
        config["experimental_v098"][key.split(".", 1)[1]] = value
    else:
        config[key] = value


def _num(row: dict, key: str) -> float:
    value = row["experimental_v098"][key.split(".", 1)[1]] if "." in key else row[key]
    _require(type(value) in (int, float) and math.isfinite(value),
             f"Invalid numeric assumption {key}")
    return float(value)


def _require_levels(raw: list, names: tuple, levels: tuple) -> None:
    _require(type(raw) is list and len(raw) == len(names), "Unapproved factorial design")
    for item, name, expected in zip(raw, names, levels):
        _require(type(item) is dict and set(item) == {
            "name", "levels", "unit", "source", "interpretation"
        }, f"{name}: missing parameter provenance")
        _require(
            item["name"] == name and item["source"] == "HYPOTHETICAL_RANGE"
            and type(item["unit"]) is str and bool(item["unit"])
            and type(item["interpretation"]) is str and len(item["interpretation"]) >= 15,
            f"{name}: unauthorized operating assumption",
        )
        _require(
            type(item["levels"]) is list
            and len(item["levels"]) == len(expected)
            and all(_finite_positive(x) for x in item["levels"])
            and tuple(item["levels"]) == expected,
            f"{name}: range changed from predeclared levels",
        )


def _box_expected() -> tuple[dict, dict]:
    wide = {
        ORDER[0]: [0.4, 0.7], ORDER[1]: [0.3, 0.8],
        ORDER[2]: [0.15, 0.25], ORDER[3]: [0.03, 0.10],
    }
    restricted = {
        ORDER[0]: [0.5, 0.7], ORDER[1]: [0.4, 0.8],
        ORDER[2]: [0.15, 0.2], ORDER[3]: [0.05, 0.10],
    }
    return wide, restricted


def _validate(manifest: dict) -> tuple[dict, list[Interval], list[float], list[float]]:
    _require(type(manifest) is dict and set(manifest) == {
        "protocol", "scenario_id", "effective_date", "evidence_class",
        "experimental_design", "reference_contract_manifest",
        "contract_manifest_sha256", "reference_chp_config", "chp_config_sha256",
        "source_evidence_register", "source_evidence_sha256",
        "varied_parameters", "one_at_a_time", "one_at_a_time_reference",
        "continuous_rectangles", "out_of_scope",
    }, "Unexpected sensitivity design keys")
    _require(
        manifest["protocol"] == PROTOCOL
        and manifest["scenario_id"] == "v0914b_fully_synthetic_two_hour_awarded_chp"
        and manifest["effective_date"] == "2026-11-15"
        and manifest["evidence_class"] == EVIDENCE
        and manifest["experimental_design"] == "EXHAUSTIVE_DISCRETE_CARTESIAN_3_LEVEL_4_FACTOR",
        "Unreviewed scenario, provenance or experiment design",
    )
    _require_levels(manifest["varied_parameters"], ORDER, LEVELS)
    _require_levels(manifest["one_at_a_time"], OAT_ORDER, OAT_LEVELS)
    reference = manifest["one_at_a_time_reference"]
    _require(type(reference) is dict and list(reference) == list(ORDER)
             and tuple(reference.values()) == REFERENCE,
             "OAT reference must remain the declared feasible corner")
    boxes = manifest["continuous_rectangles"]
    expected = _box_expected()
    _require(type(boxes) is list and len(boxes) == 2, "Expected two predeclared boxes")
    for i, (entry, bounds) in enumerate(zip(boxes, expected)):
        _require(
            type(entry) is dict and set(entry) == {"id", "bounds"}
            and entry["id"] == (
                "wide_hypothetical_box_expected_not_robust" if i == 0
                else "restricted_hypothetical_box_analytic_robust_for_this_2slot_model"
            )
            and entry["bounds"] == bounds,
            "Predeclared continuous rectangle has changed",
        )
    _require(type(manifest["out_of_scope"]) is list
             and len(manifest["out_of_scope"]) >= 7
             and all(type(s) is str and len(s) >= 15 for s in manifest["out_of_scope"]),
             "Missing scientific exclusions")
    loaded = {}
    for key, (relative, digest, hash_field) in PINS.items():
        _require(manifest[key] == relative and manifest[hash_field] == digest,
                 f"{key}: reference path or hash changed")
        path = ROOT / relative
        _require(path.is_file() and sha256(path.read_bytes()).hexdigest() == digest,
                 f"{key}: pinned original evidence/source file changed")
        loaded[key] = json.loads(path.read_text(encoding="utf8"))
    # This guard audits equipment identity separately; no manufacturer values
    # become synthetic engine configuration or uncertainty bounds.
    evidence_report = run_register(ROOT / PINS["source_evidence_register"][0])
    _require(evidence_report["unidentified_count"] == 14
             and not evidence_report["auto_import_into_dispatch"],
             "Source register cannot support calibrated dynamic parameters")
    cm = loaded["reference_contract_manifest"]
    cfg = loaded["reference_chp_config"]
    _require(cm["synthetic_chp_config"] == "v0911_synthetic_chp.json"
             and cm["model"] == "exogenous_award_hard_delivery_milp_v0911"
             and len(cm["delivery_slots"]) == 2
             and len(cm["exogenous_award"]["accepted_mwh"]) == 2
             and cfg["case_id"] == "v0911_EXPLICITLY_SYNTHETIC_CONTRACTED_CHP_WITH_STORAGE",
             "Only the explicitly frozen two-hour fictional award is admissible")
    _require(cfg["experimental_v098"]["initial_on"] is True
             and cfg["experimental_v098"]["initial_remaining_dwell_hours"] == 0
             and cfg["experimental_v098"]["minimum_up_hours"] <= 1
             and cfg["experimental_v098"]["minimum_down_hours"] <= 1
             and cfg["experimental_v098"]["terminal_gas_inventory_mwh_lhv"] == 0
             and cfg["fixed_flaring_mw_lhv"] == 0
             and cfg["fixed_losses_mw_lhv"] == 0,
             "Analytical witness assumes always-on, fixed zero flaring/loss/terminal stock")
    zone = cm["market"]["bidding_zone"]
    slots = cm["delivery_slots"]
    prices = cm["exogenous_award"]["clearing_prices_eur_mwh"]
    accepted = cm["exogenous_award"]["accepted_mwh"]
    _require(accepted == [0.2, 0.6] and prices == [100, 0]
             and [r["duration_hours"] for r in slots] == [1, 1],
             "Pinned synthetic price/award/duration contract changed")
    intervals = [
        Interval(datetime.fromisoformat(slot["start_utc"]), float(price),
                 float(slot["duration_hours"]), zone)
        for slot, price in zip(slots, prices)
    ]
    return cfg, intervals, list(accepted), prices


def forced_physical_oracle(config: dict, awards: list[float],
                           hours: list[float]) -> dict:
    """Independent algebraic *two-slot model* witness, no SciPy/HiGHS.

    Positive awards force both on. Solves hard electrical equalities
    analytically, then checks the exact gas, thermal, nameplate, midpoint-ramp
    and minimum-on feasibility requirements for the fixed 2h toy model.
    Does NOT cover general engine transients, arbitrary MILPs or real plants.
    """
    _require(len(awards) == len(hours) == 2 and all(a > 0 for a in awards)
             and all(h > 0 for h in hours), "Oracle limited to two positive-award slots")
    _require(config["experimental_v098"]["initial_on"] is True,
             "Oracle assumes a previously running CHP")
    eta = _num(config, "electric_efficiency_lhv")
    eta_th = _num(config, "thermal_efficiency_lhv")
    power = [a / h for a, h in zip(awards, hours)]
    fuel = [p / eta for p in power]
    inflow = _num(config, "gas_input_mw_lhv")
    flare = _num(config, "fixed_flaring_mw_lhv")
    losses = _num(config, "fixed_losses_mw_lhv")
    stock = [_num(config, "initial_gas_inventory_mwh_lhv")]
    for u, h in zip(fuel, hours):
        stock.append(stock[-1] + (inflow - flare - losses - u) * h)
    storage = _num(config, "gas_storage_capacity_mwh_lhv")
    minp = _num(config, "experimental_v098.minimum_on_power_mw_e")
    rating = _num(config, "electric_rating_mw")
    ramp_up = _num(config, "experimental_v098.ramp_up_mw_e_per_hour")
    ramp_down = _num(config, "experimental_v098.ramp_down_mw_e_per_hour")
    initial_power = _num(config, "experimental_v098.initial_power_mw_e")
    age = _num(config, "experimental_v098.initial_power_observation_age_hours")
    elapsed = [age + 0.5*hours[0], 0.5*(hours[0]+hours[1])]
    prev = [initial_power, power[0]]
    demand = _num(config, "heat_demand_mw_th")
    aux = _num(config, "aux_heat_capacity_mw_th")
    dump_cap = _num(config, "heat_dump_capacity_mw_th")
    heat = [eta_th * u for u in fuel]
    backup = [max(0.0, demand-q) for q in heat]
    dump = [max(0.0, q-demand) for q in heat]
    reasons = []
    if any(s < -TOL or s > storage+TOL for s in stock):
        reasons.append("GAS_STORAGE_STOCK")
    if abs(stock[-1]-_num(config, "experimental_v098.terminal_gas_inventory_mwh_lhv")) > TOL:
        reasons.append("GAS_TERMINAL_EQUALITY")
    if any(p > rating+TOL for p in power):
        reasons.append("ELECTRIC_RATING")
    if any(p < minp-TOL for p in power):
        reasons.append("MINIMUM_ON_POWER")
    if any(p - old > ramp_up*dt+TOL for p, old,dt in zip(power,prev,elapsed)):
        reasons.append("RAMP_UP")
    if any(old-p > ramp_down*dt+TOL for p, old,dt in zip(power,prev,elapsed)):
        reasons.append("RAMP_DOWN")
    if any(q > aux+TOL for q in backup):
        reasons.append("BACKUP_HEAT_CAPACITY")
    if any(q > dump_cap+TOL for q in dump):
        reasons.append("HEAT_DUMP_CAPACITY")
    return {
        "feasible": not reasons,
        "reasons": reasons,
        "forced_power_mw_e": power,
        "forced_gas_fuel_mw_lhv": fuel,
        "end_stock_mwh_lhv": stock[1:],
        "needed_backup_heat_mw_th": backup,
        "needed_heat_dump_mw_th": dump,
        "contract_mwh": awards,
    }


def _evaluate(config: dict, intervals: list[Interval],
              awards: list[float], label: str, parameters: dict) -> dict:
    hours = [r.hours for r in intervals]
    oracle = forced_physical_oracle(config, awards, hours)
    try:
        solution = optimize_commitment_milp(
            config, intervals, contracted_delivery_mwh=awards
        )
    except DispatchError as exc:
        # A numerical or audit failure may NOT be silently declared as
        # physical infeasibility, even if our independent witness rejects.
        if "MILP infeasible or not optimal: 2:" not in str(exc):
            raise SensitivityError(f"{label}: unexpected solver failure: {exc}") from exc
        feasible = False
        objective = None
        residual = None
    else:
        feasible = True
        _require(solution["solver"]["success"] is True
                 and solution["hard_contract_equalities_embedded_in_milp"]
                 and max(abs(x["stock_end_mwh_lhv"]) for x in solution["hourly"]) <=
                 _num(config, "gas_storage_capacity_mwh_lhv")+TOL
                 and solution["max_contract_delivery_residual_mwh"] <= TOL
                 and solution["max_steady_on_ramp_violation_mw_e"] <= TOL
                 and solution["optimized_dispatch"]["max_interval_balance_residual_mwh"] <= TOL
                 and abs(solution["optimized_dispatch"]["terminal_inventory_residual_mwh"]) <= TOL,
                 f"{label}: MILP solution physical ledger failed")
        objective = solution["net_contribution_eur"]
        residual = solution["max_contract_delivery_residual_mwh"]
    _require(feasible == oracle["feasible"],
             f"{label}: independently derived toy feasibility contradicts MILP")
    return {
        "case_id": label,
        "parameter_values": parameters,
        "oracle_feasible": oracle["feasible"],
        "milp_feasible": feasible,
        "analytic_infeasibility_codes": oracle["reasons"],
        "contract_delivered_mwh": sum(awards) if feasible else None,
        "net_synthetic_contribution_eur": objective,
        "maximum_energy_contract_residual_mwh": residual,
    }


def _finite_marginal(rows: list[dict]) -> dict:
    n = len(rows)
    y = [int(r["milp_feasible"]) for r in rows]
    mu = sum(y)/n
    variance = sum((v-mu)**2 for v in y)/n
    marginals = {}
    centered = {}
    for key, levels in zip(ORDER, LEVELS):
        means = []
        for value in levels:
            selected = [int(r["milp_feasible"]) for r in rows
                        if r["parameter_values"][key] == value]
            _require(len(selected) == n//3, "Unequal/missing factorial cells")
            means.append(sum(selected)/len(selected))
        effect = [m-mu for m in means]
        component = sum(v*v for v in effect)/3
        marginals[key] = {
            "levels": list(levels),
            "finite_grid_feasibility_fraction_by_level": means,
            "maximum_minus_minimum_fraction": max(means)-min(means),
            "first_order_component_of_design_variance": component,
            "first_order_share_of_design_variance":
                component/variance if variance > 0 else None,
        }
        centered[key] = dict(zip(levels,effect))
    pairs = []
    for i, left in enumerate(ORDER):
        for right in ORDER[i+1:]:
            entries = []
            for a,b in product(LEVELS[ORDER.index(left)], LEVELS[ORDER.index(right)]):
                sub = [int(r["milp_feasible"]) for r in rows
                       if r["parameter_values"][left] == a
                       and r["parameter_values"][right] == b]
                _require(len(sub) == n//9, "Unbalanced second-order design")
                entries.append(sum(sub)/len(sub)-mu-centered[left][a]-centered[right][b])
            component = sum(v*v for v in entries)/len(entries)
            pairs.append({
                "parameters": [left,right],
                "interaction_component_of_design_variance": component,
                "interaction_share_of_design_variance":
                    component/variance if variance > 0 else None,
            })
    used=sum(x["first_order_component_of_design_variance"] for x in marginals.values())
    used+=sum(x["interaction_component_of_design_variance"] for x in pairs)
    _require(used <= variance+TOL, "Unbalanced or inconsistent factorial decomposition")
    return {
        "definition": "EXACT_UNWEIGHTED_FINITE_GRID_VARIANCE_DECOMPOSITION_NOT_SOBOL_PROBABILITY",
        "grid_mean_binary_feasibility": mu,
        "grid_variance_binary_feasibility": variance,
        "first_order": marginals,
        "second_order": pairs,
        "higher_order_residual_variance": max(0.0, variance-used),
        "statistical_probability_claim": False,
    }


def _box(config: dict, intervals: list[Interval], awards: list[float],
         item: dict) -> dict:
    bounds = item["bounds"]
    corners = []
    for levels in product(*[bounds[name] for name in ORDER]):
        trial = deepcopy(config)
        for key, value in zip(ORDER, levels):
            _set(trial, key, value)
        witness = forced_physical_oracle(trial, awards, [r.hours for r in intervals])
        corners.append(witness["feasible"])
    # For this always-ON positive fixed-output 2-slot toy, feasibility is
    # monotonic in all FOUR varied variables. The worst corner is therefore
    # sufficient for an exact complete-rectangle conditional certificate.
    worst = [bounds[ORDER[0]][0],bounds[ORDER[1]][0],
             bounds[ORDER[2]][1],bounds[ORDER[3]][0]]
    best = [bounds[ORDER[0]][1],bounds[ORDER[1]][1],
            bounds[ORDER[2]][0],bounds[ORDER[3]][1]]
    trial = deepcopy(config)
    for key, value in zip(ORDER,worst):
        _set(trial,key,value)
    worst_case = _evaluate(trial,intervals,awards,item["id"]+"_worst",
                           dict(zip(ORDER,worst)))
    _require(worst_case["oracle_feasible"] == all(corners),
             "Monotone worst-corner proof contradicted by other corners")
    trial = deepcopy(config)
    for key, value in zip(ORDER,best):
        _set(trial,key,value)
    best_case = _evaluate(trial,intervals,awards,item["id"]+"_best",
                          dict(zip(ORDER,best)))
    return {
        "id":item["id"],
        "bounds":bounds,
        "corners_checked_analytically":len(corners),
        "feasible_corners":sum(corners),
        "model_conditionally_feasible_everywhere_in_continuous_rectangle":
            bool(worst_case["oracle_feasible"]),
        "worst_corner":worst_case,
        "best_corner":best_case,
        "certificate_scope": (
            "Necessary-and-sufficient worst-corner bound only for this FIXED, "
            "two-slot, always-ON, strictly positive contract with unchanged "
            "efficiency, gas input, terminal stock, heat/dump, dwell, price, "
            "rating and initial conditions. NOT an equipment-certified box."
        ),
    }


def run_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict:
    """Run all 81 predeclared discrete cells + nine OAT and box witnesses."""
    payload = json.loads(Path(path).read_text(encoding="utf8"))
    base, intervals, awards, prices = _validate(payload)
    rows = []
    for idx, values in enumerate(product(*LEVELS)):
        config = deepcopy(base)
        for key,value in zip(ORDER,values):
            _set(config,key,value)
        rows.append(_evaluate(config, intervals, awards, f"F{idx:03d}",
                              dict(zip(ORDER,values))))
    _require(len(rows) == 81, "Full factorial lost scenarios")
    oat = []
    for key,levels in zip(OAT_ORDER,OAT_LEVELS):
        for val in levels:
            config = deepcopy(base)
            for reference_key,ref in zip(ORDER,REFERENCE):
                _set(config,reference_key,ref)
            _set(config,key,val)
            oat.append(_evaluate(config,intervals,awards,
                                 f"OAT_{key}_{val}", {key:val}))
    boxes=[]
    for item in payload["continuous_rectangles"]:
        config = deepcopy(base)
        boxes.append(_box(config,intervals,awards,item))
    summary={
        "factorial_case_count":len(rows),
        "factorial_feasible_count":sum(r["milp_feasible"] for r in rows),
        "factorial_infeasible_count":sum(not r["milp_feasible"] for r in rows),
        "failure_reason_frequency_over_grid":dict(sorted(Counter(
            reason for row in rows for reason in row["analytic_infeasibility_codes"]
        ).items())),
        "oat_case_count":len(oat),
        "continuous_rectangles_checked":len(boxes),
        "synthetic_electricity_contract_mwh":sum(awards),
        "hypothetical_gross_award_cashflow_proxy_eur":
            math.fsum(p*a for p,a in zip(prices,awards)),
        "distribution_free":True,
    }
    _require(summary["factorial_feasible_count"] == 16
             and summary["factorial_infeasible_count"] == 65,
             "Predeclared oracle witness count changed")
    _require([b["model_conditionally_feasible_everywhere_in_continuous_rectangle"]
              for b in boxes] == [False, True],
             "Conditional robust box witnesses changed")
    return {
        "protocol":PROTOCOL,
        "status":"PASS_CONDITIONAL_SYNTHETIC_SENSITIVITY_NOT_PLANT_VALIDATED",
        "model_scope":"V0911_TWO_HOUR_SYNTHETIC_CONTRACT_AND_MIDPOINT_RAMP_ONLY",
        "scenario_id":payload["scenario_id"],
        "assumption_source":EVIDENCE,
        "source_fingerprint":{
            key:PINS[key][1] for key in PINS
        },
        "summary":summary,
        "finite_design_attribution":_finite_marginal(rows),
        "factorial_cases":rows,
        "one_at_a_time_cases":oat,
        "continuous_box_certificates":boxes,
        "calibration_claim":False,
        "operational_market_eligibility_claim":False,
        "probabilistic_robustness_claim":False,
        "all_14_site_unknowns_resolved":False,
        "no_manufacturer_parameter_import":True,
        "claim_limit":(
            "No physical CHP validation, manufacturer part-load or dynamic "
            "tests, measured site load, probability distribution, real market "
            "award, delivery, net metering or profitability."
        )
    }
