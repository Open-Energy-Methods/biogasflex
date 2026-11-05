"""Offline v0.9.8 price-only receding-horizon synthetic analytical stress."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))

from biogasflex.heat_dispatch import load_heat_case
from biogasflex.baseline import Interval
from biogasflex.experimental_v098 import evaluate_rolling_prices
from test_v098_rolling import config, times, snapshots


def close(got,expected,label):
    if not math.isfinite(got) or abs(got-expected)>1e-6:
        raise AssertionError(f"{label}: {got} != {expected}")


def audit():
    cfg,realized=load_heat_case(ROOT/"examples/v098_toy_config.json",
                                ROOT/"examples/v098_toy_realized_prices.csv")
    source=json.loads((ROOT/"examples/v098_toy_forecast_snapshots.json").read_text(encoding="utf-8"))
    forecast=snapshots(realized,source["forecasts_eur_per_mwh"])
    revised=evaluate_rolling_prices(cfg,realized,forecast)
    close(revised["rolling_realized_contribution_eur"],70,"3h revised realized")
    close(revised["perfect_foresight_net_contribution_eur"],80,"3h hindsight upper")
    close(revised["perfect_foresight_regret_eur"],10,"3h hindsight regret")
    static=evaluate_rolling_prices(cfg,realized,
                                   snapshots(realized,[[100,0,0],[100,0],[100]]))
    close(static["rolling_realized_contribution_eur"],60,"3h stale forecast")
    close(revised["rolling_realized_contribution_eur"]-
          static["rolling_realized_contribution_eur"],10,"reforecast gain over stale synthetic")
    two=times([0,100])
    reverse=evaluate_rolling_prices(config(n=2),two,
                                    snapshots(two,[[100,0],[100]]))
    close(reverse["rolling_realized_contribution_eur"],40,"2h adverse forecast realized")
    close(reverse["perfect_foresight_net_contribution_eur"],60,"2h hindsight upper")
    close(reverse["perfect_foresight_regret_eur"],20,"2h adverse forecast regret")
    if (revised["realized_physical_and_contribution_ledger"]["max_interval_balance_residual_mwh"]>1e-8
        or revised["realized_physical_and_contribution_ledger"]["max_heat_service_residual_mwh"]>1e-8):
        raise AssertionError("Physical gas or heat service reconciliation failed")
    if (revised["steps_executed"]!=3 or
        abs(revised["terminal_inventory_mwh_lhv"]-
            revised["original_initial_and_terminal_gas_inventory_mwh_lhv"])>1e-8):
        raise AssertionError("Not all rolling intervals executed to original terminal inventory")
    return {
        "status":"PASS","version":"0.9.8",
        "scope":"fully synthetic price-only forecast snapshots; no observed model skill or CHP validation",
        "revised_3h_realized_eur":revised["rolling_realized_contribution_eur"],
        "stale_3h_realized_eur":static["rolling_realized_contribution_eur"],
        "realized_reforecast_value_over_stale_eur":10,
        "full_actual_hindsight_3h_eur":revised["perfect_foresight_net_contribution_eur"],
        "revised_3h_hindsight_regret_eur":revised["perfect_foresight_regret_eur"],
        "two_slot_reversed_forecast_regret_eur":reverse["perfect_foresight_regret_eur"],
        "max_gas_balance_residual_mwh":revised["realized_physical_and_contribution_ledger"]["max_interval_balance_residual_mwh"],
        "initial_and_final_gas_stock_mwh_lhv":revised["terminal_inventory_mwh_lhv"],
        "steps_executed":revised["steps_executed"],
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (ValueError,RuntimeError,AssertionError) as error:
        raise SystemExit(f"v0.9.8 ROLLING AUDIT FAIL: {error}")
