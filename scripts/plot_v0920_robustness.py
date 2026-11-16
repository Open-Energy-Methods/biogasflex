"""Create four auditable SVG figures from completed v0.9.20 synthetic study.

All values are hypothetical normalized EUR/hour, not market profit.
Pure Python stdlib. Figures and complete reports remain in GitHub Actions
artifacts OUTSIDE the checked-out source tree.
"""
from __future__ import annotations

import argparse
from html import escape
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL="BIOGASFLEX_V0920_RECTANGULAR_PRICE_UNCERTAINTY_HELDOUT_REPLAY_V1"
CLASSES=("reference","wide_stress")
GROUPS=((11,24),(11,96),(11,192),(37,24),(37,96),(37,192))

def _pairs(study:dict,band:str,metric:str)->list[tuple[str,float,float]]:
    if study.get("protocol")!=PROTOCOL or not study.get("status","").startswith(
       "PASS_SYNTHETIC_FROZEN_POLICY_BOUNDED_"):
        raise ValueError("Not a complete v0.9.20 synthetic study")
    if len(study.get("cases",[]))!=14 or len(
        study.get("selected_holdout_descriptive_comparisons",[]))!=12:
        raise ValueError("Incomplete synthetic two-band source")
    if study.get("price_stress_classes")!=list(CLASSES):
        raise ValueError("Missing either reference or widened price stress")
    if any(study.get("claims",{}).values()):
        raise ValueError("Unsupported claim of real measured data")
    rows=study["selected_holdout_descriptive_comparisons"]
    keys={
        "worst_case":(
            "nominal_exact_rectangular_worst_case_eur",
            "robust_exact_rectangular_worst_case_eur"),
        "selected_heldout_mean":(
            "nominal_arithmetic_heldout_mean_eur",
            "robust_arithmetic_heldout_mean_eur"),
    }
    if metric not in keys:raise ValueError("Invalid source metric")
    if band not in CLASSES:raise ValueError("Invalid source stress band")
    a,b=keys[metric]
    out=[]
    for seed,slots in GROUPS:
        selected=[r for r in rows if r["train_seed"]==seed
                  and r["slots"]==slots and r["price_bound_class"]==band]
        if len(selected)!=1:raise ValueError("Missing/duplicate scenario cell")
        r=selected[0]
        if r["average_refers_only_to_3_selected_nonprobabilistic_holdout_paths"] is not True:
            raise ValueError("False probability distribution claim")
        v1,v2=r[a]/(slots*.25),r[b]/(slots*.25)
        if not math.isfinite(v1) or not math.isfinite(v2):
            raise ValueError("Nonfinite figure source")
        out.append((f"{seed} · {slots//4}h",v1,v2))
    return out

def svg(rows:list[tuple[str,float,float]],band:str,metric:str)->str:
    width,height=930,480
    left,right,top,bottom=85,35,102,100
    plotw=width-left-right;ploth=height-top-bottom
    nums=[v for _,a,b in rows for v in (a,b)]
    low=min(0,min(nums)*1.1);high=max(0,max(nums)*1.13)
    if high-low<.1:raise ValueError("Missing economic variation")
    def y(v):return top+(high-v)/(high-low)*ploth
    def esc(v):return escape(v)
    title=("Guaranteed worst-case contribution" if metric=="worst_case" else
           "Selected held-out arithmetic mean contribution")
    subtitle=("Exact mathematical price-rectangle lower vertex"
              if metric=="worst_case" else
              "Exactly 3 deterministic held-out paths, NOT an expected-value estimate")
    lines=[
      f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}, {esc(band)}">',
      '<rect width="100%" height="100%" fill="#ffffff"/>',
      f'<text x="{left}" y="35" font-size="23" font-family="Arial,sans-serif" font-weight="bold" fill="#192d46">{esc(title)} — {esc(band)}</text>',
      f'<text x="{left}" y="60" font-size="13" font-family="Arial,sans-serif" fill="#43566b">{esc(subtitle)}</text>',
      f'<text x="{left}" y="80" font-size="12" font-family="Arial,sans-serif" fill="#546579">All money is entirely synthetic; normalized EUR per modeled operating hour, not plant profit.</text>',
    ]
    for k in range(5):
        level=low+(high-low)*k/4
        yp=y(level)
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{yp:.1f}" y2="{yp:.1f}" stroke="#e6e9ee"/>')
        lines.append(f'<text x="{left-10}" y="{yp+4:.1f}" font-size="12" font-family="Arial,sans-serif" fill="#405069" text-anchor="end">{level:.1f}</text>')
    zero=y(0)
    lines.append(f'<line x1="{left}" x2="{width-right}" y1="{zero:.1f}" y2="{zero:.1f}" stroke="#555b63" stroke-width="1.5"/>')
    widthgroup=plotw/len(rows);bar=widthgroup*.30
    for i,(name,a,b) in enumerate(rows):
        cx=left+(i+.5)*widthgroup
        for j,val in enumerate((a,b)):
            x=cx-bar-2 if j==0 else cx+2
            yt=y(val)
            lines.append(f'<rect x="{x:.1f}" y="{min(yt,zero):.1f}" width="{bar:.1f}" height="{max(1,abs(zero-yt)):.1f}" fill="{("#306a9b" if j==0 else "#b17432")}"/>')
        lines.append(f'<text x="{cx:.1f}" y="{height-bottom+20}" font-size="12" font-family="Arial,sans-serif" fill="#394b65" text-anchor="middle">{esc(name)}</text>')
    lines.extend([
      f'<rect x="{left}" y="{height-65}" width="13" height="13" fill="#306a9b"/>',
      f'<text x="{left+20}" y="{height-54}" font-size="12" font-family="Arial,sans-serif" fill="#263d56">Nominal ex-ante MILP</text>',
      f'<rect x="{left+230}" y="{height-65}" width="13" height="13" fill="#b17432"/>',
      f'<text x="{left+250}" y="{height-54}" font-size="12" font-family="Arial,sans-serif" fill="#263d56">Rectangular maximin MILP</text>',
      f'<text x="{left}" y="{height-26}" font-size="11" font-family="Arial,sans-serif" fill="#687688">Scenario seed / horizon · Source: BiogasFlex v0.9.20 original solver and separately audited synthetic JSON</text>',
      '</svg>'
    ])
    return "\n".join(lines)+"\n"

def render(study:dict,out_dir:Path)->list[Path]:
    dest=Path(out_dir).resolve()
    if dest.is_relative_to(ROOT.resolve()):
        raise ValueError("Research SVGs must be OUTSIDE the source checkout")
    # Validate all four source sets BEFORE creating any output.
    inputs=[(band,metric,_pairs(study,band,metric))
            for band in CLASSES for metric in ("worst_case","selected_heldout_mean")]
    dest.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for band,metric,rows in inputs:
        path=dest/f"v0920_{band}_{metric}_normalized.svg"
        path.write_text(svg(rows,band,metric),encoding="utf8")
        outputs.append(path)
    return outputs

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    opts=p.parse_args()
    payload=json.loads(opts.report.read_text(encoding="utf8"))
    print(json.dumps({"generated_synthetic_figures":[p.name for p in render(payload,opts.out_dir)],
                      "actual_price_forecast_or_real_plant":False},indent=2))
