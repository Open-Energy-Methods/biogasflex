# BiogasFlex v0.9.19 — Executed endogenous CHP scenario study and independent LP certificates

**Execution date:** 2026-11-15. Original full design and
independently reconstructed physical/dual optimum audit
[GitHub Actions 43723554010](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43723554010),
after correcting a duplicated deterministic price scenario seed.
**Status:** completed independent numerical verification. All inputs
and outputs in this document are **FICTITIOUS mathematical experiments**,
not industrial operating data, market forecasts, installed capital
costs, observed operator reliability or revenue.

## Quantitative verification performed

- **36 endogenous** 24-quarter-hour = six-hour CHP binary commitment
  MILP runs: 3 **distinct** hypothetical price patterns (seeds
  11, 37 and 59), storage capacity `0/0.5/1.5 MWh_LHV`,
  external heat backup capacity `0/0.15 MW_th`, assumed engine
  startup cost `€5/€15`; identical gas, heat, power and
  thermal-service formulation otherwise.
- **9 separately modeled** 96-quarter-hour continuously-ON
  ramp-LP runs (3 selected hypothetical price seeds × 3 gas stores).
  The LP is *not* a binary relaxation of the commitment MILP
  because the ON floor and transition formulation differ.
- One additional eight-quarter-hour gas-buffered commitment case
  with **2⁸ = 256 exhaustively enumerated binary patterns** and
  a separately formulated restricted LP for every admissible
  pattern, giving a global objective cross-check for **that
  small mathematical case only**.
- **46 total optimized cases; 1,736 15-minute schedule rows checked**,
  46 separately reformulated LP primal/dual/KKT tests:
  37 for **chosen MILP binary patterns** and nine for the
  full continuous ramp-LP cases. **Only the eight-slot MILP**
  has an independent exhaustive *global* binary optimality check.
- Three 6-candidate **finite operational-design frontiers**
  are independently reconstituted from the verified full
  scenario table.
- **Six of the binary model cases actually turned the CHP OFF
  and restarted it**, with a maximum of **two modeled starts**
  in one six-hour case. These are endogenous decisions, unlike
  v0.9.18's zero-buffer forced schedule; they are not measured
  starts or authenticated physical startup traces.
- The full source+proof JSON is attached to the linked run;
  neither the price patterns nor any "plant" data are empirical.

## Non-dominated operational-design comparisons

Within each **fixed price sequence and startup cost €5**
the six `storage × backup-capacity` counterfactuals share
identical 6h duration, fuel supply, heat demand and
electricity-revenue proxy. Values are directly from original
solver outputs and independently rechecked. The three Pareto
criteria are **maximize fictional economic contribution,
minimize externally supplied heat fraction and minimize
number of starts**.

| Price seed | Gas buffer (MWh_LHV) | Backup capacity (MW_th) | Hypothetical objective (EUR, six hours) | External heat / total demand | Model starts |
|---|---:|---:|---:|---:|---:|
| 11 | 0.5 | 0.15 | **202.025** | 5.56% | 0 |
| 11 | 1.5 | 0 | **198.425** | 0% | 0 |
| 11 | 1.5 | 0.15 | **250.854** | 37.50% | 2 |
| 37 | 0.5 | 0.15 | **201.006** | 4.86% | 0 |
| 37 | 1.5 | 0 | **197.500** | 0% | 0 |
| 37 | 1.5 | 0.15 | **249.713** | 37.50% | 2 |
| 59 | 0.5 | 0.15 | **201.397** | 5.90% | 0 |
| 59 | 1.5 | 0 | **198.050** | 0% | 0 |
| 59 | 1.5 | 0.15 | **248.938** | 37.50% | 2 |

**Interpretation:** a 1.5-MWh_LHV hypothetical buffer plus
0.15 MW_th backup capacity permits a higher modeled
electricity-price contribution but shifts about **37.5% of
required thermal energy to assumed backup supply** in the
high-price solutions, and causes two mathematically modeled
start events. A 1.5-MWh buffer without external backup
can deliver the full thermal demand directly from CHP with
no starts but a lower hypothetical contribution. A smaller
0.5-MWh buffer permits intermediate economic output with
a small fraction of auxiliary heat. These choices are
non-dominated under the stated **three metrics only**.

The analysis includes **no buffer vessel acquisition cost,
backup heater CAPEX, plant degradation, startup fuel,
maintenance per start, emissions, actual electricity delivery
or uncertain operational failures**. Therefore **higher
synthetic objective is not equivalent to higher financial
NPV or operational value**.

## Independent arithmetic and scientific scope

The independent script imports **no `biogasflex` code**.
It reconstructs exact deterministic `[11,37,59]`
price sequences, UTC quarter-hour stamps and
model coefficients; checks per-interval gas/electric/heat
balances, inventory cyclicity, nameplate, minimum load,
start/stop logic, minimum dwell, midpoint ramp and the
monetary ledger; and independently builds the
restricted-pattern five-block gas/heat LP. Every LP certificate
tests equality and inequality feasibility, bound feasibility,
dual sign, stationarity, complementary slackness and
**primal/dual objective gap** (declared absolute
3×10⁻⁵ tolerance). All tests passed.

The independently formulated LPs still use the **same
SciPy/HiGHS mathematical optimization backend** as
the original solver; this is not software or hardware
independence of the underlying optimizer.

**Global optimality of the 36 longer binary models is
still solver-reported (zero MIP gap)** and independent
primal/dual verification applies to *each chosen fixed
binary pattern*. The one eight-slot full binary enumeration
provides a genuine, case-scoped global independent model
cross-check. General nonconvex real CHP dispatch
or nonlinear machine performance has not been certified.

The three seeds are **selected illustrative finite scenarios,
not three independent measurements or three sampled
probabilistic outcomes**. They are different source arrays:
the earlier seed 83 was discarded because the integer
modulo-9 generator duplicated seed 11. An adversarial test
now fails if any published seed sequence repeats.
No probability of satisfying service, confidence intervals,
expected profit or physically justified stochastic risk
can be computed from these cells.

All model-feasible cases supply **100% of instantaneous
synthetic heat demand**, but different quantities of
auxiliary heat. This is **NOT a demonstrated reliability
rate of 100%**. No actual disturbance, unplanned outage,
metering traceability, equipment hardware curve, gas
vessel pressure constraint or useful end-user
heat delivery measurement has been introduced.

## Reproduce

```powershell
git pull origin main
python -m pip install -e .

$design = Join-Path $env:TEMP 'biogasflex_v0919_design.json'
$proof  = Join-Path $env:TEMP 'biogasflex_v0919_certificate.json'

python -m biogasflex benchmark-v0919 --output $design
python scripts/audit_v0919_independent.py --input $design --output $proof
.\scripts\reproduce_v0919.ps1
```

See the [predeclared mathematical protocol](../docs/V0919_ENDOGENOUS_FLEXIBILITY_DUAL_CERTIFICATION_PROTOCOL.md)
for the complete scope, parameters and limitations.
The Matlink real **biogas** reciprocating-engine access,
genuine start/stop traces, bid-time market validation and
scientific v1.0 field-validation gates remain open.
