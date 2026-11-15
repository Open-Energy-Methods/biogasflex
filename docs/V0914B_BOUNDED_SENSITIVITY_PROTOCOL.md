# BiogasFlex v0.9.14-B — Bounded sensitivity and structural identifiability

**Version:** research phase B of software package `0.9.14`.
**Status:** predeclared, fully synthetic two-interval CHP generator-terminal
contract sensitivity. **Not** measured operational calibration, a probabilistic
robustness estimate, validation of market participation, or a claim of profit.

## Scientific question

When the hard accepted-electricity contract is fixed, which explicitly
*unmeasured* CHP/heat/gas assumptions decide whether the *existing*
synthetic on/off MILP can satisfy it, and which conclusions can be proven
for the narrowly defined interval model independently of the optimizer?

The experiment does **not** reuse unrelated manufacturer catalogue curves or
the 2012–2022 annual Polish landfill observations as hourly ramp,
min-load, fuel or storage measurements. `chp-evidence-register` and
`annual-chp-evidence` remain separate source/identity gates.
The pre-existing v0.9.13 market as-of timing gate also remains unchanged.

## Frozen original synthetic scenario and units

Predeclared `examples/v0914b_hypothetical_sensitivity.json` pins the **unchanged**
`examples/v0911_contract_hourly.json`,
`examples/v0911_synthetic_chp.json`, and
`data/evidence/v0914_chp_parameter_register.json` with SHA-256.
The new evaluator rejects changed paths, hashes, scenarios, assumptions,
range levels, or continuous boxes. An external source dataset is **not**
a probability distribution for these hypothetical parameters.

Original fictional dispatch: 2 × 1 h, accepted
`A=[0.2,0.6] MWh_e`, `η_e=0.4`,
gas production `g=[1,1] MW_LHV`, zero initial/final storage,
thermal efficiency `η_th=0.2`, instantaneous heat demand
`0.15 MW_th`, no CHP variable/start cost, no flaring/loss,
power nameplate `0.8 MW_e`, initial-on `P_prev=0.4 MW_e`.
Fictitious cleared prices `[100,0] EUR/MWh` yield a *fixed* gross
contract cashflow proxy of **€20 for feasible schedules**; there are
no metered sales, equipment profitability or balancing charges.
No 2020 observed SE3 price is used to pretend a 2026 pre-auction forecast.

The hard equality `η_e u_t Δt=A_t` requires
`P=[0.2,0.6] MW_e` and `u=[0.5,1.5] MW_LHV`.
Gas inventory after hours 1 and 2 is `[0.5,0] MWh_LHV`.
Minimum storage capacity is therefore **0.5 MWh_LHV**.
For the original *steady-on midpoint ramp convention*,
the upward ramp from `0.2` to `0.6 MW_e` over
1 h needs **0.4 MW_e/h**.
The first change from `P_prev=0.4` to `0.2` uses
0.5 h midpoint elapsed time, so requires a downward limit
at least **0.4 MW_e/h**. This is a *numerical convention of the
surrogate*, **not** a transient commissioning curve.

The minimum-on power must not exceed `0.2 MW_e`.
The first-hour useful heat is `0.1 MW_th`, so external backup
needs at least `0.05 MW_th`; the second-hour heat dump is
`0.15 MW_th`, below the fixed fictional `0.5 MW_th` dump cap.

## Full factorial: exact 3^4 = 81 experiments

| Hypothetical varied parameter | Units | Predeclared values | Analytical feasibility condition |
|---|---|---|---|
| Gas storage energy capacity | MWh_LHV | 0.4, 0.5, 0.7 | `C ≥ 0.5` |
| Steady-on upward ramp | MW_e/h | 0.3, 0.4, 0.8 | `r_up ≥ 0.4` |
| Minimum-on electrical power | MW_e | 0.15, 0.20, 0.25 | `P_min ≤ 0.20` |
| Auxiliary heat capacity | MW_th | 0.03, 0.05, 0.10 | `Q_aux,max ≥ 0.05` |

Each cell retains the **same** synthetic electricity awards, prices,
gas production, electric and thermal efficiency and all other assumptions.
Thus exactly `2×2×2×2 = 16` of `81` cells satisfy all four
necessary-and-sufficient conditions, while **65 fail** at least one.
Every cell is solved with the original constrained
SciPy/HiGHS `optimize_commitment_milp`, and an **independent algebraic
oracle** checks the gas, heat, power, ramp, terminal stock and contract
equalities. Unexpected solver errors or disagreements stop execution;
infeasible cases do **not** manufacture a cashflow/profit value.

## One-at-a-time (OAT): nine additional experiments

At the predeclared feasible reference
`(storage=0.5, ramp_up=0.8, min_power=0.15, backup_heat=0.05)`:

| Parameter | Values | Analytically expected feasible flags |
|---|---|---|
| `η_e` | 0.38, 0.40, 0.42 (LHV fraction) | No, **Yes**, No |
| `η_th` | 0.15, 0.20, 0.25 (LHV fraction) | No, **Yes**, **Yes** |
| Ramp down | 0.25, 0.40, 0.60 MW_e/h | No, **Yes**, **Yes** |

A critical scientific finding is **structural**, not empirical:
with gas arrival fixed at 2 MWh_LHV, zero flaring and cyclic stock,
the sum of fixed accepted electricity is 0.8 MWh_e.
Therefore the terminal stock equality requires
`2 = 0.8/η_e`, or exactly `η_e=0.4`.
Neither 0.38 nor 0.42 can satisfy all hard equalities.
An equipment owner could have variable flaring, another end stock,
storage replenishment, and part-load efficiencies; none are represented
here. Do not generalize the result to a real engine.

## Conditional continuous-box certificate

For the **specified, always-ON, 2-slot, strictly positive-award**
problem, these four constraints are monotonic in the varied parameters.
Checking the worst corner is sufficient and necessary for *all*
values in the continuous hyperrectangle, **when every other
original model input is held exactly fixed**.

- Wide box: storage [0.4, 0.7], ramp-up [0.3, 0.8],
  minimum-on [0.15, 0.25], backup heat [0.03, 0.10].
  **Not robust**, because its worst corner violates four conditions.
- Restricted box: storage [0.5, 0.7], ramp-up [0.4, 0.8],
  minimum-on [0.15, 0.20], backup heat [0.05, 0.10].
  **Conditionally robust for this exact simplified two-slot model only**,
  because its worst corner is feasible. All 16 vertices are also checked
  independently and best/worst corners solved by MILP.

This certificate does not cover varying electrical efficiency,
thermal efficiency, gas arrival, starting ON/OFF state,
temperature/fuel quality, startup transients, outages, net export,
equipment reliability, uncertainty correlation, time-varying
accepted awards, or other schedules. In particular, it is **not
an uncertainty-certified physical operating envelope**.

## Sensitivity attribution without probability fabrication

For the balanced **finite 81-cell design**, let
`y=1` for MILP-feasible and `y=0` otherwise.
Calculate the exact unweighted cell mean `μ=16/81`,
and the **design variance** `V=μ(1−μ)`.
For each factor `i`, calculate marginal cell means
`m_i(l)=mean(y | Xi=l)` and the main-effect variance
`V_i=mean_l[(m_i(l)−μ)^2]`.
For each pair `i,j`, calculate the second-order residual
`V_ij=mean_{l,k}[(m_ij(l,k)−m_i(l)−m_j(k)+μ)^2]`.
The unaccounted remainder is explicitly reported as
higher-order design interaction variance.

These values are **not Sobol indices for uncertain real-world plant
parameters**. Equal weight over cherry-picked hypothetical levels does
not encode physical parameter likelihood, so the observed 16/81
is not a probability that a real contract will be delivered.

## Structural identifiability (constructive non-injectivity)

The annual observation operator maps a power trace to
`(E=ΣP_tΔt, H_on=Σ1[P_t>0]Δt)`.
Two four-hour positive traces `[0.2,0.2,0.2,0.2]`
and `[0.1,0.3,0.1,0.3]` MW have identical `E=0.8 MWh`
and `H_on=4h`, but different ramps (0 vs 0.2 MW/h).
Two other traces `[0.2,0.2,0,0]`
and `[0.2,0,0.2,0]` MW have identical energy
and two running hours, but different startup counts (one vs two).
All positive values are below the reference 0.44 MW_e Polish
nameplate. These are **mathematical counterexamples, not measured
or necessarily physically permissible engine operation**.
They prove the annual summaries alone cannot uniquely identify
ramp or start dynamics.

## Reproduce and independently falsify

```bash
python -m pip install -e .
python -m biogasflex bounded-sensitivity
python -m biogasflex bounded-sensitivity --output report_v0914b.json
python scripts/audit_v0914b_sensitivity.py
python -m unittest discover -s tests -q
bash scripts/reproduce_v0914b.sh
```

Windows PowerShell: `./scripts/reproduce_v0914b.ps1`.

The independent script imports **no** `biogasflex` or solver code:
it launches the CLI once and independently recomputes **every one
of the 81** discrete feasibility classifications, the 9 OAT flags,
finite marginals, feasibility consistency and box certificates.
Regression tests also attempt to tamper with parameter levels,
source hashes, hardware provenance and scientific exclusions.

The project-wide release SHA256 manifest and historical source
freeze must pass. No optimizer source code, v0.9.11 contract
input, manufacturer source register or pre-existing published
experimental outputs are modified.

**Next evidence gate:** actual named CHP site and engine,
manufacturer part-load curve under stated fuel conditions,
metered fuel and heat/exhaust measurements, ramp/start tests,
gas-vessel pressure-volume operating limits, and synchronized
real export plus bid/settlement evidence. Human independent
methodological review and a scientific v1.0 remain outstanding.
