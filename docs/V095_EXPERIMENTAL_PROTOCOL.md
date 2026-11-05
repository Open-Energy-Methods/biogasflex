# BiogasFlex v0.9.5 — experimental always-on operating envelope and synthetic price forecast regret

**Scientific status:** uncalibrated research-software experiment. No plant validation,
general unit-commitment model, independently peer-reviewed scientific finding,
public GitHub Release, or Zenodo DOI. v0.9.5 advances directly from
the merged v0.9.3 development baseline; **no v0.9.4 release is claimed**.

## Experimental CHP mathematical constraints

This opt-in module lives at `src/biogasflex/experimental_v095.py`.
All historic model source files and original 216+5 results are frozen.

Let `u_t` be gas use (MW_LHV), electrical output
`P_t = eta_e * u_t` (MW_e), gas stock (MWh_LHV), and `dt_t`
interval duration (hours). Original constraints on exact gas stock
conservation, cyclic terminal inventory, instantaneous CHP heat, heat
rejection and auxiliary heat meeting demand are preserved.

The new, *continuous always-on* constraints are:

```text
minimum_power_mw_e <= P_t <= rated_power_mw_e
P_t - P_(t-1) <= ramp_up_mw_e_per_hour * elapsed_h
P_(t-1) - P_t <= ramp_down_mw_e_per_hour * elapsed_h
```

Between intervals, `elapsed_h = (dt_(t-1)+dt_t)/2`,
measured between **interval midpoints**. For the first interval,
`initial_power_mw_e` is explicitly specified at its *start boundary*,
so `elapsed_h = dt_0/2` to the first midpoint. These are
average-output linear envelope constraints, **not validated engine ramp
physics or dispatch tracking trajectories**.

The minimum power applies in **every** interval. There is no on/off
binary, startup, shutdown, minimum-up/down, minimum stable load
switching, cold start, transient gas pressure, thermal storage or
control stability model. Calling it a *unit-commitment MILP* would be
incorrect.

The fixed-output, constant-gas-stock comparator must satisfy these
constraints or the experiment is rejected instead of issuing a
misleading uplift. The original unconstrained heat-aware LP
provides an upper bound on the new constrained optimum.

## Fixed schedule under forecast and realized electricity prices

The optional function `evaluate_fixed_forecast_schedule` optimizes the
same synthetic physical model using declared forecast prices, then holds
**all scheduled gas and heat flows fixed** and evaluates just the
electricity revenue at supplied realized prices:

```text
realized_committed_value = forecast_planned_contribution
    + sum_t eta_e * u_forecast_t * dt_t *
      (realized_price_t - forecast_price_t)

hindsight_regret = realized_perfect_foresight_optimum
    - realized_committed_value
```

The benchmark under realized prices is a *perfect-hindsight modeled
upper bound* using **the same** gas source, demand, costs, output
minimum and ramp limits. Forecast and realized interval start,
duration and market zone must match exactly. This is not live
forecasting, day-ahead bidding, market participation, probability
calibration, receding-horizon dispatch or measured financial loss.

## Entirely invented two-hour oracle

The files `examples/v095_toy_config.json`,
`examples/v095_toy_realized_prices.csv` and
`examples/v095_toy_forecast_prices.csv` are **100% synthetic**.
The illustrative gas conversion is 0.4 electrical efficiency, zero
thermal CHP efficiency with auxiliary heat supplied, 1 MW_LHV net gas,
0.8 MW_e generator, 0.5 MWh_LHV gas buffer, initial power
0.4 MW_e and two 1-hour spot prices of €0 and €100/MWh_e.

| Counterfactual experiment | Modeled incremental contribution |
|---|---:|
| Both output ramps zero | €0 |
| Ramp up/down 0.1 MW_e/hour | €5 |
| Loose ramps and 0.36 MW_e continuously-on floor | €4 |
| Loose ramps with no lower output floor | €20 |
| Opposite synthetic forecast, loose ramps | €40 ex-post perfect-foresight regret |

All contribution figures are synthetic modeled EUR over **two
intervals**, not commercial revenue or actual profit. A separate
positive-thermal-efficiency test audits CHP heat conservation.

`scripts/audit_v095_operational.py` checks 5 ramp-capacity points,
3 increasing minimum floors, price-regret oracles, gas conservation
and midpoint ramp inequalities for a separate **synthetic 24-hour
horizon**. It does not alter recorded original research results.

## Reproduce and inspect

```bash
python -m pip install -e .
bash scripts/reproduce_v095.sh
python -m biogasflex operating-surrogate
python -m biogasflex forecast-regret
```

On Windows PowerShell: `./scripts/reproduce_v095.ps1`.
The two experimental CLI commands **print summaries and do not write
files by default**. `--output filename.json` enables full opt-in
JSON output. The historical CLI endpoints retain their older behavior.

The gate must preserve 286 inherited scientific SHA-256 pins, all 216
original market-case dual LP checks, all 216+5 original market and
hypothetical-interruption reproductions, and the v0.9.3 96-case
solver-free synthetic two-interval suite.

### Nonclaims

This does not establish actual CHP ramp performance, startup limits,
heat demand measurements, plant export permissions, calibrated gas
buffer vessel operation, price-forecast performance, real plant
profitability/NPV/CAPEX, regional islanding or black start. The
external independent human methodological review remains open in
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).

**No public GitHub Release or Zenodo DOI is warranted by these
internal tests alone.**
