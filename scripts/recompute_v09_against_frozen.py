"""Clean isolated re-execution of all v0.8 scenario LPs against packaged v0.9 results.

Uses a temporary directory, never overwrites the packaged published outputs.
Does not depend on matplotlib or the network. Unlike the standard-library
ledger auditor this step requires the SciPy/HiGHS optimizer.
"""
from __future__ import annotations
import csv,json,math,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def rows(path):
    with path.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))

def check_equal_numeric(a,b,field,case,tol=2e-6):
    x=float(a);y=float(b)
    if not (math.isfinite(x) and math.isfinite(y) and abs(x-y)<=tol):
        raise RuntimeError(f'{case}/{field}: regenerated={x}, packaged={y}')

def verify():
    with tempfile.TemporaryDirectory(prefix='biogasflex-v09-recompute-') as td:
        dst=Path(td)
        for path in ['config','data','scenarios','src']:
            shutil.copytree(ROOT/path,dst/path,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (dst/'scripts').mkdir()
        shutil.copy2(ROOT/'scripts/run_v08_study.py',dst/'scripts/run_v08_study.py')
        env=os.environ.copy();env['PYTHONPATH']=str(dst/'src')+os.pathsep+env.get('PYTHONPATH','')
        proc=subprocess.run([sys.executable,str(dst/'scripts/run_v08_study.py')],cwd=dst,
            env=env,text=True,capture_output=True,timeout=100)
        if proc.returncode:raise RuntimeError('Clean scenario recomputation failed: '+proc.stdout[-1000:]+proc.stderr[-2000:])
        orig=ROOT/'results/v0.8';fresh=dst/'results/v0.8'
        o=rows(orig/'predeclared_scenario_matrix_results.csv')
        n=rows(fresh/'predeclared_scenario_matrix_results.csv')
        if len(o)!=216 or len(n)!=216:raise RuntimeError('Recomputed market cases incomplete')
        for a,b in zip(o,n):
            if a['case_id']!=b['case_id']:raise RuntimeError('Recomputed case ID order changed')
            for key in ['fixed_value_eur','optimized_value_eur','gross_electric_increment_eur',
                        'backup_cost_increment_eur','scenario_contribution_increment_eur']:
                check_equal_numeric(a[key],b[key],key,a['case_id'])
        o=rows(orig/'hypothetical_critical_service_results.csv')
        n=rows(fresh/'hypothetical_critical_service_results.csv')
        if len(o)!=5 or len(n)!=5:raise RuntimeError('Emergency cases not reproduced')
        for a,b in zip(o,n):
            if a['case_id']!=b['case_id']:raise RuntimeError('Emergency case ID changed')
            for key in ['electric_critical_served_mwh','heat_critical_served_mwh_th',
                        'fraction_electric_served','fraction_heat_served','terminal_gas_mwh_lhv']:
                check_equal_numeric(a[key],b[key],key,a['case_id'])
        orig_summary=json.loads((orig/'v08_study_summary.json').read_text())
        fresh_summary=json.loads((fresh/'v08_study_summary.json').read_text())
        if orig_summary['registry_sha256']!=fresh_summary['registry_sha256']:
            raise RuntimeError('Recomputed registry hash changed')
        print(json.dumps({'status':'PASS','market_scenarios_recomputed':216,
            'emergency_cases_recomputed':5,'execution_context':'clean isolated temporary directory',
            'tolerance_eur_or_mwh':2e-6,'network_required':False},indent=2))

if __name__=='__main__':verify()
