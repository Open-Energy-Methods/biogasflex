# BiogasFlex v0.9.20 — Executed bounded-price CHP robustness and held-out replay

**Actual computation date:** 2026-11-16.
**Source:** [verified research workflow 43878903914](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43878903914).
**Scientific level:** synthetic mathematical computation and
out-of-sample *synthetic price* scenario evaluation, **NOT**
observed market, biogas-engine or heat-delivery data.

The research source, original HiGHS/MILP schedules, **both reference
and wide price envelopes**, three held-out prices per case,
counterfactual perfect-information schedules, and separate independent
physics/KKT verification JSON are attached to the workflow run.
The 12 targeted adversarial tests passed.
The same original source-verified workflow also produces
four normalized vector SVG charts
(`reference` and `wide_stress` for exact rectangular
worst-case and selected held-out mean modeled €/h).
The figures have no statistical probability interpretation
and are archived separately from the source and witness JSON.

## Audited numerical coverage

| Scientific check | Executed result |
|---|---:|
| Predeclared train price seeds | 2 (11, 37) |
| Explicit uncertainty-set severities | 2 (`reference` and `wide_stress`) |
| Main horizons | 24 / 96 / 192 quarter-hours (6/24/48 h) |
| Additional exact global binary proof | Two independent 8-slot price-band cases |
| Total complete mathematical cases | **14** |
| Ex-ante frozen nominal and maximin schedules | **28** |
| Held-out generated price paths | **42** |
| Physical 15-minute records independently rechecked | **6,320** |
| Separate fixed-binary LP/KKT witnesses | **70** |
| Exact eight-slot global MILP enumeration certificates | **4** |
| Eight-slot binary patterns considered per certificate | **256** |
| Passed independent small/adversarial unit tests | **11** |

The independent verifier status was
`PASS_BOUNDED_PRICE_ROBUST_CHRONOLOGY_AND_INDEPENDENT_REPLAY_CERTIFICATES`.
The 24-, 96- and 192-quarter binary MILP global solutions rely on
**solver-reported global optimum and MIP gap**, while their physical
feasibility and fixed-pattern continuous LP optimality were verified
separately. There is no claim of independently exhausting all binary
patterns at these longer horizons.

## Full cross-design results: exact rectangular worst case

All amounts are **fictional six-hour, day or two-day modeled
contribution in EUR**, not realized electricity revenue
or investment returns. The *rectangular worst case* mathematically
allows every quarter-hour price to equal its lower bound
**simultaneously**, potentially an extremely conservative
joint price trajectory.

| Train seed | Horizon | Price bound class | Nominal policy worst case (EUR) | Robust policy worst case (EUR) | Guaranteed model uplift (EUR) |
|---|---:|---|---:|---:|---:|
| 11 | 6 h | reference | 123.754 | 123.754 | 0.000 |
| 11 | 6 h | wide_stress | −9.663 | **3.713** | 13.375 |
| 11 | 24 h | reference | 510.679 | 510.679 | 0.000 |
| 11 | 24 h | wide_stress | −39.438 | **15.112** | 54.550 |
| 11 | 48 h | reference | 1026.579 | 1026.579 | 0.000 |
| 11 | 48 h | wide_stress | −79.138 | **30.312** | 109.450 |
| 37 | 6 h | reference | 122.413 | 122.413 | 0.000 |
| 37 | 6 h | wide_stress | −10.862 | **2.825** | 13.688 |
| 37 | 24 h | reference | 505.250 | 505.250 | 0.000 |
| 37 | 24 h | wide_stress | −44.238 | **11.400** | 55.638 |
| 37 | 48 h | reference | 1015.700 | 1015.700 | 0.000 |
| 37 | 48 h | wide_stress | −88.738 | **22.800** | 111.538 |

This is the precise mathematical maximin guarantee under
the **declared synthetic rectangular uncertainty**. It does
not establish any lower bound on actual biogas-CHP earnings.
The original *reference* band produced essentially the
same policy outcomes; this scientifically meaningful
negative result was retained instead of being deleted.

## Out-of-sample evaluation of the immutable policies

The following are **arithmetic means of exactly three named,
deterministically generated held-out paths** (101, 211, 307)
per train/horizon/band case. They are **not estimates of
probability-weighted expected revenue**. Hold-out prices were
generated only after both ex-ante policy decisions were fixed.

| Train seed | Horizon | Bound class | Nominal frozen policy, held-out arithmetic mean (EUR) | Robust frozen policy, held-out arithmetic mean (EUR) |
|---|---:|---|---:|---:|
| 11 | 6 h | reference | 251.070 | 251.070 |
| 11 | 6 h | wide_stress | **253.433** | 188.716 |
| 11 | 24 h | reference | 1025.803 | 1025.803 |
| 11 | 24 h | wide_stress | **1027.132** | 762.988 |
| 11 | 48 h | reference | 2054.348 | 2054.348 |
| 11 | 48 h | wide_stress | **2049.483** | 1518.109 |
| 37 | 6 h | reference | 253.194 | 253.194 |
| 37 | 6 h | wide_stress | **259.292** | 207.309 |
| 37 | 24 h | reference | 1017.632 | 1017.632 |
| 37 | 24 h | wide_stress | **1015.918** | 767.881 |
| 37 | 48 h | reference | 2039.090 | 2039.090 |
| 37 | 48 h | wide_stress | **2029.281** | 1521.764 |

**Interpretation:** The very wide price envelope generates a
deliberately pessimistic mathematical adversary. Its robust
schedule sacrifices modeled price arbitrage to increase the
guaranteed lower contribution. The three selected held-out
price paths did not jointly approach the envelope's extreme
worst-case prices: consequently the nominal schedule earned
more on **all six wide-band summary comparisons**.

That is a genuine **robustness versus selected realized
performance trade-off**, not an algorithmic failure and
not evidence that the robust schedule is financially inferior
in actual electricity trading. The result depends entirely on
the assumed uncertainty-set geometry and the chosen hold-out
paths. The severity-band expansion was made after the initial
reference-only null result and is disclosed transparently.

### 24-hour worked example: training seed 11

- Hypothetical uncertain prices: high base-price quarters
  may fall by as much as €115/MWh under `wide_stress`.
- Guaranteed worst-case contribution:
  nominal **−€39.4375** vs maximin **+€15.1125**;
  a provable gain of **€54.5500** under the defined rectangle.
- Selected held-out mean contribution:
  nominal **€1027.1318**, maximin **€762.9879**.
- Selected held-out mean hindsight regret:
  nominal **€97.1362**, maximin **€361.2801**.
- The hindsight optimum is **nonoperational**: it is computed
  after disclosure of each held-out price path to provide
  an upper-performance reference only.


## Scientific evidence boundary

The unmodified v0.9.7 CHP MILP calculates **generator-terminal
electricity**, not electricity measured or settled at the
grid connection. Price selection is hypothetical rather than
source-verified at bidding gate closure. The modeled heat
demand, backup costs, gas production, generator power efficiency,
storage capacity, min-up/down and startup transients are **not
calibrated to a manufacturer or actual site**.

The uncertainty bands are **hand-specified rectangular
stress sets**, not empirically estimated distribution,
confidence bounds, wind/weather uncertainty,
biogas production process variation or physical
equipment outage models. With simultaneous intervalwise
lower price extremes the robust guarantee may be
unrealistically conservative, so **no real reliability
probability, risk quantile, expected monetary value or
industrial production profit** is claimed.

The independent KKT auditor uses a separately derived
LP mathematical formulation but the same
SciPy/HiGHS numerical backend. It is not independent
linear optimization software. The 8-slot global binary
enumeration is restricted to the two small stress cases.

The [predeclared research protocol](../docs/V0920_RECTANGULAR_PRICE_ROBUSTNESS_HELDOUT_PROTOCOL.md)
records all 14 cases, fixed information-set chronology,
formulas, limits, solver-certification distinctions and
reproduction commands. This does **not** meet scientific
v1.0 physical CHP/biogas field validation requirements.
