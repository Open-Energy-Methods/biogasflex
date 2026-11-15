"""Independent standard-library and subprocess audit, no biogasflex imports.

Runs the installed CLI in an isolated temporary location, then recomputes
EVERY factorial result from the frozen awards and gas/heat arithmetic. The
checker does not call SciPy, invoke the LP internals or reuse oracle logic.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "examples/v0914b_hypothetical_sensitivity.json"
NAMES = (
    "gas_storage_capacity_mwh_lhv",
    "experimental_v098.ramp_up_mw_e_per_hour",
    "experimental_v098.minimum_on_power_mw_e",
    "aux_heat_capacity_mw_th",
)
LEVELS = ((.4,.5,.7),(.3,.4,.8),(.15,.2,.25),(.03,.05,.1))
PINS = {
    "examples/v0911_contract_hourly.json":
        "1ced01d0e97b0a76a0ac9f7442419fb577b20fb1056dcd6a7abda1e3441505c4",
    "examples/v0911_synthetic_chp.json":
        "637c95d5e5db7e88acade3e063d9582fffa291e2f4541ec3a2f6d5f5e2fa3b29",
    "data/evidence/v0914_chp_parameter_register.json":
        "03d1e141e33ca820878772d377234400eab7fab18825305e1dec2ae878b56823",
}

def audit() -> dict:
    for path, digest in PINS.items():
        assert sha256((ROOT/path).read_bytes()).hexdigest() == digest, path
    design = json.loads(DESIGN.read_text(encoding="utf8"))
    assert design["experimental_design"] == "EXHAUSTIVE_DISCRETE_CARTESIAN_3_LEVEL_4_FACTOR"
    assert [x["name"] for x in design["varied_parameters"]] == list(NAMES)
    assert [tuple(x["levels"]) for x in design["varied_parameters"]] == list(LEVELS)
    with tempfile.TemporaryDirectory(prefix="v0914b-independent-") as tmp:
        path = Path(tmp)/"full_report.json"
        subprocess.run(
            [sys.executable, "-m", "biogasflex", "bounded-sensitivity",
             "--manifest", str(DESIGN), "--output", str(path)],
            cwd=ROOT, check=True, capture_output=True, text=True, timeout=180,
        )
        result=json.loads(path.read_text(encoding="utf8"))
    rows=result["factorial_cases"]
    expected_cells=list(product(*LEVELS))
    assert len(rows)==len(expected_cells)==81
    codes=Counter()
    feasible=0
    for idx,(values,row) in enumerate(zip(expected_cells,rows)):
        assert row["case_id"] == f"F{idx:03d}"
        assert tuple(row["parameter_values"][key] for key in NAMES) == values
        capacity,ramp,minpower,backup=values
        # Exact fixed toy (no start): P=[.2,.6] MW and fuel=[.5,1.5]
        # MW_LHV force storage=.5 MWh, upward steady ramp=.4 MW/h,
        # minimum power <=.2 MW and first-slot auxiliary heat >=.05 MW.
        reasons=[]
        if capacity < .5-1e-10:
            reasons.append("GAS_STORAGE_STOCK")
        if ramp < .4-1e-10:
            reasons.append("RAMP_UP")
        if minpower > .2+1e-10:
            reasons.append("MINIMUM_ON_POWER")
        if backup < .05-1e-10:
            reasons.append("BACKUP_HEAT_CAPACITY")
        should_work = not reasons
        assert row["milp_feasible"] == row["oracle_feasible"] == should_work, row
        assert sorted(row["analytic_infeasibility_codes"]) == sorted(reasons), row
        if should_work:
            feasible+=1
            assert abs(row["contract_delivered_mwh"]-.8)<1e-8
            assert row["maximum_energy_contract_residual_mwh"]<1e-8
            assert abs(row["net_synthetic_contribution_eur"]-20.0)<1e-7
        else:
            assert row["contract_delivered_mwh"] is None
            assert row["net_synthetic_contribution_eur"] is None
        codes.update(reasons)
    assert feasible==16 and len(rows)-feasible==65
    summary=result["summary"]
    assert summary["factorial_feasible_count"]==16
    assert summary["factorial_infeasible_count"]==65
    assert summary["failure_reason_frequency_over_grid"] == dict(sorted(codes.items()))
    assert summary["hypothetical_gross_award_cashflow_proxy_eur"] == 20.0
    attr=result["finite_design_attribution"]
    assert abs(attr["grid_mean_binary_feasibility"]-16/81)<1e-12
    assert abs(attr["grid_variance_binary_feasibility"]-(16/81)*(65/81))<1e-12
    assert not attr["statistical_probability_claim"]
    for name in NAMES:
        actual=attr["first_order"][name]["finite_grid_feasibility_fraction_by_level"]
        assert sorted(actual)==[0.0,8/27,8/27]
    variance=sum(x["first_order_component_of_design_variance"]
                 for x in attr["first_order"].values())
    variance+=sum(x["interaction_component_of_design_variance"]
                  for x in attr["second_order"])
    variance+=attr["higher_order_residual_variance"]
    assert abs(variance-attr["grid_variance_binary_feasibility"])<1e-12
    oat = result["one_at_a_time_cases"]
    assert len(oat)==9
    expected_oat={
        "electric_efficiency_lhv":(False,True,False),
        "thermal_efficiency_lhv":(False,True,True),
        "experimental_v098.ramp_down_mw_e_per_hour":(False,True,True),
    }
    for name, expected in expected_oat.items():
        actual=tuple(row["milp_feasible"] for row in oat if name in row["parameter_values"])
        assert actual == expected, (name,actual)
    wide,safe = result["continuous_box_certificates"]
    assert not wide["model_conditionally_feasible_everywhere_in_continuous_rectangle"]
    assert wide["corners_checked_analytically"]==16
    assert safe["model_conditionally_feasible_everywhere_in_continuous_rectangle"]
    assert safe["feasible_corners"]==16
    assert safe["worst_corner"]["milp_feasible"]
    assert not result["probabilistic_robustness_claim"]
    assert not result["calibration_claim"]
    assert not result["operational_market_eligibility_claim"]
    return {
        "status":"PASS_INDEPENDENT_81_CELL_NUMERICAL_ORACLE",
        "factorial_cell_count":81,
        "factorial_feasible":feasible,
        "factorial_infeasible":65,
        "oat_case_count":9,
        "separate_two_slot_continuous_box_certificates":2,
        "counterexample_to_wide_box":True,
        "restricted_box_analytically_feasible_for_all_values":True,
        "real_chp_calibrated":False,
        "probabilistic_inference_performed":False,
    }

if __name__=="__main__":
    print(json.dumps(audit(),indent=2,allow_nan=False))
