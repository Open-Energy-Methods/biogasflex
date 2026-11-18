# BiogasFlex v0.9.26 — Independent physical and unit assurance protocol

**Scope:** frozen source-paired v0.9.21–v0.9.25 six-hour synthetic CHP system, not a new plant model or parameter calibration. The target is A5 research-software assurance. The historical original data remain regional hourly electricity price/load observations and not gas, heat, CHP or grid-export measurements.

## Independent physical boundary

The auditor imports no BiogasFlex solver. It independently converts all emitted flows from MW to W and stocks and awards from MWh to J, with each mathematical quarter-hour 900 s. Fuel quantities are on a lower-heating-value (LHV) energy basis, not kilograms or standard cubic metres. In each executed interval:

    delta_S = (G_in - U) * dt
    P_e = eta_e * U
    Q_recovered = eta_h * U
    Q_unrecovered = U - P_e - Q_recovered
    Q_useful + Q_external_backup = Q_demand
    Q_useful + Q_dump = Q_recovered

Consequently:

    G_in*dt + Q_external_backup*dt =
      delta_S + (P_e + Q_demand + Q_dump + Q_unrecovered)*dt

This whole modeled boundary is also checked cumulatively across the executed prefix, including a failed prefix. The unrecovered LHV term (0.4 of modeled burn) is an algebraic remainder, NOT measured stack loss, cooling-system load, or a validated total-engine heat rejection map. The external backup boundary is delivered heat; fuel and conversion losses of the backup source are outside the model. Generator gross electrical delivery is the idealized contract proxy only; auxiliary loads and physical net meter exports are not quantified.

The initial fuel inventory is 0.75 MWh_LHV; capacity 1.50 MWh_LHV in the frozen parent configuration. The sensitivity changes from v0.9.25 are not substituted into this validation. Initial gross power 0.4 MW_e; consecutive-ON midpoint ramp 0.8 MW_e/h (first interval half-duration); switching events have costs but no dynamic startup/shutdown energy model. Useful heat service, heat-recovery split, backup and dump ratings, on-state electrical limits, stock limits, and exact **hypothetical** interval-award meter are all checked. No pressure, volume, mass, latent fuel loss, venting, settlement penalty, or imported electricity is invented.

## Unit-specific tolerances

Independently expressed numerical allowances inherited from the existing model:
- Energy balance/local stock allowance: 180,000 J (5e-5 MWh).
- Power/rating/ramp allowance: 50 W (5e-5 MW).
- Exact award meter allowance: 1,800 J (5e-7 MWh).
- Whole energy boundary uses the combined local balance allowances; full prefix balances use summed worst-case allowance over the prefix. Certificate reports actual maximum absolute residuals separately for each tested group.
- Legacy cyclic inventory threshold remains 5e-5 MWh_LHV.

These are numerical comparison thresholds, **not measurement uncertainties or proof of thermal accuracy**.

## Parameter and provenance assurance

The machine-readable register at data/evidence/v0926_physical_parameter_register.json lists all 23 selected numerical model constants, their native units, model-assumption source, derived quantities, explicitly uncalibrated proxy ranges and field evidence gaps. The independent checker reads literal constants from the frozen joint_v0921.py abstract syntax tree without executing that model, compares independent expected values and units, and rejects false calibration declarations and altered values.

The inherited v0.9.16 public CHP source registry contains two distinct external reference identities: Luleå biogas SOFC (DOI 10.5281/zenodo.14163174) and Kitakyushu city-gas engine/fuel-cell dataset (DOI 10.6084/m9.figshare.24978645.v2). Neither is a calibration of this synthetic gas-engine CHP system. The current gate does not retrieve or infer new manufacturer numbers, and does not use these external datasets to fit any target parameter.

## Evaluation and acceptance

1. Publisher-original OPSD SHA verification and all 92 unchanged eligible source days.
2. Reproduce full parent v0.9.23 reserve and v0.9.24 award studies; independently rerun their existing source/physical ledgers and reserve/award checks.
3. Independently audit every executed interval (including partial failed prefixes) and all full horizon/terminal flags in the two reserve-control modes and six award-profile/control-mode groups, with both original commitment policies.
4. Record per-group counts, maximum residuals in J, failed cases and terminal matches. No revenue is attributed to an incomplete service path.
5. Test tampering: MW versus MWh, altered stock, double-counted recovered heat, ramp, nonfinite quantity, terminal flag, wrong calibration status and source literal.
6. Six OS/Python configurations and complete SHA manifest coverage; independent source job may run concurrently. A fully green current commit is separately required before software integration.

The original v0.9.25 sensitivity remains unchanged; this gate is a second independent unit and physical assurance layer, NOT a new contract-aware optimizer. A5 does not resolve the nondegenerate gas-input/terminal-stock conflict under fixed export, nor the missing field evidence.

## Reproduction

    python -m biogasflex source-evidence-v0921 --csv /tmp/opsd.csv --download --output /tmp/source.json
    python -m biogasflex.viability_v0923 --source /tmp/source.json --output /tmp/reserve.json
    python -m biogasflex.award_v0924 --source /tmp/source.json --output /tmp/award.json
    python scripts/audit_v0926_physical_si.py --source /tmp/source.json --reserve /tmp/reserve.json --award /tmp/award.json --output /tmp/si_audit.json

## Field no-go

No gas mass conservation claim without composition, LHV reference conditions and flow; no gas-holder pressure safety without P/V/T or controls; no true net-grid export or backup fuel claims; no startup/shutdown dynamics or measured ramp; no site calibration, calibrated uncertainty, authentic market awards or forecast issue vintages. These specific evidence gaps are explicitly preserved in the parameter register. Research software v1.0 still needs A6–A8 and the independent external review.
