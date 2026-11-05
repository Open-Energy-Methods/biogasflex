# v0.6 modelling contract, source boundary and audit decisions

**Scope:** Hourly/quarter-hour resolution gas-energy storage LP; constant or specified gas production series; optional **fixed external** flaring/losses; gross electricity price-timing opportunity.

**Input metadata:** source-specific plant `config/v06_lovsta_counterfactual.json` combines *documented* 2022 nameplate and annual figures with *assumed* 40% electrical efficiency, hypothetical constant feed and hypothetical storage. 2020 observed SE3 price data are separate. The source evidence does not attest hourly plant dispatch, headroom availability at particular hours, useful heat delivered, CHP operating envelope, or storage tank capacity.

**Technology choice:** Original roadmap suggested Pyomo/HiGHS. Current implementation uses SciPy/HiGHS directly as a continuous LP: Pyomo is not a dependency and MILP is not appropriate without discrete commitment constraints. Swapping solver interface requires re-running the frozen oracle and audit checks.

**Time:** v0.6 requires an explicit UTC end boundary to avoid the v0.5 parser's last-interval inference. No local-time time-series join is used. All energy balance and revenue calculations multiply by explicit time-step durations.

**Thermal boundary:** Potential `Q_th=eta_th*U` can be calculated, but is not the same as delivered heat. A case may gain gross electricity revenue and simultaneously violate local heating requirements. Such feasibility is deferred to v0.7. Do not describe v0.6 as a CHP-service optimum.

**Economic boundary:** Prices are EUR/MWh_e and output is gross generator MWh_e. Every value is 'spot-equivalent' because actual net export is unknown. No cost, return, price forecast, market settlement, or investment decision is represented.

**Negative tests:** Incorrect configurations and infeasible or nonoptimal solver statuses must raise an exception. If an LP solution exists but the fixed comparator is infeasible at nameplate, no opportunity estimate is produced. With identical fixed F/L and cyclic storage, used gas must match across cases.

**Licence:** Reused Svenska kraftnät historic SE3 2020 day-ahead-price extract under CC BY 4.0. See `data/observed/README.md` for precise attribution, licence link and transformation notes.

**Review status:** Internal machine-run/AI-assisted code audit and analytic oracle passed; no human review, no measured plant model calibration or independent physical validation.
