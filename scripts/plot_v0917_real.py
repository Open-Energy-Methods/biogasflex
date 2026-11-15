"""Create portable vector plots only from the integrity-checked REAL Kitakyushu study.

Usage:
 python scripts/plot_v0917_real.py --report /tmp/kitakyushu_measured_2005_analysis.json --out-dir /tmp/kitakyushu_plots

No source data, plot, or downloaded provider file is written into git checkout.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
STATUS="PASS_REAL_SOURCE_HOURLY_CHANNEL_RECONCILIATION_WITH_UNRESOLVED_METROLOGY"
PROTOCOL="BIOGASFLEX_V0917_KITAKYUSHU_HOURLY_REAL_DATA_V1"

def verify_report(data):
    if not isinstance(data,dict) or data.get("protocol")!=PROTOCOL or data.get("status")!=STATUS:
        raise ValueError("Only completed measured Kitakyushu real source reports can be plotted")
    if data.get("source_fuel")!="CITY_GAS_NOT_BIOGAS" or not data.get("source_authenticity_verified_by_provider_md5_and_sha256"):
        raise ValueError("Unverified original source file or substituted biogas scenario")
    if data.get("matched_source_records")!=8760:
        raise ValueError("Incomplete source-local 2005 calendar")
    months=data.get("monthly_observed_source_totals",[])
    if not isinstance(months,list) or len(months)!=12 or [m.get("month") for m in months]!=[f"{m:02d}" for m in range(1,13)]:
        raise ValueError("Source monthly records are missing or reordered")
    n=sum(m.get("source_hourly_records",0) for m in months)
    e=sum(m.get("generator_electric_kwh",0) for m in months)
    g=sum(m.get("source_engine_gas_m3",0) for m in months)
    if n!=8760 or abs(e-data["observed_source_sums"]["engine_electricity_kwh_hourly_integral"])>1e-5 or abs(g-data["observed_source_sums"]["gas_engine_fuel_source_m3_hourly_sum"])>1e-5:
        raise ValueError("Monthly measured-source audit does not reconcile to annual real report")
    return months

def svg_chart(months,field,label,unit,scale,subtitle):
    width,height=840,425
    left,right,top,bottom=90,35,86,84
    plot_w=width-left-right
    plot_h=height-top-bottom
    values=[float(m.get(field,0.0))*scale for m in months]
    maximum=max(values)*1.13 if max(values)>0 else 1.
    ticks=[maximum*i/4 for i in range(5)]
    def y(v):return top+plot_h-v/maximum*plot_h
    def x(i):return left+(i+.5)*plot_w/12
    out=[
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="32" font-family="Arial,sans-serif" font-size="21" fill="#16243e" font-weight="bold">{escape(label)}</text>',
        f'<text x="{left}" y="54" font-family="Arial,sans-serif" font-size="12" fill="#3b4559">{escape(subtitle)}</text>',
    ]
    for v in ticks:
        yp=y(v)
        out.append(f'<line x1="{left}" y1="{yp:.2f}" x2="{width-right}" y2="{yp:.2f}" stroke="#e4e7eb"/>')
        out.append(f'<text x="{left-8}" y="{yp+4:.2f}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#49566b">{v:.0f}</text>')
    for i,value in enumerate(values):
        xp=x(i)
        bar_w=plot_w/12*.63
        out.append(f'<rect x="{xp-bar_w/2:.2f}" y="{y(value):.2f}" width="{bar_w:.2f}" height="{max(0,top+plot_h-y(value)):.2f}" fill="#255c93"/>')
        out.append(f'<text x="{xp:.2f}" y="{height-bottom+19}" font-family="Arial,sans-serif" font-size="11" text-anchor="middle" fill="#49566b">{i+1:02d}</text>')
    out.extend([
        f'<text x="{left}" y="{height-24}" font-family="Arial,sans-serif" font-size="12" fill="#49566b">Source-local month (2005) · {escape(unit)}</text>',
        '<text x="90" y="415" font-family="Arial,sans-serif" font-size="10" fill="#717c8e">Liao, Jin &amp; Li (2024), Figshare CC BY 4.0; source measurements, no biogas-engine model calibration</text>',
        '</svg>',
    ])
    return "\n".join(out)+"\n"

def run(report:Path,out_dir:Path):
    data=json.loads(Path(report).read_text(encoding="utf8"))
    months=verify_report(data)
    dest=Path(out_dir).resolve()
    if dest.is_relative_to(ROOT.resolve()):
        raise ValueError("Real-source figure outputs cannot be written into version-controlled checkout")
    dest.mkdir(parents=True,exist_ok=True)
    specs=[
       ("engine_electricity_mwh.svg","generator_electric_kwh","Gas-engine electrical generation","MWhₑ (generator source)",.001,"Published hourly power source, nominal one-hour integration"),
       ("engine_gas_source_m3.svg","source_engine_gas_m3","Engine gas consumption","source m³ (not certified dry Nm³)",1.,"Literal measured source volume; gas heating value unknown"),
       ("electric_gas_conflict_hours.svg","generator_zero_gas_positive_hours","Gas-positive / generator-zero hours","number of source-hour records",1.,"Measurement boundary / source QA warning, not verified startup events"),
    ]
    outputs=[]
    for filename,field,label,unit,scale,subtitle in specs:
        target=dest/filename
        target.write_text(svg_chart(months,field,label,unit,scale,subtitle),encoding="utf8")
        outputs.append(target.name)
    return outputs

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.report,a.out_dir),indent=2))
