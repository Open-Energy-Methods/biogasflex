"""v0.9.9 adversarial causal information, provenance and regression oracles."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

from biogasflex.baseline import Interval
from biogasflex.experimental_v099 import (
    MODEL, make_causal_snapshots, evaluate_historical_replay, _read_declared
)
from test_v098_rolling import config

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/"examples/v099_historical_backtest.json").read_text(encoding="utf-8"))


def rows(prices, start=datetime(2020,1,2,tzinfo=timezone.utc), zone="SE3"):
    return [Interval(start+timedelta(hours=i),float(x),1.0,zone)
            for i,x in enumerate(prices)]


class CausalHistoricalRegressions(unittest.TestCase):
    def setup_inputs(self):
        return rows([10,20,30],datetime(2020,1,1,tzinfo=timezone.utc)), rows([5,15,50])

    def test_historical_training_and_two_holdouts_have_exact_utc_boundaries(self):
        tr=_read_declared(ROOT,MANIFEST["training"],"SE3")
        april=_read_declared(ROOT,MANIFEST["holdouts"][0],"SE3")
        october=_read_declared(ROOT,MANIFEST["holdouts"][1],"SE3")
        self.assertEqual(tuple(map(len,(tr,april,october))),(24,24,24))
        self.assertEqual(tr[-1].price_eur_per_mwh,24.81)
        self.assertAlmostEqual(sum(r.price_eur_per_mwh for r in april),167.71)
        self.assertAlmostEqual(sum(r.price_eur_per_mwh for r in october),732.96)
        self.assertLess(tr[-1].start_utc,april[0].start_utc)
        self.assertLess(tr[-1].start_utc,october[0].start_utc)

    def test_persistence_first_step_has_no_target_price(self):
        training,actual=self.setup_inputs()
        snaps,log=make_causal_snapshots(training,actual,"last_observed")
        self.assertEqual([s[0].price_eur_per_mwh for s in snaps],[30,5,15])
        self.assertEqual([len(s) for s in snaps],[3,2,1])
        self.assertEqual(log[0]["prior_holdout_observations_used"],0)
        self.assertTrue(all(r["future_holdout_observations_used"]==0 for r in log))

    def test_trailing_three_uses_only_known_history(self):
        training,actual=self.setup_inputs()
        snaps,_=make_causal_snapshots(training,actual,"trailing_three_mean")
        self.assertAlmostEqual(snaps[0][0].price_eur_per_mwh,20)
        self.assertAlmostEqual(snaps[1][0].price_eur_per_mwh,55/3)
        self.assertAlmostEqual(snaps[2][0].price_eur_per_mwh,50/3)

    def test_no_future_price_leakage_under_adversarial_mutation(self):
        training,actual=self.setup_inputs()
        mutated=list(actual)
        mutated[1]=Interval(actual[1].start_utc,-5000,actual[1].hours,actual[1].zone)
        for method in ("last_observed","trailing_three_mean"):
            a,_=make_causal_snapshots(training,actual,method)
            b,_=make_causal_snapshots(training,mutated,method)
            # Forecasts at steps 0 and 1 cannot depend on realized[t=1].
            self.assertEqual([[r.price_eur_per_mwh for r in s] for s in a[:2]],
                             [[r.price_eur_per_mwh for r in s] for s in b[:2]])
            self.assertNotEqual(a[2][0].price_eur_per_mwh,b[2][0].price_eur_per_mwh)

    def test_holdout_original_price_and_training_are_not_modified(self):
        tr,actual=self.setup_inputs()
        before=(list(tr),list(actual))
        for method in ("last_observed","trailing_three_mean"):
            make_causal_snapshots(tr,actual,method)
        self.assertEqual((tr,actual),before)

    def test_reject_training_that_overlaps_holdout(self):
        tr,actual=self.setup_inputs()
        for candidate in (actual[:1],actual[1:]):
            with self.assertRaisesRegex(ValueError,"overlap|future"):
                make_causal_snapshots(candidate,actual,"last_observed")

    def test_reject_market_zone_mismatch(self):
        tr,actual=self.setup_inputs()
        with self.assertRaisesRegex(ValueError,"mix bidding zones"):
            make_causal_snapshots(tr,rows([5,15,50],zone="SE2"),"last_observed")

    def test_reject_gaps_and_unsorted_or_duplicate_observations(self):
        tr,actual=self.setup_inputs()
        for bad in ([actual[0],actual[2]],
                    [actual[0],actual[0]],
                    [actual[1],actual[0]]):
            with self.assertRaisesRegex(ValueError,"missing|duplicated|unsorted|overlapping"):
                make_causal_snapshots(tr,bad,"last_observed")

    def test_reject_timezone_naive_and_nonfinite_and_wrong_duration(self):
        tr,actual=self.setup_inputs()
        candidates=[
            [Interval(datetime(2020,1,2),5,1,"SE3")],
            [Interval(actual[0].start_utc,float("nan"),1,"SE3")],
            [Interval(actual[0].start_utc,5,.3,"SE3")],
        ]
        for bad in candidates:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                make_causal_snapshots(tr,bad,"last_observed")

    def test_unknown_forecaster_rejected(self):
        tr,actual=self.setup_inputs()
        with self.assertRaisesRegex(ValueError,"Unknown"):
            make_causal_snapshots(tr,actual,"future_price_oracle")

    def test_expected_price_maes_independently_from_unchanged_csv(self):
        tr=_read_declared(ROOT,MANIFEST["training"],"SE3")
        for spec,expected in [
            (MANIFEST["holdouts"][0],{"last_observed":2.7604166666666665,
                                      "trailing_three_mean":4.499583333333332}),
            (MANIFEST["holdouts"][1],{"last_observed":4.094166666666665,
                                      "trailing_three_mean":7.238194444444445}),
        ]:
            actual=_read_declared(ROOT,spec,"SE3")
            for method,oracle in expected.items():
                _,rows_meta=make_causal_snapshots(tr,actual,method)
                mae=sum(abs(x["one_step_predicted_eur_mwh"]-x["one_step_realized_eur_mwh"])
                        for x in rows_meta)/24
                self.assertAlmostEqual(mae,oracle,places=9)

    def test_same_three_hour_synthetic_full_dispatch_still_obeys_hindsight_and_gas(self):
        tr,actual=self.setup_inputs()
        out=evaluate_historical_replay(config(n=3),tr,actual,"last_observed",
                                       include_hourly=True)
        self.assertEqual(out["intervals"],3)
        self.assertLessEqual(out["rolling_realized_contribution_eur"],
                             out["perfect_hindsight_contribution_eur"]+1e-7)
        self.assertLess(out["max_gas_balance_residual_mwh"],1e-8)
        self.assertLess(out["max_heat_service_residual_mwh"],1e-8)
        self.assertEqual(len(out["actual_executed_hourly"]),3)
        self.assertFalse(out["trained_forecast_model"])
        self.assertFalse(out["operational_forecast_skill_claimed"])

    def test_cli_lists_historical_replay(self):
        proc=subprocess.run([sys.executable,"-m","biogasflex","--help"],
                            cwd=ROOT,capture_output=True,text=True,check=True,timeout=20)
        self.assertIn("historical-replay",proc.stdout)


if __name__=="__main__":
    unittest.main()
