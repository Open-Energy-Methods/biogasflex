"""BiogasFlex v0.9.10 market information and no-imbalance gates.

All monetary examples are synthetic independently evaluated exact oracles.
No observed market awards, plant electricity export or balancing settlement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
import copy
import json
import subprocess
import sys
import unittest

from biogasflex.market_v0910 import (
    MarketBoundaryError, MODEL, _slots,
    audit_postclearing_delivery, validate_preclearing_offer, run_manifest,
)

ROOT=Path(__file__).resolve().parents[1]


def sample(quarterhour=False):
    name="v0910_market_quarterhour.json" if quarterhour else "v0910_market_hourly.json"
    x=json.loads((ROOT/"examples"/name).read_text(encoding="utf-8"))
    cfg=json.loads((ROOT/"examples/v0910_synthetic_chp.json").read_text(encoding="utf-8"))
    return x,cfg


def pre(s,config):
    return validate_preclearing_offer(s["market"],s["delivery_slots"],
                                       s["preclearing_offer"],config["electric_rating_mw"])


def post(s,config,receipt=None):
    return audit_postclearing_delivery(s["market"],s["delivery_slots"],
                                        pre(s,config) if receipt is None else receipt,
                                        s["exogenous_award"],config)


class MarketBoundaryTests(unittest.TestCase):
    def test_independent_hourly_cashflow_oracle_and_physical_zero_imbalance(self):
        x,c=sample()
        p=pre(x,c)
        self.assertFalse(p["clearing_prices_available"])
        self.assertIsNone(p["matched_energy_mwh"])
        self.assertIsNone(p["cashflow_eur"])
        self.assertEqual(p["contract_status"],"NOT_AWARDED_YET")
        a=post(x,c,p)
        self.assertEqual(a["model_type"],MODEL)
        self.assertEqual(a["phase"],"POST_CLEARING_EXOGENOUS_AWARD_MATCHED")
        self.assertAlmostEqual(a["gross_contract_cashflow_proxy_eur"],.4*20+.4*60)
        self.assertAlmostEqual(a["total_accepted_mwh"],.8)
        self.assertEqual(len(a["simulated_delivered_mwh"]),2)
        self.assertTrue(all(abs(q-.4)<1e-9 for q in a["simulated_delivered_mwh"]))
        self.assertLess(a["maximum_contract_vs_simulated_delivery_mwh"],1e-8)
        self.assertLess(a["gas_balance_max_residual_mwh"],1e-8)
        self.assertLess(a["heat_service_max_residual_mwh"],1e-8)
        self.assertFalse(a["imbalance_settlement_included"])
        self.assertFalse(a["bid_acceptance_optimization_included"])
        self.assertFalse(a["real_exchange_transaction"])
        self.assertFalse(a["market_profit_claimed"])

    def test_independent_quarter_hour_energy_duration_oracle(self):
        x,c=sample(quarterhour=True)
        a=post(x,c)
        self.assertAlmostEqual(a["gross_contract_cashflow_proxy_eur"],
                               .1*(20+40+60+80))
        self.assertAlmostEqual(a["total_accepted_mwh"],.4)
        self.assertEqual(len(a["simulated_delivered_mwh"]),4)
        self.assertTrue(all(abs(q-.1)<1e-8 for q in a["simulated_delivered_mwh"]))
        self.assertLess(a["maximum_contract_vs_simulated_delivery_mwh"],1e-8)

    def test_no_clearing_price_or_acceptance_allowed_in_preclear_api(self):
        x,c=sample()
        x["preclearing_offer"]["clearing_prices_eur_mwh"]=[20,60]
        with self.assertRaisesRegex(MarketBoundaryError,"exactly"):
            pre(x,c)
        x,c=sample()
        x["preclearing_offer"]["accepted_mwh"]=[.4,.4]
        with self.assertRaisesRegex(MarketBoundaryError,"exactly"):
            pre(x,c)

    def test_preclear_never_runs_postclear_optimizer(self):
        x,c=sample()
        with patch("biogasflex.market_v0910.optimize_commitment_milp",
                   side_effect=AssertionError("future price optimizer called")):
            p=pre(x,c)
        self.assertEqual(p["phase"],"PRE_CLEARING_EXOGENOUS_OFFER_VALIDATED")

    def test_asof_forecast_after_decision_rejected(self):
        x,c=sample()
        x["preclearing_offer"]["forecast_issued_utc"]="2026-11-17T10:45:00Z"
        with self.assertRaisesRegex(MarketBoundaryError,"as-of"):
            pre(x,c)

    def test_bid_at_or_after_gate_rejected(self):
        for time in ("2026-11-17T11:00:00Z","2026-11-17T11:01:00Z"):
            x,c=sample()
            x["preclearing_offer"]["bid_submitted_utc"]=time
            with self.subTest(time=time),self.assertRaisesRegex(MarketBoundaryError,"gate"):
                pre(x,c)

    def test_negative_or_overrated_offer_rejected(self):
        for quantity in (-.001,.801,float("nan"),True):
            x,c=sample()
            x["preclearing_offer"]["offered_mwh"][0]=quantity
            with self.subTest(quantity=quantity),self.assertRaises(MarketBoundaryError):
                pre(x,c)

    def test_offer_forecast_price_can_be_negative_but_not_nonfinite(self):
        x,c=sample()
        x["preclearing_offer"]["forecast_prices_eur_mwh"][0]=-50.0
        self.assertEqual(pre(x,c)["forecast_prices_eur_mwh"][0],-50)
        x["preclearing_offer"]["forecast_prices_eur_mwh"][0]=float("inf")
        with self.assertRaises(MarketBoundaryError):
            pre(x,c)

    def test_preclear_receipt_tampering_detected(self):
        x,c=sample()
        r=pre(x,c)
        r["offered_mwh"][0]=0.2
        with self.assertRaisesRegex(MarketBoundaryError,"modified"):
            post(x,c,r)

    def test_award_cannot_exceed_offered_quantity(self):
        x,c=sample()
        x["exogenous_award"]["accepted_mwh"][0]=0.5
        with self.assertRaisesRegex(MarketBoundaryError,"exceeds"):
            post(x,c)

    def test_partially_accepted_bid_without_feasible_contract_delivery_rejected(self):
        x,c=sample()
        x["exogenous_award"]["accepted_mwh"][0]=0.2
        with self.assertRaisesRegex(MarketBoundaryError,"UNMODELLED_IMBALANCE"):
            post(x,c)

    def test_zero_award_cannot_fabricate_alternative_sales(self):
        x,c=sample()
        x["exogenous_award"]["accepted_mwh"]=[0.0,0.0]
        with self.assertRaisesRegex(MarketBoundaryError,"UNMODELLED_IMBALANCE"):
            post(x,c)

    def test_bidding_zone_and_nameplate_must_remain_unchanged(self):
        x,c=sample()
        c["price_zone"]="SE4"
        with self.assertRaisesRegex(MarketBoundaryError,"zone"):
            post(x,c)
        x,c=sample()
        c["electric_rating_mw"]=0.7
        receipt=pre(x,c)
        c["electric_rating_mw"]=0.8
        with self.assertRaisesRegex(MarketBoundaryError,"Nameplate changed"):
            post(x,c,receipt)

    def test_result_must_be_published_after_gate_and_before_dispatch(self):
        for field,value in (
            ("prices_published_utc","2026-11-17T10:59:00Z"),
            ("participant_result_received_utc","2026-11-17T11:45:00Z"),
            ("dispatch_plan_created_utc","2026-11-17T11:54:00Z"),
            ("dispatch_plan_created_utc","2026-11-17T23:00:00Z"),
        ):
            x,c=sample()
            x["exogenous_award"][field]=value
            with self.subTest(field=field,value=value),self.assertRaisesRegex(MarketBoundaryError,"Auction result"):
                post(x,c)

    def test_delayed_result_after_delivery_rejected(self):
        x,c=sample()
        x["exogenous_award"].update({
            "prices_published_utc":"2026-11-17T23:10:00Z",
            "participant_result_received_utc":"2026-11-17T23:11:00Z",
            "dispatch_plan_created_utc":"2026-11-17T23:12:00Z",
        })
        with self.assertRaisesRegex(MarketBoundaryError,"Auction result"):
            post(x,c)

    def test_actual_negative_clearing_price_allowed_in_proxy_arithmetic(self):
        x,c=sample()
        x["exogenous_award"]["clearing_prices_eur_mwh"]=[-20.0,60.0]
        self.assertAlmostEqual(post(x,c)["gross_contract_cashflow_proxy_eur"],16.0)

    def test_missing_or_nonfinite_clearing_price_fails_closed(self):
        for bad in (float("nan"),float("inf"),True,None):
            x,c=sample()
            x["exogenous_award"]["clearing_prices_eur_mwh"][0]=bad
            with self.subTest(bad=bad),self.assertRaises(MarketBoundaryError):
                post(x,c)
        x,c=sample()
        x["exogenous_award"]["clearing_prices_eur_mwh"]=[20.0]
        with self.assertRaises(MarketBoundaryError):
            post(x,c)

    def test_unverified_market_award_source_rejected(self):
        x,c=sample()
        x["exogenous_award"]["award_provenance"]="ASSUMED_REAL_AWARD"
        with self.assertRaisesRegex(MarketBoundaryError,"verified participant"):
            post(x,c)

    def test_reject_ambiguous_naive_and_non_utc(self):
        for ts in ("2026-11-17T23:00:00", "2026-11-18T00:00:00+01:00"):
            x,c=sample()
            x["delivery_slots"][0]["start_utc"]=ts
            with self.subTest(ts=ts),self.assertRaisesRegex(MarketBoundaryError,"UTC"):
                pre(x,c)
        x,c=sample()
        x["market"]["auction_gate_close_utc"]="2026-11-17T12:00:00+01:00"
        with self.assertRaisesRegex(MarketBoundaryError,"UTC"):
            pre(x,c)

    def test_delivery_grid_rejects_gap_duplicate_and_wrong_civil_day(self):
        for start in ("2026-11-18T00:15:00Z","2026-11-17T23:00:00Z","2026-11-18T23:00:00Z"):
            x,c=sample()
            x["delivery_slots"][1]["start_utc"]=start
            with self.subTest(start=start),self.assertRaises(MarketBoundaryError):
                pre(x,c)
        x,c=sample()
        x["market"]["delivery_local_date"]="2026-11-17"
        with self.assertRaises(MarketBoundaryError):
            pre(x,c)

    def test_spring_and_autumn_dst_full_local_days_have_23_and_25_hourly_slots(self):
        local=ZoneInfo("Europe/Stockholm")
        for local_day,count in ((datetime(2026,3,29),23),(datetime(2026,10,25),25)):
            midnight=datetime(local_day.year,local_day.month,local_day.day,tzinfo=local)
            initial=midnight.astimezone(timezone.utc)
            slots=[{"start_utc":(initial+timedelta(hours=i)).isoformat(),
                    "duration_hours":1.0} for i in range(count)]
            previous=midnight-timedelta(days=1)
            m={
              "bidding_zone":"SE3",
              "delivery_local_date":local_day.date().isoformat(),
              "auction_gate_close_utc":previous.replace(hour=12).astimezone(timezone.utc).isoformat()
            }
            a=_slots(m,slots)
            self.assertEqual(len(a),count)
            self.assertEqual((initial+timedelta(hours=count)).astimezone(local).hour,0)

    def test_market_unphysical_chp_run_fails_without_fabricating_fills(self):
        x,c=sample()
        c["gas_input_mw_lhv"]=0.0
        with self.assertRaisesRegex(MarketBoundaryError,"could not satisfy physical"):
            post(x,c)

    def test_manifest_oracles_and_cli_help(self):
        for path,euros in ((ROOT/"examples/v0910_market_hourly.json",32.0),
                           (ROOT/"examples/v0910_market_quarterhour.json",20.0)):
            value=run_manifest(path)
            self.assertAlmostEqual(value["postclearing"]["gross_contract_cashflow_proxy_eur"],euros)
            self.assertNotIn("physical_solver_and_hourly",value["postclearing"])
        p=subprocess.run([sys.executable,"-m","biogasflex","--help"],
                         cwd=ROOT,capture_output=True,text=True,check=True,timeout=20)
        self.assertIn("market-boundary",p.stdout)


if __name__=="__main__":
    unittest.main()
