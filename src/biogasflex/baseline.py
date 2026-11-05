"""Fixed CHP baseline: standard library only; strictly UTC / energy-based accounting."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Interval:
    start_utc: datetime
    price_eur_per_mwh: float
    hours: float
    zone: str


def _date(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timestamps must have UTC offsets; ambiguous local timestamps rejected")
    return d.astimezone(timezone.utc)


def parse_prices(path: Path, expected_zone: str, *, required_hours: float | None = None,
                 end_utc: str | datetime | None = None) -> list[Interval]:
    with path.open(newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    if not records:
        raise ValueError("Empty price input")
    rows = []
    for r in records:
        if r['bidding_zone'] != expected_zone:
            raise ValueError("Unexpected bidding zone; do not mix markets")
        if r['price_unit'] not in ('EUR-MWh', 'EUR/MWh'):
            raise ValueError("Only EUR/MWh electricity prices accepted")
        p = float(r['price'])
        if not math.isfinite(p):
            raise ValueError("Invalid price")
        rows.append((_date(r['start_time_utc']), p))
    rows.sort()
    if len({x for x, _ in rows}) != len(rows):
        raise ValueError("Duplicate UTC timestamp")
    intervals = []
    for i, (start, price) in enumerate(rows):
        if i + 1 < len(rows):
            dt = (rows[i + 1][0] - start).total_seconds() / 3600
            if dt not in (0.25, 1.0):
                raise ValueError(f"Unsupported gap / interval of {dt} h")
        elif end_utc is not None:
            end = _date(end_utc) if isinstance(end_utc, str) else end_utc.astimezone(timezone.utc)
            dt = (end - start).total_seconds() / 3600
            if dt not in (0.25, 1.0):
                raise ValueError(f"Unsupported terminal interval duration of {dt} h")
        elif len(rows) > 1:
            # Legacy v0.5 baseline mode only; v0.6 explicitly requires end_utc.
            dt = (rows[-1][0] - rows[-2][0]).total_seconds() / 3600
        else:
            raise ValueError("A single record lacks interval duration; supply end_utc")
        intervals.append(Interval(start, price, dt, expected_zone))
    # Disallow silent missing observations at the end via caller's expected duration.
    if required_hours is not None and abs(sum(r.hours for r in intervals) - required_hours) > 1e-9:
        raise ValueError("Unexpected total duration / missing market observations")
    return intervals


def baseline(config: dict, intervals: list[Interval]) -> dict:
    g = float(config['gas_input_mw_lhv'])
    eta_e = float(config['electric_efficiency_lhv'])
    eta_th = float(config['thermal_efficiency_lhv'])
    rating = float(config['electric_rating_mw'])
    if not (g > 0 and rating > 0 and 0 < eta_e <= 1 and 0 <= eta_th <= 1 and eta_e + eta_th <= 1 + 1e-12):
        raise ValueError("Unphysical power, fuel or efficiency inputs")
    p = g * eta_e
    if p > rating + 1e-12:
        raise ValueError("Must-run power exceeds rated CHP electrical output")
    duration = sum(r.hours for r in intervals)
    out = {
        'case_id': config['case_id'],
        'market_zone': config['price_zone'],
        'time_start_utc': intervals[0].start_utc.isoformat(),
        'time_end_utc': (intervals[-1].start_utc + timedelta(hours=intervals[-1].hours)).isoformat(),
        'interval_count': len(intervals),
        'duration_hours': duration,
        'gas_input_mw_lhv': g,
        'electrical_output_mw': p,
        'thermal_potential_mw': g * eta_th,
        'rated_electric_output_mw': rating,
        'headroom_ratio': rating / p,
        'baseline_capacity_factor': p / rating,
        'gas_consumed_mwh_lhv': g * duration,
        'electricity_generated_mwh': p * duration,
        'thermal_potential_mwh': g * eta_th * duration,
        'gross_electricity_revenue_eur': math.fsum(r.price_eur_per_mwh * p * r.hours for r in intervals),
        'market_price_min_eur_per_mwh': min(r.price_eur_per_mwh for r in intervals),
        'market_price_max_eur_per_mwh': max(r.price_eur_per_mwh for r in intervals),
        'average_price_eur_per_mwh_time_weighted': math.fsum(r.price_eur_per_mwh * r.hours for r in intervals) / duration,
        'price_series_type': 'observed_or_synthetic_as_provided',
        'claim_boundary': 'Gross spot-market revenue, not net margin/profit or observed plant revenue. Heat is potential, not demonstrated useful delivery.'
    }
    assert abs(out['electricity_generated_mwh'] - out['gas_consumed_mwh_lhv'] * eta_e) < 1e-10
    assert abs(out['thermal_potential_mwh'] - out['gas_consumed_mwh_lhv'] * eta_th) < 1e-10
    return out


def select_local_day_from_svk_api_records(records: list[dict], local_date: str, zone: str) -> list[dict]:
    """Select provider rows for one local civil day, preserving UTC offsets at DST."""
    local_zone = ZoneInfo('Europe/Stockholm')
    selected = []
    for r in records:
        if r['bidding_zone'] != zone:
            continue
        d = datetime.fromisoformat(r['start_time_utc']).replace(tzinfo=timezone.utc)
        if d.astimezone(local_zone).date().isoformat() == local_date:
            selected.append(r)
    return sorted(selected, key=lambda r: r['start_time_utc'])


def write_price_csv(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['start_time_utc', 'bidding_zone', 'price', 'price_unit'])
        for r in records:
            w.writerow([r['start_time_utc'] + '+00:00', r['bidding_zone'], r['price'], r['price_unit']])


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def run(config_path: Path, price_path: Path, output_path: Path, mode: str) -> dict:
    config = load_config(config_path)
    intervals = parse_prices(price_path, config['price_zone'], required_hours=24 if mode == 'observed' else None)
    result = baseline(config, intervals)
    result['input_mode'] = mode
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result
