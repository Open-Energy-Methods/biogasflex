# Independent technical audit — v0.5 baseline

Date: 2026-11-05. Reviewer: ChatGPT, separate critical re-derivation and code inspection, **not an independent human peer reviewer**. Baseline code and test suite examined without treating its reported results as proof.

## Verified

- For config `baseline.json`: gas = 0.6 MW LHV, electric efficiency 0.4, thermal efficiency 0.45, rating 0.4 MWe; electrical power = 0.24 MW. Over four one-hour synthetic intervals, gas=2.4 MWh, electric=0.96 MWh, potential heat=1.08 MWh, and price dot-product produces EUR15.60.
- Published SVK SE3 day-ahead price 2020-01-01: 24 records, local-day boundaries UTC 2019-12-31 23:00 to 2020-01-01 22:00. Sum of hourly quotes 665.68 EUR/MWh, mean 27.736666667 EUR/MWh. Illustrative 0.24 MW fixed generation gives EUR159.7632.
- Baseline rejects non-finite prices and invalid efficiency sums; allows legitimate negative spot prices. Timestamp conversion uses UTC; DST unit tests cover local-day selection.
- New Lövsta case electric mean = 3,002.6 MWh / 8,760h = 0.342762557 MW, rated = 0.499 MW, nominal capacity factor 68.6899%. Assumed LHV gas input = 0.856906393 MW for electric efficiency 40%; heat coefficient is algebraically aligned to annual heat:electric output ratio; electricity at 2020 observed hourly prices gives EUR228.170179 **hypothetical spot-equivalent value**, not actual plant receipts.

## Independent audit findings and remaining limitations

1. **Unresolved:** Original `parse_prices` infers final-row interval from preceding gap. A truncated series can pass if the caller omits `required_hours`; observed execution enforces 24 h, but general time windows must specify an end boundary or explicit interval duration. v0.6 should remove this ambiguity.
2. **Unresolved:** Baseline's lack of CHP ramp limits, gas buffer, useful heat constraints, gas leakage/flaring, minimum load, startup limits and dynamic production means it **cannot** be interpreted as demonstrated flexibility or plant-validated operations.
3. **Unresolved:** A locally chosen representative day and year-mixed measured/assumed plant case are educational demonstrators, not an empirical estimate of annual economic benefits.
4. **Unresolved:** No operator-verified Lövsta data rights or hour-level calibration. Plant facts come from academic thesis, with facility-provided 2022 figures cited.
5. **Independent check status:** This is a documented second-pass numerical/code audit by an AI assistant, not a signature from an unaffiliated expert or peer-reviewed publication. An independent human technical review is **still open**.

## Release gate recommendation

v0.5 source-backed fixed-baseline **candidate**: conditional pass for publicly sourced plant rating/annual mean, public CC BY price data with attribution, offline reproducible numeric checks; no empirical plant calibration, no external human review, no production-grade market valuation. Keep those remaining gaps visible in all public descriptions.
