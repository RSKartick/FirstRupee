"""Market-context metrics from stored observations.

Rules
- Observations dated after the reference date are a data error: the snapshot reports FUTURE_DATA_INVALID and uses nothing.
- Observations older than MARKET_STALE_AFTER_DAYS are reported as STALE with no current metrics, so old prices are never shown as current.
- Trailing 12-month return is only produced when an observation at least 365 days older than the latest one exists.
- Statistics use float64 on prices (market quotes, not money balances). Results are rounded for display.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

from app.services.financial_engine.rules import MARKET_STALE_AFTER_DAYS


def market_snapshot(
    observations: list[tuple[date, Decimal]],
    as_of: date,
    *,
    asset_name: str,
    is_synthetic: bool,
    source: str,
    stale_after_days: int = MARKET_STALE_AFTER_DAYS,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "asset_name": asset_name,
        "is_synthetic": is_synthetic,
        "source": source,
        "as_of": as_of.isoformat(),
        "stale_after_days": stale_after_days,
        "disclaimer": "Historical context only. Not a prediction of future returns or of a good time to invest.",
    }
    future = [d for d, _ in observations if d > as_of]
    if future:
        return {**base, "status": "FUTURE_DATA_INVALID", "observations_used": 0,
                "note": "Observations dated after the reference date were found. Market context is unavailable until the data is corrected."}

    obs = sorted(((d, float(c)) for d, c in observations), key=lambda item: item[0])
    if not obs:
        return {**base, "status": "UNAVAILABLE", "observations_used": 0,
                "note": "No market observations are stored for this instrument."}

    last_date, last_close = obs[-1]
    age = (as_of - last_date).days
    if age > stale_after_days:
        return {**base, "status": "STALE", "last_observation": last_date.isoformat(), "age_days": age, "observations_used": 0,
                "note": f"The latest observation is {age} days old (limit {stale_after_days}). Market context is withheld so old prices are not treated as current."}

    window = obs[-253:]
    prices = np.array([price for _, price in window], dtype=float)
    returns = np.diff(prices) / prices[:-1]
    volatility = float(np.std(returns, ddof=1) * np.sqrt(252) * 100) if len(returns) >= 2 else None

    year_ago = last_date - timedelta(days=365)
    earlier = [(d, p) for d, p in obs if d <= year_ago]
    trailing: float | None = None
    trailing_note = "Fewer than 12 months of observations: no trailing 12-month return is shown."
    if earlier:
        base_date, base_price = earlier[-1]
        if (last_date - base_date).days >= 365 and base_price > 0:
            trailing = (last_close / base_price - 1) * 100
            trailing_note = f"Compares {base_date.isoformat()} with {last_date.isoformat()}."

    return {
        **base,
        "status": "OK",
        "last_observation": last_date.isoformat(),
        "age_days": age,
        "observations_used": len(window),
        "annualised_volatility_pct": round(volatility, 2) if volatility is not None else None,
        "trailing_12m_return_pct": round(trailing, 2) if trailing is not None else None,
        "trailing_12m_note": trailing_note,
        "note": "Volatility is computed from daily observations in the most recent year available.",
    }
