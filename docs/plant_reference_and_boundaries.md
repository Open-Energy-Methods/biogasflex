# Plant evidence — SLU Lövsta reference case

## Evidence found (secondary university thesis reporting facility-provided data)

Source: Alexander Åberg (2024), *Förstudie av småskalig tillverkning av kvävegödsel med plasmateknik*, SLU, §5.4.1, Table 1, https://stud.epsilon.slu.se/20493/1/aberg-a-20240904.pdf . Source attributes table to Lövsta 2022 operating records:

- CHP motor maximum electric rating: **499 kW**.
- Electricity generation **3,002.6 MWh during 2022**; implied calendar-year average **342.7626 kW**, based on 8,760 hours.
- Heat production **2,939.5 MWh during 2022** (not independently verified as exportable district heat).
- Annual biogas volume **1,466,062 Nm³** and average methane proportion **54%**, which cannot be used as exact CHP fuel consumption without source-specific mass balance, allocation and standard conditions.
- Digester heat need **347 MWh**, identified separately. No freely available hourly generation or heat-service time series verified.

A separate SLU brochure describes the plant as approximately 500 kW and uses annual approximations. We use the detailed thesis figures with year and provenance instead of treating rounded brochure claims as reconciled actual production.

## Counterfactual model decisions (not observations)

- Continuous CHP output is **annual 2022 electricity divided by 8,760 hours** and applied to a separate **2020-01-01 SE3 spot-price** day. This is a *uniform annual-average counterfactual*, not recorded operation.
- Nominal electric rating uses the thesis **499 kWe**. Thus annual-average electric output/nameplate = 68.69%; indicative upward nameplate headroom = 31.31%. This annual ratio is not a directly observed hourly capacity factor or actual spare dispatch capability.
- Gas input is back-calculated assuming 40% electrical efficiency, yielding **0.8569064 MW LHV**. Do not treat this inferred input as a physical gas-meter measurement. Do not calculate an empirically validated electrical efficiency from the coarse gas production volume alone.
- Heat coefficient is algebraically selected to preserve the reported annual heat:electric output ratio, giving **0.391594**; it is not an independently established measured heat recovery efficiency.
- Revenue uses market prices as a notional *gross spot-equivalent generation value*. SLU uses much of its production on site; actual exported energy, negotiated tariffs, taxes, imbalance fees, heat revenue and operating costs are all unknown.
- The model has **no verified gas-buffer volume, start-up behaviour, actual gas output trajectory, CHP heat obligations or physical flexibility potential**. v0.6 must use explicit engineering scenarios, not label them real Lövsta flexible-operation data.

## Remaining data gap

SLU site confirmation of current capacity, metered fuel-to-CHP, hourly electric and useful heat output, storage configuration and on-site consumption/export breakdown would be necessary to calibrate or validate a site-specific plant model. No such data or permission has been obtained. Therefore v0.5 can pass the **source-supported rating and annual-benchmark** gate, but not the **plant-validated dispatch** gate.
