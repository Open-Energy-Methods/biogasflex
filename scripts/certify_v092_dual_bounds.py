"""Independent primal/dual LP certificate for frozen BiogasFlex market scenarios.

This tool reconstructs the *mathematical dual* from recorded interval inputs,
without importing the original heat-dispatch solver or its dual marginals.
It uses the same SciPy/HiGHS backend, so it is an independent formulation
check, NOT an independent solver implementation, peer review, or field evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import hstack, identity, lil_matrix

ROOT = Path(__file__).resolve().parents[1]
GAP_TOL_EUR = 5e-6
FEAS_TOL = 1e-7


class CertificateFailure(ValueError):
    pass


def numeric(value, name):
    if isinstance(value, bool):
        raise CertificateFailure(f"{name}: boolean is not numeric")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CertificateFailure(f"{name}: not numeric") from exc
    if not math.isfinite(result):
        raise CertificateFailure(f"{name}: not finite")
    return result


def primal_from_ledger(case, base):
    """Construct min c.x, Ax=b, 0<=x<=upper independently from stored inputs.

    Variables are 5 blocks: gas use, end stock, useful CHP heat, auxiliary
    heat and rejected heat. Equality rows: gas balance, CHP thermal balance,
    heat service and cyclic terminal stock. Energy-rate/time units are explicit.
    """
    rows = case["input_profile"]
    n = len(rows)
    if n < 1 or case["interval_count"] != n:
        raise CertificateFailure("Incorrect scenario interval count")
    eta_e = numeric(case["electric_efficiency_lhv_assumed"], "electric efficiency")
    eta_h = numeric(case["thermal_efficiency_lhv_assumed"], "thermal efficiency")
    rating = numeric(case["chp_electric_rating_mw"], "nameplate")
    storage = numeric(case["capacity_mwh_lhv"], "buffer capacity")
    start_stock = numeric(case["initial_and_terminal_stock_mwh_lhv"], "cyclic initial stock")
    aux_cap = numeric(base["aux_heat_capacity_mw_th"], "backup capacity")
    dump_cap = numeric(base["heat_dump_capacity_mw_th"], "sink capacity")
    if not (0 < eta_e <= 1 and 0 <= eta_h <= 1 and eta_e+eta_h <= 1+1e-12
            and rating > 0 and 0 <= start_stock <= storage
            and aux_cap >= 0 and dump_cap >= 0):
        raise CertificateFailure("Unphysical scenario parameters")
    a = lil_matrix((3*n+1, 5*n), dtype=float)
    b = np.zeros(3*n+1)
    c = np.zeros(5*n)
    upper = np.zeros(5*n)
    x = np.zeros(5*n)
    duration = 0.0
    for i, row in enumerate(rows):
        dt = numeric(row["dt_h"], "interval duration")
        price = numeric(row["price_eur_per_mwh"], "market price")
        prod = numeric(row["gas_production_mw_lhv"], "gas input")
        flare = numeric(row["fixed_flaring_mw_lhv"], "fixed flaring")
        loss = numeric(row["fixed_losses_mw_lhv"], "fixed losses")
        heat = numeric(row["heat_demand_mw_th"], "heat requirement")
        backup_price = numeric(row["auxiliary_heat_cost_eur_per_mwh_th"], "backup cost")
        dump_price = numeric(row["heat_dump_penalty_eur_per_mwh_th"], "dump cost")
        variable_price = numeric(row["chp_variable_cost_eur_per_mwh_e"], "CHP cost")
        if not (dt > 0 and prod >= flare+loss >= 0 and heat >= 0
                and backup_price >= 0 and dump_price >= 0 and variable_price >= 0):
            raise CertificateFailure(f"Interval {i}: invalid supply, heat or cost")
        duration += dt
        u, s, h, backup, dumped = i, n+i, 2*n+i, 3*n+i, 4*n+i
        upper[[u, s, h, backup, dumped]] = [rating/eta_e, storage, heat, aux_cap, dump_cap]
        c[u] = -eta_e*(price-variable_price)*dt
        c[backup] = backup_price*dt
        c[dumped] = dump_price*dt
        x[[u, s, h, backup, dumped]] = [
            numeric(row[key], key) for key in (
                "optimized_gas_use_mw_lhv", "stock_end_mwh_lhv",
                "optimized_useful_heat_mw_th", "optimized_auxiliary_heat_mw_th",
                "optimized_heat_dump_mw_th"
            )
        ]
        expected_start = start_stock if i == 0 else x[n+i-1]
        if abs(numeric(row["stock_start_mwh_lhv"], "stock start")-expected_start) > FEAS_TOL:
            raise CertificateFailure(f"Interval {i}: stock continuity mismatch")
        a[i, u] = dt
        a[i, s] = 1
        if i:
            a[i, s-1] = -1
        b[i] = (prod-flare-loss)*dt+(start_stock if i == 0 else 0)
        a[n+i, u] = eta_h
        a[n+i, h] = -1
        a[n+i, dumped] = -1
        a[2*n+i, h] = 1
        a[2*n+i, backup] = 1
        b[2*n+i] = heat
    a[3*n, 2*n-1] = 1
    b[3*n] = start_stock
    if abs(duration-numeric(case["duration_hours"], "duration hours")) > FEAS_TOL:
        raise CertificateFailure("Horizon duration mismatch")
    return a.tocsr(), b, c, upper, x


def certify_case(case, base, *, gap_tol=GAP_TOL_EUR):
    """Dual bound on maximized contribution from bounded-LP weak duality.

    For primal min c.x s.t. Ax=b, 0<=x<=u, solve the dual
    min b.y+u.z s.t. -A^T y-z<=c, y free, z>=0.
    Any feasible dual solution bounds the maximized contribution -c.x above.
    """
    a, b, c, upper, x = primal_from_ledger(case, base)
    residual = float(np.max(np.abs(a @ x-b)))
    bounds_error = float(max(np.max(np.maximum(-x, 0)), np.max(np.maximum(x-upper, 0))))
    if max(residual, bounds_error) > FEAS_TOL:
        raise CertificateFailure(f"Primal violates balances/bounds: {residual}, {bounds_error}")
    value = -float(c @ x)
    reported = numeric(case["optimized_dispatch"]["economic_contribution_proxy_eur"], "reported value")
    tol = max(gap_tol, 2e-8*max(1,abs(reported),abs(value)))
    if abs(value-reported) > tol:
        raise CertificateFailure("Recorded contribution and reconstructed primal disagree")
    inequalities = hstack([-a.transpose(), -identity(len(x), format="csr")], format="csr")
    dual = linprog(
        np.concatenate([b, upper]), A_ub=inequalities, b_ub=c,
        bounds=[(None, None)]*len(b)+[(0, None)]*len(x), method="highs"
    )
    if not dual.success or dual.x is None or dual.fun is None:
        raise CertificateFailure(f"Dual solver failed: {dual.status}: {dual.message}")
    violation = float(np.max(np.maximum(np.asarray(inequalities @ dual.x).ravel()-c, 0)))
    gap = float(dual.fun)-value
    if violation > FEAS_TOL or abs(gap) > tol:
        raise CertificateFailure(f"Invalid dual bound: gap={gap}, violation={violation}")
    return {"case_id":case["case_id"], "dual_bound_eur":float(dual.fun),
            "primal_contribution_eur":value, "abs_duality_gap_eur":abs(gap),
            "primal_residual":residual, "dual_violation":violation, "status":"PASS"}


def certify_all(root=ROOT):
    root = Path(root)
    base = json.loads((root/"config/v07_lovsta_heat_proxy.json").read_text(encoding="utf-8"))
    folder = root/"results/v0.8/cases"
    names = [f"V08-S{i:03d}.json" for i in range(216)]
    if sorted(p.name for p in folder.glob("V08-S*.json")) != names:
        raise CertificateFailure("Missing or additional market-case records")
    checks = []
    for name in names:
        case = json.loads((folder/name).read_text(encoding="utf-8"))
        if case["case_id"]+".json" != name:
            raise CertificateFailure("Case identity mismatch")
        checks.append(certify_case(case, base))
    return {"status":"PASS", "development_version":"0.9.2", "cases_certified":len(checks),
            "maximum_abs_duality_gap_eur":max(r["abs_duality_gap_eur"] for r in checks),
            "maximum_primal_residual":max(r["primal_residual"] for r in checks),
            "maximum_dual_violation":max(r["dual_violation"] for r in checks),
            "independence":"separate LP formulation; same HiGHS backend",
            "claim_boundary":"hypothetical dispatch optimization only, no independent human review"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    opts = parser.parse_args()
    try:
        print(json.dumps(certify_all(opts.root), indent=2, allow_nan=False))
    except (CertificateFailure, ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"DUAL CERTIFICATE FAILED: {exc}\n")
