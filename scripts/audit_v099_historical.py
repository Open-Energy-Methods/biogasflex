"""Offline audit of two 2020 Svk SE3 windows against hypothetical CHP.

The unaltered historical market prices are actual; the CHP and the
counterfactual sequential revelation of market prices are NOT actual.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.experimental_v099 import run_manifest


def audit():
    r=run_manifest(ROOT,ROOT/"examples/v099_historical_backtest.json")
    expected={
        ("april","last_observed"):2.7604166666666665,
        ("april","trailing_three_mean"):4.499583333333332,
        ("october","last_observed"):4.094166666666665,
        ("october","trailing_three_mean"):7.238194444444445,
    }
    if len(r["studies"])!=4:
        raise AssertionError("Missing expected two-by-two historical counterfactual matrix")
    checked={}
    for study in r["studies"]:
        day="april" if "april" in study["holdout_source_path"] else "october"
        key=(day,study["method"])
        oracle=expected.get(key)
        if oracle is None or abs(study["one_step_mae_eur_mwh"]-oracle)>1e-8:
            raise AssertionError(f"Source prices / independent 24-step forecast oracle differ: {key}")
        if (study["intervals"]!=24 or len(study["predictions_as_of_steps"])!=24
            or any(row["future_holdout_observations_used"]!=0 for row in study["predictions_as_of_steps"])):
            raise AssertionError("Missing observed prices or noncausal price-prediction provenance")
        if (study["max_gas_balance_residual_mwh"]>1e-7 or
            study["max_heat_service_residual_mwh"]>1e-7 or
            study["perfect_hindsight_regret_eur"] < -1e-6 or
            study["rolling_realized_contribution_eur"] >
            study["perfect_hindsight_contribution_eur"]+1e-6):
            raise AssertionError(f"Gas/heat/hindsight oracle violation: {key}")
        if study["operational_forecast_skill_claimed"] or study["trained_forecast_model"]:
            raise AssertionError("Unwarranted market prediction or operational claim")
        label=f"{day}/{study['method']}"
        if label in checked:
            raise AssertionError("Duplicate audit study")
        checked[label]={
            "one_step_mae_eur_mwh":study["one_step_mae_eur_mwh"],
            "one_step_rmse_eur_mwh":study["one_step_rmse_eur_mwh"],
            "rolling_realized_eur":study["rolling_realized_contribution_eur"],
            "perfect_hindsight_eur":study["perfect_hindsight_contribution_eur"],
            "hindsight_regret_eur":study["perfect_hindsight_regret_eur"],
            "max_gas_balance_residual_mwh":study["max_gas_balance_residual_mwh"],
        }
    if len(checked)!=4 or any(x["count"]!=24 for x in r["source_hashes"]):
        raise AssertionError("Data provenance matrix incomplete")
    return {
        "status":"PASS",
        "version":"0.9.9",
        "market_source":"Original frozen Svk SE3 CC BY 4.0 2020 price files",
        "observed_training_intervals":24,
        "observed_holdout_intervals":48,
        "observed_holdout_windows":2,
        "forecast_methods":2,
        "model":"SYNTHETIC_CHP hypothetical sequential price reveal",
        "operational_price_forecast_skill":"NOT_VERIFIED",
        "scientific_source_files_changed":False,
        "source_sha256":[x["sha256"] for x in r["source_hashes"]],
        "studies":checked,
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (AssertionError,ValueError,RuntimeError) as exc:
        raise SystemExit(f"V099 HISTORICAL REPLAY AUDIT FAIL: {exc}")
