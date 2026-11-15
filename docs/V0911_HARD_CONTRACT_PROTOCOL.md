# BiogasFlex v0.9.11 — Hard accepted-energy constraints in CHP dispatch

**Status:** synthetic, independently numerically audited research software;
NOT a real-world auction, market bid, participant award, CHP export measurement,
price forecast, delivery nomination, imbalance settlement, or evidence of profit.

## Research defect resolved

v0.9.10 staged pre-clearing and post-clearing information, but compared
exogenous accepted electricity to the original **uncontracted optimal**
CHP schedule. It rejected other **physically feasible accepted**
schedules as `UNMODELLED_IMBALANCE` even when the CHP could meet them.
v0.9.11 adds a distinct `contract-dispatch` opt-in model that requires
**accepted energy to be satisfied by the MILP itself** rather than
posthoc comparison of an unrestricted optimum. The old
`market-boundary` command is preserved unchanged for reproduction.

## Mathematical formulation

For each declared delivery interval `t`, with duration
`Δt_t` in **hours**, `u_t` in MW_LHV and hypothetical
electrical efficiency `η_e`, and **accepted energy**
`A_t` in MWh_e:

```text
P_t = η_e × u_t                            [MW_e]
E_delivered_t = P_t × Δt_t                 [MWh_e]
η_e × u_t × Δt_t = A_t                    [MWh_e] HARD equality
```

These equalities are added directly to the existing SciPy/HiGHS
MILP constraint matrix **before solving**; the matched LP
relaxation uses the identical matrix including accepted awards.
The original constraints are intact: gas conservation and
finite-capacity stock, electric rating, minimum-on power, binary
on/off/start/stop, elapsed-hour ramps, minimum up/down and prior
dwell, fixed final inventory, instantaneous useful/auxiliary/
dumped heat service, optional startup/shutdown costs and
variable power costs.

No accepted volume is inferred from price. The pre-clearing
receipt remains a dated, integrity-checked synthetic offer;
publication, participant receipt and plan creation still
must precede the first delivery. `A_t` cannot exceed offered
MWh, and bids still must be submitted strictly before
the explicitly declared gate. Only 15-/60-minute periods
and explicit UTC are admitted. Partially accepted offers
are permitted **if the physical contract is feasible**.

The **constrained** objective still prices electrical
production and heat/aux costs in the model; it is NOT a
separate market settlement model. The gross awarded
cashflow diagnostic `Σ(A_t × cleared_price_t)` is already
part of the simulated electric revenue contribution;
**never add it a second time** to the optimizer's
net contribution or call either true operating profit.
The cashflow and solved commitment remain conditional
on fictional CHP and awarded data.

## Exact independently computed feasibility witnesses

**Hourly (2 × 1 h):** gas inflow [1,1] MW_LHV,
`η_e=0.4`, initial/final gas inventory zero,
storage cap 0.5 MWh_LHV. Accepted contract
`[0.2,0.6]` MWh_e forces gas-use rates
`[0.5,1.5]` MW_LHV and end-of-slot stock
`[0.5,0]` MWh_LHV. With fictional clearing
prices `[100,0]` EUR/MWh, gross awarded
cashflow = **€20**, physical gas residual zero.

The **uncontracted** preferred schedule instead
generates `[0.4,0.4]` MWh_e and would earn
€40 gross. It is feasible physically but violates
the *awarded* schedule. v0.9.10 posthoc mode
correctly refuses this contract; v0.9.11 finds the
**feasible but suboptimal** contracted schedule.
The fixed-operation reference is marked
`DIFFERENT_CONTRACTED_DELIVERY` rather than
being used to falsely reject the contracted optimum
as inferior to an inadmissible comparator.

**Quarter-hour (4 × 15 min):** identical 1 MW_LHV
constant inflow, `η_e=0.4`, gas cap 0.5 MWh_LHV.
Accepted `[.05,.15,.10,.10]` MWh_e entails
power `[.2,.6,.4,.4]` MW_e, gas inventory
`[.125,0,0,0]` MWh_LHV. With fictional prices
`[100,0,20,20]`, gross cashflow = **€9**.
Explicit conversion of 15 minutes to 0.25 hours
prevents a MW/MWh unit error.

**Independent negative witnesses:**
- Storage cap 0.1 MWh_LHV cannot accommodate
  first-hour required 0.5 MWh_LHV inventory.
- Tight continuous-ON ramp cannot reach
  accepted first-hour 0.2 MW_e from initial
  0.4 MW_e when only 0.5 h elapsed.
- Heat demand 0.25 MW_th with backup max
  0.1 MW_th cannot be met by 0.5 MW_LHV
  fuel use producing only 0.1 MW_th heat.
- Nonzero terminal inventory contradicts a
  contract that uses the entire gas supply.
- Zero or over-accepted energy is never
  valued as a hypothetical balancing sale.

All infeasible awards fail as `CONTRACT_INFEASIBLE`
after strict pre/post timing and offer acceptance checks.
No prices, bids, storage or electricity are fabricated
to satisfy the award.

## Reproduce

```bash
python -m pip install -e .
bash scripts/reproduce_v0911.sh
python scripts/audit_v0911_hard_contract.py
python -m biogasflex contract-dispatch
python -m biogasflex contract-dispatch --manifest examples/v0911_contract_quarterhour.json
python -m biogasflex contract-dispatch --output contracted_report.json
```

Windows: `./scripts/reproduce_v0911.ps1`.

The original research source/result freeze (286 pinned
files), 216 historical primal-dual certificates,
96 solver-free LP comparisons, previous science
data, v0.9.5–v0.9.10 model validations and negative
controls remain inherited CI gates.

## Unresolved physical and financial boundaries

The equality is at the **CHP generator terminals**,
not a grid export meter. No parasitic site demand,
network constraints, export losses, minimum auction lot
size, price/volume bidding curve, block-product
optimization, trade clearing, nominations, intraday
redispatch, imbalance price settlement, plant
calibration, uncertain gas inflow or forecast validation.
The entire awarded-volume source, actual market prices,
CHP physics and costs are synthetic.

Next scientific gap: establish genuine as-of published
market inputs and calibrated CHP/export measurements
before any realistic economic performance assessment.
The [independent methodology review issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains open. No public GitHub Release, DOI or scientific
v1.0 is warranted by CI alone.
