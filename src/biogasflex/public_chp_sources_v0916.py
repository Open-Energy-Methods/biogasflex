"""v0.9.16 independently labelled, checksum-pinned public CHP source retrieval.

Never imports, modifies or calibrates BiogasFlex's CHP dispatch solver.
Download public CC BY sources only with explicit --fetch; otherwise offline.
Original downloads and derived temporary profiles remain OUTSIDE repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT/"data/evidence/v0916_public_chp_source_registry.json"
PROTOCOL="BIOGASFLEX_V0916_PUBLIC_EXTERNAL_CHP_SOURCES_V1"
ALLOWED={
 "rise_lulea_2023_biogas_sofc":{
    "doi":"10.5281/zenodo.14163174",
    "technology":"SOLID_OXIDE_FUEL_CELL_NOT_GAS_ENGINE",
    "fuel":"AUTOMOTIVE_QUALITY_BIOGAS",
    "license":"CC-BY-4.0",
    "names":{
      "FCData_v2.xlsx":(2862185,"c9d0d97a0e16ccec9552ac7e8c17880e"),
      "MeterData_v2.xlsx":(1469441,"e59a10e63d1ae5379cae8dcac32543f5"),
      "ThermalData_v2.xlsx":(1749672,"1816bdbd305b8c4a5734157e916070b3"),
      "DhSubstation_v2.xlsx":(9341756,"781c92e932ff0b794d174e8d3863ed21"),
    },
 },
 "kitakyushu_japan_2001_2022_citygas_chp":{
    "doi":"10.6084/m9.figshare.24978645.v2",
    "technology":"RECIPROCATING_GAS_ENGINE_CHP_AND_FUEL_CELL",
    "fuel":"CITY_GAS_NOT_BIOGAS",
    "license":"CC-BY-4.0",
    "names":{
      "Power.zip":(5272497,"c005150c3da98c822ad7ad6818e98658"),
      "Gas usage.zip":(6996876,"ac5bdca572e3fd14ed9a506e2e4abb80"),
      "Heat recovery.zip":(5642319,"76dea6064810b26ffabf646a125ca487"),
    },
 }
}
REQUIRED_BLOCKED={
 "rise_lulea_2023_biogas_sofc":{
    "GAS_ENGINE_RAMP_IDENTIFIED","LOVSTA_BIOGAS_ENGINE_CALIBRATED",
    "CALIBRATION_CERTIFICATES_AUTHENTICATED",
    "COMPLETE_15_MIN_CHP_11_CHANNEL_SCHEMA_VERIFIED"
 },
 "kitakyushu_japan_2001_2022_citygas_chp":{
    "ANAEROBIC_DIGESTER_BIOGAS_FUEL_EQUIVALENCE",
    "SUBHOUR_RAMP_OR_STARTUP_IDENTIFIED",
    "CALIBRATION_CERTIFICATES_AUTHENTICATED"
 }
}
NS={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

class PublicSourceError(ValueError):
    pass

def require(ok:bool,message:str)->None:
    if not ok: raise PublicSourceError(message)

def checked_registry(path:Path=REGISTRY)->dict:
    data=json.loads(Path(path).read_text(encoding="utf8"))
    require(data["protocol"]==PROTOCOL,"Unsupported source-scoped protocol")
    require(data["status"]=="CURATED_SOURCE_IDENTITIES_NO_RAW_SOURCE_BYTES_COMMITTED",
            "Cannot assert file retrieval from curated metadata")
    require(data["reviewed_at"]=="2026-11-15","Source review date changed")
    sources=data["sources"]
    require(type(sources) is list and len(sources)==2,"Source identities missing")
    require({s["id"] for s in sources}==set(ALLOWED),"Unexpected source identity")
    for src in sources:
        sid=src["id"]
        expected=ALLOWED[sid]
        require(src["doi"]==expected["doi"] and src["technology"]==expected["technology"]
                and src["fuel"]==expected["fuel"] and src["license"]==expected["license"],
                f"{sid}: changed fuel, equipment or source licence")
        require(src["high_rate_event_data_identified"] is False
                and src["traceable_calibration_certificates_verified"] is False,
                f"{sid}: absence of event and calibration evidence must be explicit")
        require(REQUIRED_BLOCKED[sid] <= set(src["blocked_claims"]),
                f"{sid}: unsupported physics claim became unblocked")
        require(len(src["files"])==len(expected["names"]),"Incomplete provider file list")
        require({f["name"] for f in src["files"]}==set(expected["names"]),
                "Unsupported filename or source list")
        for f in src["files"]:
            name=f["name"]
            expected_size,digest=expected["names"][name]
            require(f["bytes"]==expected_size and f["md5"]==digest,
                    f"{sid}/{name}: upstream file checksum/size changed")
            require(f["url"].startswith("https://")
                    and ((sid.startswith("rise") and
                          f["url"]=="https://zenodo.org/api/records/14163174/files/"+name+"/content")
                         or (sid.startswith("kitakyushu") and
                             f["url"].startswith("https://ndownloader.figshare.com/files/"))),
                    f"{sid}: source URL is outside approved domain")
    return data

def check_bytes(data:bytes, file_spec:dict)->dict:
    """Validate provider's pinned size/MD5; record independently computed SHA256."""
    require(type(data) is bytes,"Raw data must be bytes, not decoded text")
    actual_size=len(data); md5=hashlib.md5(data).hexdigest()
    require(actual_size==file_spec["bytes"],f"{file_spec['name']}: original byte size changed")
    require(md5==file_spec["md5"],f"{file_spec['name']}: published provider MD5 mismatch")
    return {
       "source_filename":file_spec["name"],
       "source_byte_count":actual_size,
       "source_published_md5":file_spec["md5"],
       "retrieved_md5":md5,
       "retrieved_sha256":hashlib.sha256(data).hexdigest(),
       "source_original_bytes_verified_against_provider_metadata":True,
    }

def safe_archive_members(z:ZipFile,max_total:int=350_000_000)->list:
    members=z.infolist()
    require(bool(members) and len(members)<5000,"Invalid archive member count")
    total=0
    for item in members:
        name=item.filename.replace("\\","/")
        require(name and not name.startswith("/")
                and not re.match(r"^[A-Za-z]:",name)
                and ".." not in name.split("/")
                and "\x00" not in name
                and not item.flag_bits&1,
                "Encrypted or unsafe archive member rejected")
        total+=item.file_size
        require(total<=max_total,"Archive expansion limit exceeded")
    return members

def xlsx_structure(raw:bytes,member_name:str)->dict:
    """Parse only workbook metadata and first sheet HEADER/short preview.

    No interpolation, time zone assumptions, numeric unit conversions or
    physical instrument calibration are attempted.
    """
    try:
        z=ZipFile(io.BytesIO(raw))
        safe_archive_members(z)
        workbook=ET.fromstring(z.read("xl/workbook.xml"))
        sheets=[x.attrib.get("name","") for x in workbook.findall(".//x:sheet",NS)]
        sheetpaths=sorted(s for s in z.namelist()
                          if re.fullmatch(r"xl/worksheets/sheet\d+\.xml",s))
        require(bool(sheets) and bool(sheetpaths),"XLSX worksheets unavailable")
        sheet=sheetpaths[0]
        # Inspect the XML without materializing large multiyear sheets.
        preview=[];dim=None
        with z.open(sheet) as fp:
            for event, elem in ET.iterparse(fp,events=("start","end")):
                if event=="start" and elem.tag.endswith("}dimension"):
                    dim=elem.attrib.get("ref")
                if event=="end" and elem.tag.endswith("}row"):
                    cells=[]
                    for cell in elem.findall("x:c",NS):
                        v=cell.find("x:v",NS)
                        inline=cell.find("x:is/x:t",NS)
                        value=v.text if v is not None else (inline.text if inline is not None else None)
                        if value is not None:
                            cells.append({"cell":cell.attrib.get("r"),
                                          "type":cell.attrib.get("t"),
                                          "raw_excel_value":str(value)[:90]})
                        if len(cells)>=12: break
                    if cells:preview.append({"excel_row":elem.attrib.get("r"),"cells":cells})
                    elem.clear()
                    if len(preview)>=3: break
        return {
           "container":member_name,
           "format":"XLSX",
           "sheet_names":sheets[:30],
           "sheet_count":len(sheets),
           "first_sheet_path":sheet,
           "declared_first_sheet_dimension":dim,
           "raw_first_three_nonempty_rows":preview,
           "excel_shared_string_and_datetime_decoding_performed":False,
           "source_site_physical_operating_claims":False,
        }
    except (BadZipFile,KeyError,ET.ParseError,EOFError) as exc:
        raise PublicSourceError(f"{member_name}: invalid XLSX archive/XML") from exc

def profile_content(data:bytes,file_spec:dict)->dict:
    name=file_spec["name"]
    if name.endswith(".xlsx"):return {
       "archive":"DIRECT_ORIGINAL_XLSX",
       "file_sheets":[xlsx_structure(data,name)],
    }
    require(name.endswith(".zip"),"Unrecognized original container")
    try:
        z=ZipFile(io.BytesIO(data))
        members=safe_archive_members(z)
        candidates=sorted(
             (m for m in members if m.filename.lower().endswith((".xlsx",".csv"))),
             key=lambda x:x.filename,
        )
        require(bool(candidates),"Public source ZIP has no XLSX/CSV source tables")
        chosen=[m for m in candidates if re.search(r"2005",m.filename)]
        if not chosen:chosen=candidates[:1]
        chosen=chosen[:2]
        result=[]
        for m in chosen:
            require(m.file_size<=40_000_000,"Nested table too large for exploratory parser")
            sub=z.read(m)
            if m.filename.lower().endswith(".xlsx"):
                result.append(xlsx_structure(sub,m.filename))
            else:
                head=sub[:2048].decode("utf8",errors="replace").splitlines()[:4]
                result.append({"container":m.filename,"format":"CSV",
                    "literal_csv_first_lines":head,
                    "units_and_datetime_validated":False})
        return {
            "archive":"PROVIDER_ZIP",
            "original_member_count":len(members),
            "tabular_member_count":len(candidates),
            "archived_table_names_first_30":[m.filename for m in candidates[:30]],
            "profiled_member_tables":result,
            "source_originals_unchanged":True,
        }
    except (BadZipFile,EOFError) as exc:
        raise PublicSourceError(f"{name}: broken original ZIP") from exc

def fetch_once(spec:dict)->bytes:
    req=urllib.request.Request(spec["url"],headers={
        "User-Agent":"BiogasFlex-research-v0916/0.1 (public CC-BY provenance audit)",
        "Accept":"application/octet-stream"
    })
    with urllib.request.urlopen(req,timeout=80) as response:
        require(response.status==200,f"{spec['name']}: HTTP {response.status}")
        data=response.read(spec["bytes"]+1)
    require(len(data)<=spec["bytes"],"Unexpected oversized source response")
    return data

def run(source:str,fetch:bool=False,report_path:Path|None=None)->dict:
    reg=checked_registry()
    require(source in set(ALLOWED)|{"all"},"Unknown source ID")
    selected=[s for s in reg["sources"] if s["id"]==source or source=="all"]
    result={
        "protocol":PROTOCOL,
        "source_count":len(selected),
        "fetch_opted_in":bool(fetch),
        "mode":"ONLINE_ORIGINAL_SOURCE_MD5_SHA256_AND_TABLE_PREVIEW" if fetch
               else "OFFLINE_CURATED_SOURCE_REGISTER_ONLY",
        "measurements_fabricated":False,
        "physical_site_engine_calibrated":False,
        "actual_engine_ramps_estimated":False,
        "calibration_certificates_verified":False,
        "sources":[],
    }
    for s in selected:
        entry={
            "id":s["id"],"technology":s["technology"],"fuel":s["fuel"],
            "doi":s["doi"],"license":s["license"],
            "raw_original_files":[]
        }
        for f in s["files"]:
            if fetch:
                raw=fetch_once(f)
                row=check_bytes(raw,f)
                row["structure"]=profile_content(raw,f)
            else:
                row={"source_filename":f["name"],"source_published_md5":f["md5"],
                     "source_byte_count_published":f["bytes"],
                     "original_bytes_retrieved":False}
            entry["raw_original_files"].append(row)
        result["sources"].append(entry)
    result["status"]=(
        "PASS_REAL_PUBLISHED_SOURCE_RAW_BYTES_AND_SCHEMA_STRUCTURE_AUDIT_NO_ENGINE_CALIBRATION"
        if fetch else "PASS_SOURCE_METADATA_SCOPE_NOT_YET_DOWNLOADED"
    )
    if report_path is not None:
        dest=Path(report_path).resolve()
        require(not dest.is_relative_to(ROOT.resolve()),
                "Acquisition reports must remain outside checked-out source tree")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2,allow_nan=False,ensure_ascii=False)+"\n",encoding="utf8")
    return result

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",choices=sorted(ALLOWED)+["all"],default="all")
    p.add_argument("--fetch",action="store_true",
                    help="EXPLICITLY download CC-BY published source files for integrity verification")
    p.add_argument("--report",type=Path,help="JSON results outside the source repository")
    args=p.parse_args()
    print(json.dumps(run(args.source,args.fetch,args.report),indent=2,allow_nan=False,ensure_ascii=False))

if __name__=="__main__":
    main()
