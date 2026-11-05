# BiogasFlex v0.9.3 — solver-free two-interval stress protocol

**Scope:** Internal verification of a stylized CHP dispatch model. Not
observed plant validation, an independently reviewed paper, a new market
study, an independent general-purpose LP solver, or a publication.

## Mathematical two-interval oracle

With net gas supply `q_t` (MW_LHV), gas use `u_t` (MW_LHV), duration
`d_t` (h), and cyclic inventory `S_0` (MWh_LHV), the intermediate stock
`S_1` determines all gas use:

```
u_0 = q_0 + (S_0-S_1)/d_0
u_1 = q_1 + (S_1-S_0)/d_1
0 <= S_1 <= storage_capacity
0 <= u_t <= electrical_rating / electric_efficiency
heat_demand_t - backup_cap_t <= eta_h*u_t <= heat_demand_t + dump_cap_t
```

The special case `eta_h=0` checks heat-service feasibility without
division by zero. The fixed comparator must satisfy all rate bounds.

The contribution maximized for each interval is

```
d_t*[eta_e*u_t*(price_t-variable_electric_cost_t)
     - max(heat_demand_t-eta_h*u_t,0)*backup_heat_cost_t
     - max(eta_h*u_t-heat_demand_t,0)*dump_penalty_t]
```

This is piecewise affine in `S_1`. Its optimum occurs at a feasible
stock endpoint or at a heat-demand kink (`eta_h*u_t=heat_demand_t`).
Therefore evaluating no more than **four stock candidates** gives an
exact global optimum of the *two-period mathematical problem*, without
SciPy, NumPy, HiGHS, or the original source LP builder.

## Predeclared deterministic stress

`python scripts/run_v093_stress.py --seed 20261105 --count 96` checks
96 explicitly **synthetic**, seeded two-interval configurations across
negative/positive spot prices, unequal 0.25–1.75 hour durations, variable
gas input, gas flaring/losses, inventory, heat demand, backup/dump costs,
CHP cost and thermal efficiency. It compares the exact analytical oracle
to the inherited SciPy/HiGHS optimizer within **€2e-6**.

Metamorphic identities tested:

1. Equal spot-price shifts do not alter the incremental dispatch value
   under cyclic stock and fixed gas supply. Absolute contributions move
   by `price_shift * eta_e * total_gas_used_MWh`.
2. A uniform shift in CHP variable cost does not alter incremental value
   when the electrical generation total is conserved.
3. Storage capacity increases with zero initial inventory cannot reduce
   the maximized modeled contribution (feasible-set inclusion).
4. Zero gas storage and zero inventory preclude gas retiming.

Eleven new adversarial/unit tests cover infeasible baselines, nonfinite
or boolean values, price shifts, zero heat conversion, negative prices,
unequal time intervals and the inherited **€8.25 analytical toy oracle**.

The synthetic grid is **not a statistical sample** of Swedish CHP
operations. The oracle verifies two-interval model behavior only. The
historical **216 original 24-hour cases** retain their v0.9.2
primal/dual certificate checks, which share SciPy/HiGHS; the five
hypothetical interruption cases retain inherited audits. All original
**286 pinned scientific research files** and historical results are frozen.

## Reproduction

After installing Python 3.10+, SciPy, and package dependencies:

```bash
python -m pip install -e .
bash scripts/reproduce_v093.sh
```

Windows PowerShell: `./scripts/reproduce_v093.ps1`.
The CI matrix checks Ubuntu, Windows and macOS on Python 3.11–3.13
plus a separate wheel-install smoke test. The new stress tests do not
overwrite source observations or frozen results.

No verified site heat telemetry, realistic start/ramp constraints,
vessel dynamics or actual installed costs/NPV, island/black-start
capability, annual representativeness or external human scientific
review is supplied here. **No GitHub Release or DOI is authorized.**
