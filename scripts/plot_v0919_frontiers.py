"""Portable vector frontier plots from the frozen v0.9.19 synthetic design.

Never display these operational-design tradeoffs as physical reliability,
actual equipment uptime, economic NPV or uncertainty probability.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

PROTOCOL="BIOGASFLEX_V0919_ENDOGENOUS_COMMITMENT_FINITE_DESIGN_AND_DUAL_V1"
ROOT=Path(__file__).resolve().parents[1]
PALETTE={0.0:"#74808c",.5:"#22659a",1.5:"#b16a30"}

def draw(payload:dict,out_dir:Path)->list[Path]:
    if payload.get("protocol")!=PROTOCOL or payload.get("status")!=(
        "SOLVED_FINITE_SYNTHETIC_COMMITMENT_FRONTIERS_PENDING_INDEPENDENT_CERTIFICATION"):
        raise ValueError("Only the versioned, completed synthetic study can be rendered")
    if payload.get("claims",{}).get("real_plant_measurements_used") is not False:
        raise ValueError("A real plant report cannot be treated as a synthetic frontier")
    dest=Path(out_dir).resolve()
    if dest.is_relative_to(ROOT.resolve()):
        raise ValueError("Figures must be written outside repository checkout")
    if len(payload.get("cases",[]))!=46 or len(payload.get("frontiers",[]))!=3:
        raise ValueError("Incomplete finite design")
    if len({c["seed"] for c in payload["frontiers"]})!=3:
        raise ValueError("Duplicated seed frontier")
    dest.mkdir(parents=True,exist_ok=True)
    paths=[]
    width,height=920,570
    left,right,top,bottom=100,38,94,118
    chartw=width-left-right;charth=height-top-bottom
    for frontier in payload["frontiers"]:
        seed=frontier["seed"]
        cases=[c for c in payload["cases"]
               if c["seed"]==seed and c["slots"]==24
               and c["model"]=="ENDOGENOUS_ON_OFF_MILP"
               and c["startup_cost_eur"]==5.]
        if len(cases)!=6:raise ValueError("Incomplete seed-specific design frontier")
        vals=[c["reported_net_objective_eur"] for c in cases]
        ymin=min(vals)-8.;ymax=max(vals)+8.
        ymaxbackup=max(c["auxiliary_heat_fraction_of_demand"] for c in cases)
        xmax=max(.45,ymaxbackup+.05)
        pareto={(round(c["capacity_mwh_lhv"],6),
                 round(c["auxiliary_capacity_mw_th"],6))
                for c in frontier["nondominated_candidates"]}
        def xy(c):
            x=left+c["auxiliary_heat_fraction_of_demand"]/xmax*chartw
            y=top+charth-(c["reported_net_objective_eur"]-ymin)/(ymax-ymin)*charth
            return x,y
        a=[
         f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Synthetic CHP operational-design tradeoff seed {seed}">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{left}" y="38" font-size="24" font-family="Arial,sans-serif" fill="#142b45" font-weight="bold">Finite CHP flexibility design — seed {seed}</text>',
         f'<text x="{left}" y="62" font-size="13" font-family="Arial,sans-serif" fill="#48566c">Invented six-hour model inputs; larger net contribution vs less backup heat dependence</text>',
        ]
        for k in range(5):
            frac=k/4
            py=top+charth*(1-frac)
            a.append(f'<line x1="{left}" x2="{width-right}" y1="{py:.2f}" y2="{py:.2f}" stroke="#e2e8ef"/>')
            a.append(f'<text x="{left-10}" y="{py+5:.2f}" font-size="12" fill="#43536a" font-family="Arial,sans-serif" text-anchor="end">{ymin+(ymax-ymin)*frac:.0f}</text>')
            px=left+chartw*frac
            a.append(f'<line x1="{px:.2f}" x2="{px:.2f}" y1="{top}" y2="{top+charth}" stroke="#edf1f4"/>')
            a.append(f'<text x="{px:.2f}" y="{top+charth+24}" font-size="12" fill="#43536a" font-family="Arial,sans-serif" text-anchor="middle">{100*xmax*frac:.0f}%</text>')
        a.append(f'<text x="{left}" y="{height-63}" font-size="13" font-family="Arial,sans-serif" fill="#293e55">External-backup heat fraction of demand (modelled, not real reliability)</text>')
        a.append(f'<text x="{left}" y="{height-43}" font-size="12" font-family="Arial,sans-serif" fill="#43536a">Y axis: hypothetical net operating contribution (EUR). Colour: gas buffer size, radius: restart count.</text>')
        a.append(f'<text x="{left}" y="{height-23}" font-size="12" font-family="Arial,sans-serif" fill="#43536a">C=0: grey    C=0.5 MWh: blue    C=1.5 MWh: brown. Black ring = non-dominated finite-design candidate.</text>')
        # Descriptive measured numerical diagram. No fitted physical datapoints.
        for i,c in enumerate(cases):
            x,y=xy(c)
            cap=c["capacity_mwh_lhv"]
            primary=(round(cap,6),
                    round(c["auxiliary_capacity_mw_th"],6)) in pareto
            col=PALETTE[cap]
            radius=6+2.2*c["start_count"]
            if primary:a.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius+4:.2f}" fill="none" stroke="#212e43" stroke-width="2"/>')
            a.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{col}" fill-opacity="0.9"/>')
            if i%2==0:
                offset=-17
            else:
                offset=20
            txt=f'C={cap:g}, aux={c["auxiliary_capacity_mw_th"]:g}, starts={c["start_count"]}'
            a.append(f'<text x="{x+9:.2f}" y="{y+offset:.2f}" font-size="10" font-family="Arial,sans-serif" fill="#24344c">{escape(txt)}</text>')
        a.append('</svg>')
        target=dest/f'v0919_seed{seed}_synthetic_operational_frontier.svg'
        target.write_text("\n".join(a)+"\n",encoding="utf8")
        paths.append(target)
    return paths

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    args=p.parse_args()
    report=json.loads(args.report.read_text(encoding="utf8"))
    paths=draw(report,args.out_dir)
    print(json.dumps({"plots":[x.name for x in paths],
                      "real_plant_reliability_estimate":False},indent=2))
