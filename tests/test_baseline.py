import csv
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from biogasflex.baseline import baseline, parse_prices, load_config, select_local_day_from_svk_api_records

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / 'config/baseline.json')
SYNTH = ROOT / 'data/synthetic/prices_4h.csv'


def write_temp(rows):
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
    writer = csv.writer(f)
    writer.writerow(['start_time_utc','bidding_zone','price','price_unit'])
    writer.writerows(rows)
    f.close()
    return Path(f.name)


class BaselineTests(unittest.TestCase):
    def test_synthetic_oracle(self):
        b = baseline(CONFIG, parse_prices(SYNTH, 'SE3', required_hours=4))
        self.assertAlmostEqual(b['gross_electricity_revenue_eur'], 15.6)
        self.assertAlmostEqual(b['gas_consumed_mwh_lhv'], 2.4)
        self.assertAlmostEqual(b['electricity_generated_mwh'], 0.96)
        self.assertAlmostEqual(b['thermal_potential_mwh'], 1.08)
        self.assertAlmostEqual(b['headroom_ratio'], 5/3)
        self.assertAlmostEqual(b['baseline_capacity_factor'], 0.6)

    def test_price_unit_wrong(self):
        f = write_temp([('2020-01-01T00:00:00Z','SE3',10,'SEK-MWh'),('2020-01-01T01:00:00Z','SE3',20,'SEK-MWh')])
        with self.assertRaisesRegex(ValueError,'EUR'): parse_prices(f,'SE3')
        f.unlink()

    def test_no_silent_duplicate_timestamp(self):
        f = write_temp([('2020-01-01T00:00:00Z','SE3',10,'EUR-MWh'),('2020-01-01T00:00:00Z','SE3',20,'EUR-MWh')])
        with self.assertRaisesRegex(ValueError,'Duplicate'): parse_prices(f,'SE3')
        f.unlink()

    def test_zone_mismatch(self):
        with self.assertRaisesRegex(ValueError,'zone'): parse_prices(SYNTH,'SE4')

    def test_missing_interval_rejected(self):
        f = write_temp([('2020-01-01T00:00:00Z','SE3',10,'EUR-MWh'),('2020-01-01T02:00:00Z','SE3',20,'EUR-MWh')])
        with self.assertRaisesRegex(ValueError,'gap'): parse_prices(f,'SE3')
        f.unlink()

    def test_missing_final_observation_rejected_by_duration(self):
        with self.assertRaisesRegex(ValueError,'duration'): parse_prices(SYNTH,'SE3',required_hours=24)

    def test_negative_price_is_accepted(self):
        intervals = parse_prices(SYNTH,'SE3')
        self.assertEqual(intervals[2].price_eur_per_mwh,-5.0)

    def test_nonfinite_price_rejected(self):
        f = write_temp([('2020-01-01T00:00:00Z','SE3','nan','EUR-MWh'),('2020-01-01T01:00:00Z','SE3',20,'EUR-MWh')])
        with self.assertRaisesRegex(ValueError,'Invalid price'): parse_prices(f,'SE3')
        f.unlink()

    def test_unsupported_efficiency_and_capacity(self):
        ints = parse_prices(SYNTH,'SE3')
        for update in [{'electric_efficiency_lhv': 0.9,'thermal_efficiency_lhv':0.45}, {'electric_rating_mw': 0.1}, {'gas_input_mw_lhv': -3}]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                baseline({**CONFIG,**update}, ints)

    def test_utc_offsets_equivalent(self):
        f=write_temp([('2020-01-01T01:00:00+01:00','SE3',10,'EUR-MWh'),('2020-01-01T02:00:00+01:00','SE3',20,'EUR-MWh')])
        self.assertEqual(parse_prices(f,'SE3')[0].start_utc.isoformat(),'2020-01-01T00:00:00+00:00')
        f.unlink()

    def test_dst_spring_forward_23_hour_day(self):
        rows=[]
        start=datetime(2020,3,28,23,tzinfo=timezone.utc)
        for n in range(23):
            t=start+timedelta(hours=n)
            rows.append({'bidding_zone':'SE3','start_time_utc':t.replace(tzinfo=None).isoformat(), 'price':20,'price_unit':'EUR-MWh'})
        selected=select_local_day_from_svk_api_records(rows,'2020-03-29','SE3')
        self.assertEqual(len(selected),23)

    def test_dst_fall_back_25_hour_day(self):
        rows=[]
        start=datetime(2020,10,24,22,tzinfo=timezone.utc)
        for n in range(25):
            t=start+timedelta(hours=n)
            rows.append({'bidding_zone':'SE3','start_time_utc':t.replace(tzinfo=None).isoformat(), 'price':20,'price_unit':'EUR-MWh'})
        self.assertEqual(len(select_local_day_from_svk_api_records(rows,'2020-10-25','SE3')),25)

    def test_quarter_hour_price_duration(self):
        f=write_temp([(f'2025-10-01T00:{m:02d}:00Z','SE3',100,'EUR-MWh') for m in (0,15,30,45)])
        i=parse_prices(f,'SE3',required_hours=1)
        self.assertAlmostEqual(baseline(CONFIG,i)['gross_electricity_revenue_eur'],24)
        f.unlink()

    def test_price_ordering_is_canonical(self):
        f=write_temp([('2020-01-01T01:00:00Z','SE3',20,'EUR-MWh'),('2020-01-01T00:00:00Z','SE3',10,'EUR-MWh')])
        i=parse_prices(f,'SE3',required_hours=2)
        self.assertEqual(i[0].price_eur_per_mwh,10)
        f.unlink()

    def test_hourly_revenue_independently_recomputed(self):
        ints=parse_prices(SYNTH,'SE3')
        actual=baseline(CONFIG,ints)['gross_electricity_revenue_eur']
        independent=0
        for row in ints:
            independent += (0.6*0.4)*(row.price_eur_per_mwh)*row.hours
        self.assertAlmostEqual(actual,independent)


if __name__ == '__main__': unittest.main()

class ObservedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.config=load_config(ROOT / 'config/lovsta_2022_avg_with_se3_2020_prices.json')
        self.prices=parse_prices(ROOT / 'data/observed/svk_se3_20200101_CC-BY-4.0.csv','SE3',required_hours=24)

    def test_licensed_svk_snapshot_integrity(self):
        self.assertEqual(len(self.prices),24)
        self.assertEqual(self.prices[0].start_utc.isoformat(),'2019-12-31T23:00:00+00:00')
        self.assertEqual(self.prices[-1].start_utc.isoformat(),'2020-01-01T22:00:00+00:00')
        self.assertAlmostEqual(math.fsum(x.price_eur_per_mwh for x in self.prices),665.68)

    def test_annual_lovsta_rating_and_headroom(self):
        b=baseline(self.config,self.prices)
        self.assertAlmostEqual(b['electrical_output_mw'],3002.6/8760)
        self.assertAlmostEqual(b['rated_electric_output_mw'],0.499)
        self.assertAlmostEqual(b['baseline_capacity_factor'],3002.6/(8760*.499))
        self.assertGreater(b['rated_electric_output_mw'],b['electrical_output_mw'])

    def test_lovsta_cross_year_counterfactual_ledger_and_revenue(self):
        b=baseline(self.config,self.prices)
        self.assertAlmostEqual(b['electricity_generated_mwh'],24*3002.6/8760)
        self.assertAlmostEqual(b['thermal_potential_mwh'],24*2939.5/8760)
        self.assertAlmostEqual(b['gross_electricity_revenue_eur'],(3002.6/8760)*665.68)
        self.assertTrue(self.config['scenario_is_hypothetical'])

    def test_license_attribution_is_present(self):
        provenance=(ROOT/'data/observed/README.md').read_text(encoding='utf-8')
        self.assertIn('Svenska kraftnät',provenance)
        self.assertIn('Creative Commons Attribution 4.0',provenance)
        self.assertIn('reformatted extract',provenance)
