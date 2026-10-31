"""What-If Investment Simulator (deterministic, simulator-v2.0). Pandas builds the valuation grid; NumPy runs the path maths.

Correctness rules implemented here
- No look-ahead: every valuation point uses the last observation on or before that date, and the whole window ends on the
  evaluation date. Observations after the evaluation date are never read. Gaps longer than MAX_GAP_DAYS are errors, not
  silently carried forward.
- Cash-flow-neutral performance: the portfolio is tracked as a unitised NAV. External money buys new units at the current NAV,
  so contributions never appear as investment gains. Time-weighted return, drawdown and volatility are computed on that NAV.
- Money-weighted return (XIRR) is computed on the dated external cash flows and reported separately.
- Contributions are reported separately from gains. Simple "ending / contributed - 1" is never reported as a return.
- Uninvested cash earns the stated rate, accrued monthly and included in the NAV.
- Monthly contributions can be invested monthly, or accumulated in cash and invested quarterly (cash interest accrues meanwhile).
- The delayed scenario keeps initial capital in cash if the delay reaches the horizon.
- Hypothetical paths are seeded and labelled. They are not forecasts.

Floating-point note: path maths uses IEEE double. Input money is exact Decimal; outputs are rounded to paise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from app.services.financial_engine.dates import add_months
from app.services.financial_engine.rules import SIMULATOR_VERSION

MAX_GAP_DAYS = 10
MAX_DURATION_MONTHS = 360
MAX_CASH_RATE_PCT = Decimal("15")
HYPOTHETICAL_UP_MONTHLY = 0.01
HYPOTHETICAL_DOWN_MONTHLY = -0.015
GBM_ANNUAL_DRIFT = 0.10
GBM_ANNUAL_VOLATILITY = 0.20

LIMITATIONS = [
    "Excluded: entry and exit loads, expense-ratio drag, brokerage, STT, stamp duty, capital-gains tax, GST and inflation.",
    "Dividends and corporate actions are not included because no dividend series is stored for these instruments.",
    "Volatility is measured on monthly valuation points, which understates the day-to-day volatility of the asset.",
    "Results describe the historical or hypothetical path shown. They do not predict any future return.",
]


class SimulationError(ValueError):
    """Raised for invalid requests and unusable data. Messages are user-facing."""


@dataclass(frozen=True)
class AssetSeries:
    asset_id: int
    symbol: str
    name: str
    is_synthetic: bool
    source: str
    observations: list[tuple[date, Decimal]]


@dataclass(frozen=True)
class PriceGrid:
    dates: list[date]
    observation_dates: list[date]
    prices: np.ndarray
    first_observation: date
    last_observation: date


@dataclass(frozen=True)
class Plan:
    policy: str  # LUMP_SUM | STAGED_INITIAL | DELAYED_START
    initial: float
    monthly: float
    frequency: str  # MONTHLY | QUARTERLY
    delay: int
    cash_rate_pct: float


def _series(observations: list[tuple[date, Decimal]]) -> pd.Series:
    index = pd.DatetimeIndex([pd.Timestamp(d) for d, _ in observations])
    values = [float(p) for _, p in observations]
    return pd.Series(values, index=index).sort_index()


def _price_on(series: pd.Series, when: date) -> tuple[date, float] | None:
    position = int(series.index.searchsorted(pd.Timestamp(when), side="right")) - 1
    if position < 0:
        return None
    observed = series.index[position].date()
    if (when - observed).days > MAX_GAP_DAYS:
        return None
    return observed, float(series.iloc[position])


def build_grid(observations: list[tuple[date, Decimal]], evaluation: date, months: int, reference: date) -> PriceGrid:
    if evaluation > reference:
        raise SimulationError("The evaluation date cannot be in the future.")
    if not observations:
        raise SimulationError("No historical prices are stored for this instrument.")
    series = _series(observations)
    first, last = series.index[0].date(), series.index[-1].date()
    if evaluation > last:
        raise SimulationError(
            f"The evaluation date {evaluation.isoformat()} is after the last available price ({last.isoformat()})."
        )
    start = add_months(evaluation, -months)
    if start < first:
        raise SimulationError(
            f"Insufficient history: a {months}-month window needs prices from {start.isoformat()}, "
            f"but data begins {first.isoformat()}."
        )
    dates = [add_months(start, k) for k in range(months + 1)]
    prices: list[float] = []
    observed: list[date] = []
    for when in dates:
        point = _price_on(series, when)
        if point is None:
            raise SimulationError(
                f"Missing data: no price within {MAX_GAP_DAYS} days on or before {when.isoformat()}. "
                "Gaps are not carried forward."
            )
        observed.append(point[0])
        prices.append(point[1])
    return PriceGrid(dates, observed, np.array(prices, dtype=float), first, last)


def hypothetical_prices(path: str, start_price: float, months: int, seed: int) -> np.ndarray:
    k = np.arange(months + 1, dtype=float)
    if path == "ZERO_RETURN":
        return np.full(months + 1, start_price)
    if path == "HYPOTHETICAL_UP":
        return start_price * (1.0 + HYPOTHETICAL_UP_MONTHLY) ** k
    if path == "HYPOTHETICAL_DOWN":
        return start_price * (1.0 + HYPOTHETICAL_DOWN_MONTHLY) ** k
    if path == "SEEDED_GBM":
        rng = np.random.default_rng(seed)
        dt = 1.0 / 12.0
        shocks = rng.standard_normal(months)
        steps = (GBM_ANNUAL_DRIFT - 0.5 * GBM_ANNUAL_VOLATILITY**2) * dt + GBM_ANNUAL_VOLATILITY * math.sqrt(dt) * shocks
        return start_price * np.exp(np.concatenate([[0.0], np.cumsum(steps)]))
    raise SimulationError("Unknown market path.")


def xirr(flows: list[tuple[date, float]]) -> float | None:
    """Annualised money-weighted return (Actual/365) by bisection. Returns None when no sign change exists."""
    if not flows or not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    t0 = min(d for d, _ in flows)
    times = np.array([(d - t0).days / 365.0 for d, _ in flows])
    amounts = np.array([a for _, a in flows])

    def npv(rate: float) -> float:
        return float(np.sum(amounts / (1.0 + rate) ** times))

    low, high = -0.9999, 10.0
    f_low, f_high = npv(low), npv(high)
    if f_low * f_high > 0:
        return None
    for _ in range(300):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def run_path(prices: np.ndarray, dates: list[date], plan: Plan) -> dict[str, Any]:
    n = len(prices) - 1
    if n < 1:
        raise SimulationError("The window must span at least one month.")
    cash_rate_m = (1.0 + plan.cash_rate_pct / 100.0) ** (1.0 / 12.0) - 1.0

    units = 0.0
    staged = 0.0  # initial capital awaiting deployment
    contrib_cash = 0.0  # monthly contributions awaiting deployment
    shares = 0.0
    tranche = plan.initial / n if plan.policy == "STAGED_INITIAL" else 0.0

    nav = [1.0] * (n + 1)
    value = [0.0] * (n + 1)
    cash_hist = [0.0] * (n + 1)
    invested_cum = [0.0] * (n + 1)
    inflows: list[tuple[int, str, float]] = []
    trades: list[dict[str, Any]] = []
    interest_total = 0.0
    cumulative = 0.0

    for k in range(n + 1):
        price = float(prices[k])
        if k == 0:
            nav_pre = 1.0
        else:
            interest_staged = staged * cash_rate_m
            interest_contrib = contrib_cash * cash_rate_m
            staged += interest_staged
            contrib_cash += interest_contrib
            interest_total += interest_staged + interest_contrib
            pre_value = units * price + staged + contrib_cash
            nav_pre = pre_value / shares if shares > 0 else 1.0

        initial_in = plan.initial if k == 0 else 0.0
        monthly_in = plan.monthly if k >= 1 else 0.0
        if initial_in > 0:
            shares += initial_in / nav_pre
            staged += initial_in
            inflows.append((k, "STAGED_CAPITAL", initial_in))
        if monthly_in > 0:
            shares += monthly_in / nav_pre
            contrib_cash += monthly_in
            inflows.append((k, "EXTERNAL_MONTHLY", monthly_in))
        cumulative += initial_in + monthly_in

        deploy_staged = 0.0
        if plan.policy == "LUMP_SUM":
            deploy_staged = staged if k == 0 else 0.0
        elif plan.policy == "STAGED_INITIAL":
            if k >= 1:
                deploy_staged = staged if k == n else min(staged, tranche)
        elif plan.policy == "DELAYED_START":
            if plan.delay < n and k == plan.delay:
                deploy_staged = staged
        if deploy_staged > 1e-9:
            units += deploy_staged / price
            staged -= deploy_staged
            trades.append({"date": dates[k], "source": "STAGED_CAPITAL", "price": price,
                           "amount": deploy_staged, "units": deploy_staged / price})

        deploy_contrib = 0.0
        if contrib_cash > 1e-9:
            if plan.frequency == "MONTHLY":
                deploy_contrib = contrib_cash if k >= 1 else 0.0
            elif k >= 3 and k % 3 == 0:
                deploy_contrib = contrib_cash
        if deploy_contrib > 1e-9:
            units += deploy_contrib / price
            contrib_cash -= deploy_contrib
            trades.append({"date": dates[k], "source": "EXTERNAL_MONTHLY", "price": price,
                           "amount": deploy_contrib, "units": deploy_contrib / price})

        total_value = units * price + staged + contrib_cash
        value[k] = total_value
        cash_hist[k] = staged + contrib_cash
        nav[k] = total_value / shares if shares > 0 else 1.0
        invested_cum[k] = cumulative

    nav_arr = np.array(nav, dtype=float)
    total_contributions = sum(amount for _, _, amount in inflows)
    ending = value[n]
    twr = nav_arr[n] / nav_arr[0] - 1.0
    returns = nav_arr[1:] / nav_arr[:-1] - 1.0
    volatility = float(np.std(returns, ddof=1) * math.sqrt(12) * 100) if len(returns) >= 2 else None
    drawdown = float(np.min(nav_arr / np.maximum.accumulate(nav_arr) - 1.0) * 100)
    xirr_flows = [(dates[k], -amount) for k, _, amount in inflows] + [(dates[n], ending)]
    mwr = xirr(xirr_flows) if inflows else None

    return {
        "total_contributions": total_contributions,
        "ending_value": ending,
        "total_gain_loss": ending - total_contributions,
        "time_weighted_return_pct": twr * 100,
        "money_weighted_return_pct": mwr * 100 if mwr is not None else None,
        "annualised_volatility_pct": volatility,
        "max_drawdown_pct": drawdown,
        "cash_interest_earned": interest_total,
        "cash_held_at_end": cash_hist[n],
        "series": [
            {"index": k, "value": value[k], "nav": nav[k], "invested_cumulative": invested_cum[k], "cash": cash_hist[k]}
            for k in range(n + 1)
        ],
        "trades": trades,
        "inflows": [{"index": k, "source": src, "amount": amt} for k, src, amt in inflows],
    }


def rolling_windows(observations: list[tuple[date, Decimal]], evaluation: date) -> dict[str, Any]:
    """Every 12-month window whose start is a monthly anchor on or before the evaluation date (labelled accordingly)."""
    series = _series(observations)
    first = series.index[0].date()
    anchors: list[date] = []
    offset = 0
    while offset <= 600:
        anchor = add_months(evaluation, -12 - offset)
        if anchor < first:
            break
        anchors.append(anchor)
        offset += 1
    results: list[dict[str, Any]] = []
    skipped = 0
    for anchor in anchors:
        end = add_months(anchor, 12)
        start_point = _price_on(series, anchor)
        end_point = _price_on(series, end)
        if start_point is None or end_point is None or start_point[1] <= 0:
            skipped += 1
            continue
        results.append({
            "start": start_point[0].isoformat(),
            "end": end_point[0].isoformat(),
            "return_pct": (end_point[1] / start_point[1] - 1.0) * 100,
        })
    method = (
        "Every 12-month window whose start falls on a monthly anchor date on or before the evaluation date, "
        "using the last observation on or before each anchor. Windows with missing data are skipped and counted."
    )
    if not results:
        return {"method": method, "count": 0, "skipped": skipped, "best": None, "worst": None, "median_pct": None}
    ordered = sorted(results, key=lambda r: r["return_pct"])
    median = float(np.median([r["return_pct"] for r in results]))
    return {
        "method": method,
        "count": len(results),
        "skipped": skipped,
        "median_pct": round(median, 2),
        "worst": {**ordered[0], "return_pct": round(ordered[0]["return_pct"], 2)},
        "best": {**ordered[-1], "return_pct": round(ordered[-1]["return_pct"], 2)},
    }


def _r2(value: float | None) -> float | None:
    return None if value is None else round(float(value), 2)


def run_simulation(
    *,
    primary: AssetSeries,
    comparison: AssetSeries | None,
    scenario: str,
    amount_source: str,
    initial: Decimal,
    monthly: Decimal,
    frequency: str,
    duration_months: int,
    evaluation: date | None,
    market_path: str,
    cash_interest_pct: Decimal,
    delay_months: int,
    seed: int,
    reference: date,
) -> dict[str, Any]:
    if initial < 0 or monthly < 0:
        raise SimulationError("Amounts cannot be negative.")
    if initial == 0 and monthly == 0:
        raise SimulationError("Enter a starting amount, a monthly amount, or both.")
    if not 1 <= duration_months <= MAX_DURATION_MONTHS:
        raise SimulationError(f"Duration must be between 1 and {MAX_DURATION_MONTHS} months.")
    if not Decimal("0") <= cash_interest_pct <= MAX_CASH_RATE_PCT:
        raise SimulationError(f"Cash interest must be between 0% and {MAX_CASH_RATE_PCT}% a year.")
    if delay_months < 0:
        raise SimulationError("Delay cannot be negative.")
    if scenario == "COMPARISON" and comparison is None:
        raise SimulationError("A comparison scenario needs a second instrument to compare against.")
    if scenario != "COMPARISON" and comparison is not None:
        raise SimulationError("A comparison instrument was supplied for a non-comparison scenario.")
    if comparison is not None and comparison.asset_id == primary.asset_id:
        raise SimulationError("Choose two different instruments for a comparison.")
    if amount_source == "PROFILE_DERIVED" and scenario == "COMPARISON":
        raise SimulationError("Profile-derived amounts are not used for comparisons; run a labelled hypothetical comparison.")

    last_available = max(d for d, _ in primary.observations) if primary.observations else reference
    eval_date = evaluation or min(last_available, reference)
    grid = build_grid(primary.observations, eval_date, duration_months, reference)
    comp_grid = build_grid(comparison.observations, eval_date, duration_months, reference) if comparison else None

    if market_path == "HISTORICAL":
        prices = grid.prices
        comp_prices = comp_grid.prices if comp_grid else None
    else:
        prices = hypothetical_prices(market_path, float(grid.prices[0]), duration_months, seed)
        comp_prices = hypothetical_prices(market_path, float(comp_grid.prices[0]), duration_months, seed) if comp_grid else None

    policy = {"LUMP_SUM": "LUMP_SUM", "COMPARISON": "LUMP_SUM", "STAGED_INITIAL": "STAGED_INITIAL", "DELAYED_START": "DELAYED_START"}[scenario]
    plan = Plan(
        policy=policy,
        initial=float(initial),
        monthly=float(monthly),
        frequency=frequency,
        delay=delay_months,
        cash_rate_pct=float(cash_interest_pct),
    )
    primary_run = run_path(prices, grid.dates, plan)
    primary_run["asset_return_pct"] = (float(prices[-1]) / float(prices[0]) - 1.0) * 100
    primary_run["asset_max_drawdown_pct"] = float(np.min(prices / np.maximum.accumulate(prices) - 1.0) * 100)
    primary_run["asset_annualised_volatility_pct"] = (
        float(np.std(np.diff(prices) / prices[:-1], ddof=1) * math.sqrt(12) * 100) if len(prices) > 2 else None
    )

    comparison_result = None
    if comparison is not None and comp_prices is not None and comp_grid is not None:
        comp_run = run_path(comp_prices, comp_grid.dates, plan)
        comp_run["asset_return_pct"] = (float(comp_prices[-1]) / float(comp_prices[0]) - 1.0) * 100
        comp_run["asset_max_drawdown_pct"] = float(np.min(comp_prices / np.maximum.accumulate(comp_prices) - 1.0) * 100)
        comparison_result = {"asset": _asset_block(comparison), "run": _public_run(comp_run, comp_grid.dates)}

    windows = None
    if market_path == "HISTORICAL":
        windows = rolling_windows(primary.observations, eval_date)

    assumptions = [
        f"Evaluation date {eval_date.isoformat()}; the window starts {grid.dates[0].isoformat()} and uses monthly valuation points.",
        "Each valuation point uses the last observation on or before that date. No later prices are used.",
        f"Uninvested cash earns {float(cash_interest_pct):.2f}% a year, accrued monthly.",
        f"Monthly contributions are invested {'monthly' if frequency == 'MONTHLY' else 'quarterly, accumulated in cash until each quarter-end'}.",
        "Contributions are external money and are excluded from return, volatility and drawdown calculations.",
    ]
    if policy == "DELAYED_START":
        if delay_months >= duration_months:
            assumptions.append("The delay reaches the horizon, so the starting capital stays in cash for the whole window.")
        else:
            assumptions.append(f"Starting capital stays in cash for {delay_months} month(s), then is invested in one step.")
    if policy == "STAGED_INITIAL":
        assumptions.append("Starting capital is deployed in equal monthly tranches across the window.")
    if market_path != "HISTORICAL":
        assumptions.append(
            {
                "ZERO_RETURN": "Hypothetical path: the price never changes (0% return). Not a forecast.",
                "HYPOTHETICAL_UP": "Hypothetical path: a steady 1% rise per month. Not a forecast or expectation.",
                "HYPOTHETICAL_DOWN": "Hypothetical path: a steady 1.5% fall per month. Not a forecast.",
                "SEEDED_GBM": f"Hypothetical path: seeded geometric Brownian motion, drift {GBM_ANNUAL_DRIFT:.0%} and volatility {GBM_ANNUAL_VOLATILITY:.0%} a year (seed {seed}). Assumptions are illustrative, not predictive.",
            }[market_path]
        )

    limitations = list(LIMITATIONS)
    if primary.is_synthetic or (comparison is not None and comparison.is_synthetic):
        limitations.append("One or more price series are synthetic demonstration data, not live market data.")
    if market_path != "HISTORICAL":
        limitations.append("Hypothetical paths are not historical results and must not be read as expected returns.")

    return {
        "engine_version": SIMULATOR_VERSION,
        "scenario_type": scenario,
        "amount_source": amount_source,
        "financially_available": amount_source == "PROFILE_DERIVED",
        "market_path": market_path,
        "evaluation_date": eval_date.isoformat(),
        "window": {"start": grid.dates[0].isoformat(), "end": grid.dates[-1].isoformat(), "months": duration_months},
        "inputs": {
            "initial_amount": f"{initial:.2f}",
            "monthly_contribution": f"{monthly:.2f}",
            "contribution_frequency": frequency,
            "duration_months": duration_months,
            "cash_interest_pct": f"{cash_interest_pct:.2f}",
            "delay_months": delay_months,
            "seed": seed,
        },
        "data_period": {
            "first_observation": grid.first_observation.isoformat(),
            "last_observation": grid.last_observation.isoformat(),
            "source": primary.source,
            "is_synthetic": primary.is_synthetic,
            "observations_used": len(set(grid.observation_dates)),
        },
        "primary": {"asset": _asset_block(primary), "run": _public_run(primary_run, grid.dates)},
        "comparison": comparison_result,
        "windows": windows,
        "labels": {
            "total_contributions": "Money you put in (external contributions). This is not a return.",
            "total_gain_loss": "Ending value minus contributions. Includes market movement and cash interest.",
            "time_weighted_return_pct": "Cash-flow-neutral return (time-weighted, from the NAV). Use this to judge the strategy.",
            "money_weighted_return_pct": "Annualised return on your actual dated cash flows (XIRR). It depends on when you invested.",
            "annualised_volatility_pct": "Standard deviation of monthly NAV returns, annualised by √12.",
            "max_drawdown_pct": "Largest fall of the NAV from a previous peak, cash-flow-neutral.",
            "asset_return_pct": "Price change of the instrument over the window only.",
        },
        "assumptions": assumptions,
        "limitations": limitations,
        "engine_note": "Floating-point path maths; outputs are rounded to paise and two decimal places.",
    }


def _asset_block(asset: AssetSeries) -> dict[str, Any]:
    return {"asset_id": asset.asset_id, "symbol": asset.symbol, "name": asset.name,
            "is_synthetic": asset.is_synthetic, "source": asset.source}


def _public_run(run: dict[str, Any], dates: list[date]) -> dict[str, Any]:
    series = [
        {
            "date": dates[point["index"]].isoformat(),
            "value": round(point["value"], 2),
            "nav": round(point["nav"], 6),
            "invested_cumulative": round(point["invested_cumulative"], 2),
            "cash": round(point["cash"], 2),
        }
        for point in run["series"]
    ]
    return {
        "metrics": {
            "total_contributions": f"{run['total_contributions']:.2f}",
            "ending_value": f"{run['ending_value']:.2f}",
            "total_gain_loss": f"{run['total_gain_loss']:.2f}",
            "time_weighted_return_pct": _r2(run["time_weighted_return_pct"]),
            "money_weighted_return_pct": _r2(run["money_weighted_return_pct"]),
            "annualised_volatility_pct": _r2(run["annualised_volatility_pct"]),
            "max_drawdown_pct": _r2(run["max_drawdown_pct"]),
            "cash_interest_earned": f"{run['cash_interest_earned']:.2f}",
            "cash_held_at_end": f"{run['cash_held_at_end']:.2f}",
            "asset_return_pct": _r2(run["asset_return_pct"]),
            "asset_max_drawdown_pct": _r2(run["asset_max_drawdown_pct"]),
            "asset_annualised_volatility_pct": _r2(run.get("asset_annualised_volatility_pct")),
        },
        "series": series,
        "trades": [
            {"date": t["date"].isoformat(), "source": t["source"], "price": round(t["price"], 4),
             "amount": f"{t['amount']:.2f}", "units": round(t["units"], 6)}
            for t in run["trades"]
        ],
        "contributions": [
            {"date": dates[item["index"]].isoformat(), "source": item["source"], "amount": f"{item['amount']:.2f}"}
            for item in run["inflows"]
        ],
    }
