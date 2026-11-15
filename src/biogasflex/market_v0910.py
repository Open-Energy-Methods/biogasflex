"""BiogasFlex v0.9.10: explicit day-ahead information and contracted-volume boundary.

Two deliberately separate phases:
- PRE-CLEARING: an EXOGENOUS hypothetical single-period sell offer made
  with forecast information explicitly dated before gate closure. This
  API has no clearing price, auction outcome, or actual price argument.
- POST-CLEARING: exogenous, explicitly hypothetical accepted volumes
  and cleared prices, revealed to the participant before an operating
  decision. Validate exact modelled output against the contract;
  FAIL CLOSED on any mismatched volume (imbalance NOT modelled).

Not a market-clearing algorithm, a genuine accepted exchange order,
a live market participant, actual electricity export, intraday trading,
a nomination interface, balancing settlement, physical CHP calibration,
or evidence of market profits. Only a gross cashflow proxy is calculated.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from .baseline import Interval
from .dispatch import DispatchError
from .experimental_v098 import optimize_commitment_milp

MODEL = "preclearing_postclearing_exogenous_award_synthetic_chp_v0910"
LOCAL_ZONE = ZoneInfo("Europe/Stockholm")
TOL_MWH = 1e-7
PRE_FIELDS = frozenset({
    "forecast_issued_utc", "bid_decided_utc", "bid_submitted_utc",
    "forecast_prices_eur_mwh", "offered_mwh", "forecast_provenance",
})
POST_FIELDS = frozenset({
    "prices_published_utc", "participant_result_received_utc",
    "dispatch_plan_created_utc", "accepted_mwh", "clearing_prices_eur_mwh",
    "award_provenance",
})
MARKET_FIELDS = frozenset({
    "bidding_zone", "delivery_local_date", "auction_gate_close_utc",
})
SLOT_FIELDS = frozenset({"start_utc", "duration_hours"})


class MarketBoundaryError(ValueError):
    """A timing, information, contract, or unmodelled imbalance gate failed."""


def _fields(data: Any, required: frozenset[str], name: str) -> dict:
    if not isinstance(data, dict) or set(data) != required:
        raise MarketBoundaryError(f"{name} must declare exactly {sorted(required)}")
    return data


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise MarketBoundaryError(f"{label}: explicit UTC ISO timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketBoundaryError(f"{label}: invalid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise MarketBoundaryError(f"{label}: naive or non-UTC timestamp rejected")
    return parsed.astimezone(timezone.utc)


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MarketBoundaryError(f"{label}: finite numerical value required")
    v = float(value)
    if not math.isfinite(v) or (nonnegative and v < 0):
        raise MarketBoundaryError(f"{label}: invalid nonfinite or negative value")
    return v


def _values(data: Any, n: int, label: str, *, nonnegative: bool = False) -> list[float]:
    if not isinstance(data, list) or len(data) != n:
        raise MarketBoundaryError(f"{label}: expected exactly {n} values")
    return [_number(v, f"{label}[{i}]", nonnegative=nonnegative)
            for i, v in enumerate(data)]


def _market(market: dict) -> tuple[str, date, datetime]:
    _fields(market, MARKET_FIELDS, "market")
    zone = market["bidding_zone"]
    if not isinstance(zone, str) or zone not in {"SE1", "SE2", "SE3", "SE4"}:
        raise MarketBoundaryError("v0.9.10 currently supports explicit Swedish bidding zones only")
    ds = market["delivery_local_date"]
    if not isinstance(ds, str) or len(ds) != 10:
        raise MarketBoundaryError("Explicit YYYY-MM-DD Stockholm delivery date required")
    try:
        delivery_day = date.fromisoformat(ds)
    except ValueError as exc:
        raise MarketBoundaryError("Invalid delivery local date") from exc
    gate = _utc(market["auction_gate_close_utc"], "auction_gate_close_utc")
    if gate.astimezone(LOCAL_ZONE).date() != delivery_day-timedelta(days=1):
        raise MarketBoundaryError("Day-ahead gate must be on previous Stockholm civil date")
    return zone, delivery_day, gate


def _slots(market: dict, declared: Any) -> list[tuple[datetime, float]]:
    _, local_day, gate = _market(market)
    if not isinstance(declared, list) or not declared:
        raise MarketBoundaryError("Explicit nonempty delivery slot array required")
    slots = []
    for k, item in enumerate(declared):
        _fields(item, SLOT_FIELDS, f"slots[{k}]")
        start = _utc(item["start_utc"], f"slots[{k}].start_utc")
        duration = _number(item["duration_hours"], f"slots[{k}].duration_hours")
        if duration not in (0.25, 1.0):
            raise MarketBoundaryError("Only declared 15-minute / 60-minute intervals supported")
        end = start + timedelta(hours=duration)
        if start <= gate or start.astimezone(LOCAL_ZONE).date() != local_day:
            raise MarketBoundaryError("Delivery must follow gate on declared local day")
        local_end = end.astimezone(LOCAL_ZONE)
        if local_end.date() != local_day and not (
            local_end.date() == local_day + timedelta(days=1)
            and local_end.hour == 0 and local_end.minute == 0
            and local_end.second == 0
        ):
            raise MarketBoundaryError("Delivery interval crosses local-day boundary")
        if slots and slots[-1][0]+timedelta(hours=slots[-1][1]) != start:
            raise MarketBoundaryError("Delivery slots must be UTC-contiguous, sorted and nonduplicated")
        slots.append((start, duration))
    return slots


def _digest(payload: dict) -> str:
    return sha256(json.dumps(payload, allow_nan=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_preclearing_offer(
    market: dict, declared_slots: list[dict], offer: dict, rating_mw_e: float,
) -> dict[str, Any]:
    """Pre-clearing API: cannot take realized clearing prices or accepted volume.

    Input data labelled 'forecast' remain user-declared assumptions:
    an as-of timestamp alone cannot prove a true ex-ante dataset existed.
    """
    slots = _slots(market, declared_slots)
    _, delivery_day, gate = _market(market)
    _fields(offer, PRE_FIELDS, "preclearing offer")
    issued = _utc(offer["forecast_issued_utc"], "forecast_issued_utc")
    decided = _utc(offer["bid_decided_utc"], "bid_decided_utc")
    submitted = _utc(offer["bid_submitted_utc"], "bid_submitted_utc")
    if not issued <= decided <= submitted < gate:
        raise MarketBoundaryError("Forecast/bid as-of order must precede strict gate closure")
    if offer["forecast_provenance"] != "SYNTHETIC_PREAUCTION_ASSUMPTIONS":
        raise MarketBoundaryError("No verified external forecast feed in v0.9.10")
    rating = _number(rating_mw_e, "hypothetical nameplate MW_e")
    if rating <= 0:
        raise MarketBoundaryError("Nameplate must be strictly positive")
    n = len(slots)
    predictions = _values(offer["forecast_prices_eur_mwh"], n, "preauction forecasts")
    volumes = _values(offer["offered_mwh"], n, "offered electric energy", nonnegative=True)
    for i, ((_, hours), volume) in enumerate(zip(slots, volumes)):
        if volume > rating*hours+TOL_MWH:
            raise MarketBoundaryError(f"Offer[{i}] exceeds assumed CHP nameplate")
    receipt = {
        "version": "0.9.10",
        "model_type": MODEL,
        "phase": "PRE_CLEARING_EXOGENOUS_OFFER_VALIDATED",
        "bidding_zone": market["bidding_zone"],
        "delivery_local_date": delivery_day.isoformat(),
        "gate_close_utc": gate.isoformat(),
        "forecast_issued_utc": issued.isoformat(),
        "bid_decided_utc": decided.isoformat(),
        "bid_submitted_utc": submitted.isoformat(),
        "forecast_provenance": offer["forecast_provenance"],
        "hypothetical_nameplate_mw_e": rating,
        "offered_mwh": volumes,
        "forecast_prices_eur_mwh": predictions,
        "delivery_slots": [
            {"start_utc": start.isoformat(), "duration_hours": hours}
            for start, hours in slots
        ],
        "contract_status": "NOT_AWARDED_YET",
        "clearing_prices_available": False,
        "matched_energy_mwh": None,
        "cashflow_eur": None,
        "claim_limit": "Synthetic offer only; not an exchange order, bid optimizer or forecast validation",
    }
    receipt["sha256"] = _digest(receipt)
    return receipt


def audit_postclearing_delivery(
    market: dict, declared_slots: list[dict], pre_receipt: dict,
    award: dict, chp_config: dict, *, include_solver_details: bool = False,
) -> dict[str, Any]:
    """Compare exogenous auction award to exact validated synthetic CHP delivery.

    Every delivery interval must exactly meet the accepted volume.
    Any nonzero mismatch is an *unmodelled imbalance* and fails closed.
    """
    slots = _slots(market, declared_slots)
    _, _, gate = _market(market)
    if not isinstance(pre_receipt, dict):
        raise MarketBoundaryError("Pre-clearing receipt required")
    receipt = dict(pre_receipt)
    checksum = receipt.pop("sha256", None)
    if checksum != _digest(receipt) or receipt.get("phase") != "PRE_CLEARING_EXOGENOUS_OFFER_VALIDATED":
        raise MarketBoundaryError("Missing or modified preclearing receipt")
    expected = validate_preclearing_offer(
        market, declared_slots, {
            "forecast_issued_utc": receipt["forecast_issued_utc"],
            "bid_decided_utc": receipt["bid_decided_utc"],
            "bid_submitted_utc": receipt["bid_submitted_utc"],
            "forecast_prices_eur_mwh": receipt["forecast_prices_eur_mwh"],
            "offered_mwh": receipt["offered_mwh"],
            "forecast_provenance": receipt["forecast_provenance"],
        }, receipt["hypothetical_nameplate_mw_e"],
    )
    if pre_receipt != expected:
        raise MarketBoundaryError("Preclearing receipt does not match market/slot content")
    if not isinstance(chp_config, dict) or chp_config.get("price_zone") != market["bidding_zone"]:
        raise MarketBoundaryError("CHP config bidding zone differs from award zone")
    if _number(chp_config.get("electric_rating_mw"), "CHP config rating") != receipt["hypothetical_nameplate_mw_e"]:
        raise MarketBoundaryError("Nameplate changed after hypothetical offer submission")
    _fields(award, POST_FIELDS, "exogenous award")
    published = _utc(award["prices_published_utc"], "prices_published_utc")
    received = _utc(award["participant_result_received_utc"], "participant_result_received_utc")
    planned = _utc(award["dispatch_plan_created_utc"], "dispatch_plan_created_utc")
    if not (gate < published <= received <= planned < slots[0][0]):
        raise MarketBoundaryError("Auction result, participant notification and plan must follow gate and precede delivery")
    if award["award_provenance"] != "SYNTHETIC_EXOGENOUS_ACCEPTANCE":
        raise MarketBoundaryError("No verified participant-specific awards in v0.9.10")
    n = len(slots)
    accepted = _values(award["accepted_mwh"], n, "accepted electricity", nonnegative=True)
    prices = _values(award["clearing_prices_eur_mwh"], n, "clearing price")
    for i, (filled, offered) in enumerate(zip(accepted, receipt["offered_mwh"])):
        if filled > offered+TOL_MWH:
            raise MarketBoundaryError(f"Award[{i}] exceeds hypothetical submitted offer")
    market_prices = [
        Interval(start, price, hours, market["bidding_zone"])
        for (start, hours), price in zip(slots, prices)
    ]
    # Existing solver independently checks gas/heat, terminal stock, binary
    # commitment, dwell, elapsed-hour ramps and matched LP-relaxation bound.
    try:
        modelled = optimize_commitment_milp(chp_config, market_prices)
    except (DispatchError, ValueError) as exc:
        raise MarketBoundaryError("Postclear CHP dispatch could not satisfy physical model") from exc
    delivered = [float(x["power_mw_e"])*hours
                 for x, (_, hours) in zip(modelled["hourly"], slots)]
    max_error = max(abs(v-a) for v, a in zip(delivered, accepted))
    if max_error > TOL_MWH:
        raise MarketBoundaryError(
            f"UNMODELLED_IMBALANCE: contracted vs synthetic power differs by {max_error:.9g} MWh"
        )
    if any(abs(x["dt_h"]-hours)>1e-12
           or _utc(x["start_utc"], "solver.start_utc")!=start
           for x,(start,hours) in zip(modelled["hourly"],slots)):
        raise MarketBoundaryError("Solver delivery grid differs from contracted grid")
    ledger = modelled["optimized_dispatch"]
    for label in ("max_interval_balance_residual_mwh",
                  "max_heat_service_residual_mwh",
                  "terminal_inventory_residual_mwh"):
        if abs(float(ledger[label]))>TOL_MWH:
            raise MarketBoundaryError(f"Unverified modelled physical ledger: {label}")
    if not modelled["solver"]["success"] or modelled["max_steady_on_ramp_violation_mw_e"]>1e-7:
        raise MarketBoundaryError("Solver/ramp physical certification failed")
    gross = math.fsum(a*p for a,p in zip(accepted,prices))
    answer = {
        "version": "0.9.10",
        "model_type": MODEL,
        "phase": "POST_CLEARING_EXOGENOUS_AWARD_MATCHED",
        "bidding_zone": market["bidding_zone"],
        "delivery_local_date": market["delivery_local_date"],
        "preclearing_receipt_sha256": pre_receipt["sha256"],
        "gate_close_utc": gate.isoformat(),
        "prices_published_utc": published.isoformat(),
        "participant_result_received_utc": received.isoformat(),
        "dispatch_plan_created_utc": planned.isoformat(),
        "award_provenance": award["award_provenance"],
        "offered_mwh": receipt["offered_mwh"],
        "accepted_mwh": accepted,
        "clearing_prices_eur_mwh": prices,
        "simulated_delivered_mwh": delivered,
        "maximum_contract_vs_simulated_delivery_mwh": max_error,
        "total_accepted_mwh": math.fsum(accepted),
        "gross_contract_cashflow_proxy_eur": gross,
        "imbalance_settlement_included": False,
        "intraday_trading_included": False,
        "bid_acceptance_optimization_included": False,
        "real_exchange_transaction": False,
        "actual_export_measurements_included": False,
        "market_profit_claimed": False,
        "synthetic_chp_operating_contribution_eur": modelled["net_contribution_eur"],
        "gas_balance_max_residual_mwh": ledger["max_interval_balance_residual_mwh"],
        "heat_service_max_residual_mwh": ledger["max_heat_service_residual_mwh"],
        "claim_limit": "Matched fictional exogenous award and synthetic CHP production; no operational market settlement, grid export, plant profit or true price forecasting",
    }
    if include_solver_details:
        answer["physical_solver_and_hourly"] = modelled
    return answer


def run_manifest(manifest_path: Path, *, include_solver_details: bool = False) -> dict:
    """Offline, explicit two-stage scenario. Does not download data."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = frozenset({"model", "market", "delivery_slots", "preclearing_offer",
                          "exogenous_award", "synthetic_chp_config"})
    _fields(manifest, required, "market scenario")
    if manifest["model"] != MODEL:
        raise MarketBoundaryError("Unknown market-boundary protocol")
    config_path = manifest_path.parent/manifest["synthetic_chp_config"]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    market, slots = manifest["market"], manifest["delivery_slots"]
    pre = validate_preclearing_offer(market, slots, manifest["preclearing_offer"],
                                      config["electric_rating_mw"])
    post = audit_postclearing_delivery(
        market, slots, pre, manifest["exogenous_award"], config,
        include_solver_details=include_solver_details)
    return {
        "model_type": MODEL,
        "preclearing": pre,
        "postclearing": post,
        "study_boundary": "Synthetic awards, synthetic CHP and modelled electricity; explicit market information staging, not bidding, balancing, settlement or measured exports",
    }
