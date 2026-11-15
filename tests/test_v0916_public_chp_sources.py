"""v0.9.16: adversarial public source retrieval metadata and no-dynamic-calibration gate."""
from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.public_chp_sources_v0916 import (
    checked_registry, PublicSourceError, check_bytes,
    safe_archive_members, xlsx_structure, profile_content, run,
)

class PublishedCHPSources(unittest.TestCase):
    def test_registry_two_independent_equipment_classes(self):
        r=checked_registry()
        self.assertEqual(len(r["sources"]),2)
        sources={s["id"]:s for s in r["sources"]}
        self.assertEqual(sources["rise_lulea_2023_biogas_sofc"]["fuel"],
                         "AUTOMOTIVE_QUALITY_BIOGAS")
        self.assertEqual(sources["kitakyushu_japan_2001_2022_citygas_chp"]["fuel"],
                         "CITY_GAS_NOT_BIOGAS")
        self.assertEqual(sum(len(s["files"]) for s in sources.values()),7)
        self.assertTrue(all(s["license"]=="CC-BY-4.0" for s in sources.values()))
        self.assertTrue(all(not s["traceable_calibration_certificates_verified"]
                            and not s["high_rate_event_data_identified"]
                            for s in sources.values()))

    def test_no_online_download_without_explicit_optin(self):
        r=run("all")
        self.assertEqual(r["status"],"PASS_SOURCE_METADATA_SCOPE_NOT_YET_DOWNLOADED")
        self.assertFalse(r["fetch_opted_in"])
        self.assertEqual([len(s["raw_original_files"]) for s in r["sources"]],[4,3])
        self.assertTrue(all(not f["original_bytes_retrieved"]
                            for s in r["sources"] for f in s["raw_original_files"]))
        self.assertFalse(r["physical_site_engine_calibrated"])
        self.assertFalse(r["actual_engine_ramps_estimated"])

    def test_hardware_type_and_fuel_transfer_blocked(self):
        import biogasflex.public_chp_sources_v0916 as src
        original=src.REGISTRY
        try:
            with tempfile.TemporaryDirectory() as temp:
                p=Path(temp)/"altered.json"
                doc=deepcopy(checked_registry())
                doc["sources"][0]["technology"]="RECIPROCATING_BIOGAS_ENGINE"
                p.write_text(json.dumps(doc))
                with self.assertRaisesRegex(PublicSourceError,"fuel, equipment"):
                    checked_registry(p)
                doc=deepcopy(checked_registry())
                doc["sources"][1]["fuel"]="FARM_BIOGAS"
                p.write_text(json.dumps(doc))
                with self.assertRaises(PublicSourceError):
                    checked_registry(p)
        finally:
            src.REGISTRY=original

    def test_site_specific_ramp_claims_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"altered.json"
            doc=deepcopy(checked_registry())
            doc["sources"][0]["blocked_claims"].remove("GAS_ENGINE_RAMP_IDENTIFIED")
            p.write_text(json.dumps(doc))
            with self.assertRaisesRegex(PublicSourceError,"became unblocked"):
                checked_registry(p)
            doc=deepcopy(checked_registry())
            doc["sources"][1]["traceable_calibration_certificates_verified"]=True
            p.write_text(json.dumps(doc))
            with self.assertRaisesRegex(PublicSourceError,"calibration"):
                checked_registry(p)

    def test_file_md5_and_size_rejection(self):
        spec={"name":"test.xlsx","bytes":3,"md5":"900150983cd24fb0d6963f7d28e17f72"}
        d=check_bytes(b"abc",spec)
        self.assertEqual(d["retrieved_md5"],spec["md5"])
        self.assertEqual(d["retrieved_sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        with self.assertRaisesRegex(PublicSourceError,"MD5 mismatch"):
            check_bytes(b"abd",spec)
        with self.assertRaisesRegex(PublicSourceError,"byte size"):
            check_bytes(b"ab",spec)

    def test_reject_archive_path_traversal_or_bomb(self):
        for name in ("../../secret.xlsx","/etc/passwd","C:/windows/file.csv"):
            with tempfile.TemporaryFile() as f:
                with ZipFile(f,"w",ZIP_DEFLATED) as z:z.writestr(name,"bad")
                f.seek(0)
                with ZipFile(f) as z:
                    with self.assertRaisesRegex(PublicSourceError,"unsafe"):
                        safe_archive_members(z)
        with tempfile.TemporaryFile() as f:
            with ZipFile(f,"w") as z:z.writestr("safe.xlsx","a"*300)
            f.seek(0)
            with ZipFile(f) as z:
                with self.assertRaisesRegex(PublicSourceError,"expansion"):
                    safe_archive_members(z,max_total=100)

    def test_xlsx_parser_structure_without_interpreting_fuel_or_time(self):
        workbook=(
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Meter log" sheetId="1"/></sheets></workbook>'
        )
        worksheet=(
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<dimension ref="A1:B3"/><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>Time</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>kW</t></is></c></row>'
            '<row r="2"><c r="A2"><v>45000</v></c>'
            '<c r="B2"><v>12.5</v></c></row>'
            '</sheetData></worksheet>'
        )
        buff=io.BytesIO()
        with ZipFile(buff,"w",ZIP_DEFLATED) as z:
            z.writestr("xl/workbook.xml",workbook)
            z.writestr("xl/worksheets/sheet1.xml",worksheet)
        r=xlsx_structure(buff.getvalue(),"faux.xlsx")
        self.assertEqual(r["sheet_names"],["Meter log"])
        self.assertEqual(r["declared_first_sheet_dimension"],"A1:B3")
        self.assertEqual(r["raw_first_three_nonempty_rows"][1]["cells"][1]["raw_excel_value"],"12.5")
        self.assertFalse(r["excel_shared_string_and_datetime_decoding_performed"])
        self.assertFalse(r["source_site_physical_operating_claims"])

    def test_report_must_be_outside_repo_tree(self):
        with self.assertRaisesRegex(PublicSourceError,"outside"):
            run("all",report_path=ROOT/"versioned_source_report_dont_write.json")
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/"report.json"
            r=run("rise_lulea_2023_biogas_sofc",report_path=out)
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text())["source_count"],1)
            self.assertFalse(r["fetch_opted_in"])

    def test_cli_offline_is_clean_and_does_not_imply_actual_download(self):
        p=subprocess.run([sys.executable,"-m","biogasflex","public-chp-sources",
                          "--source","all"],cwd=ROOT,capture_output=True,text=True,
                         check=True,timeout=45)
        report=json.loads(p.stdout)
        self.assertEqual(report["source_count"],2)
        self.assertFalse(report["fetch_opted_in"])
        self.assertFalse(report["physical_site_engine_calibrated"])


if __name__=="__main__":
    unittest.main()
