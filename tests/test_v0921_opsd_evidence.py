"""Source SHA/vintage/UTC/leakage checks with solely synthetic test CSVs."""
from __future__ import annotations
import csv
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex import opsd_v0921 as s

class OPSDSourceContracts(unittest.TestCase):
    def test_pinned_official_publisher_source_sha(self):
        self.assertEqual(
            s.SOURCE_SHA256,
            "6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8")
        self.assertIn("time_series/2020-10-06",s.SOURCE_URL)
        self.assertIn("time_series",s.SOURCE_CHECKSUM_REPO)
        self.assertIn("SE_3",s.COL_LOAD_FORECAST)
        self.assertIn("SE_3",s.COL_LOAD_ACTUAL)

    def test_source_download_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"--download"):
                s.download_verified(Path(d)/"raw.csv",allow_network=False)

    def test_sha_fails_closed_without_original_source(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"wrong.csv"
            path.write_text("not actual OPSD data",encoding="utf8")
            with self.assertRaisesRegex(ValueError,"raw CSV SHA-256"):
                s.analyze(path)

    def test_utc_parser_fails_missing_explicit_Z(self):
        self.assertEqual(s._timestamp("2019-09-01T10:00:00Z").tzinfo,timezone.utc)
        for bad in ("2019-09-01 10:00:00","2019-09-01T10:00:00+01:00","bad"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError,"UTC timestamp"):
                    s._timestamp(bad)

    def _make(self,path,*,duplicate=False):
        start=datetime(2018,12,20,tzinfo=timezone.utc)
        end=datetime(2020,1,1,tzinfo=timezone.utc)
        fields=list(s.COLUMNS)
        with path.open("w",newline="",encoding="utf8") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            t=start
            while t<end:
                hour=t.hour
                d=(t-start).days
                row={
                    s.COL_TIME:t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    s.COL_PRICE:str(60+7*((hour+d)%5)),
                    s.COL_LOAD_FORECAST:str(2400+15*hour+4*(d%13)),
                    s.COL_LOAD_ACTUAL:str(2400+15*hour+4*(d%13)+(-1)**d*(4+hour)),
                }
                w.writerow(row)
                if duplicate and t==datetime(2019,2,1,tzinfo=timezone.utc):
                    w.writerow(row)
                t+=timedelta(hours=1)

    def test_source_day_blocks_holdout_and_no_price_forecast_mislabel(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fictional_hourly_fixture.csv"
            self._make(p)
            with patch.object(s,"_check_sha",return_value=0):
                out=s.analyze(p)
            self.assertGreater(out["quality"]["distinct_hourly_2019_aligned"],8000)
            self.assertGreater(out["quality"]["training_complete_days"],100)
            self.assertGreater(out["quality"]["heldout_complete_days"],30)
            self.assertEqual(out["source"]["sha256"],s.SOURCE_SHA256)
            self.assertFalse(out["source"]["last_per_observation_forecast_publication_verified"])
            self.assertFalse(out["interpretation"]["price_bid_gate_eligibility"].startswith("original price forecast"))
            self.assertFalse(out["training_metrics"]["heat_or_biogas_error_empirically_observed"])
            train=[x for x in out["complete_days"] if x["partition"].startswith("TRAIN")]
            hold=[x for x in out["complete_days"] if x["partition"].startswith("HOLDOUT")]
            self.assertLess(train[-1]["date_utc"],"2019-10-01")
            self.assertGreaterEqual(hold[0]["date_utc"],"2019-10-01")
            for day in (train[0],hold[-1]):
                self.assertEqual(len(day["price_baseline_error_eur_mwh"]),24)
                self.assertEqual(len(day["regional_load_error_relative"]),24)

    def test_duplicate_raw_UTC_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"synthetic_duplicate.csv"
            self._make(p,duplicate=True)
            with patch.object(s,"_check_sha",return_value=0):
                with self.assertRaisesRegex(ValueError,"Duplicate source UTC"):
                    s.analyze(p)

    def test_reject_tracked_report_output(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE checked-out repository"):
            s.write_out({"source":"synthetic"},ROOT/"temp-v0921.json",ROOT)

if __name__=="__main__":
    unittest.main()
