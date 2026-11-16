"""v0.9.21 source-verified Swedish SE3 OPSD load-forecast-error evidence.

Original OPSD 2020-10-06 60-minute CSV has a source-published SHA256.
The day-ahead load forecast is an ENTSO-E *reported forecast* without
per-observation as-of/vintage history. Day-ahead price is an AUCTION
PRICE, NOT a price forecast. This program constructs a strictly lagged,
transparent 7-day *research persistence forecast* for price and scores
its errors separately. It does not infer actual gas or district heat
forecast errors, and it makes no gate-closure timing claims.
"""
from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
import tempfile
import urllib.request

SOURCE_URL="https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv"
SOURCE_SHA256="6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"
SOURCE_CHECKSUM_REPO="https://github.com/Open-Power-System-Data/time_series/blob/master/checksums.txt"
SOURCE_RELEASE="https://doi.org/10.25832/time_series/2020-10-06"
PROTOCOL="BIOGASFLEX_V0921_OPSD_SE3_REPORTED_LOAD_VS_ACTUAL_PRICE_PERSISTENCE_V1"
COL_TIME="utc_timestamp"
COL_LOAD_FORECAST="SE_3_load_forecast_entsoe_transparency"
COL_LOAD_ACTUAL="SE_3_load_actual_entsoe_transparency"
COL_PRICE="SE_3_price_day_ahead"
COLUMNS=(COL_TIME,COL_LOAD_FORECAST,COL_LOAD_ACTUAL,COL_PRICE)
START=datetime(2019,1,1,tzinfo=timezone.utc)
END=datetime(2020,1,1,tzinfo=timezone.utc)
TRAIN_END=datetime(2019,10,1,tzinfo=timezone.utc)
MAX_RAW_BYTES=250_000_000

def demand(condition,why):
    if not condition:raise ValueError("v0.9.21 OPSD: "+why)

def download_verified(destination:Path,*,allow_network:bool=False)->dict:
    """Network must be explicitly authorized by caller; never trust path/name."""
    demand(allow_network,"Use --download to authorize a 124-MB public source fetch")
    destination=Path(destination).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    hash_ = hashlib.sha256();size=0
    with tempfile.NamedTemporaryFile(
        mode="wb",dir=destination.parent,delete=False,
        prefix="opsd-v0921-",suffix=".tmp"
    ) as handle:
        partial=Path(handle.name)
        try:
            req=urllib.request.Request(
                SOURCE_URL,headers={"User-Agent":"BiogasFlex-scientific-audit/0.9.21"})
            with urllib.request.urlopen(req,timeout=75) as source:
                while True:
                    chunk=source.read(1024*1024)
                    if not chunk:break
                    size+=len(chunk)
                    demand(size<=MAX_RAW_BYTES,"Remote source exceeds 250 MB cap")
                    hash_.update(chunk);handle.write(chunk)
            digest=hash_.hexdigest()
            demand(digest==SOURCE_SHA256,
                   f"Publisher SHA-256 mismatch: {digest}; refusing data")
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
    partial.replace(destination)
    return {"verified_full_source_sha256":digest,"downloaded_bytes":size,
            "publisher_checksum_url":SOURCE_CHECKSUM_REPO,
            "original_publisher_release_url":SOURCE_RELEASE}

def _check_sha(path:Path)->int:
    h=hashlib.sha256();n=0
    with Path(path).open("rb") as fp:
        for block in iter(lambda:fp.read(1024*1024),b""):
            h.update(block);n+=len(block)
            demand(n<=MAX_RAW_BYTES,"Oversize input is not OPSD 60-minute CSV")
    demand(h.hexdigest()==SOURCE_SHA256,
           "Input raw CSV SHA-256 differs from OPSD's independently published source checksum")
    return n

def _number(text:str)->float|None:
    if not text or text.strip().lower() in ("nan","null","na"):
        return None
    try:x=float(text)
    except (TypeError,ValueError):return None
    return x if math.isfinite(x) else None

def _timestamp(v:str)->datetime:
    try:stamp=datetime.strptime(v,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as ex:raise ValueError("Invalid OPSD explicit UTC timestamp") from ex
    return stamp

def _metric(records:list[dict])->dict:
    pairs=[(x["price_persistence_error_eur_mwh"],
            x["published_load_forecast_error_relative"])
           for x in records]
    p=[x for x,_ in pairs];h=[y for _,y in pairs]
    n=len(p)
    demand(n>=200,"Too few source-verified hourly forecast-error pairs")
    mp=mean(p);mh=mean(h)
    cp=sum((x-mp)*(y-mh) for x,y in pairs)
    pp=sum((x-mp)**2 for x in p);hh=sum((y-mh)**2 for y in h)
    corr=cp/(pp*hh)**.5 if pp>0 and hh>0 else None
    return {
        "count_hourly_paired_errors":n,
        "price_lag_7day_baseline_MAE_eur_mwh":mean(abs(x) for x in p),
        "price_lag_7day_baseline_RMSE_eur_mwh":mean(x*x for x in p)**.5,
        "price_lag_7day_baseline_mean_error_eur_mwh":mp,
        "published_TSO_load_forecast_MAE_relative":mean(abs(x) for x in h),
        "published_TSO_load_forecast_RMSE_relative":mean(x*x for x in h)**.5,
        "published_TSO_load_forecast_mean_relative_error":mh,
        "empirical_price_persistence_vs_regional_load_error_Pearson":corr,
        "covariance_sample_unit":"EUR/MWh_e vs relative regional SE3 electric demand",
        "heat_or_biogas_error_empirically_observed":False,
        "price_model_original_provider_forecast":False,
        "load_publication_vintage_exactly_at_gate_verified":False,
    }

def _complete_days(records:list[dict])->list[dict]:
    by_day={}
    for row in records:
        day=row["timestamp_utc"][:10]
        by_day.setdefault(day,[]).append(row)
    complete=[]
    for day,rows in sorted(by_day.items()):
        rows.sort(key=lambda r:r["timestamp_utc"])
        if len(rows)!=24:continue
        day_dt=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        if all(rows[i]["timestamp_utc"]==
               (day_dt+timedelta(hours=i)).isoformat() for i in range(24)):
            complete.append({
                "date_utc":day,
                "partition":"TRAIN_PRIOR_TO_2019_10_01" if day_dt<TRAIN_END else
                            "HOLDOUT_FROM_2019_10_01",
                "price_baseline_error_eur_mwh":[r["price_persistence_error_eur_mwh"]
                                              for r in rows],
                "regional_load_error_relative":[r["published_load_forecast_error_relative"]
                                                for r in rows],
                "delivery_price_eur_mwh":[r["day_ahead_clearing_price_eur_mwh"]
                                          for r in rows],
                "regional_load_forecast_mw":[r["published_tso_load_forecast_mw"]
                                             for r in rows],
                "regional_load_actual_mw":[r["reported_actual_electric_load_mw"]
                                           for r in rows],
            })
    return complete

def analyze(path:Path)->dict:
    size=_check_sha(path)
    known={};raw_seen=set()
    issues=Counter()
    with Path(path).open("r",encoding="utf-8-sig",newline="") as fp:
        reader=csv.DictReader(fp)
        demand(reader.fieldnames is not None and
               all(c in reader.fieldnames for c in COLUMNS),
               "Publisher source missing an explicitly registered SE3 field")
        for row in reader:
            stamp=_timestamp(row[COL_TIME])
            if not (datetime(2018,12,1,tzinfo=timezone.utc)<=stamp<END):
                continue
            stamp_key=stamp.isoformat()
            demand(stamp_key not in raw_seen,"Duplicate source UTC hourly timestamp")
            raw_seen.add(stamp_key)
            demand(stamp.minute==0 and stamp.second==0,
                   "Source is not 60-minute UTC data")
            p=_number(row[COL_PRICE]);a=_number(row[COL_LOAD_ACTUAL])
            f=_number(row[COL_LOAD_FORECAST])
            if p is None:issues["missing_price"]+=1
            if a is None:issues["missing_actual_load"]+=1
            if f is None:issues["missing_published_load_forecast"]+=1
            if p is None:continue
            known[stamp_key]=(p,a,f)
    records=[]
    for stamp_key,values in sorted(known.items()):
        stamp=datetime.fromisoformat(stamp_key)
        if not (START<=stamp<END):continue
        price,actual,forecast=values
        if actual is None or forecast is None or forecast<=0 or actual<=0:
            issues["incomplete_or_nonpositive_load_pair"]+=1;continue
        lag=(stamp-timedelta(days=7)).isoformat()
        if lag not in known:
            issues["missing_lagged_7day_price"]+=1;continue
        lagged=known[lag][0]
        error=(actual-forecast)/forecast
        if not -1.<error<1.:
            issues["implausible_regional_load_ratio"]+=1;continue
        records.append({
            "timestamp_utc":stamp_key,
            "day_ahead_clearing_price_eur_mwh":price,
            "price_persistence_baseline_eur_mwh":lagged,
            "price_persistence_error_eur_mwh":price-lagged,
            "published_tso_load_forecast_mw":forecast,
            "reported_actual_electric_load_mw":actual,
            "published_load_forecast_error_relative":error,
        })
    demand(len(records)>4000,"Too few aligned source-verified SE3 2019 observations")
    complete=_complete_days(records)
    train=[r for r in records if r["timestamp_utc"]<TRAIN_END.isoformat()]
    held=[r for r in records if r["timestamp_utc"]>=TRAIN_END.isoformat()]
    train_days=[d for d in complete if d["partition"].startswith("TRAIN_")]
    held_days=[d for d in complete if d["partition"].startswith("HOLDOUT_")]
    demand(len(train_days)>=100 and len(held_days)>=30,
           "Insufficient complete UTC days for leakage-safe calendar holdout")
    return {
        "protocol":PROTOCOL,"status":"SOURCE_SHA256_VERIFIED_REPORTED_FORECAST_ERROR_SNAPSHOT_NOT_GATE_VINTAGE",
        "source":{"dataset":"Open Power System Data time_series 2020-10-06",
                  "upstream_file":SOURCE_URL,
                  "upstream_release":SOURCE_RELEASE,
                  "checksum_registry":SOURCE_CHECKSUM_REPO,
                  "sha256":SOURCE_SHA256,
                  "raw_original_bytes":size,
                  "geography":"Sweden SE3 bidding zone",
                  "source_resolution":"60 minutes",
                  "source_start_utc":"2019-01-01T00:00:00+00:00",
                  "source_end_exclusive_utc":"2020-01-01T00:00:00+00:00",
                  "license":"OPSD CC BY 4.0 where applicable; underlying source conditions apply",
                  "last_per_observation_forecast_publication_verified":False,
                  "actual_load_as_of_gate_available":False,
                  "electricity_price_original_forecast_column_available":False,
                  "gas_production_or_heat_load_site_measurement_present":False},
        "interpretation":{
            "real_forecast_error":"published day-ahead ENTSO-E regional electrical load forecast vs archived actual SE3 load",
            "synthetic_price_forecast_error":"observed day-ahead clearing price minus 7-day lagged price persistence baseline; NO original vendor price forecast",
            "not_site_heat":"regional electric load is NOT a measured CHP end-use heat demand",
            "price_bid_gate_eligibility":"7-day-lagged clearing price only (historical), not contemporaneous realized price",
            "as_of_warning":"OPSD harmonized final archive not per-record vintage log; cannot prove exact last forecast version before auction gate.",
            "time_basis":"UTC 60-minute raw source; 15-minute optimizer inputs require explicit 4× forward-hold, NOT four observations",
        },
        "quality":{"skipped_and_missing_counts":dict(issues),
                   "distinct_hourly_2019_aligned":len(records),
                   "complete_contiguous_UTC_24hour_blocks":len(complete),
                   "training_complete_days":len(train_days),
                   "heldout_complete_days":len(held_days)},
        "training_metrics":_metric(train),
        "heldout_metrics":_metric(held),
        "complete_days":complete,
        "nonredistribution_warning":"Upstream values are embedded only in untracked research output; check upstream redistribution terms before publishing artifacts",
    }

def write_out(result,path:Path,repo_root:Path|None=None)->None:
    target=Path(path).resolve()
    if repo_root is not None:
        demand(not target.is_relative_to(repo_root.resolve()),"Output must be OUTSIDE checked-out repository")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv",type=Path,required=True)
    p.add_argument("--download",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    if opts.download:
        download_verified(opts.csv,allow_network=True)
    result=analyze(opts.csv)
    write_out(result,opts.output,Path(__file__).resolve().parents[2])
    print(json.dumps({
        "status":result["status"],
        "source_SHA256":result["source"]["sha256"],
        "training":result["training_metrics"],
        "holdout":result["heldout_metrics"],
        "source_quality":result["quality"],
        "physical_gas_heat_measurements_available":False,
        "source_archive_preserves_exact_historical_forecast_vintage":False,
    },indent=2,allow_nan=False))

if __name__=="__main__":
    main()
