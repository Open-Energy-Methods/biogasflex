"""Adversarial v0.9.22 tests: no future-hour physical observations or price leakage."""
from __future__ import annotations

import copy
import unittest

from biogasflex import causal_v0922 as r
from biogasflex import joint_v0921 as j


def fixture():
    p = {
        "block_key": "NOMINAL",
        "price_eur_mwh": [40.0 + 2.0 * (t // 4) for t in range(j.N)],
        "synthetic_gas_production_mw_lhv": [1.0] * j.N,
        "synthetic_site_heat_demand_mw_th": [0.15] * j.N,
    }
    a = copy.deepcopy(p)
    a["price_eur_mwh"] = [52.0 - 3.0 * (t // 4) for t in range(j.N)]
    return p, a


class CausalReplayTests(unittest.TestCase):
    def test_nominal_six_hours_conservation_and_service(self):
        n, a = fixture()
        rows = r.replay_causal(n, a, [1] * j.N)
        self.assertTrue(rows["feasible"])
        self.assertEqual(len(rows["completed_15min_rows"]), 24)
        self.assertEqual(len(rows["hourly_observation_log"]), 6)
        previous_stock = j.STOCK_INITIAL
        for item in rows["completed_15min_rows"]:
            self.assertAlmostEqual(item["stock_end_mwh_lhv"],
                                   previous_stock + j.DT * (
                                       item["gas_in_mw_lhv"] - item["gas_use_mw_lhv"]),
                                   places=6)
            self.assertAlmostEqual(item["useful_chp_heat_mw_th"] +
                                   item["backup_heat_mw_th"],
                                   item["heat_demand_mw_th"], places=6)
            self.assertAlmostEqual(item["useful_chp_heat_mw_th"] +
                                   item["dumped_heat_mw_th"],
                                   j.ETA_H * item["gas_use_mw_lhv"], places=6)
            previous_stock = item["stock_end_mwh_lhv"]
        self.assertFalse(rows["perfect_future_information_used_for_dispatch"])

    def test_future_price_gas_heat_change_cannot_modify_past_controls(self):
        n, a = fixture()
        initial = r.replay_causal(n, a, [1] * j.N)
        modified = copy.deepcopy(a)
        # This is a deliberately adversarial future change, at hour 4.
        for t in range(16, j.N):
            modified["synthetic_gas_production_mw_lhv"][t] = 0.81
            modified["synthetic_site_heat_demand_mw_th"][t] = 0.19
            modified["price_eur_mwh"][t] = -55.0
        after = r.replay_causal(n, modified, [1] * j.N)
        self.assertTrue(initial["feasible"])
        self.assertTrue(after["feasible"])
        self.assertEqual(initial["completed_15min_rows"][:16],
                         after["completed_15min_rows"][:16])

    def test_realized_current_price_is_not_used_by_controller(self):
        n, a = fixture()
        first = r.replay_causal(n, a, [1] * j.N)
        changed = copy.deepcopy(a)
        changed["price_eur_mwh"] = [-90.0] * j.N
        second = r.replay_causal(n, changed, [1] * j.N)
        self.assertTrue(first["feasible"])
        self.assertTrue(second["feasible"])
        x = first["completed_15min_rows"]
        y = second["completed_15min_rows"]
        for left, right in zip(x, y):
            for key in ("gas_use_mw_lhv", "stock_end_mwh_lhv",
                        "useful_chp_heat_mw_th", "backup_heat_mw_th",
                        "dumped_heat_mw_th"):
                self.assertAlmostEqual(left[key], right[key], places=9)
        self.assertNotEqual(first["economic_contribution_eur"],
                            second["economic_contribution_eur"])

    def test_unavailable_future_hour_source_is_not_revealed(self):
        n, a = fixture()
        result = r.replay_causal(n, a, [1] * j.N)
        self.assertTrue(result["feasible"])
        log = result["hourly_observation_log"]
        self.assertEqual([item["revealed_source_hour_utc"] for item in log],
                         [8, 9, 10, 11, 12, 13])
        self.assertTrue(all(item["future_gas_heat_from_frozen_nominal_only"]
                            for item in log))

    def test_nonbinary_commitment_rejected(self):
        n, a = fixture()
        with self.assertRaisesRegex(ValueError, "binary sequence"):
            r.replay_causal(n, a, [1] * 23 + [2])

    def test_forced_off_six_hours_reports_infeasibility_not_profit(self):
        n, a = fixture()
        result = r.replay_causal(n, a, [0] * j.N)
        self.assertFalse(result["feasible"])
        self.assertIsNone(result["economic_contribution_eur"])
        self.assertLess(result["failed_hour"], j.HOURS)

    def test_unserved_heat_capacity_fails_closed(self):
        n, a = fixture()
        a["synthetic_site_heat_demand_mw_th"] = [0.35] * j.N
        with self.assertRaisesRegex(ValueError, "heat demand"):
            r.replay_causal(n, a, [1] * j.N)

    def test_missing_prior_week_source_day_is_excluded(self):
        from datetime import date, timedelta
        target = {"date_utc": "2019-12-25"}
        known = {"2019-12-17": {"date_utc": "2019-12-17",
                                "delivery_price_eur_mwh": [2] * 24}}
        self.assertIsNone(r._historical_baseline(target, known))
        d = (date(2019, 12, 25) - timedelta(days=7)).isoformat()
        known[d] = {"date_utc": d, "delivery_price_eur_mwh": [5] * 24}
        self.assertEqual(r._historical_baseline(target, known), [5] * 24)

    def test_switching_costs_must_match_binary_pattern(self):
        n, a = fixture()
        with self.assertRaisesRegex(ValueError, "Switch costs"):
            r.replay_causal(n, a, [1]*j.N,
                            starts=[1]*j.N, stops=[0]*j.N)


if __name__ == "__main__":
    unittest.main()
