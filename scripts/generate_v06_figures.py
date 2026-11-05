"""Recreate version 0.6 figures/tables from recorded JSON results (no solver necessary)."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/v0.6'
FIG = OUT/'figures'
FIG.mkdir(parents=True, exist_ok=True)


def load(name):
    return json.loads((OUT/name).read_text(encoding='utf-8'))


def output_figure(fig,name):
    fig.savefig(FIG/name,dpi=175)
    plt.close(fig)


def plot_case(name,slug):
    d=load(name)
    rows=d['input_profile']
    x=list(range(len(rows)))
    title = 'Lövsta cross-year counterfactual' if slug.startswith('lovsta') else 'Synthetic two-period oracle'
    fig,ax=plt.subplots(figsize=(8.5,3.7),constrained_layout=True)
    ax.plot(x,[r['fixed_chp_power_mw_e']*1000 for r in rows],label='Fixed CHP output',marker='o',markersize=2)
    ax.plot(x,[r['optimized_chp_power_mw_e']*1000 for r in rows],label='Flexible CHP output',marker='.',markersize=3)
    ax.set_xlabel('Interval index (chronological UTC; consult source CSV for time)')
    ax.set_ylabel('Gross generator electric output (kW)')
    ax.set_title(title+' — hypothetical electricity output')
    ax.grid(alpha=.2)
    ax.legend(loc='best')
    output_figure(fig,slug+'_generation.png')

    fig,ax=plt.subplots(figsize=(8.5,3.6),constrained_layout=True)
    ax.step(range(len(rows)+1),[rows[0]['stock_start_mwh_lhv']]+[r['stock_end_mwh_lhv'] for r in rows],where='post')
    ax.set_xlabel('Interval boundary')
    ax.set_ylabel('Gas buffer inventory (MWh LHV)')
    ax.set_ylim(bottom=0)
    ax.set_title(title+' — cyclic gas storage')
    ax.grid(alpha=.2)
    output_figure(fig,slug+'_inventory.png')

    with (OUT/(slug+'_intervals.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_sweep(name,slug):
    d=load(name)
    rows=d['cases']
    title = 'Lövsta cross-year counterfactual' if slug.startswith('lovsta') else 'Synthetic two-period oracle'
    fig,ax=plt.subplots(figsize=(8.5,3.7),constrained_layout=True)
    ax.plot([r['capacity_mwh_lhv'] for r in rows],[r['incremental_gross_revenue_eur'] for r in rows],marker='o')
    ax.set_xlabel('Hypothetical gas-storage capacity (MWh LHV)')
    ax.set_ylabel('Incremental gross value (EUR / horizon)')
    ax.set_title(title+' — storage sweep (perfect foresight)')
    ax.grid(alpha=.2)
    output_figure(fig,slug+'_storage_sweep.png')
    with (OUT/(slug+'_storage_sweep.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


if __name__=='__main__':
    plot_case('oracle.json','synthetic_oracle')
    plot_sweep('oracle_sweep.json','synthetic_oracle')
    plot_case('lovsta_counterfactual.json','lovsta_crossyear_counterfactual')
    plot_sweep('lovsta_storage_sweep.json','lovsta_crossyear_counterfactual')
    print('Created v0.6 figures and CSV tables in',OUT)
