"""v0.9.17: measured Kitakyushu 2005 hourly gas-engine electricity/gas/heat audit.

A source-labelled descriptive analysis, never fitted biogas engine performance.
Works on provider-pinned originals, with online I/O exclusively under --fetch.
No declared city-gas LHV, no inferred thermal balance or ramp/starts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from .public_chp_sources_v0916 import (
    ALLOWED, ROOT, checked_registry, check_bytes, fetch_once,
    require, safe_archive_members, PublicSourceError
)

PROTOCOL="BIOGASFLEX_V0917_KITAKYUSHU_HOURLY_REAL_DATA_V1"
YEAR=2005
ARCHIVES={
    "Power.zip":{
        "member":"Power_time series__2005.xlsx",
        "headers":["Date","Solar energy generation (kW)",
                   "Electricity imported from grid (kW)","Gas engine (kW)","Fuel cell (kW)"],
    },
    "Gas usage.zip":{
        "member":"Gas usage_Time series__2005.xlsx",
        "headers":["Date","Boiler (m3)","Fuel cell (m3)","Gas engine (m3)",
                   "Absorption chiller 1 (m3)","Absorption chiller 2 (m3)",
                   "Absorption chiller 3 (m3)"],
    },
    "Heat recovery.zip":{
        "member":"Heat recovery_time series__2005.xlsx",
        "headers":["Date","Gas 1(GJ/h)","Gas 2(GJ/h)",
                   "Fuel cell 1(GJ/h)","Fuel cell 2(GJ/h)",
                   "Fuel cell 3(GJ/h)"],
    },
}
NS={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
PINNED_SHA256={
 "Power.zip":"07080996e8f1686c79d06c6a37a76a775b534d92c94f9d57d623e3ad77156444",
 "Gas usage.zip":"c69525c06785fe4e3ccf6f54edc57d3ccd4ea6c6b9f1e8d3631dec4f30fc1f1a",
 "Heat recovery.zip":"7d4bec1a873f7a4603b446ac248fc2679345b34c396b57759f8826345b4f57fa",
}

def _shared_strings(z:ZipFile)->list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    ans=[]
    with z.open("xl/sharedStrings.xml") as fp:
        for _,el in ET.iterparse(fp,events=("end",)):
            if el.tag.endswith("}si"):
                ans.append("".join(t.text or "" for t in el.findall(".//x:t",NS)))
                el.clear()
                require(len(ans)<100_000,"Excessively large shared string table")
    return ans

def _read_workbook(raw:bytes,archive_name:str)->dict[datetime,tuple]:
    """Reject errors and mixed conventions rather than interpolate missing source values."""
    spec=ARCHIVES[archive_name]
    z=ZipFile(io.BytesIO(raw))
    safe_archive_members(z)
    require("xl/worksheets/sheet1.xml" in z.namelist(),"Expected first worksheet missing")
    strings=_shared_strings(z)
    headers=spec["headers"]
    rows={}
    with z.open("xl/worksheets/sheet1.xml") as fp:
        for _,el in ET.iterparse(fp,events=("end",)):
            if el.tag.endswith("}row"):
                index=int(el.attrib.get("r","0"))
                values={}
                for cell in el.findall("x:c",NS):
                    ref=cell.attrib.get("r","")
                    match=re.fullmatch(r"([A-Z]+)\d+",ref)
                    require(match is not None,"Unidentified XLSX cell")
                    col=0
                    for ch in match.group(1): col=26*col+(ord(ch)-64)
                    require(col<=len(headers),"Unexpected extra spreadsheet column")
                    v=cell.find("x:v",NS)
                    inline=cell.find("x:is/x:t",NS)
                    value=v.text if v is not None else (inline.text if inline is not None else None)
                    if cell.attrib.get("t")=="s":
                        require(value is not None,"Unassigned shared-string cell")
                        k=int(value)
                        require(0<=k<len(strings),"Shared string index invalid")
                        value=strings[k]
                    if cell.attrib.get("t")=="e":raise PublicSourceError("XLSX error cell")
                    values[col-1]=value
                if index==1:
                    actual=[values.get(i) for i in range(len(headers))]
                    require(actual==headers,f"{archive_name}: source headers changed {actual!r}")
                elif index>1:
                    rawstamp=values.get(0)
                    require(isinstance(rawstamp,str),"Missing source timestamp")
                    try:
                        stamp=datetime.strptime(rawstamp,"%Y %m-%d %H:%M")
                    except ValueError as exc:
                        raise PublicSourceError("Unexpected source date string") from exc
                    require(stamp.year==YEAR and stamp.minute==0,"Year or subhour mismatch")
                    require(stamp not in rows,"Duplicate hourly timestamp")
                    nums=[]
                    for i in range(1,len(headers)):
                        value=values.get(i)
                        if value is None or value=="": nums.append(None)
                        else:
                            try: number=float(value)
                            except ValueError as exc:
                                raise PublicSourceError(f"Non-numeric measured value in {archive_name}") from exc
                            require(math.isfinite(number),"Infinite/NaN measured value")
                            nums.append(number)
                    rows[stamp]=tuple(nums)
                    require(len(rows)<=8784,"Unexpected source number of hourly rows")
                el.clear()
    start=datetime(YEAR,1,1)
    expected={start+timedelta(hours=i) for i in range(365*24)}
    require(set(rows)==expected,
            f"{archive_name}: hourly continuity not established (have {len(rows)}, expected 8760)")
    return rows

def _decode_bundle(raws:dict[str,bytes])->dict[str,dict[datetime,tuple]]:
    require(set(raws)==set(ARCHIVES),"All three independent original source files required")
    src=checked_registry()
    site=next(x for x in src["sources"] if x["id"]=="kitakyushu_japan_2001_2022_citygas_chp")
    specs={x["name"]:x for x in site["files"]}
    out={}
    for name,raw in raws.items():
        check_bytes(raw,specs[name])
        require(hashlib.sha256(raw).hexdigest()==PINNED_SHA256[name],
                f"Original {name} differs from independently observed 2026-11-15 SHA256")
        z=ZipFile(io.BytesIO(raw))
        safe_archive_members(z)
        member=ARCHIVES[name]["member"]
        require(member in z.namelist(),f"Exact 2005 member absent from {name}")
        require(z.getinfo(member).file_size<=50_000_000,"Nested source workbook too large")
        out[name]=_read_workbook(z.read(member),name)
    return out

def analyse_frames(frames:dict[str,dict[datetime,tuple]])->dict:
    require(set(frames)==set(ARCHIVES),"All electricity/gas/heat channels required")
    expected=[datetime(YEAR,1,1)+timedelta(hours=i) for i in range(8760)]
    require(all(set(frames[k])==set(expected) for k in ARCHIVES),
            "Source timestamps not one-to-one aligned")
    counts=Counter()
    sums=Counter()
    peaks={x:None for x in (
       "engine_electrical_kw","engine_gas_m3_per_hour",
       "gas1_recovery_gj_per_hour","gas2_recovery_gj_per_hour",
       "combined_gas_1_2_recovery_gj_per_hour")}
    examples=[]
    by_month={str(i).zfill(2):Counter() for i in range(1,13)}
    for dt in expected:
        p,g,h=frames["Power.zip"][dt],frames["Gas usage.zip"][dt],frames["Heat recovery.zip"][dt]
        electric=p[2];fuel=g[2];heat1=h[0];heat2=h[1]
        vals={"engine_electrical_kw":electric,"engine_gas_m3_per_hour":fuel,
              "gas1_recovery_gj_per_hour":heat1,"gas2_recovery_gj_per_hour":heat2,
              "combined_gas_1_2_recovery_gj_per_hour":
                heat1+heat2 if heat1 is not None and heat2 is not None else None}
        bucket=by_month[str(dt.month).zfill(2)]
        bucket["source_hourly_records"]+=1
        if electric is not None:
            bucket["observed_engine_electric_hours"]+=1
            bucket["generator_electric_kwh"]+=electric
        if fuel is not None:
            bucket["observed_engine_fuel_hours"]+=1
            bucket["source_engine_gas_m3"]+=fuel
        if electric is not None and electric>0: counts["engine_electric_positive_hours"]+=1
        if fuel is not None and fuel>0: counts["engine_gas_positive_hours"]+=1
        if electric is not None and fuel is not None:
            counts["paired_electric_gas_hours"]+=1
            bucket["paired_electric_gas_hours"]+=1
            if electric>0 and fuel>0:
                counts["both_electric_and_gas_positive_hours"]+=1
                bucket["electric_and_gas_positive_hours"]+=1
            if electric>0 and fuel==0:
                counts["electric_positive_gas_zero_hours"]+=1
                bucket["generator_positive_gas_zero_hours"]+=1
                if len(examples)<6:examples.append({"timestamp_local_unspecified":dt.isoformat(),
                    "issue":"GENERATOR_POWER_POSITIVE_BUT_GAS_ZERO"})
            if electric==0 and fuel>0:
                counts["electric_zero_gas_positive_hours"]+=1
                bucket["generator_zero_gas_positive_hours"]+=1
        if all(x is not None for x in (electric,fuel,heat1,heat2)):
            counts["complete_four_channel_hours"]+=1
        for key,value in vals.items():
            if value is None:counts["missing_"+key]+=1;continue
            counts["observed_"+key]+=1
            if value<0:counts["negative_"+key]+=1
            sums[key]+=value
            if peaks[key] is None or value>peaks[key]:peaks[key]=value
        counts["source_hourly_records"]+=1
    # Electricity kW across exactly one hour -> kWh; gas m³ is source m³
    # per hourly row (NOT dry-normal Nm³). Heat rate GJ/h -> GJ per hour.
    elec_hours=counts["observed_engine_electrical_kw"]
    gas_hours=counts["observed_engine_gas_m3_per_hour"]
    paired=counts["paired_electric_gas_hours"]
    return {
      "protocol":PROTOCOL,"case":"KITAKYUSHU_2005_CITY_GAS_GAS_ENGINE",
      "year":YEAR,"source_fuel":"CITY_GAS_NOT_BIOGAS",
      "engine_technology":"RECIPROCATING_GAS_ENGINE",
      "source_doi":"10.6084/m9.figshare.24978645.v2",
      "measurements":"ACTUAL_PUBLISHED_SOURCE_VALUES",
      "time_semantics":"SOURCE_REPORTED_NAIVE_HOURLY_LOCAL_TIME_NO_ASSUMED_UTC_OFFSET",
      "matched_source_records":len(expected),
      "counts":dict(counts),
      "observed_source_sums":{
         "engine_electricity_kwh_hourly_integral":round(sums["engine_electrical_kw"],6),
         "gas_engine_fuel_source_m3_hourly_sum":round(sums["engine_gas_m3_per_hour"],6),
         "gas1_recovered_heat_gj_hourly_integral":round(sums["gas1_recovery_gj_per_hour"],6),
         "gas2_recovered_heat_gj_hourly_integral":round(sums["gas2_recovery_gj_per_hour"],6),
      },
      "observed_source_maxima":peaks,
      "monthly_observed_source_totals":[{
            "month":month,
            **{k:round(v,6) if isinstance(v,float) else v for k,v in sorted(values.items())}
        } for month,values in sorted(by_month.items())],
      "source_measurement_coverage":{
         "electric_hour_fraction":round(elec_hours/8760,8),
         "gas_hour_fraction":round(gas_hours/8760,8),
         "electric_gas_paired_hour_fraction":round(paired/8760,8),
      },
      "sample_flagged_records":examples,
      "city_gas_lhv_authenticated":False,
      "city_gas_standard_state_confirmed":False,
      "gas_heat_1_2_direct_engine_allocation_confirmed":False,
      "physical_fuel_to_electric_efficiency_calculated":False,
      "physical_first_law_energy_balance_calculated":False,
      "direct_biogas_engine_parameter_validation":False,
      "subhour_plant_ramp_inferred":False,
      "observational_claim":"Descriptive 2005 published KITAKYUSHU city-gas records only",
      "status":"PASS_REAL_SOURCE_HOURLY_CHANNEL_RECONCILIATION_WITH_UNRESOLVED_METROLOGY",
    }

def run(fetch:bool=False,report_path:Path|None=None,raws:dict[str,bytes]|None=None)->dict:
    require(fetch or raws is not None,
            "Actual published source data are required: choose --fetch; no mock analysis")
    require(not(fetch and raws is not None),"Use network or supplied pinned bytes, not both")
    if fetch:
        reg=checked_registry()
        site=next(x for x in reg["sources"] if x["id"]=="kitakyushu_japan_2001_2022_citygas_chp")
        raws={f["name"]:fetch_once(f) for f in site["files"]}
    report=analyse_frames(_decode_bundle(raws))
    report["original_zip_sha256"]=dict(PINNED_SHA256)
    report["source_authenticity_verified_by_provider_md5_and_sha256"]=True
    if report_path is not None:
        dest=Path(report_path).resolve()
        require(not dest.is_relative_to(ROOT.resolve()),
                "Real source analysis reports must remain outside repository checkout")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf8")
    return report

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch",action="store_true")
    parser.add_argument("--report",type=Path,default=None)
    args=parser.parse_args()
    print(json.dumps(run(args.fetch,args.report),indent=2,allow_nan=False))

if __name__=="__main__":
    main()
