# Decisions / open issues

- D-001: Use stylized CHP archetype rather than infer individual-plant sizing from national statistics. **Accepted.** Explicit assumption label.
- D-002: 2020-01-01 SE3 price day from Svk open data, 24 × 1-hour timestamps; avoids 2025 market-time-unit change and DST complexities in first observed regression. **Accepted as a bounded test window only.**
- D-003: Do not publish copied individual price records without an explicit rights decision. **Held; release rights unresolved.** Provide source retrieval client and open synthetic fixture.
- D-004: v0.5 is baseline only. No Pyomo optimizer is justified before baseline QA. **Accepted.**
- D-005: National biogas figures are background only; 85 GWh national electricity allocation does not size an individual CHP system. **Accepted.**
- D-006: A published named Swedish biogas CHP plant rating has **not** yet been verified. **Open.** The stylized alternative is an allowed v0.4 route, but v0.5 is not a plant-calibrated baseline.
- D-007: External independent review of implementation has not yet occurred. **Open.** Do not claim independent signoff.
