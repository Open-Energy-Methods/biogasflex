"""Gas-buffered, perfect-foresight *linear* CHP dispatch using SciPy/HiGHS.

Units: production, use, fixed flaring/loss = MW_gas LHV; stock = MWh_gas LHV;
       CHP electrical power = MW_e; gross electricity price = EUR/MWh_e.
There are no commitment binaries and no thermal demand/service assumptions in v0.6.
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

# Prespecified, absolute numerical tolerance; results report scaled residuals too.
CONSERVATION_ABS_TOL_MWH = 1e-8
RATING_ABS_TOL_MW = 1e-9
OBJECTIVE_ABS_TOL_EUR = 1e-7


class DispatchError(RuntimeError):
    """Nonoptimal or physically inconsistent optimization; never reported as a valid zero uplift."""


@dataclass(frozen=True)
class Inputs:
    case_id: str
    zone: str
    rating_mw_e: float
    eta_e: float
    eta_th: float
    initial_storage_mwh_lhv: float
    storage_capacity_mwh_lhv: float
    production_mw_lhv: tuple[float, ...]
    fixed_flaring_mw_lhv: tuple[float, ...]
    fixed_losses_mw_lhv: tuple[float, ...]
    price_intervals: tuple[Interval, ...]


def _series(config: dict, name: str, fallback: float, n: int) -> tuple[float, ...]:
    raw = config.get(name, fallback)
    if isinstance(raw, (int, float)):
        vals = (float(raw),) * n
    elif isinstance(raw, (list, tuple)) and len(raw) == n:
        vals = tuple(float(v) for v in raw)
    else:
        raise ValueError(f"{name} must be a scalar or {n}-entry series")
    if not all(math.isfinite(v) and v >= 0 for v in vals):
        raise ValueError(f"{name} contains negative or nonfinite values")
    return vals


def prepare_inputs(config: dict, intervals: Sequence[Interval], *, capacity: float | None = None) -> Inputs:
    """Validate and materialize *declared* input assumptions only."""
    if not intervals:
        raise ValueError("Price intervals are empty")
    n = len(intervals)
    timestamps = [r.start_utc for r in intervals]
    if len(set(timestamps)) != n or timestamps != sorted(timestamps):
        raise ValueError("Price timestamps must be sorted and distinct")
    if not all(math.isfinite(r.price_eur_per_mwh) and math.isfinite(r.hours) and r.hours > 0
               and r.zone == config['price_zone'] for r in intervals):
        raise ValueError("Price, zone, or interval duration invalid")
    for i in range(n - 1):
        if intervals[i].start_utc + timedelta(hours=intervals[i].hours) != intervals[i+1].start_utc:
            raise ValueError("Gap or overlap between price intervals")
    eta = float(config['electric_efficiency_lhv'])
    eta_th = float(config['thermal_efficiency_lhv'])
    rating = float(config['electric_rating_mw'])
    cap = float(capacity if capacity is not None else config['gas_storage_capacity_mwh_lhv'])
    initial = float(config.get('initial_gas_inventory_mwh_lhv', 0.0))
    if not all(math.isfinite(x) for x in (eta, eta_th, rating, cap, initial)):
        raise ValueError('Nonfinite physical parameter')
    if not (0 < eta <= 1 and 0 <= eta_th <= 1 and eta + eta_th <= 1 + 1e-12
            and rating > 0 and cap >= 0 and 0 <= initial <= cap):
        raise ValueError('Invalid efficiency, nameplate, storage capacity, or initial inventory')
    prod = _series(config, 'gas_production_mw_lhv', float(config.get('gas_input_mw_lhv', 0.0)), n)
    flaring = _series(config, 'fixed_flaring_mw_lhv', 0.0, n)
    losses = _series(config, 'fixed_losses_mw_lhv', 0.0, n)
    if any(flaring[i] + losses[i] > prod[i] + 1e-12 for i in range(n)):
        raise ValueError('Fixed flaring/losses exceed gas production')
    return Inputs(str(config['case_id']), str(config['price_zone']), rating, eta, eta_th,
                  initial, cap, prod, flaring, losses, tuple(intervals))


def _recalculate(x: Inputs, fuel_use: Sequence[float], stock: Sequence[float]) -> dict[str, Any]:
    """Independent ledger, computed from profiles rather than solver objective/constraints."""
    dt = [r.hours for r in x.price_intervals]
    n = len(dt)
    supplied = math.fsum(g * d for g, d in zip(x.production_mw_lhv, dt))
    flared = math.fsum(f * d for f, d in zip(x.fixed_flaring_mw_lhv, dt))
    lost = math.fsum(l * d for l, d in zip(x.fixed_losses_mw_lhv, dt))
    used = math.fsum(u * d for u, d in zip(fuel_use, dt))
    residuals = [stock[t+1] - stock[t] - (x.production_mw_lhv[t] - fuel_use[t]
                 - x.fixed_flaring_mw_lhv[t] - x.fixed_losses_mw_lhv[t]) * dt[t]
                 for t in range(n)]
    end_balance = supplied - used - flared - lost - (stock[-1] - stock[0])
    power = [u * x.eta_e for u in fuel_use]
    heat = [u * x.eta_th for u in fuel_use]
    return {
        'gas_produced_mwh_lhv': supplied,
        'gas_utilized_mwh_lhv': used,
        'gas_flared_mwh_lhv': flared,
        'gas_lost_mwh_lhv': lost,
        'electricity_generated_mwh': math.fsum(p * d for p, d in zip(power, dt)),
        'potential_heat_generated_mwh': math.fsum(q * d for q, d in zip(heat, dt)),
        'gross_electricity_revenue_eur': math.fsum(p * d * interval.price_eur_per_mwh
             for p, d, interval in zip(power, dt, x.price_intervals)),
        'max_interval_balance_residual_mwh': max(abs(v) for v in residuals),
        'full_horizon_gas_residual_mwh': end_balance,
        'terminal_inventory_residual_mwh': stock[-1] - x.initial_storage_mwh_lhv,
        'max_over_rating_mw': max(0.0, max(power) - x.rating_mw_e),
        'min_fuel_use_mw_lhv': min(fuel_use),
        'min_stock_mwh_lhv': min(stock),
        'max_stock_mwh_lhv': max(stock),
        'max_stock_above_capacity_mwh_lhv': max(0.0, max(stock) - x.storage_capacity_mwh_lhv),
    }


def _assert_physical(x: Inputs, ledger: dict[str, Any]) -> None:
    for field in ('max_interval_balance_residual_mwh','full_horizon_gas_residual_mwh',
                  'terminal_inventory_residual_mwh'):
        if abs(ledger[field]) > CONSERVATION_ABS_TOL_MWH:
            raise DispatchError(f'Conservation failure {field}={ledger[field]}')
    for field in ('max_over_rating_mw',):
        if ledger[field] > RATING_ABS_TOL_MW:
            raise DispatchError(f'Nameplate violation {field}={ledger[field]}')
    if ledger['min_fuel_use_mw_lhv'] < -RATING_ABS_TOL_MW:
        raise DispatchError('Negative fuel use')
    if ledger['min_stock_mwh_lhv'] < -CONSERVATION_ABS_TOL_MWH:
        raise DispatchError('Negative gas inventory')
    if ledger['max_stock_above_capacity_mwh_lhv'] > CONSERVATION_ABS_TOL_MWH:
        raise DispatchError('Storage over capacity')


def optimize_dispatch(config: dict, intervals: Sequence[Interval], *,
                      capacity_mwh_lhv: float | None = None) -> dict[str, Any]:
    """Maximize *gross* electricity revenue under exact cycling and fixed supply.

    Uses an LP (not MILP): continuous CHP modulation, no min load/start-up/heat service.
    SciPy `linprog(method='highs')` uses HiGHS; no undisclosed binary constraints.
    """
    x = prepare_inputs(config, intervals, capacity=capacity_mwh_lhv)
    n = len(x.price_intervals)
    dt = [r.hours for r in x.price_intervals]
    c = [-x.eta_e * r.price_eur_per_mwh * r.hours for r in x.price_intervals] + [0.0] * n
    a = lil_matrix((n + 1, 2 * n), dtype=float)
    b = [0.0] * (n + 1)
    for t in range(n):
        a[t, t] = dt[t]
        a[t, n + t] = 1.0  # storage after interval t
        if t > 0:
            a[t, n + t - 1] = -1.0
        b[t] = (x.production_mw_lhv[t] - x.fixed_flaring_mw_lhv[t]
                - x.fixed_losses_mw_lhv[t]) * dt[t] + (x.initial_storage_mwh_lhv if t == 0 else 0.0)
    a[n, 2 * n - 1] = 1.0
    b[n] = x.initial_storage_mwh_lhv
    bounds = [(0.0, x.rating_mw_e / x.eta_e)] * n + [(0.0, x.storage_capacity_mwh_lhv)] * n
    sol = linprog(c, A_eq=a.tocsr(), b_eq=b, bounds=bounds, method='highs')
    if sol.status != 0 or not sol.success or sol.x is None:
        raise DispatchError(f'HiGHS did not find a verified optimum: status={sol.status} {sol.message}')
    use = [float(v) for v in sol.x[:n]]
    stock = [x.initial_storage_mwh_lhv] + [float(v) for v in sol.x[n:]]
    optim = _recalculate(x, use, stock)
    _assert_physical(x, optim)
    if abs(-float(sol.fun) - optim['gross_electricity_revenue_eur']) > OBJECTIVE_ABS_TOL_EUR:
        raise DispatchError('Objective/recomputed revenue mismatch')
    # Fixed comparator uses same production, fixed flaring, fixed losses, and start/end inventory.
    fixed_use = [g - f - l for g, f, l in zip(x.production_mw_lhv, x.fixed_flaring_mw_lhv, x.fixed_losses_mw_lhv)]
    fixed_stock = [x.initial_storage_mwh_lhv] * (n + 1)
    fixed_feasible = max(v * x.eta_e for v in fixed_use) <= x.rating_mw_e + RATING_ABS_TOL_MW
    fixed = _recalculate(x, fixed_use, fixed_stock)
    if fixed_feasible:
        _assert_physical(x, fixed)
    # Do not publish a gain where the reference dispatch itself is physically infeasible.
    if not fixed_feasible:
        raise DispatchError('Fixed comparator infeasible at CHP nameplate; cannot report fair uplift')
    if abs(optim['gas_utilized_mwh_lhv'] - fixed['gas_utilized_mwh_lhv']) > CONSERVATION_ABS_TOL_MWH:
        raise DispatchError('Different fuel utilization between comparable scenarios')
    uplift = optim['gross_electricity_revenue_eur'] - fixed['gross_electricity_revenue_eur']
    if uplift < -OBJECTIVE_ABS_TOL_EUR:
        raise DispatchError('Optimal revenue below feasible fixed comparator')
    return {
        'version': '0.6.0', 'case_id': x.case_id, 'model_type': 'continuous LP solved by SciPy HiGHS',
        'solver': {'library': 'scipy.optimize.linprog', 'backend': 'HiGHS',
                   'status_code': int(sol.status), 'success': bool(sol.success),
                   'termination': str(sol.message), 'iterations': int(sol.nit)},
        'claim_boundary': 'Perfect-foresight electricity-only gross spot-equivalent opportunity under assumed operating constraints; not net margin, validated plant dispatch, actual generator export, CHP heat service, or realizable storage design.',
        'price_zone': x.zone, 'gas_basis': 'MWh_LHV', 'currency': 'EUR',
        'capacity_mwh_lhv': x.storage_capacity_mwh_lhv,
        'initial_and_terminal_stock_mwh_lhv': x.initial_storage_mwh_lhv,
        'chp_electric_rating_mw': x.rating_mw_e,
        'electric_efficiency_lhv_assumed': x.eta_e,
        'heat_efficiency_lhv_assumed': x.eta_th,
        'interval_count': n, 'duration_hours': math.fsum(dt),
        'fixed_dispatch': fixed, 'optimized_dispatch': optim,
        'gross_incremental_revenue_eur': uplift,
        'input_profile': [
            {'start_utc': r.start_utc.isoformat(),
             'end_utc': (r.start_utc + timedelta(hours=r.hours)).isoformat(),
             'dt_h': r.hours, 'price_eur_per_mwh': r.price_eur_per_mwh,
             'gas_production_mw_lhv': x.production_mw_lhv[t],
             'fixed_flaring_mw_lhv': x.fixed_flaring_mw_lhv[t],
             'fixed_losses_mw_lhv': x.fixed_losses_mw_lhv[t],
             'fixed_chp_power_mw_e': x.eta_e * fixed_use[t],
             'optimized_chp_power_mw_e': x.eta_e * use[t],
             'optimized_gas_use_mw_lhv': use[t],
             'stock_start_mwh_lhv': stock[t],
             'stock_end_mwh_lhv': stock[t+1]}
            for t, r in enumerate(x.price_intervals)],
        'tolerance_contract': {
            'max_absolute_gas_balance_mwh': CONSERVATION_ABS_TOL_MWH,
            'max_absolute_rating_error_mw': RATING_ABS_TOL_MW,
            'max_absolute_objective_recalculation_eur': OBJECTIVE_ABS_TOL_EUR},
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_case(config_path: Path, price_path: Path) -> tuple[dict, list[Interval]]:
    config = load_config(config_path)
    if 'price_window_end_utc' not in config:
        raise ValueError('v0.6 requires explicit price_window_end_utc: no inferred terminal interval')
    intervals = parse_prices(price_path, config['price_zone'],
                             end_utc=config['price_window_end_utc'],
                             required_hours=config.get('expected_duration_hours'))
    return config, intervals


def run_dispatch(config_path: Path, price_path: Path, output_path: Path, *,
                 capacity_mwh_lhv: float | None = None) -> dict[str, Any]:
    config, intervals = _load_case(config_path, price_path)
    result = optimize_dispatch(config, intervals, capacity_mwh_lhv=capacity_mwh_lhv)
    result['provenance'] = {'config_path': str(config_path), 'config_sha256': _sha256(config_path),
                            'price_path': str(price_path), 'price_sha256': _sha256(price_path)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return result


def run_sweep(config_path: Path, price_path: Path, output_path: Path) -> dict[str, Any]:
    config, intervals = _load_case(config_path, price_path)
    sweep = config.get('storage_sweep_mwh_lhv')
    if not isinstance(sweep, list) or not sweep:
        raise ValueError('No preregistered storage_sweep_mwh_lhv list')
    capacities = tuple(float(v) for v in sweep)
    if not all(math.isfinite(v) and v >= 0 for v in capacities) or len(set(capacities)) != len(capacities) or sorted(capacities) != list(capacities):
        raise ValueError('Storage sweep must be finite, nonnegative, distinct, and ascending')
    results = []
    for capacity in capacities:
        # For capacity zero, the required initial inventory must be zero, which the baseline config uses.
        result = optimize_dispatch(config, intervals, capacity_mwh_lhv=capacity)
        results.append({'capacity_mwh_lhv': capacity,
                        'baseline_revenue_eur': result['fixed_dispatch']['gross_electricity_revenue_eur'],
                        'optimal_revenue_eur': result['optimized_dispatch']['gross_electricity_revenue_eur'],
                        'incremental_gross_revenue_eur': result['gross_incremental_revenue_eur'],
                        'max_balance_residual_mwh': result['optimized_dispatch']['max_interval_balance_residual_mwh'],
                        'solver_status': result['solver']['status_code']})
    # Larger storage relaxes constraints; gross revenue cannot worsen in this LP formulation.
    if any(results[i+1]['optimal_revenue_eur'] + OBJECTIVE_ABS_TOL_EUR < results[i]['optimal_revenue_eur'] for i in range(len(results)-1)):
        raise DispatchError('Optimal revenue decreases with relaxed storage capacity')
    result = {'version':'0.6.0', 'case_id':config['case_id'], 'model_type':'continuous LP',
              'predeclared_storage_sweep_mwh_lhv': list(capacities), 'cases': results,
              'claim_boundary':'Electricity-only perfect-foresight gross opportunity; no heat-service validation',
              'provenance':{'config_path':str(config_path),'config_sha256':_sha256(config_path),
                            'price_path':str(price_path),'price_sha256':_sha256(price_path)}}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n',encoding='utf-8')
    return result
