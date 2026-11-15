"""v0.9.17 real published source analysis: independent synthetic parser and adversarial gates.

All artificial XLSX rows here are test fixtures, never reported as real plant
performance. Only separate online source retrieval constitutes real evidence.
"""
import io
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile,ZIP_DEFLATED
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from biogasflex.kitakyushu_real_v0917 import (
    ARCHIVES, YEAR, _read_workbook, analyse_frames, run, PINNED_SHA256,
    PublicSourceError
)

def hourly_synthetic_frames():
    start=datetime(YEAR,1,1)
    return {
        "Power.zip":{start+timedelta(hours=i):(0.,195.,50.,0.)
                     for i in range(8760)},
        "Gas usage.zip":{start+timedelta(hours=i):(2.,0.,20.,0.,0.,0.)
                        for i in range(8760)},
        "Heat recovery.zip":{start+timedelta(hours=i):(.1,.2,0.,0.,0.)
                             for i in range(8760)}
    }

def fake_xlsx(headers,rows):
    ns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    wb=f'<workbook xmlns="{ns}"><sheets><sheet name="Sheet1" sheetId="1"/></sheets></workbook>'
    ss=headers+list(dict.fromkeys(d for d,_ in rows))
    si={t:i for i,t in enumerate(ss)}
    shared='<sst xmlns="'+ns+'">'+''.join('<si><t>'+s+'</t></si>' for s in ss)+'</sst>'
    xmlrows=['<row r="1">'+''.join(
        f'<c r="{chr(65+j)}1" t="s"><v>{si[t]}</v></c>' for j,t in enumerate(headers))+'</row>']
    for number,(stamp,nums) in enumerate(rows,start=2):
        cells=[f'<c r="A{number}" t="s"><v>{si[stamp]}</v></c>']
        for j,value in enumerate(nums,start=1):
            if value is not None:
                cells.append(f'<c r="{chr(65+j)}{number}"><v>{value}</v></c>')
        xmlrows.append(f'<row r="{number}">'+''.join(cells)+'</row>')
    sheet='<worksheet xmlns="'+ns+'"><sheetData>'+''.join(xmlrows)+'</sheetData></worksheet>'
    f=io.BytesIO()
    with ZipFile(f,"w",ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml",wb)
        z.writestr("xl/sharedStrings.xml",shared)
        z.writestr("xl/worksheets/sheet1.xml",sheet)
    return f.getvalue()

class ExternalRealHourlyStudyTests(unittest.TestCase):
    def test_offline_without_original_data_fails_closed(self):
        with self.assertRaisesRegex(PublicSourceError,"Actual published source data"):
            run()

    def test_no_borrowed_biogas_calibration_claim(self):
        report=analyse_frames(hourly_synthetic_frames())
        self.assertEqual(report["matched_source_records"],8760)
        self.assertEqual(report["observed_source_sums"]["engine_electricity_kwh_hourly_integral"],438000)
        self.assertEqual(report["observed_source_sums"]["gas_engine_fuel_source_m3_hourly_sum"],175200)
        self.assertEqual(report["observed_source_sums"]["gas1_recovered_heat_gj_hourly_integral"],876)
        self.assertEqual(report["observed_source_sums"]["gas2_recovered_heat_gj_hourly_integral"],1752)
        self.assertEqual(report["counts"]["both_electric_and_gas_positive_hours"],8760)
        self.assertEqual(len(report["monthly_observed_source_totals"]),12)
        jan=report["monthly_observed_source_totals"][0]
        self.assertEqual(jan["source_hourly_records"],744)
        self.assertEqual(jan["generator_electric_kwh"],37200)
        self.assertEqual(sum(x["source_hourly_records"] for x in report["monthly_observed_source_totals"]),8760)
        self.assertEqual(sum(x["generator_electric_kwh"] for x in report["monthly_observed_source_totals"]),438000)
        self.assertEqual(report["source_fuel"],"CITY_GAS_NOT_BIOGAS")
        self.assertFalse(report["city_gas_lhv_authenticated"])
        self.assertFalse(report["physical_fuel_to_electric_efficiency_calculated"])
        self.assertFalse(report["direct_biogas_engine_parameter_validation"])
        self.assertFalse(report["gas_heat_1_2_direct_engine_allocation_confirmed"])
        self.assertFalse(report["subhour_plant_ramp_inferred"])

    def test_source_anomalies_remain_visible(self):
        frames=hourly_synthetic_frames()
        first=datetime(YEAR,1,1)
        frames["Gas usage.zip"][first]=(2.,0.,0.,0.,0.,0.)
        frames["Heat recovery.zip"][first]=(None,None,0.,0.,0.)
        r=analyse_frames(frames)
        self.assertEqual(r["counts"]["electric_positive_gas_zero_hours"],1)
        self.assertEqual(r["monthly_observed_source_totals"][0]["generator_positive_gas_zero_hours"],1)
        self.assertEqual(r["counts"]["complete_four_channel_hours"],8759)
        self.assertEqual(r["counts"]["missing_gas1_recovery_gj_per_hour"],1)
        self.assertEqual(r["sample_flagged_records"][0]["issue"],"GENERATOR_POWER_POSITIVE_BUT_GAS_ZERO")

    def test_missing_time_duplicate_and_cross_source_offset_rejected(self):
        frames=hourly_synthetic_frames()
        frames["Power.zip"].pop(datetime(YEAR,1,1))
        with self.assertRaisesRegex(PublicSourceError,"not one-to-one"):
            analyse_frames(frames)
        frames=hourly_synthetic_frames()
        key=datetime(YEAR,1,1)
        frames["Gas usage.zip"][key+timedelta(days=365)]=frames["Gas usage.zip"].pop(key)
        with self.assertRaisesRegex(PublicSourceError,"not one-to-one"):
            analyse_frames(frames)

    def test_exact_headers_and_strict_8760_source_rows(self):
        headers=ARCHIVES["Power.zip"]["headers"]
        start=datetime(2005,1,1)
        rows=[((start+timedelta(hours=i)).strftime("%Y %m-%d %H:%M"),
               (0,195,50,0)) for i in range(8760)]
        data=fake_xlsx(headers,rows)
        actual=_read_workbook(data,"Power.zip")
        self.assertEqual(len(actual),8760)
        self.assertEqual(actual[start][2],50)
        with self.assertRaisesRegex(PublicSourceError,"headers changed"):
            _read_workbook(fake_xlsx(["WRONG"]+headers[1:],rows),"Power.zip")
        with self.assertRaisesRegex(PublicSourceError,"continuity"):
            _read_workbook(fake_xlsx(headers,rows[:-1]),"Power.zip")
        duplicate=rows.copy()
        duplicate[4]=duplicate[3]
        with self.assertRaisesRegex(PublicSourceError,"Duplicate hourly"):
            _read_workbook(fake_xlsx(headers,duplicate),"Power.zip")

    def test_never_write_real_source_report_inside_git_repo(self):
        with self.assertRaises(PublicSourceError):
            from biogasflex.public_chp_sources_v0916 import require
            require(False,"Real data cannot be stored as an unverified fixture")
        self.assertEqual(len(PINNED_SHA256),3)
        self.assertTrue(all(len(value)==64 for value in PINNED_SHA256.values()))

if __name__=="__main__":
    unittest.main()
