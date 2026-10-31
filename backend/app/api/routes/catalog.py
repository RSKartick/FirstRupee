"""Public instrument catalogue and live market benchmarks."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import csrf_protected, database, reference_date
from app.core.errors import NotFoundError, ValidationProblem
from app.data_sources.demo_catalog import fetch_live_benchmarks
from app.data_sources.provider import get_provider
from app.models.tables import Asset, MarketObservation
from app.repositories import owned as repo
from app.seed import seed_catalog
from app.services.financial_engine.market import market_snapshot

router = APIRouter(prefix="/assets", tags=["assets"])
VOLATILITY_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
MAX_HISTORY_YEARS = 10


def _summary(db: Session, asset: Asset) -> dict[str, Any]:
    stats = db.execute(
        select(func.count(MarketObservation.id), func.min(MarketObservation.obs_date), func.max(MarketObservation.obs_date))
        .where(MarketObservation.asset_id == asset.id)
    ).one()
    latest_row = db.execute(
        select(MarketObservation.close, MarketObservation.obs_date)
        .where(MarketObservation.asset_id == asset.id)
        .order_by(MarketObservation.obs_date.desc())
        .limit(2)
    ).all()
    latest_price = f"{latest_row[0].close:.2f}" if latest_row else None
    day_change_pct = None
    if len(latest_row) >= 2 and float(latest_row[1].close) > 0:
        day_change_pct = round((float(latest_row[0].close) / float(latest_row[1].close) - 1.0) * 100.0, 2)
    return {
        "id": asset.id,
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "description": asset.description,
        "volatility_class": asset.volatility_class,
        "min_horizon_months": asset.min_horizon_months,
        "expense_ratio_pct": f"{asset.expense_ratio_pct:.2f}" if asset.expense_ratio_pct is not None else None,
        "is_synthetic": asset.is_synthetic,
        "data_source": asset.data_source,
        "data_as_of": asset.data_as_of.isoformat(),
        "observations": stats[0],
        "first_observation": stats[1].isoformat() if stats[1] else None,
        "last_observation": stats[2].isoformat() if stats[2] else None,
        "latest_price": latest_price,
        "day_change_pct": day_change_pct,
    }


@router.get("/benchmarks")
def list_benchmarks() -> dict[str, Any]:
    return {
        "benchmarks": fetch_live_benchmarks(),
        "provider": get_provider().id,
    }


@router.post("/refresh", dependencies=[Depends(csrf_protected)])
def refresh_catalog(db: Session = Depends(database)) -> dict[str, Any]:
    seed_catalog(db, force_refresh=True)
    assets = db.scalars(select(Asset).order_by(Asset.asset_type, Asset.name)).all()
    return {
        "refreshed": True,
        "assets": [_summary(db, asset) for asset in assets],
        "provider": get_provider().id,
    }


@router.get("")
def list_assets(
    asset_type: Literal["EQUITY", "INDEX_FUND", "MUTUAL_FUND", "ETF", "FIXED_INCOME", "GOLD"] | None = None,
    max_volatility: Literal["LOW", "MODERATE", "HIGH"] | None = None,
    max_min_horizon_months: int | None = Query(default=None, ge=1, le=240),
    db: Session = Depends(database),
) -> dict[str, Any]:
    assets = db.scalars(select(Asset).order_by(Asset.asset_type, Asset.name)).all()
    items = []
    for asset in assets:
        if asset_type and asset.asset_type != asset_type:
            continue
        if max_volatility and VOLATILITY_ORDER[asset.volatility_class] > VOLATILITY_ORDER[max_volatility]:
            continue
        if max_min_horizon_months and asset.min_horizon_months > max_min_horizon_months:
            continue
        items.append(_summary(db, asset))
    provider = get_provider()
    return {
        "assets": items,
        "provider": provider.id,
        "note": provider.attribution,
    }


@router.get("/{asset_id}")
def get_asset(asset_id: int, db: Session = Depends(database), as_of: date = Depends(reference_date)) -> dict[str, Any]:
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise NotFoundError("Instrument not found.")
    provider = get_provider()
    observations = provider.observations(db, asset.id)
    snapshot = market_snapshot(observations, as_of, asset_name=asset.name, is_synthetic=asset.is_synthetic, source=asset.data_source)
    evidence = [
        {"evidence_key": e.key, "title": e.title, "source_type": e.source_type, "verification_status": e.verification_status,
         "publication_date": e.publication_date.isoformat() if e.publication_date else None, "period": e.period,
         "summary": e.summary, "metrics": e.payload}
        for e in provider.evidence(db, asset.id)
    ]
    return {
        "asset": {
            **_summary(db, asset),
            "what_it_is": asset.what_it_is,
            "how_it_works": asset.how_it_works,
            "advantages": asset.advantages,
            "risks": asset.risks,
            "liquidity": asset.liquidity,
            "fees": asset.fees,
        },
        "evidence": evidence,
        "market_context": snapshot,
    }


@router.get("/{asset_id}/history")
def asset_history(
    asset_id: int,
    interval: Literal["monthly", "daily"] = "monthly",
    start: date | None = Query(default=None, alias="from"),
    end: date | None = Query(default=None, alias="to"),
    db: Session = Depends(database),
    as_of: date = Depends(reference_date),
) -> dict[str, Any]:
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise NotFoundError("Instrument not found.")
    if start and end and start > end:
        raise ValidationProblem("'from' must be on or before 'to'.")
    if end and end > as_of:
        raise ValidationProblem("'to' cannot be in the future.")
    if start and end and (end - start).days > MAX_HISTORY_YEARS * 366:
        raise ValidationProblem(f"The requested range is longer than {MAX_HISTORY_YEARS} years.")
    points = [(d, c) for d, c in get_provider().observations(db, asset.id)
              if (start is None or d >= start) and (end is None or d <= end) and d <= as_of]
    if interval == "monthly":
        last_per_month: dict[str, tuple[date, Any]] = {}
        for d, c in points:
            last_per_month[d.strftime("%Y-%m")] = (d, c)
        points = sorted(last_per_month.values(), key=lambda item: item[0])
    return {
        "asset_id": asset.id,
        "interval": interval,
        "points": [{"date": d.isoformat(), "close": f"{c:.4f}"} for d, c in points],
        "source": asset.data_source,
        "is_synthetic": asset.is_synthetic,
    }
