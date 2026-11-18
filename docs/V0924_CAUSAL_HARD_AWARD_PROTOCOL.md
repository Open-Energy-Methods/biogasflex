# v0.9.24 — Causal 15-minute hypothetical awarded-electricity service

**Status:** preregistered research protocol; NOT a verified historical bid/settlement strategy and NOT field-qualified CHP reliability.

## Objective and scientific dependency

Earlier BiogasFlex work introduced hard awarded electrical-energy equalities inside its interval optimization. The v0.9.22 source-verified controller then established causal hourly physical observations and the independently audited infeasible-hour mechanism. v0.9.23 independently demonstrated that an optional next-hour low-gas feasibility witness restored six-hour *unawarded* modeled operation on 29 previously infeasible held-out dates, without claiming market contracts. v0.9.24 asks a stricter question:

**Given an externally declared and accepted hypothetical 15-minute MWh export award, can a CHP controller both honor its physical commitments and maintain a next-source-hour low-gas reserve witness?**

The answer must never include silent award reductions, hidden imported electricity, negative gas inventory, fictitious gas purchases, unlimited energy curtailment, ramp exemptions, compensation for missing deliveries or invented market penalties. If the physical optimization has no solution, the contract-delivery service is explicitly **INFEASIBLE**, not zero profit or successful dispatch.

## Physical contract service and meter boundary

For each mathematical quarter-hour interval t (Δt = 0.25 hours), impose exactly:

[
\eta_e u_t \Delta t = A_t,
\quad \eta_e=0.4,
\quad u_t\text{ in MW}_{LHV},
\quad A_t\text{ in MWh}_e.
]

This is a hard linear equality in the primary causal LP. The frozen 24-slot binary CHP commitment, available gas-buffer state, 0–1.5 MWh_LHV stock bound, 0.5–2 MW_LHV ON-state fuel use, actual modeled thermal delivery, backup/dump limits and consecutive-ON 0.8 MW_e/h ramp are **not** weakened. No import or settlement slack is available. At each completed slot, a separate modeled positive export meter reports exactly **ηe·u·Δt MWh_e** and is audited against the award A_t.

The same already-known future contract is mandatory inside the v0.9.23 next-hour minimum-gas witness. If a reserve witness could choose lower electricity output than the accepted contract, it would certify reserve feasibility by illegally withholding previously promised service. Hence it also has exact **ηe·u'_q·Δt = A_{t+q}** for all four next-source-hour intervals. The witness is not executed or marketed; it is an explicit existential consistency test under the imposed synthetic gas floor.

**Meter convention:** the modeled meter is the CHP-generated electrical MWh at the selected idealized export boundary, assuming no parasitic station load, line losses, auxiliary import, net grid measurement corrections or actual cash settlement. This is a **model-generation/export proxy**, not a physical grid meter or validated market sale.

## Preregistered hypothetical awards

All awards are specified and SHA-256-frozen before target-day synthetic physical realizations or historical target-day cleared prices are revealed. The exact same 24-quarter-hour award schedule applies to each of the 92 chronologically eligible days. The source itself contains hourly regional price/load records, **not actual 15-minute awarded CHP energy**.

| Profile | Fixed 15-min A_t | Six-hour total | Declared purpose |
|---|---:|---:|---|
| floor_budget_0p090 | 0.090 MWh_e | 2.16 MWh_e | Conservative low synthetic gas budget illustration, not universal stock-robust guarantee |
| nominal_gas_0p100 | 0.100 MWh_e | 2.40 MWh_e | Matches 1 MW_LHV constant nominal gas burn with ηe=0.4 |
| initial_ramp_stress_0p150 | 0.150 MWh_e | 3.60 MWh_e | Intentionally conflicts with first-half-interval electric ramp from 0.4 MW_e |

The 0.090 MWh_e award corresponds to 0.9 MW_LHV fuel use and arises from the declared **hypothetical** floor 0.78 MW_LHV and initial 0.75 MWh_LHV fuel reserve over six hours: average affordable burn is at most 0.78+0.75/6 = 0.905 MW_LHV. Rounding down to 0.9 provides a transparent predeclared stress level. This protects against the **lower fuel energy budget** only; high gas arrivals can still overflow the 1.5 MWh_LHV buffer if gas disposal/other consumption are excluded.

The 0.150 MWh_e stress implies 0.6 MW_e output and exceeds the first half-interval permissible step from 0.4 MW_e when ramp is 0.8 MW_e/h (0.1 MW_e first-half-slot allowance). Its expected model infeasibility is a **required negative control**, not a model defect.

No profile is a claim that an actual Swedish bidding-zone market accepted these exports. No bidding opportunity, settlement, forecast contract penalty or real trading P&L follows from these hypothetical 15-minute arrays.

## Pre-reveal chronology

1. Load only source publisher-verified original data. Identify training/held-out period and verify that a full prior-seven-day price baseline exists for each complete UTC source day.
2. Independently predeclare all three constant 24-slot award vectors and their SHA-256 fingerprints without looking at the chosen target day.
3. Solve the unchanged nominal and paired source-block maximin **first-stage commitment** MILPs with training history and nominal forecasts. Lock binary commitment and award hashes before the held-out realization.
4. Reveal only the **current** source-hour synthetic gas rate and heat load during replay; each hourly record is mathematically held constant in four 15-minute control intervals. The controller knows the accepted future award vector and prior-seven-day price baseline, **not future actual** price/gas/heat. No original historical bid-time forecast vintage is claimed.
5. Compare two matched-contract operating controllers: (a) award-only causal LP and (b) award plus next-hour low synthetic gas reserve witness. The exact same award, frozen first-stage commitment and physical equipment are used. Neither may dilute awarded energy for fuel savings.
6. Report every failed service (day, profile, policy, mode, first hour, solver outcome), without imputing zero financial earnings to infeasible days.
7. For feasible days, verify all 24 interval-level CHP MWh, heat balance, gas stock, ramp, binary states and modeled ex-post contribution. **Do not** call ex-post cleared price multiplication actual market settlement.
8. Treat terminal-inventory-unmatched operation as noncomparable for matched-service economic comparisons. Keep those counts separate from successful contracted MWh delivery.

## Independent audits and no-go gates

A wholly separate standard-library source/physical ledger auditor is reused across all six profile/control-mode variants. Another independent auditor reconstructs every 15-minute **A_t = ηe·u·0.25** physical export and the entire accepted award SHA, rejects falsified meter and rejected-contract profit, and verifies that all executed next-hour reserve witness fuel inputs also produce the previously declared accepted award, at the model floor and original ramp/buffer constraints.

Tests must reject: nonsensical award size/nonfinite MWh, positive awards with an OFF commitment, zero award with an ON min load, ramp-impossible 0.150 MWh_e stress, future realized gas/heat/price leaking into earlier controls, forged modeled exports, altered or forged first-stage/award hashes and a reserve witness that lowers export secretly.

All full 92-day results must preserve both favorable and negative profiles. A finite historical synthetic comparison does not establish statistical market performance. Identical nominal versus maximin commitments remain a **scientifically important negative result**, not a reason to optimize sample-selection post hoc.

## Reproduce

Use the frozen original OPSD publisher archive, outside the checked-out tracked source files:

```bash
python -m biogasflex source-evidence-v0921 --csv /tmp/opsd_original_60min.csv --download --output /tmp/v0921_verified.json
python -m biogasflex.award_v0924 --source /tmp/v0921_verified.json --output /tmp/v0924_full_hypothetical_contracts.json
python scripts/audit_v0924_award_independent.py --source /tmp/v0921_verified.json --study /tmp/v0924_full_hypothetical_contracts.json --output /tmp/v0924_full_audit.json
```

**Research v1.0 relationship:** [scientific release gates](V1_0_SCIENTIFIC_RELEASE_GATES.md). Gate A3 passes only after the full model-service experiment and independent contract ledger audit are green, failed-service cases remain visible, and the scope statement is precise. An actual site-specific electricity award needs a signed or otherwise authorized source with time and granularity; cannot be manufactured from regional OPSD prices.
