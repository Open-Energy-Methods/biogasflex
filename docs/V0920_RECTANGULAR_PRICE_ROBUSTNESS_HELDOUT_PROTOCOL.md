# BiogasFlex v0.9.20 — Exact rectangular price robustness and nonanticipative held-out CHP replay

## Purpose, research boundary and falsifiable claim

The objective of v0.9.20 is to test **decision robustness under bounded
electricity-price errors**, rather than claiming a realistic statistical price
forecast, reliable generator performance or realized power-market profit.
This is a rigorously defined *synthetic optimization stress test* built
on v0.9.19's fully assumed CHP/gas/thermal service configuration.

For each fixed `train_seed × horizon × price-stress band`, two
ex-ante schedules are computed with the **unchanged original
v0.9.7 elapsed-hour unit-commitment MILP**:

- **Nominal:** maximize contribution for the invented ex-ante
  nominal electricity-price vector.
- **Rectangular maximin:** maximize the worst possible contribution
  across the Cartesian product of declared hourly/quarter-hour
  price intervals. The uncertainty affects electricity prices **only**.
  Gas production, heat requirements, equipment performance, outage
  status and penalties are held invariant.

Both schedules, operating states and physical dispatch are fixed
**before** any hold-out price vector is constructed. No commitment
can be revised, no true future price can be observed before a decision,
and no fictitious balancing/imbalance remedy is credited.

Held-out scenarios are evaluated on these frozen decisions. Separately,
an ex-post perfect-information solve for each held-out price path
provides a **counterfactual regret reference**, explicitly
*not* an operational forecast or actionable bid.

## Mathematical robustness statement

In a finite horizon with 15-minute increments, let the model
generator-terminal electricity production per interval be

```text
E_t(x) = 0.25 h × η_e × u_t(x) >= 0 MWh_e
```

where `u_t >= 0` is the modeled gas fuel rate and `η_e = 0.4`
is an **assumed**, uncalibrated electric conversion efficiency.

Write the mathematical objective for any physically feasible fixed
schedule `x` at price vector `π` as

```text
F(x,π) = Σ_t E_t(x) × π_t − C(x).
```

`C(x)` includes the explicitly assumed CHP variable cost,
backup heat, dumped heat, engine startup and shutdown penalties.
It does **not** depend on electricity price in this experiment.

The adversarial price set is the **rectangular** set

```text
U = { π : lower_t <= π_t <= upper_t for each t }.
```

Since `E_t(x) >= 0` for every interval,

```text
min_{π∈U} F(x,π) = F(x,lower).
```

Therefore the robust schedule

```text
x_robust ∈ argmax_{x∈X} min_{π∈U} F(x,π)
         = argmax_{x∈X} F(x,lower)
```

can be computed **exactly** by feeding the vector of
lower price bounds into the unchanged original MILP.
The robust guarantee follows algebraically for this
specified rectangular price set; **it is not a statistical
confidence bound** on actual electricity prices.

For the nominal feasible schedule `x_nominal`, a
globally optimized robust policy satisfies:

```text
F(x_robust,lower) >= F(x_nominal,lower)
```

subject to solver tolerance. The program and the independent
audit both reject any violation.

**This statement does not guarantee better revenue for each
realization inside the envelope**, does not model contingent
intraday rebidding, and does not constrain genuine grid-delivery
awards or settlement. Nor does it provide a guarantee
if the real price vector falls outside the assumed envelope,
or actual gas/heat/machine state differs from assumptions.

## Frozen synthetic information set

| Dimension | Explicit synthetic assumption |
|---|---|
| Forecast issue | 2019-12-31 23:00 UTC — artificial clock label, not a real forecast |
| Nominal service start | 2020-01-01 00:00 UTC — artificial operational label |
| Frequency | 15 minutes, all timestamps explicitly offset-aware UTC |
| Main horizon | **24 / 96 / 192 quarters** = **6 / 24 / 48 hours** |
| Global MILP oracle | Separate **8-quarter** experiment; all 2⁸ binary patterns enumerated |
| Ex-ante nominal seeds | **11, 37** — intentionally selected price-perturbation identifiers |
| Held-out price seeds | **101, 211, 307**, generated after both ex-ante solves |
| Electricity price zone | `SE3` is the input zone label only, NOT measured SE3 prices |
| Engine LHV efficiency | η_e = 0.4, η_th = 0.2; no calibrated real CHP |
| Gas production | Constant fictional 1 MW_LHV; zero modeled flaring/loss |
| Gas buffer | 1.5 MWh_LHV with 0.75 MWh_LHV initial and terminal stock |
| Thermal service | 0.15 MW_th fixed demand and 0.15 MW_th auxiliary capacity |
| Commitment | Initially ON at 0.4 MW_e; 0.2 MW_e minimum; 0.8 MW_e nameplate |
| Dynamics | 0.8 MW_e/h steady-ON midpoint ramp; 0.5 h minimum on/off; transition transient exempt |
| Costs | €5 per modeled startup, €1 shutdown, €0.75/MWh_e CHP variable, €6/MWh_th auxiliary heat, €1/MWh_th heat dump |
| Other boundary | No gas-vessel pressure, startup transient, gas chemistry, measured export or local heat-billing data |

Two deliberately distinct, versioned **price-uncertainty severity
classes** are run for *every* price seed and horizon:

| Bounds | Base high-price quarters (base ≥€100/MWh) | Mid-price quarters (base ≥€15/MWh) | Low-price quarters |
|---|---:|---:|---:|
| `reference` | nominal ±€55/MWh | ±€12/MWh | ±€8/MWh |
| `wide_stress` | nominal ±€115/MWh | ±€20/MWh | ±€8/MWh |

Every price floor is clipped to €0/MWh and every
upper bound is `nominal+spread`. These are **invented sensitivity
bands**, not prediction intervals, manufacturer guarantees or
historic observed maximum forecast errors.

**Transparent model-development observation:** The initial
single-band reference study produced identical nominal and
robust dispatch values. The initial negative result was retained
and a **separately identified wider stress envelope** added to
test the dependence on uncertainty-set geometry; the original
reference results have not been overwritten or omitted.

The hold-out price formula is completely deterministic, with
the three frozen hold-out seeds. Paths lie inside the corresponding
assumed interval bounds, but are **not a probability sample** or
empirical market data. They are generated and evaluated only after
the ex-ante nominal and robust policies are fixed and SHA256
fingerprinted using physical on/off, fuel, gas stock and heat flows.

## Computational design and audit gates

The full experiment comprises **14 scenarios**:

```text
2 ex-ante seeds × 3 horizons × 2 price stress classes = 12
+ 2 separate eight-quarter small global verification cases.
```

For each case: two pre-reveal model optimizations
(nominal and robust) and three subsequent hindsight
oracles. Thus there are **28 frozen ex-ante policy outputs**,
**42 held-out paths**, and **70 independent reconstructed
fixed-pattern linear-program KKT witnesses**, covering 6,320
15-minute model-output rows (counting each fixed policy
and hindsight schedule).

`scripts/audit_v0920_independent.py` imports **no
`biogasflex` source module**. It independently:

1. Reconstructs both nominal price vectors and both severity
   envelopes from constants and integer arithmetic; tests the
   synthetic UTC chronology and frozen model coefficients.
2. Recomputes gas storage and full-horizon conservation,
   electricity and heat rates, heat-service obligation,
   minimum nameplate/backup/storage bounds, operation/binary
   switch/dwell/ramp rules and cost accounting for every row.
3. Recomputes original policy cash contribution for the
   nominal, lower-bound and each held-out vector; checks
   immutable SHA256 schedule fingerprints before and after
   disclosure, no optimized-price substitution or optimistic
   hindsight leakage.
4. Uses the separately written v0.9.19 **five-block fixed
   binary LP mathematical formulation** to reconstruct
   continuous-state optimality for each chosen binary pattern
   and independently checks LP **primal feasibility, dual
   signs, KKT stationarity, complementary slackness and
   primal–dual objective gap**.
5. Exhaustively enumerates all **256** binary patterns in
   each separate small eight-quarter *nominal and robust*
   case (four independently checked global MILP oracles
   across two severity classes). Also enumerates all
   **2⁸ uncertainty-price corners** in the reference
   eight-quarter test to verify the mathematical lower-
   envelope minimizer.
6. Recomputes all reported selected hold-out minima,
   nonprobabilistic arithmetic means, hindsight gaps
   and worst-case envelope objectives. An original MILP
   objective above its perfect-hindsight counterfactual or
   a realized in-envelope contribution below the proven
   lower-envelope bound fails the experiment.

**Numerical-independence limitation:** The auditor's LP
formulation is separate from the original production code,
but the numerical LP backend is still **SciPy/HiGHS**.
For 24/96/192-quarter binary decisions, global optimality
is still the inherited MILP solver's status/gap claim,
not exhaustive independent binary certification. Only
the eight-quarter cases have exhaustive independent
binary state enumeration.

## What can and cannot be inferred

Legitimate scientific outcomes are:
- reproducible, internally consistent **mathematical
  optimization under explicitly bounded synthetic price risk**;
- the exact rectangular min-price proof for nonnegative power;
- a strict no-lookahead **frozen** schedule comparison;
- bounded synthetic regret relative to a clearly
  *counterfactual* perfect-information oracle;
- empirical **sensitivity to assumed uncertainty-set width**
  rather than measured uncertainty.

**Not established:** physical CHP flexibility, gas-vessel
pressure or compressor/transient constraints, real plant
availability/forced-outage probability, equipment ageing,
stochastic distribution of price errors, actual bidder's
day-ahead forecast, contract/electricity metering match,
revenue settlement, investment costs/NPV or scientific
v1.0 field verification.

## Reproduction (output deliberately outside the source tree)

```powershell
git pull origin main
python -m pip install -e .

# Full inherited offline numerical/test/manifest release gate:
.\scripts\reproduce_v0920.ps1

# Full two-band 6h/24h/48h plus 8-slot global-oracle study:
$scenarios = Join-Path $env:TEMP "biogasflex_v0920_robust.json"
$proof = Join-Path $env:TEMP "biogasflex_v0920_certificate.json"
python -m biogasflex price-robust-v0920 --output $scenarios
python scripts/audit_v0920_independent.py --input $scenarios --output $proof
```

The dedicated workflow
`.github/workflows/v0920-robust-price-oos.yml`
uploads both the immutable fully synthetic source schedule and
the independent witness JSON as distinct research artifacts.
A scientific publication or operations claim should disclose
both *reference* and *wide_stress* outcomes, including cases
where robust dispatch is less profitable than nominal ex-post.
