# BiogasFlex v0.9.14-A — Manufacturer-source and CHP operating-parameter evidence gate

**Status:** literature/vendor source *provenance and identifiability screen*,
not physical dispatch validation, a real manufacturer engine-performance
certificate, or external human methodological review.

## Reproducible data boundary

`data/evidence/v0914_chp_parameter_register.json` is the version-controlled,
machine-readable evidence register. Its 29 entries refer to **three distinct**
identities, and may never be pooled into one manufacturer's operating
envelope without a verified engine-identification record.

| Evidence identity | Fuel/site | Sources and limits |
|---|---|---|
| `ciula_landfill_chp` | Polish municipal landfill gas (published site, engine **make/model unknown**) | Ciuła et al. (2023) Table 1: **440 kW_e** rating, **520 kW_th** rating, nominal **37.6% electrical**, **42.8% thermal**; Tables 2–3: 2012–2022 annual observations |
| `cat_cg132b8` | Caterpillar **catalogue candidate**, not identified as site's engine | Continuous **400 ekW** at 1.0 power factor; max electrical efficiency presented as **43.1% / 42.1%** without selecting a single operating condition from the extracted page; multiple advertised fuel types |
| `jenbacher_j312` | INNIO Jenbacher **catalogue candidate**, not identified as site's engine | Website says electrical output **up to 635 kW**, electrical efficiency **up to 43.1%**; reference biogas/sewage composition 65% methane, landfill version 55% methane; full-load, gas and emissions dependent |

### Primary attributable sources (reviewed 2026-11-15)

1. [Ciuła et al., *Energies* 16(5) (2023) 2180, DOI 10.3390/en16052180](https://doi.org/10.3390/en16052180): Table 1, Tables 2–3. The existing v0.9.12 CSV is source-pinned and **not** replaced.
2. [Caterpillar CG132B-8 manufacturer specifications](https://www.cat.com/en_GB/products/new/power-systems/electric-power/gas-generator-sets/15969935.html): generator-set continuous rating, fuel list and dual slash-separated maximum efficiency values. **No exact configuration assignment for the two numbers is asserted.**
3. [Jenbacher J312 manufacturer product page](https://www.jenbacher.com/en/gas-engines/type-3/j312/): full-load and fuel-reference notes, including generator-terminal boundary and manufacturer-stated qualifications. `up to` values are *catalogue envelope* statements, not measured operating points of the Polish installation.

**Source revision limitation:** These are reviewed online pages, not downloaded/signed
full-page archival snapshots. Manufacturer webpages may change. No release-time
manufacturer-authenticated dated specification revision is held. Their values
are explicitly `REFERENCE_ONLY` and cannot be substituted for engine-specific
site commissioning curves, nor used as uncertainty distributions.

## Parameter classification and admissibility

Every record declares ID, physical equipment identity, parameter name, value
(or `null` where not available), units, page/table source/locator,
provenance class, temporal resolution, permitted use, interpretation and
explicit limitation.

- `SOURCE_SITE_STATIC_SCREEN`: **only** the Polish installation's 440 kW_e
  and 520 kW_th site nameplate entries, for capacity sanity checks of that
  same site. No dynamic feasibility inference.
- `REFERENCE_ONLY`: paper's other annual/nominal entries and vendor catalogue
  examples. Vendor maximum/efficiency statements are **not** minima,
  ramp rates or part-load curves.
- `BLOCKED`: numerical or interval inference from missing/unidentified
  parameters. `value`, `source_id` and `source_locator` must be `null`.
  The audit refuses unauthorized filling.

### Explicitly unidentifiable with these admitted sources (14 gaps)

Minimum stable electrical load; upward/downward ramps; minimum uptime and
downtime; start costs; electric efficiency vs load; recoverable heat vs load;
usable gas buffer in MWh_LHV; chronological heat demand; actual gas consumed
by engine vs merely *recovered* landfill gas; net grid export; dated outages;
and time-resolved LHV/fuel composition.

**Why these are not identifiable:** An annual energy measurement gives
`E = integral(P(t) dt)`. A running-hours total gives
`H_on = integral(1[P(t)>0] dt)`. Different physically possible power
sequences, with different ramps, starts, downtime and heat demand,
can produce the same `E` and `H_on`. An independent constructive witness
compares [0.20, 0.20, 0.20, 0.20] MW with
[0.10, 0.30, 0.10, 0.30] MW in four equal-hour slots: both deliver
0.8 MWh with four running hours under the 0.44 MW nameplate, but
only the second has 0.20 MW/h adjacent changes. A separate example
has identical energy/running hours with one versus two starts.
These are mathematical non-identifiability counterexamples, **not
empirically feasible engine trajectories**. Neither a unique intraday power
trace nor a unique minimum-load/ramp envelope follows. The paper's
nominal efficiencies do not supply fuel-flow vs power calibration.
Published *recovered* landfill-gas volume need not be all engine fuel.
The annual CHP plant and the manufacturer catalogue engines are different
unverified identities. There is **no justified transfer** to Swedish Lövsta
or the fictional v0.9.11 accepted-electricity example.

Do not turn "unknown" into zero, nameplate, annual average, vendor maximum,
or even a narrow deterministic sensitivity assumption without declaring
the assumption **hypothetical**.

## Fail-closed software and independent verification

```bash
python -m pip install -e .
python -m biogasflex chp-evidence-register
python -m biogasflex chp-evidence-register --output register_audit.json
python scripts/audit_v0914_chp_sources.py
python -m unittest tests.test_v0914_chp_evidence -v
bash scripts/reproduce_v0914.sh
```

Windows: `./scripts/reproduce_v0914.ps1`.

- Internal validator checks source IDs, canonical links, disjoint equipment
  identity, original annual CSV, reference numerical values, units and source
  claims; rejects role swaps, fake manufacturer/site matches and promoted
  unidentified dynamic parameters.
- Independent solver-free audit separately checks named facts and source
  applicability using standard-library JSON/CSV only.
- Release SHA-256 manifest enforces file coverage, and the preexisting
  286 original scientific files, 216 dual certificates, 96 independent LP
  oracles, v0.9.11 contract solver, and v0.9.12 observations are inherited.
- No manufacturer's dynamic data or equipment-specific part-load maps have
  been verified. No new physical optimality, financial or operational claim
  may be attached to this register. No changes are made to the MILP
  configuration or any historical case results.

## Gate to v0.9.14-B: mathematical identifiability and bounded sensitivity

Only after this evidence classification can hypothetical parameters be
explored. The next step is a **predeclared factorial/sensitivity design**,
with labeled hypothetical ranges, physically checked model feasibility,
negative cases, carefully limited intervals and quantitative
parameter-attribution checks. An individual plant-calibrated scenario
requires serial-number/model-specific and time-resolved data:
generator-terminal electrical output and net export, measured engine fuel
LHV and flow, heat source/sink temperatures and flows, start-stop event
logs, load setpoints, network/ambient states, and uncertainty budgets.
A 440 kW paper nominal paired to 400/635 kW vendor figures does not qualify.

**Release identity:** v0.9.14-A is a verified research evidence gate only,
not completion of model identifiability, robust dispatch, engineering hardware
qualification, external human peer review, or scientific v1.0.
