"""A7: verify source ZIP and installed wheel independently of editable checkout."""
from __future__ import annotations
import argparse
import base64
import csv
from email.parser import BytesParser
from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tempfile
import venv
import zipfile
from verify_v09_manifest import verify

ROOT=Path(__file__).resolve().parents[1]
VERSION="0.9.28"

def need(ok,msg):
    if not ok: raise AssertionError("A7 distribution: "+msg)

def execute(cmd, cwd):
    env={k:v for k,v in os.environ.items() if k not in ("PYTHONPATH","PYTHONHOME")}
    p=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,
        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,timeout=600)
    if p.returncode: raise RuntimeError("Command failed: "+str(cmd)+"\n"+p.stdout)
    return p.stdout

def check_paths(names):
    need(len(names)==len(set(names)),"duplicate archive entry")
    for name in names:
        p=PurePosixPath(name)
        need(not p.is_absolute() and "\\" not in name and ":" not in name
             and ".." not in p.parts and "." not in p.parts,"unsafe archive path "+name)

def check_wheel(wheel,root=ROOT):
    with zipfile.ZipFile(wheel) as z:
        names=z.namelist();check_paths(names)
        need(all(not n.endswith("/") for n in names),"unexpected wheel directory")
        records=[n for n in names if n.endswith(".dist-info/RECORD")]
        need(len(records)==1,"missing wheel RECORD")
        record=records[0];prefix=record.rsplit("/",1)[0]+"/"
        rows=list(csv.reader(io.StringIO(z.read(record).decode("utf8"))))
        need(all(len(r)==3 for r in rows),"invalid RECORD row")
        need(len(rows)==len(names) and {r[0] for r in rows}==set(names),"RECORD coverage")
        for n,h,size in rows:
            if n==record:
                need(h==size=="","RECORD self-hash not empty");continue
            data=z.read(n)
            expected="sha256="+base64.urlsafe_b64encode(sha256(data).digest()).decode().rstrip("=")
            need(h==expected and size==str(len(data)),"RECORD checksum mismatch: "+n)
        m=BytesParser().parsebytes(z.read(prefix+"METADATA"))
        need(m["Name"]=="biogasflex" and m["Version"]==VERSION,"wheel version/name")
        need(any(n.startswith(prefix) and n.rsplit("/",1)[-1]=="LICENSE" for n in names),"wheel license absent")
        expected={p.relative_to(root/"src").as_posix() for p in (root/"src/biogasflex").rglob("*.py")}
        actual={n for n in names if n.startswith("biogasflex/")}
        need(actual==expected,"Unexpected/missing package source")
        for n in actual:
            need(z.read(n)==(root/"src"/n).read_bytes(),"Wheel/source byte mismatch: "+n)
        need(all(n in expected or n.startswith(prefix) for n in names),"unapproved wheel contents")
        return {"wheel_members":len(names),"python_package_files":len(actual),
                "wheel_record_verified":True,"wheel_sha256":sha256(wheel.read_bytes()).hexdigest()}

def qualify(out):
    checked=verify(ROOT)
    git=execute(["git","rev-parse","HEAD"],ROOT).strip()
    with tempfile.TemporaryDirectory(prefix="biogasflex-a7-") as tmp:
        root=Path(tmp); zip_path=root/"source.zip"; extracted=root/"source"
        execute(["git","archive","--format=zip","-o",zip_path,"HEAD"],ROOT)
        with zipfile.ZipFile(zip_path) as z:
            check_paths(z.namelist())
            z.extractall(extracted)
        need(verify(extracted)==checked,"source ZIP manifest mismatch")
        wheel_dir=root/"wheel"
        execute([sys.executable,"-m","pip","wheel","--no-deps","--wheel-dir",wheel_dir,ROOT],root)
        wheels=list(wheel_dir.glob("biogasflex-*.whl"));need(len(wheels)==1,"expected one wheel")
        w=check_wheel(wheels[0])
        env=root/"install"
        venv.EnvBuilder(with_pip=True).create(env)
        py=env/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        execute([py,"-m","pip","install",wheels[0]],root)
        execute([py,"-m","pip","check"],root)
        need(execute([py,"-I","-m","biogasflex","--version"],root).strip()==VERSION,"installed CLI version")
        for module in ("biogasflex","biogasflex.causal_v0922","biogasflex.viability_v0923",
                       "biogasflex.award_v0924","biogasflex.sensitivity_v0925","biogasflex.contract_v0927"):
            need("usage:" in execute([py,"-I","-m",module,"--help"],root).lower(),"CLI help missing: "+module)
        target=root/"baseline.json"
        execute([py,"-I","-m","biogasflex","baseline","--config",extracted/"config/baseline.json",
                 "--prices",extracted/"data/synthetic/prices_4h.csv","--output",target,"--mode","synthetic"],root)
        baseline=json.loads(target.read_text(encoding="utf8"))
        need(abs(baseline["electricity_generated_mwh"]-.96)<1e-10 and
             abs(baseline["gross_electricity_revenue_eur"]-15.6)<1e-9,"analytic baseline smoke mismatch")
        probe="""import json, biogasflex, scipy
from importlib import metadata
from scipy.optimize import linprog, milp, Bounds
from biogasflex.contract_v0927 import acceptance, execute
g=acceptance([.09]*24,capacity=3.,gas_lower=.78,gas_upper=1.22,heat_lower=.105,heat_upper=.195,service='carryover')
r=execute(g,[.78]*6,[.15]*6,[50.]*6)
no=acceptance([.09]*24,capacity=1.5,gas_lower=.78,gas_upper=1.22,heat_lower=.105,heat_upper=.195,service='carryover')
lp=linprog([-1.],bounds=[(0.,1.)],method='highs')
mi=milp([-1.],integrality=[1],bounds=Bounds([0.],[1.]))
assert g['accepted'] and r['status']=='fulfilled' and not no['accepted']
assert abs(r['terminal_stock_mwh_lhv']-.03)<1e-9 and lp.success and mi.success
assert abs(lp.x[0]-1)<1e-9 and abs(mi.x[0]-1)<1e-9
print(json.dumps(dict(version=biogasflex.__version__,distribution=metadata.version('biogasflex'),module_file=biogasflex.__file__,scipy=scipy.__version__)))
"""
        installed=json.loads(execute([py,"-I","-c",probe],root))
        need(installed["version"]==installed["distribution"]==VERSION,"installed metadata divergence")
        need(Path(installed["module_file"]).resolve().is_relative_to(env.resolve()),"import leaked from checkout")
        del installed["module_file"]
        result={"status":"PASS_V0928_ARCHIVE_AND_ISOLATED_WHEEL",
                "git_sha":git,"version":VERSION,"python":platform.python_version(),"platform":platform.platform(),
                "source_manifest_entries":checked,"source_zip_sha256":sha256(zip_path.read_bytes()).hexdigest(),
                **w,"isolated_wheel_cli_baseline_contract_and_lp_milp":True,"installed":installed,
                "field_qualification":False}
        out.mkdir(parents=True,exist_ok=True)
        (out/"distribution_certificate.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
        print(json.dumps(result,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir",required=True,type=Path)
    qualify(p.parse_args().output_dir)
