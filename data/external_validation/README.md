# External published CHP annual measurements — separate reference, not calibrated BiogasFlex physics

**Source:** Ciuła, J.; Kowalski, S.; Generowicz, A.; Barbusiński, K.; Matuszak, Z.; Gaska, K. *Analysis of Energy Generation Efficiency and Reliability of a Cogeneration Unit Powered by Biogas*, Energies (2023) **16**(5), 2180, DOI **10.3390/en16052180**, https://www.mdpi.com/1996-1073/16/5/2180 . Published 24 February 2023, article **CC BY 4.0**, © 2023 authors. **This file is a reformatted transcription** of 11 annual rows from Tables **2 and 3**; rated capacities from Table **1**. Attribution required.

All annual rows are publisher-reported *summaries of plant meter and operation records*, not raw calibrated instrument traces accessible in this repository. The study describes a **440 kW_e / 520 kW_th landfill-gas engine** at a municipal landfill. Rows contain the publication's running hours, recovered landfill-gas volumes, gross electricity generation and heat generation. We do **not** infer gas fuel LHV, measured electrical efficiency, start/stop ramp, minimum stable load, instantaneous export or control performance from these aggregates. The paper describes improved monitoring beginning in 2018; do not attribute between-period changes to dispatch alone.

## Reproducibility/data quality

* Source Table 2 (2012–2017) and Table 3 (2018–2022) annual values are retained exactly and frozen via SHA-256 in `examples/v0912_external_evidence.json` and the repository-wide checksum manifest.
* IMPORTANT SOURCE DISCREPANCY: Table 3 reports an average 2018–2022 recovered gas volume of **1,291,515 m³/year**, but recomputation from the *five published annual rows* gives **1,267,253.2 m³/year**, a difference of **24,261.8 m³/year**. Preserve this conflict; do not silently rewrite the published mean. Computed annual energy means agree with their reported values to usual rounding tolerance.
* Independent annual apparent operating powers are **E_electricity[MWh] / running_hours[h]**, similarly for heat; these are not maximum power or instantaneous stable/unstable operating envelopes. Rated capacity only supplies a plausibility reference. A 0.8 MW fictitious BiogasFlex model does not represent this 0.44 MW external reference plant.
* Article's Table 4 uses calculated efficiencies whose raw fuel composition is not available in the annual CSV, hence efficiency calibration is explicitly blocked.

**Scientific purpose:** external scale and aggregate accounting plausibility; not annual validation of the current dispatch predictions and certainly not independent hourly physical validation.
