"""v0.9.9 offline chronological-price replay: observed Svk prices, synthetic CHP.

This is NOT an operationally available day-ahead price forecast, site
validation, or training a statistical electricity model. Price levels are
exposed strictly after each interval in a hypothetical sequential replay.
Future interval *calendar* is known in advance; future prices are hidden.
Only fixed, predeclared lag-one and three-observation-mean naive predictors.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

from .baseline import Interval, parse_prices
from .experimental_v098 import evaluate_rolling_prices
from .heat_dispatch import prepare_heat_inputs

METHODS = ("last_observed", "trailing_three_mean")
MODEL = "historical_price_sequential_replay_synthetic_chp_v099"


def _grid(intervals: Sequence[Interval], label: str) -> None:
    if not intervals:
        raise ValueError(f"{label} must be nonempty")
    zone = intervals[0].zone
    for i, row in enumerate(intervals):
        if (not isinstance(row, Interval) or
            row.start_utc.tzinfo is None or
            row.start_utc.utcoffset() != timedelta(0) or
            row.zone != zone or not zone or
            not math.isfinite(row.hours) or row.hours not in (0.25, 1.0) or
            not math.isfinite(row.price_eur_per_mwh)):
            raise ValueError(f"{label} requires finite, UTC, single-zone quarter/hour observations")
        if i and intervals[i-1].start_utc + timedelta(hours=intervals[i-1].hours) != row.start_utc:
            raise ValueError(f"{label} contains a missing, duplicated, unsorted or overlapping interval")


def make_causal_snapshots(
    training: Sequence[Interval],
    realized: Sequence[Interval],
    method: str,
) -> tuple[list[list[Interval]], list[dict[str, Any]]]:
    """Emit one remaining-horizon constant-price snapshot per decision.

    Invariant: prediction at t reads training + realized[:t] ONLY.
    Timestamps and interval durations for the future are known scheduling
    coordinates, NOT evidence about future prices. The current target
    price is appended to history only AFTER making that step's forecast.
    """
    if method not in METHODS:
        raise ValueError("Unknown predeclared naive forecast method")
    _grid(training, "Training history")
    _grid(realized, "Holdout price window")
    if training[0].zone != realized[0].zone:
        raise ValueError("Cannot mix bidding zones between history and holdout")
    prior_end = training[-1].start_utc + timedelta(hours=training[-1].hours)
    if prior_end > realized[0].start_utc:
        raise ValueError("Training observations overlap or occur after holdout start: future information")
    history = [r.price_eur_per_mwh for r in training]
    records: list[dict[str, Any]] = []
    snapshots: list[list[Interval]] = []
    for t, row in enumerate(realized):
        price = history[-1] if method == "last_observed" else math.fsum(history[-3:]) / min(3, len(history))
        cutoff = prior_end if t == 0 else realized[t-1].start_utc + timedelta(hours=realized[t-1].hours)
        if cutoff > row.start_utc:
            raise ValueError("Forecast cutoff exceeds simulated decision time")
        snapshots.append([
            Interval(future.start_utc, price, future.hours, future.zone)
            for future in realized[t:]
        ])
        records.append({
            "step": t,
            "decision_start_utc": row.start_utc.isoformat(),
            "information_cutoff_utc": cutoff.isoformat(),
            "training_samples": len(training),
            "prior_holdout_observations_used": t,
            "future_holdout_observations_used": 0,
            "one_step_predicted_eur_mwh": price,
            "one_step_realized_eur_mwh": row.price_eur_per_mwh,
        })
        # Strict causal update: this observed price was invisible at step t.
        history.append(row.price_eur_per_mwh)
    return snapshots, records


def evaluate_historical_replay(
    config: dict,
    training: Sequence[Interval],
    realized: Sequence[Interval],
    method: str,
    *,
    include_hourly: bool = False,
) -> dict[str, Any]:
    """Run existing v0.9.8.1 engine; calculate actual-price regret/forecast errors.

    Assumes a hypothetical chronological reveal of interval spot prices.
    This does NOT match real advance publication of day-ahead prices.
    """
    _grid(realized, "Holdout price window")
    prepare_heat_inputs(config, realized)
    snapshots, audit = make_causal_snapshots(training, realized, method)
    out = evaluate_rolling_prices(config, realized, snapshots)
    errors = [row["one_step_predicted_eur_mwh"] - row["one_step_realized_eur_mwh"] for row in audit]
    n = len(errors)
    mae = math.fsum(abs(e) for e in errors)/n
    rmse = math.sqrt(math.fsum(e*e for e in errors)/n)
    realized_eur = out["rolling_realized_contribution_eur"]
    hindsight = out["perfect_foresight_net_contribution_eur"]
    if realized_eur > hindsight+1e-6:
        raise ValueError("Historical causal replay exceeds perfect-hindsight upper bound")
    ledger=out["realized_physical_and_contribution_ledger"]
    if ledger["max_interval_balance_residual_mwh"]>1e-7 or ledger["max_heat_service_residual_mwh"]>1e-7:
        raise ValueError("Physical ledger failed in chronological observed-price replay")
    report={
        "version":"0.9.9",
        "model_type":MODEL,
        "method":method,
        "case_id":config["case_id"],
        "observed_price_provenance":"Previously published Svk 2020 SE3 24h sample, CC BY 4.0; source file pinned separately",
        "plant_assumption":"ENTIRELY SYNTHETIC CHP, storage, costs and heat; never observed site returns",
        "price_reveal_assumption":"HYPOTHETICAL interval-by-interval price reveal. Not a historically deployable day-ahead trading strategy.",
        "operational_forecast_skill_claimed":False,
        "trained_forecast_model":False,
        "data_split":"Fixed earlier January 2020 price history; April/October 2020 replay holdouts",
        "intervals":n,
        "start_utc":realized[0].start_utc.isoformat(),
        "end_utc":(realized[-1].start_utc+timedelta(hours=realized[-1].hours)).isoformat(),
        "one_step_mae_eur_mwh":mae,
        "one_step_rmse_eur_mwh":rmse,
        "rolling_realized_contribution_eur":realized_eur,
        "perfect_hindsight_contribution_eur":hindsight,
        "perfect_hindsight_regret_eur":out["perfect_foresight_regret_eur"],
        "fixed_reference_feasible":out["rolling_fixed_reference_feasible"],
        "gain_over_feasible_fixed_eur":out["rolling_gain_over_feasible_fixed_eur"],
        "max_gas_balance_residual_mwh":ledger["max_interval_balance_residual_mwh"],
        "max_heat_service_residual_mwh":ledger["max_heat_service_residual_mwh"],
        "total_realized_start_cost_eur":out["total_realized_start_cost_eur"],
        "total_realized_stop_cost_eur":out["total_realized_stop_cost_eur"],
        "terminal_inventory_mwh_lhv":out["terminal_inventory_mwh_lhv"],
        "predictions_as_of_steps":audit,
    }
    if include_hourly:
        report["actual_executed_hourly"]=out["hourly_executed"]
        report["actual_physical_and_contribution_ledger"]=ledger
    return report


def _read_declared(path: Path, spec: dict, zone: str) -> list[Interval]:
    if not isinstance(spec,dict) or set(spec)!={"path","first_utc","end_utc","count"}:
        raise ValueError("Explicit source file, first and last UTC boundaries and exact count required")
    if type(spec["count"]) is not int or spec["count"]<=0:
        raise ValueError("Source count must be a positive integer")
    path_value = Path(spec["path"])
    if path_value.is_absolute() or ".." in path_value.parts or not path_value.as_posix().startswith("data/observed/"):
        raise ValueError("Historical replay inputs must be relative attributed observed-source files")
    rows = parse_prices(path/path_value,zone,
                        end_utc=spec["end_utc"],required_hours=float(spec["count"]))
    if len(rows)!=spec["count"] or rows[0].start_utc.isoformat()!=datetime.fromisoformat(spec["first_utc"].replace("Z","+00:00")).astimezone(timezone.utc).isoformat():
        raise ValueError("Observed source has missing, extra or incorrect first UTC rows")
    _grid(rows,"Source observations")
    return rows


def run_manifest(
    root: Path,
    manifest_path: Path,
    *,
    include_hourly: bool = False,
) -> dict[str, Any]:
    """Strict offline manifest replay. No downloads, no output file by default."""
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("model")!=MODEL or manifest.get("zone")!="SE3"
        or set(manifest.get("methods",[]))!=set(METHODS)
        or len(manifest.get("holdouts",[]))!=2):
        raise ValueError("Expected fixed two-holdout, two-method v0.9.9 protocol")
    config_path=root/manifest["hypothetical_chp_config"]
    config=json.loads(config_path.read_text(encoding="utf-8"))
    config.pop("price_window_end_utc",None)
    config.pop("expected_duration_hours",None)
    training=_read_declared(root,manifest["training"],manifest["zone"])
    training_path=root/manifest["training"]["path"]
    out=[]
    data_sources=[{"role":"training","path":manifest["training"]["path"],
                   "sha256":hashlib.sha256(training_path.read_bytes()).hexdigest(),
                   "count":len(training)}]
    for holdout in manifest["holdouts"]:
        obs=_read_declared(root,holdout,manifest["zone"])
        obs_path=root/holdout["path"]
        data_sources.append({"role":"held_out","path":holdout["path"],
                             "sha256":hashlib.sha256(obs_path.read_bytes()).hexdigest(),
                             "count":len(obs)})
        for mode in manifest["methods"]:
            trial={**config,"case_id":"v099_historical_prices_synthetic_CHP_"+mode+"_"+obs[0].start_utc.strftime("%Y%m%d")}
            result=evaluate_historical_replay(trial,training,obs,mode,
                                              include_hourly=include_hourly)
            result["holdout_source_path"]=holdout["path"]
            out.append(result)
    return {
        "version":"0.9.9","model_type":MODEL,
        "status":"HISTORICAL_PRICES_SYNTHETIC_PLANT_HYPOTHETICAL_SEQUENTIAL_REPLAY",
        "source_attribution":"Svenska kraftnät, SE3 day-ahead area prices 2020; CC BY 4.0",
        "methodology":"Jan 2020 historical anchor; two 24h out-of-sample calendar windows (April and October), two untuned causal naive price predictors; no within-window future prices to forecast",
        "limitations":"Prices are real but hypothetically revealed one interval at a time, not an operationally available day-ahead forecast or physical plant revenue. Two selected days do not establish statistical skill.",
        "hypothetical_chp_config_sha256":hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "source_hashes":data_sources,
        "observed_heldout_days":len(manifest["holdouts"]),
        "forecast_methods":list(manifest["methods"]),
        "studies":out,
    }
